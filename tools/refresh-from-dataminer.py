#!/usr/bin/env python3
"""Werkt de bestaande rijen in index.html bij vanuit de datamined dump.

Twee dingen die de community-bron van maart 2026 niet had of niet meer klopten:

* Prijzen. De lijst wist wel bij welke winkel iets ligt, maar niet wat het kost;
  daarom stond de kolom "Cost / source" bij uitrusting en moves leeg. De dump
  kent van 458 van de 468 uitrustingsstukken en 751 van de 852 moves het precieze
  aantal tokens. Die komen in een achtste kolom, zodat de stats blijven staan waar
  ze stonden.
* Moves die later gebufft zijn: Chaos Break ging van Power 100 naar 180. Alleen
  Power en Tension worden overgenomen; de Duration staat niet in de dump en blijft
  dus staan zoals hij was.

Kosten in spirits (Keshin, Totems) worden met rust gelaten: de dump noteert daar
alleen character-ids en spirit-rangen, en die zijn niet betrouwbaar terug te
vertalen naar "2x Legendary Goenji" zoals de lijst het schrijft.

    python3 tools/refresh-from-dataminer.py /pad/naar/ievr.en.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOP = {"market_01": "Chronicle Department Store", "market_02": "VS Store",
        "market_05": "Spirit Market", "unnamed_02": "Special Training Booth",
        "story_01": "G-Mart (Arcade Branch)", "story_02": "G-Mart (Arcade Branch)",
        "story_03": "G-Mart (Arcade Branch)", "story_04": "Kool Kit (Odaiba Branch)",
        "story_05": "Kool Kit (Odaiba Branch)",
        "story_06": "Magic Moves (Arcade Branch)",
        "story_07": "Magic Moves (Arcade Branch)"}


def norm(name):
    return re.sub(r"[^a-z0-9 ]", "", (name or "").strip().lower())


def load_data(src):
    start = src.index("const DATA = [")
    end = src.index("\n];", start)
    return json.loads(src[start + len("const DATA = "):end + 2]), start, end


def price_text(item, currencies, prefer=None):
    """De prijs bij de winkel die de lijst noemt; anders de eerste die er is."""
    options = []
    for s in (item.get("shops") or []):
        if not s or not s.get("price"):
            continue
        text = " + ".join(f"{p['amount']}x {currencies.get(p['currency'], p['currency'])}"
                          for p in s["price"])
        options.append((SHOP.get(s.get("shop")), text))
    if not options:
        return ""
    for shop, text in options:
        if prefer and shop == prefer:
            return text
    return options[0][1]


def main(dump_path):
    dump = json.load(open(dump_path, encoding="utf-8-sig"))
    currencies = {c["string_id"]: c["name"] for c in dump["currencies"]}
    equipment = {norm(x["name"]): x for x in dump["equipment"] if x.get("name")}
    moves = {norm(x["name"]): x for x in dump["hissatsu"] if x.get("name")}

    path = ROOT / "index.html"
    src = path.read_text(encoding="utf-8")
    rows, start, end = load_data(src)

    priced = buffed = 0
    for r in rows:
        while len(r) < 8:
            r.append("")
        key = norm(r[0])
        item = equipment.get(key) if r[1] == "Equipment" else moves.get(key) if r[1] == "Special Move" else None
        if not item:
            continue
        text = price_text(item, currencies, prefer=r[2])
        if text and not r[7]:
            r[7] = text
            priced += 1
        if r[1] == "Special Move":
            m = re.match(r"Power ([\d.]+) / Tension ([\d.]+)(.*)$", r[3])
            if m and (float(m.group(1)) != item["power"]
                      or float(m.group(2)) != item["tp_consumption"]):
                r[3] = f"Power {item['power']:g} / Tension {item['tp_consumption']:g}{m.group(3)}"
                buffed += 1

    block = "\n".join("[" + ", ".join(json.dumps(c, ensure_ascii=False) for c in r) + "],"
                      for r in rows).rstrip(",")
    path.write_text(src[:start] + "const DATA = [\n" + block + src[end:], encoding="utf-8")
    print(f"{priced} rijen met een prijs, {buffed} moves bijgewerkt, {len(rows)} rijen totaal")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
