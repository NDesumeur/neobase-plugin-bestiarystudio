# NeoBestiary Studio

Décris une créature en français, NeoBestiary Studio la dessine en **sprite pixel art 64×64**, vue de dessus, dans les **4 directions** avec une **marche en 3 images**, prête pour un jeu, et lui écrit sa **fiche de bestiaire**.

![NeoBestiary Studio](screenshots/1.jpg)

## Ce qu'il sait faire

- **Inspiration** : en panne d'idée ? Choisis un thème (Lovecraft, Animaux, Monstres, Folklore ou Mélange) et clique « Inspire-moi » : tu reçois un nom et une description claire, écrite pour le dessin (forme, posture, nombre d'yeux ou de pattes, couleurs). Tu la retouches si tu veux.
- **Créer** : tu écris ce que tu veux (« juste un œil géant », « une vache avec une seule corne », « un taureau au corps d'araignée »…), sans rien imposer ni interdire. L'appli dessine d'abord **3 esquisses** en une demi-minute : tu choisis la plus fidèle, et le dos, le profil et la marche sont faits à partir d'elle. Avant de dessiner, l'appli lit ta description et en retient la posture (à quatre pattes, debout, qui flotte, qui rampe, qui nage) et le nombre de pattes : elle te dit ce qu'elle a compris, et le dos et le profil la respectent (une créature qui flotte reste dans les airs, sans pattes inventées). Elle détaille aussi chaque partie avec son nombre et sa place (« trois têtes, chacune sur son cou ») et connaît les traits des monstres et objets classiques : hydre, cerbère, mimique, tyrannœil, chimère, kitsune, golem, liche, armure hantée… Tes nombres et tes couleurs restent prioritaires.
- **Contrôle automatique** : chaque esquisse est regardée par un modèle de vision, qui compte les têtes et vérifie qu'une créature sans pattes n'en a pas. Une esquisse ratée (« 1 tête au lieu de 3 ») est refaite toute seule, deux fois au plus ; sous chaque esquisse, tu vois « ✓ vérifiée » ou ce qui ne va pas. Le profil d'une créature qui flotte, nage ou rampe est contrôlé de la même façon : un profil avec des pattes est écarté et refait.
- **Retouche ciblée** : sur une esquisse, la face, le dos ou le profil, « Retoucher » ouvre l'image. Tu cliques la zone à changer (petite, moyenne, grande, ou toute la créature) et tu écris « ajoute une corne ici » ou « les yeux en rouge » : seule cette partie est redessinée. La retouche devient une nouvelle version, l'ancienne reste avec ◀ ▶, et la marche, le miroir et les attaques suivent.
- **Sprites 64×64** : la réduction garde les petits détails contrastés, les yeux et leurs pupilles ne disparaissent plus dans la peau.
- **Marche** : les pattes de la pose de repos s'animent (un côté puis l'autre de face et de dos, pattes avant et arrière en balancier de profil). La créature reste identique d'une image à l'autre, mêmes pixels, mêmes couleurs. Une créature sans pattes (œil, pieuvre, serpent) ondule sur place ; une créature qui flotte monte et descend doucement.
- **Fiche de bestiaire** : à la fin de la création, une fiche façon Pokédex est écrite toute seule : type, espèce, taille, poids, habitat, description et une petite histoire. Elle s'affiche avec le portrait, dans une police de livre facile à lire. « Réécrire la fiche » en propose une autre.
- **Combat** : la fiche donne une **rareté** (commun, peu commun, rare, épique, légendaire), des **statistiques** (PV, attaque, défense, vitesse), des **faiblesses** et des **résistances** tirées du type. La rareté reste rare : environ une créature sur deux est commune et une sur cinquante légendaire ; une créature plus menaçante monte d'un cran au plus, et plus elle est rare, plus ses statistiques sont hautes.
- **Attaques** : chaque créature a **2 attaques** (griffe, morsure, charge, projectile, souffle, onde ou rayon), avec leur élément et leur puissance. Chacune est animée dans les 4 directions, en 4 images (élan, frappe, impact, retour), avec un effet en pixel art aux couleurs de l'élément. Dans l'aperçu en jeu, les touches 1 et 2 les lancent.
- **Directions** : la planche 4 directions × 3 pas. Chaque image a ses versions (◀ ▶) et chaque direction peut être refaite ; refaire la face refait toute la créature.
- **Sprite Lab** :
  - un éditeur pixel 64×64 (crayon, gomme, pipette, seau, annuler / refaire) ;
  - la palette commune aux 12 images, le contour ;
  - un aperçu en jeu : ta créature marche sur l'herbe avec les flèches du clavier.
- **Export** : chaque créature exportée va dans le dossier `Exports` (bouton dans la Bibliothèque), un sous-dossier par créature : la planche PNG (3 colonnes × 4 lignes de 64×64), son JSON (directions, images, point d'ancrage aux pieds, ordre de l'animation, fiche) le portrait en grand, et pour chaque attaque la planche du corps, celle de l'effet et leur décalage dans le JSON.
- **Bibliothèque** : toutes tes créatures, avec recherche. Une créature supprimée part dans une corbeille, elle n'est pas effacée.

Les créatures sont rangées dans `Documents\NeoBestiary Studio`, les exports dans `Documents\NeoBestiary Studio\Exports`.

## Ce qu'il faut

- Windows et une carte graphique **NVIDIA avec 8 Go de mémoire vidéo** ou plus.
- **ComfyUI portable** ([github.com/comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI), page Releases), décompressé n'importe où. Au premier lancement, l'appli le cherche et, si besoin, te demande son dossier.
- Les modèles de dessin, que l'appli propose d'installer elle-même (licences libres, depuis Hugging Face, environ 15 Go en tout) :
  - **FLUX.2 klein 4B** (le dessin) ;
  - l'encodeur **Qwen3 4B** (il comprend le français) ;
  - **BiRefNet** (détourage : ni fond ni ombre au sol).
- Pour l'inspiration et les fiches : **Ollama** ([ollama.com](https://ollama.com)) avec un modèle de texte, par exemple `ollama pull mistral-nemo` (environ 7 Go, très bon en français). Pour le contrôle automatique, un modèle qui voit les images : `ollama pull gemma3:4b` (environ 3 Go). Sans Ollama, tout le reste fonctionne ; seules l'inspiration, les fiches et le contrôle attendent, et la posture est devinée par mots-clés.

ComfyUI démarre tout seul à la première invocation et s'arrête quand tu fermes NeoBase. Si tu as déjà lancé ton propre ComfyUI, l'appli l'utilise et ne l'arrête pas.

## Combien de temps

Sur une RTX 4060 : une demi-minute pour les 3 esquisses, puis environ 2 minutes pour le dos, le profil (deux essais chacun, le meilleur est gardé automatiquement), la marche et la fiche. Le contrôle ajoute une dizaine de secondes, plus le temps d'une esquisse refaite quand il en faut une. Une idée d'inspiration prend une dizaine de secondes (une minute la première fois, le temps de charger le modèle de texte).

## Permissions

L'appli demande l'**accès complet** : elle lance le moteur de dessin (Python, livré dans le plugin), ComfyUI et parle à Ollama sur ton PC, et enregistre tes créatures dans tes Documents. Rien ne part sur Internet, sauf le téléchargement des modèles si tu le demandes.
