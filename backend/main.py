import os
import asyncio
import httpx
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
BACKEND_DIR = BASE_DIR / "backend"
TEMPLATES_DIR = BASE_DIR / "templates"

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
print(GITHUB_CLIENT_ID)
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
print(GITHUB_CLIENT_SECRET)
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
print(GITHUB_REDIRECT_URI)

app = FastAPI(
    title="First-Commit",
    description="AI onboarding agent for junior developers making their first safe pull request.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the primary login screen."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"app_name": "First-Commit"},
    )


@app.get("/auth/github")
async def github_login():
    """Step 1: Redirect the browser to GitHub's OAuth authorization page."""
    params = (
        f"client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=read:user%20repo"
    )
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?{params}"
    )


@app.get("/auth/github/callback", response_class=HTMLResponse)
async def github_callback(request: Request, code: str | None = None, error: str | None = None):
    """Step 2: GitHub redirects back here with a temporary `code`.
    Exchange it for an access token, then fetch the user's profile and repos.
    """
    # --- handle OAuth denial ---
    if error or not code:
        return RedirectResponse(url="/")

    # --- exchange code for access token ---
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
        # token exchange failed – send back to login
        return RedirectResponse(url="/")

    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # --- fetch user profile and repositories concurrently ---
    async with httpx.AsyncClient() as client:
        user_resp, repos_resp = await asyncio.gather(
            client.get("https://api.github.com/user",           headers=auth_headers),
            client.get("https://api.github.com/user/repos?sort=updated&per_page=50", headers=auth_headers),
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


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Direct dashboard route (used post-auth; in production guard with session middleware)."""
    return RedirectResponse(url="/")


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "first-commit"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
