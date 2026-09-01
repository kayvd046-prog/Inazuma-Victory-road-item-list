# Inazuma Eleven: Victory Road — Shop Index

**<https://kayvd046-prog.github.io/Inazuma-Victory-road-item-list/>**

A searchable index of 1,879 items in *Inazuma Eleven: Victory Road* and where each one comes
from: special moves, hyper moves (Keshin, Totems, Awakenings), tactics, equipment, Bond Town
objects, kits and emblems.

Filter by shop, category, move type (Shoot / Offense / Defense / Keep) and element, and sort by
item, category, shop or type. Everything runs client-side in a single HTML file — no build step,
no dependencies, no tracking.

## Data sources

- **Inazuma Eleven VR Document v3.06** (community spreadsheet, last updated 2 March 2026) —
  moves, hyper moves, tactics, boots, bracelets, pendants, misc equipment, Kizuna Town items.
- **Chronicle kit and emblem unlocks** — kits and emblems per Chronicle team.
- Token prices from Operation Sports and NoobFeed guides.

Credit belongs to the people who compiled those sheets. If you maintain one of them and want
attribution changed or the data taken down, open an issue.

Items added to the game after March 2026 are not included. Use the **+ Add item** button to add
them yourself; entries are stored in your browser.

Filters, the search term and the sort order live in the URL, so any view you are looking at can
be bookmarked or shared as a link.

## Publishing this on GitHub Pages

### Option A — through the website, no git needed

1. Go to <https://github.com/new>. Name the repository, for example `victory-road-items`.
   Set it to **Public** and tick *Add a README file*. Click **Create repository**.
2. On the repository page click **Add file → Upload files**. Drag in `index.html` and
   `.nojekyll` (and this `README.md` if you want it). Click **Commit changes**.
3. Go to **Settings → Pages**. Under *Build and deployment* set **Source** to
   *Deploy from a branch*, **Branch** to `main` and the folder to `/ (root)`. Click **Save**.
4. Wait about a minute. Your site is live at
   `https://<your-username>.github.io/<repository-name>/`.

### Option B — from a terminal

```bash
gh repo create victory-road-items --public --source=. --push
gh api -X POST repos/:owner/victory-road-items/pages \
  -f 'source[branch]=main' -f 'source[path]=/'
```

### Notes

- `.nojekyll` is an empty file that tells GitHub Pages to serve the folder as-is instead of
  running it through Jekyll. Without it, files and folders starting with an underscore are
  skipped. Harmless to include either way.
- To use your own domain, add a file named `CNAME` containing just the domain, then point a
  CNAME record at `<your-username>.github.io` in your DNS.
- Updating later: replace `index.html` and commit. The page refreshes within a minute.

## Licence

The code is yours to do with as you like. The underlying game data belongs to Level-5, and the
compilation work belongs to the spreadsheet maintainers credited above.
