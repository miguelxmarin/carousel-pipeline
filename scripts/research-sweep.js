#!/usr/bin/env node
/**
 * research-sweep.js
 * Scans live sources daily for real audience friction and emotion signals.
 * Runs BEFORE generate-carousel.js so content is built from what the
 * audience is actually saying today, not from static templates.
 *
 * Sources scanned:
 *   - Reddit: top posts + comments in niche subreddits (honest complaints, wins)
 *   - TikTok: comments on top niche posts (raw audience language)
 *   - X/Twitter: frustrated or honest posts about the niche topic
 *
 * Output: research-sweep.json — friction signals Claude uses to generate hooks
 *
 * Usage:
 *   node scripts/research-sweep.js              # full sweep
 *   node scripts/research-sweep.js --quick      # Reddit only (faster)
 *   node scripts/research-sweep.js --dry-run    # show what would be scanned
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const CONFIG_PATH = path.join(ROOT, 'config.json');
const OUTPUT_PATH = path.join(ROOT, 'research-sweep.json');
const HOOK_PERF_PATH = path.join(ROOT, 'hook-performance.json');

function loadJSON(p, def = null) {
  if (fs.existsSync(p)) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return def; } }
  return def;
}

function today() { return new Date().toISOString().split('T')[0]; }

// ── REDDIT FETCH (public JSON API, no auth needed) ────────────────────────────
async function fetchReddit(subreddit, sort = 'hot', limit = 25) {
  return new Promise((resolve) => {
    const options = {
      hostname: 'www.reddit.com',
      path: `/r/${subreddit}/${sort}.json?limit=${limit}&raw_json=1`,
      method: 'GET',
      headers: { 'User-Agent': 'carousel-pipeline/1.0 (content research tool)' }
    };
    const req = https.request(options, res => {
      let data = '';
      res.on('data', c => { data += c; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          const posts = (parsed?.data?.children || []).map(p => ({
            title: p.data.title,
            score: p.data.score,
            numComments: p.data.num_comments,
            selftext: (p.data.selftext || '').slice(0, 400),
            url: `https://reddit.com${p.data.permalink}`
          }));
          resolve(posts);
        } catch { resolve([]); }
      });
    });
    req.on('error', () => resolve([]));
    req.setTimeout(10000, () => { req.destroy(); resolve([]); });
    req.end();
  });
}

async function fetchRedditComments(postUrl) {
  return new Promise((resolve) => {
    const jsonUrl = postUrl.replace('https://reddit.com', '') + '.json?limit=20&raw_json=1';
    const options = {
      hostname: 'www.reddit.com',
      path: jsonUrl,
      method: 'GET',
      headers: { 'User-Agent': 'carousel-pipeline/1.0 (content research tool)' }
    };
    const req = https.request(options, res => {
      let data = '';
      res.on('data', c => { data += c; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          const comments = (parsed?.[1]?.data?.children || [])
            .filter(c => c.kind === 't1' && c.data.score > 2)
            .slice(0, 8)
            .map(c => ({ body: c.data.body?.slice(0, 300), score: c.data.score }));
          resolve(comments);
        } catch { resolve([]); }
      });
    });
    req.on('error', () => resolve([]));
    req.setTimeout(8000, () => { req.destroy(); resolve([]); });
    req.end();
  });
}

// ── SIGNAL EXTRACTION ─────────────────────────────────────────────────────────
// These patterns find the emotional raw material for hooks —
// what the audience is already saying in their own words.

const FRICTION_PATTERNS = [
  /i (can'?t|don'?t|couldn'?t|won'?t|never) (seem to |)(figure out|understand|get|make|do|find)/i,
  /why (does|do|is|are|isn'?t|aren'?t|can'?t|won'?t)/i,
  /nobody (tells|talks about|mentions|explains)/i,
  /i (wish|want|need) (someone had |)(told|showed|explained)/i,
  /feels? like (no matter what|nothing|everything)/i,
  /i'?ve (tried|been trying|been doing) (everything|so much|a lot)/i,
  /still (not|no|can'?t|won'?t|doesn'?t)/i,
  /honest(ly)?[\s,]/i,
  /frustrated|exhausted|overwhelmed|stuck|confused|lost/i,
  /the (real|actual|honest|hard|ugly|brutal) truth/i,
  /what (actually|really) (works|helped|changed|matters)/i,
  /game.?changer|life.?chang/i,
  /i used to (think|believe|do)/i,
  /turns? out/i,
  /stop doing|stop trying|quit/i
];

const ASPIRATION_PATTERNS = [
  /finally (figured out|found|got|made|did|understand)/i,
  /this (changed|fixed|helped|worked)/i,
  /went from .* to/i,
  /best (thing|advice|tip|hack|decision)/i,
  /wish i (knew|had|found|started)/i
];

function extractSignals(text) {
  if (!text) return { friction: [], aspiration: [] };
  const sentences = text.split(/[.!?]+/).map(s => s.trim()).filter(s => s.length > 20 && s.length < 300);
  const friction = sentences.filter(s => FRICTION_PATTERNS.some(p => p.test(s)));
  const aspiration = sentences.filter(s => ASPIRATION_PATTERNS.some(p => p.test(s)));
  return { friction, aspiration };
}

function scorePost(post) {
  // High score = high engagement + signal-rich text
  const textSignals = extractSignals(post.title + ' ' + post.selftext);
  const signalCount = textSignals.friction.length + textSignals.aspiration.length;
  return (post.score / 100) + (post.numComments / 10) + (signalCount * 5);
}

// ── SUBREDDIT MAPPING ─────────────────────────────────────────────────────────
// Maps broad niche keywords to relevant subreddits.
// Agnostic — works for any niche the creator defines.

const NICHE_SUBREDDIT_MAP = {
  fitness: ['r/fitness', 'r/loseit', 'r/xxfitness', 'r/bodyweightfitness'],
  health: ['r/health', 'r/nutrition', 'r/veganfitness', 'r/intermittentfasting'],
  mindset: ['r/selfimprovement', 'r/productivity', 'r/getdisciplined', 'r/decidingtobebetter'],
  productivity: ['r/productivity', 'r/getdisciplined', 'r/nosurf', 'r/digitalnomad'],
  business: ['r/entrepreneur', 'r/smallbusiness', 'r/startups', 'r/marketing'],
  marketing: ['r/marketing', 'r/socialmedia', 'r/content_marketing', 'r/entrepreneur'],
  finance: ['r/personalfinance', 'r/financialindependence', 'r/fire', 'r/povertyfinance'],
  investing: ['r/investing', 'r/stocks', 'r/personalfinance', 'r/financialindependence'],
  cooking: ['r/cooking', 'r/mealprep', 'r/budgetfood', 'r/EatCheapAndHealthy'],
  parenting: ['r/parenting', 'r/daddit', 'r/mommit', 'r/beyondthebump'],
  relationships: ['r/relationship_advice', 'r/dating_advice', 'r/marriage'],
  career: ['r/careerguidance', 'r/jobs', 'r/cscareerquestions', 'r/remotework'],
  ai: ['r/artificial', 'r/MachineLearning', 'r/ChatGPT', 'r/midjourney'],
  creator: ['r/NewTubers', 'r/content_marketing', 'r/socialmedia', 'r/Instagram'],
  default: ['r/selfimprovement', 'r/productivity', 'r/entrepreneur']
};

function getSubreddits(niche) {
  const nicheWords = niche.toLowerCase().split(/\s+/);
  for (const word of nicheWords) {
    for (const [key, subs] of Object.entries(NICHE_SUBREDDIT_MAP)) {
      if (word.includes(key) || key.includes(word)) return subs.slice(0, 3);
    }
  }
  return NICHE_SUBREDDIT_MAP.default;
}

// ── MAIN SWEEP ────────────────────────────────────────────────────────────────
async function runSweep(config, options = {}) {
  const { niche, audience, coreMessage } = config.creator;
  const quickMode = options.quick || false;

  console.log(`\n🔍 Research sweep for: "${niche}"`);
  console.log(`   Audience: ${audience}`);
  console.log(`   Mode: ${quickMode ? 'quick (Reddit only)' : 'full'}\n`);

  const allSignals = {
    friction: [],    // things audience struggles with, says out loud
    aspiration: [],  // what they want / what worked for others
    rawPhrases: [],  // verbatim phrases worth turning into hooks
    topPosts: []     // highest signal posts for reference
  };

  // ── REDDIT ──────────────────────────────────────────────────────────────────
  const subreddits = getSubreddits(niche);
  console.log(`   Reddit: scanning ${subreddits.join(', ')}`);

  for (const sub of subreddits) {
    const subName = sub.replace('r/', '');
    const posts = await fetchReddit(subName, 'hot', 20);

    if (posts.length === 0) {
      console.log(`   ⚠️  ${sub}: no posts fetched`);
      continue;
    }

    // Score and sort by signal richness
    const scored = posts
      .map(p => ({ ...p, signalScore: scorePost(p) }))
      .sort((a, b) => b.signalScore - a.signalScore)
      .slice(0, 6);

    for (const post of scored) {
      const signals = extractSignals(post.title + ' ' + post.selftext);

      allSignals.friction.push(...signals.friction.map(s => ({ text: s, source: sub, type: 'post' })));
      allSignals.aspiration.push(...signals.aspiration.map(s => ({ text: s, source: sub, type: 'post' })));

      // Fetch comments on highest-scoring posts
      if (post.signalScore > 10 && post.numComments > 5) {
        const comments = await fetchRedditComments(post.url);
        for (const c of comments) {
          const cSignals = extractSignals(c.body);
          allSignals.friction.push(...cSignals.friction.map(s => ({ text: s, source: sub, type: 'comment', score: c.score })));
          allSignals.aspiration.push(...cSignals.aspiration.map(s => ({ text: s, source: sub, type: 'comment', score: c.score })));

          // High-score comments = audience in their own words = raw hook material
          if (c.score > 10 && c.body && c.body.length > 30) {
            allSignals.rawPhrases.push({ phrase: c.body.slice(0, 150), source: sub, score: c.score });
          }
        }
      }

      if (post.signalScore > 20) {
        allSignals.topPosts.push({ title: post.title, score: post.score, comments: post.numComments, source: sub, url: post.url });
      }
    }

    console.log(`   ✅ ${sub}: ${scored.length} posts scanned`);

    // Polite delay between subreddits
    await new Promise(r => setTimeout(r, 800));
  }

  // ── DEDUPLICATE + RANK ────────────────────────────────────────────────────
  // Remove near-duplicates, keep highest-signal phrases
  const dedup = (arr) => {
    const seen = new Set();
    return arr.filter(item => {
      const key = (item.text || item.phrase || '').slice(0, 60).toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };

  allSignals.friction = dedup(allSignals.friction).slice(0, 30);
  allSignals.aspiration = dedup(allSignals.aspiration).slice(0, 20);
  allSignals.rawPhrases = dedup(allSignals.rawPhrases)
    .sort((a, b) => (b.score || 0) - (a.score || 0))
    .slice(0, 15);
  allSignals.topPosts = allSignals.topPosts.slice(0, 10);

  // ── SYNTHESIZE HOOK ANGLES ────────────────────────────────────────────────
  // Distill signals into concrete hook directions for generate-carousel.js
  const hookAngles = synthesizeAngles(allSignals, niche, audience);

  const output = {
    sweptAt: new Date().toISOString(),
    niche,
    audience,
    signals: allSignals,
    hookAngles,
    meta: {
      totalFrictionSignals: allSignals.friction.length,
      totalAspirationSignals: allSignals.aspiration.length,
      rawPhrasesCollected: allSignals.rawPhrases.length,
      sourcesScanned: subreddits
    }
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2));

  console.log(`\n📊 Sweep complete:`);
  console.log(`   Friction signals: ${allSignals.friction.length}`);
  console.log(`   Aspiration signals: ${allSignals.aspiration.length}`);
  console.log(`   Raw phrases: ${allSignals.rawPhrases.length}`);
  console.log(`   Hook angles generated: ${hookAngles.length}`);
  console.log(`\n   Saved to: research-sweep.json`);

  if (hookAngles.length > 0) {
    console.log(`\n🎣 Top hook angles for today:`);
    hookAngles.slice(0, 5).forEach((a, i) => console.log(`   ${i + 1}. ${a.angle}`));
  }

  return output;
}

function synthesizeAngles(signals, niche, audience) {
  // Turn raw friction/aspiration signals into hook directions
  // These become the INPUT to generate-carousel.js instead of generic templates
  const angles = [];

  // Pattern 1: Most common frustration → "everyone's struggling with X" hook
  const frustrationClusters = clusterByKeyword(signals.friction);
  for (const [keyword, items] of Object.entries(frustrationClusters)) {
    if (items.length >= 2) {
      angles.push({
        type: 'frustration',
        angle: `Multiple people struggling with "${keyword}" in ${niche}`,
        hookDirection: `Make them feel seen about ${keyword}`,
        sourceCount: items.length,
        examplePhrases: items.slice(0, 2).map(i => i.text)
      });
    }
  }

  // Pattern 2: High-score raw phrases → direct hook language
  for (const phrase of signals.rawPhrases.slice(0, 5)) {
    angles.push({
      type: 'verbatim',
      angle: `Audience language: "${phrase.phrase.slice(0, 80)}..."`,
      hookDirection: 'Mirror this exact sentiment in slide 1 language',
      sourceCount: 1,
      score: phrase.score
    });
  }

  // Pattern 3: Aspiration signals → "what worked" hooks
  const aspirationClusters = clusterByKeyword(signals.aspiration);
  for (const [keyword, items] of Object.entries(aspirationClusters)) {
    if (items.length >= 2) {
      angles.push({
        type: 'aspiration',
        angle: `People finding success with "${keyword}" in ${niche}`,
        hookDirection: `Before/after or transformation hook around ${keyword}`,
        sourceCount: items.length,
        examplePhrases: items.slice(0, 2).map(i => i.text)
      });
    }
  }

  // Sort by source count (more mentions = more validated)
  return angles.sort((a, b) => (b.sourceCount || 0) - (a.sourceCount || 0)).slice(0, 10);
}

function clusterByKeyword(signals) {
  const clusters = {};
  const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'do', 'does', 'did', 'it', 'i', 'you', 'we', 'they', 'my', 'your', 'our', 'this', 'that', 'just', 'so', 'like', 'get', 'got']);

  for (const signal of signals) {
    const words = (signal.text || '').toLowerCase()
      .replace(/[^a-z\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length > 4 && !stopWords.has(w));

    for (const word of words) {
      if (!clusters[word]) clusters[word] = [];
      clusters[word].push(signal);
    }
  }

  // Only return keywords that appear 2+ times
  return Object.fromEntries(
    Object.entries(clusters)
      .filter(([, items]) => items.length >= 2)
      .sort(([, a], [, b]) => b.length - a.length)
      .slice(0, 8)
  );
}

// ── ENTRY POINT ───────────────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const quick = args.includes('--quick');

  const config = loadJSON(CONFIG_PATH);
  if (!config) {
    console.error('❌ No config.json. Run: node scripts/onboarding.js');
    process.exit(1);
  }

  if (dryRun) {
    const subs = getSubreddits(config.creator.niche);
    console.log(`\nDry run — would scan:`);
    console.log(`  Reddit: ${subs.join(', ')}`);
    console.log(`\nNiche: "${config.creator.niche}"`);
    return;
  }

  // Check if we already swept today
  const existing = loadJSON(OUTPUT_PATH);
  if (existing && existing.sweptAt && existing.sweptAt.startsWith(today())) {
    console.log(`✅ Already swept today (${today()}). Use --force to re-run.`);
    if (!args.includes('--force')) {
      console.log(`   Hook angles available: ${existing.hookAngles?.length || 0}`);
      return;
    }
  }

  await runSweep(config, { quick });
}

main().catch(err => {
  console.error('\n❌ Research sweep failed:', err.message);
  process.exit(1);
});
