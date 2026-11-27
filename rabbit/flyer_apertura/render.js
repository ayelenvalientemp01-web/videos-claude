// Renderiza flyer.html a PNG: node render.js
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const base = 'file://' + path.join(__dirname, 'flyer.html');
  for (const [q, w, h, out] of [['', 1080, 1350, 'rabbit_apertura_feed.png'], ['?f=story', 1080, 1920, 'rabbit_apertura_story.png']]) {
    const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
    await p.goto(base + q);
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(300);
    await p.locator('#f').screenshot({ path: path.join(__dirname, 'entrega', out) });
    await p.close();
  }
  await b.close();
})();
