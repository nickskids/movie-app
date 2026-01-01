import streamlit as st
import requests
import re
import datetime
from serpapi import GoogleSearch

# --- CONFIGURATION ---
st.set_page_config(page_title="Theater Critic Check", page_icon="🍿", layout="wide")

try:
    SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
except:
    st.error("SerpApi Key not found! Please add it to Streamlit Secrets.")
    st.stop()

# --- THEATER LIST ---
THEATERS = {
    "AMC DINE-IN Levittown 10": "11756",
    "AMC Raceway 10 (Westbury)": "11590",
    "AMC Roosevelt Field 8": "11530",
    "AMC DINE-IN Huntington Square 12": "11731",
    "AMC Stony Brook 17": "11790",
    "AMC Fresh Meadows 7": "11365"
}

# --- HEADERS ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- FUNCTIONS ---
def run_search_query(query):
    """Helper: Runs a single Google Search and returns movie titles."""
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
        
        # Method A: Knowledge Graph
        if "knowledge_graph" in results and "movies_playing" in results["knowledge_graph"]:
            for m in results["knowledge_graph"]["movies_playing"]:
                titles.append(m["name"])
        
        # Method B: Showtimes List
        elif "showtimes" in results:
            for day in results["showtimes"]:
                if "movies" in day:
                    for m in day["movies"]:
                        titles.append(m["name"])
    
        return titles
    except:
        return []

def get_movies_at_theater(theater_name, location, target_date_str=None):
    """
    Finds movies. 
    target_date_str: If None, checks "Today". If set, checks specific date.
    """
    if target_date_str:
        # Search for specific future date
        query = f"movies playing at {theater_name} {location} on {target_date_str}"
        movies = run_search_query(query)
    else:
        # Search Today
        query = f"movies playing at {theater_name} {location}"
        movies = run_search_query(query)

        # LATE NIGHT SAFETY NET (Only for Today)
        if len(set(movies)) < 4:
            movies_tomorrow = run_search_query(f"movies playing at {theater_name} {location} tomorrow")
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

def get_next_thursday():
    """Calculates the date string for the upcoming Thursday."""
    today = datetime.date.today()
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0: 
        days_ahead += 7
    next_thurs = today + datetime.timedelta(days=days_ahead)
    return next_thurs.strftime("%B %d")

# --- APP INTERFACE ---
st.title("🍿 True Critic Ratings")
st.caption("Select a theater below to see real critic scores.")

with st.sidebar:
    st.header("Settings")
    selected_theater_name = st.selectbox("Choose Theater", options=list(THEATERS.keys()))
    selected_zip = THEATERS[selected_theater_name]
    
    st.markdown("---")
    
    # Date Toggle
    date_mode = st.radio("When to check?", ["Today", "Next Thursday"], horizontal=True)
    
    target_date = None
    if date_mode == "Next Thursday":
        target_date = get_next_thursday()
        st.info(f"Checking for: **Thursday, {target_date}**")
        st.warning("Future Check Mode: Will NOT spend credits hunting for missing ratings.")
    else:
        st.info(f"Checking: **{selected_theater_name}**")
        st.caption(f"(Zip: {selected_zip})")

if st.button("Get True Ratings", type="primary"):
    with st.spinner(f"Checking schedule..."):
        # 1. Get Movies
        movies = get_movies_at_theater(selected_theater_name, selected_zip, target_date)
        
        if not movies:
            st.error("No movies found. Please try again later.")
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
                # If checking Today: We pay to find the rating.
                # If checking Next Thursday: We accept "N/A" to save money.
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
