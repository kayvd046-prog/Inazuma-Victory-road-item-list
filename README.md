# Inazuma Eleven: Victory Road — Item List

**<https://kayvd046-prog.github.io/Inazuma-Victory-road-item-list/>**

A searchable index of 1,879 items in *Inazuma Eleven: Victory Road* and where each one comes
from: special moves, hyper moves (Keshin, Totems, Awakenings), tactics, equipment, Bond Town
objects, kits and emblems.

- Search by item name, shop, team or currency — words may be typed in any order.
- Filter by shop, category, move type (Shoot / Offense / Defense / Keep) and element.
- Filter by the stat an item gives — Kick, Control, Technique, Intelligence, Pressure, Agility,
  Physical — or by a move's Power, Tension, Duration or cooldown.
- Sort by item, category, shop or type, and sort the Stats column by the value of the stat you
  picked, so the strongest items come first.
- Every filter, search term and sort order lives in the URL, so any view can be bookmarked or
  shared as a link.
- Spotted something wrong or missing? **Submit changes** opens a prefilled issue.

Alongside the searchable index there is a plain page per shop and per category — Spirit Market,
Chronicle Department Store, all Keshin, all boots, and so on — linked from the bottom of the main
page.

Items added to the game after March 2026 are not included.

## Editing the data

`index.html` is the only place the item list lives, in the `DATA` array near the top of its
script. The per-shop and per-category pages, the sitemap and the browse links are generated from
it by `tools/build-pages.py`, which a GitHub Action reruns on every push that touches
`index.html`. So edit `index.html` and nothing else; the rest catches up by itself. To rebuild
locally:

```bash
python3 tools/build-pages.py
```

Data comes from the Inazuma Eleven VR Document v3.06 and community kit, emblem and price
guides; the sources are credited at the bottom of the site.
