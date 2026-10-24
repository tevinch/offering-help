import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from 'playwright';
import { createExampleServer } from '../server.mjs';

const output = process.env.RESULT_DIR || 'test-results';
await mkdir(output, { recursive: true });
const { server, records } = createExampleServer();
await new Promise(done => server.listen(0, '127.0.0.1', done));
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'], viewport: { width: 1100, height: 850 } });
const page = await context.newPage();
const errors = [], consoleMessages = [], checkpoints = [], outbound = [];
page.on('pageerror', error => errors.push(String(error)));
page.on('console', message => consoleMessages.push({type:message.type(),text:message.text()}));
page.on('request', request => { if(request.method()==='POST') outbound.push({url:request.url(),body:request.postData()}); });
const input = page.getByLabel('Integer digits');
const group = digits => digits.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
async function snapshot() {
  return page.evaluate(() => ({ value: document.querySelector('#digits').value, raw: document.querySelector('#raw').textContent,
    model: document.querySelector('#masked').textContent, hooks: Number(document.querySelector('#hooks').textContent),
    pastes: Number(document.querySelector('#pastes').textContent), valid: document.querySelector('#digits').checkValidity(),
    receipt: document.querySelector('#receipt').textContent }));
}
async function exact(raw, label) {
  try {
    await page.waitForFunction(({raw,masked}) => document.querySelector('#digits').value===masked && document.querySelector('#raw').textContent===raw && document.querySelector('#masked').textContent===masked,
      {raw,masked:group(raw)}, {timeout:3000});
  } catch (error) { throw new Error(`${label}: expected raw=${raw}, masked=${group(raw)}; observed ${JSON.stringify(await snapshot())}`, {cause:error}); }
  checkpoints.push({label,expected:raw,...await snapshot()});
}
async function paste(text) {
  const before = Number(await page.locator('#pastes').textContent());
  await page.evaluate(text => navigator.clipboard.writeText(text), text);
  await input.press(process.platform==='darwin'?'Meta+V':'Control+V');
  await page.waitForFunction(n=>Number(document.querySelector('#pastes').textContent)>n,before,{timeout:3000});
}
async function submit(raw) {
  const before=records.length;
  const reply=page.waitForResponse(response=>response.url().endsWith('/check') && response.request().method()==='POST');
  await page.getByRole('button',{name:'Submit string'}).click();
  await reply;
  assert.equal(records.length,before+1,'real server received this submission');
  assert.equal(typeof records.at(-1).payload.value,'string','JSON value is quoted string');
  assert.equal(records.at(-1).payload.value,raw,'server received exact raw digits');
  assert.equal(records.at(-1).status,200);
  const sent=JSON.parse(outbound.at(-1).body);
  assert.equal(sent.value,raw,'independent browser request observer agrees');
  assert.equal(typeof sent.value,'string');
  await page.waitForFunction(raw=>document.querySelector('#receipt').textContent===raw,raw,{timeout:3000});
}
let result='FAIL',failure;
try {
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await input.waitFor();
  assert.equal(await input.getAttribute('type'),'text');
  assert.equal(await input.getAttribute('inputmode'),'numeric');
  await page.getByRole('button',{name:'Submit string'}).click();
  assert.equal(records.length,0,'required empty input sends nothing');
  assert.equal(await input.evaluate(e=>e.validity.valueMissing),true);
  const original='12345678901234567890';
  for(let index=0;index<original.length;index++) {
    await input.pressSequentially(original[index]);
    await exact(original.slice(0,index+1),`original keystroke ${index+1}`);
  }
  assert.ok((await snapshot()).hooks>=20,'mask callbacks really ran');
  await submit(original);
  const long=original+'1234567890';
  await input.pressSequentially('1234567890');
  await exact(long,'continued 30-digit input is not truncated');
  await input.press('Home'); await input.press('ArrowRight'); await input.press('ArrowRight');
  await input.pressSequentially('9');
  await exact(long.slice(0,2)+'9'+long.slice(2),'insert digit in the middle');
  assert.equal(await input.evaluate(e=>e.value.slice(0,e.selectionStart).replaceAll(',','')),'129','caret remains after inserted digit');
  await input.press('Backspace');
  await exact(long,'Backspace removes the inserted digit');
  await input.press('Home'); await input.press('ArrowRight'); await input.press('ArrowRight');
  await input.press('Delete');
  await exact(long.slice(0,2)+long.slice(3),'Delete removes next digit');
  await input.press('ControlOrMeta+A'); await input.press('Backspace'); await exact('','clear');
  assert.equal(await input.evaluate(e=>e.checkValidity()),false,'required still enforced after clear');
  await paste(original); await exact(original,'real clipboard paste plain digits');
  await input.press('ControlOrMeta+A'); await paste(group(original)); await exact(original,'real clipboard paste grouped digits');
  await input.press('End'); await input.press('Backspace'); await exact(original.slice(0,-1),'Backspace after paste');
  await input.press('ControlOrMeta+A'); await input.pressSequentially('00012345678901234567890');
  await exact('00012345678901234567890','leading zeros remain string data');
  await input.press('ControlOrMeta+A'); await input.pressSequentially('98765432109876543210');
  await exact('98765432109876543210','selection replacement and second entry');
  await submit('98765432109876543210');
  await input.press('End');
  const validValue=await input.inputValue();
  await input.pressSequentially('-');
  assert.equal(await input.inputValue(),validValue,'beforeinput rejects sign without rewriting digits');
  assert.equal(await input.evaluate(e=>e.checkValidity()),false,'rejected sign blocks submission');
  await page.getByRole('button',{name:'Submit string'}).click(); assert.equal(records.length,2);
  await input.press('Backspace'); await exact('9876543210987654321','valid edit clears custom error');
  await input.pressSequentially('0'); await exact('98765432109876543210','continue after rejected sign');
  await paste('12.34');
  assert.equal(await input.inputValue(),validValue,'paste rejects decimal instead of stripping dot');
  assert.equal(await input.evaluate(e=>e.checkValidity()),false);
  await page.getByRole('button',{name:'Submit string'}).click(); assert.equal(records.length,2);
  await input.press('ControlOrMeta+A'); await input.press('Backspace'); await exact('','clear rejected paste state');
  await input.pressSequentially(original); await exact(original,'re-enter original after rejection');
  await submit(original);
  assert.deepEqual(errors,[],'no browser exceptions');
  await page.screenshot({path:resolve(output,'final.png'),fullPage:true});
  result='PASS';
} catch(error) { failure=String(error.stack||error); }
finally {
  const state=await snapshot().catch(()=>null);
  await writeFile(resolve(output,'dom.html'),await page.content());
  await writeFile(resolve(output,'result.json'),JSON.stringify({result,failure,browser:browser.version(),versions:JSON.parse(await readFile('package.json')).dependencies,checkpoints,state,records,outbound,errors,consoleMessages},null,2));
  await browser.close(); await new Promise(done=>server.close(done));
}
console.log(JSON.stringify({result,failure,checkpoints:checkpoints.length,requests:records.length,output},null,2));
if(result!=='PASS')process.exitCode=1;
