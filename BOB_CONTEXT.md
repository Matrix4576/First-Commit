# BOB_CONTEXT.md — First-Commit Project Context
> Persistent reference for the AI coding partner. Updated as the project evolves.

---

## Project Mission
**First-Commit** is an AI-powered developer onboarding agent. It takes a junior developer through:
1. GitHub OAuth login → authenticate
2. Repo selection → pick a codebase to onboard into
3. Architecture analysis → AI maps the codebase visually (files, modules, data flow)
4. Safe issue discovery → AI surfaces beginner-friendly issues with near-zero blast radius
5. First PR guidance → step-by-step LLM guidance to submit first production-ready pull request

**Target user:** Confused freshers / junior devs who just joined a company and need to understand a messy codebase safely.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.x, FastAPI, Jinja2 templates, httpx (async) |
| Frontend | Vanilla HTML + Pure CSS (NO React, NO Tailwind in current impl) |
| Icons | FontAwesome CDN (`https://kit.fontawesome.com/a10bb03e8b.js`) |
| Fonts | Inter (UI), JetBrains Mono (code) via Google Fonts |
| Auth | GitHub OAuth 2.0 (backend redirect flow) |
| Config | python-dotenv — `backend/.env` holds secrets |

**IMPORTANT:** The `design_philosophy.md` references React + Tailwind + lucide-react — that is the LLM code-gen spec for component ideation. The actual running app uses **pure HTML/CSS and FontAwesome**.

---

## File Map

```
First-Commit/
├── backend/
│   ├── main.py              # FastAPI app — all routes, OAuth, session, analysis trigger, chat
│   ├── analyser.py          # ✅ Gemini 2.0 Flash pipeline: analyse_repo / fetch_issues / chat_with_repo
│   └── __init__.py
├── templates/
│   ├── login.html           # Page 1: GitHub OAuth login UI
│   ├── dashboard.html       # Page 2: Repo picker (sidebar list + card grid)
│   └── analyse.html         # ✅ Page 3: Architecture briefing + issues board + AI chatbox
├── static/
│   └── css/
│       ├── style.css        # Global CSS variables + utility classes
│       ├── login.css        # Login page styles
│       ├── dashboard.css    # Dashboard styles
│       └── analyse.css      # ✅ Analysis page styles
├── design_philosophy.md     # Full UI/UX design system spec (READ for styling)
├── BOB_CONTEXT.md           # This file
└── README.md
```

---

## Current Routes (backend/main.py)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves `login.html` |
| GET | `/auth/github` | Redirects to GitHub OAuth authorize URL |
| GET | `/auth/github/callback` | Exchanges code for token, fetches user + repos, sets session cookie, serves `dashboard.html` |
| GET | `/dashboard` | Redirects to `/` (placeholder) |
| GET | `/health` | Health check → `{"status": "healthy"}` |
| POST | `/repo/select` | ✅ Receives chosen repo, updates session cookie, redirects to `/analyse/{owner}/{repo}` |
| GET | `/analyse/{owner}/{repo}` | ✅ Runs analyse_repo + fetch_issues in parallel, renders `analyse.html` |
| GET | `/analyse/{owner}/{repo}/json` | ✅ Returns raw JSON of analysis + issues (debug endpoint) |
| POST | `/analyse/{owner}/{repo}/chat` | ✅ Chat endpoint — body: `{message, history[]}` → `{reply}` |

---

## Design System (from design_philosophy.md + style.css)

### CSS Variables (defined in style.css :root)
```css
--bg-primary: #0d1117        /* main app background */
--bg-secondary: #161b22      /* sidebar, cards */
--bg-card: #161b22
--bg-subtle: #21262d

--border-default: #30363d
--border-muted: #21262d

--text-primary: #f0f6fc
--text-secondary: #c9d1d9
--text-muted: #8b949e
--text-subtle: #484f58

/* Safety Palette — SEMANTIC, not decorative */
--safe-color: #34d399         /* green — beginner safe, success */
--safe-bg: rgba(52,211,153,0.1)
--safe-border: rgba(52,211,153,0.2)

--amber-color: #fbbf24        /* amber — intermediate, caution */
--amber-bg: rgba(251,191,36,0.1)
--amber-border: rgba(251,191,36,0.2)

--danger-color: #f43f5e       /* red — high risk, do not touch */
--danger-bg: rgba(244,63,94,0.1)
--danger-border: rgba(244,63,94,0.2)

--blue-color: #60a5fa         /* blue — AI insights, primary CTA */
--blue-bg: rgba(96,165,250,0.1)
--blue-border: rgba(96,165,250,0.2)

--font-sans: 'Inter', system-ui
--font-mono: 'JetBrains Mono', 'Fira Code', monospace
```

### Layout Pattern
- **Top nav** (60px, sticky, `backdrop-filter: blur(8px)`, `border-bottom`)
- **Workspace** = sidebar (280px) + main panel (flex: 1)
- **IDE status footer** (32px, monospace, branch indicator)

---

## Data Flow (Current)

```
User → GET /
     ← login.html

User clicks "Continue with GitHub"
     → GET /auth/github
     ← Redirect to github.com/login/oauth/authorize

GitHub → GET /auth/github/callback?code=XYZ
       → POST github.com/login/oauth/access_token  (exchange code)
       → GET api.github.com/user                   (parallel, asyncio.gather)
       → GET api.github.com/user/repos?sort=updated&per_page=50  (parallel)
       ← dashboard.html (user + repos injected via Jinja2)

User selects repo → clicks "Begin Analysis"
     → POST /repo/select  ← NOT IMPLEMENTED
```

**Token handling:** `access_token` is currently passed into the Jinja2 template context only.
It is NOT stored in a session, cookie, or DB. Needs to be persisted for subsequent API calls.

---

## What Needs to Be Built (Roadmap)

### Phase 1 — Repo Selection → Analysis Trigger ← NEXT
- [ ] `POST /repo/select` endpoint — receive `repo_full_name`, store `access_token` + repo in session/cookie
- [ ] Session/token persistence (signed cookie or server-side session)

### Phase 2 — Architecture Analysis Page
- [ ] New route `GET /analyse/{owner}/{repo}`
- [ ] New template `templates/analyse.html` + `static/css/analyse.css`
- [ ] GitHub API calls: fetch repo tree (`GET /repos/{owner}/{repo}/git/trees/HEAD?recursive=1`), languages
- [ ] LLM call to generate architecture summary (file structure → module map → data flow explanation)
- [ ] Visual architecture graph component (boxes + lines, IDE style)
- [ ] "Explanation mode" toggle: Casual vs Technical

### Phase 3 — Issue Discovery Page
- [ ] Fetch open issues: `GET /repos/{owner}/{repo}/issues?state=open&per_page=100`
- [ ] LLM classifies each issue: blast radius (safe/amber/danger), beginner-friendliness score
- [ ] New template `templates/issues.html` — issue board with risk badges
- [ ] Filter/sort by safety level

### Phase 4 — First PR Mission Plan
- [ ] User selects a safe issue
- [ ] LLM generates step-by-step mission plan: files to edit, what to change, how to test
- [ ] New template `templates/mission.html`
- [ ] Inline code explanation panel

---

## Key Conventions & Rules

1. **New HTML pages** → `templates/pagename.html` (Jinja2)
2. **New CSS** → `static/css/pagename.css`, linked in the template
3. **All colors** must use CSS variables from `style.css` — never hardcode hex in new files
4. **Safety colors are semantic** — green=safe, amber=caution, red=danger, blue=AI/info
5. **Font classes:** `font-family: var(--font-mono)` for all code/paths/hashes
6. **No JS frameworks** — vanilla JS only, in `(function(){})()` block at bottom of template
7. **Icons:** FontAwesome classes (`fa-solid fa-*`, `fa-brands fa-*`)
8. **All backend routes** in `backend/main.py` for now
9. **Env vars** loaded from `backend/.env` via python-dotenv

---

## GitHub API Reference

```python
# Auth headers (used in every GitHub API call)
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Key endpoints
GET /user                                              # authenticated user
GET /user/repos?sort=updated&per_page=50              # user's repos
GET /repos/{owner}/{repo}/git/trees/HEAD?recursive=1  # full file tree
GET /repos/{owner}/{repo}/languages                   # language breakdown
GET /repos/{owner}/{repo}/issues?state=open&per_page=100  # open issues
GET /repos/{owner}/{repo}/contents/{path}             # read a file (base64)
GET /repos/{owner}/{repo}/pulls                       # pull requests
```

---

## LLM Integration Notes (TBD)
- No LLM provider locked yet — keep AI calls in an abstracted helper function
- Expected inputs for architecture analysis: file tree + top-level README content
- Expected inputs for issue classification: issue title + body + labels
- Output format: JSON with fields like `blast_radius`, `beginner_score`, `explanation`

---

## Session Strategy (To Implement)
Options (pick one):
- **Signed cookie** — store `{"access_token": "...", "repo": "owner/name"}` encrypted with `itsdangerous`
- **Server-side** — `starlette-session` with in-memory or Redis backend
- **Simple approach for hackathon** — pass token as hidden field through form POSTs, re-embed in each page's Jinja context

Recommendation for hackathon speed: **signed cookie via `itsdangerous`** — no extra infra needed.

---

*Last updated: Session 2 — BOB_CONTEXT.md created. Login + dashboard complete. AI pipeline not started.*
