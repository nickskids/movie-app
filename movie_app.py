import streamlit as st
import requests
import re
from serpapi import GoogleSearch

# --- CONFIGURATION ---
st.set_page_config(page_title="Theater Critic Check", page_icon="🍿")

try:
    SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
except:
    st.error("SerpApi Key not found! Please add it to Streamlit Secrets.")
    st.stop()

# --- FUNCTIONS ---
def get_movies_at_theater(theater_name, location):
    """Finds what movies are playing using Google Search."""
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
        
        # Method A: Knowledge Graph (Cleanest)
        if "knowledge_graph" in results and "movies_playing" in results["knowledge_graph"]:
            for m in results["knowledge_graph"]["movies_playing"]:
                movie_titles.append(m["name"])
        
        # Method B: Showtimes List
        elif "showtimes" in results:
            for day in results["showtimes"]:
                if "movies" in day:
                    for m in day["movies"]:
                        movie_titles.append(m["name"])
                    break
        
        return list(set(movie_titles))
    except Exception as e:
        return []

def get_rt_url(movie_title):
    """Finds the direct Rotten Tomatoes URL for a movie."""
    params = {
        "engine": "google",
        "q": f"{movie_title} rotten tomatoes movie",
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
    """
    Downloads page source and regex-matches the specific JSON pattern:
    "criticsAll":{"averageRating":"8.80"}
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            html = response.text
            
            # --- THE TARGETED REGEX ---
            # We look for "criticsAll" followed eventually by "averageRating":"X.X"
            # The pattern accounts for potential spaces or different quoting styles
            pattern = r'"criticsAll"\s*:\s*\{[^}]*"averageRating"\s*:\s*"(\d+\.?\d*)"'
            
            match = re.search(pattern, html)
            if match:
                return f"{match.group(1)}/10"
            
            # Backup: Sometimes it is labeled 'criticsScore' instead of 'criticsAll'
            # (Adding this just in case the key name varies by movie type)
            backup_pattern = r'"criticsScore"\s*:\s*\{[^}]*"averageRating"\s*:\s*"(\d+\.?\d*)"'
            match_backup = re.search(backup_pattern, html)
            if match_backup:
                return f"{match_backup.group(1)}/10"

    except Exception as e:
        print(f"Scrape Error: {e}")
        
    return "Not Found"

# --- APP INTERFACE ---
st.title("🍿 True Critic Ratings")
st.caption("Hunting for 'criticsAll' data in page source...")

with st.sidebar:
    st.header("Settings")
    theater = st.text_input("Theater", "AMC DINE-IN Levittown 10")
    loc = st.text_input("Zip Code", "11756")

if st.button("Get True Ratings", type="primary"):
    with st.spinner(f"Checking {theater}..."):
        # 1. Find Movies
        movies = get_movies_at_theater(theater, loc)
        
        if not movies:
            st.error("No movies found.")
        else:
            st.info(f"Found {len(movies)} movies. Scanning source code...")
            
            # 2. Scrape Each Movie
            data = []
            progress = st.progress(0)
            
            for i, movie in enumerate(movies):
                rt_url = get_rt_url(movie)
                rating = "N/A"
                
                if rt_url:
                    rating = scrape_rt_source(rt_url)
                
                # Sort logic
                sort_val = 0.0
                try:
                    sort_val = float(rating.split("/")[0])
                except:
                    pass
                
                data.append({
                    "Movie": movie,
                    "True Rating": rating,
                    "_sort": sort_val
                })
                progress.progress((i + 1) / len(movies))
            
            progress.empty()
            data.sort(key=lambda x: x["_sort"], reverse=True)
            
            st.dataframe(
                data,
                column_config={
                    "Movie": st.column_config.TextColumn("Movie"),
                    "True Rating": st.column_config.TextColumn("Avg Score (x/10)", width="medium"),
                    "_sort": None
                },
                hide_index=True,
                use_container_width=True
            )