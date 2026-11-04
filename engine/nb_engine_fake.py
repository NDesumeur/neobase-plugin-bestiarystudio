# -*- coding: utf-8 -*-
"""Moteur factice (mêmes fonctions que nb_engine, sans GPU) : sert aux tests du serveur et de l'interface."""
import time

from PIL import Image, ImageDraw, ImageOps

TRIES = 2
COLORS = {"bas": (200, 60, 60), "haut": (60, 60, 200), "gauche": (60, 180, 60)}


def guess_brief(description):
    return dict(posture="flotte" if "flotte" in description else "quatre_pattes", pattes=0 if "flotte" in description else 4,
                en="", profil="")


LEGLESS = {"flotte", "rampe", "nage", "glisse", "roule"}


def motion(description, brief=None):
    return None


def said_posture(description):
    return "rampe" if "rampante" in description else ""


def has_legs(description, brief=None):
    if brief:
        return brief.get("pattes", 0) > 0
    return "sans pattes" not in description and "juste" not in description


def _blob(color, seed, lift=0, size=256):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = 70 + seed % 20
    d.ellipse((128 - r, 140 - r - lift, 128 + r, 140 + r - lift), fill=color + (255,), outline=(10, 10, 20, 255), width=6)
    d.ellipse((150, 100 - lift, 175, 125 - lift), fill=(255, 255, 255, 255))
    return im


def generate_design(client, description, seed, progress=lambda m: None, cancel=lambda: False, brief=None):
    progress("Esquisse du design")
    time.sleep(.05)  # une vraie tâche dure : le test « deux tâches en même temps » a le temps de la voir tourner
    return _blob(COLORS["bas"], seed)


def generate_view(client, refs, direction, seed, progress=lambda m: None, cancel=lambda: False, legs=False,
                  brief=None, description=""):
    progress(direction)
    return _blob(COLORS[direction], seed)


def generate_directions(client, design, seed, progress=lambda m: None, cancel=lambda: False, tries=TRIES, legs=False,
                        brief=None, description=""):
    out = {"bas": [design]}
    for d in ("haut", "gauche"):
        out[d] = []
        for i in range(tries):
            progress(f"{d} ({i + 1}/{tries})")
            out[d].append(_blob(COLORS[d], seed + i))
    out["droite"] = [ImageOps.mirror(im) for im in out["gauche"]]
    return out


def generate_edit(client, image, instruction, seed, zone=None, progress=lambda m: None, cancel=lambda: False):
    progress("Retouche")
    out = image.copy()
    ImageDraw.Draw(out).rectangle((10, 10, 40, 40), fill=(250, 200, 0, 255))
    return out


def generate_walk(client, view, direction, description, seed, progress=lambda m: None, cancel=lambda: False, brief=None):
    if has_legs(description, brief):
        progress(f"Marche {direction} : pas 1")
        progress(f"Marche {direction} : pas 2")
    up = Image.new("RGBA", view.size, (0, 0, 0, 0))
    up.paste(view, (0, -8), view)
    return [up, view.copy(), up.copy()]


# plume factice (mêmes fonctions que nb_writer)
def model():
    return "factice"


THEMES = {"melange": None, "animaux": None, "monstres": None}


def idea(theme="melange", seed=None):
    return dict(name="Crapaud test", description="un crapaud violet à quatre pattes avec trois yeux rouges", theme=theme)


def brief(description, seed=1):
    if "trois têtes" in description:  # le test du contrôle : 1 esquisse ratée, puis un profil avec pattes refusé
        LOOKS[:] = [dict(heads=1, legs=0)] + [dict(heads=3, legs=0)] * 3 + [dict(heads=3, legs=2)] * (TRIES + 1)             + [dict(heads=3, legs=0)]
        return dict(posture="flotte", pattes=0, en="a floating test creature", profil="a round body",
                    anatomie=["3 heads: side by side"])
    return dict(posture="quatre_pattes", pattes=4, en="a test creature", profil="a round body")


def generate_portrait(client, design, move, seed, progress=lambda m: None, cancel=lambda: False, brief=None,
                      description=""):
    progress("Portrait de combat")
    return _blob((220, 120, 40), seed, size=512)


def generate_fusion(client, designs, description, seed, progress=lambda m: None, cancel=lambda: False, brief=None):
    progress("Esquisse de l'hybride")
    return _blob((150, 60, 200), seed)


def fuse(a, b, seed=None):
    return dict(name=a["name"][:3] + b["name"][-3:], description=f"hybride de {a['description']} et {b['description']}")


LOOKS = []  # réponses imposées par le test (sinon : tout est bon)


def vision_model():
    return "factice"


MATCHES = []  # notes imposées par le test


def match(images, text, keep_alive=0):
    return [MATCHES.pop(0) if MATCHES else dict(score=7, missing=[]) for _ in images]


def generate_illustration(client, design, seed, progress=lambda m: None, cancel=lambda: False, brief=None, description=""):
    progress("Image du bestiaire")
    out = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse((100, 80, 420, 470), fill=(90 + seed % 100, 160, 90, 255))
    return out


def look(images, keep_alive=0):
    return [LOOKS.pop(0) if LOOKS else {"heads": 1, "eyes": 2, "legs": 4} for _ in images]


def lore(name, description, seed=1):
    return dict(type="poison", espece="la créature Test", taille="1 m", poids="10 kg", habitat="Les marais.",
                description=description, histoire=f"On raconte que {name} existe.", menace=3, prestige=PRESTIGE[0],
                attaques=[dict(nom="Morsure", genre="morsure", element="poison", description="Elle mord."),
                          dict(nom="Fouet", genre="fouet", element="poison", description="Elle fouette."),
                          dict(nom="Soin", genre="soin", element="plante", description="Elle se soigne."),
                          dict(nom="Crachat", genre="projectile", element="poison", description="Elle crache.")])


PRESTIGE = [50]  # imposé par le test
