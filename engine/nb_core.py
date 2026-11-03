# -*- coding: utf-8 -*-
"""NeoBestiary Studio - moteur de reprompting (sans dépendance graphique).

Pipeline : texte FR -> analyse anatomique (lexique) -> fiche structurée ->
prompt anglais (compact ou détaillé). Fonctionne hors-ligne ; la traduction
en ligne n'est qu'un complément.
"""
import re
import json
import colorsys
import unicodedata
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------

def fold(text):
    """minuscules, sans accents, apostrophes normalisées."""
    text = (text or "").lower().replace("’", "'").replace("‘", "'")
    text = text.replace("œ", "oe").replace("æ", "ae")
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


NUM_FR = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6,
          "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12}
NUM_EN = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
          8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def num_en(n):
    return NUM_EN.get(n, str(n))


def estimate_tokens(text):
    """Estimation grossière du nombre de tokens CLIP."""
    return int(len(re.findall(r"\w+|[^\w\s]", text)) * 1.15)


# --------------------------------------------------------------------------
# Traduction (optionnelle, en ligne)
# --------------------------------------------------------------------------

def translate_to_english(text, source="fr", timeout=15):
    text = (text or "").strip()
    if not text:
        return ""
    chunks, remaining = [], text
    while remaining:
        if len(remaining) <= 1500:
            chunks.append(remaining)
            break
        cut = remaining.rfind(". ", 0, 1500)
        cut = cut + 1 if cut > 300 else 1500
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].strip()
    out = []
    for chunk in chunks:
        query = urllib.parse.urlencode({"client": "gtx", "sl": source, "tl": "en",
                                        "dt": "t", "q": chunk})
        url = "https://translate.googleapis.com/translate_a/single?" + query
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out.append("".join(part[0] for part in data[0] if part and part[0]))
    return " ".join(out)


# --------------------------------------------------------------------------
# Lexique : créatures
# --------------------------------------------------------------------------
# Chaque entrée : en + traits par emplacement. "{n}" = nombre (remplaçable).

def _c(en, head=None, body=None, legs=None, tail=None, wings=None, horns=None,
       arms=None, default_n=None, extra=None):
    return dict(en=en, head=head, body=body, legs=legs, tail=tail, wings=wings,
                horns=horns, arms=arms, default_n=default_n, extra=extra)


CREATURES = {
    "taureau": _c("bull", "a bull head with a broad muzzle and thick curved horns",
                  "a muscular bull body with heavy shoulders", "{n} thick hooved bull legs",
                  "a tufted bull tail", None, "two thick curved bull horns", None, "four"),
    "minotaure": _c("minotaur", "a bull head with thick curved horns and flared nostrils",
                    "a hulking muscular humanoid body", "{n} heavy muscular legs", None, None,
                    "two thick curved horns", "two huge muscular arms", "two"),
    "araignee": _c("spider", "a spider head with many glossy eyes and fangs",
                   "a bulbous armored spider body",
                   "{n} long jointed spider legs", None, None, None, None, "eight"),
    "scorpion": _c("scorpion", "a scorpion head with mandibles and small eyes",
                   "a segmented armored scorpion body", "{n} jointed scorpion legs and two large pincers",
                   "a long segmented tail ending in a curved stinger", None, None, None, "eight"),
    "loup": _c("wolf", "a snarling wolf head with long snout and fangs",
               "a lean wolf body covered in thick fur", "{n} clawed wolf legs", "a bushy wolf tail",
               None, None, None, "four"),
    "lion": _c("lion", "a lion head with a thick mane and powerful jaws", "a muscular lion body",
               "{n} clawed lion paws", "a lion tail with a tufted tip", None, None, None, "four"),
    "tigre": _c("tiger", "a tiger head with fangs and striped face", "a muscular striped tiger body",
                "{n} clawed tiger paws", "a long striped tiger tail", None, None, None, "four"),
    "ours": _c("bear", "a bear head with small round ears and a heavy muzzle", "a massive bear body",
               "{n} heavy clawed bear legs", "a short stubby tail", None, None, None, "four"),
    "cerf": _c("stag", "a stag head with huge branching antlers", "a slender stag body",
               "{n} slender hooved stag legs", "a short stag tail", None, "huge branching antlers", None, "four"),
    "sanglier": _c("boar", "a boar head with two large curved tusks", "a stocky bristled boar body",
                   "{n} short hooved boar legs", "a thin curly tail", None, None, None, "four"),
    "belier": _c("ram", "a ram head with big spiral horns", "a woolly ram body", "{n} hooved ram legs",
                 "a short tail", None, "big spiral ram horns", None, "four"),
    "bouc": _c("goat", "a goat head with a beard and curved horns", "a wiry goat body",
               "{n} hooved goat legs", "a short tail", None, "long curved goat horns", None, "four"),
    "cheval": _c("horse", "a horse head with a long muzzle and flowing mane", "a powerful horse body",
                 "{n} hooved horse legs", "a long flowing horse tail", None, None, None, "four"),
    "chat": _c("cat", "a cat head with pointed ears and slit pupils", "a sleek feline body",
               "{n} padded clawed paws", "a long slender tail", None, None, None, "four"),
    "chien": _c("dog", "a dog head with floppy or pointed ears", "a sturdy dog body",
                "{n} dog legs", "a dog tail", None, None, None, "four"),
    "renard": _c("fox", "a fox head with a pointed snout and big ears", "a slim fox body",
                 "{n} slender fox legs", "a big bushy fox tail", None, None, None, "four"),
    "rat": _c("rat", "a rat head with long whiskers and sharp incisors", "a hunched rat body",
              "{n} small clawed legs", "a long bare scaly tail", None, None, None, "four"),
    "chauve-souris": _c("bat", "a bat head with huge ears",
                        "a small furry bat body", "{n} small clawed legs", None,
                        "large leathery bat wings with long finger bones", None, None, "two"),
    "aigle": _c("eagle", "an eagle head with a hooked beak", "a feathered eagle body",
                "{n} sharp talons", "a fan of tail feathers", "broad feathered eagle wings", None, None, "two"),
    "hibou": _c("owl", "a round owl head with huge eyes and a hooked beak",
                "a plump feathered owl body", "{n} feathered legs with talons", "short tail feathers",
                "soft rounded owl wings", None, None, "two"),
    "corbeau": _c("raven", "a raven head with a thick black beak", "a sleek feathered raven body",
                  "{n} thin clawed legs", "a wedge-shaped tail", "ragged black raven wings", None, None, "two"),
    "oiseau": _c("bird", "a bird head with a beak", "a feathered bird body", "{n} thin clawed legs",
                 "tail feathers", "feathered wings", None, None, "two"),
    "serpent": _c("snake", "a snake head with slit pupils and fangs",
                  "a long coiled serpent body covered in scales", None, "a tapering serpent tail"),
    "dragon": _c("dragon", "a horned dragon head with fangs",
                 "an armored scaly dragon body", "{n} clawed dragon legs", "a long spiked dragon tail",
                 "large membranous dragon wings", "swept-back dragon horns", None, "four"),
    "lezard": _c("lizard", "a lizard head with slit pupils", "a scaly lizard body", "{n} clawed lizard legs",
                 "a long lizard tail", None, None, None, "four"),
    "crocodile": _c("crocodile", "a crocodile head with a long toothy snout",
                    "an armored crocodile body with bony scutes", "{n} short clawed legs",
                    "a thick muscular crocodile tail", None, None, None, "four"),
    "grenouille": _c("frog", "a wide frog head with bulging eyes and a huge mouth", "a squat warty frog body",
                     "{n} folded frog legs with webbed feet", None, None, None, None, "four"),
    "crapaud": _c("toad", "a wide toad head with bulging eyes and warty skin", "a squat warty toad body",
                  "{n} folded toad legs", None, None, None, None, "four"),
    "tortue": _c("turtle", "a turtle head with a beaked mouth", "a heavy domed turtle shell",
                 "{n} thick scaly turtle legs", "a short tail", None, None, None, "four"),
    "crabe": _c("crab", "a crab face with eyes on stalks", "a wide armored crab carapace",
                "{n} jointed crab legs and two big claws", None, None, None, None, "eight"),
    "homard": _c("lobster", "a lobster head with long antennae", "a segmented armored lobster body",
                 "{n} jointed legs and two big claws", "a fan-shaped lobster tail", None, None, None, "eight"),
    "pieuvre": _c("octopus", "a bulbous octopus head with large eyes", "a soft mantle body",
                  "{n} long curling tentacles with suckers", None, None, None, None, "eight"),
    "calmar": _c("squid", "a pointed squid mantle with large eyes", "a long tapered squid body",
                 "{n} long tentacles with suckers", None, None, None, None, "eight"),
    "meduse": _c("jellyfish", "a translucent jellyfish bell", "a translucent glowing bell body",
                 "{n} long trailing stinging tentacles", None, None, None, None, "many"),
    "poisson": _c("fish", "a fish head with large round eyes and a wide mouth",
                  "a scaly streamlined fish body with fins", None, "a forked fish tail fin"),
    "requin": _c("shark", "a shark head with rows of razor teeth",
                 "a streamlined shark body with a tall dorsal fin", None, "a powerful crescent tail fin"),
    "baleine": _c("whale", "a whale head with a huge mouth", "a massive whale body", None, "a broad whale fluke"),
    "mante": _c("mantis", "a triangular mantis head with huge compound eyes",
                "a slender green mantis thorax and abdomen", "{n} thin jointed legs",
                None, None, None, "two serrated raptorial forelegs", "four"),
    "insecte": _c("insect", "an insect head with compound eyes and antennae", "a segmented chitinous insect body",
                  "{n} jointed insect legs", None, "translucent insect wings", None, None, "six"),
    "mouche": _c("fly", "a fly head with huge compound eyes", "a hairy fly body", "{n} thin bristly legs",
                 None, "translucent veined fly wings", None, None, "six"),
    "fourmi": _c("ant", "an ant head with strong mandibles and antennae", "a segmented ant body",
                 "{n} thin jointed ant legs", None, None, None, None, "six"),
    "guepe": _c("wasp", "a wasp head with big eyes and mandibles", "a banded wasp body",
                "{n} thin legs", "a sharp stinger", "translucent wasp wings", None, None, "six"),
    "scarabee": _c("beetle", "a beetle head with mandibles", "a hard glossy beetle shell",
                   "{n} spiny beetle legs", None, "hard wing cases", None, None, "six"),
    "papillon": _c("butterfly", "a small butterfly head with antennae", "a thin furry butterfly body",
                   "{n} tiny legs", None, "huge patterned butterfly wings", None, None, "six"),
    "escargot": _c("snail", "a snail head with eye stalks", "a soft slimy body with a spiral shell",
                   None, None),
    "limace": _c("slug", "a slug head with eye stalks", "a soft slimy elongated body", None, None),
    "ver": _c("worm", "a round toothed maw", "a long segmented worm body", None, None),
    "crane": _c("skull", "a bare bone skull with hollow eye sockets", "a bony body"),
    "squelette": _c("skeleton", "a bare skull with hollow eye sockets", "an exposed rib cage and spine",
                    "{n} bony legs", None, None, None, "two bony arms", "two"),
    "humain": _c("human", "a human head", "a human torso", "{n} human legs", None, None, None,
                 "two human arms", "two"),
    "homme": _c("man", "a human male head", "a human male torso", "{n} human legs", None, None, None,
                "two human arms", "two"),
    "femme": _c("woman", "a human female head", "a human female torso", "{n} human legs", None, None,
                None, "two human arms", "two"),
    "demon": _c("demon", "a demon head with horns and burning eyes", "a muscular horned demon body",
                "{n} clawed legs", "a barbed tail", "tattered bat-like wings", "twisted demon horns",
                "two clawed arms", "two"),
    "fantome": _c("ghost", "a hollow-eyed ghostly face", "a tattered floating spectral shroud",
                  None, "a wisp of mist"),
    "hydre": _c("hydra", "several serpent heads with fangs", "a massive scaly reptilian body",
                "{n} thick clawed legs", "a thick scaly tail", None, None, None, "four"),
    "singe": _c("monkey", "a monkey head with an expressive face", "a lithe furry monkey body",
                "{n} long limbs", "a long prehensile tail", None, None, "two long arms", "four"),
    "gorille": _c("gorilla", "a gorilla head with a heavy brow", "a massive muscular gorilla body",
                  "{n} short thick legs", None, None, None, "two enormous arms", "two"),
    "mouton": _c("sheep", "a sheep head with a woolly face", "a woolly sheep body", "{n} hooved legs",
                 "a short woolly tail", None, None, None, "four"),
    "coq": _c("rooster", "a rooster head with a red comb and wattle", "a feathered rooster body",
              "{n} spurred legs", "long curved tail feathers", "short feathered wings", None, None, "two"),
    "cochon": _c("pig", "a pig head with a flat snout", "a round pig body", "{n} short hooved legs",
                 "a curly tail", None, None, None, "four"),
    "gargouille": _c("gargoyle", "a grotesque stone gargoyle head with fangs", "a crouching stone body",
                     "{n} clawed legs", "a pointed tail", "stone bat wings", "small stone horns", None, "two"),
    "golem": _c("golem", "a blocky stone head with glowing eyes", "a massive body of stacked boulders",
                "{n} thick pillar legs", None, None, None, "two huge stone arms", "two"),
}

ALIASES = {
    "boeuf": "taureau", "buffle": "taureau", "bison": "taureau", "vache": "taureau",
    "chouette": "hibou", "poulpe": "pieuvre", "couleuvre": "serpent", "vipere": "serpent",
    "cobra": "serpent", "wyrm": "dragon", "wyverne": "dragon", "salamandre": "lezard",
    "mouches": "mouche", "chevaux": "cheval", "yeux": "yeux", "loups": "loup", "oiseaux": "oiseau",
    "chimpanze": "singe", "babouin": "singe", "araignees": "araignee", "taureaux": "taureau",
    "corbeaux": "corbeau", "cerfs": "cerf", "hommes": "homme", "femmes": "femme", "os": "squelette",
    "spectre": "fantome", "revenant": "fantome", "spectral": "fantome", "diable": "demon",
    "mollusque": "escargot", "aigles": "aigle", "scorpions": "scorpion", "serpents": "serpent",
    "rats": "rat", "chats": "chat", "chiens": "chien", "requins": "requin", "crabes": "crabe",
    "poissons": "poisson", "insectes": "insecte", "tortues": "tortue", "dragons": "dragon",
    "chauves-souris": "chauve-souris", "humains": "humain", "demons": "demon",
}

MATERIALS = {
    "pierre": "carved stone", "pierres": "carved stone", "roche": "rough rock", "rocher": "rough rock",
    "rochers": "rough rock", "os": "bone", "metal": "dark metal", "acier": "steel", "fer": "rusted iron",
    "rouille": "rust", "bois": "gnarled wood", "ecorce": "tree bark", "ombre": "living shadow",
    "ombres": "living shadow", "fumee": "smoke", "brume": "mist", "feu": "fire", "flamme": "flames",
    "flammes": "flames", "braise": "glowing embers", "braises": "glowing embers", "lave": "molten lava",
    "glace": "ice", "givre": "frost", "neige": "snow", "eau": "water", "boue": "mud", "vase": "slime",
    "sable": "sand", "cristal": "crystal", "cristaux": "crystal", "or": "gold", "foudre": "lightning",
    "ronce": "thorns", "ronces": "thorns", "chair": "raw flesh", "corail": "coral", "algues": "seaweed",
    "coquillage": "seashell", "obsidienne": "obsidian", "nuit": "the night sky", "etoiles": "stars",
    "lumiere": "light", "tenebres": "darkness", "sang": "blood", "mousse": "moss", "champignons": "fungus",
}

GENERIC_NOUNS = ("monstre", "creature", "etre", "bete", "golem", "statue", "colosse", "forme",
                 "silhouette", "masse", "entite", "horreur", "abomination", "esprit")

# --------------------------------------------------------------------------
# Lexique : parties du corps
# --------------------------------------------------------------------------
# mot folded -> (slot, anglais singulier, anglais pluriel)
PARTS = {
    "tete": ("head", "head", "heads"), "tetes": ("head", "head", "heads"),
    "corps": ("body", "body", "bodies"),
    "queue": ("tail", "tail", "tails"), "queues": ("tail", "tail", "tails"),
    "patte": ("legs", "leg", "legs"), "pattes": ("legs", "leg", "legs"),
    "jambe": ("legs", "leg", "legs"), "jambes": ("legs", "leg", "legs"),
    "bras": ("arms", "arm", "arms"), "aile": ("wings", "wing", "wings"), "ailes": ("wings", "wing", "wings"),
    "corne": ("horns", "horn", "horns"), "cornes": ("horns", "horn", "horns"),
    "bois": ("horns", "antler", "antlers"),
    "bec": ("beak", "beak", "beaks"), "machoire": ("jaws", "jaw", "jaws"), "machoires": ("jaws", "jaw", "jaws"),
    "griffe": ("claws", "claw", "claws"), "griffes": ("claws", "claw", "claws"),
    "croc": ("fangs", "fang", "fangs"), "crocs": ("fangs", "fang", "fangs"),
    "nageoire": ("fins", "fin", "fins"), "nageoires": ("fins", "fin", "fins"),
    "carapace": ("shell", "shell", "shells"), "peau": ("skin", "skin", "skin"),
    "criniere": ("mane", "mane", "mane"), "museau": ("snout", "snout", "snouts"),
    "pince": ("pincers", "pincer", "pincers"), "pinces": ("pincers", "pincer", "pincers"),
    "tentacule": ("tentacles", "tentacle", "tentacles"), "tentacules": ("tentacles", "tentacle", "tentacles"),
    "torse": ("torso", "torso", "torsos"), "dos": ("back", "back", "backs"),
    "oeil": ("eyes", "eye", "eyes"), "yeux": ("eyes", "eye", "eyes"),
    "abdomen": ("abdomen", "abdomen", "abdomens"), "thorax": ("thorax", "thorax", "thoraxes"),
    "ventre": ("belly", "belly", "bellies"), "visage": ("face", "face", "faces"),
    "main": ("hands", "hand", "hands"), "mains": ("hands", "hand", "hands"),
    "pied": ("feet", "foot", "feet"), "pieds": ("feet", "foot", "feet"),
    "sabot": ("hooves", "hoof", "hooves"), "sabots": ("hooves", "hoof", "hooves"),
    "epine": ("spines", "spine", "spines"), "epines": ("spines", "spine", "spines"),
    "crete": ("crest", "crest", "crests"), "fourrure": ("fur", "fur", "fur"), "pelage": ("fur", "fur", "fur"),
    "ecaille": ("scales", "scale", "scales"), "ecailles": ("scales", "scale", "scales"),
    "plume": ("feathers", "feather", "feathers"), "plumes": ("feathers", "feather", "feathers"),
    "armure": ("armor", "armor", "armor"), "cuirasse": ("armor", "armor", "armor"),
    "bouche": ("mouth", "mouth", "mouths"), "cou": ("neck", "neck", "necks"),
    "oreille": ("ears", "ear", "ears"), "oreilles": ("ears", "ear", "ears"),
    "dent": ("teeth", "tooth", "teeth"), "dents": ("teeth", "tooth", "teeth"),
    "langue": ("tongue", "tongue", "tongues"), "doigts": ("fingers", "finger", "fingers"),
}
PLURAL_SLOTS = {"legs", "arms", "wings", "horns", "claws", "fangs", "eyes", "tentacles", "spines", "scales",
                "feathers", "ears", "teeth", "hands", "feet", "hooves", "pincers", "fins", "fingers"}
# slots qui disposent de traits dans le lexique des créatures
TRAIT_SLOTS = ("head", "body", "legs", "tail", "wings", "horns", "arms")
SLOT_LABEL_FR = {"head": "Tête", "body": "Corps", "legs": "Pattes / jambes", "tail": "Queue",
                 "wings": "Ailes", "horns": "Cornes", "arms": "Bras", "beak": "Bec", "jaws": "Mâchoires",
                 "claws": "Griffes", "fangs": "Crocs", "fins": "Nageoires", "shell": "Carapace",
                 "skin": "Peau", "mane": "Crinière", "snout": "Museau", "pincers": "Pinces",
                 "tentacles": "Tentacules", "torso": "Torse", "back": "Dos", "eyes": "Yeux",
                 "abdomen": "Abdomen", "thorax": "Thorax", "belly": "Ventre", "face": "Visage",
                 "hands": "Mains", "feet": "Pieds", "hooves": "Sabots", "spines": "Épines",
                 "crest": "Crête", "fur": "Fourrure", "scales": "Écailles", "feathers": "Plumes",
                 "armor": "Armure", "mouth": "Bouche", "neck": "Cou", "ears": "Oreilles",
                 "teeth": "Dents", "tongue": "Langue", "fingers": "Doigts"}
SLOT_ORDER = ["head", "face", "eyes", "snout", "beak", "mouth", "jaws", "fangs", "teeth", "tongue", "horns",
              "ears", "mane", "neck", "body", "torso", "back", "belly", "thorax", "abdomen", "shell", "skin",
              "fur", "scales", "feathers", "armor", "spines", "crest", "arms", "hands", "claws", "pincers",
              "legs", "feet", "hooves", "tentacles", "fins", "wings", "tail"]

# --------------------------------------------------------------------------
# Couleurs, adjectifs, poses, environnements
# --------------------------------------------------------------------------

_COLOR_BASE = {
    "noir": "black", "blanc": "white", "rouge": "red", "bleu": "blue", "vert": "green",
    "violet": "violet", "rose": "pink", "jaune": "yellow", "dore": "gold", "argente": "silver",
    "gris": "gray", "brun": "brown", "marron": "brown", "orange": "orange", "cyan": "cyan",
    "turquoise": "turquoise", "ecarlate": "scarlet", "pourpre": "purple", "cramoisi": "crimson",
    "ivoire": "ivory", "cuivre": "copper", "bronze": "bronze", "rouille": "rust-colored",
    "emeraude": "emerald green", "azur": "azure blue", "indigo": "indigo", "ambre": "amber",
    "cendre": "ash gray", "pale": "pale", "ocre": "ochre",
}
COLOR_FORMS = {}
for _fr, _en in _COLOR_BASE.items():
    for _suffix in ("", "e", "s", "es"):
        COLOR_FORMS[_fr + _suffix] = _en
COLOR_FORMS.update({"blanche": "white", "blanches": "white", "blancs": "white", "noirs": "black",
                    "verdatre": "greenish", "verdatres": "greenish", "bleuatre": "bluish",
                    "rougeatre": "reddish", "grisatre": "grayish", "jaunatre": "yellowish",
                    "violette": "violet", "violettes": "violet", "doree": "gold", "dorees": "gold",
                    "dores": "gold", "argentee": "silver", "argentees": "silver", "argentes": "silver",
                    "rougeoyant": "glowing red", "rougeoyants": "glowing red", "rougeoyantes": "glowing red",
                    "cuivree": "copper", "bronzee": "bronze"})

COLOR_RAMPS = {
    "black": ["#0b0b12", "#1f1f2b", "#3a3a4b", "#666679", "#a0a0b4"],
    "white": ["#6b6f85", "#a4a8bd", "#d3d6e4", "#eceef6", "#ffffff"],
    "red": ["#2a0d14", "#6b1620", "#b02a2e", "#e05545", "#f6a283"],
    "scarlet": ["#2a0d14", "#6b1620", "#b02a2e", "#e05545", "#f6a283"],
    "crimson": ["#240a14", "#5c1226", "#9c1f3a", "#d23c52", "#f08a9a"],
    "blue": ["#0d1633", "#1d3770", "#3566b8", "#6a9be0", "#bcd6f7"],
    "azure blue": ["#0d1f3a", "#1d4e84", "#2f86c4", "#6cb9e8", "#c3e7f9"],
    "green": ["#0e2418", "#1f4a2b", "#3b7a3d", "#7dad54", "#c5de97"],
    "emerald green": ["#08241f", "#0f5040", "#17896a", "#4cc49a", "#b5efd8"],
    "violet": ["#1c1233", "#412a73", "#6c47b8", "#a285e0", "#dacdf6"],
    "purple": ["#1c1233", "#412a73", "#6c47b8", "#a285e0", "#dacdf6"],
    "indigo": ["#120f33", "#2a2275", "#4739b5", "#7e72e0", "#c6c0f6"],
    "pink": ["#3a1230", "#8a2c66", "#d1559a", "#f290c3", "#fcd2e8"],
    "yellow": ["#33290a", "#7a6414", "#c9a62a", "#f0d04d", "#fbf0a6"],
    "gold": ["#2e2008", "#7a5612", "#c28b24", "#eac05a", "#faeaa8"],
    "silver": ["#2b2e3a", "#585d70", "#8d93a8", "#c0c5d6", "#eceff8"],
    "gray": ["#1c1e26", "#3b3f4d", "#646a7c", "#9aa0b2", "#d2d6e2"],
    "ash gray": ["#1c1e26", "#3b3f4d", "#646a7c", "#9aa0b2", "#d2d6e2"],
    "brown": ["#241810", "#4b3220", "#7a5232", "#aa7b4e", "#d9b88c"],
    "orange": ["#2e1408", "#7a3512", "#c8601f", "#f09040", "#fbcf94"],
    "cyan": ["#082530", "#124f66", "#1e8aa6", "#4dc4d8", "#aeeaf2"],
    "turquoise": ["#08272a", "#10575c", "#1b9296", "#4fd0c8", "#b4f2ea"],
    "ivory": ["#4a4538", "#8a826c", "#c9c0a4", "#eae2c8", "#fbf6e6"],
    "copper": ["#2a140c", "#6a3320", "#a8582f", "#d98a55", "#f2c8a0"],
    "bronze": ["#261a0c", "#5e4219", "#946a2a", "#c8964c", "#ead0a0"],
    "amber": ["#2e1a06", "#7a4a0e", "#c7801a", "#f0aa3a", "#fad98e"],
    "ochre": ["#2b200c", "#6e5320", "#a8812f", "#d3ae5a", "#efdca4"],
    "rust-colored": ["#2a120a", "#6a2a14", "#a5441f", "#d27a40", "#efb98a"],
}

PALETTES = {
    "Auto (selon la description)": [],
    "Créature des mers": ["#101D35", "#24536B", "#3D8B91", "#A4D7C9", "#E6E6D2"],
    "Nuit / spectre": ["#17152B", "#30264E", "#59447D", "#9A83C4", "#D8D0F4"],
    "Orage / foudre": ["#202638", "#414C66", "#777E9C", "#A8D8E8", "#E6F7FF"],
    "Forêt / poison": ["#172B27", "#315B43", "#65834D", "#A9A65D", "#D8D5A2"],
    "Feu / volcan": ["#271B27", "#71333A", "#C45136", "#F09A43", "#F5D58B"],
    "Glace": ["#1A2B43", "#426D91", "#78AFC4", "#B9E2E6", "#F0FAF8"],
    "Royal / sacré": ["#29213B", "#61477B", "#B38A62", "#E6CB91", "#FFF0D0"],
    "Terre / roche": ["#302820", "#65503B", "#967650", "#C2A77A", "#E3D4B4"],
    "Os / catacombes": ["#1b1714", "#4a3f35", "#8c7b66", "#cbbba0", "#f1e9d6"],
    "Marais / toxique": ["#14231a", "#2c4a2a", "#5d7d2b", "#a3b53a", "#e0e58a"],
    "Sang / carmin": ["#1f0b12", "#5a1424", "#9a1f33", "#d9485a", "#f6b0b4"],
    "Game Boy": ["#0f380f", "#306230", "#8bac0f", "#9bbc0f"],
    "Personnalisée": ["#202033", "#51466F", "#8B6CCB", "#C3B1ED", "#F0EAFB"],
}
AUTO_PALETTE = "Auto (selon la description)"
CUSTOM_PALETTE = "Personnalisée"

PALETTE_KEYWORDS = {
    "Créature des mers": ["mer", "maree", "ocean", "rivage", "pecheur", "poisson", "algue", "recif", "vague",
                          "abysse", "naufrage", "marin", "plage", "cote", "ecume", "sirene", "corail"],
    "Nuit / spectre": ["nuit", "ombre", "spectre", "fantome", "sinistre", "lune", "reve", "cauchemar", "ame",
                       "hante", "tenebre", "crepuscule", "minuit"],
    "Orage / foudre": ["orage", "eclair", "foudre", "nuage", "tempete", "tonnerre", "electri"],
    "Forêt / poison": ["foret", "bois ", "feuille", "mousse", "druide", "sylvestre", "arbre", "racine"],
    "Marais / toxique": ["marais", "poison", "venin", "toxique", "vase", "boue", "acide", "pestilen", "putride"],
    "Feu / volcan": ["feu", "flamme", "volcan", "cendre", "lave", "braise", "brule", "ardent", "infernal"],
    "Glace": ["glace", "neige", "gel", "givre", "froid", "blizzard", "polaire", "glacier"],
    "Royal / sacré": ["roi", "reine", "sacre", "divin", "ange", "saint", "dore", "couronne", "temple", "celeste"],
    "Terre / roche": ["roche", "pierre", "montagne", "terre", "grotte", "caverne", "falaise", "canyon", "desert", "sable"],
    "Os / catacombes": ["os ", "ossements", "squelette", "crane", "tombe", "cimetiere", "crypte", "catacombe", "mort-vivant"],
    "Sang / carmin": ["sang", "carnage", "cruel", "sanguinaire", "rouge sang", "massacre"],
}

ENV_DETAILS = {
    "mer": "wet glistening surface with barnacle and seaweed details",
    "rivage": "wet glistening surface with barnacle and seaweed details",
    "ocean": "wet glistening surface with barnacle and seaweed details",
    "maree": "wet glistening surface with barnacle and seaweed details",
    "marais": "slimy mud-covered skin",
    "volcan": "glowing ember cracks and ash",
    "glace": "frost crystals and icy sheen",
    "neige": "frost crystals and icy sheen",
    "foret": "moss, bark and leaf details",
    "desert": "sun-bleached sandy texture",
    "grotte": "pale cave-dweller look",
    "caverne": "pale cave-dweller look",
    "cimetiere": "grave dirt and bone fragments",
    "orage": "crackling electric sparks",
    "nuit": "nocturnal look with cool moonlit highlights",
    "ruines": "ancient weathered look",
}

POSE_VERBS = [
    (("surgit", "bondit", "attaque", "charge", "se jette", "fonce", "chasse"), "aggressive lunging pose"),
    (("hurle", "rugit", "crie", "beugle", "gronde"), "roaring pose with open mouth"),
    (("rampe", "glisse", "serpente"), "low crawling pose"),
    (("vole", "plane", "survole"), "airborne pose with wings spread"),
    (("nage", "emerge"), "rising pose, emerging"),
    (("dort", "repose", "sommeille"), "resting coiled pose"),
    (("guette", "observe", "surveille", "veille", "epie"), "alert watchful stance"),
    (("frappent", "frappe", "martele", "pietine"), "stomping stance with raised legs"),
]

ADJECTIVES = {
    "lumineux": "glowing", "lumineuse": "glowing", "lumineuses": "glowing", "brillant": "glowing",
    "brillants": "glowing", "brillantes": "glowing", "incandescent": "incandescent", "incandescents": "incandescent",
    "vide": "hollow empty", "vides": "hollow empty", "globuleux": "bulging", "globuleuses": "bulging",
    "multiples": "multiple", "enormes": "huge", "immenses": "huge", "geants": "giant", "minuscules": "tiny",
    "acerees": "sharp", "aceree": "sharp", "acerees": "sharp", "tranchantes": "razor-sharp",
    "tranchants": "razor-sharp", "griffues": "clawed", "velu": "hairy", "velus": "hairy", "velue": "hairy",
    "ecailleux": "scaly", "ecailleuse": "scaly", "visqueux": "slimy", "visqueuse": "slimy",
    "translucide": "translucent", "translucides": "translucent", "tordues": "twisted", "tordus": "twisted",
    "recourbees": "curved", "recourbes": "curved", "courbes": "curved", "longues": "long", "longs": "long",
    "pointues": "pointed", "dechiquetees": "tattered", "dechiquetes": "tattered", "osseux": "bony",
    "osseuses": "bony", "articulees": "jointed", "articules": "jointed", "fines": "thin", "fins": "thin",
    "epais": "thick", "epaisses": "thick", "puissants": "powerful", "puissantes": "powerful",
    "luisants": "glossy", "luisantes": "glossy", "noueux": "gnarled", "noueuses": "gnarled",
}
SCALE_WORDS = {
    "geant": "huge imposing", "geante": "huge imposing", "colossal": "huge imposing", "colossale": "huge imposing",
    "massif": "massive heavy build", "massive": "massive heavy build", "gigantesque": "huge imposing",
    "minuscule": "small and compact", "petit": "small and compact", "petite": "small and compact",
    "elance": "slender elegant build", "elancee": "slender elegant build", "squelettique": "gaunt skeletal build",
    "trapu": "stocky build", "trapue": "stocky build", "difforme": "deformed asymmetrical build",
}

# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------
# nom -> (version détaillée, version courte)
STYLES = {
    "Pokémon-like (monstre à collectionner)": (
        "front-facing monster battle sprite for a creature-collecting RPG, original creature design, clean thick dark outline, "
        "flat cel shading with three tones per color, bright saturated colors, simple expressive eyes, compact chunky "
        "proportions, high contrast, crisp pixel art, no gradients",
        "creature-collecting RPG monster battle sprite, thick dark outline, flat cel shading, bright saturated colors, chunky proportions"),
    "RPG pixel art": ("polished retro RPG pixel art, crisp pixel clusters, clean pixel placement, sharp hard edges, readable silhouette",
                      "retro RPG pixel art, crisp pixels"),
    "Mignon / Kawaii": ("cute kawaii monster sprite, chibi proportions, big round head, large shiny eyes, soft rounded shapes, friendly expression, bright cheerful colors, polished crisp pixel art",
                        "cute kawaii chibi pixel art monster, big head, big shiny eyes, rounded shapes"),
    "Chibi (grosse tête)": ("chibi monster sprite, head as large as the body, tiny limbs, simple expressive face, bold outline, polished crisp pixel art",
                            "chibi pixel art monster, oversized head, tiny limbs, bold outline"),
    "Collectionneur de monstres": ("creature-collector monster battle sprite, appealing original design, bold outline, clear color blocks, readable shapes, polished pixel art",
                                   "monster battle sprite, appealing design, bold outline, clear color blocks"),
    "Cartoon contour épais": ("cartoon pixel art monster, thick dark outline, flat bright colors, exaggerated shapes, playful design",
                              "cartoon pixel art monster, thick outline, flat bright colors"),
    "16-bit JRPG": ("high quality 16-bit JRPG monster sprite, carefully clustered pixels, bold outline, rich but controlled pixel shading",
                    "16-bit JRPG monster sprite, bold outline"),
    "SNES fantasy": ("SNES era fantasy RPG pixel art, rich clustered shading, strong outline, detailed but readable sprite",
                     "SNES fantasy pixel art sprite, strong outline"),
    "NES 8-bit": ("NES 8-bit pixel art sprite, very limited palette, chunky pixels, simple shapes, strong silhouette",
                  "NES 8-bit pixel art sprite, limited palette, chunky pixels"),
    "Game Boy": ("Game Boy era pixel art sprite, four-tone monochrome green palette, precise chunky pixels",
                 "Game Boy pixel art, four-tone green"),
    "Game Boy Color / GBA": ("Game Boy Advance era pixel art monster sprite, vibrant saturated colors, clean outline, soft pixel shading",
                             "GBA pixel art monster sprite, vibrant colors, clean outline"),
    "Arcade / Neo-Geo": ("arcade fighting game boss sprite, large detailed pixel art, dramatic shading, strong rim light",
                         "arcade pixel art boss sprite, dramatic shading"),
    "32x32 minimal": ("designed for a 32x32 game sprite, extremely readable silhouette, simplified anatomy, large recognizable face, very limited palette",
                      "tiny 32x32 sprite, simple readable silhouette, very few colors"),
    "Roguelike / carte": ("top-down roguelike monster tile style, bold simple shapes, high contrast, minimal detail",
                          "roguelike monster sprite, bold simple shapes"),
    "Dark fantasy": ("dark fantasy bestiary creature, ominous atmosphere expressed through shapes and palette, polished crisp pixel art",
                     "dark fantasy pixel art creature, ominous"),
    "Horreur / sinistre": ("horror monster sprite, grotesque unsettling anatomy, sickly desaturated colors, glowing eyes, polished crisp pixel art",
                           "horror pixel art monster, grotesque, desaturated, glowing eyes"),
    "Abyssal / lovecraftien": ("eldritch deep-sea horror creature, bioluminescent details, tentacles and strange eyes, dark teal palette, polished crisp pixel art",
                               "eldritch abyssal pixel art creature, bioluminescent"),
    "Gothique": ("gothic fantasy creature, ornate spiky shapes, dark purple and bone tones, dramatic silhouette, polished crisp pixel art",
                 "gothic pixel art creature, spiky ornate shapes"),
    "Steampunk": ("steampunk mechanical creature, brass gears, rivets and pipes, copper and brown tones, polished crisp pixel art",
                  "steampunk pixel art creature, brass gears, copper tones"),
    "Cyberpunk néon": ("cyberpunk neon creature, glowing neon accents, dark body, magenta and cyan highlights, polished crisp pixel art",
                       "cyberpunk neon pixel art creature, magenta cyan glow"),
    "Conte de fées / doux": ("storybook fairy tale creature, soft pastel colors, gentle rounded shapes, whimsical details, polished crisp pixel art",
                             "fairy tale pastel pixel art creature, gentle rounded shapes"),
    "Slime & gelée": ("gelatinous translucent creature, glossy highlights, bouncy rounded body, simple face, polished crisp pixel art",
                      "glossy gelatinous pixel art creature, bouncy rounded body"),
    "Boss imposant": ("huge imposing boss monster sprite, intricate detail, heavy armored shapes, menacing presence, polished crisp pixel art",
                      "imposing boss monster pixel art, intricate detail, menacing"),
    "Sans style ajouté": ("", ""),
}
# Extras des styles personnalisés : nom -> dict(negative, lora, lora_strength). Rempli par l'application.
STYLE_EXTRA = {}

PROPORTIONS = {
    "Naturelles": "",
    "Chibi (grosse tête)": "chibi proportions, oversized head, small body",
    "Trapues": "stocky squat proportions, short limbs",
    "Élancées": "tall slender proportions, long limbs",
    "Imposantes (boss)": "huge imposing massive proportions",
}
MOODS = {
    "Neutre": "",
    "Mignon": "cute, adorable, friendly, big shiny eyes",
    "Menaçant": "menacing, aggressive, fierce",
    "Sinistre": "creepy, ominous, eerie",
    "Drôle": "goofy, funny expression",
    "Mélancolique": "sad, melancholic expression",
    "Majestueux": "majestic, noble, proud",
    "Endormi / calme": "sleepy, calm, peaceful",
}

# --------------------------------------------------------------------------
# Vues
# --------------------------------------------------------------------------
# clé -> (libellé FR, slug, consigne détaillée, consigne courte)
VIEWS = {
    "face": ("Face", "face",
             "FRONT VIEW, facing directly toward the camera, symmetrical front-facing anatomy, neutral standing pose, every defining facial feature visible.",
             "front view, facing the camera"),
    "trois_quarts": ("Trois-quarts", "trois_quarts",
                     "THREE-QUARTER VIEW, body turned about 45 degrees, face and full body both clearly visible. Same creature design, same colors and proportions as the front view.",
                     "three-quarter view, same design as the front view"),
    "dos": ("Dos", "dos",
            "BACK VIEW, creature facing away from the camera, show the back anatomy, back markings, rear silhouette and tail attachment. Same creature design, same colors and proportions as the front view.",
            "back view, seen from behind, same design as the front view"),
    "gauche": ("Côté gauche", "gauche",
               "LEFT SIDE PROFILE VIEW, creature facing left, exact side profile, full body silhouette and limb placement visible. Same creature design, same colors and proportions as the front view.",
               "left side profile, facing left, same design as the front view"),
    "droite": ("Côté droit", "droite",
               "RIGHT SIDE PROFILE VIEW, creature facing right, exact side profile, full body silhouette and limb placement visible. Same creature design, same colors and proportions as the front view.",
               "right side profile, facing right, same design as the front view"),
}
VIEW_KEYS = list(VIEWS)

# --------------------------------------------------------------------------
# Noms de couleurs à partir de l'hexadécimal
# --------------------------------------------------------------------------

def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def color_name(hex_color):
    r, g, b = hex_to_rgb(hex_color)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h *= 360
    if v < 0.16:
        return "near-black"
    if s < 0.13 or (v < 0.4 and s < 0.35):
        if v < 0.4:
            return "dark gray"
        if v < 0.68:
            return "gray"
        if v < 0.9:
            return "light gray"
        return "off-white"
    if h < 15 or h >= 345:
        base = "red"
    elif h < 40:
        base = "orange" if v > 0.5 else "brown"
    elif h < 65:
        base = "yellow" if v > 0.55 else "olive"
    elif h < 160:
        base = "green"
    elif h < 195:
        base = "teal"
    elif h < 255:
        base = "blue"
    elif h < 290:
        base = "violet"
    else:
        base = "magenta" if s > 0.5 else "pink"
    if v < 0.38:
        return "deep " + base
    if v > 0.82 and s < 0.5:
        return "pale " + base
    return base


def palette_color_names(palette):
    names = []
    for color in palette:
        n = color_name(color)
        if n not in names:
            names.append(n)
    return names

# --------------------------------------------------------------------------
# Analyse
# --------------------------------------------------------------------------

def lookup_creature(word):
    """Retourne la clé de créature pour un mot (singulier/pluriel/alias)."""
    w = word.strip("-'").lower()
    if "'" in w:
        w = w.split("'")[-1]
    candidates = [w]
    if w.endswith("s"):
        candidates.append(w[:-1])
    if w.endswith("x"):
        candidates.append(w[:-1])
    if w.endswith("aux"):
        candidates.append(w[:-3] + "al")
    for cand in candidates:
        if cand in ALIASES:
            cand = ALIASES[cand]
        if cand in CREATURES:
            return cand
    return None


def lookup_material(word):
    w = word.strip("-'")
    if "'" in w:
        w = w.split("'")[-1]
    return MATERIALS.get(w)


_PART_ALT = "|".join(sorted(PARTS, key=len, reverse=True))
_ARTICLE = (r"(?:de\s+la\s+|de\s+l'\s*|d'\s*(?:un\s+|une\s+)?|du\s+|des\s+|"
            r"de\s+(?:un\s+|une\s+)?|en\s+)")
PART_OF_RE = re.compile(r"\b(" + _PART_ALT + r")\b\s+" + _ARTICLE + r"([a-z][a-z\-]*)")
_NUM_ALT = "|".join(sorted(NUM_FR, key=len, reverse=True))
COUNT_RE = re.compile(r"\b(\d+|" + _NUM_ALT + r")\s+(?:[a-z]+\s+)?(" + _PART_ALT + r")\b")
_COLOR_ALT = "|".join(sorted(COLOR_FORMS, key=len, reverse=True))
COLOR_PART_RE = re.compile(r"\b(" + _PART_ALT + r")\b\s+(?:[a-z]+\s+)?(" + _COLOR_ALT + r")\b")
COLOR_ANY_RE = re.compile(r"\b(" + _COLOR_ALT + r")\b")
_ADJ_ALT = "|".join(sorted(ADJECTIVES, key=len, reverse=True))
ADJ_PART_RE = re.compile(r"\b(" + _PART_ALT + r")\b\s+(" + _ADJ_ALT + r")\b")
GENERIC_MAT_RE = re.compile(r"\b(?:" + "|".join(GENERIC_NOUNS) + r")\s+(?:de\s+la\s+|de\s+l'\s*|d'\s*|de\s+|du\s+|en\s+)([a-z]+)")
HYPHEN_RE = re.compile(r"\b([a-z]+)-([a-z]+)\b")
# « juste un grand œil » : la créature n'est QUE cette partie (pas de corps autour)
ONLY_RE = re.compile(r"\b(?:juste|seulement|uniquement|rien\s+qu')\s*(?:(?:un|une|des|le|la|les)\s+|[dl]'\s*)?"
                     r"(?:[a-z]+\s+)?(" + _PART_ALT + r")\b")
# « sans corps », « pas de pattes » : parties interdites
NEG_RE = re.compile(r"\b(?:sans|pas\s+de|pas\s+d'|aucun|aucune)\s*(?:[a-z]+\s+)?(" + _PART_ALT + r")\b")
BODY_SLOTS = ("head", "body", "torso", "legs", "arms", "tail", "wings")
# « un seul grand œil », « œil unique » : compte de 1 (COUNT_RE ignore « un » pour éviter le bruit)
SINGLE_RE = re.compile(r"\b(?:un|une)\s+seule?\s+(?:[a-z]+\s+){0,2}?(" + _PART_ALT + r")\b|\b(" + _PART_ALT + r")\s+unique\b")
PLURAL_EYES_RE = re.compile(r"\b(?:many |two )?((?:[a-z\-]+ )?)eyes\b")


class Spec:
    """Fiche anatomique structurée d'une créature."""

    def __init__(self):
        self.slots = {}          # slot -> dict(kind, creature, material, en, trait, explicit)
        self.counts = {}         # slot -> int
        self.colors = []         # couleurs globales (en)
        self.part_colors = {}    # slot -> [couleurs]
        self.adjs = {}           # slot -> [adjectifs]
        self.materials = []      # matières globales
        self.pose = None
        self.env = []
        self.scale = []
        self.unknown = []        # mots non reconnus
        self.mentions = []       # créatures mentionnées
        self.hybrid = False
        self.head_creature = None
        self.body_creature = None
        self.only = None         # la créature n'est que cette partie (anglais, ex. "eye")
        self.forbidden = []      # slots interdits (« sans corps », champ « À éviter »)

    def parsed_count(self):
        return len([s for s in self.slots.values() if s.get("explicit")])


def _trait_for(slot, entry, count=None):
    trait = entry.get(slot)
    if not trait:
        return None
    if "{n}" in trait:
        n = num_en(count) if count else entry.get("default_n")
        if n == "many":
            return trait.replace("{n} ", "many ")
        if count:
            return trait.replace("{n}", "exactly " + n)
        return trait.replace("{n}", n or "several")
    return trait


def analyze(name, description, resolver=None, must="", avoid=""):
    """Analyse un texte FR. resolver(mot) -> anglais, pour les mots inconnus (optionnel).
    must / avoid : champs « Doit contenir » / « À éviter » (servent à repérer « juste un œil », « pas de corps »)."""
    spec = Spec()
    text = fold(description + " " + must)
    name_f = fold(name)

    m = ONLY_RE.search(text)
    if m:
        slot = PARTS[m.group(1)][0]
        spec.only = PARTS[m.group(1)][1]
        spec.forbidden = [s for s in BODY_SLOTS if s != slot]
    for m in NEG_RE.finditer(text):
        slot = PARTS[m.group(1)][0]
        if slot not in spec.forbidden:
            spec.forbidden.append(slot)
    for word in re.findall(r"[a-z]+", fold(avoid)):
        if word in PARTS and PARTS[word][0] not in spec.forbidden:
            spec.forbidden.append(PARTS[word][0])

    # nombres explicites
    for m in COUNT_RE.finditer(text):
        raw, part = m.group(1), m.group(2)
        n = int(raw) if raw.isdigit() else NUM_FR[raw]
        slot = PARTS[part][0]
        if n >= 2 or slot in ("head", "tail"):
            spec.counts[slot] = n
    for m in SINGLE_RE.finditer(text):
        spec.counts[PARTS[m.group(1) or m.group(2)][0]] = 1

    # X de Y
    for m in PART_OF_RE.finditer(text):
        part, word = m.group(1), m.group(2)
        slot, en_sing, en_plur = PARTS[part]
        if slot in spec.slots and spec.slots[slot].get("explicit"):
            continue
        mat = lookup_material(word)
        cre = lookup_creature(word)
        count = spec.counts.get(slot)
        if cre and not (mat and word in ("os",)):
            entry = CREATURES[cre]
            trait = _trait_for(slot, entry, count) if slot in TRAIT_SLOTS else None
            if not trait:
                noun = en_plur if (slot in PLURAL_SLOTS and count != 1) or (count and count > 1) else en_sing
                trait = (f"{num_en(count)} " if count and count > 1 else "") + f"{entry['en']} {noun}"
            spec.slots[slot] = dict(kind="creature", creature=cre, en=entry["en"], trait=trait, explicit=True)
            if slot == "head":
                spec.head_creature = cre
            if slot == "body":
                spec.body_creature = cre
            if cre not in spec.mentions:
                spec.mentions.append(cre)
        elif mat:
            noun = en_plur if (slot in PLURAL_SLOTS and count != 1) or (count and count > 1) else en_sing
            trait = f"{noun} made of {mat}"
            if slot == "body":
                trait = f"a body made of {mat}"
            spec.slots[slot] = dict(kind="material", creature=None, en=mat, trait=trait, explicit=True)
        else:
            en = None
            if resolver:
                try:
                    en = resolver(word)
                except Exception:
                    en = None
            if word not in spec.unknown:
                spec.unknown.append(word)
            en = en or word
            noun = en_plur if (slot in PLURAL_SLOTS and count != 1) or (count and count > 1) else en_sing
            spec.slots[slot] = dict(kind="unknown", creature=None, en=en, explicit=True,
                                    trait=f"{noun} of a {en}" if slot != "body" else f"a {en}-like body")

    # nom composé "taureau-araignée"
    if not spec.slots.get("head") and not spec.slots.get("body"):
        m = HYPHEN_RE.search(name_f)
        if m:
            a, b = lookup_creature(m.group(1)), lookup_creature(m.group(2))
            if a and b and a != b:
                ea, eb = CREATURES[a], CREATURES[b]
                spec.slots["head"] = dict(kind="creature", creature=a, en=ea["en"], trait=ea["head"], explicit=True)
                spec.slots["body"] = dict(kind="creature", creature=b, en=eb["en"], trait=eb["body"], explicit=True)
                spec.head_creature, spec.body_creature = a, b
                spec.mentions = [a, b]

    # créatures mentionnées (hors X de Y)
    for tok in re.findall(r"[a-z][a-z\-']*", text + " " + name_f):
        cre = lookup_creature(tok)
        if cre and cre not in spec.mentions:
            spec.mentions.append(cre)

    # créature unique
    if not spec.slots.get("head") and not spec.slots.get("body") and spec.mentions:
        main = spec.mentions[0]
        entry = CREATURES[main]
        for slot in ("head", "body"):
            if entry.get(slot):
                spec.slots[slot] = dict(kind="creature", creature=main, en=entry["en"],
                                        trait=entry[slot], explicit=True)
        spec.head_creature = spec.body_creature = main

    # hybride ?
    spec.hybrid = bool(spec.head_creature and spec.body_creature and spec.head_creature != spec.body_creature)

    # emplacements implicites tirés de la créature du corps
    body_c = spec.body_creature or spec.head_creature
    if body_c:
        entry = CREATURES[body_c]
        for slot in ("legs", "tail", "wings", "arms"):
            if slot not in spec.slots:
                trait = _trait_for(slot, entry, spec.counts.get(slot))
                if trait:
                    spec.slots[slot] = dict(kind="creature", creature=body_c, en=entry["en"],
                                            trait=trait, explicit=slot in spec.counts)
    if "legs" in spec.counts and "legs" not in spec.slots:
        spec.slots["legs"] = dict(kind="creature", creature=None, en="",
                                  trait=f"exactly {num_en(spec.counts['legs'])} legs", explicit=True)

    # couleurs
    for m in COLOR_PART_RE.finditer(text):
        slot = PARTS[m.group(1)][0]
        col = COLOR_FORMS[m.group(2)]
        spec.part_colors.setdefault(slot, [])
        if col not in spec.part_colors[slot]:
            spec.part_colors[slot].append(col)
    for m in COLOR_ANY_RE.finditer(text):
        col = COLOR_FORMS[m.group(1)]
        if col not in spec.colors:
            spec.colors.append(col)

    # adjectifs
    for m in ADJ_PART_RE.finditer(text):
        slot = PARTS[m.group(1)][0]
        adj = ADJECTIVES[m.group(2)]
        spec.adjs.setdefault(slot, [])
        if adj not in spec.adjs[slot]:
            spec.adjs[slot].append(adj)

    # matière globale
    for m in GENERIC_MAT_RE.finditer(text):
        mat = lookup_material(m.group(1))
        if mat and mat not in spec.materials and not lookup_creature(m.group(1)):
            spec.materials.append(mat)

    # échelle / silhouette
    for word, en in SCALE_WORDS.items():
        if re.search(r"\b" + word + r"\b", text) and en not in spec.scale:
            spec.scale.append(en)

    # pose
    for verbs, pose in POSE_VERBS:
        if any(re.search(r"\b" + v, text) for v in verbs):
            spec.pose = pose
            break

    # environnement
    for key, detail in ENV_DETAILS.items():
        if re.search(r"\b" + key, text) and detail not in spec.env:
            spec.env.append(detail)
    for slot in spec.forbidden:
        spec.slots.pop(slot, None)
    return spec


def infer_palette(description, spec=None):
    """Palette (liste de 5 hex) : couleurs explicites > habitat > défaut."""
    text = fold(description) + " "
    if spec is not None and spec.colors:
        # couleur principale : celle qui n'est pas attachée aux yeux/flammes ; accent : yeux
        eye_cols = set(spec.part_colors.get("eyes", []))
        main = [c for c in spec.colors if c not in eye_cols] or list(spec.colors)
        accent = (list(eye_cols) or [c for c in spec.colors if c != main[0]] or [None])[0]
        base = COLOR_RAMPS.get(main[0])
        if base is None:
            base = COLOR_RAMPS.get({"glowing red": "red", "greenish": "green", "bluish": "blue",
                                    "reddish": "red", "grayish": "gray", "yellowish": "yellow",
                                    "pale": "gray"}.get(main[0], "gray"), COLOR_RAMPS["gray"])
        pal = [base[0], base[1], base[2], base[3], base[4]]
        if accent and accent in COLOR_RAMPS and accent != main[0]:
            acc = COLOR_RAMPS[accent]
            pal = [base[0], base[1], base[2], acc[2], acc[4]]
        return pal
    scores = {}
    for pname, words in PALETTE_KEYWORDS.items():
        score = sum(1 for w in words if re.search(r"\b" + re.escape(w.strip()) + (r"\b" if w.endswith(" ") else ""), text))
        if score:
            scores[pname] = score
    if scores:
        best = max(scores, key=lambda k: scores[k])
        return list(PALETTES[best])
    return list(PALETTES["Nuit / spectre"])

# --------------------------------------------------------------------------
# Construction du prompt
# --------------------------------------------------------------------------

def _decorate(slot, spec, trait):
    adjs = [a for a in spec.adjs.get(slot, []) if not any(w in trait for w in a.split())]
    cols = spec.part_colors.get(slot, [])
    bits = []
    if cols:
        bits.append(" ".join(cols))
    if adjs:
        bits.append(", ".join(adjs))
    return trait + (" (" + ", ".join(bits) + ")" if bits else "")


def anatomy_rows(spec):
    """Liste (libellé FR, texte EN, explicite?) pour l'affichage de la fiche."""
    rows = []
    done = set()
    for slot in SLOT_ORDER:
        if slot in spec.slots:
            s = spec.slots[slot]
            rows.append((SLOT_LABEL_FR.get(slot, slot), _decorate(slot, spec, s["trait"]), s.get("explicit", False)))
            done.add(slot)
    for slot, cols in spec.part_colors.items():
        if slot not in done:
            rows.append((SLOT_LABEL_FR.get(slot, slot), " ".join(cols), True))
    return rows


def anatomy_sentences(spec):
    """Phrases d'anatomie ordonnées, utilisées par les deux modes de prompt."""
    out = [f"a lone disembodied {spec.only} as the whole creature"] if spec.only else []
    head, body = spec.slots.get("head"), spec.slots.get("body")
    if spec.hybrid and head and body:
        out.append(f"hybrid monster with {_decorate('head', spec, head['trait'])} on {_decorate('body', spec, body['trait'])}")
    else:
        for slot in ("head", "body"):
            if slot in spec.slots:
                out.append(_decorate(slot, spec, spec.slots[slot]["trait"]))
    for slot in SLOT_ORDER:
        if slot in ("head", "body") or slot not in spec.slots:
            continue
        s = spec.slots[slot]
        out.append(_decorate(slot, spec, s["trait"]))
    for slot, cols in spec.part_colors.items():
        if slot not in spec.slots:
            adj = ", ".join(spec.adjs.get(slot, []))
            label = PARTS_BY_SLOT.get(slot, slot)
            if spec.only and SING_BY_SLOT.get(slot) == spec.only:
                label = spec.only  # « juste un œil noir » : un œil, pas « black eyes »
            n = spec.counts.get(slot, 0)
            count = f"exactly {num_en(n)} " if n > 1 else ""  # « six tentacules violets » garde son nombre
            out.append(f"{count}{' '.join(cols)} {adj + ' ' if adj else ''}{label}")
    if spec.counts.get("eyes") == 1:
        # le lexique dit « large eyes » (pieuvre…) : un cyclope doit rester à un œil partout
        out = [PLURAL_EYES_RE.sub(r"a single \1eye", s) for s in out]
    return out


PARTS_BY_SLOT = {}
SING_BY_SLOT = {}
for _w, (_slot, _s, _p) in PARTS.items():
    PARTS_BY_SLOT.setdefault(_slot, _p)
    SING_BY_SLOT.setdefault(_slot, _s)


def must_not_lines(spec, long=False):
    lines = []
    if spec.hybrid:
        h, b = CREATURES[spec.head_creature]["en"], CREATURES[spec.body_creature]["en"]
        lines.append(f"not a plain {h}, not a plain {b}")
        if long:
            lines.append(f"the head is a {h} head, the body and limbs are {b} anatomy")
    if spec.forbidden:
        lines.append("no " + ", no ".join(SING_BY_SLOT.get(s, s) for s in spec.forbidden))
    return lines


def build_prompt(name, description, translated, spec, style_name, custom_style, palette,
                 must="", avoid="", mode="compact", translated_ok=False, proportions="", mood=""):
    """Retourne le prompt de base (sans consigne de vue)."""
    style_long, style_short = STYLES.get(style_name, ("", ""))
    if custom_style.strip():
        style_long = (style_long + ", " + custom_style.strip()).strip(", ")
        style_short = (style_short + ", " + custom_style.strip()).strip(", ")
    names = palette_color_names(palette) if palette else []
    sentences = anatomy_sentences(spec)
    pose = spec.pose or ""  # pas de pose par défaut : « standing » ajoutait des jambes à tout
    scale = ", ".join(spec.scale)
    mats = ", ".join(spec.materials)
    env = "; ".join(spec.env[:1] if mode == "compact" else spec.env[:2])
    avoid_lines = must_not_lines(spec, long=(mode != "compact"))
    if avoid.strip():
        avoid_lines.append(avoid.strip())
    feel = ", ".join(x for x in (proportions, mood) if x)

    if mode == "compact":
        # le sujet d'abord : SDXL/CLIP écoute surtout le début du prompt, le style vient après
        parts = []
        if must.strip():
            parts.append(must.strip())
        if sentences:
            parts.append(", ".join(sentences))
        if translated_ok:
            parts.append(" ".join(translated.split()[:45]))  # la phrase entière, pas seulement ce que le lexique a lu
        elif not sentences:
            parts.append(description.strip())
        if mats:
            parts.append(f"made of {mats}")
        if scale:
            parts.append(scale)
        if feel:
            parts.append(feel)
        # pas de « no body » ici : CLIP ignore la négation et lirait « body » ; les interdits vont au négatif
        if names:
            parts.append("color palette: " + ", ".join(names))
        if pose:
            parts.append(pose)
        if env:
            parts.append(env)
        parts.append(", ".join(x for x in (style_short, "game sprite") if x))
        parts.append("centered, plain flat background, no text")
        return ". ".join(p.strip().rstrip(".") for p in parts if p and p.strip()) + "."

    # détaillé
    lines = [f"Creature name: {name}", "",
             "ORIGINAL BESTIARY DESCRIPTION (source of truth, French):", description.strip(), ""]
    if translated_ok and translated.strip():
        lines += ["ENGLISH TRANSLATION:", translated.strip(), ""]
    if sentences:
        lines.append("ANATOMY LOCK (must follow exactly):")
        for s in sentences:
            lines.append("- " + s)
        for a in avoid_lines:
            lines.append("- " + a)
        lines.append("")
    if mats:
        lines += [f"MATERIALS: {mats}", ""]
    if scale or feel:
        lines += [f"BUILD / FEEL: {', '.join(x for x in (scale, feel) if x)}", ""]
    if must.strip():
        lines += ["MUST INCLUDE: " + must.strip(), ""]
    if names:
        lines += ["COLOR PALETTE (main colors, use consistently, do not add many extra colors): " + ", ".join(names), ""]
    lines += ["VISUAL STYLE: " + (style_long or style_short or "pixel art"), ""]
    if pose or env:
        lines += ["POSE: " + (pose or "natural") + (". Environment cues shown only through texture and color: " + env if env else ""), ""]
    lines += ["ART DIRECTION: one complete, original, recognizable fantasy bestiary creature, entire creature visible, "
              "centered, separated from a plain flat background. Strong readable silhouette, large readable head and eyes, "
              "deliberate pixel clusters, sharp square pixel edges, consistent outline. Do not simplify a hybrid into a "
              "normal animal. No blur, no depth of field, no painterly rendering, no text, no watermark, no labels, "
              "no extra creatures, no scene background."]
    return "\n".join(lines).strip()


def view_suffix(view_key, mode="compact"):
    v = VIEWS[view_key]
    if mode == "compact":
        return " " + v[3] + "."
    return "\n\nCAMERA / VIEW REQUIREMENT:\n" + v[2]


# --------------------------------------------------------------------------
# Prompts SDXL (génération directe dans ComfyUI)
# --------------------------------------------------------------------------
# vue -> (positif pondéré, négatif). SDXL « oublie » vite la vue demandée : on la pondère et on interdit les autres.
VIEW_SD = {
    "face": ("(front view:1.35), (facing the viewer:1.25), (looking at the viewer:1.1), symmetrical",
             "(side view:1.3), (profile:1.3), (back view:1.2), from behind, three-quarter view"),
    "trois_quarts": ("(three-quarter view:1.35), (body turned 45 degrees:1.2), facing left",
                     "(strict front view:1.2), (side profile:1.2), back view, from behind"),
    "dos": ("(back view:1.45), (rear view:1.3), (seen from behind:1.3), facing away from the viewer, back of the head",
            "(front view:1.4), (face:1.4), (eyes visible:1.3), (looking at the viewer:1.4), snout, mouth"),
    "gauche": ("(side view:1.35), (profile view:1.35), (strict profile:1.25), facing left, only one eye visible",
               "(front view:1.4), (looking at the viewer:1.4), back view, from behind, three-quarter view"),
    "droite": ("(side view:1.35), (profile view:1.35), (strict profile:1.25), facing right, only one eye visible",
               "(front view:1.4), (looking at the viewer:1.4), back view, from behind, three-quarter view"),
}
BASE_NEGATIVE = ("blurry, smooth shading, soft gradient, photorealistic, photo, 3d render, painterly, oil painting, "
                 "concept art, anti-aliasing, vector art, smooth lines, text, watermark, signature, logo, letters, ui, "
                 "frame, border, cropped, out of frame, cut off, close-up, scenery, landscape, detailed background, "
                 "floor, ground, cast shadow, noise, jpeg artifacts, deformed, "
                 "(top-down view:1.3), (from above:1.3), bird's eye view, isometric")
NOT_HUMANOID_NEGATIVE = "(humanoid:1.3), (human:1.3), person, standing upright, two legs, bipedal, human face"
SINGLE_NEGATIVE = "character sheet, reference sheet, turnaround, multiple views, multiple characters, crowd, two creatures"
LIMB_NEGATIVE = "extra limbs, extra legs, missing limbs, bad anatomy"


def hybrid_negative(spec):
    """Négatif d'un hybride : interdit la tête de la créature du corps, et le corps de celle de la tête."""
    if spec is not None and spec.hybrid:
        hc, bc = CREATURES[spec.head_creature], CREATURES[spec.body_creature]
        return (f"({bc['en']} head:1.5), ({bc['en']} face:1.4), ({bc['head'].replace('a ', '', 1)}:1.3), "
                f"ordinary {bc['en']}, ordinary {hc['en']}, normal {hc['en']} body")
    return ""


def region_prompts(spec, view="face"):
    """Textes des zones tête / corps pour un hybride (None si la créature n'est pas un hybride)."""
    if spec is None or not spec.hybrid:
        return None
    hc, bc = CREATURES[spec.head_creature], CREATURES[spec.body_creature]
    if view == "dos":
        head = (f"pixel art, (back of the head of a {hc['en']}:1.5), ({hc.get('horns') or hc['en'] + ' ears'} seen from behind:1.3), no face")
    elif view in ("gauche", "droite"):
        head = f"pixel art, (profile of a {hc['en']} head:1.5), ({hc['head']}:1.4), one eye visible"
    elif view == "trois_quarts":
        head = f"pixel art, (three-quarter view of a {hc['en']} head:1.5), ({hc['head']}:1.4), two eyes"
    else:
        head = (f"pixel art, (front view of a {hc['en']} head:1.6), ({hc['head']}:1.5), "
                f"({hc['en']} face with two eyes and nostrils:1.4)")
    body_bits = [f"({bc['en']} body:1.35)", f"({bc['body']}:1.3)"]
    for slot in ("legs", "tail", "wings"):
        s = spec.slots.get(slot)
        if s:
            body_bits.append(f"({s['trait']}:1.3)")
    body = "pixel art, " + ", ".join(body_bits)
    return dict(head=head, body=body)


def sd_subject_tags(spec, plan, view="face"):
    """Étiquettes pondérées qui verrouillent l'anatomie (SDXL oublie vite une longue phrase)."""
    if spec is None:
        return "(monster creature:1.2)"
    if spec.only:
        return f"(single disembodied {spec.only}:1.5), (one giant {spec.only} filling the frame:1.3)"
    # « monster creature » seulement pour un animal reconnu : sur un sujet libre il inventait un corps
    tags = ["(monster creature:1.2)"] if spec.mentions else []
    if spec.hybrid:
        h, b = CREATURES[spec.head_creature], CREATURES[spec.body_creature]
        tags += [f"({h['en']} head:1.6)", f"({b['en']} body:1.1)"]
        if h.get("horns"):
            tags.append(f"({h['horns']}:1.35)")
    elif spec.head_creature:
        tags.append(f"({CREATURES[spec.head_creature]['en']}:1.3)")
    for slot, weight in (("legs", 1.3), ("wings", 1.2), ("tail", 1.15), ("arms", 1.15)):
        s = spec.slots.get(slot)
        if s and (s.get("explicit") or slot == "legs"):
            tags.append(f"({s['trait']}:{weight})")
    if spec.counts.get("eyes") == 1:
        tags += ["(cyclops:1.3)", "(one single eye:1.5)"]
    elif spec.slots.get("head") and view == "face":
        tags += ["(visible face:1.25)", "(two eyes:1.2)"]
    return ", ".join(tags)


def forbidden_negative(spec):
    """Négatif des parties interdites (« juste un œil », « sans corps », champ « À éviter »)."""
    if spec is None:
        return ""
    if spec.counts.get("eyes") == 1:
        return ", ".join(x for x in ("(two eyes:1.5), (multiple eyes:1.3), (pair of eyes:1.3)",
                                     _forbidden_words(spec)) if x)
    return _forbidden_words(spec)


def _forbidden_words(spec):
    if not spec.forbidden:
        return ""
    words = [SING_BY_SLOT.get(s, s) for s in spec.forbidden]
    if "body" in spec.forbidden:
        words += ["torso", "limbs", "animal body", "humanoid body"]
    return ", ".join(f"({w}:1.4)" for w in words)


def _subject_first(spec, plan, view, base):
    """Sujet (étiquettes + texte) avant la caméra : SDXL suit d'abord ce qui est en tête du prompt."""
    body = "" if plan == "free" or (spec is not None and spec.only) else ", full body"
    tags = sd_subject_tags(spec, plan, view)
    return ", ".join(x for x in (tags, base) if x), body


def _negative(view, spec, avoid, plan, extra_negative, single=True):
    return ", ".join(x for x in (BASE_NEGATIVE, SINGLE_NEGATIVE if single else "", VIEW_SD[view][1],
                                 LIMB_NEGATIVE if plan in ("quadruped", "biped") else "bad anatomy",
                                 NOT_HUMANOID_NEGATIVE if plan != "biped" else "",
                                 hybrid_negative(spec), forbidden_negative(spec),
                                 f"({avoid}:1.3)" if avoid else "", extra_negative) if x)


def single_prompts(base, view, spec=None, avoid="", plan="quadruped", extra_negative=""):
    """Une vue sur une image seule (design de face, ou vue générée depuis un guide coloré)."""
    subject, body = _subject_first(spec, plan, view, base)
    pos = "pixel art, " + subject + ", " + VIEW_SD[view][0] + ", solo" + body
    return pos, _negative(view, spec, avoid, plan, extra_negative)


def master_prompts(base, spec=None, avoid="", plan="quadruped", extra_negative=""):
    return single_prompts(base, "face", spec, avoid, plan, extra_negative)


def view_prompts(base, view, spec=None, avoid="", plan="quadruped", extra_negative=""):
    """Toile à deux cases : gauche = design maître de face, droite = la vue demandée."""
    subject, _body = _subject_first(spec, plan, view, base)
    pos = ("pixel art, " + subject + ", character reference sheet, the same single creature shown twice side by "
           "side on a plain background, left: front view, right: " + VIEW_SD[view][0] + ", identical design, "
           "identical colors, identical proportions, same creature")
    return pos, _negative(view, spec, avoid, plan, extra_negative, single=False)


def plain_subject(spec, style_name=""):
    """Description en clair (sans pondérations) pour MV-Adapter, qui n'interprète pas la syntaxe (mot:1.4)."""
    parts = []
    if spec is not None:
        parts += anatomy_sentences(spec)[:4]
        if spec.colors:
            parts.append(", ".join(spec.colors[:3]) + " colors")
    style_short = STYLES.get(style_name, ("", ""))[1]
    if style_short:
        parts.append(style_short)
    text = ", ".join(p for p in parts if p)
    return text or "fantasy monster"
