#!/usr/bin/env node
/**
 * daily-report.js
 * Pulls analytics from posted.json files (written by post-to-platforms.js),
 * scores performance across the 8 Carousel Method Module 9 iteration dimensions,
 * and feeds learnings back into content strategy.
 *
 * NO POSTIZ. Reads directly from platform APIs using credentials in config.json.
 *
 * The 8 iteration dimensions (Carousel Method Module 9):
 *   1. topicFit       — did people care?
 *   2. hookMagnitude  — did the hook create tension/curiosity?
 *   3. pacing         — did engagement hold through the carousel?
 *   4. slideDensity   — right amount per slide?
 *   5. valueArc       — did it build toward a payoff?
 *   6. saveTrigger    — did slide 8-9 drive saves?
 *   7. shareTrigger   — did it make people look smart?
 *   8. ctaPlacement   — did the comment CTA work?
 *
 * Usage:
 *   node scripts/daily-report.js
 *   node scripts/daily-report.js --days 5
 *   node scripts/daily-report.js --report-only
 */

const fs    = require('fs');
const path  = require('path');
const https = require('https');

const ROOT           = path.join(__dirname, '..');
const CONFIG_PATH    = path.join(ROOT, 'config.json');
const HOOK_PERF_PATH = path.join(ROOT, 'hook-performance.json');

function loadJSON(p, def = null) {
  if (fs.existsSync(p)) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return def; } }
  return def;
}
function today()    { return new Date().toISOString().split('T')[0]; }
function daysAgo(n) { const d = new Date(); d.setDate(d.getDate() - n); return d.toISOString().split('T')[0]; }

// ── ANALYTICS FETCHERS ────────────────────────────────────────────────────────

async function fetchInstagramAnalytics(mediaId, accessToken) {
  return new Promise(resolve => {
    const req = https.request({
      hostname: 'graph.instagram.com',
      path: `/v22.0/${mediaId}/insights?metric=reach,saved,shares&access_token=${accessToken}`,
      method: 'GET'
    }, res => {
      let data = '';
      res.on('data', c => { data += c; });
      res.on('end', () => {
        try {
          const parsed  = JSON.parse(data);
          const metrics = {};
          (parsed.data || []).forEach(m => { metrics[m.name] = m.values?.[0]?.value ?? m.value ?? 0; });
          resolve({ views: metrics.reach || 0, saves: metrics.saved || 0, shares: metrics.shares || 0, comments: 0 });
        } catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(10000, () => { req.destroy(); resolve(null); });
    req.end();
  });
}

async function fetchTikTokAnalytics(videoId, accessToken) {
  return new Promise(resolve => {
    const body = JSON.stringify({
      filters: { video_ids: [videoId] },
      fields:  ['video_views', 'likes', 'shares', 'comments']
    });
    const req = https.request({
      hostname: 'open.tiktokapis.com',
      path:     '/v2/video/query/',
      method:   'POST',
      headers: {
        'Authorization':  `Bearer ${accessToken}`,
        'Content-Type':   'application/json; charset=UTF-8',
        'Content-Length': Buffer.byteLength(body)
      }
    }, res => {
      let data = '';
      res.on('data', c => { data += c; });
      res.on('end', () => {
        try {
          const video = JSON.parse(data)?.data?.videos?.[0];
          if (!video) return resolve(null);
          resolve({ views: video.video_views || 0, saves: 0, shares: video.shares || 0, comments: video.comments || 0 });
        } catch { resolve(null); }
      });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(10000, () => { req.destroy(); resolve(null); });
    req.write(body);
    req.end();
  });
}

// ── SCORING ───────────────────────────────────────────────────────────────────

function scorePost({ views = 0, saves = 0, shares = 0, comments = 0 }) {
  return (
    (Math.min(views, 100000) / 100000) * 0.4 +
    (Math.min(saves, 5000)   / 5000)   * 0.3 +
    (Math.min(shares, 2000)  / 2000)   * 0.2 +
    (Math.min(comments, 500) / 500)    * 0.1
  );
}

// Module 9 — all 8 iteration dimensions
function analyzeM9(analytics, carousel) {
  const { views = 0, saves = 0, shares = 0, comments = 0 } = analytics;
  const saveRate  = views > 0 ? saves    / views : 0;
  const shareRate = views > 0 ? shares   / views : 0;
  const ctaRate   = views > 0 ? comments / views : 0;

  const g = (b) => b ? 'good' : 'poor';

  const dims = {
    topicFit:      { score: g(views >= 3000),      detail: `${views.toLocaleString()} views` },
    hookMagnitude: { score: g(views >= 8000),       detail: `hook: "${(carousel?.hookText||'').slice(0,45)}..."` },
    pacing:        { score: g(saveRate > 0.015),    detail: `save rate: ${(saveRate*100).toFixed(1)}%` },
    slideDensity:  { score: g(comments > 5),        detail: `${comments} comments` },
    valueArc:      { score: g(saveRate > 0.02),     detail: `save rate: ${(saveRate*100).toFixed(1)}%` },
    saveTrigger:   { score: g(saveRate > 0.025),    detail: `${saves} saves` },
    shareTrigger:  { score: g(shareRate > 0.008),   detail: `share rate: ${(shareRate*100).toFixed(1)}%` },
    ctaPlacement:  { score: g(ctaRate > 0.003),     detail: `comment rate: ${(ctaRate*100).toFixed(2)}%` }
  };

  // Verdict + what specifically to fix (Module 9 priority)
  let verdict, fix;
  if (views >= 10000 && saveRate >= 0.02) {
    verdict = 'double_down';
    fix = `SCALE — 3 variations of "${carousel?.hookFormula}" with "${carousel?.structureKey}"`;
  } else if (views >= 5000 && saveRate < 0.01) {
    verdict = 'fix_content';
    fix = 'Hook works, content not delivering — valueArc or saveTrigger broken. Check: insight revealed too early?';
  } else if (views < 2000 && saveRate >= 0.02) {
    verdict = 'fix_hook';
    fix = 'Content converts but hook weak — A/B test 3 different slide 1s with same structure';
  } else if (views < 1000) {
    verdict = 'fix_topic';
    fix = 'Topic had no demand — pick a different emotional territory from research sweep';
  } else {
    verdict = 'iterate';
    const weakest = Object.entries(dims).filter(([,v]) => v.score === 'poor').map(([k]) => k);
    fix = weakest.length ? `Fix weakest: ${weakest[0]} (${dims[weakest[0]].detail})` : 'Keep iterating';
  }

  return { dims, verdict, fix };
}

// ── COLLECT POSTED FILES ──────────────────────────────────────────────────────

function getPostedFiles(daysBack) {
  const postsRoot = path.join(ROOT, 'posts');
  if (!fs.existsSync(postsRoot)) return [];
  const cutoff = daysAgo(daysBack);
  const results = [];

  for (const dateDir of fs.readdirSync(postsRoot).sort().reverse()) {
    if (dateDir < cutoff) continue;
    const datePath = path.join(postsRoot, dateDir);
    if (!fs.statSync(datePath).isDirectory()) continue;
    for (const timeDir of fs.readdirSync(datePath).sort()) {
      const dir        = path.join(datePath, timeDir);
      const postedPath = path.join(dir, 'posted.json');
      if (fs.existsSync(postedPath)) {
        results.push({
          date:    dateDir,
          time:    timeDir,
          dir,
          posted:  loadJSON(postedPath),
          carousel: loadJSON(path.join(dir, 'carousel.json'))
        });
      }
    }
  }
  return results;
}

// ── FETCH + RECORD ────────────────────────────────────────────────────────────

async function fetchAndRecord(files, config) {
  const hookPerf = loadJSON(HOOK_PERF_PATH, { hooks: [], recentStructures: [], rules: { doubleDown: [], testing: [], dropped: [] } });
  const { platforms } = config;

  for (const { date, time, posted, carousel } of files) {
    if (!posted?.platforms) continue;
    let analytics = null, platform = null;

    if (posted.platforms.instagram && platforms?.instagram?.igAccessToken) {
      analytics = await fetchInstagramAnalytics(posted.platforms.instagram, platforms.instagram.igAccessToken);
      platform  = 'instagram';
    }
    if (!analytics && posted.platforms.tiktok && platforms?.tiktok?.accessToken) {
      analytics = await fetchTikTokAnalytics(posted.platforms.tiktok, platforms.tiktok.accessToken);
      platform  = 'tiktok';
    }
    if (!analytics) { console.log(`   ⚠️  ${date}/${time}: no analytics yet`); continue; }

    const score           = scorePost(analytics);
    const { dims, verdict, fix } = analyzeM9(analytics, carousel);
    const postId          = posted.platforms?.[platform];

    console.log(`   ${date}/${time} [${platform}]: ${analytics.views.toLocaleString()} views | ${verdict}`);
    console.log(`   → ${fix}`);

    // Update hook-performance.json
    const idx   = hookPerf.hooks.findIndex(h => h.postId === postId);
    const entry = {
      postId, platform, date,
      hookText:     carousel?.hookText     || '',
      hookFormula:  carousel?.hookFormula  || '',
      structureKey: carousel?.structureKey || '',
      ctaWord:      carousel?.ctaWord      || '',
      ...analytics,
      score:         Math.round(score * 100) / 100,
      verdict, fix,
      m9: Object.fromEntries(Object.entries(dims).map(([k, v]) => [k, v.score])),
      lastUpdated: new Date().toISOString()
    };
    if (idx >= 0) hookPerf.hooks[idx] = entry;
    else          hookPerf.hooks.push(entry);

    // Structural learning — update rules
    const sk = carousel?.structureKey;
    if (sk) {
      if (verdict === 'double_down' && !hookPerf.rules.doubleDown.includes(sk)) {
        hookPerf.rules.doubleDown.push(sk);
        hookPerf.rules.dropped = hookPerf.rules.dropped.filter(d => d !== sk);
      }
      const poorCount = hookPerf.hooks.filter(h => h.structureKey === sk && ['fix_topic','iterate'].includes(h.verdict)).length;
      if (poorCount >= 3 && !hookPerf.rules.dropped.includes(sk)) {
        hookPerf.rules.dropped.push(sk);
        hookPerf.rules.doubleDown = hookPerf.rules.doubleDown.filter(d => d !== sk);
        console.log(`   🗑  Dropped structure "${sk}" after 3 poor results`);
      }
    }
  }

  fs.writeFileSync(HOOK_PERF_PATH, JSON.stringify(hookPerf, null, 2));
  return hookPerf;
}

// ── REPORT ────────────────────────────────────────────────────────────────────

function generateReport(config, hookPerf) {
  const dateStr  = today();
  const { creator } = config;
  const hooks    = hookPerf.hooks || [];
  const recent   = hooks.filter(h => h.date >= daysAgo(7));
  const avgViews = recent.length ? Math.round(recent.reduce((s, h) => s + (h.views || 0), 0) / recent.length) : 0;
  const top      = [...recent].sort((a, b) => (b.score||0) - (a.score||0))[0];

  // Dimension health summary
  const dimHealth = {};
  ['topicFit','hookMagnitude','pacing','slideDensity','valueArc','saveTrigger','shareTrigger','ctaPlacement'].forEach(d => {
    const good = recent.filter(h => h.m9?.[d] === 'good').length;
    const poor = recent.filter(h => h.m9?.[d] === 'poor').length;
    dimHealth[d] = { good, poor, icon: good > poor ? '🟢' : poor > 0 ? '🔴' : '🟡' };
  });

  const fixes = Object.entries(dimHealth)
    .filter(([, v]) => v.poor > v.good)
    .map(([dim]) => {
      const fixMap = {
        topicFit:      'Try different emotional territories from research sweep',
        hookMagnitude: 'Test more polarizing hooks — try opposite angle or sharper formula',
        pacing:        'Slides 5-6 may be overloaded — apply No Fat Slide Rule, 1 idea only',
        slideDensity:  'Insights too obvious or too complex — calibrate value per slide',
        valueArc:      'Hold main insight until slide 5-6. Never reveal it early.',
        saveTrigger:   'Strengthen Slide 8 Lift — make transformation more concrete + specific',
        shareTrigger:  'Add more surprising/counterintuitive truth — make people look smart sharing',
        ctaPlacement:  'Be more specific about what CTA word delivers — "comment X and I\'ll send you [specific thing]"'
      };
      return `- ${dim}: ${fixMap[dim] || 'investigate'}`;
    });

  const report = `# Daily Report — ${dateStr}
${creator.name} | ${creator.niche} | goal: ${creator.contentGoal}

## Performance (Last 7 Days)
Posts tracked: ${recent.length} | Avg views: ${avgViews.toLocaleString()}
Top post: "${top ? top.hookText?.slice(0,60) : 'no data'}..." (${top ? (top.score*100).toFixed(0)+'%' : 'N/A'})

## Carousel Method — 8 Dimension Health
${Object.entries(dimHealth).map(([d, v]) => `${v.icon} ${d}: ${v.good} good / ${v.poor} poor`).join('\n')}

## What To Fix
${fixes.length ? fixes.join('\n') : '- All dimensions healthy — maintain approach'}

## Rules
Double down: ${hookPerf.rules?.doubleDown?.join(', ') || 'none yet'}
Drop:        ${hookPerf.rules?.dropped?.join(', ')    || 'none yet'}

---
*Carousel Pipeline — Viral Feedback Loop — ${dateStr}*`;

  fs.mkdirSync(path.join(ROOT, 'reports'), { recursive: true });
  const p = path.join(ROOT, 'reports', `${dateStr}.md`);
  fs.writeFileSync(p, report);
  return { report, reportPath: p };
}

// ── MAIN ──────────────────────────────────────────────────────────────────────

async function main() {
  const args       = process.argv.slice(2);
  const days       = parseInt(args.find(a => /^\d+$/.test(a)) || '3', 10);
  const reportOnly = args.includes('--report-only');

  const config = loadJSON(CONFIG_PATH);
  if (!config) { console.error('❌ No config.json.'); process.exit(1); }

  console.log('\n📊 DAILY REPORT');
  console.log('─'.repeat(50));

  let hookPerf = loadJSON(HOOK_PERF_PATH, { hooks: [], recentStructures: [], rules: { doubleDown: [], testing: [], dropped: [] } });

  if (!reportOnly) {
    const files = getPostedFiles(days);
    if (!files.length) console.log(`No posted files in last ${days} days. Post first.`);
    else hookPerf = await fetchAndRecord(files, config);
  }

  const { report, reportPath } = generateReport(config, hookPerf);
  console.log('\n' + report);
  console.log(`\n📄 Saved: ${reportPath}`);
}

main().catch(err => { console.error('\n❌ Report failed:', err.message); process.exit(1); });
