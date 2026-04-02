"""
Carousel content writer - full Carousel Method(tm) applied.
Structure chosen first. Hook formula second. 4 P's tested. Swipe triggers embedded.
No em-dashes. No news reporting hooks. Always starts from the feeling, not the topic.
"""

import json, os

POST_BASE = "C:/Users/migue/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/6a9b2b5d-e3e4-44a1-9547-4f5b15cd23fc/3761d0e1-454c-4368-a0da-df4778e9ccc1/skills/carousel-pipeline/posts/2026-03-26"

carousels = [

  # ─────────────────────────────────────────────────────────
  # 06:00 | HERE'S WHY YOU'RE STUCK | Hook: Limiting Belief
  # Topic: Most people use AI wrong because of bad questions
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "0600",
    "meta": {
      "topic": "The real reason your AI outputs are mediocre has nothing to do with the AI.",
      "structure": "Here's Why You're Stuck",
      "hookFormula": "limiting_belief",
      "style": "Sharp Analytical",
      "ctaWord": "PARTNER"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"Everyone blames the AI.",
       "body":"Nobody blames the question."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"Most people type into AI the same way they type into Google.",
       "body":"That is the mistake."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"AI is not a search engine.",
       "body":"It is a thinking partner. And thinking partners need context."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"Weak prompt: 'How do I make money with AI?'",
       "body":"Strong prompt: 'I have 5 hrs/week, no audience, and $0. What is my fastest path?'"},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"One gives you options.",
       "body":"The other gives you a plan. Same AI. Different question."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"The skill is not prompting.",
       "body":"The skill is context. The more you give, the more precise the output."},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"Most people are one better question away",
       "body":"from a completely different result."},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"When you stop asking AI what to do",
       "body":"and start telling it who you are, everything changes."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment PARTNER below.",
       "body":"I will send you the exact prompt framework I use every day."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"It was never the AI.",
       "body":"It was always the question."}
    ],
    "caption": "Everyone blames the AI when the output is bad. Nobody looks at the question.\n\nThe shift is simpler than you think.\n\nComment PARTNER and I will send you the full prompt framework.\n\n#AI #Claude #promptengineering #makemoneyonline #artificialintelligence"
  },

  # ─────────────────────────────────────────────────────────
  # 07:30 | MYTH -> TRUTH | Hook: Limiting Belief
  # Topic: Claude Computer Use just launched
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "0730",
    "meta": {
      "topic": "Claude can now control your Mac from your phone. This changes how you work.",
      "structure": "Myth to Truth",
      "hookFormula": "limiting_belief",
      "style": "Sharp Analytical",
      "ctaWord": "AGENT"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"You are still doing tasks yourself.",
       "body":"Claude just changed that. Most people have not noticed yet."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"Claude Computer Use launched this week.",
       "body":"You text Claude a task from your phone. It executes it on your Mac."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"The myth: AI helps you work better.",
       "body":"The truth: AI can now work instead of you."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"It opens apps. Fills forms. Browses the web.",
       "body":"Research reports. Browser tasks. Repetitive workflows. Done."},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"It asks before accessing new apps.",
       "body":"Anthropic built the safeguards in. It will not act without your permission."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"This is not a chatbot upgrade.",
       "body":"This is an agent. The gap between knowing this and not is already widening."},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"The shift that changes your entire output:",
       "body":"You stop doing tasks. You start assigning them."},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"You are no longer the bottleneck.",
       "body":"For the first time, your ceiling is not your bandwidth."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment AGENT below.",
       "body":"I will send you the 5 workflows I am automating first with Claude Computer Use."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"You just noticed what most people missed.",
       "body":"Now use it."}
    ],
    "caption": "You are still doing tasks yourself. Claude just launched something that changes that.\n\nHere is what most people have not seen yet.\n\nComment AGENT and I will send you the 5 workflows I am automating first.\n\n#Claude #AI #automation #productivity #anthropic"
  },

  # ─────────────────────────────────────────────────────────
  # 09:00 | WARNING SIGN | Hook: Problem -> Consequence
  # Topic: OpenAI killed Sora - platform dependency risk
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "0900",
    "meta": {
      "topic": "OpenAI killed Sora 6 months after launch. The real lesson is about platform dependency.",
      "structure": "Warning Sign",
      "hookFormula": "problem_consequence",
      "style": "Sharp Analytical",
      "ctaWord": "STACK"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"Sora is dead.",
       "body":"Your favorite AI tool could be next."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"6 months ago Sora topped the App Store.",
       "body":"This week OpenAI shut it down. App and API both. No warning."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"This is not a product failure.",
       "body":"This is the AI product cycle. And it will happen again."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"Warning sign 1: You built your workflow around it.",
       "body":"OpenAI just proved that any workflow you do not own can disappear overnight."},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"Warning sign 2: You have no backup system.",
       "body":"OpenAI also lost a billion-dollar Disney deal this week. They pivot without warning. Every time."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"Warning sign 3: Your audience lives on rented land.",
       "body":"Platform shuts down. Algorithm changes. API dies. If it is not yours, it is borrowed."},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"The rule that protects you:",
       "body":"Own your audience. Own your system. Rent the tools."},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"The most resilient creators do not follow tools.",
       "body":"They build principles that work on any tool. That is the real advantage."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment STACK below.",
       "body":"I will show you how to build a content system that survives any tool shutdown."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"Sora is dead.",
       "body":"Are you next? Only if you let someone else control your system."}
    ],
    "caption": "Sora topped the App Store 6 months ago. This week OpenAI killed it with no warning.\n\nYour favorite tool could be next. Here is the lesson most people will miss.\n\nComment STACK and I will show you how to build a platform-proof system.\n\n#OpenAI #AI #contentcreator #digitalstrategy #creator"
  },

  # ─────────────────────────────────────────────────────────
  # 11:00 | HERE'S WHY YOU'RE STUCK | Hook: Nobody Talks About
  # Topic: GPT-5.4 1M token context window - what it actually unlocks
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "1100",
    "meta": {
      "topic": "The reason your AI outputs are generic is context. GPT-5.4 just made that obvious.",
      "structure": "Here's Why You're Stuck",
      "hookFormula": "nobody_talks",
      "style": "Sharp Analytical",
      "ctaWord": "CONTEXT"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"Your AI gives you generic answers.",
       "body":"The reason is not the model. It is the context you are not giving it."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"You are giving AI a sentence.",
       "body":"AI is now built for a book. That gap is the entire problem."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"GPT-5.4 just dropped with a 1 million token context window.",
       "body":"Most people are using less than 1% of what that makes possible."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"1 million tokens is a full book.",
       "body":"A full codebase. Months of emails. An entire business. In one session."},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"The people using full context get outputs that feel like magic.",
       "body":"The people using one sentence get generic answers. Same tool."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"What full context actually unlocks:",
       "body":"Analyze your entire content library. Find every pattern. In one prompt."},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"This is not a bigger chat box.",
       "body":"It is a new category of thinking tool. Treat it that way."},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"When you give AI full context, it stops guessing.",
       "body":"And starts knowing. That is the entire difference."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment CONTEXT below.",
       "body":"I will send you 5 prompts that only work at 1M tokens and what they actually do."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"Your AI is not generic.",
       "body":"Your context is. Now you know what to fix."}
    ],
    "caption": "Your AI gives you generic answers. The problem is not the model. It is the context you are not giving it.\n\nGPT-5.4 just made this impossible to ignore.\n\nComment CONTEXT and I will send you 5 prompts that only work at 1M tokens.\n\n#GPT5 #AI #promptengineering #productivity #OpenAI"
  },

  # ─────────────────────────────────────────────────────────
  # 13:00 | MYTH -> TRUTH | Hook: Everyone Does This Wrong
  # Topic: Vibe coding $4.7B market, 63% non-developers
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "1300",
    "meta": {
      "topic": "63% of people shipping apps right now never learned to code. The barrier was never skill.",
      "structure": "Myth to Truth",
      "hookFormula": "everyone_wrong",
      "style": "Sharp Analytical",
      "ctaWord": "BUILD"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"63% of people shipping apps right now never learned to code.",
       "body":"Here is what that tells you."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"Vibe coding is a $4.7 billion market.",
       "body":"It barely existed two years ago. Gartner says 60% of all new code will be AI-generated by end of 2026."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"The myth: you need to code to build software.",
       "body":"The truth: you need to know what problem to solve."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"The tools making this real:",
       "body":"Bolt.new. Lovable. Base44. You describe it. AI builds it. You ship it."},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"What non-developers are building right now:",
       "body":"Internal tools. Niche SaaS. Automations. One specific problem solved. Revenue generated."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"The barrier was never skill.",
       "body":"It was access. AI just removed the last wall between the idea and the product."},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"The real skill in 2026:",
       "body":"Knowing what to build. Not how to build it."},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"The software industry is being repriced.",
       "body":"The people on the right side of this shift started building before they felt ready."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment BUILD below.",
       "body":"I will send you the exact stack I use to ship apps without writing code."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"63% of builders never learned to code.",
       "body":"They just started building."}
    ],
    "caption": "63% of people shipping apps right now never learned to code. The barrier was never skill.\n\nHere is what the vibe coding shift actually means for you.\n\nComment BUILD and I will send you the full stack I use to ship without code.\n\n#vibecoding #AI #buildwithai #nocode #entrepreneur"
  },

  # ─────────────────────────────────────────────────────────
  # 16:00 | WARNING SIGN | Hook: Problem -> Consequence
  # Topic: Oracle + Block layoffs - structural AI replacement
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "1600",
    "meta": {
      "topic": "Oracle and Block just told the workforce something most people are not ready to hear.",
      "structure": "Warning Sign",
      "hookFormula": "problem_consequence",
      "style": "Sharp Analytical",
      "ctaWord": "PROOF"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"Your job is not being automated.",
       "body":"It is being replaced. There is a difference."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"Oracle cut 30,000 jobs this week.",
       "body":"Block cut 40% of its workforce. Same week. Same reason. AI."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"These are not layoffs from a bad quarter.",
       "body":"This is the structural shift. The one everyone said was coming. It is here."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"Warning sign 1: repetitive knowledge work is disappearing.",
       "body":"Data entry. Basic analysis. Customer support at scale. Gone."},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"Warning sign 2: the roles being amplified are different.",
       "body":"The people doing the work of 5 using AI. Creative directors. Builders. Strategic thinkers."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"Warning sign 3: the question nobody is asking.",
       "body":"Does my work produce outcomes AI cannot yet replicate? If not, that needs to change now."},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"The fastest protection is not upskilling.",
       "body":"It is becoming the person who deploys AI for others. That role does not get cut."},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"The people thriving inside this shift",
       "body":"did not fight it. They positioned inside it before it arrived."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment PROOF below.",
       "body":"I will send you the 5 skills that make you AI-proof in any industry."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"Oracle replaced 30,000.",
       "body":"What are you building to make sure you are not next?"}
    ],
    "caption": "Your job is not being automated. It is being replaced. Oracle and Block just proved the difference.\n\nHere is the honest conversation about what comes next.\n\nComment PROOF and I will send you the 5 skills that make you AI-proof.\n\n#AI #futureofwork #career #artificialintelligence #entrepreneur"
  },

  # ─────────────────────────────────────────────────────────
  # 18:00 | MYTH -> TRUTH | Hook: Perspective Shift
  # Topic: Visa AI payment agents - agentic commerce
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "1800",
    "meta": {
      "topic": "Visa is building AI that buys on your behalf. The human buyer is becoming optional.",
      "structure": "Myth to Truth",
      "hookFormula": "perspective_shift",
      "style": "Sharp Analytical",
      "ctaWord": "COMMERCE"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"Your next customer might be an AI.",
       "body":"Visa just made that real."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"Visa is piloting AI payment agents right now.",
       "body":"Software that initiates purchases, manages procurement, and handles payments on your behalf."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"The myth: buying requires a human decision.",
       "body":"The truth: AI agents are already making purchasing decisions inside rules you set."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"First use cases in the pilot:",
       "body":"Automated procurement. Recurring business purchases. Subscriptions managed without any manual input."},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"What this means for your business:",
       "body":"Buying decisions will increasingly be made by agents. Not by humans browsing and clicking."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"The businesses that win this shift:",
       "body":"The ones whose products are easy for AI agents to discover, evaluate, and buy."},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"The question to ask today:",
       "body":"Is my product agent-compatible? Can a bot buy it, renew it, recommend it without friction?"},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"The next frontier is not human conversion.",
       "body":"It is agent conversion. The businesses building for this now will own the next decade."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment COMMERCE below.",
       "body":"I will break down exactly how to position your business for the agentic economy."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"Your next customer might be an AI.",
       "body":"The ones who are ready will win. Are you?"}
    ],
    "caption": "Your next customer might be an AI. Visa just made that real with their new payment agent pilot.\n\nHere is what the agentic economy actually looks like for your business.\n\nComment COMMERCE and I will show you how to position for AI buyers.\n\n#AI #ecommerce #fintech #AIagents #business"
  },

  # ─────────────────────────────────────────────────────────
  # 19:30 | WARNING SIGN | Hook: Nobody Talks About This
  # Topic: US AI Accountability Act - legal obligations for AI users
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "1930",
    "meta": {
      "topic": "The US just passed an AI law. Most creators using AI now have legal obligations they do not know about.",
      "structure": "Warning Sign",
      "hookFormula": "nobody_talks",
      "style": "Sharp Analytical",
      "ctaWord": "LAW"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"Most people using AI in their business now have legal obligations.",
       "body":"Nobody is talking about it."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"The US AI Accountability Act just passed.",
       "body":"It affects everyone using AI in business. Not just big tech."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"You assumed this was someone else's problem.",
       "body":"If you use AI in hiring, lending, healthcare, or customer decisions, it is now yours."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"Warning sign 1: you are not disclosing AI use.",
       "body":"The law requires disclosure. Regular bias audits. Published results."},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"Warning sign 2: you think this bans AI.",
       "body":"It does not. It is a floor, not a ceiling. Builders who understand it move faster inside it."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"Warning sign 3: you are using AI in content but staying silent about it.",
       "body":"Transparency is becoming the expectation. The brands that lead on this win trust."},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"The early mover advantage is real.",
       "body":"Brands that are transparent about AI now will be the most trusted when rules tighten further."},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"Regulation is not the enemy of builders.",
       "body":"It is the signal that AI is now infrastructure. Treat it that way."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment LAW below.",
       "body":"I will break down the 3 things to do right now if you use AI in your business."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"You have legal obligations now.",
       "body":"The ones who know this move fastest inside it."}
    ],
    "caption": "Most people using AI in their business now have legal obligations they do not know about.\n\nThe US AI Accountability Act just changed the rules. Here is what it actually means.\n\nComment LAW and I will share the 3 things to do right now.\n\n#AI #regulation #business #creator #artificialintelligence"
  },

  # ─────────────────────────────────────────────────────────
  # 21:00 | MYTH -> TRUTH | Hook: Limiting Belief
  # Topic: Claude solved Knuth problem - you are underusing AI
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "2100",
    "meta": {
      "topic": "You are using Claude like a faster typewriter. Knuth just showed you what it can actually do.",
      "structure": "Myth to Truth",
      "hookFormula": "limiting_belief",
      "style": "Sharp Analytical",
      "ctaWord": "THINK"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"The smartest computer scientist alive spent weeks on a problem.",
       "body":"Claude solved it in one session."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"Donald Knuth invented the algorithms your software still runs on.",
       "body":"He published a paper in shock after Claude Opus 4.6 solved a graph theory problem he had been working on for weeks."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"This is not about AI being smarter.",
       "body":"It is about AI having no assumptions. No habits. No attachment to a single approach."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"Knuth had spent decades approaching the problem the same way.",
       "body":"Claude had no patterns to repeat. That was the advantage."},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"The myth: you are using Claude well.",
       "body":"The truth: most people use it to write faster. Not to think differently."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"The prompt that unlocks a different kind of output:",
       "body":"'Approach this as if you have never seen it before. What do you notice first?'"},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"AI's edge is not intelligence.",
       "body":"It is perspective. No ego, no assumptions, no attachment to being right."},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"You are not using Claude for thinking.",
       "body":"You are using it for typing. That gap is your next breakthrough."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment THINK below.",
       "body":"I will send you the prompts I use to get Claude thinking at this level on real problems."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"Knuth was stunned.",
       "body":"Your next breakthrough might already be one session away."}
    ],
    "caption": "The smartest computer scientist alive spent weeks on a problem. Claude solved it in one session.\n\nHere is what that tells you about how you are actually using AI.\n\nComment THINK and I will send you the prompts that unlock this level.\n\n#Claude #AI #Anthropic #thinking #artificialintelligence"
  },

  # ─────────────────────────────────────────────────────────
  # 22:30 | MYTH -> TRUTH | Hook: Helpful Habit Backfires
  # Topic: AI ads $57B - the UGC model is being repriced
  # 4 P's: Precision(Y) Problem(Y) Polarity(Y) Perspective(Y)
  # ─────────────────────────────────────────────────────────
  {
    "slot": "2230",
    "meta": {
      "topic": "The ad you just watched was probably not made by a human. Most people cannot tell.",
      "structure": "Myth to Truth",
      "hookFormula": "helpful_habit_backfires",
      "style": "Sharp Analytical",
      "ctaWord": "ADS"
    },
    "slides": [
      {"number":1,"role":"HOOK","theme":"dark",
       "headline":"The ad you just watched was probably not made by a human.",
       "body":"Most people cannot tell. That is the point."},
      {"number":2,"role":"CONTEXT","theme":"light",
       "headline":"AI-powered ads are growing 63% this year.",
       "body":"$57 billion. And brands cannot get enough."},
      {"number":3,"role":"PATTERN BREAK","theme":"dark",
       "headline":"The myth: authenticity requires a real creator.",
       "body":"The truth: the market does not reward authenticity. It rewards effectiveness."},
      {"number":4,"role":"INSIGHT 1","theme":"light",
       "headline":"What brands actually want:",
       "body":"Speed. Volume. Consistency. AI delivers all three without revision cycles or scheduling conflicts."},
      {"number":5,"role":"INSIGHT 2","theme":"dark",
       "headline":"The UGC model is under pressure.",
       "body":"Not because creators are bad. Because AI produces 50 variations in the time it takes to brief one creator."},
      {"number":6,"role":"INSIGHT 3","theme":"light",
       "headline":"The creators winning right now:",
       "body":"They use AI as their production studio. They become the director. Not the talent."},
      {"number":7,"role":"INSIGHT 4","theme":"dark",
       "headline":"70% of consumers cannot tell the difference.",
       "body":"The 30% who distrust AI ads are being outspent by the majority who cannot see it."},
      {"number":8,"role":"TRANSFORMATION","theme":"light",
       "headline":"The ad industry is not asking if AI belongs.",
       "body":"It is deciding who controls it. That decision is happening right now."},
      {"number":9,"role":"CTA","theme":"dark",
       "headline":"Comment ADS below.",
       "body":"I will show you exactly what AI ad production looks like in 2026 and how to use it."},
      {"number":10,"role":"LOOP CLOSE","theme":"light",
       "headline":"The ad you just watched was probably AI.",
       "body":"$57 billion says the rest will be too."}
    ],
    "caption": "The ad you just watched was probably not made by a human. Most people cannot tell.\n\nHere is what is actually happening inside the ad industry right now.\n\nComment ADS and I will show you what AI ad production looks like in 2026.\n\n#AIads #digitalmarketing #contentcreator #advertising #realisticads"
  }

]

for c in carousels:
    slot = c["slot"]
    d = f"{POST_BASE}/{slot}"
    os.makedirs(d, exist_ok=True)
    data = {
        "meta": {
            "date": "2026-03-26",
            "slot": slot,
            "structure": c["meta"]["structure"],
            "hookFormula": c["meta"]["hookFormula"],
            "style": c["meta"]["style"],
            "topic": c["meta"]["topic"],
            "ctaWord": c["meta"]["ctaWord"]
        },
        "slides": c["slides"],
        "caption": c["caption"]
    }
    with open(f"{d}/carousel.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[OK] {slot} | {c['meta']['hookFormula']} | {c['slides'][0]['headline']}")

print("\nAll 10 carousels written with full Carousel Method(tm) applied.")
