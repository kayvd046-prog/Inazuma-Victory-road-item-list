// De itemlijst: laden, zoeken, filteren, sorteren en de plakkende kolomkoppen.
const { test, expect, query } = require('./fixtures');

// Bovenkant van de filterbalk en van de kolomkoppen, na ver naar beneden scrollen.
const scrolledPositions = async page => {
  await page.evaluate(() => window.scrollTo({ top: 3000, behavior: 'instant' }));
  return page.evaluate(() => ({
    barBottom: document.querySelector('.controls').getBoundingClientRect().bottom,
    headTop: document.querySelector('thead th').getBoundingClientRect().top,
  }));
};

test('shows every item', async ({ page }) => {
  await page.goto('index.html');
  // De eerste 80 rijen staan er meteen; de rest komt er in stukken van 200 bij,
  // telkens als de browser even niets te doen heeft, maar uiterlijk na 3 seconden.
  // Op een drukke machine duurt dat voor alle rijen dus hooguit zo'n halve minuut.
  await expect.poll(() => page.evaluate(() => document.querySelectorAll('#rows tr').length === DATA.length),
    { timeout: 45_000 }).toBe(true);
  const n = await page.evaluate(() => DATA.length);
  await expect(page.locator('#count')).toHaveText(`${n} of ${n} items`);
});

test('leaves no empty "Show more" button under a short list', async ({ page }) => {
  await page.goto('index.html?q=' + encodeURIComponent('fire tornado'));
  await expect(page.locator('#rows tr').first()).toBeVisible();
  await expect(page.locator('#more')).toBeHidden();
});

test.describe('the column headers', () => {
  for (const width of [1024, 1280, 1600]) {
    test(`stick right under the filter bar at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto('index.html');
      const { barBottom, headTop } = await scrolledPositions(page);
      expect(Math.abs(headTop - barBottom)).toBeLessThanOrEqual(1);
    });
  }
});

test.describe('on a phone', () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test('the filter bar scrolls away with the page', async ({ page }) => {
    await page.goto('index.html');
    expect((await scrolledPositions(page)).barBottom).toBeLessThanOrEqual(0);
  });

  test('nothing sticks out sideways', async ({ page }) => {
    await page.goto('index.html');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  });
});

test.describe('on a phone held sideways', () => {
  test.use({ viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true });

  test('the filter bar scrolls away and the headers stick to the top', async ({ page }) => {
    await page.goto('index.html');
    const { barBottom, headTop } = await scrolledPositions(page);
    expect(barBottom).toBeLessThanOrEqual(0);
    expect(Math.abs(headTop)).toBeLessThanOrEqual(1);
  });
});

test.describe('searching', () => {
  test('finds every word, in any order, and marks each one', async ({ page }) => {
    await page.goto('index.html?q=' + encodeURIComponent('tornado fire'));
    const name = page.locator('#rows a.item', { hasText: /^Fire Tornado$/ }).first();
    await expect(name).toBeVisible();
    expect((await name.locator('mark').allTextContents()).map(m => m.toLowerCase()).sort()).toEqual(['fire', 'tornado']);
  });

  test('for "&" shows ampersands, not "&amp;"', async ({ page }) => {
    await page.goto('index.html?q=' + encodeURIComponent('&'));
    await expect(page.locator('#rows tr').first()).toBeVisible();
    const cells = await page.locator('#rows td').allTextContents();
    expect(cells.filter(t => /&(amp|lt|gt|quot);/.test(t))).toEqual([]);
  });

  test('keeps the colour of an element that matches', async ({ page }) => {
    await page.goto('index.html?q=' + encodeURIComponent('fire tornado'));
    await expect(page.locator('#rows td.note .el mark').first()).toBeVisible();
  });
});

test.describe('the stats', () => {
  test('of a move priced in spirits sit in the Stats column, not in Details', async ({ page }) => {
    await page.goto('index.html?q=' + encodeURIComponent('God Catch'));
    const row = page.locator('#rows tr', { has: page.locator('a.item', { hasText: /^God Catch$/ }) }).first();
    await expect(row.locator('td.cost')).toContainText('Legendary Endo');
    await expect(row.locator('td.stats')).toContainText('Power 100');
    await expect(row.locator('td.note')).not.toContainText('Power');
  });

  for (const [stat, name] of [['Power', 'God Catch'], ['CD', 'Keyman Lockdown']]) {
    test(`filter on ${stat} includes ${name}`, async ({ page }) => {
      await page.goto(`index.html?stat=${stat}&q=${encodeURIComponent(name)}`);
      await expect(page.locator('#rows a.item', { hasText: new RegExp(`^${name}$`) }).first()).toBeVisible();
    });
  }

  test('sort the list on the stat that was picked, highest first', async ({ page }) => {
    await page.goto('index.html?cat=Equipment&stat=Kick&sort=-stat:Kick');
    await expect(page.locator('#rows tr').first()).toBeVisible();
    // Meestal "Kick +22.0", bij vier route-items de afgekorte vorm "25 Kick / 25 Control".
    const kicks = (await page.locator('#rows td.stats').allTextContents()).slice(0, 40).map(t => {
      const m = t.match(/Kick \+?(-?[\d.]+)|(-?[\d.]+) Kick\b/);
      return parseFloat(m[1] || m[2]);
    });
    expect(kicks).toEqual([...kicks].sort((a, b) => b - a));
  });
});

test('clicking an item name narrows the list to that item', async ({ page }) => {
  await page.goto('index.html?cat=Equipment&shop=VS%20Store');
  const first = page.locator('#rows a.item').first();
  const name = await first.textContent();
  await first.click();
  // Het is een zoekopdracht op de naam: langere namen die hem bevatten blijven staan.
  expect(query(page)).toBe(`q=${name}`);
  await expect(page.locator('#rows').getByRole('link', { name, exact: true }).first()).toBeVisible();
  const names = await page.locator('#rows a.item').allTextContents();
  expect(names.filter(x => !x.toLowerCase().includes(name.toLowerCase()))).toEqual([]);
});

test('Clear resets every filter', async ({ page }) => {
  await page.goto('index.html?q=boots&shop=VS%20Store&stat=Kick&cat=Equipment&sort=-stat:Kick');
  await page.click('#reset');
  expect(query(page)).toBe('');
  const n = await page.evaluate(() => DATA.length);
  await expect(page.locator('#count')).toHaveText(`${n} of ${n} items`);
});
