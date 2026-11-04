# -*- coding: utf-8 -*-
"""NeoBestiary Studio - service local (API JSON) pour le plugin NeoBase.

python nb_server.py --token T [--port 0] [--library DOSSIER] [--comfy-root DOSSIER] [--comfy-url URL] [--fake]
Écrit « NB_READY <port> » sur la sortie dès qu'il écoute. Seul 127.0.0.1 est servi et chaque requête doit
porter l'en-tête X-NB-Token (le plugin le connaît, les autres programmes de la machine non).
"""
import argparse
import base64
import io
import json
import os
import shutil
import sys
import threading
import urllib.request
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nb_comfy as nbc  # noqa: E402
import nb_library  # noqa: E402
import nb_attack  # noqa: E402
import nb_check  # noqa: E402
import nb_stats  # noqa: E402
import nb_sprite as sp  # noqa: E402

DIRS = ("bas", "gauche", "droite", "haut")
FRAMES = ("pas1", "repos", "pas2")  # colonnes de la planche ; lecture : pas1, repos, pas2, repos
CELL = 64
SKETCHES = 3  # esquisses du design proposées au choix avant le reste
LAB_DEFAULTS = dict(colors=24, outline=True, outline_color="#0b0b12", lock_palette=True, mirror=True)


def frame_key(d, f):
    return d if f == "repos" else f"{d}_{f}"


def png_bytes(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------- tâches

class Jobs:
    """Une tâche à la fois (le GPU ne fait qu'une image à la fois de toute façon)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.state = dict(id=0, kind="", running=False, step="", progress=0.0, error="", slug="", done=True)
        self._cancel = False

    def start(self, kind, fn, total=1, slug=""):
        with self.lock:
            if self.state["running"]:
                raise RuntimeError("Une tâche est déjà en cours.")
            self._cancel = False
            self.state = dict(id=self.state["id"] + 1, kind=kind, running=True, step="Préparation", progress=0.0,
                              error="", slug=slug, done=False, total=total, count=0)
            jid = self.state["id"]

        def progress(label):
            with self.lock:
                self.state["count"] += 1
                self.state["step"] = label
                self.state["progress"] = min(0.99, (self.state["count"] - 1) / max(1, self.state["total"]))

        def run():
            try:
                res = fn(progress, lambda: self._cancel)
                with self.lock:
                    self.state.update(progress=1.0, step="Terminé", slug=res or self.state["slug"])
            except Exception as exc:
                traceback.print_exc()
                with self.lock:
                    self.state["error"] = "Annulé." if self._cancel else str(exc)
            finally:
                with self.lock:
                    self.state.update(running=False, done=True)

        threading.Thread(target=run, daemon=True).start()
        return jid

    def grow(self, n):
        """Des étapes de plus (esquisses refaites après contrôle) : la jauge ne dépasse pas la fin."""
        with self.lock:
            self.state["total"] = self.state.get("total", 1) + n

    def cancel(self):
        self._cancel = True

    def get(self):
        with self.lock:
            return dict(self.state)


# --------------------------------------------------------------------------- studio

class Studio:
    def __init__(self, library, comfy_root, comfy_url, fake=False):
        self.lib = nb_library.Library(library)
        self.comfy_root = Path(comfy_root) if comfy_root else None
        self.manager = nbc.ComfyManager(comfy_url, self.comfy_root or ".", log=print)
        self.jobs = Jobs()
        self.fake = fake
        if fake:
            import nb_engine_fake as eng
            writer = eng
        else:
            import nb_engine as eng
            import nb_writer as writer
        self.eng, self.writer = eng, writer

    # ---------------------------------------------------------------- état
    def client(self):
        if not self.fake:
            self.manager.ensure_up()
        return self.manager.client

    def status(self):
        if self.fake:
            return dict(comfy="prêt", comfy_root=True, missing=[], model="factice", writer="factice")
        import install_models
        up = self.manager.client.is_up()
        found = bool(self.comfy_root and (self.comfy_root / "ComfyUI" / "main.py").is_file())
        missing = [dict(name=n, gb=gb) for _f, n, _r, gb in install_models.missing(self.comfy_root)] if found else []
        return dict(comfy="prêt" if up else ("arrêté" if found else "introuvable"), comfy_root=found,
                    missing=missing, model="FLUX.2 klein", writer=self.writer.model())

    def install_models(self):
        import install_models

        def run(progress, cancel):
            for folder, name, repo, gb in install_models.missing(self.comfy_root):
                if cancel():
                    raise RuntimeError("annulé")
                progress(f"Téléchargement de {name} ({gb} Go)")
                dest = self.comfy_root / "ComfyUI" / "models" / folder / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                url = install_models.HF.format(repo, f"{install_models.PREFIX.get(repo, 'split_files/')}{folder}/{name}")
                install_models.download(url, dest, name)
        total = len(install_models.missing(self.comfy_root)) if self.comfy_root else 0
        if not total:
            raise RuntimeError("Rien à installer.")
        return self.jobs.start("install", run, total)

    # ------------------------------------------------------------ créatures
    def _unique_slug(self, name):
        base = nb_library.slugify(name)
        slug, n = base, 2
        while self.lib.exists(slug):
            slug, n = f"{base}_{n}", n + 1
        return slug

    def create(self, name, description, seed=None):
        name = (name or "").strip() or "Créature"
        description = (description or "").strip()
        if not description:
            raise ValueError("Décris ta créature.")
        if self.jobs.get()["running"]:
            raise RuntimeError("Une tâche est déjà en cours.")
        seed = int(seed) if seed not in (None, "") else int(time.time()) % 1000000
        rec = self.lib.new_record(name)
        rec.update(slug=self._unique_slug(name), description=description, seed=seed, lab=dict(LAB_DEFAULTS))
        self.lib.save(rec)
        slug = rec["slug"]

        def run(progress, cancel):  # 1re étape : des esquisses du design, l'utilisateur choisit la bonne (/continue)
            progress("Lecture de la description")
            brief = self._brief(slug)
            for n, (im, note) in enumerate(self._sketches(description, seed, brief, progress, cancel), 1):
                self.lib.add_pil(slug, "bas", im, f"esquisse {n}{note}")
            self.lib.set_active(slug, "bas", 0)
            return slug
        return self.jobs.start("sketch", run, SKETCHES + 2, slug), slug

    def _look(self, images):
        """Ce que le modèle de vision voit sur ces images ([] s'il n'y en a pas : on ne contrôle rien)."""
        if not images or not self.writer.vision_model():
            return []
        self._free_gpu()
        try:
            return self.writer.look(images)
        except Exception as exc:
            print("contrôle impossible :", exc)
            return []

    def _sketches(self, description, seed, brief, progress, cancel, rounds=3):
        """SKETCHES esquisses contrôlées : celles qui ratent (mauvais nombre de têtes, pattes en trop) sont refaites,
        2 fois au plus ; s'il en manque encore, les moins fausses complètent, avec ce qui ne va pas en note."""
        good, spare, k = [], [], 0
        checks = bool(nb_check.expected_heads(brief) or nb_check.legless(brief))
        for rnd in range(rounds):
            need = SKETCHES - len(good)
            if need <= 0:
                break
            if rnd:
                self.jobs.grow(need + 1)
            c = self.client()
            batch = []
            for _ in range(need):
                batch.append(self.eng.generate_design(c, description, seed + k, progress, cancel, brief=brief))
                k += 1
            seen = self._look(batch) if checks else []
            if not seen:
                return [(im, "") for im in (([im for _, im, _ in good]) + batch)][:SKETCHES]
            progress("Vérification des esquisses")
            for im, s in zip(batch, seen):
                ok, issues, gap = nb_check.verdict(s, brief)
                (good if ok else spare).append((gap, im, issues))
        spare.sort(key=lambda t: t[0])
        picks = [(im, " ✓") for _, im, _ in good[:SKETCHES]]
        picks += [(im, " ⚠ " + ", ".join(issues)) for _, im, issues in spare[:SKETCHES - len(picks)]]
        return picks

    def _check_profile(self, c, dirs, design, back, seed, brief, description, progress, cancel):
        """Créature sans pattes : un profil qui en a quand même est écarté, et refait (2 essais de plus) s'il le faut."""
        if not nb_check.legless(brief):
            return dirs
        cands = list(dirs["gauche"])
        seen = self._look(cands)
        if not seen:
            return dirs
        ok = [im for im, s in zip(cands, seen) if nb_check.verdict(s, brief, legs_only=True)[0]]
        if not ok:
            self.jobs.grow(3)
            c = self.client()
            extra = [self.eng.generate_view(c, [design, back], "gauche", seed + 2000 + i, progress, cancel, legs=False,
                                            brief=brief, description=description) for i in range(2)]
            progress("Vérification du profil")
            seen2 = self._look(extra)
            ok = [im for im, s in zip(extra, seen2) if nb_check.verdict(s, brief, legs_only=True)[0]]
            cands += extra
        order = ok + [im for im in cands if not any(im is o for o in ok)]  # les bons d'abord : le 1er devient actif
        dirs["gauche"] = order
        dirs["droite"] = [ImageOps.mirror(im) for im in order]
        return dirs

    def _brief(self, slug):
        """Ce que la plume a compris de la description (posture, pattes, anglais), calculé une fois par créature."""
        rec = self.lib.load(slug)
        if rec.get("brief", {}).get("posture") is not None and rec["brief"].get("description") == rec["description"]:
            return rec["brief"]
        try:
            self._free_gpu()
            brief = self.writer.brief(rec["description"], int(rec.get("seed", 1)))
        except Exception as exc:  # pas d'Ollama : posture devinée par mots-clés
            print("description non analysée :", exc)
            brief = self.eng.guess_brief(rec["description"])
        brief["description"] = rec["description"]
        rec = self.lib.load(slug)
        rec["brief"] = brief
        self.lib.save(rec)
        return brief

    def _rest(self, c, slug, seed, progress, cancel):
        """Dos, profils et marche à partir du design actif (tout est refait : les 4 directions restent cohérentes)."""
        rec = self.lib.load(slug)
        design = self._active(slug, "bas")
        brief = self._brief(slug)
        legs = self.eng.has_legs(rec["description"], brief)
        dirs = self.eng.generate_directions(c, design, seed, progress, cancel, legs=legs,
                                            brief=brief, description=rec["description"])
        if not legs:
            dirs = self._check_profile(c, dirs, design, dirs["haut"][0], seed, brief, rec["description"], progress, cancel)
        for d in ("haut", "gauche"):  # droite : le miroir de la gauche active, posé par _mirror_walk
            n = len(rec.get("views", {}).get(d, {}).get("files", []))
            for im in dirs[d]:
                self.lib.add_pil(slug, d, im, f"graine {seed}")
            self.lib.set_active(slug, d, n)
        for d in ("bas", "haut", "gauche"):
            self._walk(c, slug, d, progress, cancel)
        self._mirror_walk(slug)
        self.build_sprites(slug)
        progress("Écriture de la fiche")
        try:
            self.write_lore(slug)
        except Exception as exc:  # pas d'Ollama : la créature est faite quand même, la fiche s'écrira plus tard
            print("fiche non écrite :", exc)
        return slug

    def _free_gpu(self):
        """Le modèle d'image et celui de texte se partagent la carte : on demande à ComfyUI de libérer la mémoire."""
        if self.fake or not self.manager.client.is_up():
            return
        try:
            req = urllib.request.Request(self.manager.client.url + "/free", data=b'{"unload_models":true,"free_memory":true}',
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10).read()
        except Exception:
            pass

    def inspire(self, theme, seed=None):
        if not self.jobs.get()["running"]:
            self._free_gpu()
        return self.writer.idea(theme or "melange", seed)

    def write_lore(self, slug):
        rec = self.lib.load(slug)
        if rec is None:
            raise ValueError("Créature introuvable.")
        if not self.jobs.get()["running"] or self.jobs.get()["slug"] == slug:
            self._free_gpu()
        rec = self.lib.load(slug)
        rec["lore"] = self.writer.lore(rec["name"], rec.get("description", ""), int(time.time()) % 100000)
        rec["lore"]["combat"] = nb_stats.card(slug, rec["lore"], (rec.get("brief") or {}).get("posture", ""))
        self.lib.save(rec)
        self.build_attacks(slug)
        return self.creature(slug)

    def _rest_steps(self, slug):
        return 2 * self.eng.TRIES + 1  # la marche est calculée (pas d'image à générer) ; +1 : la fiche

    def finish(self, slug, index):
        """Le design choisi parmi les esquisses devient la créature : directions et marche."""
        rec = self.lib.load(slug)
        if rec is None:
            raise ValueError("Créature introuvable.")
        if self.jobs.get()["running"]:
            raise RuntimeError("Une tâche est déjà en cours.")
        self.lib.set_active(slug, "bas", int(index))
        seed = int(rec["seed"]) + int(index)
        return self.jobs.start("create", lambda progress, cancel: self._rest(self.client(), slug, seed, progress, cancel),
                               self._rest_steps(slug), slug)

    def _active(self, slug, key):
        rec = self.lib.load(slug)
        p = self.lib.active_path(rec, key)
        return Image.open(p).convert("RGBA") if p else None

    def _walk(self, c, slug, d, progress, cancel):
        rec = self.lib.load(slug)
        frames = self.eng.generate_walk(c, self._active(slug, d), d, rec["description"], rec["seed"], progress, cancel,
                                        brief=rec.get("brief"))
        self.lib.add_pil(slug, frame_key(d, "pas1"), frames[0], "marche")
        self.lib.add_pil(slug, frame_key(d, "pas2"), frames[2], "marche")

    def _mirror_walk(self, slug):
        """Droite = miroir de gauche (vue et pas), sauf si le Sprite Lab l'a désactivé."""
        rec = self.lib.load(slug)
        if not rec.get("lab", LAB_DEFAULTS).get("mirror", True):
            return
        for f in FRAMES:
            src = self._active(slug, frame_key("gauche", f))
            if src is None:
                continue
            key = frame_key("droite", f)
            _, _, note = self.lib.version_info(rec, key)
            if note == "miroir de gauche":  # le miroir se réécrit, il ne s'empile pas en versions
                ImageOps.mirror(src).save(self.lib.active_path(rec, key))
            else:
                self.lib.add_pil(slug, key, ImageOps.mirror(src), "miroir de gauche")

    def redo(self, slug, d):
        """Nouvelle version d'une direction (et de sa marche)."""
        rec = self.lib.load(slug)
        if rec is None or d not in DIRS:
            raise ValueError("Créature ou direction inconnue.")

        def run(progress, cancel):
            brief = self._brief(slug)
            legs = self.eng.has_legs(rec["description"], brief)
            c = self.client()
            seed = int(time.time()) % 1000000
            if d == "bas":  # nouveau design : tout le reste suit, sinon dos et profil montrent l'ancienne créature
                im = self.eng.generate_design(c, rec["description"], seed, progress, cancel, brief=brief)
                self.lib.add_pil(slug, "bas", im, f"graine {seed}")
                self.lib.set_active(slug, "bas", 10 ** 6)
                return self._rest(c, slug, seed, progress, cancel)
            else:
                src = "gauche" if d == "droite" else d
                refs = [self._active(slug, "bas")] + ([self._active(slug, "haut")] if src == "gauche" else [])
                im = self.eng.generate_view(c, refs, src, seed, progress, cancel, legs=legs, brief=brief,
                                            description=rec["description"])
                if d == "droite":
                    im = ImageOps.mirror(im)
            self.lib.add_pil(slug, d, im, f"graine {seed}")
            if d == "droite":
                frames = self.eng.generate_walk(c, ImageOps.mirror(im), "gauche", rec["description"], seed, progress, cancel, brief=brief)
                frames = [ImageOps.mirror(f) for f in frames]
            else:
                frames = self.eng.generate_walk(c, im, d, rec["description"], seed, progress, cancel, brief=brief)
            self.lib.add_pil(slug, frame_key(d, "pas1"), frames[0], "marche")
            self.lib.add_pil(slug, frame_key(d, "pas2"), frames[2], "marche")
            if d == "gauche":
                self._mirror_walk(slug)
            self.build_sprites(slug)
            return slug
        total = 1 + (self._rest_steps(slug) if d == "bas" else 0)
        return self.jobs.start("redo", run, total, slug)

    def edit(self, slug, key, instruction, zone=None, index=None):
        """Retouche d'une vue (bas, haut, gauche) : zone = [x, y, rayon] en fractions, ou None pour toute la créature.
        index : une esquisse précise (avant le choix du design) ; sinon la version active. La retouche devient une
        nouvelle version : rien n'est perdu."""
        rec = self.lib.load(slug)
        if rec is None or key not in ("bas", "haut", "gauche"):
            raise ValueError("Créature ou vue inconnue.")
        instruction = (instruction or "").strip()
        if not instruction:
            raise ValueError("Écris ce qu'il faut changer.")
        if self.jobs.get()["running"]:
            raise RuntimeError("Une tâche est déjà en cours.")
        if zone is not None:
            zone = [float(v) for v in zone][:3]
            if len(zone) != 3 or not all(0 <= v <= 1 for v in zone):
                raise ValueError("Zone invalide.")
        files = rec.get("views", {}).get(key, {}).get("files", [])
        src = self.lib.dir(slug) / files[int(index)] if index is not None and 0 <= int(index) < len(files) \
            else self.lib.active_path(rec, key)
        if src is None or not Path(src).is_file():
            raise ValueError("Pas d'image à retoucher.")
        pending = not rec.get("views", {}).get("haut")

        def run(progress, cancel):
            c = self.client()
            im = self.eng.generate_edit(c, Image.open(src).convert("RGBA"), instruction, int(time.time()) % 1000000,
                                        zone, progress, cancel)
            self.lib.add_pil(slug, key, im, "retouche : " + instruction[:40])
            if pending:  # une esquisse de plus parmi lesquelles choisir
                return slug
            self.lib.set_active(slug, key, 10 ** 6)
            self._walk(c, slug, key, progress, cancel)
            if key == "gauche":
                self._mirror_walk(slug)
            self.build_sprites(slug)
            return slug
        return self.jobs.start("edit", run, 1, slug)

    def choose(self, slug, key, delta=None, index=None):
        """Change la version active d'une vue (direction ou pas) puis refait les sprites."""
        if delta is not None:
            self.lib.cycle(slug, key, int(delta))
        else:
            self.lib.set_active(slug, key, int(index))
        if key.startswith("gauche"):
            self._mirror_walk(slug)
        self.build_sprites(slug)
        return self.creature(slug)

    def creature(self, slug):
        rec = self.lib.load(slug)
        if rec is None:
            raise ValueError("Créature introuvable.")
        views = {}
        for d in DIRS:
            for f in FRAMES:
                k = frame_key(d, f)
                i, n, _ = self.lib.version_info(rec, k)
                p = self.lib.active_path(rec, k)
                views[k] = dict(version=i, versions=n, file=str(p.relative_to(self.lib.dir(slug))).replace("\\", "/") if p else None)
        sd = self.lib.dir(slug) / "sprites"
        sprites = {f"{d}_{f}": f"sprites/{d}_{f}.png" for d in DIRS for f in FRAMES if (sd / f"{d}_{f}.png").is_file()}
        return dict(slug=slug, name=rec["name"], description=rec.get("description", ""), seed=rec.get("seed"),
                    lab=rec.get("lab", dict(LAB_DEFAULTS)), views=views, sprites=sprites,
                    palette=rec.get("sprite_palette", []), updated=rec.get("updated", 0),
                    sheet="sprites/sheet.png" if (sd / "sheet.png").is_file() else None,
                    designs=rec.get("views", {}).get("bas", {}).get("files", []), lore=rec.get("lore"), brief=rec.get("brief"),
                    design_notes=rec.get("views", {}).get("bas", {}).get("notes", []),
                    attack_fx=rec.get("attack_fx", {}), timing=list(nb_attack.TIMING),
                    pending=not rec.get("views", {}).get("haut"))  # esquisses pas encore choisies

    def library(self):
        out = []
        for rec in self.lib.list():
            if "seed" not in rec:  # anciennes créatures SDXL (autre format) : ignorées
                continue
            sd = self.lib.dir(rec["slug"]) / "sprites"
            nv = len(rec.get("views", {}).get("bas", {}).get("files", []))
            out.append(dict(slug=rec["slug"], name=rec["name"], updated=rec.get("updated", 0), versions=nv,
                            thumb="sprites/bas_repos.png" if (sd / "bas_repos.png").is_file()
                            else (rec.get("views", {}).get("bas", {}).get("files") or [None])[0]))  # esquisse à choisir
        return out

    def delete(self, slug):
        """Mise à la corbeille de la bibliothèque (récupérable à la main), pas d'effacement."""
        src = self.lib.dir(slug)
        if not src.is_dir():
            raise ValueError("Créature introuvable.")
        trash = self.lib.root / "corbeille"
        trash.mkdir(exist_ok=True)
        shutil.move(str(src), str(trash / f"{slug}_{int(time.time())}"))
        return dict(ok=True)

    # ------------------------------------------------------------- sprite lab
    def set_lab(self, slug, opts):
        rec = self.lib.load(slug)
        lab = dict(LAB_DEFAULTS)
        lab.update(rec.get("lab", {}))
        for k in LAB_DEFAULTS:
            if k in opts:
                lab[k] = opts[k]
        lab["colors"] = max(2, min(64, int(lab["colors"])))
        rec["lab"] = lab
        self.lib.save(rec)
        if "mirror" in opts and lab["mirror"]:
            self._mirror_walk(slug)
        return self.build_sprites(slug)

    def build_sprites(self, slug):
        """12 images 64x64 (palette commune, même échelle, pieds alignés) + planche, retouches à la main conservées."""
        rec = self.lib.load(slug)
        lab = dict(LAB_DEFAULTS)
        lab.update(rec.get("lab", {}))
        items = []
        for d in DIRS:
            row = {f: self._active(slug, frame_key(d, f)) for f in FRAMES}
            if row["repos"] is None:
                continue
            for f in FRAMES:
                if row[f] is not None:
                    im = row[f] if f == "repos" else sp.match_colors(_same_height(row[f], row["repos"]), row["repos"])
                    items.append((f"{d}_{f}", im))  # les pas reprennent les couleurs exactes de la pose de repos
        if not items:
            return self.creature(slug)
        opts = dict(width=CELL, height=CELL, colors=int(lab["colors"]), outline=bool(lab["outline"]),
                    outline_color=lab["outline_color"], align="Bas", margin=1, bg_remove=False)
        sprites = sp.run_batch(items, opts, master_key="bas_repos", lock_palette=bool(lab["lock_palette"]))
        sd = self.lib.sprites_dir(slug)
        for k, im in sprites:
            im.save(sd / f"{k}.png")
        for k, _ in sprites:  # les retouches pixel du Sprite Lab passent par-dessus
            e = sd / "edits" / f"{k}.png"
            if e.is_file():
                shutil.copyfile(e, sd / f"{k}.png")
        rec["sprite_palette"] = sp.extract_palette(Image.open(sd / "bas_repos.png").convert("RGBA"), int(lab["colors"]))
        self.lib.save(rec)
        self._sheet(slug)
        self.build_attacks(slug)
        return self.creature(slug)

    def build_attacks(self, slug):
        """Les 2 attaques de la fiche, animées dans les 4 directions : corps (pixels du sprite) + calque d'effet."""
        rec = self.lib.load(slug)
        moves = ((rec.get("lore") or {}).get("combat") or {}).get("attaques") or []
        sd = self.lib.sprites_dir(slug)
        if not moves or not (sd / "bas_repos.png").is_file():
            return
        legs = self.eng.has_legs(rec.get("description", ""), rec.get("brief"))
        fx = {}
        for n, move in enumerate(moves, 1):
            body_sheet = Image.new("RGBA", (CELL * nb_attack.FRAMES, CELL * len(DIRS)))
            fx_sheet = Image.new("RGBA", (CELL * nb_attack.FRAMES, CELL * len(DIRS)))
            fx[str(n)] = {}
            for row, d in enumerate(DIRS):
                rest = sd / f"{d}_repos.png"
                if not rest.is_file():
                    continue
                frames = nb_attack.attack(Image.open(rest).convert("RGBA"), d, move["genre"], move["element"], legs)
                fx[str(n)][d] = []
                for i, f in enumerate(frames):
                    f["body"].save(sd / f"attaque{n}_{d}_{i}.png")
                    body_sheet.paste(f["body"], (i * CELL, row * CELL))
                    if f["effect"] is not None:
                        f["effect"].save(sd / f"effet{n}_{d}_{i}.png")
                        fx_sheet.paste(f["effect"], (i * CELL, row * CELL))
                    else:
                        (sd / f"effet{n}_{d}_{i}.png").unlink(missing_ok=True)
                    fx[str(n)][d].append(dict(offset=list(f["offset"]), effect=f["effect"] is not None))
            body_sheet.save(sd / f"attaque{n}.png")
            fx_sheet.save(sd / f"effet{n}.png")
        rec = self.lib.load(slug)
        rec["attack_fx"] = fx
        self.lib.save(rec)

    def save_frame(self, slug, key, png_b64):
        """Retouche pixel d'une image (64x64) : gardée dans sprites/edits et appliquée à chaque reconstruction."""
        if key not in {f"{d}_{f}" for d in DIRS for f in FRAMES}:
            raise ValueError("Image inconnue.")
        im = Image.open(io.BytesIO(base64.b64decode(png_b64.split(",")[-1]))).convert("RGBA")
        if im.size != (CELL, CELL):
            raise ValueError("L'image doit faire 64x64.")
        sd = self.lib.sprites_dir(slug)
        (sd / "edits").mkdir(exist_ok=True)
        im.save(sd / "edits" / f"{key}.png")
        im.save(sd / f"{key}.png")
        self._sheet(slug)
        self.build_attacks(slug)  # les attaques partent des sprites de repos retouchés
        return self.creature(slug)

    def reset_edits(self, slug):
        shutil.rmtree(self.lib.sprites_dir(slug) / "edits", ignore_errors=True)
        return self.build_sprites(slug)

    def _sheet(self, slug):
        sd = self.lib.sprites_dir(slug)
        sheet = Image.new("RGBA", (CELL * len(FRAMES), CELL * len(DIRS)), (0, 0, 0, 0))
        for r, d in enumerate(DIRS):
            for c, f in enumerate(FRAMES):
                p = sd / f"{d}_{f}.png"
                if p.is_file():
                    sheet.paste(Image.open(p).convert("RGBA"), (c * CELL, r * CELL))
        sheet.save(sd / "sheet.png")
        return sheet

    def export(self, slug, dest=None):
        rec = self.lib.load(slug)
        sheet = self._sheet(slug)
        out = Path(dest) if dest else self.exports_dir() / rec["slug"]
        out.mkdir(parents=True, exist_ok=True)
        base = rec["slug"]
        sheet.save(out / f"{base}.png")
        meta = dict(
            name=rec["name"], image=f"{base}.png", frame_width=CELL, frame_height=CELL,
            columns=len(FRAMES), rows=len(DIRS), anchor=[CELL // 2, CELL - 2], fps=8,
            animation=["pas1", "repos", "pas2", "repos"],
            directions={d: dict(row=r, frames={f: dict(x=c * CELL, y=r * CELL) for c, f in enumerate(FRAMES)})
                        for r, d in enumerate(DIRS)},
            description=rec.get("description", ""), seed=rec.get("seed"), fiche=rec.get("lore"),
            portrait="portrait.png", attaques=[],
        )
        sd = self.lib.sprites_dir(slug)
        moves = ((rec.get("lore") or {}).get("combat") or {}).get("attaques") or []
        for n, move in enumerate(moves, 1):  # 2 planches par attaque : le corps, et l'effet à poser par-dessus
            fx = rec.get("attack_fx", {}).get(str(n))
            if not fx or not (sd / f"attaque{n}.png").is_file():
                continue
            shutil.copyfile(sd / f"attaque{n}.png", out / f"{base}_attaque{n}.png")
            shutil.copyfile(sd / f"effet{n}.png", out / f"{base}_effet{n}.png")
            meta["attaques"].append(dict(
                move, image=f"{base}_attaque{n}.png", effet_image=f"{base}_effet{n}.png", timing_ms=list(nb_attack.TIMING),
                directions={d: dict(row=r, frames=[dict(x=i * CELL, y=r * CELL, effet=f["effect"],
                                                        effet_decalage=f["offset"]) for i, f in enumerate(fx[d])])
                            for r, d in enumerate(DIRS) if d in fx}))
        design = self._active(slug, "bas")
        if design is not None:  # le design en grand (pour une carte de bestiaire)
            box = design.getbbox()
            (design.crop(box) if box else design).save(out / "portrait.png")
        (out / f"{base}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        return dict(folder=str(out), png=str(out / f"{base}.png"), json=str(out / f"{base}.json"))

    def exports_dir(self):
        d = self.lib.root / "Exports"
        d.mkdir(exist_ok=True)
        return d

    def shutdown(self):
        """Fermeture du plugin : arrête le ComfyUI que ce service a lancé (pas celui de l'utilisateur), puis quitte."""
        self.jobs.cancel()
        self.manager.stop_if_started()
        threading.Timer(0.3, lambda: os._exit(0)).start()
        return dict(ok=True)

    def file(self, slug, rel):
        """Chemin d'un fichier de la créature, sans sortir de son dossier."""
        base = self.lib.dir(slug).resolve()
        p = (base / rel).resolve()
        if base not in p.parents or not p.is_file():
            raise ValueError("Fichier introuvable.")
        return p


def _same_height(im, ref):
    """Un pas généré peut sortir un peu plus grand ou plus petit que la pose de repos : on le ramène à sa taille."""
    a, b = im.getbbox(), ref.getbbox()
    if not a or not b or im is ref:
        return im
    ha, hb = a[3] - a[1], b[3] - b[1]
    if abs(ha - hb) / hb < 0.04:
        return im
    k = hb / ha
    crop = im.crop(a)
    crop = crop.resize((max(1, round(crop.width * k)), hb), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", ref.size, (0, 0, 0, 0))
    out.paste(crop, ((ref.width - crop.width) // 2, b[3] - hb), crop)
    return out


# --------------------------------------------------------------------------- HTTP

def make_handler(studio, token):
    routes_get = {
        "/status": lambda q: studio.status(),
        "/job": lambda q: studio.jobs.get(),
        "/library": lambda q: studio.library(),
        "/creature": lambda q: studio.creature(q["slug"]),
        "/exports": lambda q: dict(folder=str(studio.exports_dir())),
    }
    routes_post = {
        "/create": lambda b: dict(zip(("job", "slug"), studio.create(b.get("name"), b.get("description"), b.get("seed")))),
        "/cancel": lambda b: studio.jobs.cancel() or dict(ok=True),
        "/redo": lambda b: dict(job=studio.redo(b["slug"], b["dir"])),
        "/continue": lambda b: dict(job=studio.finish(b["slug"], b["index"])),
        "/edit": lambda b: dict(job=studio.edit(b["slug"], b["key"], b.get("instruction"), b.get("zone"), b.get("index"))),
        "/inspire": lambda b: studio.inspire(b.get("theme"), b.get("seed")),
        "/lore": lambda b: studio.write_lore(b["slug"]),
        "/choose": lambda b: studio.choose(b["slug"], b["key"], b.get("delta"), b.get("index")),
        "/lab": lambda b: studio.set_lab(b["slug"], b.get("opts", {})),
        "/rebuild": lambda b: studio.build_sprites(b["slug"]),
        "/frame": lambda b: studio.save_frame(b["slug"], b["key"], b["png"]),
        "/reset-edits": lambda b: studio.reset_edits(b["slug"]),
        "/export": lambda b: studio.export(b["slug"], b.get("dest")),
        "/delete": lambda b: studio.delete(b["slug"]),
        "/install-models": lambda b: dict(job=studio.install_models()),
        "/start-comfy": lambda b: (studio.client(), studio.status())[1],
        "/shutdown": lambda b: studio.shutdown(),
    }

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _route(self, table, arg):
            if self.headers.get("X-NB-Token") != token:
                return self._send(403, dict(error="jeton invalide"))
            path = self.path.split("?")[0]
            try:
                if path == "/file" and table is routes_get:
                    p = studio.file(arg["slug"], arg["path"])
                    return self._send(200, p.read_bytes(), "image/png")
                fn = table.get(path)
                if fn is None:
                    return self._send(404, dict(error="route inconnue"))
                return self._send(200, fn(arg))
            except (ValueError, KeyError, RuntimeError, nbc.ComfyError) as exc:
                return self._send(400, dict(error=str(exc)))
            except Exception as exc:
                traceback.print_exc()
                return self._send(500, dict(error=str(exc)))

        def do_GET(self):
            from urllib.parse import parse_qs, urlparse
            q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            self._route(routes_get, q)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._send(400, dict(error="JSON invalide"))
            self._route(routes_post, body)

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--library", default=str(Path.home() / "Documents" / "NeoBestiary Studio"))
    ap.add_argument("--comfy-root", default=r"C:\AI\ComfyUI\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable")
    ap.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    ap.add_argument("--fake", action="store_true")
    a = ap.parse_args()
    studio = Studio(a.library, a.comfy_root, a.comfy_url, fake=a.fake)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(studio, a.token))
    print("NB_READY", srv.server_address[1], flush=True)
    try:
        srv.serve_forever()
    finally:
        studio.manager.stop_if_started()


if __name__ == "__main__":
    main()
