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
        assert k["rarete"] and sum(k["stats"].values()) > 100 and len(k["attaques"]) == 2 and k["faiblesses"], k
        assert set(c["attack_fx"]["2"]) == {"bas", "haut", "gauche", "droite"}, c["attack_fx"]
        n = c["views"]["gauche"]["versions"]
        assert call(port, "/edit", {"slug": slug, "key": "gauche", "instruction": ""})[0] == 400, "retouche vide acceptée"
        assert call(port, "/edit", {"slug": slug, "key": "gauche", "instruction": "une corne", "zone": [.5, .3, .1]})[0] == 200
        wait_job(port)
        _, c = call(port, "/creature?slug=" + slug)
        v = c["views"]["gauche"]
        assert v["versions"] == n + 1 and v["version"] == v["versions"], v  # la retouche devient la vue active
        assert c["views"]["droite"]["file"] and c["attack_fx"]["1"]["droite"], "le miroir et les attaques suivent"
        _, i = call(port, "/inspire", {"theme": "lovecraft"})
        assert i["description"], i

        _, e = call(port, "/export", {"slug": slug})
        meta = json.loads(Path(e["json"]).read_text(encoding="utf-8"))
        assert meta["rows"] == 4 and meta["directions"]["haut"]["row"] == 3 and Path(e["png"]).is_file()
        assert meta["fiche"]["histoire"] and (Path(e["folder"]) / "portrait.png").is_file()
        atk = meta["attaques"][1]
        assert atk["genre"] == "projectile" and (Path(e["folder"]) / atk["effet_image"]).is_file(), atk
        assert len(atk["directions"]["gauche"]["frames"]) == 4 and "effet_decalage" in atk["directions"]["bas"]["frames"][2]
        assert Path(e["folder"]).parent == Path(call(port, "/exports")[1]["folder"]), e["folder"]

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
            call(port, "/delete", {"slug": r["slug"]})
        print("OK : toutes les routes répondent", "(moteur réel)" if real else "(moteur factice)")
    finally:
        proc.kill()


if __name__ == "__main__":
    main()
