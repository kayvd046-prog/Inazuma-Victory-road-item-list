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
import unicodedata
from urllib.parse import quote
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://kayvd046-prog.github.io/Inazuma-Victory-road-item-list/"
GAME = "Inazuma Eleven: Victory Road"
MIN_ITEMS = 10          # onder deze grens is een eigen pagina te dun om te maken

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


def stats_text(row):
    parts = [row[3] if is_stats(row[3]) else "", split_details(row)[0]]
    return " \u00b7 ".join(p for p in parts if p)


def note_text(row):
    return split_details(row)[1]


# ------------------------------------------------------------------- opmaak

MOVIE = {"Special Move", "Hyper Move"}


def clip(name):
    """Zoeklink naar beeldmateriaal van een move.

    De dataset bevat geen beeld en het spelmateriaal is niet van ons om te
    hosten, dus verwijzen we naar een zoekopdracht in plaats daarvan.
    """
    # Zelfde codering als encodeURIComponent in index.html.
    q = quote(f"Inazuma Eleven Victory Road {name}", safe="")
    return (f' <a class="play" target="_blank" rel="noopener nofollow"'
            f' title="Watch {html.escape(name)} on YouTube"'
            f' href="https://www.youtube.com/results?search_query={q}">&#9654;</a>')


def page(title, description, canonical, heading, intro, rows, siblings, sib_label):
    e = html.escape
    # Een kolom die op deze pagina overal hetzelfde is (de winkel op een
    # winkelpagina) of overal leeg, zegt niets en gaat eruit.
    varies = lambda i: len({r[i] for r in rows}) > 1
    show_cat = varies(1)
    show_shop = varies(2)
    show_cost = any(not is_stats(r[3]) and r[3] and r[3] != "—" for r in rows)
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
        play = clip(r[0]) if r[1] in MOVIE else ""
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
            cells.append(f'<td class="cost">{"" if is_stats(r[3]) else e(r[3])}</td>')
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
        body.append("<tr>" + "".join(cells) + "</tr>")

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
  body{{margin:0;background:#0B0F2B;color:#E9ECFB;font-family:'Barlow','Helvetica Neue',system-ui,sans-serif;font-size:15px;line-height:1.5}}
  .wrap{{max-width:1180px;margin:0 auto;padding:0 24px}}
  header{{border-bottom:2px solid #FFD23F;padding:34px 0 20px}}
  .crumb{{color:#949CD0;font-size:14px;margin:0 0 10px}}
  .crumb a{{color:#FFD23F}}
  h1{{font-family:'Archivo Black','Helvetica Neue',system-ui,sans-serif;font-size:clamp(26px,5vw,42px);line-height:1;margin:0 0 10px;text-transform:uppercase}}
  .lede{{color:#949CD0;max-width:70ch;margin:0}}
  table{{width:100%;border-collapse:collapse;margin:22px 0 8px}}
  th{{text-align:left;color:#949CD0;font-size:14px;padding:10px 12px;border-bottom:1px solid #2B3369;white-space:nowrap}}
  td{{padding:10px 12px;border-bottom:1px solid #1B2250;vertical-align:top}}
  .name{{font-weight:600}}
  a.item{{color:inherit;text-decoration:none}}
  a.item:hover{{color:#FFD23F;text-decoration:underline}}
  .play{{color:#949CD0;text-decoration:none;font-size:11px;vertical-align:middle;border:1px solid #2B3369;border-radius:2px;padding:1px 5px;margin-left:6px}}
  .play:hover{{color:#FF6B35;border-color:#FF6B35}}
  .cost{{font-size:14px}}
  .stats{{color:#FFD23F;font-size:14px}}
  .s-main{{display:block}}
  .s-sub{{display:block;color:#949CD0;font-size:13px;margin-top:3px}}
  .note{{color:#949CD0;font-size:13.5px}}
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
  <p class="crumb"><a href="{SITE}">{e(GAME)} item list</a></p>
  <h1>{e(heading)}</h1>
  <p class="lede">{e(intro)}</p>
</header>
<main class="wrap">
  <table>
    <thead>{''.join(head)}</thead>
    <tbody>
{chr(10).join('      ' + row for row in body)}
    </tbody>
  </table>
</main>
<nav class="more wrap">
  <h2>{e(sib_label)}</h2>
  <ul>{links}</ul>
</nav>
<footer class="wrap">
  <p>Part of the <a href="{SITE}">{e(GAME)} item list</a> &mdash; all 1,879 items, searchable and filterable.
  Data from the Inazuma Eleven VR Document v3.06 and community guides.</p>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------- bouwen

def build():
    rows = load_rows()
    for folder in ("shops", "categories"):
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

    write_browse_block(shop_links, cat_links)

    print(f"{len(written)} pagina's, {len(urls)} URL's in de sitemap")
    return shop_links, cat_links


def write_browse_block(shop_links, cat_links):
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
