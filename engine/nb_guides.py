# -*- coding: utf-8 -*-
"""Silhouettes-guides par plan corporel et par vue.

Principe repris du générateur d'origine : SDXL ignore souvent « side view » ou « front view ». Démarrer
l'échantillonneur depuis une silhouette grise fixe la caméra et l'orientation ; un fort denoise laisse le
modèle redessiner tout le reste. Chaque guide porte des indices de vue : yeux seulement de face, un seul œil de
profil, rien sur le visage de dos, dos plus sombre, devant plus clair.
"""
from PIL import Image, ImageDraw, ImageOps

PLANS = {
    "quadruped": "Quadrupède (taureau, loup…)",
    "biped": "Bipède (humanoïde, golem…)",
    "multileg": "Multi-pattes (araignée, crabe…)",
    "serpent": "Serpent / long (ver, poisson…)",
    "blob": "Flottant / rond (méduse, fantôme…)",
    "free": "Forme libre (aucune silhouette, le texte décide)",
}
PLAN_AUTO = "Auto (selon la description)"

LIGHT, MID, DARK, DEEP = (176, 174, 172), (138, 136, 134), (92, 90, 92), (52, 50, 54)

BIPED_CREATURES = {"humain", "homme", "femme", "squelette", "demon", "golem", "minotaure", "singe", "gorille",
                   "gargouille", "crane"}
MULTI_CREATURES = {"araignee", "scorpion", "crabe", "homard", "insecte", "mouche", "fourmi", "guepe",
                   "scarabee", "mante"}
LONG_CREATURES = {"serpent", "ver", "poisson", "requin", "baleine", "hydre"}
# pieuvre / calmar : un manteau rond et des tentacules, pas des pattes d'araignée
BLOB_CREATURES = {"meduse", "fantome", "limace", "escargot", "pieuvre", "calmar"}


HEAD_KINDS = {
    "taureau": "horned", "minotaure": "horned", "belier": "horned", "bouc": "horned", "cerf": "horned",
    "dragon": "horned", "demon": "horned", "gargouille": "horned",
    "loup": "eared", "chat": "eared", "renard": "eared", "chien": "eared", "rat": "eared", "chauve-souris": "eared",
    "lion": "eared", "tigre": "eared", "ours": "eared", "sanglier": "eared", "cheval": "eared",
    "aigle": "beaked", "hibou": "beaked", "corbeau": "beaked", "oiseau": "beaked", "coq": "beaked",
}
# (plan, vue) -> (cx, cy, rayon, orientation) de la tête ; orientation : 0 = face, -1 = tournée à gauche
HEAD_ANCHORS = {
    ("quadruped", "face"): (0.50, 0.29, 0.115, 0), ("quadruped", "dos"): (0.50, 0.29, 0.115, 0),
    ("quadruped", "gauche"): (0.24, 0.40, 0.095, -1), ("quadruped", "trois_quarts"): (0.34, 0.38, 0.105, -0.5),
    ("biped", "face"): (0.50, 0.16, 0.09, 0), ("biped", "dos"): (0.50, 0.16, 0.09, 0),
    ("biped", "gauche"): (0.50, 0.16, 0.08, -1), ("biped", "trois_quarts"): (0.49, 0.16, 0.085, -0.5),
    ("multileg", "face"): (0.50, 0.28, 0.15, 0), ("multileg", "dos"): (0.50, 0.28, 0.15, 0),
    ("multileg", "gauche"): (0.26, 0.44, 0.14, -1), ("multileg", "trois_quarts"): (0.32, 0.38, 0.14, -0.5),
    ("serpent", "face"): (0.50, 0.20, 0.10, 0), ("serpent", "dos"): (0.50, 0.20, 0.10, 0),
    ("serpent", "gauche"): (0.20, 0.46, 0.10, -1), ("serpent", "trois_quarts"): (0.28, 0.38, 0.10, -0.5),
}


def head_region(plan, view, mode="single", k=1.9):
    """Zone de la tête (fractions de l'image) pour le prompt par zones. mode='sheet' : case de droite d'une toile 2:1."""
    v = "gauche" if view == "droite" else view
    anchor = HEAD_ANCHORS.get((plan, v))
    if not anchor:
        return None
    cx, cy, r, _turn = anchor
    if view == "droite":
        cx = 1.0 - cx
    x0, x1 = max(0.0, cx - k * r), min(1.0, cx + k * r)
    y0, y1 = max(0.0, cy - 2.1 * r), min(1.0, cy + 1.3 * r)
    rect = dict(x=x0, y=y0, w=x1 - x0, h=y1 - y0)
    if mode == "sheet":
        rect = dict(x=0.5 + rect["x"] * 0.5, y=rect["y"], w=rect["w"] * 0.5, h=rect["h"])
    return rect


def body_region(plan, view, mode="single"):
    """Zone du corps : tout ce qui est sous la tête."""
    head = head_region(plan, view, "single")
    top = (head["y"] + head["h"] * 0.55) if head else 0.3
    rect = dict(x=0.0, y=top, w=1.0, h=1.0 - top)
    if mode == "sheet":
        rect = dict(x=0.5, y=rect["y"], w=0.5, h=rect["h"])
    return rect


def tint_guide(guide, palette_hex):
    """Recolore la silhouette grise avec les tons du design maître (le fond reste blanc)."""
    from nb_sprite import apply_palette
    mask = guide.convert("L").point(lambda p: 0 if p > 250 else 255)
    rgba = guide.convert("RGBA")
    rgba.putalpha(mask)
    tinted = apply_palette(rgba, palette_hex, "Par luminosité (recolorer)")
    out = Image.new("RGB", guide.size, (255, 255, 255))
    out.paste(tinted.convert("RGB"), mask=mask)
    return out


def head_kind_for(spec):
    return HEAD_KINDS.get(spec.head_creature, "plain")


def plan_for(spec):
    """Plan corporel déduit de la fiche anatomique (créature du corps, nombre de pattes)."""
    legs = spec.counts.get("legs", 0)
    body = spec.body_creature or spec.head_creature
    # sujet non reconnu (« un grand œil », « un nuage vivant ») ou corps interdit : imposer une silhouette de
    # quadrupède dessinait un corps à tout ; sans guide, seul le texte décide de la forme
    if getattr(spec, "only", None) or "body" in getattr(spec, "forbidden", ()) or (not body and not legs):
        return "free"
    if legs >= 6 or body in MULTI_CREATURES:
        return "multileg"
    if body in LONG_CREATURES:
        return "serpent"
    if body in BLOB_CREATURES:
        return "blob"
    if body in BIPED_CREATURES:
        return "biped"
    return "quadruped"


# ------------------------------------------------------------------ primitives

class _P:
    def __init__(self, size):
        self.S = size
        self.img = Image.new("RGB", (size, size), (255, 255, 255))
        self.d = ImageDraw.Draw(self.img)

    def p(self, x, y):
        return x * self.S, y * self.S

    def ell(self, cx, cy, rx, ry, fill):
        S = self.S
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=fill)

    def rect(self, x0, y0, x1, y1, fill, r=0.012):
        S = self.S
        self.d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S, fill=fill)

    def poly(self, pts, fill):
        self.d.polygon([self.p(x, y) for x, y in pts], fill=fill)

    def line(self, pts, w, fill):
        S = self.S
        pp = [self.p(x, y) for x, y in pts]
        self.d.line(pp, fill=fill, width=max(2, int(w * S)), joint="curve")
        r = w * S / 2
        for x, y in pp:
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def dot(self, x, y, r, fill=DEEP):
        self.ell(x, y, r, r, fill)


def _body_tone(view):
    return {"face": MID, "dos": DARK, "trois_quarts": MID, "gauche": MID}[view]


# ------------------------------------------------------------------ plans

def _quadruped(g, v):
    c = _body_tone(v)
    if v in ("face", "dos"):
        for x in (0.33, 0.67):
            g.rect(x - 0.03, 0.60, x + 0.03, 0.88, DARK)
        g.ell(0.5, 0.54, 0.20, 0.15, c)
        for x in (0.40, 0.60):
            g.rect(x - 0.035, 0.62, x + 0.035, 0.90, c)
        g.rect(0.44, 0.32, 0.56, 0.48, c)
        g.ell(0.5, 0.29, 0.11, 0.12, c if v == "face" else DARK)
        if v == "face":
            g.ell(0.385, 0.20, 0.035, 0.045, LIGHT)
            g.ell(0.615, 0.20, 0.035, 0.045, LIGHT)
            g.ell(0.5, 0.35, 0.06, 0.045, LIGHT)
            g.dot(0.46, 0.27, 0.014)
            g.dot(0.54, 0.27, 0.014)
        else:
            g.line([(0.5, 0.40), (0.5, 0.60)], 0.012, DEEP)
            g.line([(0.5, 0.60), (0.5, 0.74)], 0.02, DEEP)
    elif v == "gauche":
        for x in (0.36, 0.66):
            g.rect(x - 0.025, 0.60, x + 0.025, 0.89, DARK)
        g.ell(0.52, 0.53, 0.26, 0.12, c)
        for x in (0.30, 0.72):
            g.rect(x - 0.03, 0.60, x + 0.03, 0.90, c)
        g.poly([(0.28, 0.46), (0.36, 0.40), (0.34, 0.56)], c)
        g.ell(0.24, 0.40, 0.09, 0.075, LIGHT)
        g.ell(0.15, 0.425, 0.055, 0.04, LIGHT)
        g.ell(0.28, 0.33, 0.025, 0.04, c)
        g.dot(0.205, 0.385, 0.012)
        g.line([(0.77, 0.50), (0.85, 0.56), (0.84, 0.68)], 0.015, DEEP)
    else:  # trois_quarts (tourné vers la gauche, vers la caméra)
        for x in (0.40, 0.64):
            g.rect(x - 0.03, 0.60, x + 0.03, 0.88, DARK)
        g.ell(0.54, 0.54, 0.21, 0.13, c)
        for x in (0.36, 0.60):
            g.rect(x - 0.035, 0.60, x + 0.035, 0.90, c)
        g.poly([(0.36, 0.46), (0.44, 0.40), (0.42, 0.56)], c)
        g.ell(0.34, 0.38, 0.10, 0.095, LIGHT)
        g.ell(0.285, 0.42, 0.05, 0.04, LIGHT)
        g.ell(0.40, 0.30, 0.025, 0.04, c)
        g.ell(0.28, 0.31, 0.025, 0.04, c)
        g.dot(0.31, 0.355, 0.012)
        g.dot(0.37, 0.355, 0.01)
        g.line([(0.74, 0.50), (0.80, 0.58)], 0.015, DEEP)


def _biped(g, v):
    c = _body_tone(v)
    if v in ("face", "dos"):
        g.rect(0.43, 0.56, 0.49, 0.90, DARK if v == "dos" else c)
        g.rect(0.51, 0.56, 0.57, 0.90, DARK if v == "dos" else c)
        g.poly([(0.38, 0.28), (0.62, 0.28), (0.58, 0.60), (0.42, 0.60)], c)
        g.rect(0.31, 0.29, 0.37, 0.58, DARK)
        g.rect(0.63, 0.29, 0.69, 0.58, DARK)
        g.rect(0.46, 0.22, 0.54, 0.30, c)
        g.ell(0.5, 0.16, 0.085, 0.095, c if v == "face" else DARK)
        if v == "face":
            g.dot(0.47, 0.15, 0.011)
            g.dot(0.53, 0.15, 0.011)
            g.line([(0.47, 0.20), (0.53, 0.20)], 0.006, DEEP)
        else:
            g.line([(0.5, 0.30), (0.5, 0.58)], 0.01, DEEP)
    elif v == "gauche":
        g.rect(0.43, 0.56, 0.50, 0.89, DARK)
        g.rect(0.35, 0.86, 0.46, 0.90, DARK)
        g.rect(0.48, 0.56, 0.55, 0.88, c)
        g.rect(0.40, 0.86, 0.52, 0.90, c)
        g.poly([(0.44, 0.28), (0.56, 0.28), (0.57, 0.60), (0.43, 0.60)], c)
        g.rect(0.47, 0.31, 0.53, 0.56, LIGHT)
        g.rect(0.47, 0.22, 0.53, 0.30, c)
        g.ell(0.50, 0.16, 0.075, 0.09, LIGHT)
        g.poly([(0.43, 0.16), (0.38, 0.19), (0.44, 0.20)], LIGHT)
        g.dot(0.46, 0.145, 0.011)
    else:
        g.rect(0.43, 0.56, 0.49, 0.89, DARK)
        g.rect(0.50, 0.56, 0.56, 0.90, c)
        g.poly([(0.40, 0.28), (0.60, 0.28), (0.57, 0.60), (0.43, 0.60)], c)
        g.rect(0.34, 0.29, 0.40, 0.56, DARK)
        g.rect(0.58, 0.30, 0.64, 0.57, LIGHT)
        g.rect(0.46, 0.22, 0.54, 0.30, c)
        g.ell(0.49, 0.16, 0.08, 0.09, LIGHT)
        g.dot(0.46, 0.15, 0.011)
        g.dot(0.52, 0.15, 0.009)


def _multileg(g, v):
    """Araignée, crabe… : 4 pattes visibles de chaque côté de face/dos, céphalothorax qui relie tête et abdomen."""
    c = _body_tone(v)
    if v in ("face", "dos"):
        for s in (-1, 1):
            for i in range(4):
                knee = (0.5 + s * (0.30 + 0.035 * i), 0.30 + 0.085 * i)
                foot = (0.5 + s * (0.40 - 0.015 * i), 0.90)
                g.line([(0.5 + s * 0.12, 0.44 + 0.04 * i), knee, foot], 0.032, DARK)
        g.ell(0.5, 0.58, 0.17, 0.18, c)                  # abdomen
        g.ell(0.5, 0.44, 0.13, 0.10, c)                  # céphalothorax
    elif v == "gauche":
        for i in range(4):
            hip = (0.40 + 0.06 * i, 0.50)
            knee = (0.30 + 0.12 * i, 0.30)
            foot = (0.20 + 0.17 * i, 0.90)
            g.line([hip, knee, foot], 0.032, DARK if i % 2 else MID)
        g.ell(0.66, 0.50, 0.19, 0.15, c)                 # abdomen
        g.ell(0.42, 0.50, 0.14, 0.10, c)                 # céphalothorax, collé à la tête et à l'abdomen
    else:
        for i in range(4):
            hip = (0.42 + 0.06 * i, 0.50)
            knee = (0.32 + 0.11 * i, 0.28)
            foot = (0.22 + 0.16 * i, 0.90)
            g.line([hip, knee, foot], 0.032, DARK if i % 2 else MID)
        g.ell(0.62, 0.50, 0.18, 0.16, c)
        g.ell(0.44, 0.46, 0.14, 0.11, c)


def _serpent(g, v):
    c = _body_tone(v)
    if v in ("face", "dos"):
        pts = [(0.5, 0.28), (0.40, 0.45), (0.60, 0.62), (0.42, 0.78), (0.55, 0.88)]
        g.line(pts, 0.13, c)
        g.ell(0.5, 0.20, 0.09, 0.085, c if v == "face" else DARK)
        if v == "face":
            g.dot(0.465, 0.19, 0.012)
            g.dot(0.535, 0.19, 0.012)
        else:
            g.line([(0.5, 0.28), (0.40, 0.45), (0.60, 0.62), (0.42, 0.78)], 0.012, DEEP)
    elif v == "gauche":
        g.line([(0.28, 0.52), (0.42, 0.66), (0.58, 0.50), (0.72, 0.66), (0.86, 0.56)], 0.12, c)
        g.ell(0.20, 0.46, 0.09, 0.07, LIGHT)
        g.dot(0.18, 0.44, 0.011)
    else:
        g.line([(0.34, 0.46), (0.44, 0.64), (0.60, 0.50), (0.74, 0.66), (0.86, 0.58)], 0.12, c)
        g.ell(0.28, 0.38, 0.09, 0.075, LIGHT)
        g.dot(0.255, 0.36, 0.011)
        g.dot(0.31, 0.365, 0.009)


def _blob(g, v):
    c = _body_tone(v)
    if v in ("face", "dos"):
        g.ell(0.5, 0.56, 0.27, 0.30, c)
        if v == "face":
            g.dot(0.43, 0.48, 0.02)
            g.dot(0.57, 0.48, 0.02)
            g.line([(0.45, 0.60), (0.5, 0.63), (0.55, 0.60)], 0.01, DEEP)
        else:
            g.line([(0.5, 0.30), (0.5, 0.80)], 0.01, DEEP)
    elif v == "gauche":
        g.ell(0.52, 0.56, 0.23, 0.30, c)
        g.dot(0.34, 0.48, 0.02)
    else:
        g.ell(0.52, 0.56, 0.25, 0.30, c)
        g.dot(0.38, 0.48, 0.02)
        g.dot(0.46, 0.48, 0.016)


def _overlay_head(g, plan, view, kind):
    """Grosse tête explicite par-dessus la tête générique : cornes, oreilles ou bec, yeux seulement de face."""
    anchor = HEAD_ANCHORS.get((plan, view))
    if not anchor:
        return
    cx, cy, r, turn = anchor
    tone = DARK if view == "dos" else LIGHT
    face = view in ("face", "trois_quarts")
    g.ell(cx, cy, r, r * 1.02, tone)
    sx = 1 if turn == 0 else (-1)          # sens du museau
    if kind == "horned":
        for s in (-1, 1):
            if turn == -1 and s == 1:
                continue                    # de profil : une seule corne visible
            bx = cx + s * r * 0.75
            g.line([(bx, cy - r * 0.55), (bx + s * r * 0.75, cy - r * 1.05), (bx + s * r * 0.45, cy - r * 1.75)],
                   r * 0.38, (214, 210, 200))
    elif kind == "eared":
        for s in (-1, 1):
            if turn == -1 and s == 1:
                continue
            g.poly([(cx + s * r * 0.35, cy - r * 0.7), (cx + s * r * 1.0, cy - r * 1.5), (cx + s * r * 1.05, cy - r * 0.4)], tone)
    elif kind == "beaked":
        if turn == 0 and view != "dos":
            g.poly([(cx - r * 0.25, cy + r * 0.1), (cx + r * 0.25, cy + r * 0.1), (cx, cy + r * 0.75)], (206, 190, 120))
        elif turn != 0:
            g.poly([(cx + sx * r * 0.8, cy - r * 0.15), (cx + sx * r * 1.6, cy + r * 0.2), (cx + sx * r * 0.8, cy + r * 0.45)], (206, 190, 120))
    if view == "face":
        for s in (-1, 1):
            g.dot(cx + s * r * 0.42, cy - r * 0.1, r * 0.14)
        g.ell(cx, cy + r * 0.45, r * 0.5, r * 0.32, (150, 148, 146))
    elif view == "trois_quarts":
        g.dot(cx - r * 0.25, cy - r * 0.1, r * 0.15)
        g.dot(cx + r * 0.35, cy - r * 0.1, r * 0.11)
        g.ell(cx - r * 0.55, cy + r * 0.4, r * 0.45, r * 0.3, (150, 148, 146))
    elif view == "gauche":
        g.dot(cx - r * 0.35, cy - r * 0.15, r * 0.14)
        g.ell(cx - r * 0.75, cy + r * 0.25, r * 0.55, r * 0.36, (150, 148, 146))


_DRAW = {"quadruped": _quadruped, "biped": _biped, "multileg": _multileg, "serpent": _serpent, "blob": _blob}


def draw_guide(plan, view, size=768, head="plain"):
    """Silhouette-guide RGB (fond blanc). droite = miroir de gauche. head : plain | horned | eared | beaked.
    None pour la forme libre (génération sans guide)."""
    if plan == "free":
        return None
    plan = plan if plan in _DRAW else "quadruped"
    mirror = view == "droite"
    v = "gauche" if mirror else view
    g = _P(size)
    _DRAW[plan](g, v)
    _overlay_head(g, plan, v, head)
    return ImageOps.mirror(g.img) if mirror else g.img


def guide_sheet(plan, size=256, head="plain"):
    """Planche d'aperçu : les 5 vues du plan."""
    views = ["face", "trois_quarts", "dos", "gauche", "droite"]
    sheet = Image.new("RGB", (size * 5, size), (255, 255, 255))
    for i, v in enumerate(views):
        g = draw_guide(plan, v, size, head)
        if g is not None:
            sheet.paste(g, (i * size, 0))
    return sheet


def recolor_background(guide, bg_rgb):
    """Remplace le fond blanc du guide par la couleur de fond du design maître."""
    mask = guide.convert("L").point(lambda p: 0 if p > 250 else 255)
    out = Image.new("RGB", guide.size, tuple(bg_rgb))
    out.paste(guide, mask=mask)
    return out
