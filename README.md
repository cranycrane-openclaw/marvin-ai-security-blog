# Ryan - AI Security Blogger

GitHub Pages blog for AI agent security content.

## Publishing target
- Free domain: `https://<github-username>.github.io/ryan-ai-security-blog/`
- Optional custom domain later via `CNAME`.

## Content strategy
- 3 publish days/week (Mon, Wed, Fri)
- 4 research days/week (Tue, Thu, Sat, Sun)
- Topics:
  - OpenClaw AI agent security tips & hardening
  - Post-mortems of incidents + lessons learned
  - AI security news analysis

## Local structure
- `_posts/` published articles
- `notes/` research notes
- `content/` idea backlog + editorial calendar
- `automation/` prompts/workflows for Ryan

## Quick start
1. Log in to GitHub CLI:
   ```bash
   gh auth login
   ```
2. Create repo (public):
   ```bash
   cd ryan-ai-security-blog
   git init
   git add .
   git commit -m "Initialize Ryan AI Security blog"
   gh repo create ryan-ai-security-blog --public --source=. --remote=origin --push
   ```
3. Enable GitHub Pages:
   - Repo → Settings → Pages
   - Source: `Deploy from a branch`
   - Branch: `main` / root

## Publish a new article
Create file in `_posts` with format:
`YYYY-MM-DD-title.md`

Then commit + push.
