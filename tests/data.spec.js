// De data zelf, en de teksten die erop leunen. Deze tests falen zodra een wijziging
// aan de DATA-array iets anders op de site laat kloppen: de generator die de
// rijen anders leest, een dubbele import, of een FAQ-getal dat niet meer klopt.
const { execFileSync } = require('child_process');
const path = require('path');
const { test, expect } = require('./fixtures');

const ROOT = path.resolve(__dirname, '..');

// Dezelfde vijf dingen als de pagina per rij bepaalt, maar dan uit tools/build-pages.py.
const PY = `
import importlib.util, json
spec = importlib.util.spec_from_file_location('bp', 'tools/build-pages.py')
bp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bp)
print(json.dumps([[bp.stat_map(r), bp.main_text(r), bp.split_details(r)[0], bp.note_text(r), bp.cost_text(r)]
                  for r in bp.load_rows()], ensure_ascii=False))
`;

// Objecten met gesorteerde sleutels, zodat de volgorde niet meetelt.
const canon = v => JSON.stringify(v, (k, x) => x && typeof x === 'object' && !Array.isArray(x)
  ? Object.fromEntries(Object.entries(x).sort(([a], [b]) => a.localeCompare(b))) : x);

test('the page and tools/build-pages.py read every row the same way', async ({ page }) => {
  await page.goto('index.html');
  const js = await page.evaluate(() => DATA.map((d, i) => {
    const cost = costOf(d, i);
    return [STATS[i], MAIN[i], SUB[i].trim(), NOTE[i].trim(), cost === '—' ? '' : cost];
  }));
  const py = JSON.parse(execFileSync('python3', ['-c', PY], { cwd: ROOT, encoding: 'utf-8', maxBuffer: 64 << 20 }));
  expect(py).toHaveLength(js.length);
  const differ = js.flatMap((row, i) => canon(row) === canon(py[i]) ? [] : [`row ${i}: ${canon(row)} vs ${canon(py[i])}`]);
  expect(differ).toEqual([]);
});

test('the combat stat formulas hold for every piece of equipment', async ({ page }) => {
  await page.goto('index.html');
  const wrong = await page.evaluate(() => DATA.flatMap((d, i) => {
    if (d[1] !== 'Equipment') return [];
    const p = powerOf(STATS[i]);
    return POWER_ORDER.filter(k => k in STATS[i] && Math.abs(p[k] - STATS[i][k]) > 1e-9)
      .map(k => `${d[0]}: ${k} ${STATS[i][k]}, formula ${p[k]}`);
  }));
  expect(wrong).toEqual([]);
});

test('no move is listed a second time without its shop', async ({ page }) => {
  await page.goto('index.html');
  const twice = await page.evaluate(() => {
    const key = d => [d[0], d[1], d[3], d[4], d[5], d[6]].join('|');
    const known = new Set(DATA.filter(d => d[2] !== 'Source unknown').map(key));
    return DATA.filter(d => d[2] === 'Source unknown' && known.has(key(d))).map(d => d[0]);
  });
  expect(twice).toEqual([]);
});

test('the structured data answers the same questions as the page', async ({ page }) => {
  await page.goto('index.html');
  const { visible, data } = await page.evaluate(() => {
    const blocks = [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => JSON.parse(s.textContent));
    return {
      visible: [...document.querySelectorAll('.faq h3')]
        .map(h => [h.textContent.trim(), h.nextElementSibling.textContent.replace(/\s+/g, ' ').trim()]),
      data: blocks.find(b => b['@type'] === 'FAQPage').mainEntity.map(q => [q.name, q.acceptedAnswer.text]),
    };
  });
  expect(data).toEqual(visible);
});

test('the head and the introduction give the current number of items', async ({ page }) => {
  await page.goto('index.html');
  const total = `${await page.evaluate(() => DATA.length.toLocaleString('en-US'))} items`;
  for (const sel of ['meta[name="description"]', 'meta[property="og:description"]', 'meta[name="twitter:description"]']) {
    await expect(page.locator(sel)).toHaveAttribute('content', new RegExp(total));
  }
  await expect(page.locator('.lede')).toContainText(total);
});

// De getallen in de zichtbare FAQ zijn handwerk. Klopt er een niet meer met de
// data, dan zegt deze test welke zin bijgewerkt moet worden.
test('the numbers in the FAQ and the footer match the data', async ({ page }) => {
  await page.goto('index.html');
  const c = await page.evaluate(() => {
    const count = f => DATA.filter(f).length;
    const is = (cat, shop) => d => d[1] === cat && (shop === undefined || d[2] === shop);
    const shops = {};
    DATA.forEach(d => { shops[d[2]] = (shops[d[2]] || 0) + 1; });
    return {
      total: DATA.length,
      special: count(is('Special Move')),
      specialSources: new Set(DATA.filter(is('Special Move')).map(d => d[2])).size,
      specialAt: Object.fromEntries(['Chronicle Department Store', 'VS Store', 'Magic Moves (Odaiba Branch)',
        'Magic Moves (Arcade Branch)', 'Special Training Booth', 'Spirit Market', 'Source unknown',
        'Legendary Chest (not purchasable)', 'Serial code'].map(s => [s, count(is('Special Move', s))])),
      hyper: count(is('Hyper Move')),
      hyperOutsideSpiritMarket: count(d => d[1] === 'Hyper Move' && d[2] !== 'Spirit Market'),
      hyperTypes: Object.fromEntries(['Keshin', 'Totem', 'Awakening'].map(t => [t, count(d => d[1] === 'Hyper Move' && d[5] === t)])),
      hyperPriced: DATA.filter((d, i) => d[1] === 'Hyper Move' && filled(costOf(d, i))).length,
      spiritAll: count(d => d[2] === 'Spirit Market'),
      spirit: Object.fromEntries(['Special Move', 'Bond Object', 'Equipment'].map(k => [k, count(is(k, 'Spirit Market'))])),
      kits: count(d => d[5] === 'Kit' && d[2] === 'Chronicle - Rare Drop Battle'),
      kitsElsewhere: count(d => d[5] === 'Kit' && d[2] !== 'Chronicle - Rare Drop Battle'),
      emblems: count(d => d[5] === 'Emblem'),
      emblemsHero: count(d => d[5] === 'Emblem' && d[2] === 'Chronicle - Hero Battle'),
      emblemsRare: count(d => d[5] === 'Emblem' && d[2] === 'Chronicle - Rare Drop Battle'),
      topShops: Object.entries(shops).sort((a, b) => b[1] - a[1]).slice(0, 4),
      priced: count(d => d[7]),
      equipment: count(is('Equipment')),
      equipmentPriced: count(d => d[1] === 'Equipment' && d[7]),
      faq: document.querySelector('.faq').textContent.replace(/\s+/g, ' '),
      footer: document.querySelector('footer').textContent.replace(/\s+/g, ' '),
    };
  });
  const n = x => x.toLocaleString('en-US');
  const words = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
  const s = c.specialAt;
  const [top1, top2, top3, top4] = c.topShops;

  expect.soft(s['Magic Moves (Arcade Branch)'], 'two shops "with the same number each"').toBe(s['Special Training Booth']);
  expect.soft(c.hyperOutsideSpiritMarket, 'hyper moves "all from the Spirit Market"').toBe(0);
  expect.soft(c.kitsElsewhere, 'kits "all from Rare Drop Battles"').toBe(0);
  expect.soft(top1[0], 'the shop with the most items').toBe('Chronicle Department Store');
  expect.soft(c.faq).toContain(`${n(c.special)} special moves are spread over ${words[c.specialSources]} sources`);
  expect.soft(c.faq).toContain(`The Chronicle Department Store has the most at ${s['Chronicle Department Store']}, `
    + `followed by the VS Store with ${s['VS Store']}, Magic Moves (Odaiba Branch) with ${s['Magic Moves (Odaiba Branch)']}, `
    + `Magic Moves (Arcade Branch) and the Special Training Booth with ${s['Special Training Booth']} each, `
    + `and the Spirit Market with ${s['Spirit Market']}.`);
  expect.soft(c.faq).toContain(`${words[s['Legendary Chest (not purchasable)']].replace(/^./, x => x.toUpperCase())} more come `
    + `from the Legendary Chest and ${words[s['Serial code']]} from a serial code; for ${s['Source unknown']} of the moves`);
  expect.soft(c.faq).toContain(`All ${c.hyper} hyper moves come from one place`);
  expect.soft(c.faq).toContain(`That is ${c.hyperTypes.Keshin} Keshin, ${c.hyperTypes.Totem} Totems, ${c.hyperTypes.Awakening} Awakenings`);
  expect.soft(c.faq).toContain(`which so far is for ${c.hyperPriced} of the ${c.hyper}.`);
  expect.soft(c.faq).toContain(`${c.spiritAll} items: every one of the ${c.hyper} hyper moves, `
    + `${c.spirit['Special Move']} special moves, ${c.spirit['Bond Object']} Bond Town objects, `
    + `${c.spirit.Equipment} pieces of equipment`);
  expect.soft(c.faq).toContain(`All ${c.kits + c.emblems} kits and emblems are battle drops`);
  expect.soft(c.faq).toContain(`The ${c.kits} kits all come from Chronicle Rare Drop Battles. Of the ${c.emblems} emblems, `
    + `${c.emblemsHero} come from Chronicle Hero Battles and the other ${c.emblemsRare} from Rare Drop Battles.`);
  expect.soft(c.faq).toContain(`The Chronicle Department Store, with ${top1[1]} of the ${n(c.total)} items. `
    + `Then the ${top2[0]} with ${top2[1]}, the ${top3[0]} with ${top3[1]} and the ${top4[0]} with ${top4[1]}.`);
  expect.soft(c.faq).toContain(`Yes, for ${n(c.priced)} of the ${n(c.total)} items`);
  expect.soft(c.footer).toContain(`cover ${n(c.priced)} items, among them ${c.equipmentPriced} of the ${c.equipment} pieces of equipment`);
});
