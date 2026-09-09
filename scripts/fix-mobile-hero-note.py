from pathlib import Path
p=Path('styles.css')
s=p.read_text(encoding='utf-8')
marker='/* mobile hero note placement fix */'
if marker not in s:
    s += '''\n\n/* mobile hero note placement fix */\n@media(max-width:600px){\n  .hero-visual{padding-top:54px;}\n  .hero-note{\n    top:0;\n    left:22px;\n    transform:rotate(-2deg);\n    z-index:3;\n    padding:12px 16px;\n    max-width:245px;\n  }\n  .hero-note .icon{width:20px;height:20px;}\n  .hero-note em{font-size:14px;}\n}\n@media(max-width:359px){\n  .hero-visual{padding-top:50px;}\n  .hero-note{left:12px;max-width:225px;padding:11px 14px;}\n}\n'''
p.write_text(s,encoding='utf-8')
