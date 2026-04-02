#!/usr/bin/env node
/**
 * daily-run.js
 * Master orchestrator. Runs the full pipeline each day:
 * analytics → hook scoring → content generation → images → overlays → post
 *
 * Usage: node scripts/daily-run.js [--skip-analytics] [--skip-post]
 */

const { execSync, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, '..', 'config.json');
const SCRIPTS = path.join(__dirname);

function run(script, args = []) {
  console.log(`\n${'─'.repeat(50)}`);
  console.log(`▶ ${script} ${args.join(' ')}`);
  console.log('─'.repeat(50));
  const result = spawnSync('node', [path.join(SCRIPTS, script), ...args], {
    stdio: 'inherit',
    timeout: 900000 // 15 min — image gen can be slow
  });
  if (result.status !== 0) {
    throw new Error(`${script} failed with code ${result.status}`);
  }
}

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    console.error('❌ No config.json found. Run onboarding first:');
    console.error('   node scripts/onboarding.js');
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
}

function today() {
  return new Date().toISOString().split('T')[0];
}

async function main() {
  const args = process.argv.slice(2);
  const skipAnalytics = args.includes('--skip-analytics');
  const skipPost = args.includes('--skip-post');

  const config = loadConfig();

  console.log('\n' + '═'.repeat(50));
  console.log('  CAROUSEL PIPELINE — DAILY RUN');
  console.log(`  ${today()} — ${config.posting.postsPerDay} post(s) queued`);
  console.log('═'.repeat(50));

  // Step 1: Pull analytics from yesterday + connect any unlinked posts
  if (!skipAnalytics) {
    try {
      run('daily-report.js', ['--connect', '--days', '3']);
    } catch (e) {
      console.warn('⚠️  Analytics step failed — continuing anyway.');
      console.warn(e.message);
    }
  }

  // Step 2: Research sweep — scan audience signals before generating content
  // Runs quick if sweep already done today, full scan if not
  try {
    run('research-sweep.js');
  } catch (e) {
    console.warn('⚠️  Research sweep failed — content will use templates only.');
    console.warn(e.message);
  }

  // Step 3: Generate carousel scripts (Carousel Method™ + sweep signals)
  run('generate-carousel.js');

  // Step 4: Generate resource for each carousel (the downloadable the CTA promises)
  run('generate-resource.js');

  // Step 5: Generate AI images
  run('generate-slides.js');

  // Step 6: Add text overlays
  run('add-text-overlay.js');

  // Step 7: Post directly to TikTok + Instagram (no Postiz needed)
  if (!skipPost) {
    run('post-to-platforms.js');
  }

  console.log('\n' + '═'.repeat(50));
  console.log('  ✅ DAILY RUN COMPLETE');
  console.log('═'.repeat(50));
  console.log(`
Posts are live on TikTok and Instagram.
TikTok auto-added trending music — nothing to do manually.

Resources are saved in each post folder as resource.md
Phase 2 (ManyChat DM delivery) will use these when someone comments the CTA word.

Tomorrow morning: analytics run will score today's hooks and improve tomorrow's content.
`);
}

main().catch(err => {
  console.error('\n❌ Daily run failed:', err.message);
  process.exit(1);
});
