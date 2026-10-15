// Temporary check: compares the existing pages (main branch) with the Jekyll build,
// and takes screenshots of the new blog pages.
const { chromium } = require('playwright');
const { PNG } = require('pngjs');
const pixelmatch = require('pixelmatch');
const fs = require('fs');

const OLD = 'http://127.0.0.1:8081/nanafitmama/';
const NEW = 'http://127.0.0.1:8082/nanafitmama/';
const OUT = process.argv[2] || 'out';
fs.mkdirSync(OUT, { recursive: true });

const existing = ['index.html', 'o-meni.html', 'galerija.html', 'program.html'];
const blogPages = [['blog', 'blog/'], ['post', 'post/primjer-clanka/']];
const viewports = { desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } };

async function shoot(browser, url, vp) {
  const ctx = await browser.newContext({ viewport: vp, reducedMotion: 'reduce' });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  const resp = await page.goto(url, { waitUntil: 'networkidle' });
  const status = resp ? resp.status() : 0;
  await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important}' });
  await page.evaluate(() => {
    document.querySelectorAll('img[loading="lazy"]').forEach((i) => (i.loading = 'eager'));
    document.querySelectorAll('.rv,.rl,.rr').forEach((e) => e.classList.add('up'));
  });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => Promise.all([...document.images].map((i) => (i.decode ? i.decode().catch(() => {}) : null))));
  await page.waitForTimeout(800);
  const buf = await page.screenshot({ fullPage: true });
  const broken = await page.evaluate(() =>
    [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute('src'))
  );
  await ctx.close();
  return { buf, status, errors, broken };
}

(async () => {
  const browser = await chromium.launch();
  const lines = [];
  for (const [vpName, vp] of Object.entries(viewports)) {
    for (const p of existing) {
      const a = await shoot(browser, OLD + p, vp);
      const b = await shoot(browser, NEW + p, vp);
      const A = PNG.sync.read(a.buf);
      const B = PNG.sync.read(b.buf);
      let msg;
      if (A.width !== B.width || A.height !== B.height) {
        msg = `SIZE DIFFERS old ${A.width}x${A.height} new ${B.width}x${B.height}`;
        fs.writeFileSync(`${OUT}/${p}-${vpName}-new.png`, b.buf);
      } else {
        const diff = new PNG({ width: A.width, height: A.height });
        const n = pixelmatch(A.data, B.data, diff.data, A.width, A.height, { threshold: 0.1 });
        const pct = ((n / (A.width * A.height)) * 100).toFixed(4);
        msg = `${n} px differ (${pct}%)  size ${A.width}x${A.height}`;
        if (n > 0) {
          fs.writeFileSync(`${OUT}/${p}-${vpName}-diff.png`, PNG.sync.write(diff));
          fs.writeFileSync(`${OUT}/${p}-${vpName}-new.png`, b.buf);
        }
      }
      lines.push(`[compare] ${vpName.padEnd(7)} ${p.padEnd(13)} ${msg} | status ${a.status}/${b.status} | broken imgs old ${a.broken.length} ${a.broken.slice(0, 2).join(",")} new ${b.broken.length} ${b.broken.slice(0, 3).join(',')} | js errors new ${b.errors.length}`);
    }
    for (const [name, path] of blogPages) {
      const b = await shoot(browser, NEW + path, vp);
      fs.writeFileSync(`${OUT}/${name}-${vpName}.png`, b.buf);
      lines.push(`[blog]    ${vpName.padEnd(7)} ${path.padEnd(22)} status ${b.status} | broken imgs ${b.broken.length} ${b.broken.slice(0, 3).join(',')} | js errors ${b.errors.length} ${b.errors.slice(0, 2).join(' ')}`);
    }
  }
  await browser.close();
  fs.writeFileSync(`${OUT}/RESULT.txt`, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
})().catch((e) => { console.error(e); process.exit(1); });
