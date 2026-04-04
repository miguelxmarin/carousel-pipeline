#!/usr/bin/env node
/**
 * generate-resource.js
 * Builds the downloadable resource promised in slide 9's CTA.
 *
 * KEY PRINCIPLE: The resource must deliver EXACTLY what the carousel promised.
 * It is built from the SPECIFIC content of those slides — the myth that was named,
 * the truth that was revealed, the insights that were delivered.
 * Not generic content about the niche. This specific post's specific promise.
 *
 * Format is chosen from the structure:
 *   myth_truth      → myth breakdown: name the myth, explain the truth, show application
 *   why_youre_stuck → root cause guide: the diagnosis + the fix
 *   micro_lessons   → expanded rules: the 3 rules with full explanation
 *   before_after    → transformation guide: before state → shift → after state
 *   warning_sign    → full checklist: the 3 signs + what to do instead
 *
 * Output: posts/YYYY-MM-DD/HHmm/resource.md
 */

const fs   = require('fs');
const path = require('path');

const ROOT        = path.join(__dirname, '..');
const CONFIG_PATH = path.join(ROOT, 'config.json');
const SWEEP_PATH  = path.join(ROOT, 'research-sweep.json');

function loadJSON(p, def = null) {
  if (fs.existsSync(p)) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return def; } }
  return def;
}
function today() { return new Date().toISOString().split('T')[0]; }

function getTodayPostDirs(config) {
  const postsRoot = path.join(ROOT, config.paths.posts, today());
  if (!fs.existsSync(postsRoot)) return [];
  return fs.readdirSync(postsRoot)
    .map(d => path.join(postsRoot, d))
    .filter(d => fs.statSync(d).isDirectory() && fs.existsSync(path.join(d, 'carousel.json')));
}

// Extract slide text by role from carousel.json
function slide(carousel, role) {
  const s = carousel.slides?.find(s => s.role === role);
  return s?.overlayText?.replace(/\n/g, ' ').replace(/Comment .+ below\..+/i, '').trim() || '';
}

// Pull the N most relevant friction signals from sweep
function frictionSignals(sweep, n = 3) {
  return (sweep?.signals?.friction || [])
    .slice(0, n)
    .map(s => s.text?.slice(0, 120) || '')
    .filter(Boolean);
}

// ── RESOURCE BUILDERS ─────────────────────────────────────────────────────────
// Each builder pulls directly from the carousel's slide content.
// The resource is a deeper version of what the carousel introduced — not a new topic.

function buildMythBreakdown(carousel, sweep, creator) {
  const { hookText, niche, ctaWord } = carousel;
  const mythSlide   = slide(carousel, 'THE MYTH')        || slide(carousel, 'MYTH');
  const truthSlide  = slide(carousel, 'THE TRUTH')       || slide(carousel, 'TRUTH');
  const evidSlide   = slide(carousel, 'EVIDENCE')        || slide(carousel, 'EVIDENCE / LOGIC');
  const applySlide  = slide(carousel, 'APPLICATION')     || '';
  const transSlide  = slide(carousel, 'TRANSFORMATION')  || '';
  const friction    = frictionSignals(sweep, 2);

  return `# The ${ctaWord} Breakdown
*Requested via @${creator.handle || creator.name}*

---

## Why You're Reading This

You commented because this hit: **"${hookText}"**

That's not an accident. Here's what's actually going on — and what to do about it.

---

## The Myth (What Most People Believe)

${mythSlide || `Most people in ${niche} believe that working harder or finding the right strategy is the solution.`}

This belief is everywhere. It's repeated by people who seem to know what they're doing.
${friction[0] ? `\nYou've probably felt it yourself: *"${friction[0]}"*` : ''}

The reason this myth persists: it works just enough, just often enough, to feel true.

---

## The Truth (What's Actually Happening)

${truthSlide || `The real issue isn't what most people focus on. The upstream cause is different.`}

${evidSlide ? `\n${evidSlide}` : ''}

This matters because as long as you're solving the myth, you're solving the wrong problem.
You can work harder, optimize more, and stay just as stuck.

---

## The Application (What To Actually Do)

${applySlide || `The shift isn't doing more of something different. It's questioning the assumption underneath the approach.`}

**Concretely, this means:**

1. Identify what you've been treating as *the* problem (it's probably a symptom)
2. Ask: what's upstream from this? What creates this condition?
3. Address the upstream cause — the downstream problems often resolve on their own

---

## What Changes

${transSlide || `When you apply this, you stop fighting the current. The same effort starts producing different results.`}

Not because you found a trick. Because you're now solving the right problem.

---

*Sent by ${creator.name} | Comment ${ctaWord} under any post for more*`;
}

function buildRootCauseGuide(carousel, sweep, creator) {
  const { hookText, niche, ctaWord } = carousel;
  const symptomSlide  = slide(carousel, 'SYMPTOM');
  const misdiagSlide  = slide(carousel, 'MISDIAGNOSIS');
  const rootSlide     = slide(carousel, 'ROOT CAUSE');
  const insight1      = slide(carousel, 'NEW INSIGHT 1');
  const insight2      = slide(carousel, 'NEW INSIGHT 2');
  const applySlide    = slide(carousel, 'APPLICATION');
  const transSlide    = slide(carousel, 'TRANSFORMATION');
  const friction      = frictionSignals(sweep, 3);

  return `# The ${ctaWord} Guide: Why You're Stuck and How to Get Out
*Requested via @${creator.handle || creator.name}*

---

## The Hook That Brought You Here

"${hookText}"

If that landed — it's because it's describing your actual experience. Let's get specific about why.

---

## What You're Feeling (The Symptom)

${symptomSlide || friction[0] || `You're putting in the effort. You're doing the things. The results aren't matching the input.`}

${friction[1] ? `\nOr maybe: *"${friction[1]}"*` : ''}

You're not imagining it. Something is genuinely off.

---

## What Most People Think The Problem Is (The Misdiagnosis)

${misdiagSlide || `Most people conclude they need more discipline, a better system, or just to try harder.`}

This is the standard advice. It's also why most people stay stuck.
They're treating a symptom, not the cause.

---

## What's Actually Going On (The Root Cause)

${rootSlide || `The real issue is almost always upstream from where the pain shows up.`}

${insight1 ? `\n${insight1}` : ''}

${insight2 ? `\n${insight2}` : ''}

Once you see this, the symptom makes complete sense. And so does the fix.

---

## The Application

${applySlide || `The question to ask: "Am I solving the symptom — or the cause?"`}

Start there. One honest answer to that question is worth more than any new tactic.

---

## What Shifts

${transSlide || `When you address the actual root cause, progress stops feeling like a battle. It starts feeling inevitable.`}

---

*Sent by ${creator.name} | Comment ${ctaWord} under any post for more*`;
}

function buildExpandedRules(carousel, sweep, creator) {
  const { hookText, niche, ctaWord } = carousel;
  const rule1  = slide(carousel, 'RULE 1');
  const rule2  = slide(carousel, 'RULE 2');
  const rule3  = slide(carousel, 'RULE 3');
  const exSlide = slide(carousel, 'EXAMPLES');
  const reinf   = slide(carousel, 'REINFORCEMENT');
  const transSlide = slide(carousel, 'TRANSFORMATION');

  const clean = (s) => s.replace(/^Rule \d+:\s*/i, '').replace(/^[^:]+:\s*/,'').trim();

  return `# The ${ctaWord} Rules: Full Breakdown
*Requested via @${creator.handle || creator.name}*

---

## Why These Rules Work

"${hookText}"

Most ${niche} advice is tactics. These are principles — they change the foundation, not just the approach.

---

## Rule 1: ${clean(rule1) || `Consistency in direction beats intensity in effort`}

**Why it matters:**
Most people flip approaches when they don't see results fast enough. The switching is the problem.
Consistent direction, even with imperfect execution, compounds. Intensity without direction doesn't.

**In practice:**
Pick the one approach most aligned with your actual goal. Commit to it for 30 days.
Track progress. Don't switch. Iterate *within* the approach, not away from it.

---

## Rule 2: ${clean(rule2) || `Clarity about the goal beats clarity about the method`}

**Why it matters:**
Most people are clear on what they're doing and vague about why. This creates effort without progress.
When the goal is specific, the right method becomes obvious. When it's vague, any method seems fine.

**In practice:**
Write down the specific outcome you want from ${niche}. Not "get better" — but the exact measurable state.
Then ask: does my current approach directly produce that outcome? If not, what does?

---

## Rule 3: ${clean(rule3) || `Removing friction works better than adding motivation`}

**Why it matters:**
Motivation is unreliable. Friction removal is structural. One requires willpower. The other doesn't.
The easiest action you'll actually do consistently beats the optimal action you'll do sporadically.

**In practice:**
Find the highest-friction step in your ${niche} practice. Make it 50% easier.
Don't add something new. Remove one obstacle from what already exists.

---

## What This Looks Like Together

${exSlide || `Three rules, one direction: reduce friction, increase clarity, stay consistent.`}

${reinf || `The accounts and people making consistent progress aren't doing more. They're doing these things.`}

---

## The Result

${transSlide || `When you operate from principles instead of tactics, the short-term noise stops mattering. The long game becomes obvious.`}

---

*Sent by ${creator.name} | Comment ${ctaWord} under any post for more*`;
}

function buildTransformationGuide(carousel, sweep, creator) {
  const { hookText, niche, ctaWord } = carousel;
  const beforeSlide = slide(carousel, 'BEFORE STATE');
  const failsSlide  = slide(carousel, 'WHY IT FAILS');
  const shiftSlide  = slide(carousel, 'THE SHIFT');
  const after1      = slide(carousel, 'AFTER STATE 1');
  const after2      = slide(carousel, 'AFTER STATE 2');
  const exSlide     = slide(carousel, 'EXAMPLE');
  const transSlide  = slide(carousel, 'TRANSFORMATION');

  return `# The ${ctaWord} Path: From Before to After
*Requested via @${creator.handle || creator.name}*

---

## The Starting Point

"${hookText}"

If you're here, you recognize the before. Let's map the whole path.

---

## The Before State

${beforeSlide || `Doing the right things. Following the advice. Not seeing the results that should be there.`}

This isn't a failure of effort. It's a failure of direction. Different problem.

---

## Why The Current Approach Isn't Working

${failsSlide || `The effort is real. The approach is misaligned with the actual outcome.`}

The frustrating part: most advice about ${niche} optimizes the *approach* without questioning the *direction*.
Working harder on a misaligned path doesn't close the gap. It widens it.

---

## The Shift

${shiftSlide || `The change isn't doing something different. It's asking a different question first.`}

The question isn't *"how do I do this better?"*
It's *"am I doing the thing that actually produces the outcome I want?"*

That one shift changes everything downstream.

---

## The After State

${after1 || `Progress starts feeling consistent instead of random.`}

${after2 || `Not because everything is easier — because the right thing is finally clear.`}

The same effort. Different direction. Completely different results.

---

## What This Looks Like In Practice

${exSlide || `The path from before to after is almost always shorter than it looked from the before side.`}

---

## The Outcome

${transSlide || `Once you make the shift, you stop asking "why isn't this working." You already know. And you already know what to do.`}

---

*Sent by ${creator.name} | Comment ${ctaWord} under any post for more*`;
}

function buildWarningChecklist(carousel, sweep, creator) {
  const { hookText, niche, ctaWord } = carousel;
  const sign1     = slide(carousel, 'SIGN 1');
  const why1      = slide(carousel, 'WHY 1');
  const sign2     = slide(carousel, 'SIGN 2');
  const why2      = slide(carousel, 'WHY 2');
  const sign3     = slide(carousel, 'SIGN 3');
  const whatToDo  = slide(carousel, 'WHAT TO DO');
  const transSlide = slide(carousel, 'TRANSFORMATION');

  const clean = (s) => s.replace(/^Sign \d+:\s*/i, '').replace(/^[^:]+:\s*/,'').trim();

  return `# The ${ctaWord} Checklist
*Requested via @${creator.handle || creator.name}*

---

## The Prompt

"${hookText}"

If you recognized yourself — this checklist is for you. Not as a judgment. As a diagnostic.

---

## The 3 Signs (Full Breakdown)

### Sign 1: ${clean(sign1) || `Measuring the wrong things`}

${why1 || `This keeps effort high and results low.`}

**The fix:** Identify what you're actually measuring. Ask if that metric directly connects to your real goal. If not — change the metric, not the effort.

---

### Sign 2: ${clean(sign2) || `Optimizing for the wrong outcome`}

${why2 || `This one is subtle, but it compounds.`}

**The fix:** Write down the specific outcome you want. Now look at your last 5 actions in ${niche}. How many directly produce that outcome? Realign.

---

### Sign 3: ${clean(sign3) || `Waiting for motivation instead of building systems`}

**Why it matters:** Motivation follows action. It doesn't precede it. Waiting for motivation is a structural choice to stay stuck.

**The fix:** Design the smallest possible version of the action — one that requires no motivation to start. Do that. The motivation shows up after.

---

## The Alternative

${whatToDo || `The alternative isn't more. It's different. Specifically: address the sign that resonates most with where you are right now.`}

Don't try to fix all three today. Pick the one that feels most true and address that one first.

---

## The Result

${transSlide || `Once you stop doing the signs, the effort you were already putting in starts producing different results.`}

---

## Quick Diagnostic

- [ ] I know specifically what outcome I'm optimizing for in ${niche} (not vague — measurable)
- [ ] My last 5 actions directly produce that outcome
- [ ] I'm not waiting to "feel ready" before starting
- [ ] I have removed at least one friction point in the last 30 days

If fewer than 3 are checked — the signs are active. Start with the first unchecked one.

---

*Sent by ${creator.name} | Comment ${ctaWord} under any post for more*`;
}

// ── MAIN ──────────────────────────────────────────────────────────────────────

function buildResource(carousel, sweep, creator) {
  const { structureKey } = carousel;
  switch (structureKey) {
    case 'myth_truth':      return { format: 'myth_breakdown',       content: buildMythBreakdown(carousel, sweep, creator) };
    case 'why_youre_stuck': return { format: 'root_cause_guide',     content: buildRootCauseGuide(carousel, sweep, creator) };
    case 'micro_lessons':   return { format: 'expanded_rules',       content: buildExpandedRules(carousel, sweep, creator) };
    case 'before_after':    return { format: 'transformation_guide', content: buildTransformationGuide(carousel, sweep, creator) };
    case 'warning_sign':    return { format: 'warning_checklist',    content: buildWarningChecklist(carousel, sweep, creator) };
    default:                return { format: 'root_cause_guide',     content: buildRootCauseGuide(carousel, sweep, creator) };
  }
}

async function main() {
  const config = loadJSON(CONFIG_PATH);
  if (!config) { console.error('❌ No config.json.'); process.exit(1); }

  const sweep    = loadJSON(SWEEP_PATH);
  const postDirs = getTodayPostDirs(config);
  if (!postDirs.length) { console.error('❌ No posts for today. Run generate-carousel.js first.'); process.exit(1); }

  console.log(`\n📄 Building resources for ${postDirs.length} post(s)...\n`);

  for (const dir of postDirs) {
    const carousel = loadJSON(path.join(dir, 'carousel.json'));
    if (!carousel) { console.warn(`   ⚠️  No carousel.json in ${dir}`); continue; }

    const resourcePath = path.join(dir, 'resource.md');
    if (fs.existsSync(resourcePath)) { console.log(`   ⏭  ${path.basename(dir)}: resource exists`); continue; }

    const { format, content } = buildResource(carousel, sweep, config.creator);
    fs.writeFileSync(resourcePath, content);
    fs.writeFileSync(path.join(dir, 'resource-meta.json'), JSON.stringify({
      generatedAt: new Date().toISOString(),
      format,
      ctaWord:     carousel.ctaWord,
      hookText:    carousel.hookText,
      structureKey: carousel.structureKey
    }, null, 2));

    console.log(`   ✅ ${path.basename(dir)}: ${format}`);
    console.log(`      Hook: "${carousel.hookText?.slice(0, 60)}..."`);
    console.log(`      CTA word: "${carousel.ctaWord}"\n`);
  }

  console.log('✅ Resources complete — saved as resource.md in each post folder.');
  console.log('Phase 2 (ManyChat) will deliver these when someone comments the CTA word.');
}

main().catch(err => { console.error('\n❌ Resource generation failed:', err.message); process.exit(1); });
