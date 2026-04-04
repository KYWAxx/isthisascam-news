#!/usr/bin/env python3
"""
Generates individual scam HTML pages from JSON data files in _data/.
Also generates content via Bertha (Ollama) if JSON doesn't exist yet.

Usage:
    python scams/_build.py              # Generate missing JSON + render all HTML
    python scams/_build.py --render     # Render HTML from existing JSON only
"""

import json
import os
import sys
import html as html_mod
from pathlib import Path

SCAMS_DIR = Path(__file__).parent
DATA_DIR = SCAMS_DIR / "_data"
DATA_DIR.mkdir(exist_ok=True)

BERTHA_URL = os.getenv("BERTHA_URL", "http://192.168.1.137:11434")
BERTHA_MODEL = os.getenv("BERTHA_MODEL", "qwen2.5:32b")

SCAM_CATEGORIES = [
    {"slug": "government-grant-scams",   "icon": "🏛️", "name": "Government Grant Scams"},
    {"slug": "grandparent-scams",        "icon": "👵",  "name": "Grandparent Scams"},
    {"slug": "romance-scams",            "icon": "💔",  "name": "Romance Scams"},
    {"slug": "tech-support-scams",       "icon": "🖥️", "name": "Tech Support Scams"},
    {"slug": "sim-swapping",             "icon": "📱",  "name": "SIM Swapping"},
    {"slug": "phishing-smishing",        "icon": "🎣",  "name": "Phishing & Smishing"},
    {"slug": "investment-crypto-scams",  "icon": "📈",  "name": "Investment & Crypto Scams"},
    {"slug": "medicare-scams",           "icon": "🏥",  "name": "Medicare Scams"},
    {"slug": "charity-scams",            "icon": "🤝",  "name": "Charity Scams"},
    {"slug": "gift-card-scams",          "icon": "🎁",  "name": "Gift Card Scams"},
    {"slug": "prize-lottery-scams",      "icon": "🎰",  "name": "Prize & Lottery Scams"},
    {"slug": "irs-ssa-impersonation",    "icon": "📋",  "name": "IRS & SSA Impersonation"},
    {"slug": "virtual-kidnapping",       "icon": "🚨",  "name": "Virtual Kidnapping"},
    {"slug": "qr-code-scams",           "icon": "📲",  "name": "QR Code Scams"},
    {"slug": "ai-voice-cloning-scams",   "icon": "🤖",  "name": "AI Voice Cloning Scams"},
]

SLUG_TO_CAT = {c["slug"]: c for c in SCAM_CATEGORIES}


def _fix_json(raw: str) -> str:
    """Fix control chars in LLM JSON output."""
    cleaned = []
    in_str = False
    esc = False
    for ch in raw:
        if esc:
            cleaned.append(ch)
            esc = False
        elif ch == '\\':
            cleaned.append(ch)
            esc = True
        elif ch == '"':
            cleaned.append(ch)
            in_str = not in_str
        elif in_str and ch in ('\n', '\r', '\t'):
            cleaned.append('\\n' if ch == '\n' else ('\\r' if ch == '\r' else '\\t'))
        elif in_str and ord(ch) < 32:
            pass
        else:
            cleaned.append(ch)
    return ''.join(cleaned)


def generate_content(slug: str, name: str) -> dict:
    """Generate scam page content via Bertha."""
    import requests

    system = (
        "You write authoritative, detailed scam education content for isthisascam.news — "
        "a trusted resource for adult children (35-55) protecting their aging parents from fraud. "
        "Write for a non-technical audience. Use real statistics from FTC, FBI IC3, and BBB when possible. "
        "Never blame victims. Tone: clear, protective, expert."
    )

    user = f"""Write a comprehensive scam education page about "{name}". Return valid JSON:
{{
  "title": "{name}",
  "meta_description": "SEO meta description about {name}, under 160 chars",
  "overview": "2-3 paragraphs about what this scam is, why it's dangerous, with real statistics if possible. Write substantial content — at least 150 words.",
  "how_it_works": ["Step 1: ...", "Step 2: ...", "Step 3: ...", "Step 4: ..."],
  "examples": ["Realistic victim scenario 1 (3-4 sentences)", "Realistic victim scenario 2"],
  "red_flags": ["Red flag 1", "Red flag 2", "Red flag 3", "Red flag 4", "Red flag 5"],
  "what_to_do": ["Specific action 1", "Specific action 2", "Specific action 3", "Specific action 4"],
  "entry_points": ["How scammers reach victims - method 1", "Method 2", "Method 3"],
  "related_scams": ["slug-1", "slug-2", "slug-3"]
}}
Respond ONLY with valid JSON. No markdown fences."""

    payload = {
        "model": BERTHA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 3000},
    }

    resp = requests.post(f"{BERTHA_URL}/api/chat", json=payload, timeout=360)
    resp.raise_for_status()

    raw = resp.json()["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(_fix_json(raw))
    return data


def render_page(slug: str, data: dict) -> str:
    """Render an individual scam page HTML from JSON data."""
    cat = SLUG_TO_CAT.get(slug, {})
    icon = cat.get("icon", "🛡️")
    title = html_mod.escape(data.get("title", slug.replace("-", " ").title()))
    meta_desc = html_mod.escape(data.get("meta_description", ""))
    overview = data.get("overview", "")
    how_it_works = data.get("how_it_works", [])
    examples = data.get("examples", [])
    red_flags = data.get("red_flags", [])
    what_to_do = data.get("what_to_do", [])
    entry_points = data.get("entry_points", [])
    related_slugs = data.get("related_scams", [])
    action_plan = data.get("action_plan", {})

    # Build HTML sections
    overview_html = "".join(f"<p>{html_mod.escape(p)}</p>" for p in overview.split("\n\n")) if "\n\n" in overview else f"<p>{html_mod.escape(overview)}</p>"

    steps_html = ""
    for i, step in enumerate(how_it_works, 1):
        clean = html_mod.escape(step.lstrip("0123456789.:) "))
        steps_html += f'<div class="step"><div class="step-num">{i}</div><div class="step-text">{clean}</div></div>\n'

    examples_html = ""
    for ex in examples:
        examples_html += f'<div class="example-card"><p>{html_mod.escape(ex)}</p></div>\n'

    flags_html = ""
    for flag in red_flags:
        flags_html += f'<li><span class="flag-icon">⚠️</span> {html_mod.escape(flag)}</li>\n'

    actions_html = ""
    for action in what_to_do:
        actions_html += f'<li><span class="action-icon">✅</span> {html_mod.escape(action)}</li>\n'

    # Expanded action plan
    action_plan_html = ""
    if action_plan and isinstance(action_plan, dict):
        phase_order = ["immediate", "reporting", "financial", "identity", "emotional", "followup"]
        phase_icons = {"immediate": "🚨", "reporting": "📝", "financial": "💳", "identity": "🔒", "emotional": "💛", "followup": "📋"}
        phase_num = 0
        for key in phase_order:
            phase = action_plan.get(key)
            if not phase or not isinstance(phase, dict):
                continue
            phase_num += 1
            p_title = html_mod.escape(phase.get("title", key.title()))
            steps = phase.get("steps", [])
            is_emotional = key == "emotional"
            extra_class = " ap-emotional" if is_emotional else ""
            icon = phase_icons.get(key, "✅")
            steps_li = ""
            for s in steps:
                steps_li += f'<li><span class="ap-check">{icon}</span> {html_mod.escape(s)}</li>\n'
            action_plan_html += f'''<div class="ap-phase{extra_class}">
  <div class="ap-phase-header"><span class="ap-phase-num">{phase_num}</span><span class="ap-phase-title">{p_title}</span></div>
  <div class="ap-phase-body"><ul>{steps_li}</ul></div>
</div>\n'''

    entry_html = ""
    for ep in entry_points:
        entry_html += f'<li>{html_mod.escape(ep)}</li>\n'

    related_html = ""
    for rs in related_slugs:
        rc = SLUG_TO_CAT.get(rs, {})
        if rc:
            related_html += f'<a href="/scams/{rs}" class="related-card"><span>{rc["icon"]}</span> {html_mod.escape(rc["name"])}</a>\n'

    # Schema.org structured data
    schema_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": data.get("title", ""),
        "description": data.get("meta_description", ""),
        "url": f"https://isthisascam.news/scams/{slug}",
        "publisher": {
            "@type": "Organization",
            "name": "Is This a Scam?",
            "url": "https://isthisascam.news",
        },
        "mainEntityOfPage": f"https://isthisascam.news/scams/{slug}",
        "articleSection": "Scam Library",
    })

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Is This a Scam?</title>
<meta name="description" content="{meta_desc}">
<meta property="og:title" content="{title} | Is This a Scam?">
<meta property="og:description" content="{meta_desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://isthisascam.news/scams/{slug}">
<meta property="og:image" content="https://isthisascam.news/og-image.png">
<meta property="og:site_name" content="Is This a Scam?">
<link rel="canonical" href="https://isthisascam.news/scams/{slug}">
<script type="application/ld+json">{schema_json}</script>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛡️</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Merriweather:wght@700;900&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy: #1B2A4A; --blue: #2563EB; --blue-light: #EFF6FF;
    --amber: #D97706; --amber-light: #FEF3C7;
    --bg: #F8F9FA; --white: #FFFFFF; --text: #1B2A4A;
    --text-secondary: #4B5563; --border: #E5E7EB;
    --serif: 'Merriweather', Georgia, serif;
    --sans: 'DM Sans', -apple-system, sans-serif;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ scroll-behavior: smooth; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--sans); font-size: 16px; line-height: 1.7; }}

  .nav {{ display: flex; align-items: center; justify-content: space-between; padding: 16px 40px; background: var(--white); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }}
  .nav-brand {{ display: flex; align-items: center; gap: 10px; text-decoration: none; color: var(--navy); }}
  .nav-shield {{ font-size: 24px; }}
  .nav-name {{ font-family: var(--serif); font-size: 18px; font-weight: 900; }}
  .nav-links {{ display: flex; align-items: center; gap: 32px; list-style: none; }}
  .nav-links a {{ color: var(--text-secondary); text-decoration: none; font-size: 14px; font-weight: 500; transition: color 0.2s; }}
  .nav-links a:hover {{ color: var(--navy); }}
  .nav-cta {{ background: var(--blue); color: var(--white) !important; padding: 10px 22px; border-radius: 8px; font-weight: 600 !important; }}
  .nav-hamburger {{ display: none; background: none; border: none; font-size: 24px; cursor: pointer; color: var(--navy); }}

  .article {{ max-width: 780px; margin: 0 auto; padding: 48px 40px 80px; }}
  .breadcrumb {{ font-size: 13px; color: var(--text-secondary); margin-bottom: 24px; }}
  .breadcrumb a {{ color: var(--blue); text-decoration: none; }}

  .article-icon {{ font-size: 48px; margin-bottom: 16px; }}
  .article h1 {{ font-family: var(--serif); font-size: clamp(28px, 4vw, 40px); font-weight: 900; color: var(--navy); margin-bottom: 24px; line-height: 1.2; }}

  .section-heading {{ font-family: var(--serif); font-size: 22px; font-weight: 700; color: var(--navy); margin: 48px 0 16px; padding-bottom: 8px; border-bottom: 2px solid var(--border); }}

  .article p {{ color: var(--text-secondary); margin-bottom: 16px; font-size: 16px; line-height: 1.8; }}

  .step {{ display: flex; gap: 16px; margin-bottom: 20px; align-items: flex-start; }}
  .step-num {{ width: 36px; height: 36px; border-radius: 50%; background: var(--blue); color: var(--white); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; flex-shrink: 0; }}
  .step-text {{ font-size: 15px; color: var(--text-secondary); line-height: 1.7; padding-top: 6px; }}

  .example-card {{ background: var(--blue-light); border-left: 4px solid var(--blue); padding: 20px 24px; border-radius: 0 8px 8px 0; margin-bottom: 16px; }}
  .example-card p {{ color: var(--text); margin: 0; font-size: 15px; font-style: italic; }}

  .flags-list, .actions-list {{ list-style: none; }}
  .flags-list li, .actions-list li {{ display: flex; gap: 10px; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 15px; color: var(--text-secondary); }}
  .flag-icon, .action-icon {{ flex-shrink: 0; }}

  .entry-list {{ list-style: none; display: flex; flex-wrap: wrap; gap: 10px; }}
  .entry-list li {{ background: var(--amber-light); color: var(--amber); padding: 8px 16px; border-radius: 100px; font-size: 13px; font-weight: 600; }}

  .related-grid {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  .related-card {{ display: inline-flex; align-items: center; gap: 8px; padding: 12px 20px; background: var(--white); border: 1px solid var(--border); border-radius: 8px; text-decoration: none; color: var(--navy); font-size: 14px; font-weight: 600; transition: border-color 0.2s; }}
  .related-card:hover {{ border-color: var(--blue); }}

  .action-plan {{ margin-top: 16px; }}
  .ap-phase {{ background: var(--white); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 16px; overflow: hidden; }}
  .ap-phase-header {{ display: flex; align-items: center; gap: 12px; padding: 18px 24px; background: var(--blue-light); border-bottom: 1px solid var(--border); cursor: pointer; }}
  .ap-phase-header:hover {{ background: #E0EDFF; }}
  .ap-phase-num {{ width: 28px; height: 28px; border-radius: 50%; background: var(--blue); color: var(--white); display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0; }}
  .ap-phase-title {{ font-weight: 700; font-size: 15px; color: var(--navy); }}
  .ap-phase-body {{ padding: 20px 24px; }}
  .ap-phase-body li {{ padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 15px; color: var(--text-secondary); line-height: 1.7; list-style: none; display: flex; gap: 10px; align-items: flex-start; }}
  .ap-phase-body li:last-child {{ border-bottom: none; }}
  .ap-check {{ color: var(--blue); flex-shrink: 0; }}
  .ap-emotional {{ background: var(--amber-light); }}
  .ap-emotional .ap-phase-header {{ background: var(--amber-light); }}
  .ap-emotional .ap-phase-header:hover {{ background: #FDE68A; }}
  .ap-emotional .ap-phase-num {{ background: var(--amber); }}
  .ap-emotional .ap-check {{ color: var(--amber); }}

  .cta-box {{ background: var(--navy); border-radius: 12px; padding: 40px; text-align: center; margin-top: 48px; }}
  .cta-box h3 {{ font-family: var(--serif); font-size: 24px; color: var(--white); margin-bottom: 12px; }}
  .cta-box p {{ color: rgba(255,255,255,0.7); margin-bottom: 24px; font-size: 15px; }}
  .cta-form {{ display: flex; gap: 12px; max-width: 420px; margin: 0 auto; }}
  .cta-form input {{ flex: 1; padding: 12px 18px; border: 2px solid rgba(255,255,255,0.2); border-radius: 8px; background: rgba(255,255,255,0.1); color: var(--white); font-family: var(--sans); font-size: 14px; outline: none; }}
  .cta-form input::placeholder {{ color: rgba(255,255,255,0.4); }}
  .cta-form input:focus {{ border-color: var(--blue); }}
  .cta-form button {{ padding: 12px 24px; background: var(--blue); color: var(--white); border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-family: var(--sans); white-space: nowrap; }}
  .cta-success {{ display: none; color: #34D399; font-weight: 600; margin-top: 12px; }}
  .cta-error {{ display: none; color: #FCA5A5; font-size: 14px; margin-top: 8px; }}

  footer {{ background: var(--white); border-top: 1px solid var(--border); padding: 32px 40px; text-align: center; font-size: 13px; color: #9CA3AF; }}
  footer a {{ color: var(--blue); text-decoration: none; }}

  @media (max-width: 768px) {{
    .nav {{ padding: 14px 20px; }}
    .nav-links {{ display: none; }}
    .nav-hamburger {{ display: block; }}
    .nav-links.open {{ display: flex; flex-direction: column; position: absolute; top: 100%; left: 0; right: 0; background: var(--white); padding: 20px; border-bottom: 1px solid var(--border); gap: 16px; }}
    .article {{ padding: 32px 20px 60px; }}
    .cta-form {{ flex-direction: column; }}
  }}
</style>
</head>
<body>

<nav class="nav">
  <a href="/" class="nav-brand"><span class="nav-shield">🛡️</span><span class="nav-name">Is This a Scam?</span></a>
  <ul class="nav-links" id="navLinks">
    <li><a href="/">Home</a></li>
    <li><a href="/scams/trending">Trending</a></li>
    <li><a href="/scams/">Scam Library</a></li>
    <li><a href="/protect">Protect Yourself</a></li>
    <li><a href="/#signup">Newsletter</a></li>
    <li><a href="/checklist.pdf">Checklist</a></li>
    <li><a href="/#about">About</a></li>
    <li><a href="/kit" class="nav-cta">Free Kit</a></li>
  </ul>
  <button class="nav-hamburger" onclick="document.getElementById('navLinks').classList.toggle('open')" aria-label="Menu">&#9776;</button>
</nav>

<article class="article">
  <div class="breadcrumb"><a href="/">Home</a> &rsaquo; <a href="/scams/">Scam Library</a> &rsaquo; {title}</div>

  <div class="article-icon">{icon}</div>
  <h1>{title}</h1>

  <h2 class="section-heading">What is this scam?</h2>
  {overview_html}

  <h2 class="section-heading">How the scam works</h2>
  {steps_html}

  <h2 class="section-heading">Real examples</h2>
  {examples_html}

  <h2 class="section-heading">Red flags to watch for</h2>
  <ul class="flags-list">
    {flags_html}
  </ul>

  <h2 class="section-heading">{"Victim recovery plan" if action_plan_html else "What to do if you're targeted"}</h2>
  {"<div class='action-plan'>" + action_plan_html + "</div>" if action_plan_html else "<ul class='actions-list'>" + actions_html + "</ul>"}

  <h2 class="section-heading">How scammers find you</h2>
  <ul class="entry-list">
    {entry_html}
  </ul>

  {"<h2 class='section-heading'>Related scams</h2><div class='related-grid'>" + related_html + "</div>" if related_html else ""}

  <div class="cta-box">
    <h3>Get weekly scam alerts</h3>
    <p>We break down one scam every week — what they say, how to spot it, and what to tell your family.</p>
    <form class="cta-form" onsubmit="event.preventDefault(); handleSignup();">
      <input type="email" id="ctaEmail" placeholder="Your email address" required>
      <button type="submit" id="ctaBtn">Subscribe Free</button>
    </form>
    <div class="cta-success" id="ctaSuccess">You're in! Check your inbox.</div>
    <div class="cta-error" id="ctaError"></div>
  </div>
</article>

<footer>
  <a href="/">Is This a Scam?</a> &middot; <a href="/scams/">Scam Library</a> &middot; <a href="/#signup">Get free alerts</a>
  <br>&copy; 2026 isthisascam.news
</footer>

<script>
  async function handleSignup() {{
    const email = document.getElementById('ctaEmail').value.trim();
    const btn = document.getElementById('ctaBtn');
    const ok = document.getElementById('ctaSuccess');
    const err = document.getElementById('ctaError');
    err.style.display = 'none'; ok.style.display = 'none';
    if (!email || !email.includes('@')) {{ err.textContent = 'Please enter a valid email.'; err.style.display = 'block'; return; }}
    btn.disabled = true; btn.textContent = 'Sending...';
    try {{
      const r = await fetch('https://signup.isthisascam.news/subscribe', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{ email }}) }});
      if (r.ok) {{ ok.style.display = 'block'; document.getElementById('ctaEmail').value = ''; btn.textContent = 'Subscribed!'; }}
      else throw new Error();
    }} catch (e) {{ err.textContent = 'Something went wrong.'; err.style.display = 'block'; btn.disabled = false; btn.textContent = 'Subscribe Free'; }}
  }}
</script>
</body>
</html>"""


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--render", action="store_true", help="Render HTML only, skip content generation")
    args = parser.parse_args()

    total = len(SCAM_CATEGORIES)

    if not args.render:
        import requests
        for i, cat in enumerate(SCAM_CATEGORIES, 1):
            json_path = DATA_DIR / f"{cat['slug']}.json"
            if json_path.exists():
                print(f"  [{i}/{total}] {cat['name']} — cached, skipping")
                continue

            print(f"  [{i}/{total}] Generating: {cat['name']}...")
            try:
                data = generate_content(cat["slug"], cat["name"])
                json_path.write_text(json.dumps(data, indent=2))
                print(f"    Saved: {json_path}")
            except Exception as e:
                print(f"    ERROR: {e}")
                continue

    # Render all HTML pages
    rendered = 0
    for cat in SCAM_CATEGORIES:
        json_path = DATA_DIR / f"{cat['slug']}.json"
        if not json_path.exists():
            print(f"  Skipping {cat['slug']} — no JSON data")
            continue

        data = json.loads(json_path.read_text())
        html = render_page(cat["slug"], data)
        out_path = SCAMS_DIR / f"{cat['slug']}.html"
        out_path.write_text(html)
        rendered += 1
        print(f"  Rendered: {out_path.name}")

    print(f"\nDone — {rendered}/{total} pages rendered")


if __name__ == "__main__":
    main()
