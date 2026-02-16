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

How to connect your OpenAI account:
1. Open the website.
2. Click `AI Chat`.
3. Paste your OpenAI API key (`sk-...`) into the key field.
4. Click `Connect`.

Notes:
- The key is stored in your browser `localStorage` on your device.
- Do not hardcode API keys in this repo, because GitHub Pages is public/static.
- For production-grade security, use a backend proxy endpoint instead of browser-direct API calls.

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
