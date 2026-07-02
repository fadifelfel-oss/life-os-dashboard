// ============================================================
// SHARED MODEL CATALOG — single source of truth for the model
// job-categories used by BOTH models.html and chat.html.
// Edit the picks here once; both pages update together.
// Prices in `fb` are per-TOKEN (USD); comments show $/1M.
// Sourced from the live OpenRouter catalog 2026-07-02.
// ============================================================
window.LIFEOS_JOBS = [
  {
    key:'ingest', emoji:'📥', title:'Ingest & Summarize',
    sub:'Web clippings, PDFs, transcripts — high volume, needs cheap + fast + big context.',
    tip:'Your highest-volume job. DeepSeek V4 Flash summarizes a 1M-token doc for pennies — route the bulk here and only escalate dense technical sources.',
    picks:[
      { role:'rec', match:['deepseek-v4-flash','deepseek/deepseek-v4-flash'], fb:{name:'DeepSeek V4 Flash',provider:'DeepSeek',pp:0.00000009,pc:0.00000018,ctx:1048576}, why:'~$0.09/$0.18 per 1M with 1M context — cheapest capable summarizer available. Ideal for bulk ingestion.' },
      { role:'budget', match:['owl-alpha','ling-2.6-flash'], fb:{name:'owl-alpha (free)',provider:'OpenRouter',pp:0,pc:0,ctx:1048576}, why:'Free, 1M context — use for huge batches of light clippings where volume beats nuance.' },
      { role:'premium', match:['gemini-3.5-flash','gemini-flash-latest'], fb:{name:'Gemini 3.5 Flash',provider:'Google',pp:0.0000015,pc:0.000009,ctx:1048576}, why:'~$1.5/$9 per 1M, 1M context — higher fidelity for long, dense, or technical documents.' },
    ],
  },
  {
    key:'analyze', emoji:'🔎', title:'Analyze & Find Opportunities',
    sub:'Connect knowledge + CRM feedback to surface monetization angles — needs real reasoning.',
    tip:'The core of your AIOS thesis. Worth spending more here — a better insight pays for itself. First-pass free, then a paid deep run on the shortlist.',
    picks:[
      { role:'rec', match:['deepseek-v4-pro','deepseek/deepseek-v4-pro'], fb:{name:'DeepSeek V4 Pro',provider:'DeepSeek',pp:0.000000435,pc:0.00000087,ctx:1048576}, why:'~$0.44/$0.87 per 1M with 1M context — strong reasoning at a fraction of flagship cost. Best value for analysis.' },
      { role:'budget', match:['nemotron-3-ultra-550b:free','nemotron-3-ultra','nemotron-3-nano'], fb:{name:'Nemotron 3 Ultra 550B (free)',provider:'NVIDIA',pp:0,pc:0,ctx:1000000}, why:'A 550B reasoning model at zero cost — great for first-pass synthesis before you spend on depth.' },
      { role:'premium', match:['claude-opus-4.8','claude-opus-latest'], fb:{name:'Claude Opus 4.8',provider:'Anthropic',pp:0.000005,pc:0.000025,ctx:1000000}, why:'~$5/$25 per 1M — top-tier judgment for the highest-stakes opportunity calls and investor-facing analysis.' },
    ],
  },
  {
    key:'agent', emoji:'🤖', title:'Agent / Tool-use (Hermes routes)',
    sub:'VPS automations, function-calling, ingestion pipelines — needs reliable structured output.',
    tip:'Note: the hermes-agent framework routes to ANY OpenRouter model — Nous Hermes weights aren\'t in the current catalog, so pick the best tool-caller by job. Match the model to the tool set: cheap for simple tools, escalate only for multi-step planning.',
    picks:[
      { role:'rec', match:['deepseek-v4-pro','deepseek/deepseek-v4-pro'], fb:{name:'DeepSeek V4 Pro',provider:'DeepSeek',pp:0.000000435,pc:0.00000087,ctx:1048576}, why:'Strong, cheap structured-output/function-calling with 1M context — reliable default for routine agent loops.' },
      { role:'budget', match:['deepseek-v4-flash','qwen3.6-flash'], fb:{name:'DeepSeek V4 Flash',provider:'DeepSeek',pp:0.00000009,pc:0.00000018,ctx:1048576}, why:'Near-free for simple, well-defined single-tool calls at high volume.' },
      { role:'premium', match:['claude-opus-4.8','gpt-5.5','claude-opus-latest'], fb:{name:'Claude Opus 4.8',provider:'Anthropic',pp:0.000005,pc:0.000025,ctx:1000000}, why:'For hard multi-step plans where a wrong tool call is expensive — highest reliability.' },
    ],
  },
  {
    key:'code', emoji:'💻', title:'Coding & Building',
    sub:'Dashboard code, scripts, fixes — needs code strength and instruction-following.',
    tip:'For anything that touches the repo, keep a review step. Free coder for scaffolding, premium for tricky multi-file logic.',
    picks:[
      { role:'rec', match:['kimi-k2.7-code','kimi-latest'], fb:{name:'Kimi K2.7 Code',provider:'Moonshot',pp:0.000000612,pc:0.000003069,ctx:262144}, why:'~$0.61/$3.07 per 1M — dedicated code model, strong value for everyday build tasks.' },
      { role:'budget', match:['north-mini-code:free','north-mini-code','laguna-xs.2:free','pareto-code'], fb:{name:'North Mini Code (free)',provider:'Cohere',pp:0,pc:0,ctx:256000}, why:'Free code model — great for scaffolding, refactors, and glue code before a premium pass.' },
      { role:'premium', match:['claude-opus-4.8','gpt-5.5-pro','claude-opus-latest'], fb:{name:'Claude Opus 4.8',provider:'Anthropic',pp:0.000005,pc:0.000025,ctx:1000000}, why:'Best reliability on complex logic and large multi-file changes.' },
    ],
  },
  {
    key:'everyday', emoji:'💬', title:'Everyday & Admin',
    sub:'Chat, Notion, drafting docs, emails — balanced, low-cost, good writing.',
    tip:'Your bread-and-butter. Claude Haiku covers 90% of drafting cleanly and cheaply; only reach for premium on client-facing writing.',
    picks:[
      { role:'rec', match:['claude-haiku-latest','claude-haiku'], fb:{name:'Claude Haiku (latest)',provider:'Anthropic',pp:0.000001,pc:0.000005,ctx:200000}, why:'~$1/$5 per 1M — clean tone for emails, notes, and docs at a low price. Ideal everyday default.' },
      { role:'budget', match:['gemini-3.1-flash-lite','deepseek-v4-flash','owl-alpha'], fb:{name:'Gemini 3.1 Flash Lite',provider:'Google',pp:0.00000025,pc:0.0000015,ctx:1048576}, why:'Near-free for quick admin questions and short drafts.' },
      { role:'premium', match:['claude-sonnet-latest','claude-sonnet'], fb:{name:'Claude Sonnet (latest)',provider:'Anthropic',pp:0.000003,pc:0.000015,ctx:1000000}, why:'~$3/$15 per 1M — best tone and polish for client-facing emails and important documents.' },
    ],
  },
];

// Resolve a pick's match[] against a live /api/models list; returns the model obj or null.
window.lifeosResolvePick = function(models, matchArr){
  for (const frag of (matchArr||[])){
    const f = (frag||'').toLowerCase();
    const hit = (models||[]).find(m => ((m.id||'').toLowerCase().includes(f) || (m.name||'').toLowerCase().includes(f)));
    if (hit) return hit;
  }
  return null;
};

// Default chat model — set from the models page, honored by the chat page.
window.lifeosGetDefaultModel = function(){ try { return localStorage.getItem('lifeos-default-model') || ''; } catch(e){ return ''; } };
window.lifeosSetDefaultModel = function(id){ try { localStorage.setItem('lifeos-default-model', id); } catch(e){} };
