import { open } from './hm_common.mjs';
const { browser, newPage } = await open();
const page = await newPage();
await page.goto('http://127.0.0.1:8765/?c=fixed');
console.log(JSON.stringify(await page.evaluate(() => ({ ua: navigator.userAgent, webdriver: navigator.webdriver, languages: navigator.languages,
  brands: navigator.userAgentData && navigator.userAgentData.brands.map(b => b.brand + '/' + b.version) }))));
await browser.close();
