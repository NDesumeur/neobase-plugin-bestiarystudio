# -*- coding: utf-8 -*-
"""Dessine à la main tous les sprites de l'interface (grilles de lettres -> PNG dans ui/).

python tools/draw_ui.py [--preview fichier.png]
Une lettre = un pixel. La palette est celle du grimoire : encres violettes, laiton, parchemin, lueur verte.
"""
import sys
from pathlib import Path

from PIL import Image

UI = Path(__file__).resolve().parent.parent / "ui"

PAL = {
    ".": None,
    "k": "#0d0a14", "K": "#1a1424", "d": "#2a1f38", "p": "#4a2f5c", "v": "#7a4f9a", "l": "#b98ee0",
    "P": "#ead7aa", "q": "#c9ae7c", "Q": "#8f7148",
    "B": "#f2c25b", "b": "#c48a2c", "n": "#7a4e1c",
    "g": "#7dffb0", "G": "#2fae6e", "h": "#16573a",
    "r": "#e0525c", "R": "#8a2633",
    "w": "#fff4dc",
    "s": "#241c30", "S": "#31263f", "t": "#3c3050",
    "e": "#7ad7f0", "E": "#2f7fa8",
    # sol de l'aperçu en jeu : herbe 1-5, terre 6-9
    "1": "#1d4a2c", "2": "#2b6a3a", "3": "#3d8b46", "4": "#5eae4e", "5": "#9fd86a",
    "6": "#563620", "7": "#76502f", "8": "#946840", "9": "#bb8c5a",
    # mur : joint, pierres (3 tons), mousse
    "m": "#120d19", "u": "#2b2238", "U": "#463a5a", "o": "#2f5a3a", "O": "#4c7e45",
}


def rgba(c):
    if c is None:
        return (0, 0, 0, 0)
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def grid(rows):
    w = len(rows[0])
    for i, r in enumerate(rows):
        assert len(r) == w, f"ligne {i} : {len(r)} au lieu de {w} -> {r!r}"
        assert all(ch in PAL for ch in r), f"lettre inconnue ligne {i} : {r!r}"
    return [list(r) for r in rows]


def outline(g, ink="k"):
    """Contour 1 px autour de tout ce qui est dessiné (les dessins d'icônes sont faits en aplats)."""
    h, w = len(g), len(g[0])
    out = [row[:] for row in g]
    for y in range(h):
        for x in range(w):
            if g[y][x] != ".":
                continue
            if any(0 <= y + dy < h and 0 <= x + dx < w and g[y + dy][x + dx] not in (".", ink)
                   for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))):
                out[y][x] = ink
    return out


def flip_h(g):
    return [row[::-1] for row in g]


def flip_v(g):
    return [row[:] for row in g[::-1]]


def recolor(g, m):
    return [[m.get(c, c) for c in row] for row in g]


def img(g):
    im = Image.new("RGBA", (len(g[0]), len(g)))
    im.putdata([rgba(PAL[c]) for row in g for c in row])
    return im


def stack(*gs, vertical=True):
    """Plusieurs états côte à côte (ou empilés) dans un seul PNG, pour un décalage CSS."""
    ims = [img(g) for g in gs]
    w = max(i.width for i in ims) if vertical else sum(i.width for i in ims)
    h = sum(i.height for i in ims) if vertical else max(i.height for i in ims)
    out = Image.new("RGBA", (w, h))
    o = 0
    for i in ims:
        out.paste(i, (0, o) if vertical else (o, 0))
        o += i.height if vertical else i.width
    return out


# ---------------------------------------------------------------- cadre sombre (9 tranches, coin 12 px)
PANEL_TL = grid([
    "..kkkkkkkkkk",
    ".kBBBBBBBBBB",
    "kBkkkkkkkkbb",
    "kBkBBBBBnkbb",
    "kBkBwgGBnknn",
    "kBkBggGBnkkk",
    "kBkBGGhBnkdd",
    "kBkBBBBBnkdK",
    "kBknnnnnnkdK",
    "kBkkkkkkkkdK",
    "kBbbnkdddddK",
    "kBbbnkdKKKKK",
])


def panel(tl, edge_top, edge_left, fill, size=32):
    """Assemble un cadre 9 tranches : coins dessinés, bords = profil répété, coins du bas = miroir assombri."""
    c = len(tl)
    g = [[fill] * size for _ in range(size)]
    bl = flip_v(tl)
    bl[c - 2] = ["k" if x == 1 else ("n" if ch == "B" else ch) for x, ch in enumerate(bl[c - 2])]
    bl = [[("K" if (ch == "d" and x > 6) else ch) for x, ch in enumerate(row)] for row in bl]
    corners = {(0, 0): tl, (0, 1): flip_h(tl), (1, 0): bl, (1, 1): flip_h(bl)}
    for (cy, cx), cg in corners.items():
        for y in range(c):
            for x in range(c):
                g[y if not cy else size - c + y][x if not cx else size - c + x] = cg[y][x]
    bottom = [("n" if ch == "B" else ("K" if ch == "d" else ch)) for ch in edge_top]
    for i in range(c, size - c):
        for d, ch in enumerate(edge_top):
            if ch != fill:
                g[d][i] = ch
                g[size - 1 - d][i] = bottom[d]
        for d, ch in enumerate(edge_left):
            if ch != fill:
                g[i][d] = ch
                g[i][size - 1 - d] = ch
    return g


# ---------------------------------------------------------------- parchemin (9 tranches, coin 8 px)
PARCH_TL = grid([
    "..kkkkkk",
    ".kQQqqqq",
    "kQqPPPPP",
    "kQPwPPPP",
    "kqPPPPPP",
    "kqPPPqPP",
    "kqPPPPPP",
    "kqPPPPPP",
])


def parchment(size=24):
    c = 8
    g = [["P"] * size for _ in range(size)]
    for (cy, cx) in ((0, 0), (0, 1), (1, 0), (1, 1)):
        cg = PARCH_TL
        if cx:
            cg = flip_h(cg)
        if cy:
            cg = recolor(flip_v(cg), {"q": "Q", "w": "P"})
        for y in range(c):
            for x in range(c):
                g[y if not cy else size - c + y][x if not cx else size - c + x] = cg[y][x]
    for i in range(c, size - c):
        for d, (t, b) in enumerate(zip("kqP", "kQq")):
            if t != "P":
                g[d][i] = t
                g[i][d] = t
                g[i][size - 1 - d] = t
            g[size - 1 - d][i] = b
    return g


# ---------------------------------------------------------------- boutons (16 x 16, coin 5 px) : repos / survol / appuyé
def button(hi, face, lo, spark="w"):
    """Bouton 16 x 16 : tranches haut 2, bas 4, côtés 2."""
    return grid([".kkkkkkkkkkkkkk.",
                 f"k{spark}{hi * 13}k"]
                + [f"k{hi}{face * 12}{lo}k"] * 10
                + [f"k{lo * 14}k",
                   ".kkkkkkkkkkkkkk.",
                   "..dddddddddddd..",
                   "................"])


def pressed(hi, face, lo):
    """Bouton enfoncé : 2 px plus bas, plus d'ombre portée, liseré sombre en haut. Tranches haut 4, bas 2."""
    return grid(["................",
                 "................",
                 ".kkkkkkkkkkkkkk.",
                 "kddddddddddddddk"]
                + [f"k{hi}{face * 12}{lo}k"] * 10
                + [f"k{lo * 14}k",
                   ".kkkkkkkkkkkkkk."])


BTN = {
    "btn": ("B", "b", "n"),          # laiton
    "btn_go": ("g", "G", "h"),       # lueur : l'action principale
    "btn_red": ("r", "R", "k"),      # danger
    "btn_dark": ("v", "p", "d"),     # secondaire
}

# ---------------------------------------------------------------- onglets (16 x 16, coin 6 px) : inactif / actif
TAB_OFF = grid([
    "................",
    "................",
    "...kkkkkkkkkk...",
    "..kvvvvvvvvvvk..",
    ".kvlpppppppppvk.",
    ".kvppppppppppvk.",
] + [".kvppppppppppvk."] * 8 + [
    ".kvppppppppppvk.",
    "kkkkkkkkkkkkkkkk",
])
TAB_ON = grid([
    "..kkkkkkkkkkkk..",
    ".kBBBBBBBBBBBBk.",
    "kBwbbbbbbbbbbbnk",
    "kBbkkkkkkkkkkbnk",
    "kBkKKKKKKKKKKknk",
    "kBkKKKKKKKKKKknk",
] + ["kBkKKKKKKKKKKknk"] * 8 + [
    "kBkKKKKKKKKKKknk",
    "kBkKKKKKKKKKKknk",
])

# ---------------------------------------------------------------- jauge « potion » (tube 24 x 12, coin 5) + liquide
BAR = grid([
    "..kkkkkkkkkkkkkkkkkkkk..",
    ".kBBBBBBBBBBBBBBBBBBBBk.",
    "kBbkkkkkkkkkkkkkkkkkkbnk",
    "kBkssssssssssssssssssknk",
    "kBkssssssssssssssssssknk",
    "kBkssssssssssssssssssknk",
    "kBkssssssssssssssssssknk",
    "kBkssssssssssssssssssknk",
    "kBkssssssssssssssssssknk",
    "kbnkkkkkkkkkkkkkkkkkknnk",
    ".knnnnnnnnnnnnnnnnnnnnk.",
    "..kkkkkkkkkkkkkkkkkkkk..",
])
LIQUID = grid([      # 8 px de large, se répète ; 2 images (décalage de bulles) côte à côte
    "wggggggg" + "gggwgggg",
    "gggggggg" + "gggggggg",
    "ggGggggg" + "gggggGgg",
    "gggggwgg" + "gwgggggg",
    "GGGGGGGG" + "GGGGGGGG",
    "hhhhhhhh" + "hhhhhhhh",
])

# ---------------------------------------------------------------- icônes 16 x 16
ICONS = {}

ICONS["creer"] = outline(grid([   # plume
    "................",
    "..............w.",
    "............wwl.",
    "...........wllv.",
    "..........wllvv.",
    ".........wllvv..",
    "........wllvvp..",
    ".......wllvvp...",
    "......wllvvp....",
    ".....wlvvvp.....",
    ".....lvvpp......",
    "....bnpp........",
    "...bBn..........",
    "..bBn...........",
    "..Bn............",
    "................",
]))

ICONS["directions"] = grid([      # boussole
    ".....kkkkkk.....",
    "...kkBBBBBBkk...",
    "..kBBbbbbbbbbk..",
    ".kBbbnnnnnnbbbk.",
    ".kBbnPPrrPPnbbk.",
    "kBbnPPPrrPPPnbbk",
    "kBbnPPrrrrPPnbbk",
    "kBbnPPrwwrPPnbbk",
    "kbbnPPKwwKPPnnnk",
    "kbbnPPKKKKPPnnnk",
    "kbbnPPPKKPPPnnnk",
    ".kbbnPPKKPPnnnk.",
    ".kbbnnnnnnnnnnk.",
    "..knnnnnnnnnnk..",
    "...kknnnnnnkk...",
    ".....kkkkkk.....",
])

ICONS["lab"] = grid([             # fiole
    "......kkkk......",
    ".....kbBBbk.....",
    ".....knnnnk.....",
    "......kwpk......",
    "......kwpk......",
    ".....kwlppk.....",
    ".....kwgGGk.....",
    "....kwgggGGk....",
    "....kggggGGk....",
    "...kwggggggGk...",
    "...kgggwgggGk...",
    "..kggggggggGGk..",
    "..kgggggwggGGk..",
    ".kGggggggggGGGk.",
    ".kGGGGGGGGGGGGk.",
    "..kkkkkkkkkkkk..",
])

ICONS["biblio"] = grid([          # grimoire
    ".kkkkkkkkkkkk...",
    "kpklllllllllkk..",
    "kpklvvvvvvvvkPk.",
    "kpklvvBBBBvvkPk.",
    "kpklvBvvvvBvkPk.",
    "kpklvBvgGvBvkPk.",
    "kpklvBvGhvBvkPk.",
    "kpklvBvvvvBvkPk.",
    "kpklvvBBBBvvkPk.",
    "kpklvvvvvvvvkPk.",
    "kpklvvvvvvvvkPk.",
    "kpkpppppppppkPk.",
    "kpkkkkkkkkkkkqk.",
    "kpPPPPPPPPPPPqk.",
    ".kqqqqqqqqqqqqk.",
    "..kkkkkkkkkkkkk.",
])

ICONS["play"] = grid([
    "................",
    "................",
    "....kk..........",
    "....kwkk........",
    "....kwggkk......",
    "....kwgggGkk....",
    "....kwggggGGkk..",
    "....kggggggGGGk.",
    "....kggggggGGGk.",
    "....kgggggGGkk..",
    "....kgggGGkk....",
    "....kgGGkk......",
    "....kGkk........",
    "....kk..........",
    "................",
    "................",
])

ICONS["pause"] = grid([
    "................",
    "................",
    "...kkkk..kkkk...",
] + ["...kBbk..kBbk..."] * 9 + [
    "...knnk..knnk...",
    "...kkkk..kkkk...",
    "................",
    "................",
])

ICONS["next"] = recolor(ICONS["play"], {"w": "B", "g": "b", "G": "n"})
ICONS["prev"] = flip_h(ICONS["next"])

ICONS["undo"] = outline(grid([
    "................",
    "................",
    "................",
    "....B...........",
    "...BB...........",
    "..BbbBBBBBB.....",
    ".Bbbbbbbbbbbb...",
    "..nbbnnnnnbbbn..",
    "...nn......nbbn.",
    "....n.......bbn.",
    "............bbn.",
    "...........bbn..",
    "......bbbbbbn...",
    "......nnnnnn....",
    "................",
    "................",
]))
ICONS["redo"] = flip_h(ICONS["undo"])


def diagonal(segments, x0=2, y0=13, width=3):
    """Objet en diagonale (bas-gauche -> haut-droite) : segments = [(longueur, couleurs de la coupe)]."""
    g = [["."] * 16 for _ in range(16)]
    a = 0
    for length, cols in segments:
        for _ in range(length):
            for j, ch in enumerate(cols):
                y, x = y0 - a - j + (width - len(cols)) // 2, x0 + a
                if 0 <= y < 16 and 0 <= x < 16 and ch != ".":
                    g[y][x] = ch
            a += 1
    return outline(g)


ICONS["crayon"] = diagonal([(1, "k"), (2, "qQ"), (7, "BbN".replace("N", "n")), (1, "wPq"), (2, "rrR")])
ICONS["gomme"] = diagonal([(4, "rrrR"), (1, "kkkk"), (4, "eeeE"), (1, "wwww")], x0=3, y0=13, width=4)
ICONS["pipette"] = diagonal([(1, "w"), (6, "wE"), (1, "BbN".replace("N", "n")), (3, "rrRR"), (1, "rR")])

ICONS["seau"] = outline(grid([
    "................",
    "................",
    "....qqqqqq......",
    "...q......q.....",
    "..q........q....",
    "..bBBBBBBBBn....",
    "..bwbbbbbbbn....",
    "..bBbbbbbbbne...",
    "..bBbbbbbbbneE..",
    "...bBbbbbbn.eE..",
    "...bBbbbbbn..E..",
    "...bBbbbbbn.....",
    "....bnnnnn......",
    "................",
    "...........ee...",
    "................",
]))

ICONS["exporter"] = outline(grid([   # parchemin roulé + flèche
    "................",
    "..........g.....",
    "..........gg....",
    ".......ggggGg...",
    ".......ggggGGg..",
    "..........GG....",
    "..qqqqqq..G.....",
    ".qPPPPPPq.......",
    ".qPwPPPPPq......",
    "..qPPPPPPq......",
    "..qPQQQQPq......",
    "..qPPPPPPq......",
    "..qPQQQPPq......",
    "..qPPPPPPq......",
    "...qqqqqqq......",
    "................",
]))

ICONS["corbeille"] = outline(grid([
    "................",
    "......qqqq......",
    "...BBBBBBBBBB...",
    "...bbbbbbbbbb...",
    "................",
    "....pvvvvvvp....",
    "....plvplvpp....",
    "....plvplvpp....",
    "....plvplvpp....",
    "....plvplvpp....",
    "....plvplvpp....",
    "....plvplvpp....",
    "....pppppppp....",
    "................",
    "................",
    "................",
]))

ICONS["refaire"] = outline(grid([
    "................",
    "................",
    "......gggg.G....",
    "....gg....gG....",
    "...g.....GGG....",
    "...g............",
    "..g.............",
    "..g..........G..",
    "..g..........G..",
    "............G...",
    "............G...",
    "....ggg....G....",
    "....gg...GG.....",
    "....g.GGG.......",
    "................",
    "................",
]))

ICONS["reglages"] = grid([         # engrenage
    "................",
    "......kkkk......",
    "..kk..kBbk..kk..",
    ".kBbkkkBbkkkbnk.",
    ".kbBBBBbbbbbbnk.",
    "..kBbbbkkbbbnk..",
    "kkkBbbkKKkbbnkkk",
    "kBBbbkKKKKkbbbnk",
    "knnbbkKKKKkbbnnk",
    "kkkbbbkKKkbbnkkk",
    "..kbbbbkkbbbnk..",
    ".kbbbbbbbbbbbnk.",
    ".knnkkknnkkknnk.",
    "..kk..knnk..kk..",
    "......kkkk......",
    "................",
])

ICONS["oeil"] = grid([
    "................",
    "................",
    "................",
    "................",
    ".....kkkkkk.....",
    "...kkwwwwwwkk...",
    "..kwwwkkkkwwwk..",
    ".kwwwkggGkkwwwk.",
    ".kwwwkgkGGkwwwk.",
    "..kwwkGGGGkwwk..",
    "...kkwkkkkwkk...",
    ".....kkkkkk.....",
    "................",
    "................",
    "................",
    "................",
])

ICONS["ok"] = outline(grid([
    "................",
    "................",
    "................",
    "............gg..",
    "...........ggG..",
    "..........ggG...",
    "..gg.....ggG....",
    "..ggG...ggG.....",
    "...ggG.ggG......",
    "....ggggG.......",
    ".....ggG........",
    "......G.........",
    "................",
    "................",
    "................",
    "................",
]))

ICONS["etoile"] = outline(grid([
    "................",
    ".......B........",
    ".......B........",
    "......BBb.......",
    "......BBb.......",
    ".BBBBBBwBbbbbn..",
    "..BBBBBBBbbbn...",
    "...BBBBBbbbn....",
    "....BBBbbbn.....",
    "....BBbbbbn.....",
    "...BBbnnbbbn....",
    "...Bbn...nbn....",
    "..Bn.......nn...",
    "................",
    "................",
    "................",
]))

ICONS["de"] = outline(grid([      # dé : nouvelle graine
    "................",
    "................",
    "......wwww......",
    "....wwPPPPww....",
    "..wwPPPkPPPPww..",
    "..qwwPPPPPPwwQ..",
    "..qqqwwPPwwQQQ..",
    "..qkqqqwwQQQkQ..",
    "..qqqqqqQQQQQQ..",
    "..qqqkqqQQkQQQ..",
    "..qqqqqqQQQQQQ..",
    "..qkqqqqQQQQkQ..",
    "...qqqqqQQQQQ...",
    ".....qqqQQQ.....",
    "................",
    "................",
]))

ICONS["grille"] = grid([
    "................",
    ".kkkkkkkkkkkkkk.",
    ".kqqqkqqqkqqqqk.",
    ".kqPPkqPPkqPPPk.",
    ".kqPPkqPPkqPPPk.",
    ".kkkkkkkkkkkkkk.",
    ".kqqqkqqqkqqqqk.",
    ".kqPPkqPPkqPPPk.",
    ".kqPPkqPPkqPPPk.",
    ".kkkkkkkkkkkkkk.",
    ".kqqqkqqqkqqqqk.",
    ".kqPPkqPPkqPPPk.",
    ".kqPPkqPPkqPPPk.",
    ".kqPPkqPPkqPPPk.",
    ".kkkkkkkkkkkkkk.",
    "................",
])

ICONS["dossier"] = outline(grid([
    "................",
    "................",
    "................",
    "..bbbb..........",
    ".bBBBBb.........",
    ".bBBBBBbbbbbbb..",
    ".bBwBBBBBBBBBn..",
    ".bbbbbbbbbbbbn..",
    ".bBBBBBBBBBBBBb.",
    ".bBBBBBBBBBBBn..",
    ".bBBBBBBBBBBBn..",
    ".bBBBBBBBBBBn...",
    ".nnnnnnnnnnnn...",
    "................",
    "................",
    "................",
]))

# ---------------------------------------------------------------- emblème 32 x 32 : tête de bête dont les cornes débordent du sceau
# moitié gauche dessinée à la main, miroir pour la droite ; la lumière vient d'en haut à gauche
BEAST_HALF = [
    "................",
    "..P.............",
    "..qP............",
    "..qP............",
    "..QqP...........",
    "...QqP..........",
    "...QqqP.........",
    "....QqqP........",
    ".....QQqP.......",
    "......QQqP......",
    ".......QQqpvvvvv",
    "........pvllllll",
    "........pvlvvvvE",
    "........pvlvvvve",
    "........pvkkvvvv",
    "........pvggkkvv",
    "........pvGwggkv",
    "........pvvGGkvv",
    ".........pvvvvvv",
    ".........pvvvvvv",
    ".........pvvvvkv",
    "..........pkkkkk",
    "..........pkwRRR",
    "...........pkwrr",
    "............pkkk",
    ".............ppp",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]


def beast():
    rows = []
    for half in BEAST_HALF:
        right = half[::-1].replace("l", "v")      # côté droit dans l'ombre : pas de reflet
        rows.append(half + right)
    return outline(grid(rows))


def seal(size=32, r=13.5, cy=16.5):
    """Sceau de laiton (lumière en haut à gauche), rivets aux diagonales, fond d'encre qui s'éclaircit au centre."""
    g = [["."] * size for _ in range(size)]
    cx = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** .5
            if d <= r + .3:
                lit = (x - cx) + (y - cy) < 0
                if d > r - .7:
                    ch = "k"
                elif d > r - 1.7:
                    ch = "B" if lit else "n"
                elif d > r - 2.7:
                    ch = "b"
                elif d > r - 3.4:
                    ch = "k"
                else:
                    ch = "d" if d < r - 8 else "K"
                g[y][x] = ch
    for x, y in ((7, 8), (24, 8), (7, 25), (24, 25)):   # rivets
        g[y][x] = "w" if y < 16 and x < 16 else "B"
    return g


EMBLEM = [[h if h != "." else s_ for h, s_ in zip(hr, sr)] for hr, sr in zip(beast(), seal())]

# ---------------------------------------------------------------- curseur 12 x 12
CURSOR = grid([
    "kk..........",
    "kBk.........",
    "kwBk........",
    "kBBbk.......",
    "kBbbbk......",
    "kBbbbbk.....",
    "kBbbbbbk....",
    "kBbbbkkkk...",
    "kBbkbk......",
    "kbk.kbk.....",
    "kk..kbk.....",
    ".....kk.....",
])

# ---------------------------------------------------------------- fond : mur de briques 64 x 64 (se répète)
import random

# chaque brique : (ton de face, lumière en haut à gauche, ombre en bas)
BRICK_TONES = [("s", "S", "K"), ("u", "S", "K"), ("S", "t", "u"), ("u", "U", "s"), ("s", "u", "K")]
CRACK = ["k..", ".k.", ".kk"]  # fissure posée sur quelques briques


def stone():
    rnd = random.Random(7)
    W = H = 64
    g = [["m"] * W for _ in range(H)]
    for row in range(H // 8):
        off = 8 if row % 2 else 0
        for col in range(W // 16):
            face, hi, lo = rnd.choice(BRICK_TONES)
            x0, y0 = col * 16 - off, row * 8
            for dy in range(7):           # 15 x 7 de pierre, joint de 1 px à droite et en bas
                for dx in range(15):
                    x, y = (x0 + dx) % W, y0 + dy
                    ch = face
                    if dy == 0 or dx == 0:
                        ch = hi
                    if dy == 6 or dx == 14:
                        ch = lo
                    g[y][x] = ch
            for cx, cy in ((0, 0), (14, 0), (0, 6), (14, 6)):   # coins usés
                if rnd.random() < .35:
                    g[y0 + cy][(x0 + cx) % W] = "m"
            for _ in range(rnd.randint(1, 3)):                   # grain de la pierre
                g[y0 + rnd.randint(1, 5)][(x0 + rnd.randint(1, 13)) % W] = rnd.choice((hi, lo))
            if rnd.random() < .18:                                # fissure
                fx, fy = rnd.randint(2, 10), rnd.randint(1, 3)
                for yy, line in enumerate(CRACK):
                    for xx, ch in enumerate(line):
                        if ch == "k":
                            g[y0 + fy + yy][(x0 + fx + xx) % W] = "K"
            if rnd.random() < .1:                                 # mousse discrète au pied de la brique
                for dx in range(rnd.randint(2, 5)):
                    if rnd.random() < .75:
                        g[y0 + 6][(x0 + 3 + dx) % W] = "o"
                g[y0 + 5][(x0 + 4) % W] = "o"
    return g


DUST = grid([   # 3 images de 5 px : une poussière qui scintille
    "..w..|.....|.....".replace("|", ""),
    ".wqw.|..q..|.....".replace("|", ""),
    "..w..|.....|..q..".replace("|", ""),
])

# ---------------------------------------------------------------- sol de l'aperçu en jeu (32 x 32, se répète)
TUFT = ["..5..", "5.4.5", "4.4.4", ".242."]
FLOWER_W = [".w.", "wBw", ".4."]
FLOWER_B = [".e.", "eEe", ".4."]
PEBBLE = [".99.", "9888", "8886", ".66."]
PEBBLE_S = ["98", "86"]


def _stamp(g, shape, x, y):
    h, w = len(g), len(g[0])
    for dy, line in enumerate(shape):
        for dx, ch in enumerate(line):
            if ch != ".":
                g[(y + dy) % h][(x + dx) % w] = ch


def _mottle(base, dark, light, seed, size=32):
    """Fond en taches douces (pas de bruit pixel à pixel) : sommes de sinus qui se raccordent aux bords."""
    import math
    rnd = random.Random(seed)
    dirs = [(1, 0), (0, 1), (1, 2), (2, -1), (2, 1), (-1, 3), (3, 1), (1, -2)]
    waves = [(a, b, rnd.random() * 6.28) for a, b in rnd.sample(dirs, 6)]  # directions variées : pas de bandes
    g = []
    for y in range(size):
        r = []
        for x in range(size):
            v = sum(math.sin(2 * math.pi * (a * x + b * y) / size + ph) for a, b, ph in waves) / 6
            v += (rnd.random() - .5) * .3
            r.append(dark if v < -.3 else light if v > .32 else base)
        g.append(r)
    return g


def grass():
    g = _mottle("3", "2", "4", 11)
    for x, y in ((2, 3), (19, 1), (11, 12), (26, 14), (4, 22), (17, 25), (28, 27)):
        _stamp(g, TUFT, x, y)
    for x, y in ((8, 6), (23, 21), (13, 29), (30, 8)):
        g[y][x] = "1"
    _stamp(g, FLOWER_W, 13, 4)
    _stamp(g, FLOWER_B, 25, 6)
    _stamp(g, FLOWER_W, 9, 17)
    return g


def path():
    g = _mottle("7", "6", "8", 23)
    for x, y in ((3, 4), (21, 9), (10, 22), (26, 25)):
        _stamp(g, PEBBLE, x, y)
    for x, y in ((14, 2), (6, 13), (29, 17), (17, 15), (1, 28), (19, 29)):
        _stamp(g, PEBBLE_S, x, y)
    for x, y in ((9, 8), (10, 9), (11, 9), (24, 3), (25, 4), (15, 26), (16, 26)):  # sillons
        g[y][x] = "6"
    return g


def road():
    """Chemin de 32 px de haut bordé d'herbe en haut et en bas (l'herbe déborde en brins sur la terre)."""
    g = path()
    top = grass()
    rnd = random.Random(5)
    for x in range(32):
        edge = 3 + (1 if rnd.random() < .45 else 0) + (1 if x % 7 == 3 else 0)
        for y in range(edge):
            g[y][x] = top[y][x]
        g[edge - 1][x] = "5" if rnd.random() < .3 else "4"
        g[edge][x] = "6"                                     # ombre de l'herbe sur la terre
        bot = 3 + (1 if rnd.random() < .45 else 0) + (1 if x % 5 == 1 else 0)
        for y in range(32 - bot, 32):
            g[y][x] = top[y][x]
        g[32 - bot][x] = "5" if rnd.random() < .35 else "4"
    return g


def build():
    UI.mkdir(exist_ok=True)
    out = {}
    edge = list("kBbbnkd") + ["K"] * 5
    out["panel"] = img(panel(PANEL_TL, edge, edge, "K"))
    out["parchment"] = img(parchment())
    for name, (hi, face, lo) in BTN.items():
        out[name] = img(button(hi, face, lo))
        out[name + "_h"] = img(button("w", hi, face))
        out[name + "_p"] = img(pressed(lo, face, face))
    out["tab"] = img(TAB_OFF)
    out["tab_on"] = img(TAB_ON)
    out["bar"] = img(BAR)
    out["liquid"] = img(LIQUID)
    for k, g in ICONS.items():
        out[f"i_{k}"] = img(g)
    out["emblem"] = img(EMBLEM)
    out["cursor"] = img(CURSOR)
    out["stone"] = img(stone())
    out["dust"] = img(DUST)
    out["grass"] = img(grass())
    out["path"] = img(path())
    out["road"] = img(road())
    for k, im in out.items():
        im.save(UI / f"{k}.png")
    return out


def preview(out, dest, scale=4):
    """Planche de contrôle : chaque sprite agrandi sur fond d'encre."""
    items = list(out.items())
    cols, cell = 8, 40 * scale
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell), rgba("#3c3050"))
    for i, (k, im) in enumerate(items):
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        if big.width > cell - 8:
            f = (cell - 8) / big.width
            big = big.resize((int(big.width * f), int(big.height * f)), Image.NEAREST)
        sheet.alpha_composite(big, ((i % cols) * cell + 4, (i // cols) * cell + 4))
    sheet.save(dest)


if __name__ == "__main__":
    o = build()
    if "--preview" in sys.argv:
        preview(o, sys.argv[sys.argv.index("--preview") + 1])
    print(len(o), "sprites ->", UI)
