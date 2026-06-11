import streamlit as st
import google.generativeai as genai
import json
import os
import yt_dlp
from datetime import datetime, timedelta
from youtube_transcript_api import YouTubeTranscriptApi

# ============================================================
# 1. CONFIG & STORAGE
# ============================================================
BASE_DATABASE = "production_database"
os.makedirs(BASE_DATABASE, exist_ok=True)

TOPIC_CONFIG = {
    "👑 ROYAL NEWS": {
        "folder": "royal_news",
        "channels": [
            "https://www.youtube.com/@crownwatchnews/videos",
            "https://www.youtube.com/@PalaceInsider1/videos",
            "https://www.youtube.com/@ThePrimeExpedition/videos",
            "https://www.youtube.com/@CrownMeltdown/videos",
            "https://www.youtube.com/@RoyalCheezee/videos",
            "https://www.youtube.com/@VintageExpose1/videos",
            "https://www.youtube.com/@PalaceUncovered2/videos",
        ],
    },
    "🚀 TECH NEWS": {
        "folder": "tech_news",
        "channels": ["https://www.youtube.com/@verge/videos"],
    },
}

STEPS = [
    "🔍  STEP 1 — SPY TRENDING",
    "✍️  STEP 2 — REWRITE SCRIPT",
    "📊  STEP 3 — SEO & THUMBNAIL",
    "📜  STEP 4 — HISTORY",
]

# ============================================================
# 2. SESSION STATE
# ============================================================
_DEFAULTS = {
    "trending_list": [],
    "selected_topic": "",
    "selected_transcript": "",
    "outline": None,
    "current_part": 0,
    "full_script_list": [],
    "seo_result": "",
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ============================================================
# 3. HELPERS
# ============================================================
def get_topic_path(cat: str) -> str:
    path = os.path.join(BASE_DATABASE, TOPIC_CONFIG[cat]["folder"])
    os.makedirs(path, exist_ok=True)
    return path


def call_ai(prompt: str, key: str) -> str:
    if not key:
        return "❌ MISSING API KEY"
    genai.configure(api_key=key)
    try:
        model = genai.GenerativeModel("gemini-3-flash-preview")
        return model.generate_content(prompt).text
    except Exception as e:
        return f"❌ Gemini Error: {e}"


def get_yt_trending(url: str):
    date_limit = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    ydl_opts = {
        "quiet": True,
        "extract_flat": False,
        "playlistend": 30,
        "daterange": yt_dlp.utils.DateRange(start=date_limit),
        "ignoreerrors": True,
    }
    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and "entries" in info:
                for e in info["entries"]:
                    if e and e.get("view_count", 0) >= 10000:
                        results.append(
                            {
                                "title": e["title"],
                                "id": e["id"],
                                "views": e["view_count"],
                                "url": f"https://www.youtube.com/watch?v={e['id']}",
                            }
                        )
    except:
        pass
    return results


def get_transcript(v_id: str) -> str:
    try:
        ts_list = YouTubeTranscriptApi.list_transcripts(v_id)
        try:
            ts = ts_list.find_transcript(["en"])
        except:
            ts = ts_list.find_generated_transcript(["en"])
        return " ".join([t["text"] for t in ts.fetch()])
    except:
        return ""


def reset_project():
    for k, v in _DEFAULTS.items():
        st.session_state[k] = v
    st.rerun()


# ============================================================
# 4. PAGE CONFIG & GLOBAL CSS
# ============================================================
st.set_page_config(
    page_title="AI Production Hub",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* ── Base ── */
    [data-testid="stAppViewContainer"] { background: #0f1117; }
    [data-testid="stSidebar"] { background: #16181f; border-right: 1px solid #2a2d3a; }

    /* ── Sidebar title ── */
    .hub-title {
        font-size: 1.25rem; font-weight: 700; letter-spacing: .05em;
        color: #f0c040; padding: 0 0 .25rem 0; margin-bottom: .5rem;
    }
    .hub-version {
        font-size: .7rem; color: #555; margin-top: -.4rem; margin-bottom: 1rem;
    }

    /* ── Category badge ── */
    .cat-label {
        font-size: .65rem; font-weight: 700; letter-spacing: .12em;
        color: #888; text-transform: uppercase; margin-bottom: .2rem;
    }

    /* ── Step radio custom look ── */
    div[data-testid="stRadio"] label {
        font-size: .85rem !important;
        color: #ccc !important;
        padding: .35rem .5rem !important;
        border-radius: 6px !important;
        display: block !important;
        transition: background .15s;
    }
    div[data-testid="stRadio"] label:hover { background: #1e2130 !important; }
    div[data-testid="stRadio"] [data-checked="true"] label {
        background: #1e3a5f !important;
        color: #60aaff !important;
        font-weight: 600 !important;
    }

    /* ── Section headers ── */
    .section-header {
        display: flex; align-items: center; gap: .6rem;
        border-left: 3px solid #f0c040;
        padding-left: .75rem;
        margin-bottom: 1.25rem;
    }
    .section-header h2 { font-size: 1.3rem; font-weight: 700; color: #f0f0f0; margin: 0; }
    .section-sub { font-size: .8rem; color: #777; margin-top: .15rem; }

    /* ── Progress bar ── */
    .progress-wrap { margin: 1rem 0 1.5rem; }
    .progress-label { font-size: .75rem; color: #888; margin-bottom: .3rem; }
    .progress-bar-bg {
        background: #1e2130; border-radius: 99px; height: 8px; overflow: hidden;
    }
    .progress-bar-fill {
        background: linear-gradient(90deg, #f0c040, #e07b20);
        height: 100%; border-radius: 99px; transition: width .4s ease;
    }

    /* ── Video card ── */
    .vcard {
        background: #16181f; border: 1px solid #2a2d3a; border-radius: 10px;
        padding: .85rem 1rem; margin-bottom: .6rem;
        display: flex; justify-content: space-between; align-items: center;
        gap: 1rem;
    }
    .vcard-title { font-size: .9rem; font-weight: 600; color: #eee; margin-bottom: .2rem; }
    .vcard-meta { font-size: .75rem; color: #666; }

    /* ── Outline box ── */
    .outline-box {
        background: #12151e; border: 1px solid #2a2d3a; border-radius: 10px;
        padding: 1rem 1.2rem; margin-bottom: 1rem;
    }

    /* ── Part chip ── */
    .part-chip {
        display: inline-block; background: #1e3a5f; color: #60aaff;
        font-size: .7rem; font-weight: 700; letter-spacing: .08em;
        padding: .2rem .6rem; border-radius: 99px; margin-bottom: .5rem;
        text-transform: uppercase;
    }

    /* ── Reset button ── */
    div[data-testid="stButton"] button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid #3a3d4a !important;
        color: #888 !important;
        font-size: .75rem !important;
        width: 100%;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover {
        border-color: #e05050 !important; color: #e05050 !important;
    }

    /* ── Inputs ── */
    textarea, input[type="text"], input[type="password"] {
        background: #12151e !important;
        border: 1px solid #2a2d3a !important;
        color: #eee !important;
        border-radius: 8px !important;
    }

    /* ── Divider ── */
    hr { border-color: #2a2d3a !important; margin: 1rem 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 5. SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown('<div class="hub-title">👑 PRODUCTION HUB</div>', unsafe_allow_html=True)
    st.markdown('<div class="hub-version">AI-Powered Script Factory · v24</div>', unsafe_allow_html=True)

    gemini_key = st.text_input(
        "Gemini API Key", type="password", placeholder="AIza...", key="api_key_input"
    )
    api_ok = bool(gemini_key)
    if api_ok:
        st.success("API key loaded", icon="✅")
    else:
        st.warning("Enter API key to unlock AI steps", icon="🔑")

    st.divider()

    st.markdown('<div class="cat-label">Category</div>', unsafe_allow_html=True)
    main_cat = st.selectbox(
        "Category",
        list(TOPIC_CONFIG.keys()),
        key="cat_box",
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown('<div class="cat-label">Workflow Steps</div>', unsafe_allow_html=True)
    menu = st.radio(
        "Steps",
        STEPS,
        key="menu_radio",
        label_visibility="collapsed",
    )

    st.divider()

    # Progress indicator
    part = st.session_state.current_part
    if st.session_state.outline and part <= 6:
        pct = int((part - 1) / 6 * 100)
        st.markdown(
            f"""
            <div class="progress-wrap">
                <div class="progress-label">Script Progress — Part {part - 1 if part > 1 else 0} of 6</div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width:{pct}%"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("↺  Reset Project", type="secondary"):
        reset_project()


# ============================================================
# 6. MAIN CONTENT
# ============================================================
gemini_key = st.session_state.get("api_key_input", "")

# ── STEP 1: SPY TRENDING ──────────────────────────────────
if menu == STEPS[0]:
    st.markdown(
        """
        <div class="section-header">
            <div><h2>Viral Spy</h2>
            <div class="section-sub">Scan competitor channels · Last 7 days · ≥ 10,000 views</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        target_channel = st.selectbox(
            "Competitor channel", TOPIC_CONFIG[main_cat]["channels"], label_visibility="collapsed"
        )
    with col_btn:
        scan = st.button("▶  Scan", use_container_width=True, type="primary")

    if scan:
        with st.spinner("Scanning YouTube..."):
            st.session_state.trending_list = get_yt_trending(target_channel)

    videos = st.session_state.trending_list
    if videos:
        st.caption(f"Found **{len(videos)}** videos matching criteria")
        st.divider()
        for v in videos:
            col_info, col_act = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f"""
                    <div class="vcard">
                        <div>
                            <div class="vcard-title">🔥 {v['title']}</div>
                            <div class="vcard-meta">👁 {v['views']:,} views &nbsp;·&nbsp;
                            <a href="{v['url']}" target="_blank" style="color:#60aaff">Open on YouTube ↗</a></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_act:
                if st.button("Select", key=f"sel_{v['id']}", use_container_width=True):
                    with st.spinner("Fetching transcript..."):
                        st.session_state.selected_topic = v["title"]
                        st.session_state.selected_transcript = get_transcript(v["id"])
                    st.success("Video loaded → go to Step 2")


# ── STEP 2: REWRITE SCRIPT ───────────────────────────────
elif menu == STEPS[1]:
    st.markdown(
        """
        <div class="section-header">
            <div><h2>Rewrite Master</h2>
            <div class="section-sub">6-part structure · 5,000 words · Gemini 3</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.session_state.selected_topic = st.text_input(
            "Project name / topic", value=st.session_state.selected_topic
        )
    with c2:
        st.caption("Transcript source")
        st.session_state.selected_transcript = st.text_area(
            "Transcript",
            value=st.session_state.selected_transcript,
            height=120,
            label_visibility="collapsed",
        )

    st.divider()

    # ── Phase A: Generate outline
    if st.session_state.outline is None:
        st.info("Step 2a — Generate outline first, then write each part.", icon="ℹ️")
        disabled_a = not (gemini_key and st.session_state.selected_transcript)
        if st.button(
            "Generate Outline  →",
            type="primary",
            disabled=disabled_a,
            use_container_width=False,
        ):
            prompt_o = f"""
ACT AS A MASTER CONTENT CREATOR (expert in high-retention YouTube scripts).
Task: Create a detailed OUTLINE to REWRITE this script into a 5000-word viral YouTube script.
Category: {main_cat}

STRICT RULES:
1. Divide into EXACTLY SIX PARTS.
2. Assign a specific word count per part (total = five thousand words).
3. NO DIGITS — write all numbers as words (e.g. 'eight hundred' not 800).
4. ENGLISH ONLY.

Topic: {st.session_state.selected_topic}
Transcript: {st.session_state.selected_transcript[:3500]}
"""
            with st.spinner("Generating outline..."):
                res = call_ai(prompt_o, gemini_key)
                if "❌" not in res:
                    st.session_state.outline = res
                    st.session_state.current_part = 1
                    st.rerun()
                else:
                    st.error(res)

    # ── Phase B: Write parts
    else:
        curr = st.session_state.current_part

        # Outline display
        with st.expander("📋 View Outline", expanded=(curr == 1)):
            st.markdown(
                f'<div class="outline-box">{st.session_state.outline}</div>',
                unsafe_allow_html=True,
            )

        st.divider()

        if curr <= 6:
            col_status, col_action = st.columns([3, 1])
            with col_status:
                st.markdown(
                    f'<div class="part-chip">Part {curr} / 6</div>', unsafe_allow_html=True
                )
                pct = int((curr - 1) / 6 * 100)
                st.progress(pct / 100)
            with col_action:
                write_btn = st.button(
                    f"Write Part {curr}  →",
                    type="primary",
                    use_container_width=True,
                    disabled=not gemini_key,
                )

            if write_btn:
                prompt_w = f"""
OUTLINE REFERENCE:
{st.session_state.outline}

TASK: Write PART {curr} of the script — ENGLISH ONLY.

STRICT REQUIREMENTS:
1. WORD COUNT — match the word count allocated for Part {curr} in the outline exactly. Expand with deep analysis and dramatic storytelling.
2. NO DIGITS — write all numbers as words (e.g. 'twenty-twenty-five' not 2025).
3. STYLE — cinematic, high-stakes drama, authoritative tone.
"""
                with st.spinner(f"Writing Part {curr}..."):
                    result = call_ai(prompt_w, gemini_key)
                    if "❌" not in result:
                        st.session_state.full_script_list.append(
                            f"## PART {curr}\n\n{result}"
                        )
                        if curr == 6:
                            # Auto-save
                            path = get_topic_path(main_cat)
                            fname = f"{path}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            with open(fname, "w", encoding="utf-8") as f:
                                json.dump(
                                    {
                                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "topic": st.session_state.selected_topic,
                                        "content": "\n\n".join(
                                            st.session_state.full_script_list
                                        ),
                                    },
                                    f,
                                    ensure_ascii=False,
                                    indent=4,
                                )
                        st.session_state.current_part += 1
                        st.rerun()
                    else:
                        st.error(result)

        # Written parts
        if st.session_state.full_script_list:
            st.divider()
            st.caption(f"Written so far — {len(st.session_state.full_script_list)} part(s)")
            for p in st.session_state.full_script_list:
                st.markdown(p)
                st.divider()

        # Completion
        if curr > 6:
            st.success("✅ All 6 parts complete — script saved to History.")
            full_text = "\n\n".join(st.session_state.full_script_list)
            st.download_button(
                "⬇  Download Full Script (.md)",
                full_text,
                file_name=f"{st.session_state.selected_topic or 'script'}.md",
                mime="text/markdown",
                type="primary",
            )


# ── STEP 3: SEO & THUMBNAIL ──────────────────────────────
elif menu == STEPS[2]:
    st.markdown(
        """
        <div class="section-header">
            <div><h2>SEO & Thumbnail</h2>
            <div class="section-sub">5 titles · thumbnail brief · full description</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        titles = st.text_area(
            "Paste 10 competitor titles here", height=200, placeholder="Paste titles, one per line..."
        )
    with col_b:
        full_script_text = "\n\n".join(st.session_state.full_script_list)
        script_box = st.text_area(
            "Your script (auto-filled from Step 2)",
            value=full_script_text,
            height=200,
        )

    st.divider()

    if st.button("🚀  Generate SEO Package", type="primary", disabled=not gemini_key):
        prompt_seo = f"""
Analyze these competitor titles:
{titles}

TASK 1 — TITLES: Create 5 new viral titles following the same emotional pattern.
TASK 2 — THUMBNAIL: Write a thumbnail composition brief (main visual, text overlay, color mood).
TASK 3 — DESCRIPTION: Write using this exact template:

[2–3 dramatic sentence summary based on: {script_box[:500]}]
• [Key point 1]
• [Key point 2]
• [Key point 3]
👉 Don't miss our deep dives into royal truth and tradition
Subscribe: https://www.youtube.com/@RoyalSignal-1 and turn on the bell!

📍 Disclaimer
Independent commentary and analysis for discussion. We do not verify allegations. Examined under YouTube Fair Use.
#KateMiddleton #QueenCamilla #RoyalNews #BreakingNews #PrincessOfWales #RoyalFamily #HouseOfWindsor #RoyalExpert #KingCharlesIII #BritishMonarchy

ENGLISH ONLY.
"""
        with st.spinner("Generating SEO package..."):
            st.session_state.seo_result = call_ai(prompt_seo, gemini_key)

    if st.session_state.seo_result:
        st.divider()
        st.markdown(st.session_state.seo_result)
        st.download_button(
            "⬇  Download SEO Package",
            st.session_state.seo_result,
            file_name="seo_package.txt",
            mime="text/plain",
        )


# ── STEP 4: HISTORY ──────────────────────────────────────
elif menu == STEPS[3]:
    st.markdown(
        f"""
        <div class="section-header">
            <div><h2>Script History</h2>
            <div class="section-sub">{main_cat} · Saved scripts</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    folder = get_topic_path(main_cat)
    files = sorted(
        [f for f in os.listdir(folder) if f.endswith(".json")], reverse=True
    )

    if not files:
        st.info(f"No scripts saved yet for **{main_cat}**.", icon="📂")
    else:
        st.caption(f"{len(files)} script(s) saved")
        for fn in files:
            fpath = os.path.join(folder, fn)
            with open(fpath, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            col_exp, col_dl, col_del = st.columns([6, 1, 1])
            with col_exp:
                with st.expander(f"📅 {data['date']}  ·  🎬 {data['topic']}"):
                    st.markdown(data["content"])
            with col_dl:
                st.download_button(
                    "⬇",
                    data["content"],
                    file_name=f"{data['topic']}.md",
                    mime="text/markdown",
                    key=f"dl_{fn}",
                    use_container_width=True,
                )
            with col_del:
                if st.button("🗑", key=f"del_{fn}", use_container_width=True):
                    os.remove(fpath)
                    st.toast("Deleted.")
                    st.rerun()
