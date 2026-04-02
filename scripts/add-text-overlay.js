#!/usr/bin/env node
/**
 * add-text-overlay.js
 * Renders overlay text onto slide images using node-canvas.
 * Uses Larry's exact formula — proven at 1M+ TikTok views.
 *
 * Install canvas first:
 *   macOS: brew install pkg-config cairo pango libpng jpeg giflib librsvg && npm install canvas
 *   Ubuntu: sudo apt-get install build-essential libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev && npm install canvas
 *   Windows: npm install canvas (auto-downloads prebuilt)
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const CONFIG_PATH = path.join(ROOT, 'config.json');

// Check canvas is installed
let createCanvas, loadImage;
try {
  ({ createCanvas, loadImage } = require('canvas'));
} catch {
  console.error('❌ node-canvas not installed. Run:');
  console.error('   macOS: brew install pkg-config cairo pango libpng jpeg giflib librsvg && npm install canvas');
  console.error('   Ubuntu: sudo apt-get install build-essential libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev librsvg2-dev && npm install canvas');
  console.error('   Windows: npm install canvas');
  process.exit(1);
}

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.error('❌ No config.json found.');
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

/**
 * Add text overlay to a single image.
 * Larry's exact formula — do not change these values without A/B testing.
 */
async function addOverlay(imagePath, text, outputPath) {
  const img = await loadImage(imagePath);
  const canvas = createCanvas(img.width, img.height);
  const ctx = canvas.getContext('2d');

  // Draw base image
  ctx.drawImage(img, 0, 0);

  // ── FONT SIZE: scales dynamically with word count ──
  const wordCount = text.split(/\s+/).filter(Boolean).length;
  let fontSizePercent;
  if (wordCount <= 5)        fontSizePercent = 0.075;  // short → 75px on 1024w
  else if (wordCount <= 12)  fontSizePercent = 0.065;  // medium → 66px
  else                       fontSizePercent = 0.050;  // long → 51px

  const fontSize = Math.round(img.width * fontSizePercent);
  const outlineWidth = Math.round(fontSize * 0.15);   // thick outline = readable on any bg
  const maxWidth = img.width * 0.75;                  // text wraps at 75% width
  const lineHeight = fontSize * 1.3;

  ctx.font = `bold ${fontSize}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';

  // ── WORD WRAP ──
  // Respect manual \n breaks, then auto-wrap long lines
  const lines = [];
  const manualLines = text.split('\n');
  for (const ml of manualLines) {
    const words = ml.trim().split(/\s+/);
    let current = '';
    for (const word of words) {
      const test = current ? `${current} ${word}` : word;
      if (ctx.measureText(test).width <= maxWidth) {
        current = test;
      } else {
        if (current) lines.push(current);
        current = word;
      }
    }
    if (current) lines.push(current);
  }

  // ── POSITION: text block centered at 28% from top ──
  // This is the TikTok safe zone — above the comment area, below the status bar
  const totalTextHeight = lines.length * lineHeight;
  const startY = (img.height * 0.28) - (totalTextHeight / 2);
  const x = img.width / 2;

  // ── DRAW EACH LINE ──
  for (let i = 0; i < lines.length; i++) {
    const y = startY + (i * lineHeight);

    // 1. Black outline (drawn first, underneath)
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = outlineWidth;
    ctx.lineJoin = 'round';
    ctx.miterLimit = 2;
    ctx.strokeText(lines[i], x, y);

    // 2. White fill (drawn on top)
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText(lines[i], x, y);
  }

  // Save final image
  fs.writeFileSync(outputPath, canvas.toBuffer('image/png'));
}

async function processPost(postDir) {
  const carouselPath = path.join(postDir, 'carousel.json');
  const carousel = JSON.parse(fs.readFileSync(carouselPath, 'utf8'));
  const slidesDir = path.join(postDir, 'slides');

  console.log(`\n✍️  Adding overlays for: ${path.basename(postDir)}`);

  for (const slide of carousel.slides) {
    const num = String(slide.slideNum).padStart(2, '0');
    const rawPath = path.join(slidesDir, `slide-${num}-raw.png`);
    const finalPath = path.join(slidesDir, `slide-${num}-final.png`);

    if (!fs.existsSync(rawPath)) {
      console.warn(`   ⚠️  Slide ${slide.slideNum} raw image not found — run generate-slides.js first`);
      continue;
    }

    // Resume: skip if already overlaid
    if (fs.existsSync(finalPath)) {
      console.log(`   ⏭  Slide ${slide.slideNum} — already done`);
      continue;
    }

    // Skip overlay on slides with no text (shouldn't happen but safety check)
    const text = slide.overlayText || '';
    if (!text.trim()) {
      fs.copyFileSync(rawPath, finalPath);
      console.log(`   ⏭  Slide ${slide.slideNum} — no text, copied raw`);
      continue;
    }

    try {
      await addOverlay(rawPath, text, finalPath);
      console.log(`   ✅ Slide ${slide.slideNum} — "${text.replace(/\n/g, ' ').substring(0, 40)}..."`);
    } catch (err) {
      console.error(`   ❌ Slide ${slide.slideNum} failed: ${err.message}`);
      throw err;
    }
  }

  console.log(`✅ Overlays complete for ${path.basename(postDir)}`);
}

async function main() {
  const config = loadConfig();
  const postDirs = getTodayPostDirs(config);

  if (postDirs.length === 0) {
    console.error(`❌ No post directories for today (${today()}).`);
    console.error('   Run: node scripts/generate-slides.js first.');
    process.exit(1);
  }

  console.log(`\n✍️  Processing ${postDirs.length} post(s)...`);

  for (const postDir of postDirs) {
    await processPost(postDir);
  }

  console.log('\n✅ All text overlays applied.');
  console.log('Next: node scripts/post-to-platforms.js');
}

main().catch(err => {
  console.error('\n❌ Text overlay failed:', err.message);
  process.exit(1);
});
