"""Migrate the old floating hero cards; verify the resulting responsive layout."""
from __future__ import annotations

import argparse
import functools
import html
import json
import re
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "/* hero layout v2: photo-bound outline and in-flow information */"
END = "/* end hero layout v2 */"
CSS = r'''
/* hero layout v2: photo-bound outline and in-flow information */
@media screen {
  .hero .hero-visual {
    display: flex;
    flex-direction: column;
    gap: 16px;
    width: 100%;
    max-width: none;
    min-width: 0;
    padding: 6px;
    margin: 0;
  }
  .hero .hero-image-wrap {
    width: 100%;
    flex: none;
    outline: 1px solid #d9b8bc;
    outline-offset: 5px;
  }
  .hero .hero-image-wrap::after { content: none; }
  .hero .hero-meta {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: stretch;
    width: 100%;
    min-width: 0;
    padding: 13px 0;
    background: var(--white);
    border: 1px solid var(--line);
    border-radius: 14px;
  }
  .hero .hero-note,
  .hero .rating-pill {
    position: static;
    inset: auto;
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    max-width: none;
    margin: 0;
    padding: 0 16px;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    transform: none;
    line-height: 1.4;
  }
  .hero .hero-note > .icon {
    width: 21px;
    height: 21px;
    color: var(--wine);
  }
  .hero .hero-note > span,
  .hero .hero-rating-value {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;
    min-width: 0;
  }
  .hero .hero-meta-label {
    font-family: var(--sans);
    font-size: 11px;
    font-weight: 400;
    line-height: 1.4;
    letter-spacing: 0;
    color: var(--muted);
  }
  .hero .hero-note strong {
    font-family: var(--sans);
    font-size: 14px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    color: var(--ink);
  }
  .hero .rating-pill {
    border-left: 1px solid var(--line);
    color: var(--wine);
  }
  .hero .rating-star { font-size: 19px; }
  .hero .rating-pill strong {
    font-size: 23px;
    line-height: 1;
    letter-spacing: -.035em;
    font-weight: 600;
    color: var(--ink);
  }
  .hero .rating-pill .icon {
    width: 16px;
    height: 16px;
    margin-left: auto;
  }
  .hero .rating-pill:hover .hero-meta-label {
    color: var(--wine);
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .hero .rating-pill:focus-visible {
    outline-offset: 4px;
    border-radius: 4px;
  }
}
@media screen and (min-width: 601px) and (max-width: 900px) {
  .hero {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 28px;
    min-height: 0;
  }
  .hero h1 { font-size: clamp(46px, 7vw, 63px); }
  .hero .hero-doodle { display: none; }
  .hero .hero-note,
  .hero .rating-pill { gap: 6px; padding-inline: 9px; }
  .hero .hero-note > .icon { width: 17px; height: 17px; }
  .hero .hero-note strong { font-size: 11px; }
  .hero .hero-meta-label { font-size: 9px; }
  .hero .rating-pill .icon { display: none; }
}
@media screen and (max-width: 600px) {
  .hero { gap: 20px; padding-bottom: 28px; }
  .hero .hero-visual { gap: 14px; padding: 6px; }
  .hero .hero-image-wrap { max-height: none; aspect-ratio: 1.08; }
  .hero .hero-meta { padding-block: 12px; }
  .hero .hero-note,
  .hero .rating-pill { gap: 9px; padding-inline: 13px; }
  .hero .hero-note > .icon { width: 20px; height: 20px; }
  .hero .hero-note strong { font-size: 13px; }
  .hero .hero-meta-label { font-size: 10px; }
}
@media screen and (min-width: 480px) and (max-width: 600px) {
  .hero .hero-image-wrap { aspect-ratio: 1.3; }
}
@media screen and (max-width: 359px) {
  .hero .hero-note,
  .hero .rating-pill { gap: 7px; padding-inline: 10px; }
  .hero .hero-note > .icon { width: 18px; height: 18px; }
  .hero .hero-note strong { font-size: 12px; }
  .hero .rating-pill .icon { display: none; }
}
/* end hero layout v2 */
'''


def apply() -> None:
    index_path = ROOT / "index.html"
    css_path = ROOT / "styles.css"
    source = index_path.read_text(encoding="utf-8")
    styles = css_path.read_text(encoding="utf-8")
    visual_start = source.index('      <div class="hero-visual">')
    visual_end = source.index('    </section>', visual_start)
    old = source[visual_start:visual_end]
    image = re.search(r'<img\b[^>]*class="hero-image"[^>]*>', old)
    rating = re.search(r'<a\b[^>]*class="rating-pill"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', old, re.S)
    hours = re.search(r'\b\d{2}:\d{2}[–—-]\d{2}:\d{2}\b', old)
    if not image or not rating or not hours:
        raise RuntimeError("Hero markup changed; refusing a partial rewrite.")
    value = re.search(r'<strong>([^<]+)</strong>', rating.group(2))
    if not value:
        raise RuntimeError("Could not preserve the existing rating.")
    score = html.escape(html.unescape(value.group(1)))
    link = html.escape(html.unescape(rating.group(1)), quote=True)
    replacement = f'''      <div class="hero-visual">
        <div class="hero-image-wrap">{image.group(0)}</div>
        <div class="hero-meta">
          <div class="hero-note">
            <svg class="icon" aria-hidden="true"><use href="#i-clock"/></svg>
            <span><span class="hero-meta-label">Ежедневно</span><strong>{hours.group(0)}</strong></span>
          </div>
          <a class="rating-pill" href="{link}" target="_blank" rel="noopener noreferrer" aria-label="Рейтинг студии {score} из 5 на Яндекс Картах">
            <span class="rating-star" aria-hidden="true">★</span>
            <span class="hero-rating-value"><strong>{score}</strong><span class="hero-meta-label">Яндекс Карты</span></span>
            <svg class="icon" aria-hidden="true"><use href="#i-up"/></svg>
          </a>
        </div>
      </div>
'''
    source = source[:visual_start] + replacement + source[visual_end:]
    source, count = re.subn(r'href="\./styles\.css(?:\?[^"]*)?"',
                            'href="./styles.css?v=hero-layout-2"', source)
    if count != 1:
        raise RuntimeError("Expected exactly one stylesheet link.")
    styles = re.sub(r'/\* mobile hero note placement fix \*/\s*'
                    r'@media\(max-width:600px\)\{.*?\n\}\s*'
                    r'@media\(max-width:359px\)\{.*?\n\}', '', styles, flags=re.S)
    styles = re.sub(re.escape(START) + r'.*?' + re.escape(END), '', styles, flags=re.S)
    # Remove only obsolete standalone ornament rules, leaving unrelated CSS intact.
    styles = re.sub(r'\.(?:hero-orbit|hero-side-label)\{[^{}]*\}', '', styles)
    index_path.write_text(source, encoding="utf-8")
    css_path.write_text(styles.rstrip() + '\n\n' + CSS.strip() + '\n', encoding="utf-8")
    print("Updated index.html and styles.css; existing photo, hours and rating preserved.")


@contextmanager
def serve():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def verify() -> None:
    from playwright.sync_api import sync_playwright
    out = ROOT / "test-results" / "hero-layout"
    out.mkdir(parents=True, exist_ok=True)
    report = []
    with serve() as url, sync_playwright() as pw:
        for name in ("chromium", "webkit"):
            browser = getattr(pw, name).launch()
            for width in (320, 360, 375, 390, 430, 600, 601, 768, 900, 1024, 1440):
                page = browser.new_page(viewport={"width": width, "height": 1200}, device_scale_factor=1)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url, wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                page.wait_for_function("document.querySelector('.hero-image').complete && document.querySelector('.hero-image').naturalWidth > 0")
                data = page.evaluate('''() => {
                  const box = selector => {
                    const e = document.querySelector(selector), r = e.getBoundingClientRect();
                    return {x:r.x, y:r.y, right:r.right, bottom:r.bottom, width:r.width,
                            height:r.height, scroll:e.scrollWidth, client:e.clientWidth};
                  };
                  const image = document.querySelector('.hero-image-wrap');
                  return {photo:box('.hero-image-wrap'), meta:box('.hero-meta'),
                    hours:box('.hero-note'), rating:box('.rating-pill'),
                    hoursText:box('.hero-note > span'), ratingText:box('.hero-rating-value'),
                    viewport:innerWidth, pageWidth:document.documentElement.scrollWidth,
                    orbit:!!document.querySelector('.hero-orbit'),
                    outline:getComputedStyle(image).outlineStyle,
                    offset:getComputedStyle(image).outlineOffset};
                }''')
                label = f"{name} {width}px"
                assert data["pageWidth"] <= width + 1, (label, "horizontal overflow", data)
                assert not data["orbit"], (label, "old detached outline is still present")
                assert data["outline"] == "solid" and data["offset"] == "5px", (label, data)
                assert 8 <= data["meta"]["y"] - data["photo"]["bottom"] <= 20, (label, "photo/metadata gap", data)
                assert abs(data["meta"]["x"] - data["photo"]["x"]) <= 1, (label, "left alignment", data)
                assert abs(data["meta"]["width"] - data["photo"]["width"]) <= 1, (label, "width alignment", data)
                assert data["hours"]["y"] > data["photo"]["bottom"], (label, "hours cover photo", data)
                assert data["rating"]["y"] > data["photo"]["bottom"], (label, "rating covers photo", data)
                assert data["hours"]["right"] <= data["rating"]["x"] + 1, (label, "cards overlap", data)
                for key in ("hours", "rating", "hoursText", "ratingText"):
                    assert data[key]["scroll"] <= data[key]["client"] + 1, (label, "text overflow", key, data)
                assert not errors, (label, errors)
                if width in (320, 390, 768, 1440):
                    page.locator('.hero').screenshot(path=str(out / f"{name}-{width}.png"))
                # Only open and close the local dialog. Never submit an appointment.
                page.locator('.hero-actions [data-book]').click()
                assert page.locator('#booking-dialog').is_visible(), (label, "booking dialog did not open")
                page.keyboard.press("Escape")
                assert not page.locator('#booking-dialog').is_visible(), (label, "booking dialog did not close")
                report.append({"browser": name, "width": width, "status": "passed", "layout": data})
                page.close()
            browser.close()
    (out / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Passed {len(report)} hero layout and booking-dialog checks.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Test the existing result without modifying files.")
    args = parser.parse_args()
    verify() if args.verify else apply()
