import streamlit as st
import requests
import re
from serpapi import GoogleSearch

# --- CONFIGURATION ---
st.set_page_config(page_title="Theater Critic Check", page_icon="🍿", layout="wide")

try:
    SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
except:
    st.error("SerpApi Key not found! Please add it to Streamlit Secrets.")
    st.stop()

# --- HEADERS ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- FUNCTIONS ---
def get_movies_at_theater(theater_name, location):
    """Finds what movies are playing (Costs 1 Search Credit)."""
    query = f"movies playing at {theater_name} {location}"
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
        movie_titles = []
        
        if "knowledge_graph" in results and "movies_playing" in results["knowledge_graph"]:
            for m in results["knowledge_graph"]["movies_playing"]:
                movie_titles.append(m["name"])
        elif "showtimes" in results:
            for day in results["showtimes"]:
                if "movies" in day:
                    for m in day["movies"]:
                        movie_titles.append(m["name"])
                    break
        
        return list(set(movie_titles))
    except:
        return []

def guess_rt_url(title):
    """
    FUTURE-PROOF LOGIC:
    Checks specific years first to handle Remakes/Reboots.
    """
    clean_title = re.sub(r'[^\w\s]', '', title).lower()
    slug = re.sub(r'\s+', '_', clean_title)
    
    # Updated List: 2025 -> 2028
    potential_urls = [
        f"https://www.rottentomatoes.com/m/{slug}_2025",
        f"https://www.rottentomatoes.com/m/{slug}_2026",
        f"https://www.rottentomatoes.com/m/{slug}_2027",
        f"https://www.rottentomatoes.com/m/{slug}_2028",
        f"https://www.rottentomatoes.com/m/{slug}" # Standard
    ]
    
    for url in potential_urls:
        try:
            # INCREASED TIMEOUT: 0.5 -> 1.0
            # This prevents "Zootopia 2" from failing just because the wifi blinked.
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
            
            # Primary Pattern
            pattern = r'"criticsAll"\s*:\s*\{[^}]*"averageRating"\s*:\s*"(\d+\.?\d*)"'
            match = re.search(pattern, html)
            if match:
                return f"{match.group(1)}/10"
            
            # Backup Pattern
            backup = r'"criticsScore"\s*:\s*\{[^}]*"averageRating"\s*:\s*"(\d+\.?\d*)"'
            match_back = re.search(backup, html)
            if match_back:
                return f"{match_back.group(1)}/10"

    except:
        pass
        
    return "N/A"

# --- APP INTERFACE ---
st.title("🍿 True Critic Ratings")
st.caption("Updated: Optimized connection timeout to save credits.")

with st.sidebar:
    st.header("Settings")
    theater = st.text_input("Theater", "AMC DINE-IN Levittown 10")
    loc = st.text_input("Zip Code", "11756")

if st.button("Get True Ratings", type="primary"):
    with st.spinner(f"Checking {theater}..."):
        # 1. Find Movies (1 Credit)
        movies = get_movies_at_theater(theater, loc)
        
        if not movies:
            st.error("No movies found.")
        else:
            st.info(f"Found {len(movies)} movies. Hunting for ratings...")
            
            data = []
            progress = st.progress(0)
            status_text = st.empty()
            
            for i, movie in enumerate(movies):
                status_text.text(f"Checking: {movie}")
                
                # Phase 1: Future-Proof Guess
                url = guess_rt_url(movie)
                method = "Free Guess"
                rating = scrape_rt_source(url)
                
                # Phase 2: Fallback to Paid Search
                if rating == "N/A":
                    url = find_rt_url_paid(movie)
                    method = "Paid Search"
                    rating = scrape_rt_source(url)
                
                # Sorting helper
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
            
            # Display
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
