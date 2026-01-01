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
# Enhanced headers to mimic a real user visiting the site
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/"
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

def scrape_rt_national_forecast():
    """
    Method B (Upcoming): Scrapes Rotten Tomatoes using a robust 'Broad Net' regex.
    """
    movies = []
    seen_titles = set()
    
    # URL 1: POPULAR (Holdovers)
    try:
        url_pop = "https://www.rottentomatoes.com/browse/movies_in_theaters/sort:popular"
        res_pop = requests.get(url_pop, headers=HEADERS, timeout=5)
        if res_pop.status_code == 200:
            html = res_pop.text
            # PATTERN 1: Look for the structural 'data-qa' tag (Most reliable)
            matches = re.findall(r'data-qa="discovery-media-list-item-title">\s*([^<]+)\s*</span>', html)
            
            # PATTERN 2: Fallback to finding any /m/ link with text inside
            if not matches:
                matches = re.findall(r'href="(/m/[^"]+)"[^>]*>\s*<span[^>]*>([^<]+)</span>', html)
                # If this pattern hits, it returns tuples (link, title). We just want titles for now.
                matches = [m[1] for m in matches]

            for title in matches[:15]:
                clean_title = title.strip()
                if clean_title not in seen_titles:
                    movies.append({
                        "title": clean_title,
                        # We reconstruct the link safely
                        "link": f"https://www.rottentomatoes.com/m/{re.sub(r'[^\w\s]', '', clean_title).lower().replace(' ', '_')}",
                        "type": "Popular"
                    })
                    seen_titles.add(clean_title)
    except Exception as e:
        print(f"Popular Scrape Error: {e}")

    # URL 2: COMING SOON (New Stuff)
    try:
        url_soon = "https://www.rottentomatoes.com/browse/movies_in_theaters/coming_soon"
        res_soon = requests.get(url_soon, headers=HEADERS, timeout=5)
        if res_soon.status_code == 200:
            html = res_soon.text
            matches = re.findall(r'data-qa="discovery-media-list-item-title">\s*([^<]+)\s*</span>', html)
            
            if not matches:
                 matches = re.findall(r'href="(/m/[^"]+)"[^>]*>\s*<span[^>]*>([^<]+)</span>', html)
                 matches = [m[1] for m in matches]

            for title in matches[:15]:
                clean_title = title.strip()
                if clean_title not in seen_titles:
                    movies.append({
                        "title": clean_title,
                        "link": f"https://www.rottentomatoes.com/m/{re.sub(r'[^\w\s]', '', clean_title).lower().replace(' ', '_')}",
                        "type": "New Release"
                    })
                    seen_titles.add(clean_title)
    except Exception as e:
        print(f"Coming Soon Scrape Error: {e}")
        
    return movies

def get_movies_at_theater(theater_name, use_national_forecast=False):
    """
    Decides whether to use Google (Today) or RT Forecast (Upcoming).
    """
    zip_code = THEATERS[theater_name]
    
    if use_national_forecast:
        # UPCOMING MODE -> RT FORECAST
        return scrape_rt_national_forecast()
    else:
        # TODAY MODE -> GOOGLE
        query = f"movies playing at {theater_name} {zip_code}"
        titles = run_search_query(query)
        
        # Late night safety net
        if len(set(titles)) < 4:
            titles_tomorrow = run_search_query(f"movies playing at {theater_name} {zip_code} tomorrow")
            titles.extend(titles_tomorrow)
            
        return list(set(titles))

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

# --- APP INTERFACE ---
st.title("🍿 True Critic Ratings")
st.caption("Select a theater below to see real critic scores.")

with st.sidebar:
    st.header("Settings")
    selected_theater_name = st.selectbox("Choose Theater", options=list(THEATERS.keys()))
    
    st.markdown("---")
    
    # Date Toggle
    date_mode = st.radio("When to check?", ["Today", "Upcoming Movies"], horizontal=True)
    
    use_forecast = False
    
    if date_mode == "Upcoming Movies":
        use_forecast = True
        st.info(f"Showing: **National Top 25**")
        st.warning("National Forecast Mode: Shows Popular & Coming Soon movies nationwide. (0 Credits)")
    else:
        st.info(f"Checking: **{selected_theater_name}**")
        st.caption("Using Google Search (1 Credit)")

if st.button("Get True Ratings", type="primary"):
    with st.spinner(f"Building schedule..."):
        
        # 1. Get Movies
        raw_results = get_movies_at_theater(selected_theater_name, use_forecast)
        
        if not raw_results:
             st.error("Could not fetch movie list. Rotten Tomatoes might be updating their site.")
        else:
            st.info(f"Found {len(raw_results)} movies. Getting scores...")
            
            data = []
            progress = st.progress(0)
            status_text = st.empty()
            
            for i, item in enumerate(raw_results):
                # Handle data format differences
                if isinstance(item, dict):
                    # Upcoming Mode
                    movie_title = item["title"]
                    # We re-guess the URL to be safe, as list URLs can vary
                    rt_url = None 
                    method = "Forecast"
                else:
                    # Today Mode
                    movie_title = item
                    rt_url = None
                    method = "Scanning..."

                status_text.text(f"Checking: {movie_title}")
                
                # Logic Flow
                rating = "N/A"
                
                # We always verify the link to ensure we get the Rating Page, not the Info Page
                rt_url = guess_rt_url(movie_title)
                if not rt_url and isinstance(item, dict):
                    # Fallback to the link found in the forecast if guess fails
                    rt_url = item["link"]
                
                if rt_url:
                    method = "Free Guess"
                    rating = scrape_rt_source(rt_url)
                    
                    # Paid Fallback (Only for Today mode)
                    if rating == "N/A" and date_mode == "Today":
                        rt_url = find_rt_url_paid(movie_title)
                        method = "Paid Search"
                        rating = scrape_rt_source(rt_url)
                
                sort_val = 0.0
                try:
                    sort_val = float(rating.split("/")[0])
                except:
                    pass
                
                data.append({
                    "Movie": movie_title,
                    "True Rating": rating,
                    "Source": method,
                    "_sort": sort_val,
                    "Link": rt_url
                })
                progress.progress((i + 1) / len(raw_results))
            
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
