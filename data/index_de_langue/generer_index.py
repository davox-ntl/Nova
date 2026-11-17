"""Build the per-language JSON indexes consumed by the translation prompt.

Run: python data/index_de_langue/generer_index.py
The resulting files are data/index_de_langue/<code>/{vocabulaire,phonetique,prononciation}.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

INDEXES = {
    "dyu": {
        "name": "Dioula",
        "vocabulaire_source": "Index-dioula-francais.pdf — Urs Niggli",
        "entries": [
            ("bonjour (matin)", "i ni sɔgɔma", "i ni so-goma", "salutation"),
            ("bonjour (journée)", "i ni tile", "i ni ti-le", "salutation"),
            ("salut", "i ni ce", "i ni tche", "salutation"),
            ("comment ça va ?", "hɛɛrɛ sira", "hɛ-hɛ sira", "salutation"),
            ("merci", "i ni ce / abarika", "i ni tche / a-ba-ri-ka", "politesse"),
            ("oui", "awɔ", "a-wɔ", "politesse"),
            ("bonne nuit", "sanbɛsanb ɲuman", "san-bɛ-sanb ɲu-man", "salutation"),
            ("eau", "ji", "dji", "quotidien"),
            ("eau à boire", "minniji", "min-ni-dji", "quotidien"),
            ("argent", "wari", "wa-ri", "marché"),
            ("manger", "dumu", "du-mu", "quotidien"),
            ("aller", "taga / wa", "ta-ga / wa", "quotidien"),
            ("boire", "ji", "dji", "quotidien"),
            ("bon / beau", "ɲuman", "ɲu-man", "quotidien"),
            ("bon (au goût)", "diman", "di-man", "quotidien"),
            ("maladie", "bana", "ba-na", "santé"),
            ("prix", "sɔngɔ", "sɔn-gɔ", "marché"),
            ("homme", "cɛ", "tchɛ", "quotidien"),
            ("femme", "muso", "mu-so", "quotidien"),
            ("enfant", "den", "den", "quotidien"),
            ("comment", "cogo / cogo di", "co-go di", "quotidien"),
        ],
        "phonetique_notes": (
            "Transcription simplifiée en lettres latines pour un lecteur francophone. "
            "Chaque syllabe est ouverte : elle se termine par une voyelle."
        ),
        "rules": [
            ("ɛ", "è court, comme dans « père »"),
            ("ɔ", "o ouvert, comme dans « porte »"),
            ("ɲ", "gn, comme dans « agneau »"),
            ("ŋ", "ng nasal, comme dans « parking »"),
            ("c", "tch, comme dans « tchat »"),
            ("j", "dj, comme dans « diamant »"),
            ("gb", "gb prononcé des deux lèvres en même temps"),
            ("h", "h aspiré, bien audible"),
            ("an / en / in / on", "voyelles nasales comme en français (an, in, bon)"),
        ],
        "prononciation_notes": (
            "Orthographe dioula (alphabet latin) issue de l'index de référence. "
            "Les tons ne sont pas notés dans la transcription simplifiée."
        ),
    },
    "any": {
        "name": "Agni",
        "vocabulaire_source": "Introduction à la langue agni — Louis de Gouyon Matignon (lexique français-agni)",
        "entries": [
            ("eau", "n’zwé", "n-zwé", "quotidien"),
            ("prix", "gwa", "gwa", "marché"),
            ("maladie", "awonïalé", "a-wo-nï-a-lé", "santé"),
            ("oui", "ïo", "ï-o", "politesse"),
            ("non", "tchètchè", "tchè-tchè", "politesse"),
            ("femme", "basoua", "ba-soua", "quotidien"),
            ("enfant", "ba / batouman", "ba / ba-tou-man", "quotidien"),
            ("à bientôt", "ïè té wonou", "ïè té wo-nou", "salutation"),
            ("bonne année !", "afouè kpa", "a-fouè kpa", "salutation"),
            ("ami", "amïangouan", "a-mïan-gouan", "quotidien"),
            ("argent (monnaie)", "ésika", "é-si-ka", "marché"),
            ("arbre", "bakaa", "ba-kaa", "quotidien"),
            ("allumette", "matésé", "ma-té-sé", "quotidien"),
            ("ananas", "gnangoman", "gnan-go-man", "marché"),
            ("année", "afouè", "a-fouè", "quotidien"),
            ("assiette", "tchinzé", "tchin-zé", "quotidien"),
        ],
        "phonetique_notes": (
            "L'ouvrage utilise l'alphabet latin avec la graphie du français ; "
            "la transcription ci-dessous découpe les mots en syllabes lisibles."
        ),
        "rules": [
            ("voyelles", "se prononcent comme en français"),
            ("an (ex. toféman)", "comme « ant » de « maintenant »"),
            ("ï (ex. anoïé, ïè)", "comme le ï de « païen » ou « monoï »"),
            ("consonnes", "son dur, à l'allemande"),
            ("apostrophe (ex. n’gémo)", "allonge et durcit la lettre précédente : « nn-gémo »"),
            ("a’nwué", "se prononce « aa-nwué »"),
            ("dj (ex. djadé)", "comme le j de « John »"),
            ("w (ex. waté)", "comme le w de « whisky »"),
        ],
        "prononciation_notes": (
            "Règles de phonétique extraites du chapitre « Phonétique » de l'ouvrage. "
            "L'agni est une langue à tons ; les tons ne sont pas notés ici."
        ),
    },
    "bci": {
        "name": "Baoulé",
        "vocabulaire_source": "Parlons baoulé — Kouadio N'Guessan & Kouamé (chapitre « La langue baoulé »)",
        "entries": [
            ("garçon / homme / mâle", "yasua", "ya-soua", "quotidien"),
            ("fille / femme / femelle", "bla", "bla", "quotidien"),
            ("enfant", "ba", "ba", "quotidien"),
            ("homme", "sran", "sran", "quotidien"),
            ("hommes (pluriel)", "sran mun", "sran moun", "grammaire"),
            ("papier", "fluwa", "flou-a", "quotidien"),
            ("dire", "se", "sé", "quotidien"),
            ("trois", "nsan", "n-san", "nombre"),
            ("piège", "gba", "gba", "quotidien"),
            ("crédit", "kale", "ka-lé", "marché"),
            ("couper", "kpe", "kpé", "quotidien"),
            ("coucher", "la", "la", "quotidien"),
            ("bouteille", "panndu", "pann-dou", "quotidien"),
            ("igname", "nza", "n-za", "marché"),
            ("écoper de l'eau", "fen", "fèn", "quotidien"),
            ("écraser", "tin", "tin", "quotidien"),
            ("sombre", "tuun", "tou-un", "quotidien"),
            ("planter", "ta", "ta", "quotidien"),
            ("cuire", "be", "bé", "quotidien"),
            ("fatiguer", "fe", "fé", "quotidien"),
            ("acheter", "to", "to", "marché"),
            ("casser", "bu", "bou", "quotidien"),
            ("grandir / fermer", "nym", "gnim", "quotidien"),
            ("épouse", "yi", "yi", "quotidien"),
        ],
        "phonetique_notes": (
            "Transcription syllabique simplifiée ; toutes les syllabes du baoulé "
            "sont ouvertes (terminées par une voyelle orale ou nasale)."
        ),
        "rules": [
            ("a / e / ɛ / i / o / ɔ / u", "7 voyelles orales ; e et ɛ proches de « été » et « père »"),
            ("an / ɛn / on", "voyelles nasales comme dans « chant », « pain », « bon »"),
            ("in / un", "pronnoncés i / ou avec la voix nasalisée (« en parlant du nez »)"),
            ("j", "comme le j de « diamant », « diète » (souvent noté dj)"),
            ("gb", "son double articulé, prononcé en même temps à l'arrière et à l'avant"),
            ("kp", "comme gb mais sans vibration des cordes vocales"),
            ("r", "r battu, plus proche du l français"),
            ("c", "comme le tch de « tiers »"),
            ("w", "comme dans « ouate », « ouest »"),
            ("y", "comme dans « yaourt », « cahier »"),
            ("ny", "comme le gn de « agnat »"),
            ("mun", "marque du pluriel, ajoutée après le nom"),
        ],
        "prononciation_notes": (
            "Règles extraites du chapitre de phonologie de « Parlons baoulé ». "
            "Pas d'opposition grammaticale masculin/féminin : la distinction est celle du sexe."
        ),
    },
    "bet": {
        "name": "Bété",
        "vocabulaire_source": "Parlons bété — aperçu (l'extrait disponible est surtout linguistique)",
        "entries": [
            ("Daloa", "Daloa", "da-lo-a", "geographie"),
            ("Soubré", "Soubré", "sou-bré", "geographie"),
            ("Gagnoa", "Gagnoa", "ga-gno-a", "geographie"),
            ("Ouragahio", "Ouragahio", "ou-ra-ga-hio", "geographie"),
            ("Guibéroua", "Guibéroua", "gui-bé-rou-a", "geographie"),
            ("Issia", "Issia", "is-sia", "geographie"),
            ("Saïoua", "Saïoua", "sa-ï-oua", "geographie"),
            ("Nyabwa", "Nyabwa", "gnia-bwa", "geographie"),
            ("Kouzié", "Kouzié", "kou-zié", "geographie"),
            ("Gbadi", "Gbadi", "gba-di", "dialecte"),
            ("Nekedi", "Nekedi", "né-ké-di", "dialecte"),
            ("Zedi", "Zedi", "zé-di", "dialecte"),
        ],
        "phonetique_notes": (
            "L'extrait de « Parlons bété » disponible ne contient pas de lexique "
            "français-bété : les entrées ci-dessous sont des noms propres et dialectes "
            "avec une transcription lisible. Ne pas inventer d'équivalents bété absents de l'index."
        ),
        "rules": [
            ("dialecte de référence", "celui de Daloa (triangle Daloa-Issia-Saïoua)"),
            ("famille", "langue kru (avec Nyabwa, Kouzié, Bakwé, Godié, Dida)"),
            ("parlers", "Gbadi, Nekedi, Zedi (axe Soubré-Gagnoa-Ouragahio) et parlers de l'axe Daloa-Issia"),
            ("orthographe", "alphabet latin ; lire chaque syllabe distinctement, voyelles bien ouvertes"),
        ],
        "prononciation_notes": (
            "Le bété est une langue à tons, non notés dans cette transcription simplifiée. "
            "Privilégier le dialecte de Daloa pour les traductions."
        ),
    },
}


def main() -> None:
    for code, data in INDEXES.items():
        folder = ROOT / code
        folder.mkdir(parents=True, exist_ok=True)

        vocabulaire = {
            "language": code,
            "name": data["name"],
            "source": data["vocabulaire_source"],
            "entries": [
                {"fr": fr, "translation": translation, "phonetic": phonetic, "context": context}
                for fr, translation, phonetic, context in data["entries"]
            ],
        }
        phonetique = {
            "language": code,
            "name": data["name"],
            "notes": data["phonetique_notes"],
            "entries": [
                {"mot": translation, "phonetic": phonetic, "fr": fr}
                for fr, translation, phonetic, _ in data["entries"]
            ],
        }
        prononciation = {
            "language": code,
            "name": data["name"],
            "source": data["vocabulaire_source"],
            "notes": data["prononciation_notes"],
            "rules": [{"graphie": graphie, "son": son} for graphie, son in data["rules"]],
        }
        for filename, payload in (
            ("vocabulaire.json", vocabulaire),
            ("phonetique.json", phonetique),
            ("prononciation.json", prononciation),
        ):
            (folder / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(f"{code}: {len(data['entries'])} mots, {len(data['rules'])} règles")


if __name__ == "__main__":
    main()
