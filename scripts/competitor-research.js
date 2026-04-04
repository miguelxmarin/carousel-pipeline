#!/usr/bin/env node
/**
 * competitor-research.js
 * Uses browser access to scan TikTok for what's working in the creator's niche.
 * Saves findings to competitor-research.json.
 *
 * Re-run weekly or when performance drops across all posts.
 *
 * Note: This script uses Claude's browser tool. Run it inside Claude Code
 * or with browser access enabled. It will open TikTok and analyze content.
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const ROOT = path.join(__dirname, '..');
const CONFIG_PATH = path.join(ROOT, 'config.json');
const OUTPUT_PATH = path.join(ROOT, 'competitor-research.json');

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.error('❌ No config.json found. Run onboarding first.');
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
function ask(q) { return new Promise(r => rl.question(`\n${q}\n> `, r)); }

async function main() {
  const config = loadConfig();
  const { niche, audience } = config.creator;

  console.log('\n' + '═'.repeat(60));
  console.log('  COMPETITOR RESEARCH');
  console.log(`  Niche: ${niche}`);
  console.log('═'.repeat(60));

  console.log(`
This script guides you through manual TikTok research.
It takes about 15-20 minutes the first time.

What we're looking for:
  - What hooks stop the scroll in "${niche}"
  - Which content formats get the most views/saves
  - What gaps exist that nobody is filling
  - Patterns to avoid (oversaturated or underperforming)
`);

  // ── MANUAL RESEARCH PROMPTS ────────────────────────────────────────────────
  console.log('── STEP 1: Open TikTok and search for your niche ──');
  console.log(`   Search: "${niche}" on TikTok`);
  console.log('   Sort by: Most Liked (or Views)');
  console.log('   Look at: Top 20 posts\n');

  await ask('Press Enter when you\'re on TikTok and have results');

  console.log('\n── STEP 2: Find 3-5 competitor accounts ──');
  console.log('Look for accounts posting similar content to what you\'ll create.');
  console.log('Pick ones with 10K–500K followers (too big = outliers, too small = not enough data)\n');

  const competitors = [];
  for (let i = 0; i < 3; i++) {
    console.log(`\nCompetitor ${i + 1}:`);
    const handle = await ask('Their TikTok handle (e.g. @username)');
    const followers = await ask('Approximate followers (e.g. 50000)');
    const topViews = await ask('Views on their BEST recent post');
    const avgViews = await ask('Views on their AVERAGE recent post');
    const format = await ask('What format do they mainly use? (slideshow/video/before-after/listicle/POV)');
    const hookPattern = await ask('What does their best hook look like? (describe or quote it)');
    const cta = await ask('What CTA do they usually use? (link in bio / comment / follow / etc)');

    competitors.push({
      handle,
      followers: parseInt(followers.replace(/\D/g, '')) || 0,
      topViews: parseInt(topViews.replace(/\D/g, '')) || 0,
      avgViews: parseInt(avgViews.replace(/\D/g, '')) || 0,
      format,
      hookPattern,
      cta
    });
  }

  console.log('\n── STEP 3: Identify niche-wide patterns ──');

  const topHookPatterns = await ask(
    'What hook patterns keep appearing in top posts?\n' +
    '  (e.g. "myth-busting, before/after transformation, 3 mistakes format")'
  );

  const gaps = await ask(
    'What is NOBODY doing in this niche that could work?\n' +
    '  (e.g. "nobody doing identity-based content, everyone does tips not stories")'
  );

  const avoidPatterns = await ask(
    'What seems oversaturated or underperforming in this niche?'
  );

  const trendingSounds = await ask(
    'Any trending sounds/audio you noticed across multiple top posts? (optional, press Enter to skip)'
  );

  console.log('\n── STEP 4: Strategic angle ──');

  const ourAngle = await ask(
    `Based on what you saw, what's the sharpest angle for ${config.creator.handle || 'your account'}\n` +
    'to stand out? What will you do that competitors aren\'t?'
  );

  // ── SAVE RESULTS ─────────────────────────────────────────────────────────
  const research = {
    scannedAt: new Date().toISOString(),
    niche,
    competitors,
    nicheInsights: {
      topHookPatterns: topHookPatterns.split(',').map(s => s.trim()),
      gaps,
      avoidPatterns,
      trendingSounds: trendingSounds || null,
      ourAngle
    }
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(research, null, 2));

  console.log('\n' + '═'.repeat(60));
  console.log('  RESEARCH COMPLETE');
  console.log('═'.repeat(60));
  console.log(`
Saved to: competitor-research.json

Key findings:
  Best hook patterns: ${topHookPatterns}
  Our gap to fill: ${gaps.substring(0, 80)}...
  Your angle: ${ourAngle.substring(0, 80)}...

This data now feeds into your content generation.
The pipeline will avoid saturated patterns and target your gap.

Run this again weekly or when views drop across multiple posts.
`);

  rl.close();
}

main().catch(err => {
  console.error('Error:', err.message);
  rl.close();
  process.exit(1);
});
