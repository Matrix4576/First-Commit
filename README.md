# First-Commit

> **AI-Powered Codebase Onboarding Agent** — Taking junior developers from *"I just joined and have no idea what this codebase does"* to *"I understand the architecture, found a safe issue, and made my first pull request."*

---

## Overview

Joining a new engineering team often means staring at hundreds of files with zero documentation and high fear of breaking production. Junior developers struggle with three core questions:
1. **What does this repository actually do, and where does data enter and flow?**
2. **Which files are safe to read and edit vs. core systems that shouldn't be touched?**
3. **Which open issues are truly beginner-friendly with near-zero blast radius?**

**First-Commit** solves this with an AI agent tailored for developer onboarding. By analyzing file trees, configuration files, and GitHub issues with Google Gemini, First-Commit generates an architectural briefing, classifies open issues by blast radius, and provides an in-context AI assistant scoped strictly to the chosen codebase.

---

## Core Features

- **GitHub OAuth 2.0 Integration**
  - Seamless authentication allowing access to user repositories (both public and private).
  - Secure signed session cookies with zero client-side credential exposure.

- **Developer Dashboard & Repository Picker**
  - Clean repository browser displaying visibility badges, primary language, stars, forks, and open issues.
  - Live client-side repository search and filter.
  - Radio-style single selection with a persistent bottom tray to launch codebase analysis.

- **Fullscreen Architecture Loading Experience**
  - High-aesthetic "Trusted IDE" loading screen while Gemini runs server-side analysis.
  - Live 4-step progress checklist with spinners and checkmarks tracking tree traversal, module mapping, issue classification, and briefing synthesis.

- **AI Codebase Briefing (Powered by Gemini 3.6 Flash)**
  - Executive summary explaining the repository's purpose in plain English.
  - Automatically detected tech stack tags.
  - High-level data flow diagram/explanation.
  - Recommended beginner entry points (exact files to read first).
  - Explicit **"Do Not Touch"** risk guardrails highlighting sensitive files (auth, database migrations, CI/CD).

- **Visual Architecture Map**
  - Modular layers mapped out with individual responsibilities.
  - Color-coded risk indicators:
    - `Safe` (green) — isolated utilities, documentation, presentation
    - `Caution` (amber) — business logic, internal state
    - `Danger` (red) — core engines, protocols, database schemas
  - Clickable file path chips for quick navigation.

- **Issue Discovery & Blast Radius Scoring**
  - GitHub issue triage using AI evaluation.
  - Blast radius classification (`Safe`, `Caution`, `Danger`) based on affected scope.
  - Difficulty assessment (`Beginner`, `Intermediate`, `Advanced`).
  - Clear rationale explaining why each issue is or isn't suitable for a newcomer.
  - Interactive filtering by risk and sorting by safety, difficulty, or issue number.

- **Scoped Repository AI Chat**
  - In-browser interactive chat assistant with repository structure context.
  - Hard guardrails: refuses off-topic queries and focuses exclusively on explaining the target codebase.
  - Quick-prompt hint chips for common newcomer questions (*"Where to start?"*, *"Safest issue?"*, *"Data flow?"*).

- **Editor Integration Previews ("Add to IDE")**
  - Navigation bar dropdown and banner highlighting upcoming editor extensions for VS Code, JetBrains (IntelliJ / PyCharm), Neovim, Cursor, and Zed.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Jinja2 Templates, httpx (async) |
| **AI Engine** | Google Gemini API via `google-genai` SDK (`gemini-3.6-flash`) |
| **Authentication** | GitHub OAuth 2.0, Starlette signed cookies via `itsdangerous` |
| **Frontend** | Semantic HTML5, Pure CSS3 (zero external frameworks), Vanilla JavaScript |
| **Icons & Fonts** | FontAwesome 6 CDN, Inter & JetBrains Mono typography |
| **Caching** | In-memory LRU Cache with TTL (30 minutes) to minimize token consumption |

---

## Repository Structure

```
First-Commit/
├── backend/
│   ├── __init__.py          # Package marker
│   ├── .env                 # Environment variables (GitHub OAuth & Gemini API)
│   ├── analyser.py          # Gemini AI pipeline: file tree fetch, architecture mapping, issue triage, chat
│   └── main.py              # FastAPI application: routes, auth callback, session management, endpoints
├── templates/
│   ├── login.html           # Authentication landing page
│   ├── dashboard.html       # Repository selection dashboard & loading screen
│   └── analyse.html         # Codebase architecture report, issues board & AI chat
├── static/
│   └── css/
│       ├── style.css        # Global design tokens, typography, and utility classes
│       ├── login.css        # Login page layout and aesthetic styles
│       ├── dashboard.css    # Dashboard workspace, sidebar, cards, and overlay styles
│       └── analyse.css      # Architecture view, issue cards, chat interface styles
├── design_philosophy.md     # Design system documentation ("The Trusted IDE")
├── README.md                # Project documentation
└── LICENSE                  # License file
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10 or higher installed.
- A GitHub account.
- A Google Gemini API key (from Google AI Studio).

### 2. Register GitHub OAuth App
1. Go to [GitHub Developer Settings → OAuth Apps](https://github.com/settings/developers).
2. Click **New OAuth App**.
3. Set the following fields:
   - **Application name**: `First-Commit`
   - **Homepage URL**: `http://127.0.0.1:8000`
   - **Authorization callback URL**: `http://127.0.0.1:8000/auth/github/callback`
4. Copy the generated **Client ID** and generate a **Client Secret**.

### 3. Installation
Clone the repository and install the dependencies:

```bash
git clone https://github.com/Matrix4576/First-Commit.git
cd First-Commit

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install required packages
pip install fastapi uvicorn httpx python-dotenv jinja2 itsdangerous google-genai pydantic
```

### 4. Configuration
Create a `.env` file in the `backend/` directory:

```ini
# backend/.env
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
GITHUB_REDIRECT_URI=http://127.0.0.1:8000/auth/github/callback
GEMINI_API=your_gemini_api_key_here
SESSION_SECRET=a_random_secure_secret_string
```

### 5. Running the Application
Start the development server:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Login page with GitHub OAuth entry point |
| `GET` | `/auth/github` | Redirects to GitHub OAuth authorization |
| `GET` | `/auth/github/callback` | OAuth callback exchanging code for token, loads user repos, sets session cookie |
| `GET` | `/dashboard` | Session-aware dashboard displaying user repositories |
| `POST` | `/repo/select` | Captures selected repository and redirects to analysis view |
| `GET` | `/analyse/{owner}/{repo}` | Runs Gemini analysis & issue classification, renders analysis report |
| `GET` | `/analyse/{owner}/{repo}/json` | Debug endpoint returning raw JSON output of analysis and classified issues |
| `POST` | `/analyse/{owner}/{repo}/chat` | Contextual AI chat endpoint for repository questions |
| `DELETE` | `/analyse/{owner}/{repo}/cache` | Force-invalidates cached analysis for a given repository |
| `GET` | `/cache/stats` | In-memory cache hit/miss statistics |
| `GET` | `/health` | Health check endpoint returning service status |

---

## Design System: "The Trusted IDE"

First-Commit follows strict UI principles modeled after high-productivity developer tools (VS Code, JetBrains):
- **Dark Palette**: `#0d1117` (primary canvas), `#161b22` (cards/surfaces), `#30363d` (borders).
- **Semantic Safety Palette**:
  - `Safe` (`#34d399`): Beginner-friendly code paths, zero-blast-radius issues.
  - `Caution` (`#fbbf24`): Moderate complexity, touches logic in one module.
  - `Danger` (`#f43f5e`): High risk, core architecture, shared state.
  - `Blue` (`#60a5fa`): Primary actions, AI briefing highlights.
- **Zero Framework Bloat**: Pure HTML5 and CSS3 without frontend library overhead for instant load times and pixel-perfect responsiveness.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
