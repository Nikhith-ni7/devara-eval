/* Optional browser verification against a running local server.
   Use a disposable EVAL_DB: this creates demo runs, a prompt version, and a TEST review.
   npm install --no-save --package-lock=false playwright && npx playwright install chromium
   node scripts/browser-smoke.cjs
*/
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({headless:true, executablePath:process.env.BROWSER_EXECUTABLE_PATH || undefined,args:['--no-sandbox']});
  const page = await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1,httpCredentials:process.env.EVAL_TEST_PASSWORD ? {username:'owner',password:process.env.EVAL_TEST_PASSWORD} : undefined});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const base=process.env.EVAL_URL || 'http://127.0.0.1:8000';
  await page.goto(base);
  await page.getByRole('button',{name:'▶ Run demo comparison'}).click();
  await page.getByText('Demo completed. Faults are deliberately injected;', {exact:false}).waitFor({timeout:20000});
  await page.getByText('Comparison complete',{exact:false}).waitFor();
  assert.equal(await page.locator('tbody tr').count(),50);
  await page.screenshot({path:path.join(__dirname,'../docs/dashboard.png'),fullPage:false});
  await page.getByRole('button',{name:'Regressed 5',exact:true}).click();
  assert.equal(await page.locator('tbody tr').count(),5);
  await page.getByRole('button',{name:'Inspect prog-004',exact:true}).click();
  await page.getByRole('dialog').waitFor();
  assert.ok((await page.getByRole('dialog').innerText()).includes('A tuple can change freely.'));
  await page.locator('select[name="correctness"]').selectOption('0');
  await page.locator('select[name="completeness"]').selectOption('0');
  await page.locator('select[name="clarity"]').selectOption('1');
  await page.getByLabel('Reviewer',{exact:true}).fill('Automated UI smoke test — synthetic');
  await page.getByLabel('Evidence / rationale',{exact:true}).fill('TEST RECORD ONLY: validates review persistence; not a human judgment.');
  await page.getByRole('button',{name:'Save human review',exact:true}).click();
  await page.getByText('Review saved to the candidate run.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Close test details',exact:true}).click();
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'↓ Export report',exact:true}).click();
  const downloaded=await download;
  assert.ok(downloaded.suggestedFilename().endsWith('.json'));
  await page.getByRole('button',{name:/Test dataset/}).click();
  assert.equal(await page.locator('details.case-card').count(),50);
  await page.getByRole('button',{name:/Prompt versions/}).click();
  await page.getByLabel('Version ID',{exact:true}).fill('browser-test-'+Date.now());
  await page.getByLabel('Provider',{exact:true}).selectOption('demo');
  await page.getByRole('button',{name:'Save version',exact:true}).click();
  await page.getByText('Immutable version saved.',{exact:false}).waitFor();
  await page.getByRole('button',{name:/Run history/}).click();
  assert.ok(await page.locator('tbody tr').count() >= 2);
  await page.getByRole('button',{name:/Comparisons/}).click();
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(__dirname,'../docs/mobile.png'),fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth > window.innerWidth),false);
  await page.reload();
  await page.getByText('Comparison complete',{exact:false}).waitFor();
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({status:'passed',checks:['Demo launch and 50 results','Five regression rows','Answer detail','Review persistence','JSON download','Dataset view','Immutable prompt creation','Run history','Mobile overflow','Reload persistence','No browser exceptions']},null,2));
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
