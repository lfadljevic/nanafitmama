const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const out = process.argv[2]; fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
  await p.goto('https://www.nanamilatic.com/o-meni', { waitUntil: 'networkidle', timeout: 90000 });
  let last = 0;
  for (let i = 0; i < 40; i++) {
    await p.mouse.wheel(0, 900); await p.waitForTimeout(500);
    const h = await p.evaluate(() => document.documentElement.scrollHeight);
    if (i > 8 && h === last) break; last = h;
  }
  await p.waitForTimeout(1500);
  const data = await p.evaluate(() => {
    const r = e => { const b = e.getBoundingClientRect(); return { top: Math.round(b.top + scrollY), left: Math.round(b.left), w: Math.round(b.width), h: Math.round(b.height) }; };
    const imgs = [...document.querySelectorAll('img, source, [style*="wixstatic"]')].map(e => ({ tag: e.tagName, src: e.currentSrc || e.src || e.srcset || e.getAttribute('style') || '', alt: e.alt || '', ...r(e) }));
    const links = [...document.querySelectorAll('a')].map(e => ({ href: e.href, text: (e.innerText || '').trim().slice(0, 200), ...r(e) }));
    const texts = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,p,span')].map(e => ({ t: e.tagName, text: (e.innerText || '').trim().slice(0, 200), ...r(e) })).filter(x => x.text);
    return { imgs, links, texts, height: document.documentElement.scrollHeight };
  });
  fs.writeFileSync(out + '/media.json', JSON.stringify(data, null, 1));
  fs.writeFileSync(out + '/media-rendered.html', await p.content());
  await p.screenshot({ path: out + '/media-full.jpg', fullPage: true, type: 'jpeg', quality: 70 });
  await b.close();
})();
