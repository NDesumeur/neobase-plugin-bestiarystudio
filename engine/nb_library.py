# -*- coding: utf-8 -*-
"""NeoBestiary Studio - bibliothèque de créatures (JSON + images sur disque)."""
import json
import re
import shutil
import threading
import time
from pathlib import Path

from PIL import Image

from nb_core import fold

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "_", fold(name)).strip("_")
    return s or "creature"


class Library:
    def __init__(self, root):
        self.root = Path(root)
        self.cdir = self.root / "creatures"
        self.cdir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.root / "config.json"
        self.lock = threading.RLock()

    # ------------------------------------------------------------ config
    def load_config(self, defaults):
        cfg = dict(defaults)
        try:
            cfg.update(json.loads(self.config_path.read_text(encoding="utf-8")))
        except Exception:
            pass
        return cfg

    def save_config(self, cfg):
        with self.lock:
            self.config_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---------------------------------------------------------- créatures
    def dir(self, slug):
        return self.cdir / slug

    def _file(self, slug):
        return self.dir(slug) / "creature.json"

    def exists(self, slug):
        return self._file(slug).is_file()

    def load(self, slug):
        with self.lock:
            try:
                return json.loads(self._file(slug).read_text(encoding="utf-8"))
            except Exception:
                return None

    def save(self, rec):
        with self.lock:
            rec["updated"] = time.time()
            d = self.dir(rec["slug"])
            (d / "views").mkdir(parents=True, exist_ok=True)
            self._file(rec["slug"]).write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")

    def new_record(self, name):
        return dict(slug=slugify(name), name=name, description="", translated="", style="RPG pixel art",
                    custom_style="", palette_name="Auto (selon la description)", palette=[], prompt="",
                    prompt_mode="compact", must="", avoid="", created=time.time(), updated=time.time(),
                    views={}, notes="")

    def list(self):
        out = []
        for d in self.cdir.iterdir():
            f = d / "creature.json"
            if f.is_file():
                try:
                    out.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
        out.sort(key=lambda r: r.get("updated", 0), reverse=True)
        return out

    def delete(self, slug):
        with self.lock:
            shutil.rmtree(self.dir(slug), ignore_errors=True)

    # -------------------------------------------------------------- images
    def _next_name(self, rec, view_key):
        d = self.dir(rec["slug"]) / "views"
        n = 1
        while (d / f"{view_key}_{n:03d}.png").exists():
            n += 1
        return f"{view_key}_{n:03d}.png"

    def add_image(self, slug, view_key, src, note=""):
        """Copie une image externe dans la bibliothèque (convertie en PNG) et l'active."""
        with self.lock:
            rec = self.load(slug)
            if rec is None:
                return None
            name = self._next_name(rec, view_key)
            dst = self.dir(slug) / "views" / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            Image.open(src).convert("RGBA").save(dst)
            return self._register(rec, view_key, name, note or Path(src).name)

    def add_pil(self, slug, view_key, img, note=""):
        with self.lock:
            rec = self.load(slug)
            if rec is None:
                return None
            name = self._next_name(rec, view_key)
            dst = self.dir(slug) / "views" / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            img.convert("RGBA").save(dst)
            return self._register(rec, view_key, name, note)

    def _register(self, rec, view_key, name, note):
        v = rec["views"].setdefault(view_key, {"files": [], "active": 0, "notes": []})
        v.setdefault("notes", [""] * len(v["files"]))
        v["files"].append("views/" + name)
        v["notes"].append(note)
        v["active"] = len(v["files"]) - 1
        self.save(rec)
        return rec

    def active_path(self, rec, view_key):
        v = rec.get("views", {}).get(view_key)
        if not v or not v["files"]:
            return None
        p = self.dir(rec["slug"]) / v["files"][min(v["active"], len(v["files"]) - 1)]
        return p if p.is_file() else None

    def version_info(self, rec, view_key):
        v = rec.get("views", {}).get(view_key)
        if not v or not v["files"]:
            return 0, 0, ""
        i = min(v["active"], len(v["files"]) - 1)
        notes = v.get("notes", [])
        return i + 1, len(v["files"]), (notes[i] if i < len(notes) else "")

    def cycle(self, slug, view_key, delta):
        with self.lock:
            rec = self.load(slug)
            v = rec["views"].get(view_key) if rec else None
            if not v or not v["files"]:
                return rec
            v["active"] = (v["active"] + delta) % len(v["files"])
            self.save(rec)
            return rec

    def set_active(self, slug, view_key, index):
        with self.lock:
            rec = self.load(slug)
            v = rec["views"].get(view_key) if rec else None
            if v and v["files"]:
                v["active"] = max(0, min(int(index), len(v["files"]) - 1))
                self.save(rec)
            return rec

    def remove_version(self, slug, view_key):
        with self.lock:
            rec = self.load(slug)
            v = rec["views"].get(view_key) if rec else None
            if not v or not v["files"]:
                return rec
            i = min(v["active"], len(v["files"]) - 1)
            try:
                (self.dir(slug) / v["files"][i]).unlink()
            except OSError:
                pass
            v["files"].pop(i)
            if v.get("notes"):
                v["notes"].pop(i)
            v["active"] = max(0, min(v["active"], len(v["files"]) - 1))
            if not v["files"]:
                rec["views"].pop(view_key)
            self.save(rec)
            return rec

    def sprites_dir(self, slug):
        d = self.dir(slug) / "sprites"
        d.mkdir(parents=True, exist_ok=True)
        return d
