# -*- coding: utf-8 -*-
"""Fabrique l'archive du plugin (neobase.bestiarystudio-<version>.zip) : manifeste, page, volet système, ui/ et engine/."""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"test_server.py"}


def main():
    m = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    out = ROOT / f"{m['id']}-{m['version']}.zip"
    files = [ROOT / n for n in ("plugin.json", "index.js", "main.js", "icon.png")]
    files += sorted(p for p in (ROOT / "ui").iterdir() if p.is_file())
    files += sorted(p for p in (ROOT / "engine").glob("*.py") if p.name not in SKIP)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.relative_to(ROOT).as_posix())
    print(out.name, len(files), "fichiers", out.stat().st_size // 1024, "Ko")


if __name__ == "__main__":
    main()
