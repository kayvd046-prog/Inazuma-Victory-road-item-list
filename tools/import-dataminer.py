#!/usr/bin/env python3
"""Vult de itemlijst aan met wat er sinds de bron van maart 2026 bij is gekomen.

De lijst in index.html komt uit het VR Document v3.06 (2 maart 2026). Het spel
is daarna doorgegaan: de Orion & Lumen DLC (25 februari 2026), The Rising Bond
(31 maart 2026) en latere updates brachten nieuwe moves, uitrusting en tactics.
Die staan in de datamined dump van kizuna (github.com/salty-max/kizuna, MIT),
uitgelezen uit spelversie 6.00.23.00.

    python3 tools/import-dataminer.py /pad/naar/ievr.en.json

Schrijft de nieuwe rijen naar stdout als JSON, in hetzelfde formaat als DATA.

Twee dingen uit die dump zijn NIET zomaar over te nemen:

1. De statnamen zijn omgewisseld: wat de dump 'agility' noemt is Intelligence
   en andersom. Dat is hier geen aanname maar een meting: de combatstats in
   index.html (Focus DF, Scramble DF, KP) volgen uit de basisstats via vaste
   formules, en die kloppen alleen met de namen omgewisseld. Zo komt de dump op
   389 van de 401 overlappende items exact uit op wat de lijst al had.
2. De shop-ids zijn intern ('market_01'). De vertaling hieronder is afgeleid uit
   de items die in beide bronnen staan; waar de dump geen winkel noemt, blijft
   het 'Source unknown' in plaats van een gok.
"""
import json
import re
import sys
from collections import OrderedDict

# De dump verwisselt deze twee; zie de kop.
STAT_NAME = {"kick": "Kick", "control": "Control", "technique": "Technique",
             "pressure": "Pressure", "physical": "Physical",
             "intelligence": "Agility", "agility": "Intelligence"}
# Vaste volgorde waarin index.html de stats van uitrusting schrijft.
STAT_ORDER = ["Kick", "Control", "Technique", "Pressure", "Physical",
              "Intelligence", "Agility"]

SLOT = {"boots": "Boots", "pendant": "Pendant", "bracelet": "Bracelet",
        "special": "Misc"}
CATEGORY = {1: "Shoot", 2: "Dribble", 3: "Block", 4: "Catch"}
ELEMENT = {1: "風 (Wind)", 2: "林 (Forest)", 3: "火 (Fire)",
           4: "山 (Mountain)", 5: "無 (Void)"}
# Afgeleid uit de overlap; unnamed_01 verkoopt dezelfde items voor
# hero-tokens en heeft geen eigen naam in de lijst, dus die telt niet mee.
SHOP = {"market_01": "Chronicle Department Store", "market_02": "VS Store",
        "market_05": "Spirit Market", "unnamed_02": "Special Training Booth",
        "story_01": "G-Mart (Arcade Branch)", "story_02": "G-Mart (Arcade Branch)",
        "story_03": "G-Mart (Arcade Branch)", "story_04": "Kool Kit (Odaiba Branch)",
        "story_05": "Kool Kit (Odaiba Branch)",
        "story_06": "Magic Moves (Arcade Branch)",
        "story_07": "Magic Moves (Arcade Branch)"}
UNKNOWN = "Source unknown"

# Dezelfde formules als powerOf() in index.html, daar geverifieerd op alle 436
# uitrustingsstukken die de lijst al had.
COMBAT = ["Shoot AT", "Focus AT", "Focus DF", "Scramble AT", "Scramble DF", "Wall DF", "KP"]


def combat_stats(s):
    g = lambda k: s.get(k, 0)
    return {"Shoot AT": g("Kick") + g("Control"),
            "Focus AT": g("Technique") + g("Control") + g("Kick") * 0.5,
            "Focus DF": g("Technique") + g("Intelligence") + g("Agility") * 0.5,
            "Scramble AT": g("Intelligence") + g("Physical"),
            "Scramble DF": g("Intelligence") + g("Pressure"),
            "Wall DF": g("Pressure") + g("Physical"),
            "KP": g("Pressure") * 2 + g("Physical") * 3 + g("Agility") * 4}


def combat_text(s):
    """Focus AT en DF staan er altijd met een decimaal; de rest alleen als hij
    niet nul is, en zonder decimaal. Zo schrijft index.html ze bij alle 436."""
    w = combat_stats(s)
    out = []
    for k in COMBAT:
        if k in ("Focus AT", "Focus DF"):
            out.append(f"{k} {w[k]:.1f}")
        elif w[k]:
            out.append(f"{k} {w[k]:g}")
    return ", ".join(out)


def shop_of(item):
    for s in (item.get("shops") or []):
        if s and s.get("shop") in SHOP:
            return SHOP[s["shop"]]
    return UNKNOWN


def norm(name):
    return re.sub(r"[^a-z0-9 ]", "", (name or "").strip().lower())


def load_existing(path="index.html"):
    src = open(path, encoding="utf-8").read()
    start = src.index("const DATA = [")
    end = src.index("\n];", start)
    return json.loads(src[start + len("const DATA = "):end + 2])


def build(dump_path):
    import difflib
    dump = json.load(open(dump_path, encoding="utf-8-sig"))
    rows = load_existing()
    have = {}
    for r in rows:
        have.setdefault(r[1], set()).add(norm(r[0]))

    def is_new(name, category):
        n = norm(name)
        pool = have.get(category, set())
        if n in pool:
            return False
        # Een net andere schrijfwijze is hetzelfde item, geen nieuw item.
        return not difflib.get_close_matches(n, pool, n=1, cutoff=0.86)

    out = []
    for x in dump["equipment"]:
        if not x.get("name") or not is_new(x["name"], "Equipment"):
            continue
        st = OrderedDict()
        for key, value in x["stats"].items():
            if value:
                st[STAT_NAME[key]] = float(value)
        main = ", ".join(f"{k} +{st[k]:.1f}" for k in STAT_ORDER if k in st)
        out.append([x["name"], "Equipment", shop_of(x), main or "—",
                    combat_text(st), SLOT.get(x["slot"], "Misc"), ""])

    for x in dump["hissatsu"]:
        if not x.get("name") or not is_new(x["name"], "Special Move"):
            continue
        el = ELEMENT.get(x["element"], "")
        note = ("Long Shoot · " if x.get("is_longshot") else "") + el
        out.append([x["name"], "Special Move", shop_of(x),
                    f"Power {x['power']:g} / Tension {x['tp_consumption']:g}",
                    note, CATEGORY.get(x["category"], "Misc"), el])

    for x in dump["tactics"]:
        name = x.get("name") or ""
        # Vier regels dragen nog een onvertaalde Japanse plaatshouder.
        if not name or re.search(r"[぀-ヿ一-鿿]", name):
            continue
        if not is_new(name, "Tactic"):
            continue
        if any(r[0] == name for r in out):
            continue
        detail = (x.get("description") or "").replace("\\n", " ").strip()
        if x.get("tp_cost"):
            detail = (detail + " · " if detail else "") + f"TP {x['tp_cost']:g}"
        out.append([name, "Tactic", shop_of(x), "—", detail, "Tactic", ""])

    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(json.dumps(build(sys.argv[1]), ensure_ascii=False, indent=1))
