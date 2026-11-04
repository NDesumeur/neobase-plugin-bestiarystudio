# -*- coding: utf-8 -*-
"""Auto-test du service : lance nb_server.py avec le moteur factice et appelle chaque route.

python test_server.py          (ajouter --real pour le vrai moteur, ComfyUI doit être prêt)
"""
import base64
import io
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
TOKEN = "test-jeton"


def call(port, path, body=None, token=TOKEN, raw=False):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-NB-Token": token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = r.read()
            return r.status, (data if raw else json.loads(data))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def wait_job(port, timeout=900):
    t = time.time()
    while time.time() - t < timeout:
        _, j = call(port, "/job")
        if j["done"]:
            assert not j["error"], j["error"]
            return j
        time.sleep(0.3)
    raise AssertionError("tâche trop longue")


def main():
    real = "--real" in sys.argv
    lib = tempfile.mkdtemp(prefix="nbtest_")
    cmd = [sys.executable, str(HERE / "nb_server.py"), "--token", TOKEN, "--library", lib] + ([] if real else ["--fake"])
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    try:
        port = int(proc.stdout.readline().split()[1])
        assert call(port, "/status", token="faux")[0] == 403, "jeton non vérifié"
        code, st = call(port, "/status")
        assert code == 200 and "comfy" in st, st
        assert call(port, "/create", {"name": "X", "description": ""})[0] == 400, "description vide acceptée"

        code, r = call(port, "/create", {"name": "Chien de feu", "description": "chien de feu blanc et rouge", "seed": 42})
        assert code == 200, r
        slug = r["slug"]
        assert call(port, "/create", {"name": "Autre", "description": "x"})[0] == 400, "deux tâches en même temps"
        j = wait_job(port)
        assert j["kind"] == "sketch"
        _, c = call(port, "/creature?slug=" + slug)
        assert c["pending"] and len(c["designs"]) == 3, c
        assert c["brief"]["posture"] and c["brief"]["en"], c["brief"]  # la description est lue avant les esquisses
        assert call(port, "/library")[1][0]["thumb"], "pas de vignette pour une esquisse"
        assert call(port, "/continue", {"slug": slug, "index": 1})[0] == 200
        wait_job(port)

        _, c = call(port, "/creature?slug=" + slug)
        assert not c["pending"] and c["views"]["bas"]["version"] == 2, c["views"]["bas"]
        assert len(c["sprites"]) == 12, c["sprites"]
        assert c["views"]["haut"]["versions"] == 2 and c["views"]["droite"]["file"], c["views"]
        code, png = call(port, f"/file?slug={slug}&path=sprites/sheet.png", raw=True)
        sheet = Image.open(io.BytesIO(png))
        assert sheet.size == (192, 256), sheet.size
        assert call(port, f"/file?slug={slug}&path=../../config.json")[0] == 400, "sortie du dossier possible"

        _, c = call(port, "/choose", {"slug": slug, "key": "haut", "delta": 1})
        assert c["views"]["haut"]["version"] == 2
        _, c = call(port, "/choose", {"slug": slug, "key": "gauche", "delta": 1})
        assert c["views"]["droite"]["versions"] == 1, "le miroir s'empile en versions"

        _, c = call(port, "/lab", {"slug": slug, "opts": {"colors": 8, "outline": False}})
        assert c["lab"]["colors"] == 8 and len(c["palette"]) <= 8, c["palette"]

        red = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
        buf = io.BytesIO()
        red.save(buf, "PNG")
        _, c = call(port, "/frame", {"slug": slug, "key": "bas_repos", "png": base64.b64encode(buf.getvalue()).decode()})
        _, c = call(port, "/rebuild", {"slug": slug})
        _, png = call(port, f"/file?slug={slug}&path=sprites/bas_repos.png", raw=True)
        assert Image.open(io.BytesIO(png)).convert("RGBA").getpixel((5, 5)) == (255, 0, 0, 255), "retouche perdue"
        call(port, "/reset-edits", {"slug": slug})

        _, r = call(port, "/redo", {"slug": slug, "dir": "gauche"})
        wait_job(port)
        _, c = call(port, "/creature?slug=" + slug)
        assert c["views"]["gauche"]["versions"] == 3, c["views"]["gauche"]
        haut = c["views"]["haut"]["versions"]
        _, r = call(port, "/redo", {"slug": slug, "dir": "bas"})
        wait_job(port)
        _, c = call(port, "/creature?slug=" + slug)
        assert c["views"]["bas"]["version"] == 4 and c["views"]["haut"]["versions"] == haut + 2, "refaire la face ne suit pas"

        assert c["lore"] and c["lore"]["histoire"], "fiche absente après la création"
        _, c = call(port, "/lore", {"slug": slug})
        assert c["lore"]["type"], c["lore"]
        k = c["lore"]["combat"]
        R = ["commun", "peu commun", "rare", "épique", "légendaire"]
        assert k["rarete"] and sum(k["stats"].values()) > 100 and k["faiblesses"], k
        assert len(k["attaques"]) == (2, 3, 3, 4, 4)[R.index(k["rarete"])], k  # 2 à 4 attaques selon la rareté
        assert len({a["genre"] for a in k["attaques"]}) == len(k["attaques"]), k  # jamais deux fois le même geste
        # rareté choisie à la main : verrouillée, 4 attaques pour une légendaire ; puis de nouveau calculée
        _, c = call(port, "/rarity", {"slug": slug, "rarete": "légendaire"})
        kk = c["lore"]["combat"]
        assert kk["rarete"] == "légendaire" and kk["rarete_fixe"] and len(kk["attaques"]) == 4, kk
        assert any(a.get("effet", {}).get("soin") for a in kk["attaques"]) and set(c["attack_fx"]) == {"1", "2", "3", "4"}
        assert call(port, "/rarity", {"slug": slug, "rarete": "mythique"})[0] == 400
        _, c = call(port, "/rarity", {"slug": slug, "rarete": None})
        assert c["lore"]["combat"]["rarete"] == k["rarete"] and not c["lore"]["combat"]["rarete_fixe"]
        assert set(c["attack_fx"]["2"]) == {"bas", "haut", "gauche", "droite"}, c["attack_fx"]
        n = c["views"]["gauche"]["versions"]
        assert call(port, "/edit", {"slug": slug, "key": "gauche", "instruction": ""})[0] == 400, "retouche vide acceptée"
        assert call(port, "/edit", {"slug": slug, "key": "gauche", "instruction": "une corne", "zone": [.5, .3, .1]})[0] == 200
        wait_job(port)
        _, c = call(port, "/creature?slug=" + slug)
        v = c["views"]["gauche"]
        assert v["versions"] == n + 1 and v["version"] == v["versions"], v  # la retouche devient la vue active
        assert c["views"]["droite"]["file"] and c["attack_fx"]["1"]["droite"], "le miroir et les attaques suivent"
        # portrait de combat, animations attente / dégâts / K.O., arene.json
        assert c["portrait"] and c["portrait_version"][1] >= 1, c["portrait"]
        _, png = call(port, f"/file?slug={slug}&path=sprites/portrait.png", raw=True)
        assert Image.open(io.BytesIO(png)).size == (256, 256)
        _, png = call(port, f"/file?slug={slug}&path=sprites/ko.png", raw=True)
        assert Image.open(io.BytesIO(png)).size == (256, 256)  # 4 images x 4 directions
        assert c["illustration"] and c["illustration_version"][1] % 3 == 0 and c["hd"]["illustration"], c["illustration_version"]
        _, png = call(port, f"/file?slug={slug}&path=sprites/illustration.png", raw=True)
        assert Image.open(io.BytesIO(png)).size == (256, 256)
        ni = c["illustration_version"][1]
        assert call(port, "/illustration", {"slug": slug})[0] == 200
        wait_job(port)
        _, c = call(port, "/creature?slug=" + slug)
        assert c["illustration_version"] == [ni + 3, ni + 3], c["illustration_version"]
        _, png = call(port, f"/file?slug={slug}&path=" + c["hd"]["illustration"], raw=True)
        hd = Image.open(io.BytesIO(png))
        mask = Image.new("RGB", hd.size)
        mask.paste((255, 0, 0), (0, 0, hd.width // 2, hd.height))  # rouge : la moitié gauche est effacée
        buf = io.BytesIO()
        mask.save(buf, "PNG")
        b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        assert call(port, "/cutout", {"slug": slug, "key": "sheet", "mask": b64})[0] == 400
        _, c = call(port, "/cutout", {"slug": slug, "key": "illustration", "mask": b64})
        assert c["illustration_version"] == [ni + 4, ni + 4], c["illustration_version"]
        _, png = call(port, f"/file?slug={slug}&path=" + c["hd"]["illustration"], raw=True)
        cut = Image.open(io.BytesIO(png)).convert("RGBA")
        assert cut.getbbox()[0] >= hd.width // 2, cut.getbbox()
        n_g = c["views"]["gauche"]["versions"]
        _, png = call(port, f"/file?slug={slug}&path=" + c["views"]["gauche"]["file"], raw=True)
        g = Image.open(io.BytesIO(png))
        green = Image.new("RGB", g.size, (0, 255, 0))  # vert partout : tout est restauré
        buf = io.BytesIO()
        green.save(buf, "PNG")
        _, c = call(port, "/cutout", {"slug": slug, "key": "gauche", "mask": base64.b64encode(buf.getvalue()).decode()})
        assert c["views"]["gauche"]["versions"] == n_g + 1 and c["views"]["droite"]["file"], c["views"]["gauche"]
        before = c["portrait_version"][1]
        assert call(port, "/portrait", {"slug": slug})[0] == 200
        wait_job(port)
        _, c = call(port, "/creature?slug=" + slug)
        assert c["portrait_version"] == [before + 1, before + 1], c["portrait_version"]
        # variantes : chromatique monte d'un cran, glace prend le type glace
        assert call(port, "/variant", {"slug": slug, "variant": "arc-en-ciel"})[0] == 400
        _, c = call(port, "/variant", {"slug": slug, "variant": "chromatique"})
        _, c = call(port, "/variant", {"slug": slug, "variant": "glace"})
        f = {x["id"]: x for x in c["forms"]}
        assert set(f) == {"base", "chromatique", "glace"} and f["glace"]["nom"].endswith("de glace"), f
        R = ["commun", "peu commun", "rare", "épique", "légendaire"]
        assert R.index(f["chromatique"]["combat"]["rarete"]) == min(4, R.index(f["base"]["combat"]["rarete"]) + 1)
        assert f["glace"]["combat"]["faiblesses"] == ["feu", "roche", "acier"]
        _, png = call(port, f"/file?slug={slug}&path=sprites/variantes/glace/attaque2.png", raw=True)
        assert Image.open(io.BytesIO(png)).size == (256, 256)
        ar = json.loads((Path(lib) / "creatures" / slug / "arene.json").read_text(encoding="utf-8"))
        assert len(ar["formes"]) == 3 and ar["animations"]["ko"]["ms"] and ar["formes"][2]["attaques"][1]["decalages"]["bas"], ar
        _, c = call(port, "/variant-remove", {"slug": slug, "variant": "glace"})
        assert c["variants"] == ["chromatique"] and not (Path(lib) / "creatures" / slug / "sprites/variantes/glace").exists()
        _, i = call(port, "/inspire", {"theme": "lovecraft"})
        assert i["description"], i

        _, e = call(port, "/export", {"slug": slug})
        meta = json.loads(Path(e["json"]).read_text(encoding="utf-8"))
        assert meta["rows"] == 4 and meta["directions"]["haut"]["row"] == 3 and Path(e["png"]).is_file()
        assert meta["fiche"]["histoire"] and (Path(e["folder"]) / "portrait.png").is_file()
        assert (Path(e["folder"]) / meta["illustration"]).is_file() and (Path(e["folder"]) / meta["illustration_hd"]).is_file()
        atk = meta["attaques"][-1]
        assert atk["genre"] == "projectile" and (Path(e["folder"]) / atk["effet_image"]).is_file(), atk
        assert len(atk["directions"]["gauche"]["frames"]) == 4 and "effet_decalage" in atk["directions"]["bas"]["frames"][2]
        assert Path(e["folder"]).parent == Path(call(port, "/exports")[1]["folder"]), e["folder"]
        assert meta["animations"]["attente"]["timing_ms"] and (Path(e["folder"]) / meta["animations"]["degats"]["image"]).is_file()
        assert meta["variantes"][0]["id"] == "chromatique" and (Path(e["folder"]) / "variantes/chromatique/attaque1.png").is_file()
        _, bal = call(port, "/balance")
        assert bal["total"] == 1 and sum(x["n"] for x in bal["raretes"]) == 1 and bal["alertes"], bal
        assert "conseils" in bal and bal["creatures"][0]["prestige"] == 50, bal

        _, libr = call(port, "/library")
        assert [x["slug"] for x in libr] == [slug] and libr[0]["thumb"]
        call(port, "/delete", {"slug": slug})
        assert call(port, "/library")[1] == [] and (Path(lib) / "corbeille").is_dir()
        if not real:  # contrôle automatique : l'esquisse à 1 tête est refaite, le profil avec pattes est refait
            _, r = call(port, "/create", {"name": "Trio", "description": "méduse à trois têtes qui flotte", "seed": 5})
            wait_job(port)
            _, c = call(port, "/creature?slug=" + r["slug"])
            assert len(c["designs"]) == 3 and all("✓" in n for n in c["design_notes"]), c["design_notes"]
            call(port, "/continue", {"slug": r["slug"], "index": 0})
            wait_job(port)
            _, c = call(port, "/creature?slug=" + r["slug"])
            assert c["views"]["gauche"]["versions"] == 4, c["views"]["gauche"]  # 2 refusés + 2 refaits
            # fusion : l'hybride de deux créatures finies hérite du type de l'une et d'une attaque de chacune
            _, r2 = call(port, "/create", {"name": "Bis", "description": "chien de glace", "seed": 9})
            wait_job(port)
            call(port, "/continue", {"slug": r2["slug"], "index": 0})
            wait_job(port)
            assert call(port, "/fuse", {"a": r["slug"], "b": r["slug"]})[0] == 400, "fusion avec soi-même"
            code, fu = call(port, "/fuse", {"a": r["slug"], "b": r2["slug"]})
            assert code == 200, fu
            wait_job(port)
            _, c = call(port, "/creature?slug=" + fu["slug"])
            assert c["pending"] and len(c["designs"]) == 3 and c["parents"] == [r["slug"], r2["slug"]], c
            assert "hybride" in c["description"], c["description"]
            call(port, "/continue", {"slug": fu["slug"], "index": 0})
            wait_job(port)
            _, c = call(port, "/creature?slug=" + fu["slug"])
            pa = [call(port, "/creature?slug=" + s_)[1]["lore"] for s_ in (r["slug"], r2["slug"])]
            assert c["lore"]["type"] in {p["type"] for p in pa}, c["lore"]["type"]
            names = [a["nom"] for a in c["lore"]["attaques"]]
            assert names == [a["nom"] for a in pa[0]["attaques"][:2] + pa[1]["attaques"][-2:]], names
            # posture écrite en toutes lettres (« rampante ») : elle prime sur ce que la plume a compris
            _, rr = call(port, "/create", {"name": "Ver", "description": "une créature rampante", "seed": 3})
            wait_job(port)
            assert call(port, "/creature?slug=" + rr["slug"])[1]["brief"]["posture"] == "rampe"
            call(port, "/delete", {"slug": rr["slug"]})
            for s_ in (r["slug"], r2["slug"], fu["slug"]):
                call(port, "/delete", {"slug": s_})
        print("OK : toutes les routes répondent", "(moteur réel)" if real else "(moteur factice)")
    finally:
        proc.kill()


if __name__ == "__main__":
    main()
