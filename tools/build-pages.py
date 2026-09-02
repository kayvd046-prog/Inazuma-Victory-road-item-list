#!/usr/bin/env python3
"""Genereert de statische winkel- en categoriepagina's uit index.html.

index.html is de enige bron: de itemlijst staat daar in de DATA-array en wordt
hier uitgelezen, nooit apart bijgehouden. Draai dit opnieuw na elke wijziging
aan die array; de GitHub Action in .github/workflows/pages.yml doet dat vanzelf.

    python3 tools/build-pages.py
"""
import html
import json
import re
import shutil
import base64
import unicodedata
from urllib.parse import quote
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://kayvd046-prog.github.io/Inazuma-Victory-road-item-list/"
GAME = "Inazuma Eleven: Victory Road"
MIN_ITEMS = 10          # onder deze grens is een eigen pagina te dun om te maken
TOTAL = 0               # aantal items; wordt in build() gezet
TOP_EQUIP = 15          # lengte van een ranglijst per stat
TOP_MOVE = 25

# ---------------------------------------------------------------- data inlezen

def load_rows():
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    start = src.index("const DATA = [")
    end = src.index("\n];", start)
    return json.loads(src[start + len("const DATA = "):end + 2])


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


# --------------------------------------------------------------- stats splitsen
# Zelfde regels als in index.html: kolom 3 is of stats, of prijs/vindplaats.
EQ_STAT = re.compile(r"^[A-Za-z][A-Za-z ]*\s[+-]\d")
MOVE_STAT = re.compile(r"^\s*(Power|Tension|Duration|CD)\s+([\d.]+)s?\s*$")


def is_stats(value):
    if not value or value == "—":
        return False
    if EQ_STAT.match(value):
        return True
    if " / " in value or MOVE_STAT.match(value):
        return all(MOVE_STAT.match(part) for part in value.split(" / "))
    return False


# De Details-kolom van uitrusting is een tweede set stats; zelfde regels als in
# index.html, zodat de pagina's dezelfde splitsing tonen.
SUB_STAT = re.compile(r"^([A-Za-z][A-Za-z ]*?)\s+(-?\d+(?:\.\d+)?)$")
ALT_STAT = re.compile(r"^(-?\d+(?:\.\d+)?)\s+([A-Za-z]+)$")
ALT_NAMES = {"Int", "Phys", "Tech", "Kick", "Control", "Agility", "Pressure"}


def split_details(row):
    """Geeft (stats-tekst, resterende toelichting) voor de Details-kolom."""
    v = (row[4] or "").strip()
    if not v:
        return "", ""
    if not is_stats(row[3]):
        head, _, rest = v.partition(" \u00b7 ")
        parts = [p.strip() for p in head.split(" / ")]
        ms = [ALT_STAT.match(p) for p in parts]
        if all(ms) and all(m.group(2) in ALT_NAMES for m in ms):
            return head, rest
    if all(SUB_STAT.match(p.strip()) for p in v.split(",")):
        return v, ""
    return "", v


def cost_text(row):
    """De prijs in tokens als die bekend is, anders de herkomst uit
    kolom 3 - en niets als daar de stats van het item staan."""
    price = row[7] if len(row) > 7 else ""
    if price:
        return price
    return "" if is_stats(row[3]) or row[3] == "—" else row[3]


def stats_text(row):
    parts = [row[3] if is_stats(row[3]) else "", split_details(row)[0]]
    return " \u00b7 ".join(p for p in parts if p)


def note_text(row):
    return split_details(row)[1]


# ------------------------------------------------- stats als getallen
# Dezelfde volgorde en dezelfde regels als STATS in index.html, zodat een
# ranglijst dezelfde cijfers gebruikt als de filters op de hoofdpagina.
PRIMARY = ["Kick", "Control", "Technique", "Intelligence", "Pressure", "Agility", "Physical"]
SECONDARY = ["Shoot AT", "Focus AT", "Focus DF", "Scramble AT", "Scramble DF", "Wall DF", "KP"]
MOVE_KEYS = ["Power", "Tension", "Duration", "CD"]
ALT_FULL = {"Int": "Intelligence", "Phys": "Physical", "Tech": "Technique",
            "Kick": "Kick", "Control": "Control", "Agility": "Agility", "Pressure": "Pressure"}


def _col3_stats(value):
    v = value or ""
    if EQ_STAT.match(v):
        return {m.group(1).strip(): float(m.group(2))
                for m in re.finditer(r"([A-Za-z][A-Za-z ]*?)\s*([+-]\d+(?:\.\d+)?)", v)}
    if " / " in v or MOVE_STAT.match(v):
        out = {}
        for part in v.split(" / "):
            m = MOVE_STAT.match(part)
            if not m:
                return {}
            out[m.group(1)] = float(m.group(2))
        return out
    return {}


def _alt_stats(value):
    head = (value or "").split(" \u00b7 ")[0]
    parts = [p.strip() for p in head.split(" / ")]
    ms = [ALT_STAT.match(p) for p in parts]
    if not parts or not all(ms) or not all(m.group(2) in ALT_FULL for m in ms):
        return None
    return {ALT_FULL[m.group(2)]: float(m.group(1)) for m in ms}


def _sub_stats(value):
    out = {}
    for part in (value or "").split(","):
        m = SUB_STAT.match(part.strip())
        if not m:
            return None
        out[m.group(1).strip()] = float(m.group(2))
    return out or None


def stat_map(row):
    """Alle stats van een rij als getallen: kolom 3 en de Details-kolom samen."""
    main = _col3_stats(row[3])
    alt = None if main else _alt_stats(row[4])
    sub = None if alt else _sub_stats(row[4])
    merged = dict(main)
    merged.update(alt or sub or {})
    return merged


def num(v):
    """Hele getallen zonder .0, zoals de bouwer op de hoofdpagina ze toont."""
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


# ------------------------------------------------------------------- opmaak

MOVIE = {"Special Move", "Hyper Move"}

# Dezelfde elementkleuren als index.html; de kanji staan al in de data.
EL_COLOR = {"火": "#FF6B35", "山": "#D98C3A", "林": "#3EA97B",
            "風": "#4A9BD0", "無": "#9A7BD0"}


def el_color(row):
    return EL_COLOR.get((row[6] or "")[:1], "")


CODEX = "zukan.inazuma.jp"


def codex_url(name):
    """Zoekopdracht in de Player Codex, in de vorm die die site zelf gebruikt.

    De JSON {"name_filter":["<naam>"]} met elke byte omgekeerd (XOR 0xFF), dan
    base64, dan percent-gecodeerd: bij 388 van de movenamen bevat de base64 een
    '+', die anders als spatie zou worden gelezen. Zelfde uitkomst als codexURL()
    in index.html.
    """
    payload = json.dumps({"name_filter": [name.lower()]},
                         separators=(",", ":"), ensure_ascii=False)
    blob = base64.b64encode(bytes(b ^ 0xFF for b in payload.encode())).decode()
    return f"https://{CODEX}/en/skill/?q={quote(blob, safe='')}"


# encodeURIComponent laat deze tekens staan; met dezelfde lijst geeft quote()
# letter voor letter dezelfde URL als index.html.
URI_SAFE = "!*'()"


def site_search(name):
    """Voor hyper moves kennen we het pad in de codex niet, dus zoeken we ernaar."""
    return f"https://www.google.com/search?q={quote(f'site:{CODEX} {name}', safe=URI_SAFE)}"


def clip(name, category):
    href = codex_url(name) if category == "Special Move" else site_search(name)
    return (f' <a class="codex" target="_blank" rel="noopener nofollow"'
            f' title="Watch {html.escape(name)} in the Inazuma Eleven Player Codex"'
            f' href="{href}">video &#8599;</a>')


def page(title, description, canonical, heading, intro, rows, siblings, sib_label):
    """Een gewone lijstpagina: alle items van een winkel of soort onder elkaar."""
    return shell(title, description, canonical, heading, intro,
                 table_html(rows), siblings, sib_label)


def table_html(rows):
    e = html.escape
    # Een kolom die op deze pagina overal hetzelfde is (de winkel op een
    # winkelpagina) of overal leeg, zegt niets en gaat eruit.
    varies = lambda i: len({r[i] for r in rows}) > 1
    show_cat = varies(1)
    show_shop = varies(2)
    show_cost = any(cost_text(r) for r in rows)
    show_stats = any(stats_text(r) for r in rows)
    show_type = any(r[5] and r[5] != "?" for r in rows)
    show_note = any(note_text(r) for r in rows)

    head = ["<tr><th>Item</th>"]
    for on, label in ((show_cat, "Category"), (show_shop, "Shop"),
                      (show_cost, "Cost / source"), (show_stats, "Stats"),
                      (show_type, "Type"), (show_note, "Details")):
        if on:
            head.append(f"<th>{label}</th>")
    head.append("</tr>")

    body = []
    for r in rows:
        play = clip(r[0], r[1]) if r[1] in MOVIE else ""
        # Naar het item in de doorzoekbare lijst; nofollow zodat Google niet 1.879
        # querystring-varianten van dezelfde pagina gaat crawlen.
        href = f"{SITE}?q={quote(r[0], safe='')}"
        cells = [f'<td class="name">'
                 f'<a class="item" rel="nofollow" href="{href}">{e(r[0])}</a>{play}</td>']
        if show_cat:
            cells.append(f"<td>{e(r[1])}</td>")
        if show_shop:
            cells.append(f"<td>{e(r[2])}</td>")
        if show_cost:
            cells.append(f'<td class="cost">{e(cost_text(r))}</td>')
        if show_stats:
            main = r[3] if is_stats(r[3]) else ""
            sub = split_details(r)[0]
            inner = ((f'<span class="s-main">{e(main)}</span>' if main else "")
                     + (f'<span class="s-sub">{e(sub)}</span>' if sub else ""))
            cells.append(f'<td class="stats">{inner}</td>')
        if show_type:
            cells.append(f'<td>{e(r[5]) if r[5] and r[5] != "?" else ""}</td>')
        if show_note:
            cells.append(f'<td class="note">{e(note_text(r))}</td>')
        el = el_color(r)
        attr = f' style="--el:{el}"' if el else ""
        body.append(f"<tr{attr}>" + "".join(cells) + "</tr>")

    return f"""<main class="wrap">
  <table>
    <thead>{''.join(head)}</thead>
    <tbody>
{chr(10).join('      ' + row for row in body)}
    </tbody>
  </table>
</main>"""


def shell(title, description, canonical, heading, intro, main_html, siblings, sib_label):
    """De omhulling die elke subpagina deelt: kop, stijl, inhoud, voetregel."""
    e = html.escape
    links = "".join(
        f'<li><a href="{e(href)}">{e(name)}</a> <span>{n}</span></li>'
        for name, href, n in siblings
    )

    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "url": canonical,
        "name": title,
        "description": description,
        "isPartOf": {"@type": "WebSite", "url": SITE, "name": "Victory Road Item List"},
        "about": {"@type": "VideoGame", "name": GAME},
    }, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta name="robots" content="index, follow, max-snippet:-1">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0B0F2B">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{SITE}og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ctext y='26' font-size='26'%3E%E2%9A%A1%3C/text%3E%3C/svg%3E">
<script type="application/ld+json">
{ld}
</script>
<style>
  *{{box-sizing:border-box}}
  body{{margin:0;color:#E9ECFB;font-family:'Barlow','Helvetica Neue',system-ui,sans-serif;font-size:15px;line-height:1.5;
        background:radial-gradient(1100px 480px at 78% -6%, rgba(255,107,53,.20), transparent 62%),
                   radial-gradient(760px 420px at 6% 0%, rgba(255,210,63,.10), transparent 60%),#0B0F2B;
        background-attachment:fixed}}
  body::before{{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.5;
        background:repeating-linear-gradient(-19deg, rgba(255,210,63,.055) 0 2px, transparent 2px 26px)}}
  .wrap{{max-width:1180px;margin:0 auto;padding:0 24px}}
  header{{padding:34px 0 22px;display:flex;align-items:flex-start;gap:20px}}
  .bolt-mark{{flex:none;margin-top:4px}}
  .crumb{{color:#949CD0;font-size:14px;margin:0 0 10px}}
  .crumb a{{color:#FFD23F}}
  h1{{font-family:'Archivo Black','Helvetica Neue',system-ui,sans-serif;font-size:clamp(26px,5vw,42px);
      line-height:1;margin:0 0 10px;text-transform:uppercase;text-shadow:4px 4px 0 #1B2250}}
  .slash{{height:12px;background:linear-gradient(90deg,#FFD23F,#FF6B35 70%,#FFD23F);
      clip-path:polygon(0 0,100% 0,100% 62%,0 100%)}}
  .lede{{color:#949CD0;max-width:70ch;margin:0}}
  table{{width:100%;border-collapse:collapse;margin:22px 0 8px}}
  th{{text-align:left;color:#949CD0;font-size:14px;padding:10px 12px;border-bottom:3px solid #FFD23F;
      white-space:nowrap;font-family:'Barlow Semi Condensed','Helvetica Neue',system-ui,sans-serif;
      text-transform:uppercase;letter-spacing:.10em;font-weight:600}}
  td{{padding:10px 12px;border-bottom:1px solid #1B2250;vertical-align:top}}
  tbody tr{{border-left:4px solid var(--el, transparent)}}
  tbody td:first-child{{padding-left:14px}}
  .name{{font-weight:600}}
  a.item{{color:inherit;text-decoration:none}}
  a.item:hover{{color:#FFD23F;text-decoration:underline}}
  .codex{{color:#949CD0;text-decoration:none;font-size:10.5px;vertical-align:middle;white-space:nowrap;letter-spacing:.03em;text-transform:uppercase;border:1px solid #2B3369;border-radius:2px;padding:1px 5px;margin-left:7px}}
  .codex:hover{{color:#FF6B35;border-color:#FF6B35}}
  .cost{{font-size:14px}}
  .stats{{color:#FFD23F;font-size:14px}}
  .s-main{{display:block}}
  .s-sub{{display:block;color:#949CD0;font-size:13px;margin-top:3px}}
  .note{{color:#949CD0;font-size:13.5px}}
  h2.sec{{font-family:'Archivo Black','Helvetica Neue',system-ui,sans-serif;font-size:19px;
          text-transform:uppercase;margin:38px 0 4px;color:#fff;letter-spacing:.01em}}
  h2.sec::before{{content:"";display:block;width:54px;height:4px;background:#FFD23F;margin-bottom:11px}}
  .sec-note{{color:#949CD0;font-size:14px;margin:0}}
  .jump ul{{list-style:none;padding:0;margin:18px 0 0;display:flex;flex-wrap:wrap;gap:8px}}
  .jump a{{color:#E9ECFB;text-decoration:none;border:1px solid #2B3369;padding:6px 12px;
          display:inline-block;font-size:14px;
          font-family:'Barlow Semi Condensed','Helvetica Neue',system-ui,sans-serif;
          text-transform:uppercase;letter-spacing:.05em}}
  .jump a:hover{{border-color:#FFD23F;color:#FFD23F}}
  .jump span{{color:#949CD0;font-size:13px}}
  td.rk{{color:#949CD0;font-variant-numeric:tabular-nums;width:34px;text-align:right}}
  td.val{{color:#FFD23F;font-weight:700;font-size:17px;font-variant-numeric:tabular-nums;white-space:nowrap;
         font-family:'Barlow Semi Condensed','Helvetica Neue',system-ui,sans-serif}}
  nav.more{{border-top:1px solid #2B3369;padding:22px 0 8px}}
  nav.more h2{{font-size:15px;color:#949CD0;margin:0 0 10px;font-weight:600}}
  nav.more ul{{list-style:none;padding:0;margin:0;display:flex;flex-wrap:wrap;gap:8px}}
  nav.more a{{color:#E9ECFB;text-decoration:none;border:1px solid #2B3369;border-radius:3px;padding:7px 12px;display:inline-block;font-size:14px}}
  nav.more a:hover{{border-color:#FFD23F;color:#FFD23F}}
  nav.more span{{color:#949CD0}}
  footer{{color:#949CD0;font-size:13px;padding:20px 0 40px}}
  footer a{{color:#FFD23F}}
  @media (max-width:720px){{
    thead{{display:none}}
    tr{{display:block;border-bottom:1px solid #2B3369;padding:10px 0}}
    td{{display:block;border:0;padding:2px 0}}
    td:empty{{display:none}}
  }}
</style>
</head>
<body>
<header class="wrap">
  <svg class="bolt-mark" width="34" height="47" viewBox="0 0 62 86" fill="none" aria-hidden="true">
    <path d="M38 2 6 50h20L20 84 56 32H34L38 2Z" fill="#FFD23F" stroke="#0B0F2B" stroke-width="3"/>
  </svg>
  <div>
    <p class="crumb"><a href="{SITE}">{e(GAME)} item list</a></p>
    <h1>{e(heading)}</h1>
    <p class="lede">{e(intro)}</p>
  </div>
</header>
<div class="slash"></div>
{main_html}
{f'<nav class="more wrap"><h2>{e(sib_label)}</h2><ul>{links}</ul></nav>' if links else ''}
<footer class="wrap">
  <p>Part of the <a href="{SITE}">{e(GAME)} item list</a> &mdash; all {TOTAL:,} items, searchable and filterable.
  Data from the Inazuma Eleven VR Document v3.06 and community guides.</p>
</footer>
</body>
</html>
"""


# ------------------------------------------------------------- ranglijsten
# Niemand zoekt op "Chronicle Department Store"; mensen zoeken op "best boots".
# Deze pagina's beantwoorden die vraag rechtstreeks uit de data: per slot en per
# soort move de hoogste waarden, met de winkel erbij.

SLOT_PAGES = [
    ("Boots", "boots", "boots",
     "Every pair of boots ranked by the stat it raises"),
    ("Pendant", "pendants", "pendants",
     "Every pendant ranked by the stat it raises"),
    ("Bracelet", "bracelets", "bracelets",
     "Every bracelet ranked by the stat it raises"),
    ("Misc", "misc-equipment", "misc equipment",
     "Every misc item ranked by the stat it raises"),
]

MOVE_PAGES = [
    ("Shoot", "shoot-moves", "shoot moves"),
    ("Dribble", "dribble-moves", "dribble moves"),
    ("Block", "block-moves", "block moves"),
    ("Catch", "catch-moves", "catch moves"),
]

ELEMENTS = [("火", "Fire"), ("山", "Mountain"), ("林", "Forest"),
            ("風", "Wind"), ("無", "Void")]


def ranked(items, stat, top):
    """De hoogste <top> items op deze stat.

    Een naam die twee keer voorkomt met precies dezelfde stats is hetzelfde item
    uit twee winkels; dat telt als een regel, met beide winkels erbij. Lucky
    Bracelet bestaat wel twee keer met andere stats en blijft dus twee regels.
    """
    seen = {}
    for r in items:
        v = stat_map(r).get(stat)
        if v is None:
            continue
        key = (r[0], r[3], r[4])
        if key in seen:
            if r[2] not in seen[key][1]:
                seen[key][1].append(r[2])
            continue
        seen[key] = [r, [r[2]], v]
    return sorted(seen.values(), key=lambda e: (-e[2], e[0][0]))[:top]


def rank_table(entries, stat, show_element=False):
    e = html.escape
    head = ["<tr><th>#</th><th>Item</th>", f"<th>{e(stat)}</th>"]
    if show_element:
        head.append("<th>Element</th>")
    head.append("<th>Stats</th><th>Shop</th></tr>")

    body = []
    for n, (r, shops, v) in enumerate(entries, 1):
        play = clip(r[0], r[1]) if r[1] in MOVIE else ""
        href = f"{SITE}?q={quote(r[0], safe='')}"
        cells = [f'<td class="rk">{n}</td>',
                 f'<td class="name"><a class="item" rel="nofollow" href="{href}">{e(r[0])}</a>{play}</td>',
                 f'<td class="val">{num(v)}</td>']
        if show_element:
            cells.append(f"<td>{e(r[6])}</td>")
        cells.append(f'<td class="stats">{e(stats_text(r))}</td>')
        cells.append(f"<td>{e(' / '.join(shops))}</td>")
        el = el_color(r)
        attr = f' style="--el:{el}"' if el else ""
        body.append(f"<tr{attr}>" + "".join(cells) + "</tr>")

    return ("  <table>\n    <thead>" + "".join(head) + "</thead>\n    <tbody>\n"
            + "\n".join("      " + b for b in body) + "\n    </tbody>\n  </table>")


def sections_html(sections):
    """Kopjes met een springlijst erboven, zodat een lange pagina te doen blijft."""
    e = html.escape
    jump = "".join(f'<li><a href="#{slug(t)}">{e(t)}</a></li>' for t, _, _ in sections)
    parts = [f'<nav class="jump"><ul>{jump}</ul></nav>']
    for title, note, table in sections:
        parts.append(f'<h2 class="sec" id="{slug(title)}">{e(title)}</h2>')
        if note:
            parts.append(f'<p class="sec-note">{e(note)}</p>')
        parts.append(table)
    return '<main class="wrap">\n' + "\n".join(parts) + "\n</main>"


def best_links(pages):
    return [(label, f"{SITE}best/{name}.html", n) for label, name, n in pages]


def build_best(rows, links):
    """Acht ranglijstpagina's plus een overzicht."""
    written = []
    e = html.escape

    for slot, name, plural, tag in SLOT_PAGES:
        items = [r for r in rows if r[1] == "Equipment" and r[5] == slot]
        sections = []
        for stat in PRIMARY + SECONDARY:
            entries = ranked(items, stat, TOP_EQUIP)
            # Onder de vijf items is een ranglijst geen ranglijst.
            if len(entries) < 5:
                continue
            best = entries[0]
            sections.append((
                f"Highest {stat}",
                f"{best[0][0]} leads with {num(best[2])}. "
                f"{len(entries)} of the {len(items)} {plural} are listed here, highest first.",
                rank_table(entries, stat),
            ))
        canonical = f"{SITE}best/{name}.html"
        (ROOT / "best" / f"{name}.html").write_text(shell(
            title=f"Best {plural} in {GAME} &mdash; ranked by stat".replace("&mdash;", "—"),
            description=(f"The {len(items)} {plural} in {GAME} ranked by every stat they give, "
                         f"from Kick and Control to Shoot AT and KP, with the shop for each."),
            canonical=canonical,
            heading=f"Best {plural}",
            intro=(f"All {len(items)} {plural} in {GAME}, ranked by each stat they raise. "
                   f"Pick the stat your player needs and take the top of that list."),
            main_html=sections_html(sections),
            siblings=[l for l in links if l[1] != canonical],
            sib_label="Other rankings",
        ), encoding="utf-8")
        written.append(ROOT / "best" / f"{name}.html")

    for kind, name, plural in MOVE_PAGES:
        items = [r for r in rows if r[1] == "Special Move" and r[5] == kind]
        sections = []
        power = ranked(items, "Power", TOP_MOVE)
        if power:
            sections.append((
                "Most powerful",
                f"The {len(power)} strongest of the {len(items)} {plural}, by Power.",
                rank_table(power, "Power", show_element=True),
            ))
        dur = ranked(items, "Duration", 15)
        if dur:
            sections.append((
                "Longest lasting",
                "Duration is how long the move runs, in seconds.",
                rank_table(dur, "Duration", show_element=True),
            ))
        for kanji, label in ELEMENTS:
            sub_items = [r for r in items if (r[6] or "").startswith(kanji)]
            entries = ranked(sub_items, "Power", 10)
            if len(entries) < 3:
                continue
            sections.append((
                f"Strongest {label} {plural}",
                f"{len(sub_items)} {plural} carry the {label} element.",
                rank_table(entries, "Power"),
            ))
        canonical = f"{SITE}best/{name}.html"
        (ROOT / "best" / f"{name}.html").write_text(shell(
            title=f"Best {plural} in {GAME} &mdash; ranked by power".replace("&mdash;", "—"),
            description=(f"The {len(items)} {plural} in {GAME} ranked by Power and Duration, "
                         f"overall and per element, with the shop that sells each one."),
            canonical=canonical,
            heading=f"Best {plural}",
            intro=(f"All {len(items)} {plural} in {GAME}, ranked by Power and by how long they last, "
                   f"overall and for each element."),
            main_html=sections_html(sections),
            siblings=[l for l in links if l[1] != canonical],
            sib_label="Other rankings",
        ), encoding="utf-8")
        written.append(ROOT / "best" / f"{name}.html")

    hub = ('<main class="wrap">\n<nav class="jump"><ul>'
           + "".join(f'<li><a href="{e(href.replace(SITE, SITE))}">{e(label)}</a> '
                     f"<span>{n}</span></li>" for label, href, n in links)
           + "</ul></nav>\n</main>")
    (ROOT / "best" / "index.html").write_text(shell(
        title=f"Best equipment and moves in {GAME}",
        description=(f"Rankings for every stat in {GAME}: the strongest boots, pendants, "
                     f"bracelets and misc items, and the most powerful shoot, dribble, "
                     f"block and catch moves."),
        canonical=f"{SITE}best/",
        heading="Best of Victory Road",
        intro=("Eight rankings, worked out from the item list itself: equipment ordered by "
               "every stat it gives, and moves ordered by power and duration."),
        main_html=hub,
        siblings=[],
        sib_label="",
    ), encoding="utf-8")
    written.append(ROOT / "best" / "index.html")
    return written


# ---------------------------------------------------------------------- bouwen

def build():
    global TOTAL
    rows = load_rows()
    TOTAL = len(rows)
    for folder in ("shops", "categories", "best"):
        target = ROOT / folder
        if target.exists():
            shutil.rmtree(target)
        target.mkdir()

    groups = {}
    for key, field, folder in (("shop", 2, "shops"), ("category", 1, "categories")):
        counts = {}
        for r in rows:
            counts.setdefault(r[field], []).append(r)
        groups[key] = {
            name: items for name, items in counts.items() if len(items) >= MIN_ITEMS
        }

    shop_links = [
        (name, f"{SITE}shops/{slug(name)}.html", len(items))
        for name, items in sorted(groups["shop"].items(), key=lambda kv: -len(kv[1]))
    ]
    cat_links = [
        (name, f"{SITE}categories/{slug(name)}.html", len(items))
        for name, items in sorted(groups["category"].items(), key=lambda kv: -len(kv[1]))
    ]

    written = []
    for name, items in groups["shop"].items():
        kinds = sorted({r[1] for r in items})
        path = ROOT / "shops" / f"{slug(name)}.html"
        path.write_text(page(
            title=f"{name} &mdash; every item it sells in {GAME}".replace("&mdash;", "—"),
            description=(f"All {len(items)} items available from {name} in {GAME}: "
                         f"{', '.join(kinds).lower()}, with the cost or stats of each."),
            canonical=f"{SITE}shops/{slug(name)}.html",
            heading=name,
            intro=(f"Every one of the {len(items)} items {name} offers in {GAME}, "
                   f"with what each one costs or the stats it gives."),
            rows=items, siblings=[l for l in shop_links if l[0] != name],
            sib_label="Other shops",
        ), encoding="utf-8")
        written.append(path)

    for name, items in groups["category"].items():
        shops = sorted({r[2] for r in items})
        path = ROOT / "categories" / f"{slug(name)}.html"
        path.write_text(page(
            title=f"All {name.lower()}s in {GAME} and where to get them",
            description=(f"All {len(items)} {name.lower()} entries in {GAME}, "
                         f"from {len(shops)} sources, with cost or stats for each."),
            canonical=f"{SITE}categories/{slug(name)}.html",
            heading=f"{name}s",
            intro=(f"All {len(items)} {name.lower()} entries in {GAME}, spread over "
                   f"{len(shops)} shop{'s' if len(shops) != 1 else ''}."),
            rows=items, siblings=[l for l in cat_links if l[0] != name],
            sib_label="Other categories",
        ), encoding="utf-8")
        written.append(path)

    rank_links = best_links(
        [(f"Best {plural}", name, len([r for r in rows
                                       if r[1] == "Equipment" and r[5] == slot]))
         for slot, name, plural, _ in SLOT_PAGES]
        + [(f"Best {plural}", name, len([r for r in rows
                                         if r[1] == "Special Move" and r[5] == kind]))
           for kind, name, plural in MOVE_PAGES])
    written += build_best(rows, rank_links)

    urls = [SITE] + [f"{SITE}{p.relative_to(ROOT).as_posix()}" for p in written]
    today = date.today().isoformat()
    entries = "\n".join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n"
        f"    <priority>{'1.0' if u == SITE else '0.7'}</priority>\n  </url>"
        for u in urls
    )
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n</urlset>\n", encoding="utf-8")

    write_browse_block(shop_links, cat_links, rank_links)

    print(f"{len(written)} pagina's, {len(urls)} URL's in de sitemap")
    return shop_links, cat_links


def write_browse_block(shop_links, cat_links, rank_links):
    """Zet de links naar de subpagina's in index.html tussen de markers.

    Zonder deze links zijn het weespagina's: bezoekers vinden ze niet en
    zoekmachines crawlen ze nauwelijks.
    """
    def block(label, links):
        items = "".join(
            f'<li><a href="{href.replace(SITE, "")}">{html.escape(name)}</a> '
            f"<span>{n}</span></li>"
            for name, href, n in links
        )
        return f"  <h2>{label}</h2>\n  <ul>{items}</ul>\n"

    body = ("  <!-- browse:start -->\n"
            + block('Best of &mdash; <a href="best/">all rankings</a>', rank_links)
            + block("Browse by shop", shop_links)
            + block("Browse by category", cat_links)
            + "  <!-- browse:end -->")

    path = ROOT / "index.html"
    src = path.read_text(encoding="utf-8")
    new = re.sub(r"  <!-- browse:start -->.*?  <!-- browse:end -->",
                 lambda _: body, src, count=1, flags=re.S)
    if new == src and "browse:start" not in src:
        raise SystemExit("markers ontbreken in index.html")
    path.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    build()
