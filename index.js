// NeoBestiary Studio : une description en français -> une créature pixel art 64x64, 4 directions, marche en 3 images.
// La page parle au moteur (main.js -> engine/nb_server.py) ; tout le dessin de l'interface est dans ui/ (sprites faits main).
const ID = 'neodex.bestiarystudio', U = 'neoplugin://' + ID + '/';
const DIRS = ['bas', 'gauche', 'droite', 'haut'], FR = ['pas1', 'mi1', 'repos', 'mi2', 'pas2'], CYCLE = ['repos', 'mi1', 'pas1', 'mi1', 'repos', 'mi2', 'pas2', 'mi2'];
const FRAME_NAME = { pas1: 'pas 1', mi1: 'demi-pas 1', repos: 'repos', mi2: 'demi-pas 2', pas2: 'pas 2' };
const ARROW = { bas: '↓', gauche: '←', droite: '→', haut: '↑' };
const ic = n => `<i class="ic" style="background-image:url(${U}ui/i_${n}.png)"></i>`;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const viewKey = (d, f) => f === 'repos' ? d : d + '_' + f;

const HTML = `<link rel="stylesheet" href="${U}ui/studio.css">
<div class="nbs">
  <i class="dust" style="left:8%;top:95%;animation-delay:-3s,0s"></i><i class="dust" style="left:37%;top:100%;animation-delay:-9s,-.4s"></i>
  <i class="dust" style="left:71%;top:97%;animation-delay:-1s,-.8s"></i><i class="dust" style="left:90%;top:99%;animation-delay:-6s,-.2s"></i>
  <header class="nbs-head">
    <i class="emb"></i>
    <h1>NeoBestiary <b>Studio</b></h1>
    <div class="nbs-status off" id="st"><i></i><span>Réveil du grimoire…</span></div>
  </header>
  <nav class="nbs-tabs">
    <button class="nbs-tab on" data-p="creer" title="Créer">${ic('creer')}Créer</button>
    <button class="nbs-tab" data-p="dirs" title="Directions">${ic('directions')}Directions</button>
    <button class="nbs-tab" data-p="lab" title="Sprite Lab">${ic('lab')}Sprite Lab</button>
    <button class="nbs-tab" data-p="lib" title="Bibliothèque">${ic('biblio')}Bibliothèque</button>
    <button class="nbs-tab" data-p="eq" title="Équilibre">${ic('balance')}Équilibre</button>
  </nav>
  <main class="nbs-frame">
    <section class="nbs-page" id="p-setup">
      <div class="nbs-title">Préparer le grimoire</div>
      <div id="setupBody"></div>
    </section>

    <section class="nbs-page on" id="p-creer">
      <div class="nbs-row nbs-themes nbs-kinds" id="kinds">
        <button class="nbs-btn dark on" data-k="creature">${ic('creer')}Créature</button>
        <button class="nbs-btn dark" data-k="objet">${ic('objet')}Objet</button>
        <button class="nbs-btn dark" data-k="attaque">${ic('attaque')}Attaque</button>
        <button class="nbs-btn dark" data-k="musique">${ic('musique')}Musique</button>
        <span class="nbs-hint" id="kindBusy"></span>
      </div>
      <div class="nbs-cols" id="mkCreature">
        <div class="grow">
          <div class="nbs-title">Inspiration</div>
          <div class="nbs-row nbs-themes" id="themes">
            <button class="nbs-btn dark sm on" data-t="melange">Mélange</button>
            <button class="nbs-btn dark sm" data-t="lovecraft">Lovecraft</button>
            <button class="nbs-btn dark sm" data-t="animaux">Animaux</button>
            <button class="nbs-btn dark sm" data-t="monstres">Monstres</button>
            <button class="nbs-btn dark sm" data-t="folklore">Folklore</button>
            <button class="nbs-btn sm" id="inspire" style="margin-left:auto">${ic('etoile')}Inspire-moi</button>
          </div>
          <span class="nbs-hint" id="inspireMsg"></span>
          <div class="nbs-row nbs-crtype"><span class="nbs-hint">Type</span><div class="nbs-parch"><select id="crType" title="Auto : un type tiré au sort, les types rares du bestiaire d'abord ; l'idée et le dessin sont faits autour"></select></div></div>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Nom</div>
          <div class="nbs-parch"><input type="text" id="name" maxlength="60" placeholder="Ophidrache, Chien de feu…" spellcheck="false"></div>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Décris ta créature</div>
          <div class="nbs-parch"><textarea id="desc" rows="5" placeholder="une pieuvre géante avec un seul grand œil jaune, six tentacules violets…"></textarea></div>
          <div class="nbs-sep"></div>
          <div class="nbs-row">
            <button class="nbs-btn go big" id="go">${ic('play')}Invoquer</button>
            <button class="nbs-btn" id="auto" title="Invente, dessine et finit des créatures l'une après l'autre, jusqu'à ce que tu rappuies">${ic('refaire')}Invocation en boucle</button>
            <button class="nbs-btn red" id="cancel" hidden>Arrêter</button>
            <button class="nbs-btn dark sq" id="dice" title="Nouvelle graine">${ic('de')}</button>
            <span class="nbs-hint" id="seedTxt"></span>
          </div>
          <div class="nbs-sep"></div>
          <div class="nbs-bar"><i id="bar" style="width:0"></i></div>
          <div class="nbs-step" id="step">&nbsp;</div>
          
          <div id="sketches" hidden>
            <div class="nbs-sep"></div>
            <div class="nbs-title">Choisis ton design</div>
            <div class="nbs-row nbs-sketches" id="sketchRow"></div>
            <div class="nbs-hint" id="understood"></div>
          </div>
        </div>
        <div>
          <div class="nbs-title" id="liveTitle">Grimoire vivant</div>
          <div class="nbs-grid4" id="stages"></div>
        </div>
      </div>
      <div class="nbs-cols" id="mkOther" hidden>
        <div class="grow">
          <div class="nbs-title">Nom</div>
          <div class="nbs-parch"><input type="text" id="mkName" maxlength="60" spellcheck="false"></div>
          <div class="nbs-sep"></div>
          <div class="nbs-title" id="mkDescT">Décris</div>
          <div class="nbs-parch"><textarea id="mkDesc" rows="4"></textarea></div>
          <div class="nbs-sep"></div>
          <div class="nbs-row nbs-mkopts" data-only="objet">
            <span>Catégorie</span><div class="nbs-parch"><select id="mkCat"></select></div>
            <span>Rareté</span><div class="nbs-parch"><select id="mkRar"></select></div>
          </div>
          <div class="nbs-row nbs-mkopts" data-only="attaque">
            <span>Élément</span><div class="nbs-parch"><select id="mkElem"></select></div>
            <span>Geste</span><div class="nbs-parch"><select id="mkGenre"></select></div>
          </div>
          <div data-only="musique">
            <div class="nbs-title">Paroles <span class="nbs-hint">(vide : instrumental)</span></div>
            <div class="nbs-parch"><textarea id="mkLyrics" rows="3" placeholder="[couplet]&#10;…"></textarea></div>
            <div class="nbs-row nbs-mkopts" style="margin-top:10px">
              <span>Durée</span><div class="nbs-parch"><select id="mkDur"><option value="30">30 s</option><option value="60" selected>1 min</option><option value="120">2 min</option><option value="180">3 min</option></select></div>
              <span>Tempo</span><div class="nbs-parch"><select id="mkTempo"><option value="lent">lent</option><option value="moyen" selected>moyen</option><option value="rapide">rapide</option></select></div>
              <span>Ambiance</span><div class="nbs-parch"><select id="mkMood"><option value="joyeuse">lumineuse</option><option value="sombre">sombre</option></select></div>
            </div>
          </div>
          <div class="nbs-sep"></div>
          <div class="nbs-row">
            <button class="nbs-btn go big" id="mkGo">${ic('play')}Créer</button>
            <button class="nbs-btn red" id="mkCancel" hidden>Arrêter</button>
            <span class="nbs-hint" id="mkInfo"></span>
          </div>
          <div class="nbs-sep"></div>
          <div class="nbs-bar"><i id="mkBar" style="width:0"></i></div>
          <div class="nbs-step" id="mkStep">&nbsp;</div>
        </div>
        <div>
          <div class="nbs-title" id="mkPrevT">Aperçu</div>
          <div class="nbs-well nbs-mkbox" id="mkPrev"><span class="nbs-hint">Rien pour l'instant.</span></div>
          <div class="nbs-mkinfo" id="mkPrevInfo"></div>
        </div>
      </div>
    </section>

    <section class="nbs-page" id="p-dirs">
      <div class="nbs-title" id="dirTitle">Planche 4 directions × 3 pas · 64×64</div>
      <div class="nbs-sheet" id="sheet"></div>
      <div class="nbs-sep"></div>
      <div class="nbs-row">
        <button class="nbs-btn dark" id="toLab">${ic('oeil')}Voir en jeu</button>
        <span class="nbs-hint" id="dirHint"></span>
      </div>
      <div class="nbs-sep"></div>
      <div class="nbs-title">Variantes de couleur</div>
      <div class="nbs-row nbs-themes" id="forms"></div>
      <div class="nbs-row" style="margin-top:8px">
        <div class="nbs-parch"><select id="varSel"></select></div>
        <button class="nbs-btn dark" id="varAdd">${ic('etoile')}Créer la variante</button>
        <span class="nbs-hint" id="varMsg"></span>
      </div>
      <div class="nbs-sep"></div>
      <div class="nbs-title">Attaques</div>
      <div id="attacks"></div>
      <div class="nbs-sep"></div>
      <div class="nbs-title">Animations de combat</div>
      <div id="anims"></div>
      <div class="nbs-sep"></div>
      <div class="nbs-title">Fiche du bestiaire</div>
      <div class="nbs-parch nbs-fiche" id="fiche"></div>
      <div class="nbs-row" style="margin-top:8px">
        <button class="nbs-btn dark" id="relore">${ic('refaire')}Réécrire la fiche</button>
        <span class="nbs-hint" id="loreMsg"></span>
      </div>
      <div class="nbs-row" style="margin-top:8px">
        <button class="nbs-btn dark" id="illuRedo">${ic('crayon')}Refaire l'image</button>
        <button class="nbs-btn dark sq" id="iPrev" title="Image précédente">${ic('prev')}</button>
        <span class="nbs-num" id="iVer">—</span>
        <button class="nbs-btn dark sq" id="iNext" title="Image suivante">${ic('next')}</button>
        <button class="nbs-btn dark" id="illuCut">${ic('gomme')}Détourage</button>
        <span class="nbs-hint" id="iNote"></span>
      </div>
      <div class="nbs-row" style="margin-top:8px">
        <button class="nbs-btn dark" id="portraitRedo">${ic('crayon')}Refaire le portrait</button>
        <button class="nbs-btn dark sq" id="pPrev" title="Portrait précédent">${ic('prev')}</button>
        <span class="nbs-num" id="pVer">—</span>
        <button class="nbs-btn dark sq" id="pNext" title="Portrait suivant">${ic('next')}</button>
        <button class="nbs-btn dark" id="portraitCut">${ic('gomme')}Détourage</button>
      </div>
    </section>

    <section class="nbs-page" id="p-lab">
      <div class="nbs-cols">
        <div>
          <div class="nbs-title">Outils</div>
          <div class="nbs-tools" id="tools">
            <button class="nbs-btn dark sq on" data-t="pen" title="Crayon">${ic('crayon')}</button>
            <button class="nbs-btn dark sq" data-t="erase" title="Gomme">${ic('gomme')}</button>
            <button class="nbs-btn dark sq" data-t="pick" title="Pipette">${ic('pipette')}</button>
            <button class="nbs-btn dark sq" data-t="fill" title="Seau">${ic('seau')}</button>
            <button class="nbs-btn dark sq" id="undo" title="Annuler (Ctrl+Z)">${ic('undo')}</button>
            <button class="nbs-btn dark sq" id="redo" title="Refaire (Ctrl+Y)">${ic('redo')}</button>
            <button class="nbs-btn dark sq on" id="gridBtn" title="Grille">${ic('grille')}</button>
            <button class="nbs-btn dark sq" id="resetEd" title="Oublier les retouches">${ic('refaire')}</button>
          </div>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Palette</div>
          <div class="nbs-swatches" id="sw"></div>
          <div class="nbs-row" style="margin-top:10px"><span class="nbs-cur" id="cur"></span><input type="color" id="colorIn" title="Autre couleur"></div>
        </div>
        <div>
          <div class="nbs-title" id="fLabel">Image</div>
          <div class="nbs-canvas grid" id="cv"><canvas width="64" height="64" id="ed"></canvas></div>
          <div class="nbs-row" style="margin-top:14px">
            <button class="nbs-btn dark sq" id="fprev">${ic('prev')}</button>
            <span class="nbs-num" id="fnum">1 / 20</span>
            <button class="nbs-btn dark sq" id="fnext">${ic('next')}</button>
          </div>
        </div>
        <div class="grow">
          <div class="nbs-title">Aperçu en jeu</div>
          <div class="nbs-world" id="world"><div class="road"></div><img class="hero" id="hero" alt=""><img class="fx" id="heroFx" alt=""><canvas class="sig" id="heroSig" width="1" height="1"></canvas></div>
          <div class="nbs-keys" style="margin-top:8px">Flèches : marcher · 1 à 4 : attaquer</div>
          <div class="nbs-sep"></div>
          <div class="nbs-title">Réglages</div>
          <div class="nbs-opt" data-o="outline"><span class="nbs-check"></span>Contour sombre</div>
          <div class="nbs-opt" data-o="lock_palette" style="margin-top:6px"><span class="nbs-check"></span>Palette verrouillée sur les 20 images</div>
          <div class="nbs-opt" data-o="mirror" style="margin-top:6px"><span class="nbs-check"></span>Droite = miroir de gauche</div>
          <div class="nbs-opt" style="margin-top:6px">Couleurs <button class="nbs-btn dark sq" id="cminus">-</button><span class="nbs-num" id="cnum">24</span><button class="nbs-btn dark sq" id="cplus">+</button></div>
          <div class="nbs-sep"></div>
          <div class="nbs-row">
            <button class="nbs-btn go" id="exp">${ic('exporter')}Exporter PNG + JSON</button>
            <button class="nbs-btn dark" id="expTo" title="Exporter dans un autre dossier">${ic('dossier')}Ailleurs…</button>
          </div>
          <div class="nbs-hint" id="expMsg" style="margin-top:6px"></div>
        </div>
      </div>
    </section>

    <section class="nbs-page" id="p-lib">
      <div class="nbs-row nbs-themes" id="libKinds" style="margin-bottom:10px">
        <button class="nbs-btn dark sm on" data-k="creature">${ic('creer')}Créatures</button>
        <button class="nbs-btn dark sm" data-k="objet">${ic('objet')}Objets</button>
        <button class="nbs-btn dark sm" data-k="attaque">${ic('attaque')}Attaques</button>
        <button class="nbs-btn dark sm" data-k="musique">${ic('musique')}Musiques</button>
        <button class="nbs-btn dark sm" id="favOnly" style="margin-left:auto" title="Seulement les favoris">${ic('etoile_vide')}Favoris</button>
        <div class="nbs-parch nbs-sort"><select id="libSort" title="Trier">
          <option value="recent">Récents</option><option value="nom">Nom</option><option value="rarete">Rareté</option><option value="type">Type</option>
        </select></div>
      </div>
      <div class="nbs-row" style="margin-bottom:12px">
        <div class="nbs-parch" style="flex:1"><input type="text" id="q" placeholder="Chercher…" spellcheck="false"></div>
        <button class="nbs-btn dark" id="fuseBtn" title="Inventer l'hybride de deux créatures">${ic('etoile')}Fusionner</button>
        <button class="nbs-btn dark" id="openExports" title="Les créatures exportées, prêtes pour le bestiaire">${ic('dossier')}Exports</button>
      </div>
      <div class="nbs-row nbs-fusebar" id="fuseBar" hidden>
        <span class="nbs-hint" id="fuseMsg">Choisis deux créatures finies.</span>
        <button class="nbs-btn go" id="fuseGo" disabled>${ic('play')}Fusionner ces deux</button>
        <button class="nbs-btn dark" id="fuseStop">Annuler</button>
      </div>
      <div class="nbs-lib" id="lib"></div>
    </section>

    <section class="nbs-page" id="p-eq">
      <div id="eq"><div class="nbs-hint">Lecture du bestiaire…</div></div>
    </section>
  </main>
  <div class="nbs-modal" id="cutout" hidden>
    <div class="nbs-frame nbs-modal-box">
      <div class="nbs-title" id="ctTitle">Détourage</div>
      <div class="nbs-rt-cols">
        <div class="nbs-rt-pic nbs-well nbs-ct-pic" id="ctPic"><img id="ctImg" alt=""><canvas id="ctMask"></canvas></div>
        <div class="nbs-rt-side">
          <div class="nbs-hint">Rouge : à effacer · vert : à restaurer.</div>
          <div class="nbs-row nbs-themes" id="ctTool" style="margin-top:8px">
            <button class="nbs-btn dark sm on" data-t="erase">Gomme</button>
            <button class="nbs-btn dark sm" data-t="keep">Restaurer</button>
          </div>
          <div class="nbs-row nbs-themes" id="ctSize" style="margin-top:8px">
            <button class="nbs-btn dark sm" data-s=".012">Fin</button>
            <button class="nbs-btn dark sm on" data-s=".03">Moyen</button>
            <button class="nbs-btn dark sm" data-s=".07">Large</button>
          </div>
          <div class="nbs-row" style="margin-top:12px">
            <button class="nbs-btn go" id="ctGo">${ic('ok')}Valider</button>
            <button class="nbs-btn dark" id="ctClear">${ic('refaire')}Effacer les traits</button>
            <button class="nbs-btn dark" id="ctClose">Annuler</button>
          </div>
          <div class="nbs-hint" id="ctMsg" style="margin-top:8px"></div>
        </div>
      </div>
    </div>
  </div>
  <div class="nbs-modal" id="retouch" hidden>
    <div class="nbs-frame nbs-modal-box">
      <div class="nbs-title" id="rtTitle">Retouche</div>
      <div class="nbs-rt-cols">
        <div class="nbs-rt-pic nbs-well" id="rtPic"><img id="rtImg" alt=""><i id="rtZone"></i></div>
        <div class="nbs-rt-side">
          <div class="nbs-hint">Clique la zone à changer.</div>
          <div class="nbs-row nbs-themes" id="rtSize" style="margin-top:8px">
            <button class="nbs-btn dark sm" data-r=".06">Petite zone</button>
            <button class="nbs-btn dark sm on" data-r=".1">Moyenne</button>
            <button class="nbs-btn dark sm" data-r=".16">Grande</button>
            <button class="nbs-btn dark sm" data-r="0">Toute la créature</button>
          </div>
          <div class="nbs-title" style="margin-top:12px">Que faut-il changer ?</div>
          <div class="nbs-parch"><input type="text" id="rtText" maxlength="160" placeholder="ajoute une corne ici, les yeux en rouge…" spellcheck="false"></div>
          <div class="nbs-row" style="margin-top:12px">
            <button class="nbs-btn go" id="rtGo">${ic('crayon')}Retoucher</button>
            <button class="nbs-btn dark" id="rtClose">Annuler</button>
          </div>
          <div class="nbs-hint" id="rtMsg" style="margin-top:8px"></div>
        </div>
      </div>
    </div>
  </div>
</div>`;

export default async function (ctx) {
  const view = ctx.view;
  if (!ctx.host) { view.textContent = "Ce plugin doit être approuvé par NeoDex pour s'ouvrir."; return; }
  view.innerHTML = HTML;
  const $ = s => view.querySelector(s), $$ = s => [...view.querySelectorAll(s)];
  const call = (n, ...a) => ctx.neo.pluginMain(ID, n, ...a);
  const get = r => call('get', r), post = (r, b) => call('post', r, b || {});
  const S = { tab: 'creer', cr: null, stamp: 0, seed: Math.floor(Math.random() * 1e6), sel: 'bas_repos', frame: 1, alive: true };
  const src = p => p && S.cr ? `${U}lib/${encodeURIComponent(S.cr.slug)}/${p}?v=${S.stamp}` : '';
  const sprite = (d, f) => S.cr?.sprites?.[d + '_' + f] ? src(S.cr.sprites[d + '_' + f]) : '';
  const say = (msg, bad) => { $('#step').textContent = msg || ' '; $('#step').style.color = bad ? 'var(--red)' : ''; };

  // ------------------------------------------------------------ onglets
  const show = p => {
    S.tab = p;
    $$('.nbs-tab').forEach(t => t.classList.toggle('on', t.dataset.p === p));
    $$('.nbs-page').forEach(x => x.classList.toggle('on', x.id === 'p-' + p));
    if (p === 'lib') loadLib();
    if (p === 'eq') loadBalance();
    if (p === 'lab') loadFrame();
  };
  $$('.nbs-tab').forEach(t => t.onclick = () => show(t.dataset.p));

  // ------------------------------------------------------------ préparation (ComfyUI, modèles)
  async function setup() {
    const body = $('#setupBody');
    const s = await call('setup');
    if (!s.comfyRoot) {
      show('setup');
      body.innerHTML = `<p>NeoBestiary Studio dessine avec <b>ComfyUI portable</b> (carte NVIDIA, 8 Go de mémoire vidéo).</p>
        <p class="nbs-hint">Installe la version portable depuis github.com/comfyanonymous/ComfyUI (Releases), décompresse-la, puis montre-moi son dossier.</p>
        <div class="nbs-row"><button class="nbs-btn go" id="pick">${ic('dossier')}Choisir le dossier de ComfyUI</button><span class="nbs-hint" id="pickMsg"></span></div>`;
      $('#pick').onclick = async () => {
        const r = await call('pickComfy');
        if (r.ok) setup(); else $('#pickMsg').textContent = "Ce dossier n'est pas ComfyUI portable (il doit contenir python_embeded).";
      };
      return false;
    }
    let st = await get('/status');  // le moteur lance tout seul le téléchargement de ce qui manque
    status(st);
    if (st.missing.length) {
      show('setup');
      const gb = st.missing.reduce((a, m) => a + m.gb, 0);
      body.innerHTML = `<p>Installation automatique des modèles du grimoire (locaux, licences libres, depuis Hugging Face) :</p>
        <div class="nbs-parch">${st.missing.map(m => `<div>${esc(m.name)} <span class="nbs-hint">· ${m.gb} Go</span></div>`).join('')}</div>
        <div class="nbs-hint">${gb.toFixed(1)} Go pour le dessin, puis le modèle de musique (sans bloquer les créations).</div>
        <div class="nbs-sep"></div><div class="nbs-bar"><i id="ibar" style="width:0"></i></div><div class="nbs-step" id="istep">&nbsp;</div>
        <div class="nbs-row" id="iretry" hidden><button class="nbs-btn go" id="inst">${ic('refaire')}Réessayer</button></div>`;
      $('#inst').onclick = () => { $('#iretry').hidden = true; post('/install-models').then(() => setup()).catch(e => { $('#istep').textContent = e.message; }); };
      while (S.alive && st.missing.length) {
        const i = st.install;
        $('#ibar').style.width = Math.round(i.progress * 100) + '%';
        $('#istep').textContent = i.error || (i.running ? `${i.step} · ${Math.round(i.progress * 100)} %` : 'Préparation…');
        if (i.error && !i.running) { $('#iretry').hidden = false; return false; }
        await new Promise(r => setTimeout(r, 1500));
        st = await get('/status');
      }
    }
    if (S.tab === 'setup') show('creer');
    return true;
  }
  function status(st) {
    $('#st').classList.toggle('off', st.comfy !== 'prêt');
    $('#st span').textContent = st.comfy === 'prêt' ? `ComfyUI prêt · ${st.model}` : st.comfy === 'arrêté' ? 'ComfyUI démarre à la première invocation' : 'ComfyUI introuvable';
  }

  // ------------------------------------------------------------ tâches (création, refaire, installation)
  async function follow(onTick) {
    for (;;) {
      const j = await get('/job');
      onTick(j);
      if (j.done || !S.alive) return j;
      await new Promise(r => setTimeout(r, 600));
    }
  }
  // une seule création à la fois (créature, objet, attaque ou musique) : tous les boutons Créer attendent la fin
  const JOB_NAME = { 'make-objet': 'un objet', 'make-attaque': 'une attaque', 'make-musique': 'une musique' };
  const busy = (on, kind) => {
    $('#go').hidden = on; $('#cancel').hidden = !on; $$('.nbs-redo').forEach(b => b.disabled = on);
    $('#mkGo').disabled = on; $('#mkCancel').hidden = !on; $('#auto').disabled = on && !S.auto;
    $('#kindBusy').textContent = on ? `Création en cours : ${JOB_NAME[kind] || 'une créature'} (une seule à la fois)` : '';
  };
  async function runJob(start, out = { bar: '#bar', say }) {
    busy(true);
    try { await start(); } catch (e) { busy(false); out.say(e.message, true); return null; }
    const j = await follow(j => {
      busy(true, j.kind);
      $(out.bar).style.width = Math.round(j.progress * 100) + '%';
      out.say(j.step === 'Préparation' ? 'Préparation… (ComfyUI démarre, ~1 min la première fois)' : `${j.step}… ${Math.round(j.progress * 100)} %`);
    });
    busy(false);
    if (j.error) { out.say(j.error, true); return null; }
    if (j.kind.startsWith('make-')) { out.say({ 'make-objet': 'Objet créé ✓', 'make-attaque': 'Attaque créée ✓', 'make-musique': 'Musique composée ✓' }[j.kind]); return j; }
    say(j.kind === 'sketch' ? 'Choisis ton design ↓' : j.kind === 'edit' ? 'Retouche faite ✓ (nouvelle version)'
      : j.kind === 'portrait' ? 'Portrait de combat prêt ✓ (onglet Directions, fiche)'
      : j.kind === 'illustration' ? 'Image du bestiaire prête ✓ (onglet Directions, fiche)' : 'Créature invoquée ✓');
    get('/status').then(status).catch(() => {});
    if (j.slug) await open(j.slug);
    return j;
  }

  // ------------------------------------------------------------ créer
  const seedTxt = () => $('#seedTxt').textContent = 'graine ' + S.seed;
  seedTxt();
  $('#dice').onclick = () => { S.seed = Math.floor(Math.random() * 1e6); seedTxt(); };
  $('#go').onclick = () => {
    const description = $('#desc').value.trim();
    if (!description) { say('Décris ta créature d\'abord.', true); $('#desc').focus(); return; }
    runJob(() => post('/create', { name: $('#name').value.trim() || description.split(/[,.]/)[0].slice(0, 40), description, seed: S.seed, type: $('#crType').value || S.idType || '' }))
      .then(j => { if (j) { S.seed = Math.floor(Math.random() * 1e6); S.idType = ''; seedTxt(); } });
  };
  $('#cancel').onclick = () => post('/cancel');

  // ------------------------------------------------------------ créer : objet, attaque, musique
  const MK = {
    objet: { desc: "Décris l'objet", ph: "une montre à gousset en or, cadran fêlé, aiguilles qui brillent…", name: 'Montre du temps perdu…' },
    attaque: { desc: "Décris l'effet de l'attaque", ph: "une lance de glace bleue qui tourbillonne puis éclate en éclats de givre…", name: 'Lance de givre…' },
    musique: { desc: 'Style de la musique', ph: "chiptune joyeuse pour un village, flûte et percussions 8 bits, ambiance d'aventure…", name: 'Thème du village…' },
  };
  const CATS = ['arme', 'armure', 'bouclier', 'potion', 'nourriture', 'outil', 'bijou', 'trésor', 'clé', 'livre', 'objet du quotidien', 'ingrédient'];
  const ELEMS = ['feu', 'eau', 'plante', 'vent', 'roche', 'glace', 'foudre', 'lumière', 'ombre', 'esprit', 'acier', 'poison'];
  const opts = (l, lab = x => x) => l.map(x => `<option value="${esc(x)}">${esc(lab(x))}</option>`).join('');
  const fillOpts = () => {  // au premier usage : RAR et GENRE sont déclarés plus bas
    if ($('#mkCat').options.length) return;
    $('#mkCat').innerHTML = opts(CATS); $('#mkRar').innerHTML = opts(RAR.slice(0, 5));
    $('#mkElem').innerHTML = opts(ELEMS); $('#mkGenre').innerHTML = opts(Object.keys(GENRE), g => GENRE[g]); $('#mkGenre').value = 'projectile';
  };
  const mkSay = (msg, bad) => { $('#mkStep').textContent = msg || ' '; $('#mkStep').style.color = bad ? 'var(--red)' : ''; };
  const mkUrl = (kind, it, f) => `${U}mk/${{ objet: 'objets', attaque: 'attaques', musique: 'musiques' }[kind]}/${it.slug.split('/').map(encodeURIComponent).join('/')}${f}?v=${it.updated || 0}`;
  S.kind = 'creature';
  function setKind(k) {
    S.kind = k;
    $$('#kinds [data-k]').forEach(b => b.classList.toggle('on', b.dataset.k === k));
    $('#mkCreature').hidden = k !== 'creature'; $('#mkOther').hidden = k === 'creature';
    if (k === 'creature') return;
    fillOpts();
    $$('#mkOther [data-only]').forEach(x => x.hidden = x.dataset.only !== k);
    $('#mkDescT').textContent = MK[k].desc; $('#mkDesc').placeholder = MK[k].ph; $('#mkName').placeholder = MK[k].name;
    if (S.item?.kind !== k) { S.item = null; showItem(null); }
    $('#mkInfo').textContent = '';
    $('#mkGo').disabled = !!$('#kindBusy').textContent;  // la musique a pu le bloquer pendant l'installation de son modèle
    if (k === 'musique') musicState();
  }
  $$('#kinds [data-k]').forEach(b => b.onclick = () => setKind(b.dataset.k));
  async function musicState() {  // le modèle de musique s'installe tout seul en arrière-plan : on montre où il en est
    if (S.kind !== 'musique' || !S.alive) return;
    const st = await get('/status').catch(() => null);
    if (!st) return;
    const i = st.install, wait = st.missing_music?.length;
    $('#mkInfo').textContent = !wait ? '' : i.running ? `Modèle de musique : installation ${Math.round(i.progress * 100)} %` : (i.error || 'Modèle de musique pas encore installé');
    if (wait && !$('#kindBusy').textContent) $('#mkGo').disabled = true;
    else if (!$('#kindBusy').textContent) $('#mkGo').disabled = false;
    if (wait) setTimeout(musicState, 2000);
  }
  $('#mkGo').onclick = () => {
    const k = S.kind, description = $('#mkDesc').value.trim();
    if (!description) { mkSay('Décris ce que tu veux créer d\'abord.', true); $('#mkDesc').focus(); return; }
    const body = { kind: k, nom: $('#mkName').value.trim(), description, seed: Math.floor(Math.random() * 1e6),
      categorie: $('#mkCat').value, rarete: $('#mkRar').value, element: $('#mkElem').value, genre: $('#mkGenre').value,
      paroles: $('#mkLyrics').value, duree: +$('#mkDur').value, tempo: $('#mkTempo').value, ambiance: $('#mkMood').value };
    runJob(() => post('/make', body), { bar: '#mkBar', say: mkSay }).then(async j => {
      if (!j?.slug) return;
      const [kind, ...rest] = j.slug.split('/');
      showItem(await get(`/item?kind=${kind}&slug=${encodeURIComponent(rest.join('/'))}`));
    });
  };
  $('#mkCancel').onclick = () => post('/cancel');
  function showItem(it) {
    S.item = it;
    const box = $('#mkPrev'), info = $('#mkPrevInfo');
    box.querySelector('audio')?.pause();  // la musique d'avant s'arrête
    if (!it) { box.innerHTML = '<span class="nbs-hint">Rien pour l\'instant.</span>'; info.innerHTML = ''; return; }
    $('#mkPrevT').textContent = it.nom;
    const chips = [];
    if (it.kind === 'objet') {
      box.innerHTML = `<img class="nbs-mkicon" src="${mkUrl('objet', it, `/icone_${it.version || 0}.png`)}" alt="">` + (it.versions > 1
        ? `<div class="nbs-row nbs-mkver"><button class="nbs-btn dark sq" data-d="-1">${ic('prev')}</button><span>version ${(it.version || 0) + 1}/${it.versions}</span><button class="nbs-btn dark sq" data-d="1">${ic('next')}</button></div>` : '');
      box.querySelectorAll('[data-d]').forEach(b => b.onclick = async () => showItem(await post('/item-choose', { kind: 'objet', slug: it.slug, delta: +b.dataset.d })));
      chips.push(`<span class="nbs-rare r${RAR.indexOf(it.rarete)}">${esc(it.rarete)}</span>`, `<span class="nbs-chip">${esc(it.categorie)}</span>`);
    } else if (it.kind === 'attaque') {
      box.innerHTML = '<canvas class="nbs-sig-cv nbs-mk-cv" width="320" height="180"></canvas>';
      chips.push(atkRar(it.rarete), `<span class="nbs-chip">${esc(it.element)}</span>`, `<span class="nbs-chip">${esc(GENRE[it.genre] || it.genre)}</span>`);
      if (it.mecanique) chips.push(`<div class="nbs-hint">${esc(it.mecanique)}</div>`);
      if (it.source === 'catalogue') get('/catalog-sheet?id=' + encodeURIComponent(it.id)).then(() => S.item === it && mkLoop()).catch(() => {});  // la planche se fait au 1er clic
      else mkLoop();
      if (it.source === 'signature') chips.unshift(`<span class="nbs-chip">signature ${it.creature === 'neome' ? 'NeoMe' : esc(it.creature)}</span>`);
    } else {
      box.innerHTML = `<div class="nbs-mkdisc">${ic('musique')}</div><audio src="${mkUrl('musique', it, '/musique.mp3')}"></audio>
        <div class="nbs-row nbs-mkplay"><button class="nbs-btn dark sq">${ic('play')}</button><div class="nbs-bar"><i style="width:0"></i></div><span>0:00</span></div>`;
      const a = box.querySelector('audio'), b = box.querySelector('.nbs-mkplay button'), bar = box.querySelector('.nbs-mkplay .nbs-bar');
      const mmss = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
      b.onclick = () => a.paused ? a.play() : a.pause();
      a.onplay = a.onpause = () => b.innerHTML = ic(a.paused ? 'play' : 'pause');
      a.ontimeupdate = () => { bar.firstChild.style.width = (100 * a.currentTime / (a.duration || 1)) + '%'; box.querySelector('.nbs-mkplay span').textContent = mmss(a.currentTime) + ' / ' + mmss(a.duration || 0); };
      bar.onclick = e => { if (a.duration) a.currentTime = a.duration * e.offsetX / bar.clientWidth; };
      chips.push(`<span class="nbs-chip">${Math.round(it.duree)} s</span>`, `<span class="nbs-chip">${esc(it.tempo)}</span>`, `<span class="nbs-chip">${esc(it.ambiance === 'sombre' ? 'sombre' : 'lumineuse')}</span>`);
    }
    info.innerHTML = `<div class="nbs-row nbs-themes">${chips.join('')}</div><div class="nbs-hint">${esc(it.description || '')}</div>`;
  }
  function mkLoop() {  // l'attaque créée, rejouée en boucle avec sa mise en scène (comme NeoMe dans Directions)
    if (S.mkRun) return; S.mkRun = true;
    const step = now => {
      const cv = $('.nbs-mk-cv'), it = S.item;
      if (!cv || !view.isConnected || it?.kind !== 'attaque') { S.mkRun = false; return; }
      const sig = it.source === 'signature', show = sig ? SIG_SHOW[it.visuel] : it.show;  // une signature : sa planche et sa mise en scène de l'Arène
      if (S.tab === 'creer') sigDraw(cv, now % show.len, { show, sheet: sig ? `${U}lib/${encodeURIComponent(it.creature)}/signature/${it.visuel}.png` : mkUrl('attaque', it, it.source === 'catalogue' ? '_planche.png' : '/planche.png'), X: [96, 236], ground: 124 });
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  // ------------------------------------------------------------ invocation en boucle : rappuyer l'arrête après la créature en cours
  $('#auto').onclick = async () => {
    const b = $('#auto');
    if (S.auto) {
      S.auto = 'stop';
      await post('/auto-stop').catch(() => {});
      b.disabled = true; b.lastChild.textContent = 'Arrêt après cette créature…';
      return;
    }
    try { await post('/auto'); } catch (e) { say(e.message, true); return; }
    S.auto = 'on'; $('#go').hidden = true; $('#cancel').hidden = false; $$('.nbs-redo').forEach(x => x.disabled = true);
    b.lastChild.textContent = 'Arrêter la boucle';
    let made = 0;
    const j = await follow(j => {
      $('#bar').style.width = Math.round(j.progress * 100) + '%';
      say(`${S.auto === 'stop' ? 'Dernière créature · ' : ''}${j.step === 'Préparation' ? 'Préparation… (ComfyUI démarre, ~1 min la première fois)' : j.step + '…'} ${Math.round(j.progress * 100)} % · ${j.made || 0} finie${(j.made || 0) > 1 ? 's' : ''}`);
      if ((j.made || 0) > made && j.slug) { made = j.made; open(j.slug).catch(() => {}); }
    });
    S.auto = null; busy(false);
    b.disabled = false; b.lastChild.textContent = 'Invocation en boucle';
    say(j.error ? j.error : `Boucle terminée : ${j.made || made} créature${(j.made || made) > 1 ? 's' : ''} invoquée${(j.made || made) > 1 ? 's' : ''} ✓`, !!j.error);
    if (j.slug) await open(j.slug).catch(() => {});
  };
  $('#stages').innerHTML = DIRS.map((d, i) => `<div class="nbs-stage${i % 3 ? ' path' : ''}"><img class="w" data-d="${d}" alt=""><span class="tag">${ARROW[d]} ${d}</span></div>`).join('');

  // ------------------------------------------------------------ inspiration
  S.theme = 'melange';
  $$('#themes [data-t]').forEach(b => b.onclick = () => {
    S.theme = b.dataset.t;
    $$('#themes [data-t]').forEach(x => x.classList.toggle('on', x === b));
  });
  $('#crType').innerHTML = `<option value="">Auto (les types rares d'abord)</option>` + ELEMS.map(t => `<option value="${t}">${t}</option>`).join('');
  $('#crType').onchange = () => { S.idType = ''; };
  $('#inspire').onclick = async () => {
    const b = $('#inspire'), msg = $('#inspireMsg');
    b.disabled = true; msg.textContent = 'La plume réfléchit… (une minute la première fois)';
    try {
      const i = await post('/inspire', { theme: S.theme, type: $('#crType').value });
      if (i.name) $('#name').value = i.name;
      $('#desc').value = i.description;
      S.idType = i.type || '';
      msg.textContent = `Idée prête${i.type ? ` (type ${i.type})` : ''} : retouche-la si tu veux, puis Invoquer.`;
    } catch (e) { msg.textContent = e.message; }
    b.disabled = false;
  };

  // ------------------------------------------------------------ forme affichée : la créature ou une de ses variantes
  const form = () => S.cr?.forms?.find(f => f.id === S.form) || S.cr?.forms?.[0] ||
    { id: 'base', nom: S.cr?.name, dossier: 'sprites/', fx: S.cr?.attack_fx || {}, combat: S.cr?.lore?.combat };
  function renderForms() {
    const box = $('#forms'), sel = $('#varSel');
    if (!S.cr?.forms?.length) { box.innerHTML = '<span class="nbs-hint">Les variantes arrivent avec la fiche de combat.</span>'; sel.innerHTML = ''; return; }
    if (!S.cr.forms.some(f => f.id === S.form)) S.form = 'base';
    box.innerHTML = S.cr.forms.map(f => `<span class="nbs-form${f.id === S.form ? ' on' : ''}" data-f="${esc(f.id)}">
      <img src="${src(f.dossier + 'bas_repos.png')}" alt=""><b>${esc(f.id === 'base' ? 'Originale' : f.nom.slice(S.cr.name.length + 1))}</b>
      <span class="nbs-rare r${RAR.indexOf(f.combat.rarete)}">${esc(f.combat.rarete)}</span>
      ${f.id === 'base' ? '' : `<button class="nbs-btn red sq" data-rm="${esc(f.id)}" title="Supprimer la variante">${ic('corbeille')}</button>`}</span>`).join('');
    const have = new Set(S.cr.variants || []);
    sel.innerHTML = (S.cr.variant_choices || []).filter(v => !have.has(v.id)).map(v => `<option value="${esc(v.id)}">${esc(v.id === 'chromatique' ? 'chromatique (rare)' : v.label)}</option>`).join('');
    $$('#forms .nbs-form').forEach(el => el.onclick = async e => {
      const rm = e.target.closest('[data-rm]');
      if (rm) {
        e.stopPropagation();
        try { refresh(await post('/variant-remove', { slug: S.cr.slug, variant: rm.dataset.rm })); } catch (err) { $('#varMsg').textContent = err.message; }
        return;
      }
      S.form = el.dataset.f; renderForms(); renderFiche(); renderAttacks(); renderAnims();
    });
  }
  $('#varAdd').onclick = async () => {
    const v = $('#varSel').value;
    if (!v || !S.cr) return;
    $('#varMsg').textContent = 'Peinture de la variante…';
    try { S.form = v; refresh(await post('/variant', { slug: S.cr.slug, variant: v })); $('#varMsg').textContent = 'Variante prête ✓'; }
    catch (e) { $('#varMsg').textContent = e.message; }
  };
  const RAR = ['commun', 'peu commun', 'rare', 'épique', 'légendaire', '???'];  // ??? : la créature unique (n° 0, NeoMe)

  // ------------------------------------------------------------ fiche
  function renderFiche() {
    const f = S.cr?.lore, box = $('#fiche'), F = form();
    if (!S.cr) { box.innerHTML = '<div class="nbs-hint">Aucune créature ouverte.</div>'; return; }
    const big = S.cr.illustration ? src(F.dossier + 'illustration.png') : S.cr.portrait ? src(F.dossier + 'portrait.png') : '';
    const face = F.id === 'base' && S.cr.views?.bas?.file;  // le rendu de face du modèle (HD), plus l'image du bestiaire
    const pic = face ? src(face) : big || src(F.dossier + 'bas_repos.png');
    const pv = S.cr.portrait_version || [0, 0], iv = S.cr.illustration_version || [0, 0];
    $('#pVer').textContent = pv[1] ? `${pv[0]} / ${pv[1]}` : '—';
    $('#iVer').textContent = iv[1] ? `${iv[0]} / ${iv[1]}` : '—';
    $('#iNote').textContent = (S.cr.illustration_note || '').replace(/^bestiaire\s*/, '');
    box.innerHTML = f ? `<div class="nbs-fiche-top">${pic ? `<div class="nbs-fiche-pic nbs-well${face || big ? ' big' : ''}"><img src="${pic}" alt="" title="De face"></div>` : ''}
      <div><div class="nbs-fiche-head"><b>${esc(F.nom || S.cr.name)}</b>${String(F.id === 'base' || F.id === 'chromatique' ? f.type : F.id).split(' et ').map(t => `<span class="nbs-type">${esc(t)}</span>`).join('')}</div>
      <dl class="nbs-fiche-stats"><dt>Espèce</dt><dd>${esc(f.espece)}</dd><dt>Taille</dt><dd>${esc(f.taille)}</dd>
      <dt>Poids</dt><dd>${esc(f.poids)}</dd><dt>Habitat</dt><dd>${esc(f.habitat)}</dd></dl></div></div>
      <p class="nbs-read">${esc(f.description)}</p>
      <div class="nbs-story"><div class="nbs-story-t">Légende</div><p class="nbs-read">${esc(f.histoire)}</p></div>${combat(F.combat || f.combat, S.cr.illustration && S.cr.portrait ? src(F.dossier + 'portrait.png') : '')}`
      : '<div class="nbs-hint">Pas encore de fiche : clique « Réécrire la fiche ».</div>';
    const edit = async (route, body, what) => {
      $('#loreMsg').textContent = what;
      try { refresh(await post(route, { slug: S.cr.slug, ...body })); $('#loreMsg').textContent = ''; }
      catch (e) { $('#loreMsg').textContent = e.message; }
    };
    const t1 = $('#typeSel1'), t2 = $('#typeSel2');
    if (t1) t1.onchange = t2.onchange = () => edit('/set-types', { types: [t1.value, t2.value] }, 'Nouveaux types…');
    $$('#fiche .nbs-movesel').forEach(s => s.onchange = () => edit('/set-attack', { index: +s.dataset.i, id: s.value || null }, 'Nouvelle attaque…'));
    if (f?.combat && !S.moves) get('/moves').then(m => { S.moves = m; renderFiche(); }).catch(() => {});
    const rs = $('#rarSel');
    if (rs) rs.onchange = async () => {
      $('#loreMsg').textContent = 'Nouvelle rareté…';
      try { refresh(await post('/rarity', { slug: S.cr.slug, rarete: rs.value || null })); $('#loreMsg').textContent = ''; }
      catch (e) { $('#loreMsg').textContent = e.message; }
    };
  }
  const STAT = { pv: 'PV', attaque: 'Attaque', defense: 'Défense', vitesse: 'Vitesse' };
  const GENRE = { griffe: 'griffes', morsure: 'morsure', charge: 'charge', fouet: 'fouet', corne: 'corne', dard: 'dard', etreinte: 'étreinte',
    projectile: 'projectile', souffle: 'souffle', rayon: 'rayon', cri: 'cri', rafale: 'rafale', pluie: 'pluie', onde: 'onde',
    explosion: 'explosion', soin: 'soin', renfort: 'renfort' };
  const STATUT = { 'brûlure': 'brûle', poison: 'empoisonne', gel: 'gèle', paralysie: 'paralyse' };
  const moveExtra = a => a.effet_texte != null  // catalogue des 204 attaques : la mécanique en clair
    ? `${a.puissance ? `<span class="nbs-pow">puissance ${a.puissance}</span> ` : ''}<span class="nbs-pow" title="${esc(a.technique || '')}">${a.puissance && a.effet_texte ? '· ' : ''}${esc(a.effet_texte)}</span>`
    : a.effet?.soin ? `<span class="nbs-pow">soigne ${a.effet.soin} % des PV</span>`
    : a.effet?.attaque ? `<span class="nbs-pow">attaque +${a.effet.attaque} %</span>`
    : `<span class="nbs-pow">puissance ${a.puissance}</span>${a.statut ? ` <span class="nbs-pow">· ${STATUT[a.statut.nom] || esc(a.statut.nom)} (${a.statut.chance} %)</span>` : ''}`;
  const atkRar = r => r ? `<span class="nbs-rare r${RAR.indexOf(r)}">${esc(r)}</span> ` : '';
  function combat(k, portrait) {
    if (!k) return '';
    const xm = (k, e) => ({4: ' ×4', 2: ' ×2', .5: ' ×½', .25: ' ×¼'})[(k.multiplicateurs || {})[e]] || '';  // table des types : ×4, ×2, ×½, ×¼
    const chips = (l, cls) => l.map(t => `<span class="nbs-chip ${cls}">${esc(t)}</span>`).join(' ') || '—';
    const base = form().id === 'base';
    const rar = base && k.rarete !== '???' ? `<select class="nbs-rarsel" id="rarSel" title="Rareté : calculée d'après le prestige, ou choisie à la main">
        <option value="">auto${k.prestige != null ? ` · prestige ${k.prestige}` : ''}</option>
        ${RAR.slice(0, 5).map(r => `<option value="${r}"${k.rarete_fixe && k.rarete === r ? ' selected' : ''}>${r} (fixée)</option>`).join('')}</select>` : '';
    const hand = base && k.rarete !== '???', ts = String(S.cr.lore?.type || '').split(' et ');
    const tsel = (id, v, none) => `<select class="nbs-rarsel" id="${id}" title="Type choisi à la main">${none ? '<option value="">—</option>' : ''}${ELEMS.map(t => `<option${t === v ? ' selected' : ''}>${t}</option>`).join('')}</select>`;
    const types = hand ? `<div class="nbs-combat-head"><span class="nbs-hint">Types</span> ${tsel('typeSel1', ts[0])} ${tsel('typeSel2', ts[1] || '', true)}</div>` : '';
    const top = Math.min(4, RAR.indexOf(k.rarete) + 2), ok = m => RAR.indexOf(m.rarete) <= top;  // jusqu'à 2 crans au-dessus de la créature
    const msel = (a, i) => !hand || !S.moves ? '' : `<select class="nbs-rarsel nbs-movesel" data-i="${i}" title="Changer cette attaque">
        <option value="">changer…</option>${ELEMS.map(e => `<optgroup label="${e}">${S.moves.filter(m => m.element === e && ok(m)).map(m =>
          `<option value="${m.id}"${m.id === a.id ? ' selected' : ''}>${esc(m.nom)} · ${GENRE[m.genre] || m.genre} · ${m.rarete}</option>`).join('')}</optgroup>`).join('')}</select>`;
    return `<div class="nbs-combat">${portrait ? `<div class="nbs-fiche-pic nbs-well nbs-combat-pic"><img src="${portrait}" alt="" title="Portrait de combat"></div>` : ''}<div class="nbs-combat-head"><span class="nbs-rare r${RAR.indexOf(k.rarete)}">${esc(k.rarete)}</span>${k.rarete_fixe ? ' <span class="nbs-pow">🔒</span>' : ''} ${rar}</div>${types}
      <div class="nbs-statgrid">${Object.entries(STAT).map(([key, label]) => `<span>${label}</span><i><b style="width:${Math.min(100, k.stats[key])}%"></b></i><em>${k.stats[key]}</em>`).join('')}</div>
      <div class="nbs-read nbs-weak"><b>Faible contre</b> ${chips(k.faiblesses.map(e => e + xm(k, e)), 'bad')} &nbsp; <b>Résiste à</b> ${chips(k.resistances.map(e => e + xm(k, e)), 'good')}${(k.immunites || []).length ? ` &nbsp; <b>Immunisé contre</b> ${chips(k.immunites, 'good')}` : ''}</div>
      ${k.attaques.map((a, i) => `<div class="nbs-move"><div class="nbs-move-t">${i + 1}. ${esc(a.nom)} ${atkRar(k.rarete === '???' ? '???' : a.rarete || S.moves?.find(m => m.id === a.id)?.rarete)}<span class="nbs-chip">${esc(a.element)}</span> <span class="nbs-chip">${GENRE[a.genre] || esc(a.genre)}</span> ${moveExtra(a)} ${msel(a, i)}</div><p class="nbs-read">${esc(a.description)}</p></div>`).join('')}</div>`;
  }
  // ------------------------------------------------------------ attaques animées (corps + calque d'effet)
  const imgCache = {};
  const pic = url => { if (!imgCache[url]) { const im = new Image(); im.src = url; imgCache[url] = im; } return imgCache[url]; };
  const atkMoves = () => form().combat?.attaques || [];
  function atkFrame(n, d, i) {
    const F = form(), fx = F.fx?.[n]?.[d]?.[i];
    if (!fx) return null;
    return { body: src(`${F.dossier}attaque${n}_${d}_${i}.png`), fx: fx.effect ? src(`${F.dossier}effet${n}_${d}_${i}.png`) : null, off: fx.offset };
  }
  function renderAttacks() {
    const box = $('#attacks'), moves = atkMoves();
    if (!S.cr || !moves.length || !form().fx?.['1']) { box.innerHTML = '<div class="nbs-hint">Les attaques arrivent avec la fiche du bestiaire.</div>'; return; }
    box.innerHTML = moves.map((a, k) => `<div class="nbs-atk"><div class="nbs-atk-t">${k + 1}. ${esc(a.nom)} <span class="nbs-hint">· ${esc(a.element)} · ${GENRE[a.genre] || esc(a.genre)}</span></div>
      <div class="nbs-atk-row">${sigOf(a) ? `<canvas width="320" height="180" class="nbs-sig-cv nbs-well" data-n="${k + 1}" data-v="${sigOf(a)}" title="Comme dans l'Arène"></canvas>`
        : DIRS.map(d => `<canvas width="192" height="192" class="nbs-atk-cv nbs-well" data-n="${k + 1}" data-d="${d}"></canvas>`).join('')}</div></div>`).join('');
    if (box.querySelector('.nbs-sig-cv')) sigLoop();
  }
  /* NeoMe (n° 0) a ses attaques signature (dossier signature/ : planches de 10 images de 128 px, une ligne par temps : lancer, trajet, impact).
     Rejouées ici avec la mise en scène et les tailles de l'Arène (scène 320 × 180, NeoMe en 64 px). */
  const SIG = ['eclipse', 'regard', 'casque', 'coquille'];
  const sigOf = a => S.cr?.slug === 'neome' && SIG.includes(a.visuel) ? a.visuel : '';
  const SIG_SHOW = {  // parts : [début ms, ligne de la planche, 0 = sur NeoMe / 1 = sur la cible, taille, ms par image, options] ; rings : [début, où, rayon, couleur, ms, épaisseur]
    eclipse: { len: 1700, hitAt: 520, parts: [[0, 0, 0, 210, 80, { dy: -8 }], [520, 2, 1, 180, 60, { dy: -4 }]], rings: [[480, 0, 320, '#ffd84a', 650, 6], [570, 0, 256, '#ff4fd8', 600, 4], [640, 0, 192, '#ffffff', 520, 3]] },
    regard: { len: 1700, hitAt: 620, parts: [[0, 0, 0, 100, 45, { dx: 4, dy: -12 }], [420, 1, 0, 64, 40, { dx: 10, dy: -12, beam: true, until: 820 }], [510, 2, 1, 160, 55, { dy: -8 }]], rings: [[620, 1, 90, '#ffd84a', 480, 5]] },
    casque: { len: 1900, hitAt: 780, parts: [[0, 0, 0, 160, 40, { dy: -6, until: 780 }], [360, 1, 0, 96, 50, { dx: 18, dy: -8, travel: 420, until: 780 }], [780, 2, 1, 190, 55, { dy: -6 }]], rings: [[0, 0, 70, '#ff4fd8', 480, 3], [110, 0, 90, '#5ef0ff', 480, 3], [220, 0, 110, '#ff4fd8', 480, 3], [780, 1, 110, '#5ef0ff', 520, 5], [860, 1, 80, '#ff4fd8', 480, 4]] },
    coquille: { len: 1500, hitAt: 520, parts: [[0, 0, 0, 170, 95, {}]], rings: [[520, 0, 70, '#ffd84a', 520, 4], [620, 0, 50, '#ffffff', 440, 3]] },
  };
  // o (Sprite Lab) : { v, ground, X, flip } — seulement les effets, autour du héros qui se déplace ; t = ms depuis le début de l'attaque
  function sigDraw(cv, now, o) {
    const v = o?.v || cv.dataset.v, P = o?.show || SIG_SHOW[v], g = cv.getContext('2d'), t = o ? now : now % P.len, W = cv.width, H = cv.height,
      GROUND = o?.ground ?? 124, cy = GROUND - 30, X = o?.X || [96, 236];
    g.imageSmoothingEnabled = false; g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, H);
    if (!o) for (const x of X) { g.fillStyle = 'rgba(0,0,0,.35)'; g.beginPath(); g.ellipse(x, GROUND + 2, 18, 4, 0, 0, 7); g.fill(); }
    if (!o && t > 120 && t < 900) { g.fillStyle = 'rgba(0,0,0,.45)'; g.fillRect(0, 0, W, H); }  // la scène s'assombrit pendant l'attaque, comme dans l'Arène
    if (o?.flip) g.setTransform(-1, 0, 0, 1, 2 * X[0], 0);  // tourné vers la gauche : les effets en miroir autour de NeoMe
    if (o?.sheet) for (const x of X) { g.fillStyle = 'rgba(122,79,154,.35)'; g.beginPath(); g.ellipse(x, GROUND + 2, 18, 4, 0, 0, 7); g.fill(); }  // aperçu d'une attaque créée : lanceur et cible
    const i = Math.floor(t / 110), body = !o && pic(src(form().dossier + (i < 4 ? `attaque${cv.dataset.n}_droite_${i}.png` : 'droite_repos.png')));
    if (body?.complete) g.drawImage(body, X[0] - 32, GROUND - 62);
    const tg = pic(src(form().dossier + 'gauche_repos.png'));  // la cible : une silhouette, qui recule sous le coup
    if (tg.complete && v !== 'coquille') { g.save(); g.globalAlpha = .35; g.filter = 'brightness(0)'; g.drawImage(tg, X[1] - 32 + (t >= P.hitAt && t < P.hitAt + 300 ? 3 : 0), GROUND - 62); g.restore(); }
    for (const [x0, k, r1, c, ms, w] of P.rings) {  // les ondes de choc
      const u = (t - x0) / ms; if (u < 0 || u > 1) continue;
      const r = 4 + (r1 - 4) * (1 - (1 - u) ** 3);
      g.strokeStyle = c; g.globalAlpha = 1 - u; g.lineWidth = w; g.beginPath(); g.ellipse(X[k], cy - 6, r, r * .55, 0, 0, 7); g.stroke(); g.globalAlpha = 1;
    }
    const sheet = pic(o?.sheet || src('signature/' + v + '.png'));
    if (sheet.complete) for (const [t0, row, at, size, ms, o] of P.parts) {
      const dt = t - t0; if (dt < 0 || (o.until && t >= o.until)) continue;
      const loop = o.beam || o.travel, f = loop ? Math.floor(dt / ms) % 10 : Math.floor(dt / ms); if (f > 9) continue;
      const k = o.travel ? Math.min(1, dt / o.travel) : 0, x = X[at] + (o.dx || 0) + (X[1] - X[at] - (o.dx || 0)) * k, y = cy + (o.dy || 0);
      for (const glow of [0, 1]) {  // l'effet, puis son halo (couleurs additionnées)
        if (glow) { g.globalCompositeOperation = 'lighter'; g.globalAlpha = .55; }
        if (o.beam) g.drawImage(sheet, f * 128, row * 128, 128, 128, x, y - size / 2, X[1] - x - 10, size);
        else g.drawImage(sheet, f * 128, row * 128, 128, 128, Math.round(x - size / 2), Math.round(y - size / 2), size, size);
        g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
      }
    }
    g.setTransform(1, 0, 0, 1, 0, 0);
    if (t >= P.hitAt && t < P.hitAt + 90) { g.fillStyle = 'rgba(255,236,255,.35)'; g.fillRect(0, 0, W, H); }  // l'éclair du coup
  }
  // Sprite Lab : l'attaque signature joue autour du héros (calque à mi-résolution, donc NeoMe y fait 64 px comme dans l'Arène)
  function heroSig(v, n) {
    const cv = $('#heroSig'), w = $('#world'), t0 = performance.now();
    cv.width = w.clientWidth / 2; cv.height = w.clientHeight / 2; cv.dataset.n = n; hero.sig = t0;
    const step = now => {
      if (hero.sig !== t0) return;
      if (now - t0 > SIG_SHOW[v].len || S.tab !== 'lab' || !view.isConnected) { cv.width = cv.width; return; }
      const x0 = (hero.x + 64) / 2;
      sigDraw(cv, now - t0, { v, ground: hero.y / 2 + 62, X: [x0, x0 + 140], flip: hero.d === 'gauche' });
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
  function sigLoop() {
    if (S.sigRun) return; S.sigRun = true;
    const step = now => { const cvs = $$('.nbs-sig-cv'); if (!cvs.length || !view.isConnected) { S.sigRun = false; return; } if (S.tab === 'dirs') cvs.forEach(cv => sigDraw(cv, now)); requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }
  function drawAttack(cv, n, d, i) {
    const f = atkFrame(n, d, i), g = cv.getContext('2d');
    g.imageSmoothingEnabled = false; g.clearRect(0, 0, 192, 192);
    if (!f) return;
    const b = pic(f.body); if (b.complete) g.drawImage(b, 64, 64);
    if (f.fx) { const e = pic(f.fx); if (e.complete) g.drawImage(e, 64 + f.off[0], 64 + f.off[1]); }
  }
  // ------------------------------------------------------------ animations de combat (planches : une ligne par direction)
  const ANIM_NAMES = { attente: 'Attente', degats: 'Dégâts reçus', ko: 'K.O.' };
  function renderAnims() {
    const box = $('#anims');
    if (!S.cr || S.cr.pending || !S.cr.anims) { box.innerHTML = '<div class="nbs-hint">Elles arrivent avec la créature.</div>'; return; }
    box.innerHTML = Object.keys(ANIM_NAMES).map(a => `<div class="nbs-atk"><div class="nbs-atk-t">${ANIM_NAMES[a]}</div>
      <div class="nbs-atk-row">${DIRS.map(d => `<canvas width="64" height="64" class="nbs-anim-cv nbs-well" data-a="${a}" data-d="${d}"></canvas>`).join('')}</div></div>`).join('');
  }
  function animIndex(ms, t, hold) {  // image à montrer au temps t ; hold : la dernière image reste un moment (K.O.)
    const total = ms.reduce((x, y) => x + y, 0) + hold;
    let k = t % total;
    for (let i = 0; i < ms.length; i++) { if (k < ms[i]) return i; k -= ms[i]; }
    return ms.length - 1;
  }
  function drawAnims() {
    const now = performance.now(), F = form();
    $$('.nbs-anim-cv').forEach(cv => {
      const a = cv.dataset.a, ms = S.cr.anims[a], sheet = pic(src(F.dossier + a + '.png')), g = cv.getContext('2d');
      const i = animIndex(ms, now, a === 'ko' ? 900 : a === 'degats' ? 600 : 0);
      g.imageSmoothingEnabled = false; g.clearRect(0, 0, 64, 64);
      if (sheet.complete) g.drawImage(sheet, i * 64, DIRS.indexOf(cv.dataset.d) * 64, 64, 64, 0, 0, 64, 64);
    });
  }
  // ------------------------------------------------------------ retouche ciblée
  const RT = { key: 'bas', index: null, x: null, y: null, r: .1 };
  const NAMES = { bas: 'la face', haut: 'le dos', gauche: 'le profil' };
  function openRetouch(key, index, url) {
    if (!url) return;
    Object.assign(RT, { key, index, x: null, y: null });
    $('#rtTitle').textContent = index === null ? `Retoucher ${NAMES[key]}` : `Retoucher l'esquisse ${index + 1}`;
    $('#rtImg').src = url; $('#rtText').value = ''; $('#rtMsg').textContent = '';
    drawZone(); $('#retouch').hidden = false; $('#rtText').focus();
  }
  function drawZone() {
    const z = $('#rtZone');
    z.hidden = !RT.r || RT.x === null;
    if (z.hidden) return;
    Object.assign(z.style, { left: RT.x * 100 + '%', top: RT.y * 100 + '%', width: RT.r * 200 + '%', height: RT.r * 200 + '%' });
  }
  $('#rtPic').onclick = e => {
    const b = $('#rtImg').getBoundingClientRect();
    RT.x = Math.max(0, Math.min(1, (e.clientX - b.left) / b.width)); RT.y = Math.max(0, Math.min(1, (e.clientY - b.top) / b.height));
    if (!RT.r) { RT.r = .1; $$('#rtSize .nbs-btn').forEach(x => x.classList.toggle('on', x.dataset.r === '.1')); }
    drawZone();
  };
  $$('#rtSize .nbs-btn').forEach(b => b.onclick = () => {
    RT.r = +b.dataset.r; $$('#rtSize .nbs-btn').forEach(x => x.classList.toggle('on', x === b)); drawZone();
  });
  $('#rtClose').onclick = () => { $('#retouch').hidden = true; };
  $('#rtGo').onclick = () => {
    const instruction = $('#rtText').value.trim();
    if (!instruction) { $('#rtMsg').textContent = 'Écris ce qu\'il faut changer.'; return; }
    if (RT.r && RT.x === null) { $('#rtMsg').textContent = 'Clique sur l\'image pour placer la zone (ou choisis « Toute la créature »).'; return; }
    $('#retouch').hidden = true;
    show('creer');
    runJob(() => post('/edit', { slug: S.cr.slug, key: RT.key, instruction, index: RT.index, zone: RT.r ? [RT.x, RT.y, RT.r] : null }));
  };
  $('#rtText').onkeydown = e => { if (e.key === 'Enter') $('#rtGo').click(); };

  $('#illuRedo').onclick = () => {
    if (!S.cr || S.cr.pending) return;
    show('creer');
    runJob(() => post('/illustration', { slug: S.cr.slug }));
  };
  const illuTurn = async delta => {
    if (!S.cr?.illustration_version?.[1]) return;
    try { refresh(await post('/choose', { slug: S.cr.slug, key: 'illustration', delta })); } catch (e) { $('#loreMsg').textContent = e.message; }
  };
  $('#iPrev').onclick = () => illuTurn(-1);
  $('#iNext').onclick = () => illuTurn(1);
  $('#illuCut').onclick = () => S.cr?.hd?.illustration && openCutout('illustration', src(S.cr.hd.illustration));
  $('#portraitCut').onclick = () => S.cr?.hd?.portrait && openCutout('portrait', src(S.cr.hd.portrait));

  // ------------------------------------------------------------ détourage au pinceau (rouge : effacer, vert : restaurer)
  const CT = { key: '', tool: 'erase', size: .03, down: false };
  const CT_NAMES = { bas: 'la face', haut: 'le dos', gauche: 'le profil', portrait: 'le portrait de combat', illustration: "l'image du bestiaire" };
  function openCutout(key, url) {
    if (!url) return;
    CT.key = key;
    $('#ctTitle').textContent = `Détourage de ${CT_NAMES[key] || key}`;
    $('#ctMsg').textContent = '';
    const img = $('#ctImg'), cv = $('#ctMask');
    img.onload = () => { cv.width = img.naturalWidth; cv.height = img.naturalHeight; placeMask(); };
    img.src = url;
    $('#cutout').hidden = false;
  }
  function placeMask() {  // le calque couvre exactement l'image affichée (object-fit: contain)
    const img = $('#ctImg'), cv = $('#ctMask'), box = $('#ctPic'), W = box.clientWidth, H = box.clientHeight;
    const k = Math.min(W / img.naturalWidth, H / img.naturalHeight), w = img.naturalWidth * k, h = img.naturalHeight * k;
    Object.assign(cv.style, { left: (W - w) / 2 + 'px', top: (H - h) / 2 + 'px', width: w + 'px', height: h + 'px' });
  }
  function ctPaint(e) {
    const cv = $('#ctMask'), b = cv.getBoundingClientRect(), g = cv.getContext('2d');
    const x = (e.clientX - b.left) / b.width * cv.width, y = (e.clientY - b.top) / b.height * cv.height;
    g.fillStyle = CT.tool === 'erase' ? '#ff0000' : '#00ff00';
    g.beginPath(); g.arc(x, y, CT.size * cv.width, 0, Math.PI * 2); g.fill();
  }
  $('#ctMask').onpointerdown = e => { CT.down = true; $('#ctMask').setPointerCapture(e.pointerId); ctPaint(e); };
  $('#ctMask').onpointermove = e => { if (CT.down) ctPaint(e); };
  $('#ctMask').onpointerup = () => { CT.down = false; };
  $$('#ctTool .nbs-btn').forEach(b => b.onclick = () => { CT.tool = b.dataset.t; $$('#ctTool .nbs-btn').forEach(x => x.classList.toggle('on', x === b)); });
  $$('#ctSize .nbs-btn').forEach(b => b.onclick = () => { CT.size = +b.dataset.s; $$('#ctSize .nbs-btn').forEach(x => x.classList.toggle('on', x === b)); });
  $('#ctClear').onclick = () => { const cv = $('#ctMask'); cv.getContext('2d').clearRect(0, 0, cv.width, cv.height); };
  $('#ctClose').onclick = () => { $('#cutout').hidden = true; };
  $('#ctGo').onclick = async () => {
    const b = $('#ctGo'); b.disabled = true; $('#ctMsg').textContent = 'Détourage…';
    try { refresh(await post('/cutout', { slug: S.cr.slug, key: CT.key, mask: $('#ctMask').toDataURL('image/png') })); $('#cutout').hidden = true; }
    catch (e) { $('#ctMsg').textContent = e.message; }
    b.disabled = false;
  };

  $('#portraitRedo').onclick = () => {
    if (!S.cr || S.cr.pending) return;
    show('creer');
    runJob(() => post('/portrait', { slug: S.cr.slug }));
  };
  const portraitTurn = async delta => {
    if (!S.cr?.portrait_version?.[1]) return;
    try { refresh(await post('/choose', { slug: S.cr.slug, key: 'portrait', delta })); } catch (e) { $('#loreMsg').textContent = e.message; }
  };
  $('#pPrev').onclick = () => portraitTurn(-1);
  $('#pNext').onclick = () => portraitTurn(1);
  $('#relore').onclick = async () => {
    if (!S.cr) return;
    const b = $('#relore'); b.disabled = true; $('#loreMsg').textContent = 'La plume écrit…';
    try { refresh(await post('/lore', { slug: S.cr.slug })); $('#loreMsg').textContent = ''; } catch (e) { $('#loreMsg').textContent = e.message; }
    b.disabled = false;
  };
  $('#openExports').onclick = async () => { try { call('openFolder', (await get('/exports')).folder); } catch (e) { say(e.message, true); } };

  // ------------------------------------------------------------ créature ouverte
  async function open(slug) {
    if (S.cr?.slug !== slug) S.form = 'base';
    S.cr = await get('/creature?slug=' + encodeURIComponent(slug));
    S.stamp = Date.now();
    $('#liveTitle').textContent = S.cr.name;
    $('#dirTitle').textContent = S.cr.name + ' · 4 directions × 3 pas · 64×64';
    renderSheet(); renderLab(); renderSketches(); renderForms(); renderFiche(); renderAttacks(); renderAnims();
    if (S.tab === 'lab') loadFrame();
  }
  function renderSketches() {  // esquisses pas encore choisies : on les montre, un clic lance le reste
    const box = $('#sketches'), pending = !!S.cr?.pending;
    box.hidden = !pending;
    if (!pending) return;
    const b = S.cr.brief, P = { quatre_pattes: 'à quatre pattes', deux_jambes: 'debout sur deux jambes', plusieurs_pattes: `sur ${b?.pattes} pattes`,
      flotte: 'flotte dans les airs, sans pattes', vole: 'vole', rampe: 'rampe, sans pattes', nage: 'nage, sans pattes',
      sautille: 'avance par bonds', roule: 'roule en boule', glisse: 'glisse comme une gelée', enracine: 'enracinée dans le sol' };
    $('#understood').textContent = b?.posture ? `Compris : ${P[b.posture] || b.posture}. Le dos et le profil suivront cette posture.` : '';
    // note du contrôle automatique : « esquisse 2 ✓ » ou « esquisse 3 ⚠ 1 tête au lieu de 3 »
    const checkNote = n => { const m = /([✓⚠].*)$/.exec(n || ''); return m ? `<span class="nbs-verdict ${m[1][0] === '✓' ? 'ok' : 'ko'}">${m[1] === '✓' ? '✓ vérifiée' : esc(m[1])}</span>` : ''; };
    $('#sketchRow').innerHTML = S.cr.designs.map((f, i) => `<div class="nbs-sketch" data-i="${i}">
      <img src="${src(f)}" alt="">${checkNote(S.cr.design_notes?.[i])}<button class="nbs-btn go" data-go="${i}">${ic('ok')}Celle-ci</button>
      <button class="nbs-btn dark sm" data-rt="${i}">Retoucher</button></div>`).join('');
    $$('#sketchRow [data-go]').forEach(b => b.onclick = () => {
      box.hidden = true;
      runJob(() => post('/continue', { slug: S.cr.slug, index: +b.dataset.go }));
    });
    $$('#sketchRow [data-rt]').forEach(b => b.onclick = () => openRetouch('bas', +b.dataset.rt, src(S.cr.designs[+b.dataset.rt])));
  }
  const refresh = cr => { S.cr = cr; S.stamp = Date.now(); renderSheet(); renderLab(); renderForms(); renderFiche(); renderAttacks(); renderAnims(); if (S.tab === 'lab') loadFrame(); };

  // ------------------------------------------------------------ directions
  function renderSheet() {
    const box = $('#sheet');
    if (!S.cr) { box.innerHTML = '<div class="nbs-hint">Invoque ou choisis une créature dans la Bibliothèque.</div>'; return; }
    box.innerHTML = DIRS.map(d => `<div class="lbl">${ARROW[d]} ${d}</div>` +
      FR.map(f => `<div class="cell${S.sel === d + '_' + f ? ' sel' : ''}" data-k="${d}_${f}"><img src="${sprite(d, f)}" alt=""></div>`).join('') +
      `<div class="nbs-row"><div class="nbs-ver"><button class="nbs-btn dark sq" data-v="-1" data-d="${d}">${ic('prev')}</button>` +
      `<span>${verTxt(d)}</span><button class="nbs-btn dark sq" data-v="1" data-d="${d}">${ic('next')}</button></div>` +
      `<button class="nbs-btn dark nbs-redo" data-redo="${d}">${ic('refaire')}Refaire</button>` +
      (d === 'droite' ? '' : `<button class="nbs-btn dark nbs-redo" data-rt="${d}">${ic('crayon')}Retoucher</button>` +
        `<button class="nbs-btn dark nbs-redo" data-ct="${d}">${ic('gomme')}Détourage</button>`) + `</div>`).join('');
    box.querySelectorAll('[data-ct]').forEach(b => b.onclick = () => {
      const k = b.dataset.ct, v = S.cr.views[k];
      openCutout(k, v?.file ? src(v.file) : '');
    });
    box.querySelectorAll('.cell').forEach(c => c.onclick = () => { S.sel = c.dataset.k; renderSheet(); });
    box.querySelectorAll('[data-v]').forEach(b => b.onclick = async () => {
      const d = b.dataset.d, f = S.sel.startsWith(d + '_') ? S.sel.slice(d.length + 1) : 'repos';
      try { refresh(await post('/choose', { slug: S.cr.slug, key: viewKey(d, f), delta: +b.dataset.v })); } catch (e) { $('#dirHint').textContent = e.message; }
    });
    box.querySelectorAll('[data-rt]').forEach(b => b.onclick = () => {
      const k = b.dataset.rt, v = S.cr.views[k];
      openRetouch(k, null, v?.file ? src(v.file) : '');
    });
    box.querySelectorAll('[data-redo]').forEach(b => b.onclick = () => {
      $('#dirHint').textContent = 'Nouvelle version en cours… (suivi dans Créer)';
      runJob(() => post('/redo', { slug: S.cr.slug, dir: b.dataset.redo })).then(() => { $('#dirHint').textContent = ''; });
    });
  }
  function verTxt(d) {
    const f = S.sel.startsWith(d + '_') ? S.sel.slice(d.length + 1) : 'repos', v = S.cr.views[viewKey(d, f)];
    return v && v.versions ? `${f === 'repos' ? 'vue' : FRAME_NAME[f]} v${v.version}/${v.versions}` : '—';
  }
  $('#toLab').onclick = () => show('lab');

  // ------------------------------------------------------------ animation (scènes + aperçu en jeu)
  const hero = { x: 160, y: 64, d: 'bas', step: 0, keys: new Set() };
  const KEYS = { ArrowDown: ['bas', 0, 1], ArrowUp: ['haut', 0, -1], ArrowLeft: ['gauche', -1, 0], ArrowRight: ['droite', 1, 0] };
  let tick = 0;
  const anim = setInterval(() => {
    if (!view.isConnected) { clearInterval(anim); S.alive = false; return; }
    tick++;
    const floats = S.cr?.brief?.posture === 'flotte';  // elle flotte : un va-et-vient en CSS, ses images ne changent pas
    if (S.cr) $$('img.w, #hero').forEach(i => i.classList.toggle('nbs-float', floats));
    if (S.cr) $$('img.w').forEach(i => { const s = sprite(i.dataset.d, CYCLE[tick % CYCLE.length]); if (i.getAttribute('src') !== s) i.src = s; i.style.visibility = s ? '' : 'hidden'; });
    if (S.cr && S.tab === 'dirs') { $$('.nbs-atk-cv').forEach(cv => drawAttack(cv, cv.dataset.n, cv.dataset.d, Math.min(3, tick % 7))); drawAnims(); }
    if (S.tab !== 'lab' || !S.cr) return;
    const fxImg = $('#heroFx');
    if (hero.atk) {  // une attaque en cours : ses 4 images, puis retour à la marche
      const f = atkFrame(hero.atk, hero.d, hero.atkI++);
      if (f) {
        const h = $('#hero');
        h.src = f.body; h.style.left = hero.x + 'px'; h.style.top = hero.y + 'px';
        fxImg.hidden = !f.fx;
        if (f.fx) { fxImg.src = f.fx; fxImg.style.left = hero.x + f.off[0] * 2 + 'px'; fxImg.style.top = hero.y + f.off[1] * 2 + 'px'; }
        return;
      }
      hero.atk = 0;
    }
    fxImg.hidden = true;
    const k = [...hero.keys].pop(), world = $('#world');
    if (k) {
      const [d, dx, dy] = KEYS[k];
      hero.d = d; hero.step++;
      hero.x = Math.max(-32, Math.min(world.clientWidth - 96, hero.x + dx * 6));
      hero.y = Math.max(-32, Math.min(world.clientHeight - 96, hero.y + dy * 6));
    } else hero.step = 0;
    const h = $('#hero'), s = sprite(hero.d, CYCLE[hero.step % CYCLE.length]);
    if (h.getAttribute('src') !== s) h.src = s;
    h.style.left = hero.x + 'px'; h.style.top = hero.y + 'px';
  }, 110);
  const onKey = e => {
    if (!view.isConnected) { removeEventListener('keydown', onKey, true); removeEventListener('keyup', onUp, true); return; }
    if (S.tab !== 'lab' || /INPUT|TEXTAREA/.test(document.activeElement?.tagName)) return;
    if (KEYS[e.key]) { hero.keys.add(e.key); e.preventDefault(); }
    if (/^[1-4]$/.test(e.key) && !hero.atk && S.cr?.attack_fx?.[e.key]) {
      hero.atk = +e.key; hero.atkI = 0; e.preventDefault();
      const sv = sigOf(atkMoves()[hero.atk - 1] || {}); if (sv) heroSig(sv, hero.atk);
    }
    if (e.ctrlKey && e.key.toLowerCase() === 'z') { undo(); e.preventDefault(); }
    if (e.ctrlKey && e.key.toLowerCase() === 'y') { redo(); e.preventDefault(); }
  };
  const onUp = e => hero.keys.delete(e.key);
  addEventListener('keydown', onKey, true);
  addEventListener('keyup', onUp, true);

  // ------------------------------------------------------------ sprite lab : réglages
  function renderLab() {
    if (!S.cr) return;
    const lab = S.cr.lab;
    $$('.nbs-opt[data-o]').forEach(o => o.querySelector('.nbs-check').classList.toggle('on', !!lab[o.dataset.o]));
    $('#cnum').textContent = lab.colors;
    $('#sw').innerHTML = (S.cr.palette || []).map(c => `<i style="background:${c}" data-c="${c}" class="${c === ed.color ? 'on' : ''}"></i>`).join('');
    $('#sw').querySelectorAll('i').forEach(i => i.onclick = () => setColor(i.dataset.c));
    if (!ed.color && S.cr.palette?.length) setColor(S.cr.palette[0]);
  }
  const setLab = async opts => {
    if (!S.cr) return;
    $('#expMsg').textContent = 'Recalcul des 20 images…';
    try { refresh(await post('/lab', { slug: S.cr.slug, opts })); $('#expMsg').textContent = ''; } catch (e) { $('#expMsg').textContent = e.message; }
  };
  $$('.nbs-opt[data-o]').forEach(o => o.onclick = () => setLab({ [o.dataset.o]: !S.cr?.lab[o.dataset.o] }));
  $('#cminus').onclick = () => S.cr && setLab({ colors: Math.max(2, S.cr.lab.colors - 2) });
  $('#cplus').onclick = () => S.cr && setLab({ colors: Math.min(64, S.cr.lab.colors + 2) });
  $('#resetEd').onclick = async () => { if (S.cr) refresh(await post('/reset-edits', { slug: S.cr.slug })); };
  $('#exp').onclick = async () => {
    if (!S.cr) return;
    try {
      const r = await post('/export', { slug: S.cr.slug });
      $('#expMsg').innerHTML = `Exporté dans Exports : planche, JSON, fiche et portrait · <a href="#" id="openf">ouvrir le dossier</a>`;
      $('#openf').onclick = e => { e.preventDefault(); call('openFolder', r.folder); };
    } catch (e) { $('#expMsg').textContent = e.message; }
  };
  $('#expTo').onclick = async () => {
    if (!S.cr) return;
    try { const r = await call('saveSheet', S.cr.slug); if (r) $('#expMsg').textContent = 'Exporté dans ' + r.folder; } catch (e) { $('#expMsg').textContent = e.message; }
  };

  // ------------------------------------------------------------ sprite lab : éditeur pixel 64x64
  const cv = $('#ed'), g = cv.getContext('2d', { willReadFrequently: true });
  const ed = { tool: 'pen', color: '', undo: [], redo: [], down: false, dirty: false };
  const ALL = DIRS.flatMap(d => FR.map(f => d + '_' + f));
  function setColor(c) { ed.color = c; $('#cur').style.background = c; $('#colorIn').value = c; $$('#sw i').forEach(i => i.classList.toggle('on', i.dataset.c === c)); }
  $('#colorIn').oninput = e => setColor(e.target.value);
  $$('#tools [data-t]').forEach(b => b.onclick = () => { ed.tool = b.dataset.t; $$('#tools [data-t]').forEach(x => x.classList.toggle('on', x === b)); });
  $('#gridBtn').onclick = () => { $('#cv').classList.toggle('grid'); $('#gridBtn').classList.toggle('on'); };
  $('#undo').onclick = () => undo();
  $('#redo').onclick = () => redo();
  $('#fprev').onclick = () => { S.frame = (S.frame + ALL.length - 1) % ALL.length; loadFrame(); };
  $('#fnext').onclick = () => { S.frame = (S.frame + 1) % ALL.length; loadFrame(); };

  function loadFrame() {
    const key = ALL[S.frame], [d, f] = key.split('_');
    $('#fnum').textContent = `${S.frame + 1} / ${ALL.length}`;
    $('#fLabel').textContent = `${ARROW[d]} ${d} · ${FRAME_NAME[f]}`;
    g.clearRect(0, 0, 64, 64);
    ed.undo = []; ed.redo = [];
    if (!S.cr) return;
    const im = new Image();
    im.onload = () => { g.clearRect(0, 0, 64, 64); g.drawImage(im, 0, 0); };
    im.src = sprite(d, f);
  }
  const hex = (r, g2, b) => '#' + [r, g2, b].map(v => v.toString(16).padStart(2, '0')).join('');
  const rgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  function at(e) { const r = cv.getBoundingClientRect(); return [Math.floor((e.clientX - r.left) / r.width * 64), Math.floor((e.clientY - r.top) / r.height * 64)]; }
  function plot(x, y) {
    if (x < 0 || y < 0 || x > 63 || y > 63) return;
    if (ed.tool === 'erase') g.clearRect(x, y, 1, 1);
    else { g.fillStyle = ed.color || '#0b0b12'; g.fillRect(x, y, 1, 1); }
    ed.dirty = true;
  }
  function fill(x, y) {
    const img = g.getImageData(0, 0, 64, 64), p = img.data, i0 = (y * 64 + x) * 4;
    const from = [p[i0], p[i0 + 1], p[i0 + 2], p[i0 + 3]], to = [...rgb(ed.color || '#0b0b12'), 255];
    if (from.every((v, i) => v === to[i])) return;
    const same = i => p[i] === from[0] && p[i + 1] === from[1] && p[i + 2] === from[2] && p[i + 3] === from[3];
    const stack = [[x, y]];
    while (stack.length) {
      const [cx, cy] = stack.pop(), i = (cy * 64 + cx) * 4;
      if (cx < 0 || cy < 0 || cx > 63 || cy > 63 || !same(i)) continue;
      p.set(to, i);
      stack.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
    }
    g.putImageData(img, 0, 0);
    ed.dirty = true;
  }
  let last = null;
  cv.onpointerdown = e => {
    if (!S.cr) return;
    const [x, y] = at(e);
    if (ed.tool === 'pick') {
      const d = g.getImageData(x, y, 1, 1).data;
      if (d[3]) setColor(hex(d[0], d[1], d[2]));
      return;
    }
    ed.undo.push(g.getImageData(0, 0, 64, 64)); if (ed.undo.length > 60) ed.undo.shift(); ed.redo = [];
    if (ed.tool === 'fill') { fill(x, y); save(); return; }
    ed.down = true; cv.setPointerCapture(e.pointerId); plot(x, y); last = [x, y];
  };
  cv.onpointermove = e => {
    if (!ed.down) return;
    const [x, y] = at(e), [lx, ly] = last, n = Math.max(Math.abs(x - lx), Math.abs(y - ly));
    for (let i = 1; i <= n; i++) plot(Math.round(lx + (x - lx) * i / n), Math.round(ly + (y - ly) * i / n));  // trait continu même si la souris va vite
    last = [x, y];
  };
  cv.onpointerup = () => { if (ed.down) { ed.down = false; save(); } };
  function undo() { if (!ed.undo.length) return; ed.redo.push(g.getImageData(0, 0, 64, 64)); g.putImageData(ed.undo.pop(), 0, 0); ed.dirty = true; save(); }
  function redo() { if (!ed.redo.length) return; ed.undo.push(g.getImageData(0, 0, 64, 64)); g.putImageData(ed.redo.pop(), 0, 0); ed.dirty = true; save(); }
  let saving = Promise.resolve();
  function save() {  // chaque trait est gardé (retouche conservée même si on change les réglages ensuite)
    if (!ed.dirty || !S.cr) return;
    ed.dirty = false;
    const png = cv.toDataURL('image/png'), key = ALL[S.frame], slug = S.cr.slug;
    saving = saving.then(() => post('/frame', { slug, key, png })).then(cr => { if (S.cr?.slug === slug) { S.cr = cr; S.stamp = Date.now(); renderSheet(); } })
      .catch(e => { $('#expMsg').textContent = e.message; });
  }

  // ------------------------------------------------------------ bibliothèque
  let libCache = [];
  S.libKind = 'creature'; S.favOnly = false;
  try { $('#libSort').value = localStorage.getItem('nbs-sort') || 'recent'; } catch {}
  async function loadLib() {
    const kind = S.libKind;
    let list;
    try { list = await get('/items?kind=' + kind); } catch (e) { $('#lib').textContent = e.message; return; }
    if (kind !== S.libKind) return;  // un autre genre a été choisi pendant le chargement : sa propre réponse l'affichera
    libCache = list;
    renderLib();
  }
  $$('#libKinds [data-k]').forEach(b => b.onclick = () => {
    S.libKind = b.dataset.k; S.fuse = null; fuseBar();
    $$('#libKinds [data-k]').forEach(x => x.classList.toggle('on', x === b));
    $('#fuseBtn').hidden = S.libKind !== 'creature';
    libCache = []; $('#lib').innerHTML = '';  // pas de clic sur une carte de l'ancien genre pendant le chargement
    loadLib();
  });
  $('#favOnly').onclick = () => {
    S.favOnly = !S.favOnly; $('#favOnly').classList.toggle('on', S.favOnly);
    $('#favOnly .ic').style.backgroundImage = `url(${U}ui/i_${S.favOnly ? 'etoile' : 'etoile_vide'}.png)`;
    renderLib();
  };
  $('#libSort').onchange = () => { try { localStorage.setItem('nbs-sort', $('#libSort').value); } catch {} renderLib(); };
  const nameOf = c => c.name || c.nom || '';
  const typeOf = c => c.type || c.categorie || c.element || '';
  const rankOf = c => c.rarete ? RAR.indexOf(c.rarete) : (c.force || 0) / 1000;
  const SORT = {
    recent: (a, b) => (b.updated || b.created || 0) - (a.updated || a.created || 0),
    nom: (a, b) => nameOf(a).localeCompare(nameOf(b), 'fr'),
    rarete: (a, b) => rankOf(b) - rankOf(a) || nameOf(a).localeCompare(nameOf(b), 'fr'),
    type: (a, b) => typeOf(a).localeCompare(typeOf(b), 'fr') || nameOf(a).localeCompare(nameOf(b), 'fr'),
  };
  function thumbOf(c) {
    if (S.libKind === 'creature') return c.thumb ? `${U}lib/${encodeURIComponent(c.slug)}/${c.thumb}?v=${c.updated}` : '';
    if (S.libKind === 'objet') return mkUrl('objet', c, `/icone_${c.version || 0}.png`);
    if (S.libKind === 'attaque') return mkUrl('attaque', c, c.source ? '.png' : '/vignette.png');
    return '';
  }
  function cardMeta(c) {
    const r = c.rarete ? `<span class="nbs-rare r${RAR.indexOf(c.rarete)}">${esc(c.rarete)}</span>` : '';
    if (S.libKind === 'creature') return r + String(c.type || '').split(' et ').filter(Boolean).map(t => `<span class="nbs-chip">${esc(t)}</span>`).join('') || `${c.versions} version${c.versions > 1 ? 's' : ''}`;
    if (S.libKind === 'objet') return r + `<span class="nbs-chip">${esc(c.categorie)}</span>`;
    if (S.libKind === 'attaque') return r + `<span class="nbs-chip">${esc(c.element)}</span><span class="nbs-chip">${esc(GENRE[c.genre] || c.genre)}</span>`;
    return `<span class="nbs-chip">${Math.round(c.duree)} s</span>`;
  }
  const EMPTY = { creature: 'Aucune créature pour l\'instant : invoque la première dans Créer.', objet: 'Aucun objet : crée le premier dans Créer › Objet.',
    attaque: 'Aucune attaque.', musique: 'Aucune musique : compose la première dans Créer › Musique.' };
  function renderLib() {
    const q = $('#q').value.trim().toLowerCase(), by = SORT[$('#libSort').value] || SORT.recent;
    const list = libCache.filter(c => (!q || nameOf(c).toLowerCase().includes(q) || typeOf(c).toLowerCase().includes(q)) && (!S.favOnly || c.fav))
      .sort((a, b) => (b.fav - a.fav) || by(a, b));  // les favoris d'abord
    $('#lib').innerHTML = list.length ? list.map(c => `<div class="nbs-card" data-s="${esc(c.slug)}">
      ${thumbOf(c) ? `<img src="${thumbOf(c)}" alt="">` : `<div class="nbs-thumb-empty">${S.libKind === 'musique' ? ic('musique') : '?'}</div>`}
      <div class="nm">${esc(nameOf(c))}</div><div class="meta">${cardMeta(c)}</div>
      <button class="nbs-btn dark sq nbs-fav${c.fav ? ' on' : ''}" title="${c.fav ? 'Retirer des favoris' : 'Ajouter aux favoris'}">${ic(c.fav ? 'etoile' : 'etoile_vide')}</button>
      ${c.source ? '' : `<button class="nbs-btn red sq nbs-del" title="Mettre à la corbeille">${ic('corbeille')}</button>`}</div>`).join('')
      : `<div class="nbs-hint">${S.favOnly ? 'Aucun favori ici : clique sur l\'étoile d\'une carte.' : EMPTY[S.libKind]}</div>`;
    $$('#lib .nbs-card').forEach(card => {
      card.classList.toggle('picked', !!S.fuse?.includes(card.dataset.s));
      const it = libCache.find(c => c.slug === card.dataset.s);
      card.querySelector('.nbs-fav').onclick = async e => {
        e.stopPropagation();
        try { await post('/favorite', { kind: S.libKind, slug: it.slug, on: !it.fav }); it.fav = !it.fav; renderLib(); } catch (err) { say(err.message, true); }
      };
      if (S.libKind !== 'creature') {
        card.onclick = async e => {
          const del = e.target.closest('.nbs-del');
          if (del) {
            e.stopPropagation();
            if (!del.classList.contains('sure')) { del.classList.add('sure'); del.title = 'Clique encore pour confirmer'; setTimeout(() => del.classList.remove('sure'), 3000); return; }
            await post('/item-delete', { kind: S.libKind, slug: it.slug });
            if (S.item?.slug === it.slug) S.item = null;
            return loadLib();
          }
          show('creer'); setKind(S.libKind); showItem(it);
        };
        return;
      }
      card.onclick = async e => {
        if (S.fuse) {  // mode fusion : on choisit deux créatures
          const i = S.fuse.indexOf(card.dataset.s);
          if (i >= 0) S.fuse.splice(i, 1); else S.fuse = [...S.fuse, card.dataset.s].slice(-2);
          fuseBar();
          return renderLib();
        }
        const del = e.target.closest('.nbs-del');
        if (del) {
          e.stopPropagation();
          if (!del.classList.contains('sure')) { del.classList.add('sure'); del.title = 'Clique encore pour confirmer'; setTimeout(() => del.classList.remove('sure'), 3000); return; }
          await post('/delete', { slug: card.dataset.s });
          if (S.cr?.slug === card.dataset.s) { S.cr = null; renderSheet(); }
          return loadLib();
        }
        await open(card.dataset.s);
        show(S.cr.pending ? 'creer' : 'dirs');
      };
    });
  }
  $('#q').oninput = renderLib;
  function fuseBar() {
    $('#fuseBar').hidden = !S.fuse;
    if (!S.fuse) return;
    const names = S.fuse.map(s => libCache.find(c => c.slug === s)?.name || s);
    $('#fuseMsg').textContent = names.length ? names.join(' + ') + (names.length < 2 ? ' + … (choisis-en une autre)' : '') : 'Choisis deux créatures finies.';
    $('#fuseGo').disabled = S.fuse.length !== 2;
  }
  $('#fuseBtn').onclick = () => { S.fuse = S.fuse ? null : []; fuseBar(); renderLib(); };
  $('#fuseStop').onclick = () => { S.fuse = null; fuseBar(); renderLib(); };
  $('#fuseGo').onclick = () => {
    const [a, b] = S.fuse || [];
    if (!b) return;
    S.fuse = null; fuseBar(); show('creer');
    runJob(() => post('/fuse', { a, b }));
  };

  // ------------------------------------------------------------ équilibrage du bestiaire
  async function loadBalance() {
    const box = $('#eq');
    let B;
    try { B = await get('/balance'); } catch (e) { box.innerHTML = `<div class="nbs-hint">${esc(e.message)}</div>`; return; }
    if (!B.total) { box.innerHTML = '<div class="nbs-hint">Aucune créature avec une fiche de combat pour l\'instant.</div>' + (B.alertes.length ? `<ul class="nbs-alerts">${B.alertes.map(a => `<li>${esc(a)}</li>`).join('')}</ul>` : ''); return; }
    const pct = n => Math.round(100 * n / B.total);
    box.innerHTML = `<div class="nbs-cols nbs-eq">
      <div class="grow">
        <div class="nbs-title">Raretés · ${B.total} créature${B.total > 1 ? 's' : ''}</div>
        <div class="nbs-eqbars">${B.raretes.map((r, i) => `<span class="nbs-rare r${i}">${esc(r.nom)}</span>
          <i title="attendu : environ ${r.attendu} %"><b class="r${i}" style="width:${pct(r.n)}%"></b><u style="left:${r.attendu}%"></u></i>
          <em>${r.n} · ${pct(r.n)} %</em>`).join('')}</div>
        
        <div class="nbs-title" style="margin-top:14px">Types</div>
        <div class="nbs-eqtypes">${B.types.map(t => `<span class="nbs-eqtype${t.n ? '' : ' none'}"><b>${t.n}</b>${esc(t.type)}</span>`).join('')}</div>
        <div class="nbs-title" style="margin-top:14px">Moyennes</div>
        <div class="nbs-eqavg">${Object.entries(STAT).map(([k, l]) => `<span><b>${B.moyennes[k]}</b>${l}</span>`).join('')}</div>
      </div>
      <div class="grow">
        <div class="nbs-title">À surveiller</div>
        ${B.alertes.length ? `<ul class="nbs-alerts">${B.alertes.map(a => `<li>${esc(a)}</li>`).join('')}</ul>` : '<div class="nbs-ok">✓ Bestiaire équilibré</div>'}
        ${B.conseils?.length ? `<div class="nbs-title" style="margin-top:14px">Raretés conseillées</div>
        
        <div class="nbs-eqlist">${B.conseils.map(t => `<div class="nbs-eqrow nbs-tip"><span class="nm">${esc(t.nom)} <span class="nbs-hint">· prestige ${t.prestige}</span></span>
          <span class="nbs-rare r${RAR.indexOf(t.actuelle)}">${esc(t.actuelle)}</span>→<span class="nbs-rare r${RAR.indexOf(t.conseillee)}">${esc(t.conseillee)}</span>
          <button class="nbs-btn dark sm" data-tip="${esc(t.slug)}" data-r="${esc(t.conseillee)}">Appliquer</button></div>`).join('')}</div>` : ''}
        <div class="nbs-title" style="margin-top:14px">Classement</div>
        <div class="nbs-eqlist">${B.creatures.sort((x, y) => y.total - x.total).map(c => `<div class="nbs-eqrow" data-s="${esc(c.slug)}">
          <img src="${U}lib/${encodeURIComponent(c.slug)}/sprites/bas_repos.png" alt=""><span class="nm">${esc(c.nom)}</span>
          <span class="nbs-rare r${RAR.indexOf(c.rarete)}">${esc(c.rarete)}</span>${String(c.type || '').split(' et ').map(t => `<span class="nbs-chip">${esc(t)}</span>`).join('')}
          <em>${c.total}</em>${c.variantes ? `<span class="nbs-hint">+${c.variantes} var.</span>` : ''}</div>`).join('')}</div>
      </div></div>`;
    $$('#eq .nbs-eqrow[data-s]').forEach(row => row.onclick = async () => { await open(row.dataset.s); show('dirs'); });
    $$('#eq [data-tip]').forEach(b => b.onclick = async () => {
      b.disabled = true;
      try { await post('/rarity', { slug: b.dataset.tip, rarete: b.dataset.r }); if (S.cr?.slug === b.dataset.tip) refresh(await get('/creature?slug=' + encodeURIComponent(b.dataset.tip))); loadBalance(); }
      catch (e) { b.disabled = false; say(e.message, true); }
    });
  }

  // ------------------------------------------------------------ démarrage
  renderSheet();
  try {
    if (await setup()) {
      const lib = await get('/library');
      if (lib.length) await open(lib[0].slug);
    }
  } catch (e) {
    $('#st span').textContent = 'Moteur indisponible : ' + e.message;
  }
}
