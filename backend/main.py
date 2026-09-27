import os
import asyncio
import httpx
from pathlib import Path
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from itsdangerous import URLSafeSerializer, BadSignature
from pydantic import BaseModel

from backend.analyser import analyse_repo, fetch_issues, chat_with_repo, invalidate_cache, _analysis_cache, _issues_cache

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
BACKEND_DIR = BASE_DIR / "backend"

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

GITHUB_CLIENT_ID     = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI  = os.getenv("GITHUB_REDIRECT_URI")
SESSION_SECRET       = os.getenv("SESSION_SECRET", "change-me-in-production")

_signer = URLSafeSerializer(SESSION_SECRET, salt="session")

SESSION_COOKIE = "fc_session"


def _set_session(response, data: dict) -> None:
    """Serialise `data` into a signed cookie on `response`."""
    response.set_cookie(
        key=SESSION_COOKIE,
        value=_signer.dumps(data),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,   # 8 hours
    )


def _get_session(request: Request) -> dict | None:
    """Read and verify the signed session cookie. Returns None if missing/invalid."""
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        return _signer.loads(raw)
    except BadSignature:
        return None


app = FastAPI(
    title="First-Commit",
    description="AI onboarding agent for junior developers making their first safe pull request.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ─────────────────────────────────────────────
#  LOGIN / AUTH
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"app_name": "First-Commit"},
    )


@app.get("/auth/github")
async def github_login():
    params = (
        f"client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=read:user%20repo"
    )
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?{params}"
    )


@app.get("/auth/github/callback", response_class=HTMLResponse)
async def github_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
):
    if error or not code:
        return RedirectResponse(url="/")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id":     GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code":          code,
                "redirect_uri":  GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
        )

    token_data   = token_resp.json()
    access_token = token_data.get("access_token", "")

    if not access_token:
        return RedirectResponse(url="/")

    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient() as client:
        user_resp, repos_resp = await asyncio.gather(
            client.get("https://api.github.com/user", headers=auth_headers),
            client.get(
                "https://api.github.com/user/repos?sort=updated&per_page=50",
                headers=auth_headers,
            ),
        )

    user  = user_resp.json()
    repos = repos_resp.json() if isinstance(repos_resp.json(), list) else []

    response = templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "app_name":     "First-Commit",
            "user":         user,
            "repos":        repos,
            "access_token": access_token,
        },
    )
    # Persist the token in a signed cookie so subsequent pages can use it
    _set_session(response, {"access_token": access_token, "github_login": user.get("login", "")})
    return response


# ─────────────────────────────────────────────
#  REPO SELECTION
# ─────────────────────────────────────────────

@app.post("/repo/select")
async def repo_select(
    request: Request,
    repo_full_name: str = Form(...),
    repo_name: str      = Form(...),
):
    """
    Receive the chosen repository from the dashboard form.
    Saves the selection to the session cookie and redirects to the analysis page.
    """
    session = _get_session(request)
    if not session:
        # Token lost — send user back to login
        return RedirectResponse(url="/", status_code=303)

    # repo_full_name is "owner/repo-name"
    parts = repo_full_name.split("/", 1)
    if len(parts) != 2:
        return RedirectResponse(url="/dashboard", status_code=303)

    owner, repo = parts

    # Update session with selected repo
    session["selected_repo"] = repo_full_name
    redirect = RedirectResponse(
        url=f"/analyse/{owner}/{repo}",
        status_code=303,
    )
    _set_session(redirect, session)
    return redirect


# ─────────────────────────────────────────────
#  ANALYSIS
# ─────────────────────────────────────────────

@app.get("/analyse/{owner}/{repo}", response_class=HTMLResponse)
async def analyse_page(request: Request, owner: str, repo: str):
    """
    Trigger the AI codebase analysis for owner/repo.
    Runs analysis + issue classification in parallel, renders analyse.html.
    """
    session = _get_session(request)
    if not session or not session.get("access_token"):
        return RedirectResponse(url="/", status_code=303)

    access_token = session["access_token"]

    # Run architecture analysis and issue classification in parallel
    analysis, issues = await asyncio.gather(
        analyse_repo(owner, repo, access_token),
        fetch_issues(owner, repo, access_token),
    )

    return templates.TemplateResponse(
        request=request,
        name="analyse.html",
        context={
            "app_name":     "First-Commit",
            "owner":        owner,
            "repo":         repo,
            "analysis":     analysis,
            "issues":       issues,
            "github_login": session.get("github_login", ""),
        },
    )


@app.get("/analyse/{owner}/{repo}/json")
async def analyse_json(request: Request, owner: str, repo: str):
    """Raw JSON debug endpoint — returns analysis + classified issues."""
    session = _get_session(request)
    if not session or not session.get("access_token"):
        return JSONResponse({"error": "not authenticated"}, status_code=401)

    access_token = session["access_token"]
    analysis, issues = await asyncio.gather(
        analyse_repo(owner, repo, access_token),
        fetch_issues(owner, repo, access_token),
    )
    return JSONResponse({"analysis": analysis, "issues": issues})


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/analyse/{owner}/{repo}/chat")
async def analyse_chat(request: Request, owner: str, repo: str, body: ChatRequest):
    """
    Chatbox endpoint. Receives a user message + conversation history,
    returns the AI reply as JSON.
    """
    session = _get_session(request)
    if not session or not session.get("access_token"):
        return JSONResponse({"error": "not authenticated"}, status_code=401)

    reply = await chat_with_repo(
        owner=owner,
        repo=repo,
        access_token=session["access_token"],
        messages=body.history,
        user_message=body.message,
    )
    return JSONResponse({"reply": reply})


# ─────────────────────────────────────────────
#  DASHBOARD  (session-aware, no re-auth needed)
# ─────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """
    Serve the dashboard if the user already has a valid session cookie.
    If no session exists, send them back to login.
    """
    session = _get_session(request)
    if not session or not session.get("access_token"):
        return RedirectResponse(url="/", status_code=303)

    access_token = session["access_token"]
    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        user_resp, repos_resp = await asyncio.gather(
            client.get("https://api.github.com/user", headers=auth_headers),
            client.get(
                "https://api.github.com/user/repos?sort=updated&per_page=50",
                headers=auth_headers,
            ),
        )

    user  = user_resp.json()
    repos = repos_resp.json() if isinstance(repos_resp.json(), list) else []

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "app_name":     "First-Commit",
            "user":         user,
            "repos":        repos,
            "access_token": access_token,
        },
    )


# ─────────────────────────────────────────────
#  CACHE MANAGEMENT
# ─────────────────────────────────────────────

@app.delete("/analyse/{owner}/{repo}/cache")
async def clear_repo_cache(request: Request, owner: str, repo: str):
    """Force-invalidate cached analysis for a repo."""
    session = _get_session(request)
    if not session:
        return JSONResponse({"error": "not authenticated"}, status_code=401)
    invalidate_cache(owner, repo)
    return JSONResponse({"invalidated": f"{owner}/{repo}"})


@app.get("/cache/stats")
async def cache_stats(request: Request):
    """Return cache stats — useful for debugging during the hackathon."""
    session = _get_session(request)
    if not session:
        return JSONResponse({"error": "not authenticated"}, status_code=401)
    return JSONResponse({
        "analysis": _analysis_cache.stats(),
        "issues":   _issues_cache.stats(),
    })


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "first-commit"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

