// Toegankelijkheid, gemeten met axe-core: de lijst met een open set-builder, en
// elke gegenereerde pagina uit de sitemap.
const fs = require('fs');
const path = require('path');
const { test, expect } = require('./fixtures');

const AXE = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const SITE = 'https://kayvd046-prog.github.io/Inazuma-Victory-road-item-list/';
const PAGES = fs.readFileSync(path.resolve(__dirname, '../sitemap.xml'), 'utf8')
  .match(/<loc>[^<]*<\/loc>/g).map(l => l.slice(5, -6).replace(SITE, '')).filter(Boolean);

async function violations(page) {
  await page.addScriptTag({ content: AXE });
  return page.evaluate(async () => (await axe.run(document, { resultTypes: ['violations'] })).violations
    .map(v => `${v.id} (${v.impact}): ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(', ')}`));
}

test('the list with the set builder open has no violations', async ({ page }) => {
  await page.goto('index.html?c=Mark%20Evans');
  await expect(page.locator('#totals .t-head')).toContainText('Mark Evans');
  // Met een open keuzelijst, inclusief de melding dat er niets past.
  await page.fill('.gearq[data-slot="Boots"]', 'qqqzzz');
  await expect(page.locator('#gearlist-Boots')).toContainText('Nothing matches');
  expect(await violations(page)).toEqual([]);
});

test('the sitemap lists the generated pages', () => {
  expect(PAGES.length).toBeGreaterThan(20);
});

for (const url of PAGES) {
  test(`${url} has no violations`, async ({ page }) => {
    await page.goto(url);
    expect(await violations(page)).toEqual([]);
  });
}
