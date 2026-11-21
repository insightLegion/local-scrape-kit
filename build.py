"""Build dist/<target>.js = targets/<target>.js + engine.js (one file to paste). `python build.py --check` fails if dist is old."""
import sys
from pathlib import Path

HERE = Path(__file__).parent


def build():
    engine = (HERE / "engine.js").read_text(encoding="utf-8")
    out = {}
    for t in sorted((HERE / "targets").glob("*.js")):
        out[HERE / "dist" / t.name] = (f"// local-scrape-kit: {t.stem}. Paste all of this into the browser console (F12 -> Console).\n"
                                       f"// Built by build.py from targets/{t.name} and engine.js. Rules: GUIDELINES.md.\n"
                                       + t.read_text(encoding="utf-8") + "\n" + engine)
    return out


if __name__ == "__main__":
    files = build()
    if "--check" in sys.argv:
        old = [p.name for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if old:
            sys.exit(f"dist is out of date: {', '.join(old)}. Run: python build.py")
        print("dist is up to date")
    else:
        (HERE / "dist").mkdir(exist_ok=True)
        for p, text in files.items():
            p.write_text(text, encoding="utf-8", newline="\n")
            print("wrote", p.relative_to(HERE))
