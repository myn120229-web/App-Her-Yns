"""
unemployed (Codespaces edition) - Streamlit UI.

Run with: streamlit run app.py
Everything reads/writes data/*.json on this container's own disk. The only
network calls are to the ATS job-board APIs (public) and to your local
Ollama server - nothing about you leaves the Codespace.
"""
import json
from pathlib import Path

import streamlit as st

from app import data_store, ats_fetchers, remote_boards, filters, scorer, resume_writer, latex_resume, outreach, llm_client

st.set_page_config(page_title="unemployed (Codespaces edition)", page_icon="🧭", layout="wide")

OUTPUT_DIR = Path(__file__).parent / "data" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- helpers

def ollama_status_banner():
    if llm_client.is_available():
        st.sidebar.success(f"Ollama is running · model: {llm_client.MODEL}")
    else:
        st.sidebar.error(
            "Ollama isn't responding.\n\nIn a terminal, run:\n\n"
            "`bash .devcontainer/start_ollama.sh`\n\n"
            f"then make sure the model is pulled: `ollama pull {llm_client.MODEL}`"
        )


def included_jobs(jobs: dict) -> list[dict]:
    return sorted(
        [j for j in jobs.values() if j.get("included")],
        key=lambda j: j.get("total_score", -1),
        reverse=True,
    )


def excluded_jobs(jobs: dict) -> list[dict]:
    return [j for j in jobs.values() if not j.get("included", True)]


# ---------------------------------------------------------------- sidebar

st.sidebar.title("🧭 unemployed")
st.sidebar.caption("Codespaces edition — free, local model, one file of yours on disk.")
ollama_status_banner()

page = st.sidebar.radio(
    "Section",
    ["1 · Profile & knowledge base", "2 · Build your pipeline", "3 · Matches",
     "4 · Resume", "5 · LaTeX resume", "6 · Find who to talk to"],
)

st.sidebar.divider()
st.sidebar.caption("Your data: `data/profile.json`, `data/companies.json`, `data/jobs.json` — all local, never sent anywhere except your own Ollama and public job-board APIs.")


# ---------------------------------------------------------------- 1. profile

if page.startswith("1"):
    st.header("Profile & knowledge base")
    st.caption("This is the file that decides everything after it. Fill it in properly — ten minutes here saves hours later.")

    profile = data_store.load_profile()

    with st.form("basic_info"):
        c1, c2 = st.columns(2)
        with c1:
            profile["name"] = st.text_input("Name", profile.get("name", ""))
            profile["email"] = st.text_input("Email", profile.get("email", ""))
            profile["phone"] = st.text_input("Phone", profile.get("phone", ""))
            profile["location"] = st.text_input("Location", profile.get("location", ""))
            profile["school"] = st.text_input("School (used for alumni-first outreach)", profile.get("school", ""))
        with c2:
            links = profile.get("links", {})
            links["linkedin"] = st.text_input("LinkedIn", links.get("linkedin", ""))
            links["github"] = st.text_input("GitHub", links.get("github", ""))
            links["portfolio"] = st.text_input("Portfolio", links.get("portfolio", ""))
            profile["links"] = links

        st.subheader("Filters")
        st.caption("This build is scoped to worldwide-remote roles only — every fetch and filter assumes that. No region field to fill in.")
        c4, c5 = st.columns(2)
        with c4:
            profile["years_experience"] = st.number_input("Years of experience", 0, 40, profile.get("years_experience", 0))
        with c5:
            profile["seniority_ceiling"] = st.selectbox(
                "Highest seniority to show", filters.SENIORITY_LEVELS,
                index=filters.SENIORITY_LEVELS.index(profile.get("seniority_ceiling", "Mid")),
            )

        profile["target_functions"] = [
            f.strip() for f in st.text_input(
                "Target functions (comma separated)", ", ".join(profile.get("target_functions", []))
            ).split(",") if f.strip()
        ]
        profile["excluded_functions"] = [
            f.strip() for f in st.text_input(
                "Excluded functions (comma separated)", ", ".join(profile.get("excluded_functions", []))
            ).split(",") if f.strip()
        ]

        st.subheader("Preferences (used for scoring, not hard filters)")
        prefs = profile.get("preferences", {})
        prefs["remote_ok"] = st.checkbox("Remote OK", prefs.get("remote_ok", True))
        prefs["meaning_statement"] = st.text_area("What gives your work meaning?", prefs.get("meaning_statement", ""))
        prefs["other_preferences"] = st.text_area("Other preferences (team size, pace, etc.)", prefs.get("other_preferences", ""))
        prefs["keyword_boosts"] = [
            k.strip() for k in st.text_input("Keyword boosts (comma separated)", ", ".join(prefs.get("keyword_boosts", []))).split(",") if k.strip()
        ]
        prefs["keyword_penalties"] = [
            k.strip() for k in st.text_input("Dealbreaker keywords (comma separated)", ", ".join(prefs.get("keyword_penalties", []))).split(",") if k.strip()
        ]
        profile["preferences"] = prefs

        if st.form_submit_button("Save profile", type="primary"):
            data_store.save_profile(profile)
            st.success("Saved.")

    st.divider()
    st.subheader("Knowledge base")
    st.caption("Every project, internship, hackathon, certification. In detail, with numbers. This is the only source resume bullets and outreach messages are allowed to draw from.")

    kb = profile.get("knowledge_base", [])

    for idx, item in enumerate(kb):
        with st.expander(f"{item.get('title', '(untitled)')}"):
            item["title"] = st.text_input("Title", item.get("title", ""), key=f"kb_title_{idx}")
            item["text"] = st.text_area("Description", item.get("text", ""), key=f"kb_text_{idx}")
            item["skills"] = [s.strip() for s in st.text_input("Skills (comma separated)", ", ".join(item.get("skills", [])), key=f"kb_skills_{idx}").split(",") if s.strip()]
            item["numbers"] = [n.strip() for n in st.text_input("Numbers/metrics (comma separated, copy exactly)", ", ".join(item.get("numbers", [])), key=f"kb_numbers_{idx}").split(",") if n.strip()]
            if st.button("Delete this item", key=f"kb_delete_{idx}"):
                kb.pop(idx)
                profile["knowledge_base"] = kb
                data_store.save_profile(profile)
                st.rerun()

    if st.button("+ Add knowledge-base item"):
        kb.append({"id": f"kb{len(kb)+1}_{len(kb)}", "title": "New item", "text": "", "skills": [], "numbers": []})
        profile["knowledge_base"] = kb
        data_store.save_profile(profile)
        st.rerun()

    if st.button("Save knowledge base", type="primary"):
        profile["knowledge_base"] = kb
        data_store.save_profile(profile)
        st.success("Saved.")


# ---------------------------------------------------------------- 2. pipeline

elif page.startswith("2"):
    st.header("Build your pipeline")
    st.caption("Worldwide-remote only. Reads straight from job-board and ATS public APIs — no scraping, and deliberately nothing from LinkedIn (they don't offer a public jobs API, and scraping their site breaks their Terms of Service).")

    st.subheader("🌍 Remote job boards (worldwide coverage)")
    st.caption("Remotive, Arbeitnow, RemoteOK, We Work Remotely, Jobicy — five boards' own free public APIs, combined.")
    profile_for_kw = data_store.load_profile()
    default_kw = (profile_for_kw.get("preferences", {}).get("keyword_boosts", []) or [""])[0]
    kw = st.text_input("Optional keyword to focus the fetch (e.g. 'backend', 'python')", value=default_kw)
    if st.button("Fetch from all 5 remote boards", type="primary"):
        with st.spinner("Fetching Remotive, Arbeitnow, RemoteOK, We Work Remotely, Jobicy..."):
            board_jobs, errors = remote_boards.fetch_all(keyword=kw)
        for e in errors:
            st.warning(f"One source failed (continuing with the rest): {e}")
        profile = data_store.load_profile()
        filtered = filters.filter_jobs(board_jobs, profile)
        data_store.upsert_jobs(filtered)
        included = sum(1 for j in filtered if j["included"])
        st.success(f"Pulled {len(filtered)} remote postings across 5 boards. {included} passed your filters, {len(filtered)-included} excluded. See **3 · Matches**.")

    st.divider()
    st.subheader("🏢 Specific companies (Greenhouse / Lever / Ashby / SmartRecruiters)")
    st.caption("For when you already have target companies in mind — same worldwide-remote filter applies after fetching.")

    tracked = data_store.load_companies()

    col_add, col_seed = st.columns([2, 1])

    with col_add:
        st.subheader("Add a company")
        name = st.text_input("Company name or careers-page slug (e.g. 'stripe', or the word from jobs.lever.co/<this>)")
        if st.button("Search"):
            with st.spinner("Checking Greenhouse, Lever, Ashby and SmartRecruiters..."):
                hits = ats_fetchers.probe_company(name)
            st.session_state["_probe_hits"] = hits
            st.session_state["_probe_name"] = name

        hits = st.session_state.get("_probe_hits", [])
        if hits:
            st.write(f"Found on:")
            for h in hits:
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{h['ats']}** as `{h['token']}` — {h['job_count']} open roles")
                if c2.button("Add", key=f"add_{h['ats']}_{h['token']}"):
                    data_store.add_company({"name": st.session_state.get("_probe_name", h["token"]), "ats": h["ats"], "token": h["token"]})
                    st.success(f"Added {h['token']} ({h['ats']}).")
                    st.rerun()
        elif "_probe_hits" in st.session_state:
            st.warning("Nothing found under that name on any of the four platforms. Try the exact slug from their careers-page URL.")

    with col_seed:
        st.subheader("Quick-add suggestions")
        st.caption("Unverified — checked live before anything is added.")
        seeds = json.load(open(Path(__file__).parent / "app" / "seed_companies.json"))
        tracked_keys = {(c["ats"], c["token"]) for c in tracked}
        for s in seeds:
            if (s["ats"], s["token"]) in tracked_keys:
                continue
            if st.button(f"+ {s['name']}", key=f"seed_{s['ats']}_{s['token']}"):
                with st.spinner(f"Verifying {s['name']}..."):
                    try:
                        jobs = ats_fetchers.fetch_for_company(s["ats"], s["token"])
                        if jobs:
                            data_store.add_company(s)
                            st.success(f"Added {s['name']} ({len(jobs)} open roles).")
                            st.rerun()
                        else:
                            st.warning(f"{s['name']} returned zero postings right now.")
                    except Exception as e:
                        st.error(f"Couldn't verify {s['name']}: {e}")

    st.divider()
    st.subheader("Tracked companies")
    if not tracked:
        st.info("No companies tracked yet — add some above.")
    for c in tracked:
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{c['name']}** — {c['ats']} / `{c['token']}`")
        if c3.button("Remove", key=f"rm_{c['ats']}_{c['token']}"):
            data_store.remove_company(c["token"], c["ats"])
            st.rerun()

    if tracked and st.button("Fetch + filter jobs from all tracked companies", type="primary"):
        profile = data_store.load_profile()
        all_new = []
        progress = st.progress(0.0, text="Fetching...")
        for i, c in enumerate(tracked):
            try:
                jobs = ats_fetchers.fetch_for_company(c["ats"], c["token"])
                all_new.extend(jobs)
            except Exception as e:
                st.warning(f"Failed to fetch {c['name']}: {e}")
            progress.progress((i + 1) / len(tracked), text=f"Fetched {c['name']}")
        filtered = filters.filter_jobs(all_new, profile)
        data_store.upsert_jobs(filtered)
        included = sum(1 for j in filtered if j["included"])
        st.success(f"Fetched {len(filtered)} postings. {included} passed your filters, {len(filtered) - included} were excluded (see Matches tab for reasons). Head to **3 · Matches** to score them.")

    st.divider()
    st.subheader("Or paste a job description you found elsewhere")
    with st.form("manual_job"):
        mc = st.text_input("Company")
        mt = st.text_input("Title")
        ml = st.text_input("Location")
        mu = st.text_input("URL (optional)")
        md = st.text_area("Full job description text", height=200)
        if st.form_submit_button("Add this job"):
            profile = data_store.load_profile()
            job = {
                "id": f"manual:{mc}:{mt}:{len(md)}",
                "company": mc, "ats": "manual", "title": mt, "location": ml, "url": mu,
                "description_text": md, "posted_at": "",
            }
            job = filters.apply_filters(job, profile)
            data_store.upsert_jobs([job])
            st.success("Added. Check the Matches tab.")


# ---------------------------------------------------------------- 3. matches

elif page.startswith("3"):
    st.header("Matches")
    jobs = data_store.load_jobs()
    inc = included_jobs(jobs)
    exc = excluded_jobs(jobs)

    unscored = [j for j in inc if "total_score" not in j]
    c1, c2 = st.columns([1, 3])
    with c1:
        if unscored and st.button(f"Score {len(unscored)} unscored jobs", type="primary"):
            profile = data_store.load_profile()
            progress = st.progress(0.0)
            for i, j in enumerate(unscored):
                try:
                    result = scorer.score_job(j, profile)
                    data_store.update_job(j["id"], {"total_score": result["total_score"], "score_breakdown": result["breakdown"]})
                except Exception as e:
                    st.warning(f"Couldn't score {j.get('title')}: {e}")
                progress.progress((i + 1) / len(unscored))
            st.rerun()

    st.caption(f"{len(inc)} jobs passed your filters · {len(exc)} were excluded")

    jobs = data_store.load_jobs()
    inc = included_jobs(jobs)

    for j in inc:
        score = j.get("total_score")
        title_line = f"{'⭐ ' if score and score >= 70 else ''}{j['title']} — {j['company']}" + (f" · **{score}/100**" if score is not None else " · not scored yet")
        with st.expander(title_line):
            st.write(f"📍 {j.get('location','')} · [posting]({j.get('url','')})" if j.get('url') else f"📍 {j.get('location','')}")
            if "score_breakdown" in j:
                for key, part in j["score_breakdown"].items():
                    st.write(f"**{key.replace('_',' ')}**: {part['score']}/100 × {part['weight']} = {part['weighted_points']} pts — {part['reason']}")
            st.text_area("Description", j.get("description_text", "")[:2000], height=150, key=f"desc_{j['id']}", disabled=True)

            bc1, bc2 = st.columns(2)
            if bc1.button("Generate resume for this job", key=f"resume_{j['id']}"):
                st.session_state["_resume_target_job_id"] = j["id"]
                st.info("Go to **4 · Resume** — this job is now pre-selected.")
            if bc2.button("Find who to talk to", key=f"outreach_{j['id']}"):
                st.session_state["_outreach_target_job_id"] = j["id"]
                st.info("Go to **6 · Find who to talk to** — this job is now pre-selected.")

    if exc:
        st.divider()
        with st.expander(f"Excluded jobs ({len(exc)}) — and why"):
            for j in exc:
                st.write(f"**{j['title']}** — {j['company']}: " + "; ".join(j.get("exclusion_reasons", [])))


# ---------------------------------------------------------------- 4. resume

elif page.startswith("4"):
    st.header("Resume")
    st.caption("Every bullet traces back to your knowledge base. Anything the model can't verify gets replaced with a plain version built straight from your source data.")

    profile = data_store.load_profile()
    jobs = data_store.load_jobs()
    inc = included_jobs(jobs)

    options = ["(general — not tailored to a specific job)"] + [f"{j['title']} — {j['company']}" for j in inc]
    default_idx = 0
    target_id = st.session_state.get("_resume_target_job_id")
    if target_id and target_id in jobs:
        j = jobs[target_id]
        label = f"{j['title']} — {j['company']}"
        if label in options:
            default_idx = options.index(label)

    choice = st.selectbox("Tailor to which job?", options, index=default_idx)
    job = None
    if choice != options[0]:
        job = inc[options.index(choice) - 1]

    if st.button("Generate resume", type="primary"):
        with st.spinner("Writing and verifying..."):
            out_path = OUTPUT_DIR / "resume.pdf"
            result = resume_writer.generate_resume(profile, job, out_path)
        for w in result["warnings"]:
            st.warning(w)
        st.success(f"Built {len(result['bullets'])} bullets.")
        for b in result["bullets"]:
            tag = "🤖 model" if b["source"] == "model" else "📋 fallback (verbatim from your data)"
            st.write(f"- **{b['title']}** ({tag}): {b['text']}")
        with open(result["pdf_path"], "rb") as f:
            st.download_button("Download resume.pdf", f, file_name="resume.pdf", mime="application/pdf")


# ---------------------------------------------------------------- 5. latex

elif page.startswith("5"):
    st.header("LaTeX resume")
    st.caption("Paste the LaTeX resume you already have. It rewrites \\item bullets in place — anything it can't verify is left exactly as you wrote it.")

    profile = data_store.load_profile()
    jobs = data_store.load_jobs()
    inc = included_jobs(jobs)

    options = ["(general — not tailored to a specific job)"] + [f"{j['title']} — {j['company']}" for j in inc]
    choice = st.selectbox("Tailor to which job?", options)
    job = inc[options.index(choice) - 1] if choice != options[0] else None

    default_tex = st.session_state.get("_latex_source", "")
    tex_source = st.text_area("Your LaTeX source", value=default_tex, height=300, placeholder=r"""\documentclass{article}
\begin{document}
\begin{itemize}
  \item Built a thing that did a thing
\end{itemize}
\end{document}""")

    if st.button("Rewrite", type="primary"):
        with st.spinner("Rewriting bullets and verifying against your knowledge base..."):
            result = latex_resume.rewrite_latex(tex_source, profile, job)
        st.session_state["_latex_source"] = tex_source
        st.success(f"Rewrote {result['changed_count']} of {result.get('total_bullets', 0)} bullets.")
        for w in result["warnings"]:
            st.warning(w)
        st.code(result["latex"], language="latex")
        st.download_button("Download resume.tex", result["latex"], file_name="resume.tex")
        st.caption("Paste this into Overleaf, or compile locally if this Codespace has a TeX distribution installed (it doesn't by default — see README).")


# ---------------------------------------------------------------- 6. outreach

else:
    st.header("Find who to talk to")
    st.caption("Builds search links, doesn't scrape. You run the search yourself, so your account is never at risk.")

    profile = data_store.load_profile()
    jobs = data_store.load_jobs()
    inc = included_jobs(jobs)

    if not inc:
        st.info("No matched jobs yet — go fetch and score some first.")
    else:
        options = [f"{j['title']} — {j['company']}" for j in inc]
        target_id = st.session_state.get("_outreach_target_job_id")
        default_idx = 0
        if target_id and target_id in jobs:
            label = f"{jobs[target_id]['title']} — {jobs[target_id]['company']}"
            if label in options:
                default_idx = options.index(label)

        choice = st.selectbox("Which job?", options, index=default_idx)
        job = inc[options.index(choice)]

        if st.button("Build outreach", type="primary"):
            with st.spinner("Building search links and drafting a message..."):
                result = outreach.find_contacts_and_pitch(profile, job)

            st.subheader("People to search for")
            for link in result["search_links"]:
                st.markdown(f"- [{link['label']}]({link['url']})")

            st.subheader("Draft opening message")
            if result.get("message"):
                st.text_area("Message", result["message"], height=100)
            for w in result.get("warnings", []):
                st.warning(w)

            st.subheader("Project suggestion")
            st.write(result.get("project_suggestion", "—"))
