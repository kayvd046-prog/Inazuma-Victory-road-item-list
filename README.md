# Inazuma Eleven: Victory Road — Item List

**<https://kayvd046-prog.github.io/Inazuma-Victory-road-item-list/>**

A searchable index of 2,060 items in *Inazuma Eleven: Victory Road* and where each one comes
from: special moves, hyper moves (Keshin, Totems, Awakenings), tactics, equipment, Bond Town
objects, kits and emblems.

- Search by item name, shop, team or currency — words may be typed in any order.
- Filter by shop, category, move type (Shoot / Dribble / Block / Catch) and element.
- Filter by any of the 18 stats an item gives: the base stats (Kick, Control, Technique,
  Intelligence, Pressure, Agility, Physical), the combat stats (Shoot AT, Focus AT, Focus DF,
  Scramble AT, Scramble DF, Wall DF, KP), or a move's Power, Tension, Duration or cooldown.
- Pick several stats at once: only items that give all of them are shown. Click any of the
  chips to rank by that one stat, or **Total** to rank by what they add up to.
- Every filter, search term and sort order lives in the URL, so any view can be bookmarked or
  shared as a link.
- Every item name is a link to that one item, so you can share a direct link to a single
  entry instead of the whole list.
- Every special move and hyper move has a **video** link that looks it up in the official
  Inazuma Eleven Player Codex.
- **Build a set** puts a character next to their gear: search one of 5,206 characters, switch
  between their normal, Hero and Fabled version and between level 50 and 99, fill the boots,
  pendant, bracelet and misc slots, and see the base stats and the combat stats they end up with —
  base, what the gear adds, and the total. Each gear slot is a search list that shows the stats of
  every item, and the menu above it ranks all four lists by any stat you like. The character, the
  version, the level and the set live in the URL, so a build can be shared as a link.
- Spotted something wrong or missing? **Submit changes** opens a prefilled issue.

Alongside the searchable index there is a plain page per shop and per category — Spirit Market,
Chronicle Department Store, all Keshin, all boots, and so on — plus eight ranking pages under
`best/`: every piece of equipment ordered by each stat it gives, and the shoot, dribble, block and
catch moves ordered by power and duration. All of them are linked from the bottom of the main page.

The list started from a community document of March 2026. The 189 moves, equipment and tactics that
the Ares and Orion routes and the updates after them added were imported from a datamined dump of
game version 6.00.23.00 (`tools/import-dataminer.py`), and `tools/refresh-from-dataminer.py` filled
in the token prices of 1,248 items and the 74 moves whose power was changed by later patches. Kits
and emblems for those routes are not in that dump and are still missing.

## Editing the data

`index.html` is the only place the item list lives, in the `DATA` array near the top of its
script. The per-shop and per-category pages, the sitemap and the browse links are generated from
it by `tools/build-pages.py`, which a GitHub Action reruns on every push that touches
`index.html`. So edit `index.html` and nothing else; the rest catches up by itself. To rebuild
locally:

```bash
python3 tools/build-pages.py
```

`characters.json` is the one data file that is not derived from `index.html`: 5,206 characters with
their level 50 and level 99 stats, plus the Hero and Fabled versions where the game has them, read
out of the datamined dump. It is fetched only when the builder is opened, so it costs nothing on a
normal visit. A character's combat stats are computed, not stored: `powerOf()` in `index.html` holds
the formulas, which reproduce the combat stats of all 491 pieces of equipment in `DATA` exactly, so
they can be trusted for characters too.

Data comes from the Inazuma Eleven VR Document v3.06 and community kit, emblem and price
guides; the sources are credited at the bottom of the site.
