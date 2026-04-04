#!/usr/bin/env node
/**
 * onboarding.js
 * First-run setup. Interviews the creator, builds config.json,
 * validates API keys, runs competitor research, generates first batch.
 */

const readline = require('readline');
const fs = require('fs');
const path = require('path');
const https = require('https');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');
const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

function ask(question) {
  return new Promise(resolve => rl.question(`\n${question}\n> `, resolve));
}

function askNum(question, min, max) {
  return new Promise(async resolve => {
    while (true) {
      const raw = await ask(`${question} (${min}–${max})`);
      const n = parseInt(raw, 10);
      if (!isNaN(n) && n >= min && n <= max) { resolve(n); break; }
      console.log(`Please enter a number between ${min} and ${max}.`);
    }
  });
}

function askChoice(question, choices) {
  const menu = choices.map((c, i) => `  ${i + 1}. ${c}`).join('\n');
  return new Promise(async resolve => {
    while (true) {
      const raw = await ask(`${question}\n${menu}`);
      const n = parseInt(raw, 10);
      if (!isNaN(n) && n >= 1 && n <= choices.length) { resolve(choices[n - 1]); break; }
      console.log('Please enter a valid number.');
    }
  });
}


async function validateOpenAIKey(apiKey) {
  return new Promise(resolve => {
    const req = https.request({
      hostname: 'api.openai.com',
      path: '/v1/models',
      method: 'GET',
      headers: { 'Authorization': `Bearer ${apiKey}` }
    }, res => resolve(res.statusCode === 200));
    req.on('error', () => resolve(false));
    req.end();
  });
}

function buildPostingTimes(count, timezone) {
  const slots = ['06:00','07:30','09:00','11:00','13:00','16:00','18:00','19:30','21:00','22:30'];
  // Spread evenly across waking hours
  const step = Math.floor(slots.length / count);
  return Array.from({ length: count }, (_, i) => slots[Math.min(i * step, slots.length - 1)]);
}

async function run() {
  console.log('\n' + '═'.repeat(60));
  console.log('  CAROUSEL PIPELINE — ONBOARDING');
  console.log('  Let\'s set up your automated content machine.');
  console.log('═'.repeat(60));

  console.log('\nI\'ll ask you a few questions to personalize the pipeline');
  console.log('to your brand. This takes about 5 minutes.\n');

  // ── CREATOR PROFILE ──────────────────────────────────────────
  console.log('\n── WHO YOU ARE ─────────────────────────────────────────');

  const name = await ask('What\'s your name or creator handle?');

  const niche = await ask(
    'What\'s your niche? Be specific.\n' +
    '  Examples: "fitness for busy moms", "personal finance for Gen Z",\n' +
    '  "mindset for entrepreneurs", "healthy cooking on a budget"'
  );

  const audience = await ask(
    'Who is your ideal viewer/follower?\n' +
    '  Age, situation, what they struggle with.\n' +
    '  Example: "Women 28-40 who want to lose weight but hate restrictive diets"'
  );

  const coreMessage = await ask(
    'What\'s your unique angle or core message?\n' +
    '  What do you say that others in your niche don\'t?\n' +
    '  Example: "Consistency beats intensity — small systems beat willpower"'
  );

  const brandVoice = await askChoice(
    'What\'s your brand voice?',
    [
      'Calm & educational (like a knowledgeable friend)',
      'Bold & direct (no-fluff, straight talk)',
      'Inspiring & motivational (uplift and energize)',
      'Funny & relatable (humor + truth)',
      'Analytical & data-driven (logical, evidence-based)',
      'Warm & personal (storytelling, vulnerable)'
    ]
  );

  const contentGoal = await askChoice(
    'What\'s your main content goal right now?',
    ['Follower growth', 'Saves (authority + reach)', 'Shares (virality)', 'Comments (community)', 'All of the above']
  );

  // ── IMAGE STYLE ───────────────────────────────────────────────
  console.log('\n── VISUAL STYLE ────────────────────────────────────────');
  console.log('Your image style is critical. The more specific, the better.');
  console.log('Vague prompts = generic AI images. Specific prompts = scroll-stopping content.\n');

  const subject = await ask(
    'What\'s typically in your images?\n' +
    '  Examples: "a woman in her 30s", "a person at a desk",\n' +
    '  "a meal on a kitchen counter", "an outdoor workout scene"'
  );

  const visualVibe = await ask(
    'What\'s the visual vibe? (lighting, mood, setting)\n' +
    '  Examples: "warm golden hour light, cozy home", "clean minimal desk setup,\n' +
    '  bright natural light", "moody gym, dramatic contrast"'
  );

  const consistencyAnchor = await ask(
    'What visual element stays the same across all slides?\n' +
    '  (This keeps a slideshow looking like one cohesive shoot)\n' +
    '  Examples: "same woman, same kitchen, white cabinets and oak countertop",\n' +
    '  "same desk setup, silver MacBook always visible on left"'
  );

  const basePrompt =
    `iPhone photo of ${subject}, ${visualVibe}. ` +
    `Realistic, natural colors, taken on iPhone 15 Pro. No text, no watermarks, no logos. ` +
    `${consistencyAnchor}`;

  console.log('\nBase image prompt built:');
  console.log(`  "${basePrompt}"`);

  console.log('(Slide 1 hook image is auto-derived from hook emotion — no setup needed)');

  // ── POSTING SETUP ─────────────────────────────────────────────
  console.log('\n── POSTING SETUP ───────────────────────────────────────');

  const postsPerDay = await askNum(
    'How many posts do you want to generate and queue per day?',
    1, 10
  );

  const timezone = await ask(
    'What\'s your timezone?\n' +
    '  Examples: America/New_York, America/Los_Angeles, Europe/London, Asia/Tokyo'
  );

  const postingTimes = buildPostingTimes(postsPerDay, timezone);
  console.log(`\nPosting schedule: ${postingTimes.join(', ')} (${timezone})`);
  console.log('(You can edit these in config.json later)');

  const platforms = await askChoice(
    'Which platforms do you want to post to?',
    ['TikTok only', 'Instagram only', 'Both TikTok and Instagram']
  );

  // ── LANGUAGE PREFERENCE ───────────────────────────────────────
  console.log('\n── LANGUAGE ────────────────────────────────────────────');
  console.log('The pipeline writes carousel content in the language you choose.');
  console.log('Multilingual mode generates EN + FR + ES versions of every post.\n');

  const langChoice = await askChoice(
    'What language do you post in?',
    ['English (en)', 'French (fr)', 'Spanish (es)', 'Multilingual (EN + FR + ES — 3x posts per slot)']
  );

  const multilingualEnabled = langChoice.includes('Multilingual');
  let postingLanguage = 'en';
  if (langChoice.includes('French'))   postingLanguage = 'fr';
  if (langChoice.includes('Spanish'))  postingLanguage = 'es';
  if (multilingualEnabled)             postingLanguage = 'en';  // EN is primary in multilingual mode

  console.log(multilingualEnabled
    ? '\nMultilingual mode: 3 versions per post (EN primary, FR +3 min, ES +6 min)'
    : `\nPosting language: ${postingLanguage.toUpperCase()}`
  );

  // ── API KEYS ──────────────────────────────────────────────────
  console.log('\n── API KEYS ─────────────────────────────────────────────');
  console.log('These are stored locally in config.json — never shared anywhere.\n');

  // PostFast — the only required integration
  console.log('POSTFAST API KEY  (required)');
  console.log('PostFast handles scheduling to both TikTok and Instagram in one place.');
  console.log('Get it at: app.postfa.st → Settings → API Keys\n');
  const postfastKey = await ask('Paste your PostFast API key (leave blank to set up later)');
  if (postfastKey.trim()) {
    console.log('✅ PostFast key saved — connect TikTok + Instagram inside the PostFast dashboard');
  } else {
    console.log('⚠️  Add later: config.json → postfast.apiKey');
  }

  // PostFast account IDs
  console.log('\nPOSTFAST ACCOUNT IDs');
  console.log('Find these in app.postfa.st → Settings → Connected Accounts\n');
  const tiktokAccountId    = await ask('PostFast TikTok account ID (leave blank to set up later)');
  const instagramAccountId = await ask('PostFast Instagram account ID (leave blank to set up later)');

  // Google Drive — optional
  console.log('\nGOOGLE DRIVE  (optional — for PDF resource uploads)');
  console.log('If enabled, every post\'s PDF resource is automatically uploaded to:');
  console.log('  Google Drive → CLAUDE AGENT CAROUSEL PDFS → [date -- topic]');
  console.log('\nSetup steps (one-time):');
  console.log('  1. console.cloud.google.com → enable Google Drive API');
  console.log('  2. Create OAuth 2.0 Desktop App credentials');
  console.log('  3. Download JSON → save as credentials/google-credentials.json');
  console.log('  4. First run of upload_to_drive.py opens browser for authorization\n');
  const driveEnabled = await askChoice(
    'Enable Google Drive PDF uploads?',
    ['Yes — I will add credentials/google-credentials.json', 'No — skip for now']
  );

  const platformList = [];
  if (platforms.includes('TikTok'))     platformList.push('tiktok');
  if (platforms.includes('Instagram'))  platformList.push('instagram');

  // ── BUILD CONFIG ──────────────────────────────────────────────
  const langOffsets = multilingualEnabled
    ? { en: { offsetMinutes: 0 }, fr: { offsetMinutes: 3 }, es: { offsetMinutes: 6 } }
    : { [postingLanguage]: { offsetMinutes: 0 } };

  const config = {
    creator: {
      name, niche, audience, coreMessage, brandVoice,
      contentGoal: contentGoal.toLowerCase().split(' ')[0]
    },
    visualIdentity: {
      canvas: { width: 1080, height: 1350, format: 'jpeg', quality: 96 },
      fonts: { headline: 'Anton Bold', body: 'Poppins Light', label: 'Poppins Medium' },
      colors: { black: [8,8,8], cream: [237,232,223], gold: [255,252,0], white: [245,240,232], dim: [175,170,162] },
      slideAlternation: 'odd=dark, even=light'
    },
    postfast: {
      apiKey: postfastKey.trim() || null,
      baseUrl: 'https://api.postfa.st',
      accounts: {
        tiktok:    { id: tiktokAccountId.trim()    || null, platform: 'TIKTOK' },
        instagram: { id: instagramAccountId.trim() || null, platform: 'INSTAGRAM' }
      },
      languages: Object.fromEntries(
        Object.entries(langOffsets).map(([lang, cfg]) => [lang, {
          tiktok:        tiktokAccountId.trim()    || null,
          instagram:     instagramAccountId.trim() || null,
          offsetMinutes: cfg.offsetMinutes
        }])
      )
    },
    posting: {
      postsPerDay,
      postingLanguage,
      multilingualEnabled,
      languages: multilingualEnabled ? ['en','fr','es'] : [postingLanguage],
      times: postingTimes,
      timezone: timezone || 'America/New_York',
      platforms: platformList,
      totalDailyPosts: postsPerDay * (multilingualEnabled ? 3 : 1)
    },
    googleDrive: {
      enabled: driveEnabled.startsWith('Yes'),
      rootFolderName: 'CLAUDE AGENT CAROUSEL PDFS',
      credentialsFile: 'credentials/google-credentials.json',
      tokenFile: 'credentials/google-token.json'
    },
    paths: {
      posts: 'posts/',
      reports: 'reports/',
      competitorResearch: 'competitor-research.json',
      hookPerformance: 'hook-performance.json'
    },
    _setupDate: new Date().toISOString()
  };

  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
  console.log('\n✅ Config saved to config.json');

  const totalPosts = postsPerDay * (multilingualEnabled ? 3 : 1);

  // ── NEXT STEPS ────────────────────────────────────────────────
  console.log('\n' + '═'.repeat(60));
  console.log('  SETUP COMPLETE');
  console.log('═'.repeat(60));
  console.log(`
Creator:    ${name} — ${niche}
Language:   ${multilingualEnabled ? 'EN + FR + ES (multilingual)' : postingLanguage.toUpperCase()}
Posts/day:  ${postsPerDay} slots x ${multilingualEnabled ? '3 languages' : '1 language'} = ${totalPosts} posts
Platforms:  ${platformList.join(', ')}
Schedule:   ${postingTimes.join(', ')} (${timezone})
Drive:      ${driveEnabled.startsWith('Yes') ? 'Enabled (add credentials/google-credentials.json)' : 'Disabled'}

NEXT STEPS:
  1. Run your first daily batch:
     python scripts/daily_run.py

  2. After slides are generated, add trending audio on TikTok before publishing.
     (30 seconds per post — the single biggest reach factor on TikTok)

  3. Check analytics after 24 hours:
     python scripts/analytics_pull.py

  4. If Google Drive is enabled, upload today's PDF:
     python scripts/upload_to_drive.py --slot-dir posts/YYYY-MM-DD/HHMM

The pipeline runs itself from here.
`);

  rl.close();
}

run().catch(err => {
  console.error('Onboarding error:', err);
  rl.close();
  process.exit(1);
});
