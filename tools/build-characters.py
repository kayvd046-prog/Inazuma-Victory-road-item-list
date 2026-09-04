#!/usr/bin/env python3
"""Bouwt characters.json uit de datamined dump.

Dit is het enige databestand naast index.html. Het draagt per character de
zeven basisstats op level 50 en 99, en dezelfde veertien voor de Hero- en
Fabled-versie waar het spel die kent. De bouwer haalt het pas op zodra je hem
openklapt.

Het skills-veld uit de dump zit er bewust NIET in. Dat leek de moves te geven
die een character leert, maar 5.413 van de 5.418 characters dragen exact
hetzelfde levelpatroon (1, 13, 20, 30, 38, 43) en op 43 staat altijd een van
vijf Awakenings. Dat is een vast sjabloon, geen leercurve, en wat het dan wel
betekent is van buitenaf niet vast te stellen.

    python3 tools/build-characters.py /pad/naar/ievr.en.json

Bron: github.com/salty-max/kizuna (MIT), uitgelezen uit spelversie 6.00.23.00.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["kick", "control", "technique", "intelligence", "pressure", "agility", "physical"]
POS = {1: "GK", 2: "FW", 3: "MF", 4: "DF"}
EL = {1: "Wind", 2: "Forest", 3: "Fire", 4: "Mountain", 5: "Void"}


def block(x):
    return [x["stats_lv50"][k] for k in ORDER] + [x["stats_lv99"][k] for k in ORDER]


def build(dump_path):
    d = json.load(open(dump_path, encoding="utf-8-sig"))
    hero = {}
    fabled = {}
    for x in d["heroes"]:
        hero.setdefault(x["character_id"], x)
    for x in d["basaras"]:
        fabled.setdefault(x["character_id"], x)

    usable = [x for x in d["characters"]
              if x.get("name") and x["name"] != "???"
              and x.get("main_position") in POS and x.get("element") in EL]
    # Een dubbel met een Hero- of Fabled-versie wint van een dubbel zonder.
    seen = {}
    for x in sorted(usable, key=lambda y: -((y["character_id"] in hero)
                                            + (y["character_id"] in fabled))):
        seen.setdefault((x["name"], tuple(block(x))), x)
    uniq = list(seen.values())

    count = Counter(x["name"] for x in uniq)
    rows = []
    for x in sorted(uniq, key=lambda y: (y["name"], -sum(y["stats_lv99"].values()))):
        name = x["name"]
        if count[name] > 1 and x.get("series"):
            name = f"{name} ({x['series']})"
        h = hero.get(x["character_id"])
        f = fabled.get(x["character_id"])
        rows.append([name, POS[x["main_position"]], EL[x["element"]]] + block(x)
                    + [block(h) if h else None, block(f) if f else None])

    out = {
        "note": ("Character data datamined from Inazuma Eleven: Victory Road 6.00.23.00, "
                 "via github.com/salty-max/kizuna (MIT). Each entry: name, position, "
                 "element, the seven base stats at level 50 then at level 99, the same "
                 "fourteen again for the Hero and Fabled versions where they exist."),
        "stats": ["Kick", "Control", "Technique", "Intelligence", "Pressure", "Agility", "Physical"],
        "characters": rows,
    }
    path = ROOT / "characters.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(rows)} characters, {sum(1 for r in rows if r[17])} met Hero, "
          f"{sum(1 for r in rows if r[18])} met Fabled, {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    build(sys.argv[1])
