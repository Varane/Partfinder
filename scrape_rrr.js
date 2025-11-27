const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
const fs = require("fs");
const path = require("path");
puppeteer.use(StealthPlugin());
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const parsePrice = (text) => {
  if (!text) return null;
  const cleaned = text.replace(/[^0-9.,-]/g, "").replace(/,/g, ".");
  const match = cleaned.match(/-?\d+(?:\.\d+)?/);
  return match ? parseFloat(match[0]) : null;
};
const median = (arr) => {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};
async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let totalHeight = 0;
      const distance = 600;
      const timer = setInterval(() => {
        const scrollHeight = document.body.scrollHeight;
        window.scrollBy(0, distance);
        totalHeight += distance;
        if (totalHeight >= scrollHeight) {
          clearInterval(timer);
          resolve();
        }
      }, 300);
    });
  });
}
async function navigateWithRetry(page, url, retries = 3) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
      return;
    } catch (err) {
      if (attempt === retries) throw err;
      await delay(2000 * attempt);
    }
  }
}
async function extractBrands(page) {
  await navigateWithRetry(page, "https://rrr.lt/en/used-car-parts");
  await page.waitForSelector(".sidebar__brands a", { timeout: 60000 });
  return await page.$$eval(".sidebar__brands a", (links) =>
    links.map((a) => ({ name: a.textContent.trim(), url: a.href }))
  );
}
async function extractModels(page, url) {
  await navigateWithRetry(page, url);
  await page.waitForSelector(".sidebar__models a", { timeout: 60000 });
  return await page.$$eval(".sidebar__models a", (links) =>
    links.map((a) => ({ name: a.textContent.trim(), url: a.href }))
  );
}
async function extractCategories(page, url) {
  await navigateWithRetry(page, url);
  await page.waitForSelector(".sidebar__categories a", { timeout: 60000 });
  return await page.$$eval(".sidebar__categories a", (links) =>
    links.map((a) => ({ name: a.textContent.trim(), url: a.href }))
  );
}
async function collectItems(page, url, brand, model, category) {
  let current = url;
  const allItems = [];
  const seen = new Set();
  while (current) {
    await navigateWithRetry(page, current);
    await page.waitForSelector(".search-result__item", { timeout: 60000 });
    await autoScroll(page);
    await delay(2000);
    const items = await page.evaluate(() => {
      const nodes = document.querySelectorAll(".search-result__item");
      const results = [];
      nodes.forEach((node) => {
        const article = node.querySelector(".search-result__code")?.textContent?.trim() || "";
        const description = node.querySelector(".search-result__title")?.textContent?.trim() || "";
        const priceText = node.querySelector(".search-result__price")?.textContent?.trim() || "";
        const link = node.querySelector("a")?.href || "";
        const img = node.querySelector("img");
        const imageUrl = img ? img.src : "";
        const width = img?.naturalWidth || img?.width || 0;
        const height = img?.naturalHeight || img?.height || 0;
        results.push({ article, description, priceText, imageUrl, url: link, width, height });
      });
      return results;
    });
    items.forEach((it) => {
      const key = `${it.url}::${it.article}`;
      if (seen.has(key)) return;
      seen.add(key);
      const price = parsePrice(it.priceText);
      allItems.push({
        article: it.article,
        description: it.description,
        price,
        image_url: it.imageUrl,
        url: it.url,
        brand,
        model,
        category,
        width: it.width,
        height: it.height,
      });
    });
    const nextUrl = await page.evaluate(() => {
      const next = document.querySelector('a[rel="next"], .pagination__item--next a');
      return next ? next.href : null;
    });
    if (!nextUrl || nextUrl === current) break;
    current = nextUrl;
  }
  return allItems;
}
(async () => {
  const browser = await puppeteer.launch({ headless: false, args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1366, height: 768 });
  const brands = await extractBrands(page);
  const results = [];
  for (const brand of brands) {
    const models = await extractModels(page, brand.url);
    for (const model of models) {
      const categories = await extractCategories(page, model.url);
      for (const category of categories) {
        const items = await collectItems(page, category.url, brand.name, model.name, category.name);
        const prices = items.map((i) => i.price).filter((p) => typeof p === "number" && !Number.isNaN(p));
        const medianPrice = median(prices);
        const averagePrice = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0;
        const sonverPrice = medianPrice * 1.35;
        let cleanestPhoto = "";
        let bestScore = -1;
        for (const it of items) {
          const score = (it.width || 0) * (it.height || 0);
          if (score > bestScore && it.image_url) {
            bestScore = score;
            cleanestPhoto = it.image_url;
          }
        }
        if (!cleanestPhoto && items.length) cleanestPhoto = items[0].image_url || "";
        results.push({
          brand: brand.name,
          model: model.name,
          category: category.name,
          median_price: medianPrice,
          average_price: averagePrice,
          sonver_price: sonverPrice,
          cleanest_photo: cleanestPhoto,
          items: items.map(({ width, height, ...rest }) => rest),
        });
      }
    }
  }
  const outputPath = path.join(__dirname, "rrr_full_export.json");
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
  await browser.close();
})();
