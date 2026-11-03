# NeoBestiary Studio

Décris une créature en français, NeoBestiary Studio la dessine en **sprite pixel art 64×64**, vue de dessus, dans les **4 directions** avec une **marche en 3 images**, prête pour un jeu.

![NeoBestiary Studio](screenshots/1.jpg)

## Ce qu'il sait faire

- **Créer** : tu écris ce que tu veux (« juste un œil géant », « une vache avec une seule corne », « un taureau au corps d'araignée »…), sans rien imposer ni interdire. L'appli dessine d'abord **3 esquisses** en une demi-minute : tu choisis la plus fidèle, et le dos, le profil et la marche sont faits à partir d'elle.
- **Directions** : la planche 4 directions × 3 pas. Chaque image a ses versions (◀ ▶) et chaque direction peut être refaite.
- **Sprite Lab** :
  - un éditeur pixel 64×64 (crayon, gomme, pipette, seau, annuler / refaire) ;
  - la palette commune aux 12 images, le contour ;
  - un aperçu en jeu : ta créature marche sur l'herbe avec les flèches du clavier.
- **Export** : une planche PNG (3 colonnes × 4 lignes de 64×64) et son JSON (directions, images, point d'ancrage aux pieds, ordre de l'animation).
- **Bibliothèque** : toutes tes créatures, avec recherche. Une créature supprimée part dans une corbeille, elle n'est pas effacée.

Les créatures sont rangées dans `Documents\NeoBestiary Studio`.

## Ce qu'il faut

- Windows et une carte graphique **NVIDIA avec 8 Go de mémoire vidéo** ou plus.
- **ComfyUI portable** ([github.com/comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI), page Releases), décompressé n'importe où. Au premier lancement, l'appli le cherche et, si besoin, te demande son dossier.
- Les modèles, que l'appli propose d'installer elle-même (licences libres, depuis Hugging Face, environ 15 Go en tout) :
  - **FLUX.2 klein 4B** (le dessin) ;
  - l'encodeur **Qwen3 4B** (il comprend le français) ;
  - **BiRefNet** (détourage : ni fond ni ombre au sol).

ComfyUI démarre tout seul à la première invocation et s'arrête quand tu fermes NeoBase. Si tu as déjà lancé ton propre ComfyUI, l'appli l'utilise et ne l'arrête pas.

## Combien de temps

Sur une RTX 4060 : une demi-minute pour les 3 esquisses, puis 2 à 3 minutes pour le dos et le profil (deux essais chacun, le meilleur est gardé automatiquement) et la marche. Les images de marche reprennent exactement les couleurs de la pose de repos.

## Permissions

L'appli demande l'**accès complet** : elle lance le moteur de dessin (Python, livré dans le plugin) et ComfyUI sur ton PC, et enregistre tes créatures dans tes Documents. Rien ne part sur Internet, sauf le téléchargement des modèles si tu le demandes.
