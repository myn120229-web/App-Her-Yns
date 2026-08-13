# unemployed — Codespaces edition (remote-only)

A rebuild of the [unemployed](https://unemployed-eight.vercel.app) job-hunting
tool, restructured to run inside a **GitHub Codespace** instead of your own
laptop, and scoped to **worldwide-remote roles only**. Same idea: it finds
roles, filters and scores them against what you've actually done, and writes
a resume — all with a local model, no account, no API key.

> This is an independent reimplementation built from the original's public
> description, not a copy of its source. Some details (exact filter
> heuristics, prompt wording) will differ.

## Why no LinkedIn

LinkedIn doesn't offer a public jobs-search API to individual developers,
and scraping their site — even through a third-party tool — breaks their
Terms of Service and risks the account or IP being blocked. So instead of
scraping LinkedIn, this pulls from five boards that publish their listings
through **their own free, public, keyless APIs**: Remotive, Arbeitnow,
RemoteOK, We Work Remotely, and Jobicy, plus any specific companies' own
Greenhouse/Lever/Ashby/SmartRecruiters boards you add. That combination
gets close to LinkedIn-level breadth for remote roles without touching
LinkedIn at all — same approach the "anotherjob" tool you referenced
actually uses under the hood.

## What it does

| # | Feature | Where |
|---|---|---|
| 1 | Pulls from 5 public remote-job-board APIs (worldwide) + any Greenhouse/Lever/Ashby/SmartRecruiters company you add, or paste a JD | **2 · Build your pipeline** |
| 2 | Filters on worldwide-remote status, seniority ceiling, years required, function — every drop shows the rule that caused it | same tab, results in **3 · Matches** |
| 3 | Scores each job 0–100 from 5 weighted parts (required skills, preferred skills, keywords, meaning, stated preferences) | **3 · Matches** |
| 4 | Writes a one-page PDF resume, every bullet traced to your knowledge base, invented numbers dropped and replaced with a verbatim fallback | **4 · Resume** |
| 5 | Rewrites your own LaTeX resume's `\item` bullets in place, leaving anything unverifiable untouched | **5 · LaTeX resume** |
| 6 | Builds targeted LinkedIn search links (alumni-first) + drafts a short outreach message + suggests one project to build | **6 · Find who to talk to** |

## Quickstart

1. Click **Code → Codespaces → Create codespace on main** on this repo.
2. Wait for `onCreateCommand` to finish — it installs Python deps, installs
   Ollama, and pulls a small model (`qwen2.5:3b`, ~2GB). This takes several
   minutes the first time.
3. In the terminal:
   ```bash
   streamlit run app.py --server.address 0.0.0.0
   ```
4. A popup offers to open the forwarded port (8501) in your browser. Use that.
5. Go to **1 · Profile & knowledge base** first and fill in your real
   accomplishments — this is the file everything else depends on.

If Ollama isn't responding (sidebar will say so), run:
```bash
bash .devcontainer/start_ollama.sh
```

## Pushing this to your own GitHub

This build doesn't push to GitHub itself, and can't drive a third-party
Telegram bot — the container this was built in has no network access and
no integration with outside bots. The normal path:

```bash
cd unemployed-clone
git init
git add .
git commit -m "unemployed - codespaces edition"
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Then open it as a Codespace from that repo. If you have your own automation
(a Telegram bot or otherwise) that pushes local folders to GitHub for you,
feed it this same folder — nothing about the app depends on how it got into
your repo.

## Where your data lives

Everything is JSON on this container's own disk under `data/`:
- `data/profile.json` — your knowledge base, filters, preferences (git-ignored)
- `data/companies.json` — companies you're tracking (git-ignored)
- `data/jobs.json` — fetched/filtered/scored postings (git-ignored)

The only network calls this app makes are to the four ATS platforms' public
job-board APIs (the same ones your browser calls when you open a careers
page) and to your own Ollama server on `127.0.0.1:11434`. Nothing about you
is sent anywhere else. If you push this repo, your personal data doesn't go
with it — `.gitignore` excludes those three files.

## Honest limitations vs. the original

- **No LinkedIn.** See "Why no LinkedIn" above — deliberate, not an
  oversight.
- **Remote-only, hard-coded.** There's no region filter anymore; the app
  assumes worldwide-remote everywhere (fetching, filtering, scoring). If
  you also want on-site/hybrid roles in a specific city, that's a bigger
  change — ask and I'll add a toggle back.
- **The 5 remote boards' free tiers ask for attribution** (link back to the
  original posting) if you redistribute their listings — the UI already
  links every job back to its source, so you're covered by default; don't
  strip those links out if you customize the UI.
- **Company search isn't a real name→ATS lookup.** There's no public API for
  that. "Search a company" tries your input as a slug against all four
  platforms live and shows what it finds — this works well for most
  companies once you know (or guess) their careers-page slug, but it's not
  the same as a curated 90-company index.
- **The LaTeX rewriter works on `\item` lines specifically.** If your resume
  template doesn't use `itemize`/`\item` for bullets, it won't find anything
  to rewrite yet.
- **PDF compilation for `.tex` isn't done in-container.** No TeX distribution
  is installed by default (it's a multi-GB install). Download the rewritten
  `.tex` and paste it into Overleaf, or `sudo apt install texlive-full` in
  the Codespace if you want it local.
- **Outreach never touches LinkedIn's API or scrapes anything.** It builds
  search URLs you open and run yourself, exactly like the original describes.
- **Local model quality.** `qwen2.5:3b` is small enough to run acceptably on
  a free-tier Codespace (4 cores / 8GB). It's noticeably less sharp than
  a frontier hosted model — expect to review its scoring reasons and bullet
  drafts, not blindly trust them. Swap `UNEMPLOYED_MODEL` in
  `.devcontainer/setup.sh` for a larger model if your Codespace machine type
  has the RAM for it.

## Changing the model

```bash
ollama pull llama3.1:8b
export UNEMPLOYED_MODEL=llama3.1:8b   # then restart streamlit
```

## Project layout

```
app.py                   Streamlit UI (all 6 sections)
app/
  ats_fetchers.py         Greenhouse / Lever / Ashby / SmartRecruiters clients
  remote_boards.py     Remotive / Arbeitnow / RemoteOK / We Work Remotely / Jobicy clients
  filters.py               worldwide-remote / seniority / years / function filtering
  scorer.py                 5-part weighted LLM scoring
  resume_writer.py       knowledge-base-traced PDF resume generation
  latex_resume.py         in-place \item rewriting for your own LaTeX template
  outreach.py               search-link builder + message drafting
  llm_client.py             Ollama wrapper (JSON-mode, retries)
  data_store.py             JSON file storage
  profile.example.json  starter profile, copied to data/profile.json on first run
.devcontainer/
  devcontainer.json       Codespaces config
  setup.sh                    one-time: installs deps, Ollama, pulls model
  start_ollama.sh         runs on every codespace start
```
