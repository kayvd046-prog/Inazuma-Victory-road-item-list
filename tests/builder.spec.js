// De set-builder: characters, versies, deellinks en de vier uitrustingsslots.
const { test, expect, holdCharacters, query, inList } = require('./fixtures');

const HARPER = 'Harper Evans (Inazuma Eleven: Victory Road)';

test.describe('a shared build link', () => {
  test('keeps the character in the address bar while the characters load', async ({ page }) => {
    const release = await holdCharacters(page);
    await page.goto('index.html?c=Mark%20Evans&v=hero&lv=50');
    await expect(page.locator('#totals')).toContainText('Loading the character from the link');
    expect(query(page)).toBe('c=Mark Evans&v=hero&lv=50');
    release();
    await expect(page.locator('#totals .t-head')).toContainText('Hero');
    expect(query(page)).toBe('c=Mark Evans&v=hero&lv=50');
  });

  test('survives a reload', async ({ page }) => {
    await page.goto('index.html?b=' + encodeURIComponent('Raimon Boots~~~') + '&c=Mark%20Evans&v=hero&lv=50');
    await expect(page.locator('#totals .t-head')).toContainText('Mark Evans');
    await page.reload();
    await expect(page.locator('#totals .t-head')).toHaveText(/Mark Evans.*Hero.*Lv 50.*1 of 4 slots filled/);
    await expect(page.locator('.gearq[data-slot="Boots"]')).toHaveValue('Raimon Boots');
  });

  test('says so when the character is not in the list', async ({ page }) => {
    await page.goto('index.html?c=' + encodeURIComponent('Nobody Real'));
    await expect(page.locator('#chosen')).toHaveText('No character called “Nobody Real” in this list.');
  });
});

test('shows the stats of each version', async ({ page }) => {
  // Mark Evans op level 99: 1.103 als gewone speler, 1.324 als Hero, 1.586 als Fabled.
  for (const [v, total] of [['', '1103'], ['&v=hero', '1324'], ['&v=fabled', '1586']]) {
    await page.goto('index.html?c=Mark%20Evans' + v);
    await expect(page.locator('.t-table tfoot td.sum').first()).toHaveText(total);
  }
});

test.describe('two players with the same name', () => {
  test('a link to the second one opens the second one', async ({ page }) => {
    await page.goto('index.html');
    await page.click('#buildbtn');
    await page.fill('#charq', HARPER);
    await page.locator('#charlist li[data-n]', { hasText: 'Fabled' }).dispatchEvent('mousedown');
    await page.selectOption('#version', 'fabled');
    expect(query(page)).toBe(`c=${HARPER} #2&v=fabled`);
    await page.reload();
    await expect(page.locator('#version')).toHaveValue('fabled');
  });

  test('a bare name still opens the first one', async ({ page }) => {
    await page.goto('index.html?c=' + encodeURIComponent(HARPER));
    await expect(page.locator('#chosen')).toContainText(HARPER);
    await expect(page.locator('#version option[value="fabled"]')).toBeDisabled();
  });
});

test.describe('the character search', () => {
  test('fills in once the characters arrive, when typed into before', async ({ page }) => {
    const release = await holdCharacters(page);
    await page.goto('index.html');
    await page.click('#buildbtn');
    await page.locator('#charq').pressSequentially('mark');
    await expect(page.locator('#charlist')).toContainText('Loading characters');
    release();
    await expect(page.locator('#charlist li[data-n]').first()).toBeVisible();
  });

  test('says when no character matches', async ({ page }) => {
    await page.goto('index.html');
    await page.click('#buildbtn');
    await page.fill('#charq', 'zzzzqqq');
    await expect(page.locator('#charlist')).toHaveText('No character matches');
  });

  test('keeps the highlighted character in view and tells screen readers', async ({ page }) => {
    await page.goto('index.html');
    await page.click('#buildbtn');
    await page.fill('#charq', 'a');
    await expect(page.locator('#charlist li[data-n]')).toHaveCount(25);
    for (let n = 0; n < 15; n++) await page.keyboard.press('ArrowDown');
    await expect(page.locator('#charq')).toHaveAttribute('aria-activedescendant', 'charopt-15');
    expect(await inList(page, '#charopt-15')).toBe(true);
  });

  test.describe('after a failed download', () => {
    test.use({ allowedErrors: [/status of 500/] });

    test('tries again on the next keystroke', async ({ page }) => {
      let fail = true;
      await page.route(/characters\.json/, r => fail ? r.fulfill({ status: 500, body: '' }) : r.continue());
      await page.goto('index.html');
      await page.click('#buildbtn');
      await expect(page.locator('#totals')).toContainText('could not be loaded');
      fail = false;
      await page.fill('#charq', 'mark');
      await expect(page.locator('#charlist li[data-n]').first()).toBeVisible();
    });
  });
});

test.describe('a gear slot', () => {
  test('opens, follows the arrow keys and picks with Enter', async ({ page }) => {
    await page.goto('index.html');
    await page.click('#buildbtn');
    const boots = page.locator('.gearq[data-slot="Boots"]');
    await boots.focus();
    await expect(boots).toHaveAttribute('aria-expanded', 'true');
    for (let n = 0; n < 20; n++) await page.keyboard.press('ArrowDown');
    await expect(boots).toHaveAttribute('aria-activedescendant', 'gear-Boots-20');
    expect(await inList(page, '#gear-Boots-20')).toBe(true);
    await page.keyboard.press('Enter');
    await expect(boots).toHaveAttribute('aria-expanded', 'false');
    await expect(boots).not.toHaveValue('');
    expect(query(page)).toMatch(/^b=[^~]+~~~$/);
  });

  test('says when nothing matches', async ({ page }) => {
    await page.goto('index.html');
    await page.click('#buildbtn');
    await page.fill('.gearq[data-slot="Pendant"]', 'qqqzzz');
    await expect(page.locator('#gearlist-Pendant')).toContainText('Nothing matches');
  });

  test('adds up the stats and the price of the set', async ({ page }) => {
    await page.goto('index.html?b=' + encodeURIComponent('Raimon Boots~~~'));
    await expect(page.locator('#totals .t-head')).toHaveText(/Build total.*1 of 4 slots filled/);
    await expect(page.locator('#totals .t-list')).toContainText('Agility+6');
    await expect(page.locator('#totals .setcost')).toContainText('8× Practice is Like Rice Balls');
  });
});
