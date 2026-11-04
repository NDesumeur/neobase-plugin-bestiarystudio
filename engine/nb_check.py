# -*- coding: utf-8 -*-
"""NeoBestiary Studio - contrôle d'une image : ce que le modèle de vision voit contre ce que la description demande.

Mesuré sur la RTX 4060 avec gemma3:4b : il compte bien les têtes jusqu'à 3 ou 4 et voit si une créature a des
pattes, mais il compte mal les yeux et surestime au-delà de 5 têtes. On ne vérifie donc que les têtes (tolérance
au-delà de 4) et l'absence de pattes ; le reste n'est pas contrôlé.
"""
import re

LEGLESS = {"flotte", "vole", "nage", "rampe"}
_HEADS = re.compile(r"^\s*(\d+)\s+heads?\b", re.I)


def expected_heads(brief):
    for line in (brief or {}).get("anatomie") or []:
        m = _HEADS.match(line)
        if m:
            return int(m.group(1))
    return None


def legless(brief):
    b = brief or {}
    return b.get("posture") in LEGLESS or (bool(b.get("posture")) and b.get("pattes", 1) == 0)


def verdict(seen, brief, legs_only=False):
    """(bonne ?, [problèmes en français], écart) ; seen = {"heads", "legs", ...} vu par le modèle de vision."""
    issues, gap = [], 0
    want = None if legs_only else expected_heads(brief)
    try:
        heads = int(seen.get("heads", 0))
    except (TypeError, ValueError):
        heads = None
    if want and heads is not None:
        off = abs(heads - want)
        if off > (0 if want <= 4 else 2):
            issues.append(f"{heads} tête{'s' if heads > 1 else ''} au lieu de {want}")
            gap += off
    try:
        legs = int(seen.get("legs", 0))
    except (TypeError, ValueError):
        legs = 0
    if legless(brief) and legs > 0:
        issues.append("des pattes alors qu'elle n'en a pas")
        gap += 2
    return not issues, issues, gap


if __name__ == "__main__":
    b = dict(posture="quatre_pattes", pattes=4, anatomie=["3 heads: each on its own neck", "6 eyes: two per head"])
    assert expected_heads(b) == 3
    assert verdict({"heads": 3, "legs": 4}, b)[0]
    assert verdict({"heads": 1, "legs": 4}, b)[1] == ["1 tête au lieu de 3"]
    h = dict(posture="quatre_pattes", pattes=4, anatomie=["5 heads: in a row"])
    assert verdict({"heads": 7, "legs": 4}, h)[0] and not verdict({"heads": 2, "legs": 4}, h)[0]
    f = dict(posture="flotte", pattes=0, anatomie=["1 eye: centre"])
    assert not verdict({"heads": 1, "legs": 2}, f)[0] and verdict({"heads": 1, "legs": 0}, f)[0]
    assert verdict({"heads": 1, "legs": 4}, dict(posture="quatre_pattes", pattes=4))[0]  # rien à compter
    print("ok")
