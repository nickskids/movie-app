import streamlit as st
import requests
import re
import datetime
import json
from serpapi import GoogleSearch

# --- CONFIGURATION ---
st.set_page_config(page_title="Theater Critic Check", page_icon="🍿", layout="wide")

try:
    SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
except:
    st.error("SerpApi Key not found! Please add it to Streamlit Secrets.")
    st.stop()

# --- THEATER LIST (With AMC URL Slugs) ---
# We map the name to both Zip (for Google) and Slug (for AMC Direct)
THEATERS = {
    "AMC DINE-IN Levittown 10": {
        "zip": "11756",
        "slug": "new-york-city/amc-dine-in-levittown-10"
    },
    "AMC Raceway 10 (Westbury)": {
        "zip": "11590",
        "slug": "new-york-city/amc-raceway-10"
    },
    "AMC Roosevelt Field 8": {
        "zip": "11530",
        "slug": "new-york-city/amc-roosevelt-field-8"
    },
    "AMC DINE-IN Huntington Square 12": {
        "zip": "11731",
        "slug": "new-york-city/amc-dine-in-huntington-square-12"
    },
    "AMC Stony Brook 17": {
        "zip": "11790",
        "slug": "new-york-city/amc-stony-brook-17"
    },
    "AMC Fresh Meadows 7": {
        "zip": "11365",
        "slug": "new-york-city/amc-fresh-meadows-7"
    }
}

# --- HEADERS ---
# We need a robust User-Agent so AMC doesn't block the request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

# --- FUNCTIONS ---

def run_search_query(query):
    """Helper: Runs a single Google Search and returns movie titles (Method A: Today)."""
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "en",
        "gl": "us"
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        titles = []
        
        # Method 1: Showtimes List
        if "showtimes" in results:
            for day in results["showtimes"]:
                if "movies" in day:
                    for m in day["movies"]:
                        titles.append(m["name"])
        
        # Method 2: Knowledge Graph (Backup)
        if not titles and "knowledge_graph" in results and "movies_playing" in results["knowledge_graph"]:
            for m in results["knowledge_graph"]["movies_playing"]:
                titles.append(m["name"])
    
        return titles
    except:
        return []

def scrape_amc_direct(slug, date_iso):
    """
    Method B (Next Thursday): Connects directly to AMC's website.
    scrapes the hidden Schema.org JSON data to find movies.
    """
    url = f"https://www.amctheatres.com/movie-theatres/{slug}/showtimes"
    # We append the date parameter
    params = {"date": date_iso}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=5)
        if response.status_code == 200:
            html = response.text
            movies = set()
            
            # AMC embeds data in <script type="application/ld+json">
            # We look for that specific pattern
            json_matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    # Check if this JSON block is a Movie or ScreeningEvent
                    if isinstance(data, dict):
                        # Pattern 1: Direct "Movie" object
                        if data.get("@type") == "Movie" and "name" in data:
                            movies.add(data["name"])
                        
                        # Pattern 2: "ScreeningEvent" which contains "workPresented"
                        if data.get("@type") == "ScreeningEvent":
                            work = data.get("workPresented", {})
                            if "name" in work:
                                movies.add(work["name"])
                                
                    # Sometimes it's a list of objects
                    if isinstance(data, list):
                        for item in data:
                            if item.get("@type") == "Movie" and "name" in item:
                                movies.add(item["name"])
                except:
                    pass
            
            # FALLBACK: If JSON parsing fails, regex scan for Title Headers
            if not movies:
                # AMC often uses an aria-label or class for titles
                regex_titles = re.findall(r'class="MovieTitleHeader"[^>]*>([^<]+)</a>', html)
                for t in regex_titles:
                    movies.add(t.strip())
            
            return list(movies)
            
    except Exception as e:
        print(f"AMC Scrape Error: {e}")
        return []
    
    return []

def get_movies_at_theater(theater_name, target_date_iso=None):
    """
    Decides whether to use Google (Today) or AMC Direct (Future).
    """
    theater_info = THEATERS[theater_name]
    
    if target_date_iso:
        # FUTURE MODE -> USE AMC DIRECT
        return scrape_amc_direct(theater_info["slug"], target_date_iso)
    else:
        # TODAY MODE -> USE GOOGLE (Reliable for current times)
        zip_code = theater_info["zip"]
        query = f"movies playing at {theater_name} {zip_code}"
        movies = run_search_query(query)
        
        # Late night safety net
        if len(set(movies)) < 4:
            movies_tomorrow = run_search_query(f"movies playing at {theater_name} {zip_code} tomorrow")
            movies.extend(movies_tomorrow)
            
        return list(set(movies))

def guess_rt_url(title):
    """Checks years (2025-2028) first to handle Remakes/Reboots."""
    clean_title = re.sub(r'[^\w\s]', '', title).lower()
    slug = re.sub(r'\s+', '_', clean_title)
    
    potential_urls = [
        f"https://www.rottentomatoes.com/m/{slug}_2025",
        f"https://www.rottentomatoes.com/m/{slug}_2026",
        f"https://www.rottentomatoes.com/m/{slug}_2027",
        f"https://www.rottentomatoes.com/m/{slug}_2028",
        f"https://www.rottentomatoes.com/m/{slug}"
    ]
    
    for url in potential_urls:
        try:
            response = requests.get(url, headers=HEADERS, timeout=1.0)
            if response.status_code == 200:
                return url
        except:
            pass
    return None

def find_rt_url_paid(title):
    """Uses Google Search to find the exact URL (Costs 1 Credit)."""
    params = {
        "engine": "google",
        "q": f"{title} rotten tomatoes movie",
        "api_key": SERPAPI_KEY,
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        if "organic_results" in results:
            for result in results["organic_results"]:
                link = result.get("link", "")
                if "rottentomatoes.com/m/" in link:
                    return link
    except:
        pass
    return None

def scrape_rt_source(url):
    """Extracts 'criticsAll':{'averageRating':'8.8'} from source."""
    if not url: return "N/A"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code == 200:
            html = response.text
            pattern = r'"criticsAll"\s*:\s*\{[^}]*"averageRating"\s*:\s*"(\d+\.?\d*)"'
            match = re.search(pattern, html)
            if match:
                return f"{match.group(1)}/10"
            backup = r'"criticsScore"\s*:\s*\{[^}]*"averageRating"\s*:\s*"(\d+\.?\d*)"'
            match_back = re.search(backup, html)
            if match_back:
                return f"{match_back.group(1)}/10"
    except:
        pass
    return "N/A"

def get_next_thursday_iso():
    """
    Returns TWO formats:
    1. Display: "January 8"
    2. ISO: "2026-01-08" (Required for AMC URL)
    """
    today = datetime.date.today()
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0: 
        days_ahead += 7
    next_thurs = today + datetime.timedelta(days=days_ahead)
    
    display_fmt = next_thurs.strftime("%B ") + str(next_thurs.day)
    iso_fmt = next_thurs.isoformat() # Returns YYYY-MM-DD
    
    return display_fmt, iso_fmt

# --- APP INTERFACE ---
st.title("🍿 True Critic Ratings")
st.caption("Select a theater below to see real critic scores.")

with st.sidebar:
    st.header("Settings")
    selected_theater_name = st.selectbox("Choose Theater", options=list(THEATERS.keys()))
    
    st.markdown("---")
    
    # Date Toggle
    date_mode = st.radio("When to check?", ["Today", "Next Thursday"], horizontal=True)
    
    target_iso = None
    target_display = None
    
    if date_mode == "Next Thursday":
        target_display, target_iso = get_next_thursday_iso()
        st.info(f"Checking for: **Thursday, {target_display}**")
        st.warning("Future Mode: Connecting directly to AMC (Saves Credits!)")
    else:
        st.info(f"Checking: **{selected_theater_name}**")
        st.caption("Using Google Search (1 Credit)")

if st.button("Get True Ratings", type="primary"):
    with st.spinner(f"Checking schedule..."):
        # 1. Get Movies (Logic split inside function)
        movies = get_movies_at_theater(selected_theater_name, target_iso)
        
        if not movies:
             st.error("No movies found. If checking Next Thursday, AMC might be blocking the request or the schedule isn't live yet.")
        else:
            st.info(f"Found {len(movies)} movies. Hunting for ratings...")
            
            data = []
            progress = st.progress(0)
            status_text = st.empty()
            
            for i, movie in enumerate(movies):
                status_text.text(f"Checking: {movie}")
                
                # Phase 1: Free Guess
                url = guess_rt_url(movie)
                method = "Free Guess"
                rating = scrape_rt_source(url)
                
                # Phase 2: Paid Fallback (CONDITIONAL)
                if rating == "N/A" and date_mode == "Today":
                    url = find_rt_url_paid(movie)
                    method = "Paid Search"
                    rating = scrape_rt_source(url)
                
                sort_val = 0.0
                try:
                    sort_val = float(rating.split("/")[0])
                except:
                    pass
                
                data.append({
                    "Movie": movie,
                    "True Rating": rating,
                    "Source": method,
                    "_sort": sort_val,
                    "Link": url
                })
                progress.progress((i + 1) / len(movies))
            
            progress.empty()
            status_text.empty()
            data.sort(key=lambda x: x["_sort"], reverse=True)
            
            st.dataframe(
                data,
                column_order=["Movie", "True Rating", "Source", "Link"], 
                column_config={
                    "Movie": st.column_config.TextColumn("Movie", width="medium"),
                    "True Rating": st.column_config.TextColumn("Score", width="small"),
                    "Source": st.column_config.TextColumn("Method", width="small"),
                    "Link": st.column_config.LinkColumn("Verify"),
                    "_sort": None
                },
                hide_index=True,
                use_container_width=True
            )
