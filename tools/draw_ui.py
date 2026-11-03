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
BEAST = outline(grid([
    "................................",
    ".P............................P.",
    ".qP..........................Pq.",
    ".qP..........................Pq.",
    "..qP........................Pq..",
    "..QqP......................PqQ..",
    "...QqP....................PqQ...",
    "....QqPP................PPqQ....",
    ".....QqqPP............PPqqQ.....",
    "......QQqqPvvvvvvvvvvPqqQQ......",
    "........QQvllllllllllvQQ........",
    ".......pvvlvvvvvvvvvvlvvp.......",
    "......pvvlvvvvvvvvvvvvlvvp......",
    "......pvlkkkvvvvvvvvkkklvp......",
    "......pvvkkgwkvvvvkwgkkvvp......",
    "......pvvvkGGgkvvkgGGkvvvp......",
    "......pvvvvkkkvvvvkkkvvvvp......",
    "......pvvvvvvvvvvvvvvvvvvp......",
    ".......pvvvvvvkvvkvvvvvvp.......",
    ".......pvvvvvvvvvvvvvvvvp.......",
    "........pkkkkkkkkkkkkkkp........",
    "........pkwkRRRRRRRRkwkp........",
    ".........pkwkRRRRRRkwkp.........",
    "..........pkkwkkkkwkkp..........",
    "...........ppvvvvvvpp...........",
    ".............pppppp.............",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
]))


def seal(size=32, r=13.5, cy=16.5):
    """Disque de laiton (lumière en haut à gauche) au fond d'encre."""
    g = [["."] * size for _ in range(size)]
    cx = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** .5
            if d <= r + .3:
                lit = (x - cx) + (y - cy) < 0
                g[y][x] = "k" if d > r - .7 else ("B" if lit else "n") if d > r - 1.7 else "b" if d > r - 2.7 else "K"
    return g


EMBLEM = [[h if h != "." else s_ for h, s_ in zip(hr, sr)] for hr, sr in zip(BEAST, seal())]

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

# ---------------------------------------------------------------- fond : dalle de pierre 32 x 32 (se répète) + poussière
def stone():
    rows = []
    for y in range(32):
        r = []
        for x in range(32):
            band = y // 8
            off = 8 if band % 2 else 0
            jx = (x + off) % 16
            if y % 8 == 7 or jx == 15:
                ch = "k"
            elif y % 8 == 0 or jx == 0:
                ch = "S"
            else:
                ch = "s"
            r.append(ch)
        rows.append(r)
    for (y, x, ch) in ((3, 5, "S"), (4, 6, "S"), (11, 20, "S"), (12, 21, "S"), (19, 9, "d"), (20, 9, "d"),
                       (21, 10, "d"), (27, 25, "S"), (26, 26, "t"), (5, 27, "d"), (13, 3, "t"), (29, 14, "S")):
        rows[y][x] = ch
    return rows


DUST = grid([   # 3 images de 5 px : une poussière qui scintille
    "..w..|.....|.....".replace("|", ""),
    ".wqw.|..q..|.....".replace("|", ""),
    "..w..|.....|..q..".replace("|", ""),
])

# ---------------------------------------------------------------- tuiles de sol pour l'aperçu en jeu (16 x 16)
GRASS = grid([
    "GGGGGGGGGGGGGGGG",
    "GGGgGGGGGGGGhGGG",
    "GGgGGGGGGGGGGGGG",
    "GGGGGGGGGhGGGGGG",
    "GGGGGGGGGGGGGGgG",
    "GhGGGGGgGGGGGGGG",
    "GGGGGGgGGGGGGGGG",
    "GGGGGGGGGGGGGGGG",
    "GGGGGGGGGGGhGGGG",
    "GGGgGGGGGGGGGGGG",
    "GGGGGGGGGGGGGGGG",
    "GGGGGGGGGgGGGGGG",
    "GGhGGGGGgGGGGGgG",
    "GGGGGGGGGGGGGGGG",
    "GGGGGGGGGGGGhGGG",
    "GGGGGgGGGGGGGGGG",
])
PATH = grid([
    "qqqqqqqqqqqqqqqq",
    "qPqqqqqqqQqqqqqq",
    "qqqqQqqqqqqqqPqq",
    "qqqqqqqqqqqqqqqq",
    "qqqqqqqPqqqqqqqq",
    "qQqqqqqqqqqqQqqq",
    "qqqqqqqqqqqqqqqq",
    "qqqqqqqqqqQqqqqq",
    "qqqPqqqqqqqqqqqq",
    "qqqqqqqqqqqqqqPq",
    "qqqqqqQqqqqqqqqq",
    "qqqqqqqqqqqqqqqq",
    "qQqqqqqqqPqqqqqq",
    "qqqqqqqqqqqqqQqq",
    "qqqqqPqqqqqqqqqq",
    "qqqqqqqqqqqqqqqq",
])


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
    out["grass"] = img(GRASS)
    out["path"] = img(PATH)
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
