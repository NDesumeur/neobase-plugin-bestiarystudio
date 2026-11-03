# -*- coding: utf-8 -*-
"""Moteur factice (mêmes fonctions que nb_engine, sans GPU) : sert aux tests du serveur et de l'interface."""
from PIL import Image, ImageDraw, ImageOps

TRIES = 2
COLORS = {"bas": (200, 60, 60), "haut": (60, 60, 200), "gauche": (60, 180, 60)}


def has_legs(description):
    return "sans pattes" not in description and "juste" not in description


def _blob(color, seed, lift=0, size=256):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = 70 + seed % 20
    d.ellipse((128 - r, 140 - r - lift, 128 + r, 140 + r - lift), fill=color + (255,), outline=(10, 10, 20, 255), width=6)
    d.ellipse((150, 100 - lift, 175, 125 - lift), fill=(255, 255, 255, 255))
    return im


def generate_design(client, description, seed, progress=lambda m: None, cancel=lambda: False):
    progress("Esquisse du design")
    return _blob(COLORS["bas"], seed)


def generate_view(client, refs, direction, seed, progress=lambda m: None, cancel=lambda: False, legs=False):
    progress(direction)
    return _blob(COLORS[direction], seed)


def generate_directions(client, design, seed, progress=lambda m: None, cancel=lambda: False, tries=TRIES, legs=False):
    out = {"bas": [design]}
    for d in ("haut", "gauche"):
        out[d] = []
        for i in range(tries):
            progress(f"{d} ({i + 1}/{tries})")
            out[d].append(_blob(COLORS[d], seed + i))
    out["droite"] = [ImageOps.mirror(im) for im in out["gauche"]]
    return out


def generate_walk(client, view, direction, description, seed, progress=lambda m: None, cancel=lambda: False):
    if has_legs(description):
        progress(f"Marche {direction} : pas 1")
        progress(f"Marche {direction} : pas 2")
    up = Image.new("RGBA", view.size, (0, 0, 0, 0))
    up.paste(view, (0, -8), view)
    return [up, view.copy(), up.copy()]


# plume factice (mêmes fonctions que nb_writer)
def model():
    return "factice"


def idea(theme="melange", seed=None):
    return dict(name="Crapaud test", description="un crapaud violet à quatre pattes avec trois yeux rouges", theme=theme)


def lore(name, description, seed=1):
    return dict(type="poison", espece="la créature Test", taille="1 m", poids="10 kg", habitat="Les marais.",
                description=description, histoire=f"On raconte que {name} existe.")
