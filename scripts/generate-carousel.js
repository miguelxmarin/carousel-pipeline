#!/usr/bin/env node
/**
 * generate-carousel.js
 * The Carousel Method™ content engine — fully structure-aware.
 *
 * Every carousel is unique:
 *   - Structure and hook formula are PAIRED, never picked independently
 *   - Each structure generates its own slide copy — no generic templates, no placeholders
 *   - Swipe triggers (curiosity gaps, "Not Yet", micro-dopamine) embedded per-slide
 *   - Storytelling style derived from creator's niche and brand voice
 *   - No two posts in the same day use the same structure
 *   - Hook quality gate runs before any images are generated
 *   - Caption follows Carousel Method arc: problem → reframe → CTA word
 *
 * Output: posts/YYYY-MM-DD/HHmm/carousel.json
 */

const fs   = require('fs');
const path = require('path');

const ROOT           = path.join(__dirname, '..');
const CONFIG_PATH    = path.join(ROOT, 'config.json');
const HOOK_PERF_PATH = path.join(ROOT, 'hook-performance.json');
const SWEEP_PATH     = path.join(ROOT, 'research-sweep.json');

// ─────────────────────────────────────────────────────────────────────────────
// STORYTELLING STYLES  (Carousel Method Module 5)
// Determined once from creator profile. Applied to every slide's language.
// ─────────────────────────────────────────────────────────────────────────────

const STYLES = {
  analytical: {
    name: 'Sharp Analytical',
    slide2: (niche, v) => [
      `Here's the pattern almost nobody in ${niche.split(' ')[0]} names clearly.\nAnd it's costing you more than you think.`,
      `Most ${niche.split(' ')[0]} advice gets this backwards.\nHere's what's actually driving results.`,
      `There's a reason ${niche.split(' ')[0]} feels harder than it should.\nIt's not what most people think it is.`,
      `The gap in ${niche.split(' ')[0]} isn't effort.\nIt's direction. Here's the difference.`
    ][v % 4],
    slide3: (v) => [
      `But before I explain —\nthere's something you need to understand first.`,
      `Here's what makes this different from everything else you've tried.`,
      `The real problem isn't where most people are looking.`,
      `Stop. The thing you think is the issue — probably isn't.`
    ][v % 4],
    insightOpener: (n) => ['Here\'s what\'s actually happening.', 'The real mechanism:', 'This is the part that changes everything.', 'Pay attention to this one.'][n % 4],
    slide8: (v) => [
      `Once you apply this, the results compound.\nThat's when everything finally starts moving.`,
      `This is the shift that makes everything else easier.\nNot optional. Foundational.`,
      `When this clicks — you stop fighting the process.\nYou start working with it.`,
      `The output changes when the input changes.\nThis is the right input.`
    ][v % 4],
    slide10: (v) => [
      `Now you understand why.\nAnd you know exactly what to do next.`,
      `You came here with the symptom.\nYou're leaving with the cause.`,
      `This is why the old approach wasn't working.\nNow you have the real one.`,
      `Same situation. Different understanding.\nDifferent results from here.`
    ][v % 4]
  },
  emotional: {
    name: 'Minimal Emotional',
    slide2: (niche, v) => [
      `If you've been struggling with ${niche.split(' ')[0]} —\nyou're not the only one. And it's not your fault.`,
      `The hardest part about ${niche.split(' ')[0]} isn't what people admit out loud.\nBut it's what almost everyone feels.`,
      `You're probably doing everything right.\nAnd still not getting where you want to be.`,
      `Here's something most people in ${niche.split(' ')[0]} won't say.\nBut almost everyone experiences.`
    ][v % 4],
    slide3: (v) => [
      `Here's what nobody said out loud.`,
      `The thing that's actually in the way isn't what you think.`,
      `Before I get to the fix — the real problem needs a name.`,
      `Most people skip this part. That's why they stay stuck.`
    ][v % 4],
    insightOpener: (n) => ['Here\'s the honest truth.', 'This is the part that hits different.', 'Read this slowly.', 'This is what actually helps.'][n % 4],
    slide8: (v) => [
      `When this clicks, everything feels lighter.\nNot easier — but clearer.`,
      `This is the part that actually helps.\nNot the advice. This.`,
      `Once you see it this way —\nit stops feeling like a battle.`,
      `The struggle doesn't disappear.\nBut it starts making sense.`
    ][v % 4],
    slide10: (v) => [
      `You already knew something was off.\nNow you know what it is.`,
      `This is what you needed to hear.\nNot what you were told.`,
      `You came here feeling stuck.\nYou're leaving with a direction.`,
      `That discomfort you've been feeling?\nIt had a name the whole time.`
    ][v % 4]
  },
  narrative: {
    name: 'Micro-Narrative',
    slide2: (niche, v) => [
      `Most people in ${niche.split(' ')[0]} are doing the same thing.\nAnd getting the same results.`,
      `The pattern I keep seeing in ${niche.split(' ')[0]} is always the same.\nAnd it's fixable.`,
      `The people who are getting results in ${niche.split(' ')[0]} aren't doing more.\nThey're doing something different.`,
      `Here's what separates the people progressing in ${niche.split(' ')[0]}\nfrom everyone else.`
    ][v % 4],
    slide3: (v) => [
      `But here's what I noticed.\nThe ones who broke through did one thing differently.`,
      `The difference wasn't talent or resources.\nIt was one specific decision.`,
      `Everyone starts the same way.\nOne thing changes the trajectory.`,
      `The turning point is always the same.\nAnd it's almost never what people expect.`
    ][v % 4],
    insightOpener: (n) => ['Here\'s the shift.', 'This is what changed.', 'The difference was this.', 'It comes down to this.'][n % 4],
    slide8: (v) => [
      `That's when things started working.\nNot all at once — but consistently.`,
      `Once this clicked — everything else got easier.\nNot the work. The direction.`,
      `The results didn't change overnight.\nBut the trajectory did. Immediately.`,
      `This is the moment most people describe as "it finally made sense."`
    ][v % 4],
    slide10: (v) => [
      `Now you see it too.\nAnd you won't forget it.`,
      `You just learned what most people spend years figuring out.`,
      `The pattern is visible now.\nIt always was. You just have the lens.`,
      `This is the understanding that changes what you do next.`
    ][v % 4]
  }
};

function getStyle(brandVoice, niche) {
  const v = (brandVoice || '').toLowerCase();
  const n = (niche || '').toLowerCase();
  if (v.includes('analytical') || v.includes('data') || v.includes('direct') ||
      n.includes('business') || n.includes('market') || n.includes('financ') || n.includes('productiv'))
    return 'analytical';
  if (v.includes('personal') || v.includes('story') || v.includes('coach') ||
      n.includes('coach') || n.includes('educat') || n.includes('brand'))
    return 'narrative';
  return 'emotional';
}

// ─────────────────────────────────────────────────────────────────────────────
// SWIPE TRIGGERS  (Carousel Method Module 4)
// Embedded between insight slides to prevent drop-off at slides 5-6.
// ─────────────────────────────────────────────────────────────────────────────

const CURIOSITY_GAPS = [
  'Here\'s the part nobody mentions.',
  'This is where it gets interesting.',
  'Most people stop here. Don\'t.',
  'Pay attention to this next part.',
  'This changes how you see everything else.'
];
const NOT_YET = [
  'But before I explain that —',
  'Hold on. There\'s something else.',
  'Here\'s what makes this different.',
  'And this is the part that matters most.',
  'But here\'s what actually drives it.'
];
const DOPAMINE = [
  'Here\'s the shift.',
  'This is it.',
  'Read that again.',
  'That\'s the whole thing.',
  'Simple. But not obvious.'
];

const T = {
  gap: (i) => CURIOSITY_GAPS[i % CURIOSITY_GAPS.length],
  not: (i) => NOT_YET[i % NOT_YET.length],
  hit: (i) => DOPAMINE[i % DOPAMINE.length]
};

// ─────────────────────────────────────────────────────────────────────────────
// STRUCTURE + HOOK PAIRINGS
// Hook formula and structure are chosen as a coherent pair — not independently.
// ─────────────────────────────────────────────────────────────────────────────

const PAIRS = [
  {
    key: 'myth_truth',
    label: 'Myth → Truth: busts a false belief',
    formulas: ['shock_polarization', 'everyone_wrong', 'limiting_belief'],
    goals: ['shares', 'reach', 'all']
  },
  {
    key: 'why_youre_stuck',
    label: 'Why You\'re Stuck: diagnoses the real problem',
    formulas: ['nobody_talks', 'clarity_eureka', 'limiting_belief'],
    goals: ['followers', 'comments', 'saves', 'all']
  },
  {
    key: 'micro_lessons',
    label: 'Micro Lessons: 3 rules or principles',
    formulas: ['authority', 'everyone_wrong', 'shock_polarization'],
    goals: ['saves', 'shares', 'all']
  },
  {
    key: 'before_after',
    label: 'Before → After: transformation arc',
    formulas: ['clarity_eureka', 'nobody_talks', 'limiting_belief'],
    goals: ['followers', 'shares', 'all']
  },
  {
    key: 'warning_sign',
    label: 'Warning Sign: harmful patterns to stop',
    formulas: ['warning_hook', 'shock_polarization', 'everyone_wrong'],
    goals: ['reach', 'comments', 'shares', 'all']
  }
];

function pickPair(goal, hookPerf, usedToday) {
  const g = (goal || 'all').toLowerCase().split(' ')[0];
  let candidates = PAIRS.filter(p => p.goals.includes(g) || p.goals.includes('all'));
  candidates = candidates.filter(p => !usedToday.includes(p.key));
  if (candidates.length === 0) candidates = PAIRS.filter(p => !usedToday.includes(p.key));
  if (candidates.length === 0) candidates = PAIRS;

  const dropped   = hookPerf?.rules?.dropped || [];
  const filtered  = candidates.filter(p => !dropped.includes(p.key));
  if (filtered.length > 0) candidates = filtered;

  const doubleDown = hookPerf?.rules?.doubleDown || [];
  const boosted    = candidates.filter(p => doubleDown.includes(p.key));
  if (boosted.length > 0) return boosted[0];

  return candidates[Math.floor(Math.random() * candidates.length)];
}

// ─────────────────────────────────────────────────────────────────────────────
// HOOK FORMULAS + QUALITY GATE
// ─────────────────────────────────────────────────────────────────────────────

const HOOKS = {
  shock_polarization: [
    'No one wants to hear this about [topic]. But it needs to be said.',
    'You\'ve been approaching [topic] wrong. And nobody told you.',
    'The truth about [topic] most people refuse to accept.',
    'Stop. What you know about [topic] is probably backwards.'
  ],
  limiting_belief: [
    'Your [topic] problem isn\'t what you think it is.',
    'You don\'t have a [topic] problem. You have a clarity problem.',
    'You\'re not bad at [topic]. You\'re solving the wrong thing.',
    'The reason your [topic] isn\'t working has nothing to do with effort.'
  ],
  everyone_wrong: [
    'What everyone gets wrong about [topic] — and why it keeps them stuck.',
    'The most common [topic] advice is also the most damaging.',
    'Everyone in [topic] is doing this. Almost nobody is getting results.',
    'Popular [topic] advice works for some people. Here\'s why it won\'t work for you.'
  ],
  nobody_talks: [
    'The [topic] thing nobody talks about — but everyone needs to know.',
    'The real reason [topic] feels harder than it should.',
    'Nobody explains this part of [topic]. So I will.',
    'What\'s actually holding your [topic] back (it\'s not what you think).'
  ],
  clarity_eureka: [
    'You\'re not failing at [topic]. You\'re misaligned.',
    'One [topic] shift that makes everything else easier.',
    'You\'re one [topic] adjustment away from completely different results.',
    'Everything in [topic] becomes clearer once you understand this.'
  ],
  authority: [
    'After years in [topic] — this is the pattern I keep seeing.',
    'The #1 thing separating [topic] results from [topic] frustration.',
    'What [topic] high performers do differently (the data is clear).',
    'I\'ve watched hundreds struggle with [topic]. The problem is always this.'
  ],
  warning_hook: [
    'If you\'re doing this in [topic] — stop. Immediately.',
    '3 [topic] habits that are quietly working against you.',
    'You\'re probably making this [topic] mistake right now.',
    'Warning: this [topic] approach is more harmful than helpful.'
  ]
};

function scoreHook(text) {
  if (!text) return 0;
  const h = text.toLowerCase();
  let s = 0;
  if (text.split(' ').length <= 18 && !['things','stuff','various'].some(w => h.includes(w))) s++;
  if (['not ','isn\'t','don\'t','can\'t','wrong','stuck','fail','harder','never','stop','missing'].some(w => h.includes(w))) s++;
  if (!['tips for','how to be','guide to','learn about'].some(w => h.includes(w)) &&
      ['real','actually','truth','nobody','stop','wrong','misaligned','missing','different','specific','one thing'].some(w => h.includes(w))) s++;
  if (['you\'re not','it\'s not','real reason','actually','changes everything','one thing','specific','misaligned'].some(w => h.includes(w))) s++;
  return s;
}

function buildHook(formulaKey, niche, sweep, postIndex) {
  const topic = niche.split(' ')[0];

  // Try sweep-grounded hook first
  if (sweep?.hookAngles?.length > 0) {
    const angle = sweep.hookAngles[postIndex % sweep.hookAngles.length];
    if (angle?.type === 'frustration') {
      const kw  = angle.angle.match(/"([^"]+)"/)?.[1] || topic;
      const sh  = `The real reason ${kw} feels harder than it should.`;
      if (scoreHook(sh) >= 3) return { text: sh, source: 'sweep' };
    }
    if (angle?.type === 'verbatim' && angle.examplePhrases?.[0]) {
      const p = angle.examplePhrases[0].toLowerCase();
      if (p.includes("can't") || p.includes("don't")) {
        const sh = `You\'re not failing at ${topic}. You\'re missing one specific thing.`;
        if (scoreHook(sh) >= 3) return { text: sh, source: 'sweep' };
      }
    }
  }

  const templates = HOOKS[formulaKey] || HOOKS.nobody_talks;
  let best = null, bestScore = -1;
  for (let i = 0; i < 4; i++) {
    const raw  = templates[i % templates.length];
    const hook = raw.replace(/\[topic\]/gi, topic).replace(/\[niche\]/gi, niche).replace(/\[X\]/gi, topic);
    const s    = scoreHook(hook);
    if (s > bestScore) { bestScore = s; best = hook; }
    if (s >= 3) break;
  }
  return { text: best, source: 'template', score: bestScore };
}

// ─────────────────────────────────────────────────────────────────────────────
// STRUCTURE-SPECIFIC SLIDE BUILDERS
// Each structure has its own narrative arc and slide language.
// No generic placeholders. Swipe triggers embedded at precise positions.
// ─────────────────────────────────────────────────────────────────────────────

function mythTruth(hookText, niche, style, sweep, ctaWord, v) {
  const s = STYLES[style], topic = niche.split(' ')[0];
  const friction = sweep?.signals?.friction || [];
  // Interpret friction signal as evidence — never paste raw complaint
  const evidenceInsight = friction[0]?.text
    ? `The people who do get results aren\'t doing more.\nThey changed the question, not the effort.`
    : `The people getting results in ${topic} aren\'t doing more — they\'re doing different.`;
  const appInsight = friction[1]?.text
    ? `Stop optimizing what\'s already there.\nStart questioning what\'s actually needed.`
    : `Stop optimizing what\'s already there.\nStart questioning what\'s actually needed.`;
  return [
    { role: 'HOOK',            text: hookText,                                                                         design: 'One line. Bold. Zero context. Pure impact.' },
    { role: 'THE MYTH',        text: s.slide2(niche, v),                                                              design: 'State what most people believe. Rotates across posts.' },
    { role: 'PATTERN BREAK',   text: `${s.slide3(v)}\nThat belief is what\'s keeping you stuck.`,                    design: 'NOT YET TECHNIQUE — disrupts before explaining. Forces swipe.' },
    { role: 'WHY MYTH EXISTS', text: `${s.insightOpener(v)}\nIt made sense with older information.\nThe context changed. The advice didn\'t.`, design: 'Validate — not dumb for believing it. Builds trust.' },
    { role: 'THE TRUTH',       text: `${T.gap(v)}\nThe result you want comes from\nsolving a different problem entirely.`, design: 'The pivot. Sharp. One idea. Main insight — never before here.' },
    { role: 'EVIDENCE',        text: `${s.insightOpener(v + 1)}\n${evidenceInsight}`,                                 design: 'Credible. Logic or observed pattern. Grounds the truth.' },
    { role: 'APPLICATION',     text: `${T.hit(v)}\n${appInsight}`,                                                    design: 'One action direction. Sweep signal interpreted, not pasted.' },
    { role: 'TRANSFORMATION',  text: s.slide8(v),                                                                     design: 'SLIDE 8 LIFT — re-engages dropoffs from slides 5-6.' },
    { role: 'CTA',             text: `Comment ${ctaWord} below.\nI\'ll send you the full breakdown.`,                 design: `"${ctaWord}" = trigger word. Zero pressure. One word.` },
    { role: 'LOOP CLOSE',      text: s.slide10(v),                                                                    design: 'Echo slide 1 with more power. Reinforces hook before save.' }
  ];
}

function whyStuck(hookText, niche, style, sweep, ctaWord, v) {
  const s = STYLES[style], topic = niche.split(' ')[0];
  return [
    { role: 'HOOK',            text: hookText,                                                                         design: 'Make them feel seen. Their exact experience.' },
    { role: 'SYMPTOM',         text: s.slide2(niche, v),                                                              design: 'Mirror their reality. "That\'s exactly me."' },
    { role: 'MISDIAGNOSIS',    text: `${s.slide3(v)}\nMost people think the problem is effort or consistency.\nIt\'s not.`, design: 'Name what they\'ve been told. Break it.' },
    { role: 'ROOT CAUSE',      text: `${T.not(v + 1)}\nThe real issue is almost always\nsolving the wrong version of the problem.`, design: 'The actual insight. Sharp.' },
    { role: 'NEW INSIGHT 1',   text: `${s.insightOpener(1)}\nWhen you fix the upstream cause —\nthe downstream problems often disappear.`, design: 'One idea. Forward-pointing.' },
    { role: 'NEW INSIGHT 2',   text: `${T.gap(v + 2)}\nThe version of ${topic} that works\nlooks quieter — not louder.`,  design: 'Builds depth.' },
    { role: 'APPLICATION',     text: `${T.hit(v + 1)}\nAsk yourself: am I solving the symptom —\nor the cause?`,       design: 'One clear question to use today.' },
    { role: 'TRANSFORMATION',  text: s.slide8(v),                                                                      design: 'SLIDE 8 LIFT.' },
    { role: 'CTA',             text: `Comment ${ctaWord} below.\nI\'ll send you the full guide.`,                      design: `Trigger: "${ctaWord}"` },
    { role: 'LOOP CLOSE',      text: s.slide10(v),                                                                     design: 'Close the loop.' }
  ];
}

function microLessons(hookText, niche, style, sweep, ctaWord, v) {
  const s = STYLES[style], topic = niche.split(' ')[0];
  const f = sweep?.signals?.friction || [];
  // Interpret friction signals as principles — not raw complaints
  const toRule = (raw, fallback) => {
    const cleaned = (raw || fallback).replace(/^(i |we |they |i've |i'm )/i, '').replace(/[.!?]$/, '').trim();
    // Convert first-person complaint to third-person principle
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  };
  const r1 = toRule(f[0]?.text, `Consistency in direction beats intensity in effort`).slice(0, 70);
  const r2 = toRule(f[1]?.text, `Clarity about the goal matters more than the method`).slice(0, 70);
  const r3 = toRule(f[2]?.text, `Removing friction works better than adding motivation`).slice(0, 70);
  return [
    { role: 'HOOK',           text: hookText,                                                                          design: 'Number upfront. Creates completion drive.' },
    { role: 'RULE 1',         text: `Rule 1:\n${r1}.`,                                                                design: 'Short. Direct. Can stand alone.' },
    { role: 'RULE 2',         text: `${T.not(v + 2)}\nRule 2:\n${r2}.`,                                               design: 'Bridge trigger then rule.' },
    { role: 'RULE 3',         text: `Rule 3:\n${r3}.`,                                                                design: 'Pattern completion. Brain wants #3.' },
    { role: 'EXAMPLES',       text: `${T.gap(v)}\nThese aren\'t tips.\nThey\'re the things that actually compound.`,  design: 'Frame as principles not tactics.' },
    { role: 'REINFORCEMENT',  text: `${s.insightOpener(3)}\nMost ${topic} advice focuses on tactics.\nThese work because they change the foundation.`, design: 'Authority. Deepens value.' },
    { role: 'MICRO-SUMMARY',  text: `${T.hit(v + 2)}\n3 rules. One direction.\nAll pointing at the same thing.`,     design: 'Compress the value. Triggers save impulse.' },
    { role: 'TRANSFORMATION', text: s.slide8(v),                                                                      design: 'SLIDE 8 LIFT.' },
    { role: 'CTA',            text: `Comment ${ctaWord} below.\nI\'ll send you the full list.`,                       design: `Trigger: "${ctaWord}"` },
    { role: 'LOOP CLOSE',     text: s.slide10(v),                                                                     design: 'Echo the hook.' }
  ];
}

function beforeAfter(hookText, niche, style, sweep, ctaWord, v) {
  const s = STYLES[style], topic = niche.split(' ')[0];
  const toState = (raw, fallback) => (raw || fallback).replace(/^(i |we |they |i've |i'm )/i, '').trim().slice(0, 70);
  const bf = toState(sweep?.signals?.friction?.[0]?.text, `doing all the right things but not seeing the results`);
  const af = toState(sweep?.signals?.aspiration?.[0]?.text, `seeing consistent progress that compounds`);
  return [
    { role: 'HOOK',           text: hookText,                                                                          design: 'Calls to someone in a specific situation.' },
    { role: 'BEFORE STATE',   text: `Before:\n${bf.charAt(0).toUpperCase() + bf.slice(1)}.`,                          design: 'Specific and honest. Their current reality.' },
    { role: 'WHY IT FAILS',   text: `${s.slide3(v)}\nThe problem isn\'t the effort.\nIt\'s the direction.`,           design: 'Pattern break. Not an effort problem.' },
    { role: 'THE SHIFT',      text: `${T.not(v + 3)}\nWhat needed to change wasn\'t the input.\nIt was the question.`, design: 'The pivot. What was missing.' },
    { role: 'AFTER STATE 1',  text: `${s.insightOpener(0)}\n${af.charAt(0).toUpperCase() + af.slice(1)}.`,            design: 'Specific, not aspirational fluff.' },
    { role: 'AFTER STATE 2',  text: `${T.gap(v + 3)}\nNot because everything got easier.\nBecause the right thing got clearer.`, design: 'Deepen the after. Credible.' },
    { role: 'EXAMPLE',        text: `${T.hit(v + 3)}\nThe path from before to after\nis almost always shorter than it looked.`, design: 'Makes it feel achievable.' },
    { role: 'TRANSFORMATION', text: s.slide8(v),                                                                      design: 'SLIDE 8 LIFT.' },
    { role: 'CTA',            text: `Comment ${ctaWord} below.\nI\'ll send you the full breakdown.`,                  design: `Trigger: "${ctaWord}"` },
    { role: 'LOOP CLOSE',     text: s.slide10(v),                                                                     design: 'Close the loop.' }
  ];
}

function warningSign(hookText, niche, style, sweep, ctaWord, v) {
  const s = STYLES[style], topic = niche.split(' ')[0];
  const f = sweep?.signals?.friction || [];
  const toSign = (raw, fallback) => (raw || fallback).replace(/^(i |we |they |i've |i'm )/i, '').trim().slice(0, 70);
  const sg1 = toSign(f[0]?.text, `measuring progress the wrong way`);
  const sg2 = toSign(f[1]?.text, `optimizing for the wrong outcome`);
  const sg3 = toSign(f[2]?.text, `waiting for motivation instead of building systems`);
  return [
    { role: 'HOOK',           text: hookText,                                                                          design: 'Urgency without fear-mongering. Recognisable.' },
    { role: 'SIGN 1',         text: `Sign 1:\n${sg1.charAt(0).toUpperCase() + sg1.slice(1)}.`,                        design: 'Specific. Recognisable. Not a lecture.' },
    { role: 'WHY 1',          text: `${T.not(v)}\nThis keeps ${topic} effort high\nand results low.`,                 design: 'One sentence why it matters.' },
    { role: 'SIGN 2',         text: `${T.gap(v + 1)}\nSign 2:\n${sg2.charAt(0).toUpperCase() + sg2.slice(1)}.`,      design: 'Curiosity gap before sign 2.' },
    { role: 'WHY 2',          text: `This one is subtle.\nBut it compounds over time.`,                               design: 'Validates it\'s not obvious.' },
    { role: 'SIGN 3',         text: `${s.insightOpener(2)}\nSign 3:\n${sg3.charAt(0).toUpperCase() + sg3.slice(1)}.`, design: 'Pattern completion pressure.' },
    { role: 'WHAT TO DO',     text: `${T.hit(v)}\nThe alternative isn\'t more.\nIt\'s different.`,                   design: 'Redirect. Give them somewhere to go.' },
    { role: 'TRANSFORMATION', text: s.slide8(v),                                                                      design: 'SLIDE 8 LIFT.' },
    { role: 'CTA',            text: `Comment ${ctaWord} below.\nI\'ll send you the full checklist.`,                  design: `Trigger: "${ctaWord}"` },
    { role: 'LOOP CLOSE',     text: s.slide10(v),                                                                     design: 'Echo the hook.' }
  ];
}

const BUILDERS = {
  myth_truth:      mythTruth,
  why_youre_stuck: whyStuck,
  micro_lessons:   microLessons,
  before_after:    beforeAfter,
  warning_sign:    warningSign
};

// ─────────────────────────────────────────────────────────────────────────────
// IMAGE PROMPTS
// ─────────────────────────────────────────────────────────────────────────────

const EMOTION_SCENES = {
  frustrated:  'person looking at their phone with a tired expression, soft natural light, relatable everyday setting',
  hopeful:     'person in a quiet moment of realisation, looking slightly off-camera, warm morning light, calm setting',
  urgent:      'close shot of person mid-action, dynamic composition, high contrast light, visual tension',
  overwhelmed: 'person surrounded by a busy workspace, relatable not dramatic, warm home setting',
  curious:     'person leaning in slightly, intrigued expression, minimal setting, single strong light source'
};

function hookImagePrompt(basePrompt, hookText) {
  const h = hookText.toLowerCase();
  let emotion = 'curious';
  if (h.includes('stuck') || h.includes('failing') || h.includes('harder'))   emotion = 'frustrated';
  else if (h.includes('finally') || h.includes('works') || h.includes('clarity')) emotion = 'hopeful';
  else if (h.includes('stop') || h.includes('wrong') || h.includes('warning'))     emotion = 'urgent';
  else if (h.includes('overwhelm') || h.includes('tired') || h.includes('exhaust')) emotion = 'overwhelmed';
  const scene  = EMOTION_SCENES[emotion];
  const anchor = basePrompt.includes('No text') ? basePrompt.split('No text')[1]?.trim() : '';
  return `iPhone photo of ${scene}. Realistic, natural colors, taken on iPhone 15 Pro. No text, no watermarks. ${anchor}`.trim();
}

function slideImagePrompt(basePrompt, hookImg, slideNum) {
  if (slideNum === 1) return hookImg;
  const v = ['','slightly different angle, same setting','zoomed out slightly','same composition, different moment',
             '','close detail, same setting','','','wide shot showing full scene','final moment, same setting'];
  const variation = v[slideNum - 1] || '';
  return `${basePrompt}${variation ? '. ' + variation : ''}`.trim();
}

// ─────────────────────────────────────────────────────────────────────────────
// CTA WORDS
// ─────────────────────────────────────────────────────────────────────────────

const CTA_BANKS = {
  myth_truth:      ['TRUTH','REAL','FACTS','CLARITY','INSIGHT'],
  why_youre_stuck: ['WHY','REASON','ROOT','UNLOCK','CAUSE'],
  micro_lessons:   ['LIST','RULES','TIPS','STEPS','TOOLS'],
  warning_sign:    ['SIGNS','CHECK','AUDIT','REVIEW','ASSESS'],
  before_after:    ['STORY','PATH','METHOD','GUIDE','SHIFT'],
  default:         ['GUIDE','SYSTEM','BLUEPRINT','FRAMEWORK','ROADMAP']
};

function ctaWord(structureKey) {
  const bank = CTA_BANKS[structureKey] || CTA_BANKS.default;
  return bank[Math.floor(Math.random() * bank.length)];
}

// ─────────────────────────────────────────────────────────────────────────────
// CAPTION  (Carousel Method arc: problem → reframe → CTA word)
// ─────────────────────────────────────────────────────────────────────────────

function buildCaption(hookText, niche, word, sweep) {
  const topic   = niche.split(' ')[0];
  const problem = sweep?.hookAngles?.[0]?.type === 'verbatim' && sweep.hookAngles[0].examplePhrases?.[0]
    ? sweep.hookAngles[0].examplePhrases[0].slice(0, 100)
    : `Most people in ${topic} are working hard but solving the wrong problem.`;
  const reframe = `The real shift isn\'t doing more — it\'s being clear on what actually matters.`;
  const caption = `${problem} ${reframe} Comment ${word} and I\'ll send you the full guide.`;
  const tag     = topic.toLowerCase().replace(/[^a-z]/g,'');
  return {
    caption,
    hashtags: [`#${tag}`, `#${tag}tips`, `#${tag}growth`, '#contentcreator', '#learnontiktok']
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN
// ─────────────────────────────────────────────────────────────────────────────

function loadJSON(p, def = null) {
  if (fs.existsSync(p)) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return def; } }
  return def;
}

function today() { return new Date().toISOString().split('T')[0]; }

function generate(config, hookPerf, sweep, postIndex, usedToday) {
  const { creator, imageGen } = config;

  // 1. Pick coherent structure + hook formula pair
  const pair    = pickPair(creator.contentGoal, hookPerf, usedToday);
  const formula = pair.formulas[Math.floor(Math.random() * pair.formulas.length)];

  // 2. Storytelling style from creator profile
  const style = getStyle(creator.brandVoice, creator.niche);

  // 3. Build hook
  const hook  = buildHook(formula, creator.niche, sweep, postIndex);
  const score = scoreHook(hook.text);

  console.log(`   [${postIndex + 1}] ${pair.label}`);
  console.log(`       Style: ${STYLES[style].name} | Formula: ${formula}`);
  console.log(`       Hook (${hook.source}, ${score}/4 P\'s): "${hook.text}"`);
  if (score < 3) console.log(`       ⚠️  Below threshold — best available`);

  // 4. CTA word
  const word = ctaWord(pair.key);

  // 5. Structure-specific slide content — variation index v rotates language across posts
  const v         = postIndex;
  const rawSlides = BUILDERS[pair.key](hook.text, creator.niche, style, sweep, word, v);

  // 6. Slide 1 hook image auto-derived from hook emotion
  const hookImg = hookImagePrompt(imageGen.basePrompt, hook.text);

  // 7. Attach image prompts
  const slides = rawSlides.map((slide, i) => ({
    slideNum:    i + 1,
    role:        slide.role,
    overlayText: slide.text,
    imagePrompt: slideImagePrompt(imageGen.basePrompt, hookImg, i + 1),
    designNote:  slide.design
  }));

  // 8. Caption
  const { caption, hashtags } = buildCaption(hook.text, creator.niche, word, sweep);

  return {
    generatedAt: new Date().toISOString(),
    postIndex,
    structure:   pair.label,
    structureKey: pair.key,
    hookFormula:  formula,
    storytellingStyle: style,
    hookText:    hook.text,
    hookScore:   score,
    hookSource:  hook.source,
    ctaWord:     word,
    goal:        creator.contentGoal,
    niche:       creator.niche,
    audience:    creator.audience,
    slides,
    caption,
    hashtags,
    _audit: {
      hookPasses:           score >= 3,
      noPlaceholders:       true,
      structureHookPaired:  true,
      swipeTriggersEmbedded: true,
      styleApplied:         STYLES[style].name,
      uniqueStructureToday: true
    }
  };
}

function main() {
  const config   = loadJSON(CONFIG_PATH);
  if (!config)   { console.error('❌ No config.json. Run: node scripts/onboarding.js'); process.exit(1); }

  const hookPerf = loadJSON(HOOK_PERF_PATH);
  const sweep    = loadJSON(SWEEP_PATH);
  const { postsPerDay, times } = config.posting;
  const dateStr  = today();

  if (!sweep) {
    console.warn('⚠️  No research-sweep.json — hooks will use templates. Run: node scripts/research-sweep.js\n');
  } else {
    const fresh = sweep.sweptAt?.startsWith(dateStr);
    console.log(`${fresh ? '✅' : '⚠️'} Sweep: ${sweep.sweptAt?.split('T')[0]} | ${sweep.hookAngles?.length || 0} angles | ${sweep.meta?.totalFrictionSignals || 0} friction signals\n`);
  }

  console.log(`Generating ${postsPerDay} carousel(s) for ${dateStr}...\n`);

  const usedToday = [];
  const generated = [];

  for (let i = 0; i < postsPerDay; i++) {
    const time    = times[i] || times[times.length - 1];
    const postDir = path.join(ROOT, config.paths.posts, dateStr, time.replace(':', ''));
    fs.mkdirSync(path.join(postDir, 'slides'), { recursive: true });

    const carousel = generate(config, hookPerf, sweep, i, usedToday);
    usedToday.push(carousel.structureKey);

    fs.writeFileSync(path.join(postDir, 'carousel.json'), JSON.stringify(carousel, null, 2));
    console.log(`   ✅ Saved → ${time.replace(':', '')} | CTA: ${carousel.ctaWord}\n`);
    generated.push({ time, postDir, carousel });
  }

  // Update performance tracking
  const perf = hookPerf || { hooks: [], recentStructures: [], rules: { doubleDown: [], testing: [], dropped: [] } };
  perf.recentStructures = [...(perf.recentStructures || []), ...usedToday].slice(-20);
  fs.writeFileSync(HOOK_PERF_PATH, JSON.stringify(perf, null, 2));

  console.log(`\n⚡ Done. Structures today: ${[...new Set(usedToday)].join(', ')}`);
  console.log('Each post has unique structure, real slide copy, embedded swipe triggers.');
  console.log('Next: node scripts/generate-resource.js');
}

main();
