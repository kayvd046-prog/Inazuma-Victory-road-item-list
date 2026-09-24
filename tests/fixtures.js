// Gedeelde opzet voor alle tests.
//
// * Geen webfonts: die doen er voor wat hier getest wordt niet toe, en zo is
//   er geen netwerk nodig.
// * Elke JavaScript-fout op de pagina laat de test falen, ook als de test zelf
//   ergens anders naar kijkt. Een test die een fout verwacht, zet die in
//   allowedErrors.
const base = require('@playwright/test');

const FONTS = /fonts\.(googleapis|gstatic)\.com/;

exports.test = base.test.extend({
  allowedErrors: [[], { option: true }],
  page: async ({ page, allowedErrors }, use) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => {
      if (m.type() !== 'error' || FONTS.test(m.location().url)) return;
      if (!allowedErrors.some(re => re.test(m.text()))) errors.push(m.text());
    });
    await page.route(FONTS, r => r.abort());
    await use(page);
    base.expect(errors, 'JavaScript errors on the page').toEqual([]);
  },
});

exports.expect = base.expect;

// Houdt characters.json vast tot de test hem loslaat, zoals een trage verbinding.
// Een vaste vertraging zou de toestand ertussen alleen soms laten zien: onder
// belasting is het laden dan al voorbij voordat de test kijkt.
exports.holdCharacters = async page => {
  let release;
  const released = new Promise(res => { release = res; });
  await page.route(/characters\.json/, async r => { await released; await r.continue(); });
  return release;
};

// De querystring van de huidige URL, leesbaar: "c=Mark Evans&v=hero".
exports.query = page => decodeURIComponent(new URL(page.url()).search.slice(1).replace(/\+/g, ' '));

// Of een optie binnen het zichtbare deel van zijn keuzelijst valt.
exports.inList = (page, selector) => page.evaluate(sel => {
  const li = document.querySelector(sel);
  if (!li) return false;
  const box = li.parentElement.getBoundingClientRect(), r = li.getBoundingClientRect();
  return r.top >= box.top - 1 && r.bottom <= box.bottom + 1;
}, selector);
