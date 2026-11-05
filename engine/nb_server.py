# -*- coding: utf-8 -*-
"""NeoBestiary Studio - service local (API JSON) pour le plugin NeoDex.

python nb_server.py --token T [--port 0] [--library DOSSIER] [--comfy-root DOSSIER] [--comfy-url URL] [--fake]
Écrit « NB_READY <port> » sur la sortie dès qu'il écoute. Seul 127.0.0.1 est servi et chaque requête doit
porter l'en-tête X-NB-Token (le plugin le connaît, les autres programmes de la machine non).
"""
import argparse
import base64
import io
import json
import os
import random
import shutil
import sys
import threading
import urllib.request
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nb_comfy as nbc  # noqa: E402
import nb_library  # noqa: E402
import nb_attack  # noqa: E402
import nb_check  # noqa: E402
import nb_anim  # noqa: E402
import nb_variant  # noqa: E402
import nb_stats  # noqa: E402
import nb_sprite as sp  # noqa: E402

DIRS = ("bas", "gauche", "droite", "haut")
FRAMES = ("pas1", "repos", "pas2", "mi1", "mi2")  # colonnes de la planche (repos reste en 2e colonne)
WALK = ("pas1", "mi1", "repos", "mi2", "pas2")  # l'ordre des images rendues par generate_walk
CYCLE = ["repos", "mi1", "pas1", "mi1", "repos", "mi2", "pas2", "mi2"]  # lecture de la marche
CELL = 64
PORTRAIT = 256  # portrait de combat, en pixels
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

    def restart(self, total, **info):
        """Nouvelle créature dans une même tâche (invocation en boucle) : la jauge repart de zéro."""
        with self.lock:
            self.state.update(total=total, count=0, progress=0.0, **info)

    def cancel(self):
        self._cancel = True

    def get(self):
        with self.lock:
            return dict(self.state)


# --------------------------------------------------------------------------- studio

SIG_PICK = {  # pour chaque visuel signature : (ligne, image) de la planche 10 x 3 pour élan, frappe, impact, retour ; les lignes 1 vont dans la direction
    "eclipse": [(0, 3), (0, 6), (2, 3), (2, 6)],
    "regard": [(0, 4), (1, 3), (2, 3), (2, 7)],
    "casque": [(0, 4), (1, 4), (2, 3), (2, 7)],
    "coquille": [(0, 2), (0, 4), (0, 6), (0, 8)],
}
SIG_STEP = {"bas": (0, 1), "haut": (0, -1), "gauche": (-1, 0), "droite": (1, 0)}


def _signature_sheet(folder, visuel):
    """La planche signature (10 images x 3 lignes de 128 px) du dossier signature/ de la créature, si elle en a une pour ce visuel."""
    if visuel not in SIG_PICK:
        return None
    for p in [folder, *list(Path(folder).parents)[:3]]:
        f = Path(p) / "signature" / f"{visuel}.png"
        if f.is_file():
            return Image.open(f).convert("RGBA")
    return None


def _signature_frame(sheet, move, d, i):
    """Une image d'effet 64 px tirée de la planche signature : tournée vers la direction pour ce qui voyage (ligne 1),
    poussée vers la cible pour la frappe et l'impact d'une attaque à distance."""
    row, col = SIG_PICK[move["visuel"]][i]
    im = sheet.crop((col * 128, row * 128, col * 128 + 128, row * 128 + 128))
    if row == 1:  # dessinée vers la droite
        im = {"gauche": ImageOps.mirror(im), "haut": im.rotate(90), "bas": im.rotate(-90)}.get(d, im)
    im = im.resize((CELL, CELL), Image.BOX)
    a = im.getchannel("A").point(lambda v: 255 if v > 110 else 0)  # contour net, comme le reste du pixel art
    im.putalpha(a)
    far = move.get("portee") == "distance" and i in (1, 2, 3)
    dx, dy = SIG_STEP[d]
    k = (18, 30, 30)[i - 1] if far else 0
    return im, (dx * k, dy * k + 2)


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
        self.upgrade_cards()
        self.upgrade_effects()
        self.upgrade_types()
        self.upgrade_float()

    def upgrade_float(self):
        """Une fois : les créatures qui flottent (sans ailes) perdent leurs images de marche tassées : la même image partout,
        le flottement est joué à l'affichage (arene.json : marche.flotte)."""
        cfg = self.lib.load_config({})
        if cfg.get("flotte"):
            return 0
        done = 0
        for rec in self.lib.list():
            if self.eng.floats(rec.get("description", ""), rec.get("brief")) and self._still_walk(rec["slug"]):
                self.build_sprites(rec["slug"])
                done += 1
        cfg["flotte"] = 1
        self.lib.save_config(cfg)
        if done:
            print(f"{done} créature(s) qui flottent : marche sans images de mouvement")
        return done

    def _still_walk(self, slug):
        """Chaque image de marche devient la vue de repos de sa direction. False : rien à changer."""
        changed = False
        for d in DIRS:
            view = self._active(slug, d)
            if view is None:
                continue
            for f in FRAMES:
                if f != "repos":
                    self.lib.add_pil(slug, frame_key(d, f), view.copy(), "flotte")
                    changed = True
        return changed

    def upgrade_types(self):
        """Une fois : les créatures d'avant les doubles types passent à une sur deux avec deux types."""
        cfg = self.lib.load_config({})
        if cfg.get("types", 1) >= 5:  # 5 : la table des types équilibrée
            return []
        done = self.retype() if cfg.get("types", 1) < 2 else []
        n = self.recard()
        cfg["types"] = 5
        self.lib.save_config(cfg)
        if done or n:
            print(f"{len(done)} créature(s) : un 2e type ; {n} fiche(s) : table des types")
        return done

    def recard(self):
        """Table des types façon Pokémon : chaque fiche reçoit ses multiplicateurs (×4 à ×0), même rareté ;
        « ombre et lumière » reste à NeoMe seul (les autres changent de 2e type)."""
        n = 0
        for r in self.lib.list():
            lore = r.get("lore") or {}
            t = nb_stats.split(lore.get("type"))
            if not t or not lore.get("combat"):
                continue
            if r.get("rarete_fixe") == nb_stats.UNIQUE:  # fiche écrite à la main : seulement les multiplicateurs
                lore["combat"].update(nb_stats.weaknesses(lore["type"]))
            else:
                if len(t) == 2 and nb_stats.OPPOSED.get(t[0]) == t[1]:
                    text = " ".join(str(lore.get(k, "")) for k in ("espece", "habitat", "description", "histoire"))
                    lore["type"] = t[0] + " et " + nb_stats.choose_type(r.get("description", ""), text, lore.get("types_proposes", []), {}, exclude=tuple(t))
                fixed = r.get("rarete_fixe")
                r["rarete_fixe"] = lore["combat"]["rarete"]  # même rareté qu'avant
                new = self._card(r)
                new["rarete_fixe"], r["rarete_fixe"] = bool(fixed), fixed
                lore["combat"] = new
            self.lib.save(r)
            if (self.lib.sprites_dir(r["slug"]) / "bas_repos.png").is_file():
                self.build_attacks(r["slug"])
            n += 1
        return n

    EFFECTS = 2  # 2 : les visuels signés (nb_attack_sig), un par attaque

    def upgrade_effects(self):
        """Les créatures d'avant les visuels signés : leurs effets d'attaque sont redessinés une fois (corps inchangés)."""
        cfg = self.lib.load_config({})
        if cfg.get("effets", 1) >= self.EFFECTS:
            return 0
        done = 0
        for rec in self.lib.list():
            if self._moves(rec) and (self.lib.sprites_dir(rec["slug"]) / "bas_repos.png").is_file():
                self.build_attacks(rec["slug"])
                done += 1
        cfg["effets"] = self.EFFECTS
        self.lib.save_config(cfg)
        if done:
            print(f"{done} créature(s) : effets d'attaque redessinés")
        return done

    def upgrade_cards(self):
        """Les fiches d'avant le catalogue des 204 attaques reçoivent leur mécanique (mêmes gestes, mêmes noms)."""
        done = 0
        for rec in self.lib.list():
            card = (rec.get("lore") or {}).get("combat")
            if not card or all("id" in a for a in card.get("attaques", [])):
                continue
            fixed = rec.get("rarete_fixe")
            rec["rarete_fixe"] = card["rarete"]  # même rareté, donc mêmes gestes : les animations restent valables
            new = self._card(rec)
            new["rarete_fixe"] = bool(fixed)
            rec["rarete_fixe"] = fixed
            rec["lore"]["combat"] = new
            self.lib.save(rec)
            if [a["genre"] for a in new["attaques"]] != [a.get("genre") for a in card.get("attaques", [])]:
                self.build_attacks(rec["slug"])  # un geste a changé (règles plus récentes) : ses animations aussi
            elif (self.lib.dir(rec["slug"]) / "arene.json").is_file():
                self._arena(rec["slug"])
            done += 1
        if done:
            print(f"{done} fiche(s) de combat mises à jour (catalogue des attaques)")
        return done

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

    def auto(self):
        """Invocation en boucle : une idée au hasard, ses esquisses, la meilleure (vérifiée) choisie toute seule, toute la
        créature, puis la suivante, jusqu'à /auto-stop (qui laisse finir la créature en cours) ou /cancel (tout de suite)."""
        if self.jobs.get()["running"]:
            raise RuntimeError("Une tâche est déjà en cours.")
        self.auto_stop = False

        def run(progress, cancel):
            made, fails, last = 0, 0, ""
            while not cancel() and not self.auto_stop:
                self.jobs.restart(SKETCHES + 3 + self._rest_steps(""), made=made, slug=last)
                try:
                    last = self._auto_one(progress, cancel, made + 1)
                    made, fails = made + 1, 0
                    self.jobs.restart(1, made=made, slug=last)
                except Exception as exc:
                    if cancel():
                        raise
                    fails += 1
                    print("invocation en boucle : créature ratée :", exc)
                    if fails >= 3:  # trois ratés de suite : quelque chose ne va pas (ComfyUI, Ollama), on s'arrête
                        raise RuntimeError(f"La boucle s'arrête après {made} créature(s) : {exc}")
            return last
        return self.jobs.start("auto", run, 1)

    def _auto_one(self, progress, cancel, n):
        progress(f"Créature {n} : idée")
        self._free_gpu()  # la plume a besoin de la carte
        idea = self.writer.idea(random.choice([t for t in self.writer.THEMES if t != "melange"] + ["melange"]))
        seed = random.randrange(10 ** 6)
        rec = self.lib.new_record(idea["name"] or "Créature")
        rec.update(slug=self._unique_slug(idea["name"] or "Créature"), description=idea["description"], seed=seed,
                   lab=dict(LAB_DEFAULTS), auto=True)
        self.lib.save(rec)
        slug = rec["slug"]
        self.jobs.restart(self.jobs.get()["total"], slug=slug)
        tag = lambda m: progress(f"Créature {n} · {m}")
        brief = self._brief(slug)
        picks = self._sketches(idea["description"], seed, brief, tag, cancel)
        for k, (im, note) in enumerate(picks, 1):
            self.lib.add_pil(slug, "bas", im, f"esquisse {k}{note}")
        best = next((i for i, (_, note) in enumerate(picks) if "✓" in note), 0)  # la première vérifiée
        self.lib.set_active(slug, "bas", best)
        return self._rest(self.client(), slug, seed + best, tag, cancel)

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

    def _sketches(self, description, seed, brief, progress, cancel, rounds=3, draw=None):
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
                batch.append(draw(c, seed + k) if draw else
                             self.eng.generate_design(c, description, seed + k, progress, cancel, brief=brief))
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
            said = self.eng.said_posture(rec["description"])  # « rampante » écrit en toutes lettres prime sur la plume
            if said and said != brief.get("posture") and not (said == "rampe" and brief.get("posture") == "nage"):
                brief["posture"] = said
                if said in self.eng.LEGLESS:
                    brief["pattes"] = 0
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
        self._portrait(self.client(), slug, progress, cancel)
        self._illustration(self.client(), slug, progress, cancel)
        return slug

    def _portrait(self, c, slug, progress, cancel):
        """Portrait de combat (version de plus de la vue « portrait »), puis sa version pixel 256x256."""
        rec = self.lib.load(slug)
        moves = self._moves(rec)
        move = moves[-1] if moves else dict(genre="charge", element=(nb_stats.split((rec.get("lore") or {}).get("type")) or [""])[0])
        brief, seed = rec.get("brief"), int(time.time()) % 1000000
        draw = lambda s_: self.eng.generate_portrait(c, self._active(slug, "bas"), move, s_, progress, cancel, brief=brief,
                                                     description=rec.get("description", ""))
        im, note = draw(seed), ""
        if nb_check.expected_heads(brief):  # en pleine attaque, une tête se cache parfois derrière les autres
            seen = self._look([im])
            if seen and not nb_check.verdict(seen[0], brief)[0]:
                self.jobs.grow(1)
                c = self.client()
                im2 = draw(seed + 1)
                seen2 = self._look([im2])
                ok2 = bool(seen2) and nb_check.verdict(seen2[0], brief)[0]
                im, note = (im2, " ✓") if ok2 else (im, " ⚠ " + ", ".join(nb_check.verdict(seen[0], brief)[1]))
            elif seen:
                note = " ✓"
        self.lib.add_pil(slug, "portrait", im, "portrait : " + move.get("nom", move["genre"]) + note)
        self.lib.set_active(slug, "portrait", 10 ** 6)
        self.build_sprites(slug)

    ILLUSTRATIONS = 3  # images du bestiaire tirées, la plus fidèle (modèle de vision) devient active

    def _illustration(self, c, slug, progress, cancel):
        """Image du bestiaire : plusieurs essais au calme, notés par le modèle de vision (bon nombre de têtes, pas de
        pattes en trop, ressemblance à la description) ; la meilleure devient active, les autres restent en versions."""
        rec = self.lib.load(slug)
        brief, desc, seed = rec.get("brief"), rec.get("description", ""), int(time.time()) % 1000000
        design = self._active(slug, "bas")
        ims = [self.eng.generate_illustration(c, design, seed + 101 * i, progress, cancel, brief=brief, description=desc)
               for i in range(self.ILLUSTRATIONS)]
        seen, scores = [], []
        if self.writer.vision_model():
            progress("Vérification de l'image du bestiaire")
            self._free_gpu()
            try:
                checks = bool(nb_check.expected_heads(brief) or nb_check.legless(brief))
                seen = self.writer.look(ims) if checks else []
                scores = self.writer.match(ims, ((brief or {}).get("en") or desc) + " " + "; ".join((brief or {}).get("anatomie", [])))
            except Exception as exc:
                print("image du bestiaire non vérifiée :", exc)
        rows = []
        for i, im in enumerate(ims):
            ok, issues, _ = nb_check.verdict(seen[i], brief) if i < len(seen) else (True, [], 0)
            sc = scores[i] if i < len(scores) else dict(score=0, missing=[])
            bad = issues + sc["missing"]
            note = (f" {sc['score']}/10" if scores else "") + (" ✓" if ok and not sc["missing"] else " ⚠ " + ", ".join(bad) if bad else "")
            rows.append((ok, sc["score"], im, "bestiaire" + note))
        rows.sort(key=lambda r: (r[0], r[1]))  # la meilleure en dernier : elle devient active
        for _, _, im, note in rows:
            self.lib.add_pil(slug, "illustration", im, note)
        self.lib.set_active(slug, "illustration", 10 ** 6)
        self._pixel_illustration(slug)

    def _pixel_illustration(self, slug):
        src = self._active(slug, "illustration")
        out = self.lib.sprites_dir(slug) / "illustration.png"
        if src is None:
            out.unlink(missing_ok=True)
            return
        opts = dict(width=PORTRAIT, height=PORTRAIT, colors=48, outline=True, outline_color="#140c1c", align="Centré",
                    margin=4, bg_remove=False)
        sp.run_batch([("illustration", src)], opts, master_key="illustration", lock_palette=False)[0][1].save(out)

    def illustration(self, slug):
        if self.lib.load(slug) is None:
            raise ValueError("Créature introuvable.")
        if self.jobs.get()["running"]:
            raise RuntimeError("Une tâche est déjà en cours.")
        return self.jobs.start("illustration", lambda progress, cancel: (
            self._illustration(self.client(), slug, progress, cancel), slug)[1], self.ILLUSTRATIONS + 1, slug)

    def portrait(self, slug):
        if self.lib.load(slug) is None:
            raise ValueError("Créature introuvable.")
        if self.jobs.get()["running"]:
            raise RuntimeError("Une tâche est déjà en cours.")
        return self.jobs.start("portrait", lambda progress, cancel: (self._portrait(self.client(), slug, progress, cancel),
                                                                     slug)[1], 1, slug)

    def _pixel_portrait(self, slug):
        """Le portrait actif en pixel art 256x256 (sprites/portrait.png), même nettoyage que les sprites."""
        src = self._active(slug, "portrait")
        out = self.lib.sprites_dir(slug) / "portrait.png"
        if src is None:
            out.unlink(missing_ok=True)
            return
        opts = dict(width=PORTRAIT, height=PORTRAIT, colors=48, outline=True, outline_color="#140c1c", align="Bas",
                    margin=4, bg_remove=False)
        sp.run_batch([("portrait", src)], opts, master_key="portrait", lock_palette=False)[0][1].save(out)

    # ------------------------------------------------------------- fusion
    def fuse(self, a, b, seed=None):
        """L'hybride de deux créatures finies : la plume l'invente, les esquisses partent des deux designs."""
        ra, rb = self.lib.load(a), self.lib.load(b)
        if ra is None or rb is None or a == b:
            raise ValueError("Choisis deux créatures différentes.")
        da, db = self._active(a, "bas"), self._active(b, "bas")
        if da is None or db is None or not ra.get("views", {}).get("haut") or not rb.get("views", {}).get("haut"):
            raise ValueError("Les deux créatures doivent être finies.")
        if self.jobs.get()["running"]:
            raise RuntimeError("Une tâche est déjà en cours.")
        seed = int(seed) if seed not in (None, "") else int(time.time()) % 1000000
        name = ra["name"][:max(2, len(ra["name"]) // 2)] + rb["name"][len(rb["name"]) // 2:]
        rec = self.lib.new_record(name)
        rec.update(slug=self._unique_slug(name), description=f"hybride de {ra['name']} et {rb['name']}", seed=seed,
                   lab=dict(LAB_DEFAULTS), parents=[a, b])
        self.lib.save(rec)
        slug = rec["slug"]

        def run(progress, cancel):
            progress("Invention de l'hybride")
            self._free_gpu()
            try:
                idea = self.writer.fuse(dict(name=ra["name"], description=ra.get("description", "")),
                                        dict(name=rb["name"], description=rb.get("description", "")), seed)
            except Exception as exc:  # pas d'Ollama : les deux descriptions côte à côte
                print("hybride non écrit :", exc)
                idea = dict(name=name, description=f"un hybride mêlant {ra.get('description', '')} et {rb.get('description', '')}")
            r = self.lib.load(slug)
            r.update(name=idea["name"] or name, description=idea["description"])
            self.lib.save(r)
            brief = self._brief(slug)
            draw = lambda c, sd: self.eng.generate_fusion(c, [da, db], idea["description"], sd, progress, cancel, brief=brief)
            for n, (im, note) in enumerate(self._sketches(idea["description"], seed, brief, progress, cancel, draw=draw), 1):
                self.lib.add_pil(slug, "bas", im, f"esquisse {n}{note}")
            self.lib.set_active(slug, "bas", 0)
            return slug
        return self.jobs.start("sketch", run, SKETCHES + 3, slug), slug

    def _pick_type(self, rec, lore):
        """Le type : ce que la plume propose, les mots de la description, et les types qui manquent au bestiaire.
        Une créature sur deux a deux types (« feu et vent ») : un double type quand le bestiaire en a moins que de simples."""
        counts, n = {}, [0, 0]
        for r in self.lib.list():
            t = nb_stats.split((r.get("lore") or {}).get("type"))
            if t and r.get("slug") != rec["slug"] and r.get("rarete_fixe") != nb_stats.UNIQUE:
                n[len(t) - 1] += 1
                for x in t:
                    counts[x] = counts.get(x, 0) + 1
        dual = n[1] < n[0] or (n[1] == n[0] and random.Random("types:" + rec["slug"]).random() < .5)
        text = " ".join(str(lore.get(k, "")) for k in ("espece", "habitat", "description", "histoire"))
        return nb_stats.choose_types(rec.get("description", ""), text, lore.get("types_proposes", [lore.get("type")]),
                                     counts, dual)

    def retype(self):
        """Créatures déjà faites : une sur deux reçoit un 2e type (sans réécrire la fiche), sa fiche de combat est recalculée."""
        recs = [r for r in self.lib.list() if nb_stats.split((r.get("lore") or {}).get("type")) and r.get("rarete_fixe") != nb_stats.UNIQUE]
        recs.sort(key=lambda r: random.Random("retype:" + r["slug"]).random())  # la moitié tirée au sort, toujours la même
        done = []
        for r in recs:
            lore = r["lore"]
            if r.get("parents") or len(nb_stats.split(lore["type"])) == 2:
                continue
            want = sum(len(nb_stats.split(x["lore"]["type"])) == 2 for x in recs) < len(recs) / 2
            if not want:
                break
            text = " ".join(str(lore.get(k, "")) for k in ("espece", "habitat", "description", "histoire"))
            first = nb_stats.split(lore["type"])[0]
            lore["type"] = first + " et " + nb_stats.choose_type(r.get("description", ""), text, lore.get("types_proposes", []), {}, exclude=(first,))
            fixed = r.get("rarete_fixe")
            r["rarete_fixe"] = lore["combat"]["rarete"] if lore.get("combat") else fixed  # même rareté qu'avant
            new = self._card(r)
            new["rarete_fixe"], r["rarete_fixe"] = bool(fixed), fixed
            r["lore"]["combat"] = new
            self.lib.save(r)
            self.build_attacks(r["slug"])
            done.append((r["slug"], lore["type"]))
        return done

    def _mix_lore(self, rec, lore):
        """Un hybride hérite : le type de l'un de ses parents, une attaque de chacun, la menace du plus fort."""
        parents = [self.lib.load(p) for p in rec.get("parents", [])]
        parents = [(p.get("lore") or {}) for p in parents if p and p.get("lore")]
        if len(parents) != 2:
            return lore
        rnd = random.Random(rec["slug"])
        firsts = list(dict.fromkeys(nb_stats.split(p.get("type"))[0] for p in parents if nb_stats.split(p.get("type"))))
        if len(firsts) == 2 and nb_stats.OPPOSED.get(firsts[0]) == firsts[1]:
            firsts = firsts[:1]  # « ombre et lumière » : NeoMe seul
        if firsts:  # le 1er type de chaque parent : deux parents de types différents -> un double type
            lore["type"] = " et ".join(firsts)
        moves = [(p.get("attaques") or []) for p in parents]
        mixed = moves[0][:2] + moves[1][-2:]  # les rapides de l'un, les fortes de l'autre
        if len(mixed) >= 2:
            lore["attaques"] = mixed
        try:
            lore["menace"] = max(int(p.get("menace", 3)) for p in parents)
        except (TypeError, ValueError):
            pass
        best = [p["prestige"] for p in parents if isinstance(p.get("prestige"), int)]
        if best and isinstance(lore.get("prestige"), int):
            lore["prestige"] = max(lore["prestige"], max(best))  # l'hybride impressionne au moins autant que ses parents
        return lore

    def _prestiges(self, but=None):
        """Le prestige des autres créatures du bestiaire (le classement fixe la rareté quand il y en a assez)."""
        return [(r.get("lore") or {}).get("prestige") for r in self.lib.list()
                if r.get("slug") != but and isinstance((r.get("lore") or {}).get("prestige"), int)]

    def _card(self, rec):
        if rec.get("rarete_fixe") == nb_stats.UNIQUE:
            return rec["lore"]["combat"]  # la créature unique garde sa fiche écrite à la main
        brief = rec.get("brief") or {}
        return nb_stats.card(rec["slug"], rec["lore"], brief.get("posture", ""), rec.get("rarete_fixe"),
                             self._prestiges(rec["slug"]), brief.get("anatomie", []))

    def set_rarity(self, slug, rarete=None):
        """Rareté choisie à la main (verrouillée), ou None : de nouveau calculée d'après le prestige."""
        rec = self.lib.load(slug)
        if rec is None or not (rec.get("lore") or {}).get("combat"):
            raise ValueError("Pas encore de fiche de combat.")
        if rec.get("rarete_fixe") == nb_stats.UNIQUE:
            raise ValueError("Cette créature est unique : sa rareté ne change pas.")
        if rarete not in (None, "", *nb_stats.RARITIES):
            raise ValueError("Rareté inconnue.")
        rec["rarete_fixe"] = rarete or None
        rec["lore"]["combat"] = self._card(rec)
        self.lib.save(rec)
        self.build_attacks(slug)
        return self.creature(slug)

    # ------------------------------------------------------------- équilibrage
    def balance(self):
        """Répartition des raretés, types et statistiques du bestiaire, et ce qui manque ou déborde."""
        rows, missing = [], 0
        for rec in self.lib.list():
            if "seed" not in rec or not rec.get("views", {}).get("haut"):
                continue
            card = (rec.get("lore") or {}).get("combat")
            if not card:
                missing += 1
                continue
            rows.append(dict(slug=rec["slug"], nom=rec["name"], type=rec["lore"].get("type"), rarete=card["rarete"],
                             total=sum(card["stats"].values()), stats=card["stats"], prestige=rec["lore"].get("prestige"),
                             fixe=bool(rec.get("rarete_fixe")), variantes=len(rec.get("variants", []))))
        n = len(rows)
        weights = sum(nb_stats.WEIGHTS)
        rare = [dict(nom=r, n=sum(x["rarete"] == r for x in rows), attendu=round(100 * w / weights))
                for r, w in zip(nb_stats.RARITIES, nb_stats.WEIGHTS)]
        types = sorted(({"type": t, "n": sum(t in nb_stats.split(x["type"]) for x in rows)} for t in nb_stats.CHART),
                       key=lambda t: -t["n"])
        avg = {s: round(sum(x["stats"][s] for x in rows) / n) if n else 0 for s in nb_stats.STATS}
        alerts = []
        if missing:
            alerts.append(f"{missing} créature{'s' if missing > 1 else ''} sans fiche de combat : ouvre-la et clique « Réécrire la fiche ».")
        if n >= 4:
            empty = [t["type"] for t in types if not t["n"]]
            if empty:
                alerts.append("Aucune créature " + ", ".join(nb_variant.label(t) for t in empty) + ".")
            top = types[0]
            if n >= 6 and top["n"] / n > .35:
                alerts.append(f"Beaucoup de créatures {nb_variant.label(top['type'])} ({top['n']} sur {n}).")
            for r in rare[2:]:
                if r["n"] >= 2 and 100 * r["n"] / n > 2 * r["attendu"]:
                    alerts.append(f"Trop de créatures {r['nom']}s : {r['n']} sur {n} (environ {r['attendu']} sur 100 attendues).")
            if rare[0]["n"] == 0:
                alerts.append("Aucune créature commune : un bestiaire a besoin de créatures ordinaires.")
        elif n:
            alerts.append("Encore trop peu de créatures pour juger l'équilibre (4 au moins).")
        # conseils : la rareté que le prestige mérite aujourd'hui, comparée au reste du bestiaire
        tips = []
        for x in rows:
            if x["fixe"] or not isinstance(x["prestige"], int):
                continue
            others = [y["prestige"] for y in rows if y is not x and isinstance(y["prestige"], int)]
            want = nb_stats.RARITIES[nb_stats.tier_of(x["prestige"], others)]
            if want != x["rarete"]:
                tips.append(dict(slug=x["slug"], nom=x["nom"], actuelle=x["rarete"], conseillee=want, prestige=x["prestige"]))
        old = sum(1 for x in rows if not isinstance(x["prestige"], int))
        if old:
            alerts.append(f"{old} fiche{'s' if old > 1 else ''} sans prestige (rareté tirée au sort) : « Réécrire la fiche » "
                          "la rend fidèle à la créature.")
        return dict(total=n, raretes=rare, types=types, moyennes=avg, creatures=rows, alertes=alerts, conseils=tips)

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
        if rec.get("rarete_fixe") == nb_stats.UNIQUE:
            raise ValueError("Cette créature est unique : sa fiche ne se réécrit pas.")
        lore = self.writer.lore(rec["name"], rec.get("description", ""), int(time.time()) % 100000)
        lore["type"] = self._pick_type(rec, lore)
        rec["lore"] = self._mix_lore(rec, lore)
        rec["lore"]["combat"] = self._card(rec)
        self.lib.save(rec)
        self.build_attacks(slug)
        return self.creature(slug)

    def _rest_steps(self, slug):
        # la marche est calculée (pas d'image à générer) ; +2 : la fiche et le portrait ; puis l'image du bestiaire
        return 2 * self.eng.TRIES + 2 + self.ILLUSTRATIONS + 1

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
        self._store_walk(slug, d, frames)

    def _store_walk(self, slug, d, frames):
        for f, im in zip(WALK, frames):
            if f != "repos":
                self.lib.add_pil(slug, frame_key(d, f), im, "marche")

    def _fill_walk(self, slug):
        """Créatures d'avant les demi-pas : les images manquantes de la marche sont calculées (sans le modèle d'image)."""
        rec = self.lib.load(slug)
        for d in ("bas", "haut", "gauche", "droite"):
            if self._active(slug, frame_key(d, "mi1")) is not None or self._active(slug, d) is None:
                continue
            if d == "droite" and rec.get("lab", LAB_DEFAULTS).get("mirror", True) and self._active(slug, "gauche") is not None:
                self._mirror_walk(slug)
                continue
            view = self._active(slug, d)
            src = ImageOps.mirror(view) if d == "droite" else view
            frames = self.eng.generate_walk(None, src, "gauche" if d == "droite" else d, rec.get("description", ""),
                                            rec.get("seed", 0), brief=rec.get("brief"))
            frames = [ImageOps.mirror(f) for f in frames] if d == "droite" else frames
            for f, im in zip(WALK, frames):
                if f in ("mi1", "mi2"):
                    self.lib.add_pil(slug, frame_key(d, f), im, "marche")

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
            self._store_walk(slug, d, frames)
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
        fix, rest = self.eng.orientation_fix(instruction, key) if zone is None else (None, instruction)

        def run(progress, cancel):
            seed = int(time.time()) % 1000000
            im, notes = Image.open(src).convert("RGBA"), []
            c = self.client() if fix == "regen" or rest else None
            if fix == "mirror":
                im = ImageOps.mirror(im)
            elif fix == "flip":
                im = ImageOps.flip(im)
            elif fix == "regen":  # la vue refaite dans la bonne orientation, d'après la créature elle-même
                brief = self._brief(slug)
                legs = self.eng.has_legs(rec["description"], brief)
                design = im if key == "bas" else self._active(slug, "bas")
                refs = {"bas": [im], "haut": [ImageOps.mirror(design)],
                        "gauche": [design] if legs or pending else [design, self._active(slug, "haut")]}[key]
                im = self.eng.generate_facing(c, key, refs, seed, progress, cancel, legs=legs, brief=brief,
                                              description=rec["description"])
            if fix:
                notes.append(self.eng.FIX_NOTE[key if fix == "regen" else fix])
            if rest:
                im = self.eng.generate_edit(c, im, rest, seed, zone, progress, cancel)
                notes.append("retouche : " + rest[:40])
            self.lib.add_pil(slug, key, im, " · ".join(notes))
            if pending:  # une esquisse de plus parmi lesquelles choisir
                return slug
            self.lib.set_active(slug, key, 10 ** 6)
            self._walk(c, slug, key, progress, cancel)
            if key == "gauche":
                self._mirror_walk(slug)
            self.build_sprites(slug)
            return slug
        return self.jobs.start("edit", run, 1, slug)

    CUTOUT_KEYS = ("bas", "haut", "gauche", "portrait", "illustration")

    def cutout(self, slug, key, mask_b64):
        """Détourage corrigé au pinceau : mask = PNG à la taille de l'image, rouge = à effacer, vert = à restaurer
        (les pixels d'origine sont gardés sous la transparence). Nouvelle version de la vue, la marche et les sprites suivent."""
        rec = self.lib.load(slug)
        if rec is None or key not in self.CUTOUT_KEYS:
            raise ValueError("Image inconnue.")
        if self.jobs.get()["running"]:
            raise RuntimeError("Une tâche est déjà en cours.")
        im = self._active(slug, key)
        if im is None:
            raise ValueError("Pas encore d'image à détourer.")
        m = Image.open(io.BytesIO(base64.b64decode(mask_b64.split(",")[-1]))).convert("RGB").resize(im.size, Image.Resampling.NEAREST)
        r, g, _ = m.split()
        a = ImageChops.subtract(im.getchannel("A"), r.point(lambda v: 255 if v > 128 else 0))
        im.putalpha(ImageChops.lighter(a, g.point(lambda v: 255 if v > 128 else 0)))
        if not im.getbbox():
            raise ValueError("Tout a été effacé.")
        self.lib.add_pil(slug, key, im, "détourage retouché")
        self.lib.set_active(slug, key, 10 ** 6)
        if key in DIRS and rec.get("views", {}).get("haut"):  # créature finie : la marche repart de la vue corrigée
            self._walk(None, slug, key, lambda m_: None, lambda: False)
            if key == "gauche":
                self._mirror_walk(slug)
        self.build_sprites(slug)
        return self.creature(slug)

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
                    anims={n: list(t) for n, t in nb_anim.ANIMS.items()}, variants=rec.get("variants", []),
                    portrait="sprites/portrait.png" if (sd / "portrait.png").is_file() else None,
                    portrait_version=self.lib.version_info(rec, "portrait")[:2], parents=rec.get("parents", []),
                    illustration="sprites/illustration.png" if (sd / "illustration.png").is_file() else None,
                    hd={k: str(p.relative_to(self.lib.dir(slug))).replace("\\", "/") for k in ("portrait", "illustration")
                        for p in [self.lib.active_path(rec, k)] if p},
                    illustration_version=self.lib.version_info(rec, "illustration")[:2],
                    illustration_note=self.lib.version_info(rec, "illustration")[2],
                    variant_choices=[dict(id=v, label=nb_variant.label(v)) for v in nb_variant.VARIANTS],
                    forms=self.forms(rec),
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
        """20 images 64x64 (palette commune, même échelle, pieds alignés) + planche, retouches à la main conservées."""
        self._fill_walk(slug)
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
        self._pixel_portrait(slug)
        self._pixel_illustration(slug)
        self.build_attacks(slug)
        return self.creature(slug)

    def _moves(self, rec):
        return ((rec.get("lore") or {}).get("combat") or {}).get("attaques") or []

    def _combat_anims(self, folder, moves, legs, move=None):
        """Dans folder (les 12 sprites de marche y sont) : les 2 attaques (corps + effet) et les animations
        attente / dégâts / K.O., une ligne par direction. Rend les décalages des effets {n: {direction: [...]}}."""
        fx = {}
        sheets = {name: Image.new("RGBA", (CELL * len(t), CELL * len(DIRS))) for name, t in nb_anim.ANIMS.items()}
        for row, d in enumerate(DIRS):
            rest = folder / f"{d}_repos.png"
            if rest.is_file():
                for name, frames in nb_anim.build(Image.open(rest).convert("RGBA"), d, move).items():
                    for i, im in enumerate(frames):
                        sheets[name].paste(im, (i * CELL, row * CELL))
        for name, sheet in sheets.items():
            sheet.save(folder / f"{name}.png")
        for n, move in enumerate(moves, 1):
            body_sheet = Image.new("RGBA", (CELL * nb_attack.FRAMES, CELL * len(DIRS)))
            fx_sheet = Image.new("RGBA", (CELL * nb_attack.FRAMES, CELL * len(DIRS)))
            fx[str(n)] = {}
            for row, d in enumerate(DIRS):
                rest = folder / f"{d}_repos.png"
                if not rest.is_file():
                    continue
                frames = nb_attack.attack(Image.open(rest).convert("RGBA"), d, move["genre"], move["element"], legs,
                                          move.get("visuel"))
                sig = _signature_sheet(folder, move.get("visuel"))
                if sig is not None:  # une attaque signature : ses effets viennent de sa grande planche (les mêmes que dans l'Arène)
                    for i, f in enumerate(frames):
                        f["effect"], f["offset"] = _signature_frame(sig, move, d, i)
                fx[str(n)][d] = []
                for i, f in enumerate(frames):
                    f["body"].save(folder / f"attaque{n}_{d}_{i}.png")
                    body_sheet.paste(f["body"], (i * CELL, row * CELL))
                    if f["effect"] is not None:
                        f["effect"].save(folder / f"effet{n}_{d}_{i}.png")
                        fx_sheet.paste(f["effect"], (i * CELL, row * CELL))
                    else:
                        (folder / f"effet{n}_{d}_{i}.png").unlink(missing_ok=True)
                    fx[str(n)][d].append(dict(offset=list(f["offset"]), effect=f["effect"] is not None))
            body_sheet.save(folder / f"attaque{n}.png")
            fx_sheet.save(folder / f"effet{n}.png")
        return fx

    def build_attacks(self, slug):
        """Attaques et animations de combat de la créature, puis de chacune de ses variantes de couleur."""
        rec = self.lib.load(slug)
        moves = self._moves(rec)
        sd = self.lib.sprites_dir(slug)
        if not (sd / "bas_repos.png").is_file():
            return
        legs = self.eng.has_legs(rec.get("description", ""), rec.get("brief"))
        move = self.eng.motion(rec.get("description", ""), rec.get("brief"))
        fx = self._combat_anims(sd, moves, legs, move)
        vfx = {vid: self._build_variant(rec, vid, legs, move) for vid in rec.get("variants", [])}
        rec = self.lib.load(slug)
        rec["attack_fx"], rec["variant_fx"] = fx, vfx
        self.lib.save(rec)
        self._arena(slug)

    def _build_variant(self, rec, vid, legs, move=None):
        """La variante : les sprites (et le portrait) repeints, puis ses propres attaques et animations."""
        sd = self.lib.sprites_dir(rec["slug"])
        vd = sd / "variantes" / vid
        vd.mkdir(parents=True, exist_ok=True)
        names = [f"{d}_{f}.png" for d in DIRS for f in FRAMES] + ["sheet.png", "portrait.png", "illustration.png"]
        srcs = {n: Image.open(sd / n).convert("RGBA") for n in names if (sd / n).is_file()}
        fn, cache = nb_variant.color_fn(vid, rec["slug"], nb_variant.colors_of(srcs.values())), {}
        for n, im in srcs.items():
            nb_variant.recolor(im, fn, cache).save(vd / n)
        card = ((rec.get("lore") or {}).get("combat"))
        moves = nb_variant.card(card, vid)["attaques"] if card else []
        return self._combat_anims(vd, moves, legs, move)

    def add_variant(self, slug, vid):
        rec = self.lib.load(slug)
        if rec is None or vid not in nb_variant.VARIANTS:
            raise ValueError("Variante inconnue.")
        if not (self.lib.sprites_dir(slug) / "bas_repos.png").is_file():
            raise ValueError("Finis d'abord la créature.")
        if vid not in rec.setdefault("variants", []):
            rec["variants"].append(vid)
            self.lib.save(rec)
        self.build_attacks(slug)
        return self.creature(slug)

    def remove_variant(self, slug, vid):
        rec = self.lib.load(slug)
        if rec is None:
            raise ValueError("Créature introuvable.")
        rec["variants"] = [v for v in rec.get("variants", []) if v != vid]
        rec.get("variant_fx", {}).pop(vid, None)
        self.lib.save(rec)
        shutil.rmtree(self.lib.sprites_dir(slug) / "variantes" / vid, ignore_errors=True)
        self._arena(slug)
        return self.creature(slug)

    def forms(self, rec):
        """La créature et ses variantes, telles qu'un jeu les voit : nom, fiche de combat, dossier des images."""
        card = (rec.get("lore") or {}).get("combat")
        if not card:
            return []
        out = [dict(id="base", nom=rec["name"], combat=card, dossier="sprites/", fx=rec.get("attack_fx", {}))]
        for vid in rec.get("variants", []):
            out.append(dict(id=vid, nom=f"{rec['name']} {nb_variant.label(vid)}", combat=nb_variant.card(card, vid),
                            dossier=f"sprites/variantes/{vid}/", fx=rec.get("variant_fx", {}).get(vid, {})))
        return out

    def _arena(self, slug):
        """arene.json : tout ce qu'il faut pour faire combattre la créature (lu par l'appli NeoBestiary Arène)."""
        rec = self.lib.load(slug)
        path = self.lib.dir(slug) / "arene.json"
        forms = self.forms(rec)
        if not forms:
            path.unlink(missing_ok=True)
            return
        lore = rec.get("lore") or {}
        sd = self.lib.sprites_dir(slug)
        meta = dict(
            format=1, slug=slug, nom=rec["name"], type=lore.get("type"), espece=lore.get("espece"),
            description=lore.get("description", ""), mis_a_jour=rec.get("updated", 0), case=CELL, directions=list(DIRS),
            marche=dict(image="sheet.png", images=list(FRAMES), ordre=CYCLE, ms=90,
                        **({"flotte": True} if self.eng.floats(rec.get("description", ""), rec.get("brief")) else {})),
            animations={n: dict(image=f"{n}.png", ms=list(t)) for n, t in nb_anim.ANIMS.items()},
            portrait=(sd / "portrait.png").is_file(), **({"numero": rec["numero"]} if "numero" in rec else {}),
            formes=[dict(id=f["id"], nom=f["nom"], dossier=f["dossier"], combat=f["combat"],
                         attaques=[dict(a, image=f"attaque{n}.png", effet=f"effet{n}.png", ms=list(nb_attack.TIMING),
                                        decalages={d: [dict(x=e["offset"][0], y=e["offset"][1], visible=e["effect"])
                                                       for e in fr] for d, fr in f["fx"].get(str(n), {}).items()})
                                   for n, a in enumerate(f["combat"]["attaques"], 1)])
                    for f in forms])
        path.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")

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
            columns=len(FRAMES), rows=len(DIRS), anchor=[CELL // 2, CELL - 2], fps=11,
            animation=CYCLE,
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
        meta["animations"] = {}
        for name, t in nb_anim.ANIMS.items():  # attente, dégâts, K.O. : 4 directions x 4 images
            if (sd / f"{name}.png").is_file():
                shutil.copyfile(sd / f"{name}.png", out / f"{base}_{name}.png")
                meta["animations"][name] = dict(image=f"{base}_{name}.png", timing_ms=list(t), rows=list(DIRS))
        meta["variantes"] = []
        for f in self.forms(rec)[1:]:  # chaque variante : ses planches dans variantes/<id>/, mêmes noms de fichiers
            vd, dst = self.lib.dir(slug) / f["dossier"], out / "variantes" / f["id"]
            dst.mkdir(parents=True, exist_ok=True)
            for n in ["sheet", "portrait", "illustration", *nb_anim.ANIMS] + [f"{k}{i}" for i in range(1, 5) for k in ("attaque", "effet")]:
                if (vd / f"{n}.png").is_file():
                    shutil.copyfile(vd / f"{n}.png", dst / f"{n}.png")
            meta["variantes"].append(dict(id=f["id"], nom=f["nom"], dossier=f"variantes/{f['id']}/", combat=f["combat"]))
        if (sd / "illustration.png").is_file():  # l'image du bestiaire (pixel 256) et sa version détaillée
            shutil.copyfile(sd / "illustration.png", out / "illustration.png")
            self._active(slug, "illustration").save(out / "illustration_hd.png")
            meta["illustration"], meta["illustration_hd"] = "illustration.png", "illustration_hd.png"
        design = self._active(slug, "bas")
        if (sd / "portrait.png").is_file():  # le portrait de combat, sinon le design en grand
            shutil.copyfile(sd / "portrait.png", out / "portrait.png")
        elif design is not None:
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
        "/balance": lambda q: studio.balance(),
        "/creature": lambda q: studio.creature(q["slug"]),
        "/exports": lambda q: dict(folder=str(studio.exports_dir())),
    }
    routes_post = {
        "/create": lambda b: dict(zip(("job", "slug"), studio.create(b.get("name"), b.get("description"), b.get("seed")))),
        "/cancel": lambda b: studio.jobs.cancel() or dict(ok=True),
        "/auto": lambda b: dict(job=studio.auto()),
        "/auto-stop": lambda b: setattr(studio, "auto_stop", True) or dict(ok=True),
        "/redo": lambda b: dict(job=studio.redo(b["slug"], b["dir"])),
        "/continue": lambda b: dict(job=studio.finish(b["slug"], b["index"])),
        "/rarity": lambda b: studio.set_rarity(b["slug"], b.get("rarete")),
        "/cutout": lambda b: studio.cutout(b["slug"], b["key"], b["mask"]),
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
        "/variant": lambda b: studio.add_variant(b["slug"], b["variant"]),
        "/portrait": lambda b: dict(job=studio.portrait(b["slug"])),
        "/illustration": lambda b: dict(job=studio.illustration(b["slug"])),
        "/fuse": lambda b: dict(zip(("job", "slug"), studio.fuse(b.get("a"), b.get("b"), b.get("seed")))),
        "/variant-remove": lambda b: studio.remove_variant(b["slug"], b["variant"]),
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
