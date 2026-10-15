// Temporary: render the old Wix gallery in a browser, scroll to the end, record every image in order.
const { chromium } = require('playwright');
const fs = require('fs');
const URL = 'https://www.nanamilatic.com/galerry';
const OUT = process.argv[2] || '_probe';
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'hr-HR' });
  const page = await ctx.newPage();
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(2000);

  const log = [];
  let stable = 0, lastHeight = 0, lastCount = 0;
  for (let i = 0; i < 150 && stable < 6; i++) {
    // click any "load more" style button if the gallery has one
    const more = await page.$('[data-hook="load-more-button"], button:has-text("Load More"), button:has-text("Učitaj"), button:has-text("Prikaži više")');
    if (more) { try { await more.click({ timeout: 2000 }); log.push(`clicked load more at step ${i}`); } catch (e) {} }
    await page.evaluate(() => window.scrollBy(0, 600));
    await page.waitForTimeout(600);
    const [h, count] = await page.evaluate(() => [document.documentElement.scrollHeight, document.querySelectorAll('img').length]);
    if (h === lastHeight && count === lastCount) stable++; else stable = 0;
    lastHeight = h; lastCount = count;
  }
  log.push(`scroll finished: height ${lastHeight}, img elements ${lastCount}`);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1000);

  const data = await page.evaluate(() => {
    const re = /static\.wixstatic\.com\/media\/([^\/"'\s,)]+)/g;
    const seen = new Set(), items = [];
    const all = document.querySelectorAll('*');
    for (const el of all) {
      const hay = [el.getAttribute('src'), el.getAttribute('srcset'), el.getAttribute('data-src'), el.getAttribute('style'), el.getAttribute('data-image-info'), el.getAttribute('href')].filter(Boolean).join(' ');
      if (!hay.includes('wixstatic.com/media/')) continue;
      let m; re.lastIndex = 0;
      const ids = [];
      while ((m = re.exec(hay))) ids.push(m[1]);
      const r = el.getBoundingClientRect();
      for (const id of ids) {
        if (seen.has(id)) continue;
        seen.add(id);
        items.push({ id, tag: el.tagName.toLowerCase(), cls: (el.className && el.className.toString().slice(0, 60)) || '', hook: el.getAttribute('data-hook') || '', top: Math.round(r.top + window.scrollY), left: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height), alt: el.getAttribute('alt') || '' });
      }
    }
    const hooks = {};
    document.querySelectorAll('[data-hook]').forEach((e) => { const k = e.getAttribute('data-hook').replace(/\d+/g, 'N'); hooks[k] = (hooks[k] || 0) + 1; });
    return { items, hooks, title: document.title, url: location.href };
  });
  fs.writeFileSync(`${OUT}/gallery.json`, JSON.stringify(data, null, 1));
  fs.writeFileSync(`${OUT}/gallery-rendered.html`, await page.content());
  await page.screenshot({ path: `${OUT}/gallery-full.jpg`, type: 'jpeg', quality: 50, fullPage: true });
  fs.writeFileSync(`${OUT}/gallery-log.txt`, log.join('\n') + `\nimages found: ${data.items.length}\ntitle: ${data.title}\n`);
  console.log(log.join('\n'), '\nimages found:', data.items.length);
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
