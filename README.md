# Simple GitHub Pages Website

This is a minimal personal website with content managed in Markdown files.

## Content management (Markdown-first)

Edit only these files to update site content:
- `content/hero.md`
- `content/about.md`
- `content/contacts.md`

Layout and behavior files:
- `index.html` (page shell)
- `styles.css` (design)
- `app.js` (loads Markdown content)

## AI chat popup

The site includes a bottom-right AI chat popup.

How to connect:
1. Open the website.
2. Click `AI Chat`.
3. Set `apiUrl` in `chat.config.js` to your backend endpoint URL (`.../chat`).
4. Keep `allowBrowserKey: false` for production.

Notes:
- The key is stored in your browser `localStorage` on your device.
- Do not hardcode API keys in this repo, because GitHub Pages is public/static.
- For production-grade security, use a backend proxy endpoint instead of browser-direct API calls.

Troubleshooting:
- If chat UI looks unstyled, clear browser cache and hard refresh.
- If using backend mode, verify CORS and endpoint response format: `{ \"reply\": \"...\" }`.

## Backend (Render)

Backend files are in `backend/`:
- `backend/app.py`
- `backend/requirements.txt`
- `backend/.env.example`

### Deploy on Render (free plan)

1. Push this repo to GitHub.
2. In Render dashboard, click **New +** -> **Web Service**.
3. Connect your GitHub repo.
4. Configure service:
   - **Environment**: Python
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Add environment variables:
   - `OPENAI_API_KEY` = your OpenAI secret key
   - `OPENAI_MODEL` = `gpt-4o-mini`
   - `ALLOWED_ORIGINS` = `https://idisappear.github.io`
6. Deploy and wait until service is live.
7. Open `https://<your-render-service>.onrender.com/health` and confirm it returns `{\"ok\":true}`.
8. Update `chat.config.js`:
   - `apiUrl: \"https://<your-render-service>.onrender.com/chat\"`
9. Commit/push frontend changes and hard refresh your GitHub Pages site.

### Optional Blueprint deploy

This repo includes `render.yaml`, so you can also use Render Blueprint deploy.

## Publish on GitHub Pages

1. Push this repo to GitHub.
2. Open your repository on GitHub.
3. Go to **Settings** -> **Pages**.
4. Under **Build and deployment**, choose:
   - **Source**: Deploy from a branch
   - **Branch**: `main` and `/ (root)`
5. Save and wait about 1-2 minutes.
6. Your site will be live at:
   - `https://<your-username>.github.io/<repo-name>/`

If this repo is named `<your-username>.github.io`, then the URL is:
- `https://<your-username>.github.io/`
