#!/usr/bin/env node
/**
 * generate-slides.js
 * Reads carousel.json files for today → generates AI images via OpenAI gpt-image-1.5.
 * Supports resume: skips already-generated slides.
 *
 * ⚠️  Set exec timeout to 600s+ — 10 slides × ~60s each = up to 10 minutes.
 * ⚠️  Always uses gpt-image-1.5 — never gpt-image-1. Quality difference is massive.
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const CONFIG_PATH = path.join(ROOT, 'config.json');

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.error('❌ No config.json. Run onboarding first.');
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

function today() { return new Date().toISOString().split('T')[0]; }

function getTodayPostDirs(config) {
  const dateStr = today();
  const postsRoot = path.join(ROOT, config.paths.posts, dateStr);
  if (!fs.existsSync(postsRoot)) return [];
  return fs.readdirSync(postsRoot)
    .map(d => path.join(postsRoot, d))
    .filter(d => fs.statSync(d).isDirectory() && fs.existsSync(path.join(d, 'carousel.json')));
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function generateImage(prompt, apiKey) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      model: 'gpt-image-1.5', // NEVER gpt-image-1
      prompt,
      size: '1024x1536',      // Portrait — fills TikTok screen
      quality: 'high',
      n: 1,
      response_format: 'b64_json'
    });

    const req = https.request({
      hostname: 'api.openai.com',
      path: '/v1/images/generations',
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
      }
    }, res => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.error) return reject(new Error(parsed.error.message));
          if (!parsed.data || !parsed.data[0]) return reject(new Error('No image data returned'));
          resolve(parsed.data[0].b64_json);
        } catch (e) {
          reject(new Error(`Failed to parse response: ${e.message}`));
        }
      });
    });

    req.on('error', reject);
    req.setTimeout(120000, () => { req.destroy(); reject(new Error('Request timeout')); });
    req.write(body);
    req.end();
  });
}

async function processPost(postDir, apiKey) {
  const carouselPath = path.join(postDir, 'carousel.json');
  const carousel = JSON.parse(fs.readFileSync(carouselPath, 'utf8'));
  const slidesDir = path.join(postDir, 'slides');
  fs.mkdirSync(slidesDir, { recursive: true });

  console.log(`\n📸 Generating images for: ${path.basename(postDir)}`);
  console.log(`   Structure: ${carousel.structure}`);
  console.log(`   Hook: "${carousel.hookText}"\n`);

  for (const slide of carousel.slides) {
    const rawPath = path.join(slidesDir, `slide-${String(slide.slideNum).padStart(2, '0')}-raw.png`);

    // Resume: skip if already generated
    if (fs.existsSync(rawPath)) {
      console.log(`   ⏭  Slide ${slide.slideNum} — already exists, skipping`);
      continue;
    }

    console.log(`   🎨 Slide ${slide.slideNum}/${carousel.slides.length} — generating...`);
    console.log(`      Prompt: ${slide.imagePrompt.substring(0, 80)}...`);

    try {
      const b64 = await generateImage(slide.imagePrompt, apiKey);
      fs.writeFileSync(rawPath, Buffer.from(b64, 'base64'));
      console.log(`   ✅ Slide ${slide.slideNum} — saved`);
    } catch (err) {
      console.error(`   ❌ Slide ${slide.slideNum} failed: ${err.message}`);
      console.error('      Re-run script to resume from this slide.');
      throw err;
    }

    // Rate limit safety: 1s between requests
    if (slide.slideNum < carousel.slides.length) await sleep(1000);
  }

  console.log(`\n✅ All slides generated for ${path.basename(postDir)}`);
}

async function main() {
  const config = loadConfig();
  const { apiKey } = config.imageGen;

  if (!apiKey || !apiKey.startsWith('sk-')) {
    console.error('❌ Invalid OpenAI API key in config.json');
    process.exit(1);
  }

  const postDirs = getTodayPostDirs(config);
  if (postDirs.length === 0) {
    console.error(`❌ No carousel.json files found for today (${today()}).`);
    console.error('   Run first: node scripts/generate-carousel.js');
    process.exit(1);
  }

  console.log(`\n🖼  Generating images for ${postDirs.length} post(s)...`);
  console.log('⏱  This takes 1–2 minutes per post. Do not interrupt.\n');

  for (const postDir of postDirs) {
    await processPost(postDir, apiKey);
    await sleep(2000); // brief pause between posts
  }

  console.log('\n✅ All image generation complete.');
  console.log('Next: node scripts/add-text-overlay.js');
}

main().catch(err => {
  console.error('\n❌ Image generation failed:', err.message);
  process.exit(1);
});
