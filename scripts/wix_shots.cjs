// Screenshots of the migrated blog (temporary, for visual review)
const { chromium } = require('playwright');
const fs = require('fs');
const BASE = 'http://127.0.0.1:8082/nanafitmama/';
const OUT = process.argv[2] || 'shots';
fs.mkdirSync(OUT, { recursive: true });

const posts = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const pick = ['kad-spustis-gard', 'budi-i-ti-fit-mama', 'pametna-tjelovjezba-u-trudnoci-je-od-velike-vaznosti'];

async function prep(page) {
  await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important}' });
  await page.evaluate(() => {
    document.querySelectorAll('img[loading="lazy"]').forEach((i) => (i.loading = 'eager'));
    document.querySelectorAll('.rv,.rl,.rr').forEach((e) => e.classList.add('up'));
  });
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => Promise.all([...document.images].map((i) => (i.decode ? i.decode().catch(() => {}) : null))));
  await page.waitForTimeout(500);
}

(async () => {
  const browser = await chromium.launch();
  const log = [];
  for (const [vpName, vp] of Object.entries({ desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } })) {
    const ctx = await browser.newContext({ viewport: vp, reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    await page.goto(BASE + 'blog/', { waitUntil: 'networkidle' });
    await prep(page);
    const visible = async () => page.evaluate(() => [...document.querySelectorAll('.post-card')].filter((c) => !c.hidden).length);
    log.push(`${vpName} overview: visible cards at start = ${await visible()}`);
    await page.screenshot({ path: `${OUT}/overview-${vpName}.jpg`, type: 'jpeg', quality: 70 });
    await page.click('#showMore');
    log.push(`${vpName} after "show more": ${await visible()}`);
    await page.click('.filter-chip[data-filter="sport-zdravlje"]');
    await prep(page);
    log.push(`${vpName} filter Sport&Zdravlje: ${await visible()} visible, button hidden = ${await page.evaluate(() => document.getElementById('showMore').hidden)}`);
    await page.screenshot({ path: `${OUT}/overview-filter-${vpName}.jpg`, type: 'jpeg', quality: 70 });
    for (const slug of pick) {
      const r = await page.goto(BASE + 'post/' + slug + '/', { waitUntil: 'networkidle' });
      await prep(page);
      const broken = await page.evaluate(() => [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.src));
      log.push(`${vpName} post ${slug}: status ${r.status()}, broken images ${broken.length}`);
      await page.screenshot({ path: `${OUT}/post-${slug}-${vpName}.jpg`, type: 'jpeg', quality: 70, fullPage: true });
    }
    log.push(`${vpName} js errors: ${errors.length} ${errors.slice(0, 2).join(' | ')}`);
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(`${OUT}/SHOTS.txt`, log.join('\n') + '\n');
  console.log(log.join('\n'));
})().catch((e) => { console.error(e); process.exit(1); });
