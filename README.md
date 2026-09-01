# Inazuma Eleven: Victory Road — Item List

**<https://kayvd046-prog.github.io/Inazuma-Victory-road-item-list/>**

A searchable index of 1,878 items in *Inazuma Eleven: Victory Road* and where each one comes
from: special moves, hyper moves (Keshin, Totems, Awakenings), tactics, equipment, Bond Town
objects, kits and emblems.

- Search by item name, shop, team or currency — words may be typed in any order.
- Filter by shop, category, move type (Shoot / Offense / Defense / Keep) and element.
- Filter by any of the 18 stats an item gives: the base stats (Kick, Control, Technique,
  Intelligence, Pressure, Agility, Physical), the combat stats (Shoot AT, Focus AT, Focus DF,
  Scramble AT, Scramble DF, Wall DF, KP), or a move's Power, Tension, Duration or cooldown.
- Pick several stats at once: only items that give all of them are shown. Click any of the
  chips to rank by that one stat, or **Total** to rank by what they add up to.
- Every filter, search term and sort order lives in the URL, so any view can be bookmarked or
  shared as a link.
- Every item name is a link to that one item, so you can share a direct link to a single
  entry instead of the whole list.
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
