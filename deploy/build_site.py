"""Build the questionnaire as a static site (hosted on a free static Hugging Face Space).

The page runs Streamlit inside the visitor's browser (stlite), so there is no server that can
drop requests or go to sleep. Answers never leave the browser until the participant downloads them.

Usage (from the repo root):  python3 deploy/build_site.py [output folder, default _site]
Preview it:                  python3 -m http.server 8000 -d _site   then open http://localhost:8000
"""
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

STLITE = "1.12.0"  # @stlite/browser version on jsDelivr (bundles Streamlit 1.65)
ROOT = Path(__file__).resolve().parents[1]

# Hugging Face reads this header to serve the folder as a free static Space.
SPACE_CARD = """---
title: LPB Style Questionnaire
emoji: ✍️
colorFrom: blue
colorTo: yellow
sdk: static
pinned: false
---

Lexicon Personality Bot style questionnaire (SJSU CMPE 259, Team 3).
Built from the team's GitHub repo by `deploy/build_site.py`; do not edit files here.
"""


def version_tag():
    """Short commit id, added to file URLs so browsers fetch the new files after each deploy."""
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "dev"


def streamlit_config():
    """Theme from .streamlit/config.toml, flattened the way stlite wants it ("theme.primaryColor")."""
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    flat = {f"theme.{key}": value for key, value in cfg.get("theme", {}).items()}
    flat["client.toolbarMode"] = "viewer"
    return flat


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "_site").resolve()
    if out == ROOT or out in ROOT.parents:
        sys.exit(f"Refusing to build into {out}; pick an empty folder like _site")
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "app", out / "app",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))

    tag = version_tag()
    files = {}
    for path in sorted((out / "app").rglob("*")):
        if path.is_file():
            rel = path.relative_to(out).as_posix()
            files[rel] = {"url": f"./{rel}?v={tag}"}

    html = (ROOT / "deploy" / "index.html").read_text(encoding="utf-8")
    html = (html.replace("__STLITE__", STLITE)
                .replace("__FILES__", json.dumps(files, indent=2))
                .replace("__CONFIG__", json.dumps(streamlit_config())))
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / "README.md").write_text(SPACE_CARD, encoding="utf-8")
    print(f"Built {out}: {len(files)} app files, stlite {STLITE}, version {tag}")


if __name__ == "__main__":
    main()
