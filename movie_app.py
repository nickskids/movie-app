import streamlit as st
import requests
import re
import datetime
import json
import concurrent.futures
from serpapi import GoogleSearch

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="CriticScore | Real Ratings",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
#  CUSTOM CSS  — Dark editorial cinema theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0d0d0f;
    color: #e8e4dc;
}

.stApp {
    background: #0d0d0f;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #111114;
    border-right: 1px solid #2a2a30;
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] p {
    color: #a09a90 !important;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #1a1a1f;
    border: 1px solid #2a2a30;
    color: #e8e4dc;
    border-radius: 6px;
}

/* ── Header ── */
.cs-header {
    padding: 2.5rem 0 1.5rem 0;
    border-bottom: 1px solid #2a2a30;
    margin-bottom: 2rem;
}

.cs-title {
    font-family: 'Playfair Display', serif;
    font-size: 3.2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #f5f0e8;
    line-height: 1;
    margin: 0;
}

.cs-title span {
    font-style: italic;
    color: #c8a96e;
}

.cs-subtitle {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #5a5a65;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 0.6rem;
}

/* ── Score Cards ── */
.score-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1px;
    background: #1e1e24;
    border: 1px solid #1e1e24;
    border-radius: 10px;
    overflow: hidden;
    margin-top: 1.5rem;
}

.score-card {
    background: #111114;
    padding: 1.4rem 1.6rem;
    display: flex;
    align-items: center;
    gap: 1.2rem;
    transition: background 0.2s;
    position: relative;
}

.score-card:hover {
    background: #161618;
}

.score-badge {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    min-width: 68px;
    text-align: center;
    line-height: 1;
}

.score-great  { color: #6ec87a; }
.score-good   { color: #a8c86e; }
.score-mid    { color: #c8a96e; }
.score-low    { color: #c87a6e; }
.score-na     { color: #3a3a42; font-size: 1.2rem; }

.score-meta {
    flex: 1;
    min-width: 0;
}

.score-title {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 500;
    color: #e8e4dc;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 0.3rem;
}

.score-detail {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    color: #4a4a55;
    letter-spacing: 0.05em;
}

.score-detail span {
    color: #6a6a75;
}

.score-bar-wrap {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: #1e1e24;
}

.score-bar {
    height: 100%;
    border-radius: 0 2px 2px 0;
    transition: width 0.8s ease;
}

/* ── Pick highlight (7.6+) ── */
.score-card.pick {
    background: #13120e;
    border-left: 3px solid #c8a96e;
    box-shadow: inset 0 0 40px rgba(200, 169, 110, 0.04);
}

.score-card.pick:hover {
    background: #17160f;
    box-shadow: inset 0 0 40px rgba(200, 169, 110, 0.08);
}

.pick-badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 0.58rem;
    font-weight: 500;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #0d0d0f;
    background: #c8a96e;
    border-radius: 3px;
    padding: 0.15rem 0.45rem;
    margin-left: 0.5rem;
    vertical-align: middle;
    position: relative;
    top: -1px;
}

/* ── Stats row ── */
.stats-row {
    display: flex;
    gap: 2rem;
    padding: 1rem 0;
    border-bottom: 1px solid #1e1e24;
    margin-bottom: 1rem;
}

.stat-item {
    display: flex;
    flex-direction: column;
}

.stat-value {
    font-family: 'Playfair Display', serif;
    font-size: 1.6rem;
    color: #c8a96e;
    line-height: 1;
}

.stat-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    color: #4a4a55;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.2rem;
}

/* ── Theater badge ── */
.theater-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #1a1a1f;
    border: 1px solid #2a2a30;
    border-radius: 20px;
    padding: 0.35rem 0.9rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    color: #7a7a85;
    letter-spacing: 0.06em;
    margin-bottom: 1rem;
}

/* ── Button ── */
.stButton > button {
    background: #c8a96e !important;
    color: #0d0d0f !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.8rem !important;
    width: 100% !important;
    margin-top: 1rem !important;
    transition: all 0.2s !important;
}

.stButton > button:hover {
    background: #d4ba82 !important;
    transform: translateY(-1px) !important;
}

/* ── Progress bar ── */
.stProgress > div > div {
    background: #c8a96e !important;
}

/* ── Alert boxes ── */
.stSuccess, .stInfo, .stWarning, .stError {
    border-radius: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
}

/* ── Divider ── */
hr {
    border-color: #1e1e24 !important;
    margin: 1.2rem 0 !important;
}

/* ── Hide streamlit branding ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Spinner ── */
.stSpinner > div {
    border-top-color: #c8a96e !important;
}

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
try:
    SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
except Exception:
    st.error("🔑 SerpApi Key not found. Add it to Streamlit Secrets to continue.")
    st.stop()

THEATERS = {
    "AMC DINE-IN Levittown 10":        "11756",
    "AMC Raceway 10 (Westbury)":        "11590",
    "AMC Roosevelt Field 8":            "11530",
    "AMC DINE-IN Huntington Square 12": "11731",
    "AMC Stony Brook 17":               "11790",
    "AMC Fresh Meadows 7":              "11365",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

RT_TIMEOUT      = 5.0   # seconds per RT request
PARALLEL_WORKERS = 6    # concurrent RT lookups


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def get_next_thursday():
    today = datetime.date.today()
    days_ahead = (3 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    nxt = today + datetime.timedelta(days=days_ahead)
    return (
        nxt.strftime("%b ") + str(nxt.day),   # short: "Jun 5"
        nxt.strftime("%B ") + str(nxt.day),   # long:  "June 5"
        days_ahead,
    )


def score_color_class(score_str: str) -> str:
    try:
        v = float(score_str.split("/")[0])
        if v >= 7.6: return "score-great"
        if v >= 6.0: return "score-good"
        if v >= 4.5: return "score-mid"
        return "score-low"
    except Exception:
        return "score-na"


def is_pick(score_str: str) -> bool:
    try:
        return float(score_str.split("/")[0]) >= 7.6
    except Exception:
        return False


def score_bar_color(score_str: str) -> str:
    cls = score_color_class(score_str)
    return {
        "score-great": "#6ec87a",
        "score-good":  "#a8c86e",
        "score-mid":   "#c8a96e",
        "score-low":   "#c87a6e",
        "score-na":    "#1e1e24",
    }[cls]


def score_bar_pct(score_str: str) -> float:
    try:
        return (float(score_str.split("/")[0]) / 10.0) * 100
    except Exception:
        return 0.0


# ─────────────────────────────────────────────
#  SHOWTIME FETCHING
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def run_search_query(query: str, target_date_str=None):
    params = {
        "engine":   "google",
        "q":        query,
        "api_key":  SERPAPI_KEY,
        "hl":       "en",
        "gl":       "us",
    }
    try:
        results = GoogleSearch(params).get_dict()
        movies: set = set()
        found_date   = "Unknown Date"
        date_matched = False

        if "showtimes" in results:
            for day_block in results["showtimes"]:
                day_header = day_block.get("day", "").lower()
                if target_date_str:
                    if target_date_str.lower() in day_header:
                        found_date = day_block.get("day", "Target Date")
                        for m in day_block.get("movies", []):
                            movies.add(m["name"])
                        date_matched = True
                        break
                else:
                    for m in day_block.get("movies", []):
                        movies.add(m["name"])
                    found_date = "Today +"

        kg = results.get("knowledge_graph", {})
        for m in kg.get("movies_playing", []):
            movies.add(m["name"])

        # Fallback: strict mode found nothing → grab first available day
        if target_date_str and not date_matched:
            blocks = results.get("showtimes", [])
            if blocks:
                first = blocks[0]
                found_date = first.get("day", "Today")
                for m in first.get("movies", []):
                    movies.add(m["name"])

        return list(movies), found_date

    except Exception as e:
        return [], f"Error: {e}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_movies_at_theater(theater_name, location, target_date_short=None, target_date_long=None):
    query = f"showtimes for {theater_name} {location}"

    if target_date_long:
        movies, found_date = run_search_query(query, target_date_str=target_date_short)
        is_fallback = bool(
            target_date_short and
            target_date_short.lower() not in found_date.lower()
        )
        if is_fallback:
            movies, found_date = run_search_query(query, target_date_str=None)
        return movies, found_date, is_fallback
    else:
        movies, found_date = run_search_query(query, target_date_str=None)
        return list(movies), "Today", False


# ─────────────────────────────────────────────
#  RT URL RESOLUTION
# ─────────────────────────────────────────────

def guess_rt_url(title: str) -> str | None:
    clean = re.sub(r"[^\w\s]", "", title).lower()
    slug  = re.sub(r"\s+", "_", clean.strip())
    yr    = datetime.date.today().year

    # Current year first (most likely for a film in theaters now),
    # then adjacent years for cross-year releases,
    # no-year LAST — it returns the oldest/most prominent RT entry
    # and would pull the wrong film if a title has prior history.
    candidates = [
        f"https://www.rottentomatoes.com/m/{slug}_{yr}",
        f"https://www.rottentomatoes.com/m/{slug}_{yr + 1}",
        f"https://www.rottentomatoes.com/m/{slug}_{yr - 1}",
        f"https://www.rottentomatoes.com/m/{slug}",
    ]
    for url in candidates:
        try:
            r = requests.get(url, headers=HEADERS, timeout=RT_TIMEOUT)
            if r.status_code == 200:
                return url
        except Exception:
            pass
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def find_rt_url_paid(title: str) -> str | None:
    params = {
        "engine":  "google",
        "q":       f"{title} rotten tomatoes movie",
        "api_key": SERPAPI_KEY,
    }
    try:
        results = GoogleSearch(params).get_dict()
        for r in results.get("organic_results", []):
            link = r.get("link", "")
            if "rottentomatoes.com/m/" in link:
                return link
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
#  RT SCRAPING  — JSON-first, regex fallback
# ─────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def scrape_rt_source(url: str | None):
    """Returns (rating, count, release_date) or ('N/A', 'N/A', 'N/A')."""
    if not url:
        return "N/A", "N/A", "N/A"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=RT_TIMEOUT)
        if resp.status_code != 200:
            return "N/A", "N/A", "N/A"

        html    = resp.text
        rating  = "N/A"
        count   = "N/A"
        r_date  = "N/A"

        # ── Strategy 1: pull embedded JSON blobs ──────────────────────────
        json_blobs = re.findall(
            r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        for blob in json_blobs:
            try:
                data = json.loads(blob)
                blob_str = json.dumps(data)

                # averageRating under criticsAll
                m = re.search(
                    r'"criticsAll"\s*:\s*\{[^}]*?"averageRating"\s*:\s*"(\d+\.?\d*)"',
                    blob_str
                )
                if m and rating == "N/A":
                    rating = f"{m.group(1)}/10"

                # reviewCount under criticsAll
                m2 = re.search(
                    r'"criticsAll"\s*:\s*\{[^}]*?"reviewCount"\s*:\s*(\d+)',
                    blob_str
                )
                if m2 and count == "N/A":
                    count = m2.group(1)

            except (json.JSONDecodeError, Exception):
                continue

        # ── Strategy 2: regex on full HTML (same patterns as before) ──────
        if rating == "N/A":
            m = re.search(
                r'"criticsAll"\s*:\s*\{[^}]*?"averageRating"\s*:\s*"(\d+\.?\d*)"',
                html
            )
            if m:
                rating = f"{m.group(1)}/10"

        if rating == "N/A":
            m = re.search(
                r'"criticsScore"\s*:\s*\{[^}]*?"averageRating"\s*:\s*"(\d+\.?\d*)"',
                html
            )
            if m:
                rating = f"{m.group(1)}/10"

        if count == "N/A":
            m = re.search(
                r'"criticsAll"\s*:\s*\{[^}]*?"reviewCount"\s*:\s*(\d+)',
                html
            )
            if m:
                count = m.group(1)

        # ── Release date ───────────────────────────────────────────────────
        m = re.search(
            r'Release Date \((?:Theaters|Wide)\).*?(\w{3}\s+\d{1,2},\s+\d{4})',
            html, re.DOTALL
        )
        if m:
            try:
                r_date = datetime.datetime.strptime(m.group(1), "%b %d, %Y").strftime("%m/%d/%Y")
            except Exception:
                r_date = m.group(1)

        return rating, count, r_date

    except Exception:
        return "N/A", "N/A", "N/A"


# ─────────────────────────────────────────────
#  PARALLEL MOVIE LOOKUP
# ─────────────────────────────────────────────

def lookup_movie(movie: str, use_paid: bool) -> dict:
    url    = guess_rt_url(movie)
    method = "Direct"
    rating, count, r_date = scrape_rt_source(url)

    # Skip paid search if we got a review count and it's too low
    skip_paid = False
    if count != "N/A":
        try:
            skip_paid = int(count) < 5
        except Exception:
            pass

    if rating == "N/A" and use_paid and not skip_paid:
        url    = find_rt_url_paid(movie)
        method = "Search"
        rating, count, r_date = scrape_rt_source(url)

    try:
        sort_val = float(rating.split("/")[0])
    except Exception:
        sort_val = -1.0

    return {
        "movie":  movie,
        "rating": rating,
        "count":  count,
        "r_date": r_date,
        "method": method,
        "url":    url,
        "_sort":  sort_val,
    }


# ─────────────────────────────────────────────
#  UI — HEADER
# ─────────────────────────────────────────────

st.markdown("""
<div class="cs-header">
  <div class="cs-title">Critic<span>Score</span></div>
  <div class="cs-subtitle">Rotten Tomatoes · All Critics Average · /10</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  UI — SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🎬 Settings")
    st.markdown("---")

    selected_theater = st.selectbox(
        "THEATER",
        options=list(THEATERS.keys()),
        label_visibility="visible"
    )
    selected_zip = THEATERS[selected_theater]

    st.markdown("---")

    date_mode = st.radio(
        "DATE",
        ["Today", "Next Thursday"],
        horizontal=False,
        label_visibility="visible"
    )

    target_short = target_long = None

    if date_mode == "Next Thursday":
        target_short, target_long, days_away = get_next_thursday()
        st.info(f"📅 **{target_long}**")
        if days_away > 5:
            st.warning("Schedule may not be posted yet.")

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.68rem;color:#3a3a45;font-family:DM Mono,monospace;"
        "letter-spacing:0.06em;line-height:1.7'>"
        "Scores are the hidden All Critics<br>Average (x/10) embedded in<br>"
        "RT page source — not the<br>visible Tomatometer %."
        "</div>",
        unsafe_allow_html=True
    )

    run = st.button("Get Ratings", type="primary")


# ─────────────────────────────────────────────
#  UI — MAIN PANEL
# ─────────────────────────────────────────────

if run:
    # Theater badge
    st.markdown(
        f'<div class="theater-badge">📍 {selected_theater}</div>',
        unsafe_allow_html=True
    )

    with st.spinner("Fetching showtimes…"):
        movies, found_date, is_fallback = get_movies_at_theater(
            selected_theater, selected_zip, target_short, target_long
        )

    if not movies:
        st.error("No movies found. The schedule may not be posted yet.")
        st.stop()

    if is_fallback:
        st.warning(f"Schedule for **{target_long}** isn't posted yet — showing today's full lineup instead.")
    elif date_mode == "Next Thursday":
        st.success(f"✅ Found schedule for **{target_long}**")

    # ── Parallel RT lookups ─────────────────────────────────────────────
    use_paid = (date_mode == "Today") or is_fallback
    results  = []

    progress    = st.progress(0)
    status_text = st.empty()
    completed   = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as pool:
        future_map = {pool.submit(lookup_movie, m, use_paid): m for m in movies}
        for future in concurrent.futures.as_completed(future_map):
            completed += 1
            name = future_map[future]
            status_text.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:0.75rem;"
                f"color:#5a5a65'>Checking {completed}/{len(movies)} — {name}</div>",
                unsafe_allow_html=True
            )
            progress.progress(completed / len(movies))
            try:
                results.append(future.result())
            except Exception:
                results.append({
                    "movie": name, "rating": "N/A", "count": "N/A",
                    "r_date": "N/A", "method": "Error", "url": None, "_sort": -1.0
                })

    progress.empty()
    status_text.empty()

    results.sort(key=lambda x: x["_sort"], reverse=True)

    # ── Summary stats ───────────────────────────────────────────────────
    scored   = [r for r in results if r["_sort"] >= 0]
    avg_str  = f"{sum(r['_sort'] for r in scored)/len(scored):.2f}" if scored else "—"
    top      = results[0]["rating"] if results else "—"
    n_scored = len(scored)

    st.markdown(f"""
    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-value">{len(movies)}</div>
        <div class="stat-label">Films Playing</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{n_scored}</div>
        <div class="stat-label">Scores Found</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">{avg_str}</div>
        <div class="stat-label">Lineup Average</div>
      </div>
      <div class="stat-item">
        <div class="stat-value" style="color:#6ec87a">{top}</div>
        <div class="stat-label">Best Reviewed</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Score cards — rendered two per row to avoid Streamlit HTML limits ──
    def render_card(r: dict) -> str:
        color_cls  = score_color_class(r["rating"])
        bar_color  = score_bar_color(r["rating"])
        bar_pct    = round(score_bar_pct(r["rating"]), 1)
        display_rt = r["rating"] if r["rating"] != "N/A" else "—"
        pick       = is_pick(r["rating"])
        card_cls   = "score-card pick" if pick else "score-card"
        pick_badge = '<span class="pick-badge">&#10022; Pick</span>' if pick else ""
        link_html  = (
            f'<a href="{r["url"]}" target="_blank" '
            f'style="color:#c8a96e;text-decoration:none;font-size:0.7rem">RT &#8599;</a>'
            if r["url"] else ""
        )
        detail_parts = []
        if r["count"] != "N/A":
            detail_parts.append(f'<span>{r["count"]} reviews</span>')
        if r["r_date"] != "N/A":
            detail_parts.append(r["r_date"])
        detail_parts.append(r["method"])
        detail_str = " &middot; ".join(detail_parts)

        return (
            f'<div class="{card_cls}" style="border-radius:8px;margin-bottom:1px;">'
            f'<div class="score-badge {color_cls}">{display_rt}</div>'
            f'<div class="score-meta">'
            f'<div class="score-title" title="{r["movie"]}">{r["movie"]}{pick_badge}</div>'
            f'<div class="score-detail">{detail_str} &nbsp; {link_html}</div>'
            f'</div>'
            f'<div class="score-bar-wrap">'
            f'<div class="score-bar" style="width:{bar_pct}%;background:{bar_color}"></div>'
            f'</div>'
            f'</div>'
        )

    # Render two cards per row
    pairs = [results[i:i+2] for i in range(0, len(results), 2)]
    for pair in pairs:
        cols = st.columns(len(pair))
        for col, r in zip(cols, pair):
            with col:
                st.markdown(render_card(r), unsafe_allow_html=True)

    st.markdown(
        "<div style='font-family:DM Mono,monospace;font-size:0.65rem;"
        "color:#2a2a32;text-align:right;padding-top:1.5rem;letter-spacing:0.06em'>"
        f"pulled {datetime.datetime.now().strftime('%b %d · %I:%M %p')}"
        "</div>",
        unsafe_allow_html=True
    )
