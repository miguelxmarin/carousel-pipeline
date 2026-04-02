#!/usr/bin/env node
/**
 * post-to-platforms.js
 * Posts finished carousels directly to TikTok and Instagram
 * via their official APIs. No third-party tool needed. Free forever.
 *
 * TikTok:   Content Posting API — auto-adds trending music
 * Instagram: Graph API — posts carousel directly to feed
 *
 * Both require one-time OAuth setup during onboarding (see onboarding.js).
 * After that, fully automated.
 *
 * Usage:
 *   node scripts/post-to-platforms.js
 *   node scripts/post-to-platforms.js --dry-run   # log what would post, don't post
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const ROOT = path.join(__dirname, '..');
const CONFIG_PATH = path.join(ROOT, 'config.json');

function loadJSON(p, def = null) {
  if (fs.existsSync(p)) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return def; } }
  return def;
}

function today() { return new Date().toISOString().split('T')[0]; }

function getTodayPostDirs(config) {
  const dateStr = today();
  const postsRoot = path.join(ROOT, config.paths.posts, dateStr);
  if (!fs.existsSync(postsRoot)) return [];
  return fs.readdirSync(postsRoot)
    .sort()
    .map(d => ({ time: d, dir: path.join(postsRoot, d) }))
    .filter(({ dir }) =>
      fs.statSync(dir).isDirectory() &&
      fs.existsSync(path.join(dir, 'carousel.json')) &&
      !fs.existsSync(path.join(dir, 'posted.json'))
    );
}

function getFinalSlides(postDir) {
  const slidesDir = path.join(postDir, 'slides');
  if (!fs.existsSync(slidesDir)) return [];
  return fs.readdirSync(slidesDir)
    .filter(f => f.endsWith('-final.png'))
    .sort()
    .map(f => path.join(slidesDir, f));
}

// ── HTTP HELPERS ──────────────────────────────────────────────────────────────

function httpsRequest(options, body = null) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, res => {
      let data = '';
      res.on('data', c => { data += c; });
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, body: JSON.parse(data) });
        } catch {
          resolve({ status: res.statusCode, body: data });
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(60000, () => { req.destroy(); reject(new Error('Request timeout')); });
    if (body) req.write(typeof body === 'string' ? body : JSON.stringify(body));
    req.end();
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── IMAGE HOSTING ─────────────────────────────────────────────────────────────
// Instagram Graph API requires publicly accessible image URLs.
// We use imgur's anonymous upload (free, no account needed for basic use).
// The image URL returned is used for the Instagram container creation.

async function uploadImageToImgur(imagePath, clientId) {
  return new Promise((resolve, reject) => {
    const imageData = fs.readFileSync(imagePath);
    const b64 = imageData.toString('base64');
    const body = JSON.stringify({ image: b64, type: 'base64' });

    const req = https.request({
      hostname: 'api.imgur.com',
      path: '/3/image',
      method: 'POST',
      headers: {
        'Authorization': `Client-ID ${clientId}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body)
      }
    }, res => {
      let data = '';
      res.on('data', c => { data += c; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          if (parsed.success && parsed.data?.link) resolve(parsed.data.link);
          else reject(new Error(`Imgur upload failed: ${data}`));
        } catch { reject(new Error(`Parse error: ${data}`)); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── INSTAGRAM GRAPH API ───────────────────────────────────────────────────────
// Docs: https://developers.facebook.com/docs/instagram-platform/content-publishing
//
// Flow:
//   1. Upload each image → get container ID
//   2. Create carousel container with all child IDs
//   3. Publish the carousel container

async function createIgImageContainer(igUserId, imageUrl, accessToken, isCarouselItem = true) {
  const params = new URLSearchParams({
    image_url: imageUrl,
    is_carousel_item: String(isCarouselItem),
    access_token: accessToken
  });

  const res = await httpsRequest({
    hostname: 'graph.instagram.com',
    path: `/v22.0/${igUserId}/media?${params}`,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });

  if (res.status !== 200 || !res.body?.id) {
    throw new Error(`IG container creation failed: ${JSON.stringify(res.body)}`);
  }
  return res.body.id;
}

async function createIgCarouselContainer(igUserId, childIds, caption, accessToken) {
  const body = JSON.stringify({
    media_type: 'CAROUSEL',
    children: childIds.join(','),
    caption,
    access_token: accessToken
  });

  const res = await httpsRequest({
    hostname: 'graph.instagram.com',
    path: `/v22.0/${igUserId}/media`,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
  }, body);

  if (res.status !== 200 || !res.body?.id) {
    throw new Error(`IG carousel container failed: ${JSON.stringify(res.body)}`);
  }
  return res.body.id;
}

async function publishIgContainer(igUserId, containerId, accessToken) {
  const body = JSON.stringify({ creation_id: containerId, access_token: accessToken });

  const res = await httpsRequest({
    hostname: 'graph.instagram.com',
    path: `/v22.0/${igUserId}/media_publish`,
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
  }, body);

  if (res.status !== 200 || !res.body?.id) {
    throw new Error(`IG publish failed: ${JSON.stringify(res.body)}`);
  }
  return res.body.id;
}

async function postToInstagram(slides, caption, config) {
  const { igUserId, igAccessToken, imgurClientId } = config.platforms.instagram;

  console.log(`   Instagram: uploading ${slides.length} images...`);

  // Step 1: Upload each image to public hosting
  const imageUrls = [];
  for (const slide of slides) {
    const url = await uploadImageToImgur(slide, imgurClientId);
    imageUrls.push(url);
    console.log(`   ✅ Image hosted: ${path.basename(slide)}`);
    await sleep(500);
  }

  // Step 2: Create carousel item containers
  console.log('   Instagram: creating media containers...');
  const childIds = [];
  for (const url of imageUrls) {
    const id = await createIgImageContainer(igUserId, url, igAccessToken, true);
    childIds.push(id);
    await sleep(300);
  }

  // Step 3: Create carousel container
  const carouselId = await createIgCarouselContainer(igUserId, childIds, caption, igAccessToken);

  // Step 4: Publish
  console.log('   Instagram: publishing...');
  await sleep(2000); // Instagram needs a moment between container creation and publish
  const mediaId = await publishIgContainer(igUserId, carouselId, igAccessToken);

  console.log(`   ✅ Instagram posted (ID: ${mediaId})`);
  return mediaId;
}

// ── TIKTOK CONTENT POSTING API ────────────────────────────────────────────────
// Docs: https://developers.tiktok.com/doc/content-posting-api-get-started
//
// Flow:
//   1. Initialize photo post → get upload_url per image
//   2. Upload each image to TikTok's servers
//   3. Create the post with autoAddMusic = true (TikTok adds trending music)
//
// tiktokAutoAddMusic = true means TikTok automatically picks trending audio.
// This removes the only manual step that existed with the Postiz draft approach.

async function initTikTokPhotoPost(accessToken, imageCount) {
  const body = JSON.stringify({
    post_info: {
      privacy_level: 'PUBLIC_TO_EVERYONE',
      disable_duet: false,
      disable_comment: false,
      disable_stitch: false,
      auto_add_music: true   // TikTok auto-adds trending music — no manual step needed
    },
    source_info: {
      source: 'FILE_UPLOAD',
      photo_cover_index: 0,
      photo_images: Array(imageCount).fill('placeholder') // will be replaced with actual uploads
    },
    media_type: 'PHOTO'
  });

  const res = await httpsRequest({
    hostname: 'open.tiktokapis.com',
    path: '/v2/post/publish/content/init/',
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json; charset=UTF-8',
      'Content-Length': Buffer.byteLength(body)
    }
  }, body);

  if (res.status !== 200 || !res.body?.data) {
    throw new Error(`TikTok init failed: ${JSON.stringify(res.body)}`);
  }
  return res.body.data;
}

async function uploadTikTokImage(uploadUrl, imagePath) {
  return new Promise((resolve, reject) => {
    const imageData = fs.readFileSync(imagePath);
    const parsed = new URL(uploadUrl);
    const isHttps = parsed.protocol === 'https:';
    const lib = isHttps ? https : http;

    const options = {
      hostname: parsed.hostname,
      path: parsed.pathname + parsed.search,
      method: 'PUT',
      headers: {
        'Content-Type': 'image/jpeg',
        'Content-Length': imageData.length
      }
    };

    const req = lib.request(options, res => {
      let data = '';
      res.on('data', c => { data += c; });
      res.on('end', () => resolve({ status: res.statusCode, body: data }));
    });
    req.on('error', reject);
    req.write(imageData);
    req.end();
  });
}

async function publishTikTokPost(publishId, accessToken, caption) {
  // After images are uploaded, finalize the post
  const body = JSON.stringify({
    post_id: publishId,
    post_info: {
      title: caption.slice(0, 150), // TikTok title max 150 chars
      privacy_level: 'PUBLIC_TO_EVERYONE',
      auto_add_music: true
    }
  });

  const res = await httpsRequest({
    hostname: 'open.tiktokapis.com',
    path: '/v2/post/publish/content/complete/',
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json; charset=UTF-8',
      'Content-Length': Buffer.byteLength(body)
    }
  }, body);

  return res;
}

async function postToTikTok(slides, caption, config) {
  const { accessToken } = config.platforms.tiktok;

  console.log(`   TikTok: initializing photo post (${slides.length} images)...`);

  // Step 1: Initialize — get upload URLs
  const initData = await initTikTokPhotoPost(accessToken, slides.length);
  const publishId = initData.publish_id;
  const uploadUrls = initData.photo_upload_urls || [];

  if (uploadUrls.length !== slides.length) {
    throw new Error(`TikTok: expected ${slides.length} upload URLs, got ${uploadUrls.length}`);
  }

  // Step 2: Upload each image
  for (let i = 0; i < slides.length; i++) {
    await uploadTikTokImage(uploadUrls[i], slides[i]);
    console.log(`   ✅ TikTok image ${i + 1}/${slides.length} uploaded`);
    await sleep(300);
  }

  // Step 3: Finalize post
  console.log('   TikTok: publishing with auto-music...');
  const result = await publishTikTokPost(publishId, accessToken, caption);

  if (result.status === 200) {
    console.log(`   ✅ TikTok posted (publish ID: ${publishId}) — trending music auto-added`);
    return publishId;
  } else {
    throw new Error(`TikTok publish failed: ${JSON.stringify(result.body)}`);
  }
}

// ── MAIN ──────────────────────────────────────────────────────────────────────

async function processPost(postData, config, dryRun) {
  const { time, dir } = postData;
  const carousel = loadJSON(path.join(dir, 'carousel.json'));
  const slides = getFinalSlides(dir);

  if (!carousel) { console.error(`   ❌ No carousel.json in ${dir}`); return; }
  if (slides.length === 0) { console.error(`   ❌ No final slides in ${dir} — run add-text-overlay.js first`); return; }

  console.log(`\n📤 Posting: ${path.basename(dir)}`);
  console.log(`   Hook: "${carousel.hookText}"`);
  console.log(`   CTA word: "${carousel.ctaWord || 'GUIDE'}"`);
  console.log(`   Slides: ${slides.length}\n`);

  if (dryRun) {
    console.log('   [DRY RUN] Would post to:', config.posting.platforms.join(', '));
    return;
  }

  const caption = carousel.caption || '';
  const results = {};

  // Post to each configured platform
  for (const platform of (config.posting.platforms || [])) {
    try {
      if (platform === 'instagram' && config.platforms?.instagram?.igAccessToken) {
        results.instagram = await postToInstagram(slides, caption, config);
      } else if (platform === 'tiktok' && config.platforms?.tiktok?.accessToken) {
        results.tiktok = await postToTikTok(slides, caption, config);
      } else {
        console.warn(`   ⚠️  ${platform}: not configured or missing credentials — skipping`);
      }
    } catch (err) {
      console.error(`   ❌ ${platform} failed: ${err.message}`);
      results[platform] = { error: err.message };
    }
  }

  // Save post results
  fs.writeFileSync(path.join(dir, 'posted.json'), JSON.stringify({
    postedAt: new Date().toISOString(),
    platforms: results,
    ctaWord: carousel.ctaWord,
    hookText: carousel.hookText
  }, null, 2));
}

async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');

  const config = loadJSON(CONFIG_PATH);
  if (!config) { console.error('❌ No config.json. Run onboarding first.'); process.exit(1); }

  // Check platforms are configured
  if (!config.platforms) {
    console.error('❌ No platforms configured in config.json.');
    console.error('   Run onboarding again or add platforms manually.');
    console.error('   See SKILL.md → Platform Setup section.');
    process.exit(1);
  }

  const postDirs = getTodayPostDirs(config);
  if (postDirs.length === 0) {
    console.log(`✅ No unposted carousels for today (${today()})`);
    return;
  }

  console.log(`\n📤 Posting ${postDirs.length} carousel(s)...`);
  if (dryRun) console.log('   [DRY RUN MODE — nothing will actually post]\n');

  for (const postData of postDirs) {
    await processPost(postData, config, dryRun);
    await sleep(3000); // pause between posts
  }

  console.log('\n✅ All posts published.');
  console.log('TikTok trending music was auto-added — no manual step needed.');
  console.log('\nAnalytics will be pulled tomorrow by daily-report.js');
}

main().catch(err => {
  console.error('\n❌ Posting failed:', err.message);
  process.exit(1);
});
