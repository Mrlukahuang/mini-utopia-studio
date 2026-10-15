/**
 * A-008 visual evidence for the actual exported Godot 4 Web game.
 * The workflow exports Creator as CI-only main_scene into dist/creator-visual;
 * production Web export remains separate and unchanged. No family credentials.
 * Screenshots require human visual review: a canvas screenshot alone cannot
 * assert that there are no missing CJK glyphs or overlapping Godot Controls.
 */
'use strict';
const {chromium} = require('/tmp/mini-utopia-playwright/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');

async function main() {
  const out = path.resolve('dist/visual-evidence');
  fs.mkdirSync(out, {recursive: true});
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl', '--no-sandbox'],
  });
  try {
    for (const [width, height] of [[1180, 820], [1366, 1024]]) {
      const context = await browser.newContext({
        viewport: {width, height},
        deviceScaleFactor: 1,
        hasTouch: true,
        isMobile: true,
      });
      const page = await context.newPage();
      const pageErrors = [];
      page.on('pageerror', e => pageErrors.push(String(e.message)));
      await page.goto('http://127.0.0.1:8765/', {waitUntil: 'load', timeout: 120000});
      await page.locator('canvas').first().waitFor({state: 'visible', timeout: 120000});
      await page.waitForFunction(() => {
        const canvas = document.querySelector('canvas');
        return canvas && canvas.width > 0 && canvas.height > 0;
      }, {timeout: 120000});
      // Allow a few frames after the Godot engine reports a live canvas.
      await page.waitForTimeout(4500);
      const bounds = await page.locator('canvas').first().boundingBox();
      if (!bounds || bounds.width < width * 0.75 || bounds.height < height * 0.75) {
        throw new Error('Godot canvas does not occupy the iPad viewport: ' + JSON.stringify(bounds));
      }
      const filename = path.join(out, 'creator-' + width + 'x' + height + '.png');
      await page.screenshot({path: filename, fullPage: true});
      if (fs.statSync(filename).size < 12000) {
        throw new Error('Screenshot too small to inspect: ' + filename);
      }
      if (pageErrors.length) {
        throw new Error('Godot browser JavaScript error: ' + pageErrors.join(' | '));
      }
      console.log('Captured real Godot Creator screenshot:', filename);
      await context.close();
    }
  } finally {
    await browser.close();
  }
}
main().catch(e => { console.error(e); process.exitCode = 1; });
