# -*- coding: utf-8 -*-
"""Petit bestiaire de référence : les traits visuels des monstres, créatures et objets vivants connus.

Les modèles locaux (texte comme image) en ont une idée floue : un « tyrannœil » leur sort sur deux jambes, une
« hydre » avec une seule tête. Quand la description en nomme un, ses traits typiques sont ajoutés à la consigne ;
les nombres et couleurs de la description restent prioritaires.
"""
import re

import nb_core

# (motif sur le texte sans accents, posture ou None, traits en anglais)
ARCHETYPES = [
    (r"hydre|hydra", None, "a hydra: one heavy reptilian body on four short legs, with several serpent heads, each head on "
     "its own long separate neck, the necks fanning out side by side from the shoulders"),
    (r"cerbere|cerberus|chien (des|de l') ?enfers?", "quatre_pattes", "Cerberus: one big dog body on four legs with three dog "
     "heads side by side, each on its own neck, left, middle and right"),
    (r"mimi(que|c)", None, "a mimic: a treasure chest whose open lid is a huge mouth lined with sharp teeth, with a long "
     "tongue hanging out; the chest itself is the body"),
    (r"tyrann?oeil|beholder|oeil tyran", "flotte", "a beholder: a large floating sphere that is mostly one huge central "
     "eye, a wide mouth full of teeth below the eye, and many thin eye stalks on top, each ending in a small eye; "
     "no legs, no arms"),
    (r"chimere|chimera", "quatre_pattes", "a chimera: a lion's body and lion head, a goat head growing from the middle of "
     "its back, and a live snake as its tail"),
    (r"kitsune|renard a (plusieurs|neuf|\w+) queues", "quatre_pattes", "a kitsune: a fox with several big fluffy tails "
     "fanned out behind it"),
    (r"manticore", "quatre_pattes", "a manticore: a lion's body, a human-like face with a mane, bat wings and a scorpion tail"),
    (r"griffon|gryphon", "quatre_pattes", "a griffin: an eagle's head, wings and front talons on a lion's body and back legs"),
    (r"hippogriffe", "quatre_pattes", "a hippogriff: an eagle's head, wings and front talons on a horse's body"),
    (r"centaure", "quatre_pattes", "a centaur: a human torso, arms and head on top of a horse's body with four legs"),
    (r"\bnaga\b", "rampe", "a naga: a human upper body with arms, the lower body a long snake tail"),
    (r"sirene|mermaid", "nage", "a mermaid: a human upper body, the lower body a fish tail with fins"),
    (r"harpie", "deux_jambes", "a harpy: a woman's head and torso, large bird wings for arms, bird legs with talons"),
    (r"minotaure", "deux_jambes", "a minotaur: a muscular humanoid standing on two legs with a bull's head and two horns"),
    (r"cyclope", "deux_jambes", "a cyclops: a giant humanoid with one single eye in the middle of the forehead"),
    (r"basilic|basilisk", "rampe", "a basilisk: a huge serpent with a crowned crest on its head and deadly glowing eyes"),
    (r"cocatrix|cockatrice", "deux_jambes", "a cockatrice: a rooster's head, body and legs with bat wings and a snake tail"),
    (r"wyverne?|wyvern", "deux_jambes", "a wyvern: a dragon with two hind legs and two wings, no front legs, a long tail"),
    (r"\bdragon", None, "a dragon: a scaled reptile with horns, a long neck and tail, and bat-like wings"),
    (r"gargouille", None, "a gargoyle: a grey stone demon with bat wings, horns and claws, crouching"),
    (r"golem", "deux_jambes", "a golem: a heavy humanoid made of blocks of stone, clay or metal, glowing eyes, no mouth"),
    (r"liche|lich\b", "deux_jambes", "a lich: a skeletal undead sorcerer in tattered robes with a crown and glowing eye "
     "sockets"),
    (r"squelette|skeleton", "deux_jambes", "a skeleton: bare white bones, empty eye sockets with small glowing pupils"),
    (r"zombie|goule|ghoul", None, "an undead: grey-green rotting skin, hunched posture, sunken glowing eyes"),
    (r"spectre|fantome|ghost|banshee|dame blanche", "flotte", "a ghost: a translucent floating figure whose body fades "
     "into wisps at the bottom, no legs"),
    (r"feu follet|will.o", "flotte", "a will-o'-the-wisp: a small floating ball of pale flame with two tiny eyes"),
    (r"slime|gelee|blob", "rampe", "a slime: a glossy translucent jelly blob with a rounded top, eyes inside the jelly"),
    (r"wendigo", "deux_jambes", "a wendigo: a gaunt, very tall emaciated humanoid with a deer skull head and antlers"),
    (r"loup.garou|lycanthrope|werewolf", "deux_jambes", "a werewolf: a hulking wolf-headed humanoid on two legs, fur and claws"),
    (r"kappa", "deux_jambes", "a kappa: a small green turtle-like river imp with a beak, a shell on its back and a "
     "water-filled dish on top of its head"),
    (r"tengu", "deux_jambes", "a tengu: a bird-headed humanoid with a long nose or beak, black wings and monk clothes"),
    (r"kraken", "nage", "a kraken: a giant squid with a huge mantle and many long tentacles"),
    (r"sphinx", "quatre_pattes", "a sphinx: a lion's body lying down with a human head wearing a headdress"),
    (r"phenix|phoenix|oiseau de feu", "vole", "a phoenix: a bird made of fire with long burning tail feathers"),
    (r"licorne|unicorn", "quatre_pattes", "a unicorn: a horse with one single spiral horn in the middle of the forehead"),
    (r"pegase|pegasus", "quatre_pattes", "a pegasus: a horse with two large feathered wings"),
    (r"vouivre", "rampe", "a vouivre: a winged serpent with a glowing gem in its forehead"),
    (r"tarasque", "quatre_pattes", "a tarasque: a lion-headed dragon-turtle with a spiked turtle shell on six short legs"),
    (r"mandragore", "deux_jambes", "a mandrake: a small root creature with a screaming face and leaves sprouting from its head"),
    (r"ent\b|sylvain|homme.arbre|treant", "deux_jambes", "a treant: a walking tree with a face in the bark, branch arms "
     "and root feet"),
    (r"champignon", None, "a mushroom creature: a big spotted mushroom cap as its head, a thick stalk body"),
    (r"armure (hantee|vivante)|haunted armor", "deux_jambes", "a haunted armor: an empty suit of plate armor standing "
     "upright, glowing eyes inside the dark helmet"),
    (r"epee (vivante|hantee|maudite)", "flotte", "a living sword: a floating sword with an eye in the guard"),
    (r"livre (vivant|maudit)|grimoire vivant", "flotte", "a living book: a floating open book whose pages form a toothy mouth"),
    (r"epouvantail", "deux_jambes", "a scarecrow: a straw-stuffed figure in ragged clothes with a sack head and stitched face"),
    (r"djinn|genie", "flotte", "a djinn: a muscular upper body whose lower half is a swirling cloud of smoke, floating"),
    (r"elementaire", None, "an elemental: a body made entirely of its element (stone, fire, water or air), glowing core"),
    (r"momie|mummy", "deux_jambes", "a mummy: a humanoid wrapped in old bandages, glowing eyes between the wraps"),
    (r"vampire", "deux_jambes", "a vampire: a pale aristocrat with fangs, red eyes and a high-collared cape"),
]
_COMPILED = [(re.compile(rx), posture, traits) for rx, posture, traits in ARCHETYPES]


def match(description):
    """[(posture, traits)] des archétypes nommés dans la description (3 au plus)."""
    text = nb_core.fold(description)
    return [(p, t) for rx, p, t in _COMPILED if rx.search(text)][:3]


def says_posture(description):
    """La description dit-elle elle-même comment elle se tient ? Alors elle prime sur l'archétype."""
    return bool(re.search(r"patte|jambe|debout|flott|levit|rampe|nage|vole\b|dans les airs|sans pattes",
                          nb_core.fold(description)))


if __name__ == "__main__":
    assert match("un tyrannœil violet")[0][0] == "flotte"
    assert "Cerberus" in match("un chien des enfers à trois têtes")[0][1]
    assert not match("une vache rouge")
    assert says_posture("une hydre qui flotte") and not says_posture("une hydre verte")
    print("ok")
