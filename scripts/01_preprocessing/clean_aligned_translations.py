"""
Purpose:
    Clean aligned human and machine Catalan translations for phonological
    transcription while preserving the line IDs used to match them.
Input:
    Run split_aligned_text.py first, then pass its output folder as
    --input-dir. The UTF-8 tab-separated text files (.txt) contain a line
    ID and the text of a human (_CA) or machine (_TA) Catalan translation.

Output:
    --output-dir receives cleaned UTF-8 tab-separated text files
    (cleaned_*.txt) with the original line IDs. Rows that become empty
    carry an [EMPTY LINE] marker.
"""

import argparse
import os
import re
import unicodedata
from pathlib import Path
from typing import Tuple

def neteja_caracters_estranys(text, eliminar_no_ascii=False):
    """
    Neteja el text de:
    - Caràcters de control
    - Espais insecables
    - Cometes tipogràfiques
    - Opcionalment: caràcters no ASCII
    """

    original_length = len(text)

    # Substituir espais insecables per espais normals
    text = text.replace('\u00A0', ' ')

    # Substituir cometes i apòstrofs tipogràfics
    cometes_tipografiques = {
        '“': '"', '”': '"',
        '‘': "'", '’': "'",
        '«': '"', '»': '"',
        '‚': "'", '„': '"',
    }
    for char, replacement in cometes_tipografiques.items():
        text = text.replace(char, replacement)

    # Eliminar caràcters de control (excepte \n i \t)
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)

    # Si vols eliminar caràcters no ASCII
    if eliminar_no_ascii:
        text = re.sub(r'[^\x00-\x7F]', '', text)

    cleaned_length = len(text)
    if original_length != cleaned_length:
        print(f"🧹 Netejats {original_length - cleaned_length} caràcters no desitjats.")

    return text


def is_chapter_header(linia: str) -> bool:
    """
    Retorna True si la línia és només un títol de capítol (pot envoltat de guions/espais), del tipus:
    - Chapter 1, Chapter-1, CHAPTER 1, Capítol 1, etc.
    - Chapter I, Capítol IV, etc.
    - Chapter ONE, CHAPTER-ONE, Chapter Ten, etc.
    - I, II, III, IV... (números romans sols)
    - 1, 2, 3, 10... (número sol en la línia)
    - També variants amb guions decoratius al voltant, ex: ----CHAPTER-ONE----------
    """

    linia = linia.strip()
    if not linia:
        return False

    number_words = (
        r"one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
        r"seventeen|eighteen|nineteen|twenty|thirty|forty|"
        r"fifty|sixty|seventy|eighty|ninety"
    )

    # separador intern entre "chapter/capítol" i el número/paraula
    sep = r"[-–—.:]?"

    pattern = re.compile(
        r'^[\-–—\s]*('                            # decoració inicial opcional
        r'(?:cap[ií]tol|chapter)\s*' + sep + r'\s*\d+'          # Chapter 1, Capítol 1
        r'|'
        r'(?:cap[ií]tol|chapter)\s*' + sep + r'\s*[ivxlcdmIVXLCDM]+'  # Chapter I, Capítol IV
        r'|'
        r'(?:chapter)\s*' + sep + r'\s*(?:' + number_words + r')'    # CHAPTER-ONE, Chapter ten
        r'|'
        r'[IVXLCDM]{1,6}'                                  # I, II, III...
        r'|'
        r'\d{1,3}'                                         # 1..999 sols
        r')[\-–—\s]*$',                                    # decoració final opcional
        re.IGNORECASE
    )

    return bool(pattern.match(linia))



# --- Conversió de números a paraules en català ---

def number_to_catalan(n: int) -> str:
    """
    Converteix un enter 0 <= n <= 999999 a paraules en català.
    Versió simplificada però correcta per a ús general.
    """

    if n < 0:
        return "menys " + number_to_catalan(-n)
    if n == 0:
        return "zero"

    units = [
        "zero", "un", "dos", "tres", "quatre",
        "cinc", "sis", "set", "vuit", "nou",
        "deu", "onze", "dotze", "tretze", "catorze",
        "quinze", "setze", "disset", "divuit", "dinou"
    ]

    tens_map = {
        20: "vint",
        30: "trenta",
        40: "quaranta",
        50: "cinquanta",
        60: "seixanta",
        70: "setanta",
        80: "vuitanta",
        90: "noranta",
    }

    hundreds_map = {
        1: "cent",
        2: "dos-cents",
        3: "tres-cents",
        4: "quatre-cents",
        5: "cinc-cents",
        6: "sis-cents",
        7: "set-cents",
        8: "vuit-cents",
        9: "nou-cents",
    }

    def sub_0_99(x: int) -> str:
        if x < 20:
            return units[x]
        if x < 30:
            if x == 20:
                return "vint"
            return "vint-i-" + units[x - 20]
        tens = (x // 10) * 10
        u = x % 10
        if u == 0:
            return tens_map[tens]
        # Forma general: "trenta-u", "quaranta-dos", etc.
        return tens_map[tens] + "-" + units[u]

    def sub_0_999(x: int) -> str:
        if x < 100:
            return sub_0_99(x)
        hundreds = x // 100
        rest = x % 100
        if x == 100:
            return "cent"
        prefix = hundreds_map[hundreds]
        if rest == 0:
            return prefix
        return prefix + " " + sub_0_99(rest)

    # fins a 999999
    if n < 1000:
        return sub_0_999(n)

    thousands = n // 1000
    rest = n % 1000

    if thousands == 1:
        prefix = "mil"
    else:
        prefix = sub_0_999(thousands) + " mil"

    if rest == 0:
        return prefix
    return prefix + " " + sub_0_999(rest)


def replace_numbers_with_words(text: str) -> str:
    """
    Substitueix números sencers (tokens només dígits) per paraules en català
    per a valors entre 0 i 999999. Fora d'aquest rang, els deixa tal qual.
    """

    def repl(match):
        num_str = match.group(0)
        try:
            n = int(num_str)
        except ValueError:
            return num_str
        if 0 <= n <= 999999:
            return number_to_catalan(n)
        return num_str

    return re.sub(r'\b\d+\b', repl, text)


# --- Neteja de línies ---

def neteja_linia(linia: str) -> str:
    """
    Neteja una línia aplicant:
    - Normalització Unicode
    - Eliminació d'etiquetes <text> & variants
    - Eliminació de títols de capítol / números sols
    - Eliminació de caràcters estranys i emojis
    - Eliminació de paraules amb més d'un guion intern
    - Substitució de seqüències de guions (--, ---...) per espai
    - Conversió de números a paraules en català
    - Neteja d'espais, puntuació i caràcters de control
    """

    # Normalitza a NFC
    linia = unicodedata.normalize("NFC", linia)

    # 1) Eliminar etiquetes <text> i variants (inclou atributs)
    linia= linia.replace('LA GRÀCIA',' ')
    linia= linia.replace('FRAGMENT SENSE EQUIVALENT',' ')
    linia = linia.replace('<\\text>', '',)
    linia = re.sub(r'<\s*/?\s*text[^>]*>', '', linia, flags=re.IGNORECASE)
    # 2) Després de treure etiquetes, si és només un títol de capítol / número → eliminar
    if is_chapter_header(linia):
        return ""

    # 3) Eliminar caràcters no imprimibles "rars" però deixar llatins i signes habituals
    linia = re.sub(r'[^\x20-\x7EÀ-ÿ·’\'",.;:!?()\-\s]', '', linia)

    # 4) Eliminar emojis i símbols no llatins (definició restrictiva)
    linia = re.sub(
        r'[^\u0000-\u007F'
        r'\u00A0-\u00FF'
        r'\u0100-\u017F'
        r'\u20AC'
        r'\u2013\u2014\u2018\u2019\u201C\u201D'
        r'\u2030\u2032\u2033\u2039-\u203A'
        r'\u2044\u2057'
        r'\s.,;:!?\'"()\[\]-]',
        '',
        linia
    )

    # 5) Eliminar paraules amb més d'un guion intern (The-Cyclone-Dorothy, etc.)
    linia = re.sub(r'\b[^\s-]*(?:-[^\s-]*){2,}\b', '', linia)

    # 6) Substituir seqüències de guions (dos o més seguits) per un espai
    linia = re.sub(r'-{2,}', ' ', linia)

    # 7) Conversió de números a paraules (només dígits sols)
    linia = replace_numbers_with_words(linia)

    # 8) Substituir múltiples espais (incloent tabs) per un
    linia = re.sub(r'\s+', ' ', linia)

    # 9) Eliminar cometes dobles i dos punts
    linia = linia.replace('"', '')
    linia = linia.replace(':', '')

    # 9.5 Elimina caràcters estranys amb ^
    linia = linia.replace('Û', 'U')
    linia = linia.replace('Â', 'A')
    linia = linia.replace('Ê', 'E')
    linia = linia.replace('Î', 'I')
    linia = linia.replace('Ô', 'O')
    linia = linia.replace('û', 'u')
    linia = linia.replace('â', 'a')
    linia = linia.replace('ê', 'e')
    linia = linia.replace('ô', 'o')
    linia = linia.replace('î', 'i')
    linia = linia.replace('á', 'à')
    linia = linia.replace('ì', 'í')
    linia = linia.replace('Ä', 'A')
    linia = linia.replace('ä', 'a')
    linia = linia.replace('Ö', 'O')
    linia = linia.replace('ö', 'o')
    linia = linia.replace('Ë', 'E')
    linia = linia.replace('ë', 'e')
    linia = linia.replace('.-', '')
    linia = re.sub(r"(?<!['’])\b(?![aeiouAEIOU]\b)[A-Za-zÀ-ÿ]\b(?!['’])","", linia)
    linia = re.sub(r"^\s*['’](?=\w)", "", linia)
    
    # 10) Retirar espais abans de la puntuació
    linia = re.sub(r'\s+([.,;:!?])', r'\1', linia)

    # 11) Eliminar caràcters de control
    linia = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', linia)

    # 12) Eliminar espai després d'apòstrof en l', n', d', s'
    linia = re.sub(r"\b([lnds])'\s+", r"\1'", linia, flags=re.IGNORECASE)

    # 13) Última neteja general (cometes tipogràfiques, etc.)
    linia = neteja_caracters_estranys(linia)

    # 14) Normalitzar espais finals: cap múltiple
    linia = re.sub(r'\s{2,}', ' ', linia)

    # 15) Passar a minúscules [No altera resultats de la transcripció amb Segre]
    linia = linia.lower()

    return linia.strip()

# --- Line-number aware wrappers ---

def split_number_and_text(raw: str) -> Tuple[str, str]:
    raw = raw.rstrip("\n")
    if "\t" in raw:
        num, txt = raw.split("\t", 1)
    else:
        num, txt = "", raw
    return num, txt

def clean_line_with_number(raw: str) -> str:
    num, txt = split_number_and_text(raw)
    cleaned = neteja_linia(txt)
    if cleaned.strip():
        return f"{num}\t{cleaned}".strip()
    return f"{num}\t[EMPTY LINE]".strip()

def clean_file_preserving_numbers(input_path: str | Path, output_path: str | Path):
    src = Path(input_path)
    dst = Path(output_path)
    if dst.exists():
        print(f"{dst} ja existeix; elimina'l per tornar-lo a crear.")
        return str(dst)
    lines_out = []
    with open(src, "r", encoding="utf-8") as f:
        for line in f:
            lines_out.append(clean_line_with_number(line))
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))
    print(f"Text netejat i desat a: {dst}")
    return str(dst)

# --- RUN FOR ALL FILES IN TRIPLE INPUT FOLDER ---

def clean_all_ca_ta(input_dir: Path, output_dir: Path):
    for src in input_dir.glob("*.txt"):
        name = src.name
        # skip already-cleaned or non-target files
        if name.startswith("cleaned_"):
            continue
        if not ("_CA" in name or "_TA" in name):
            continue
        clean_file_preserving_numbers(src, output_dir / f"cleaned_{src.name}")

def main():
    parser = argparse.ArgumentParser(description="Clean aligned Catalan translations.")
    parser.add_argument("--input-dir", type=Path, required=True,
                        help="Folder containing the split .txt files")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New or empty folder for the cleaned .txt files")
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error(f"Input directory does not exist: {args.input_dir}")

    output_dir = args.output_dir
    if output_dir.exists():
        if not output_dir.is_dir():
            parser.error(f"Output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            parser.error(
                f"Output directory is not empty: {output_dir}\n"
                "Choose a new or empty directory with --output-dir."
            )

    clean_all_ca_ta(args.input_dir, output_dir)


if __name__ == "__main__":
    main()
