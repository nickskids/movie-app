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

# --- HELPER: HEADER FOR FAKING A BROWSER ---
# We use this for both guessing and scraping to avoid being blocked
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
    except Exception as e:
        return []

def get_rt_url_smart(title):
    """
    1. Tries to GUESS the URL (Free).
    2. If guess fails, USES SEARCH (1 Credit).
    """
    # --- STEP 1: FREE GUESS ---
    # Convert "Marty Supreme" -> "marty_supreme"
    # Remove special chars (like :) and replace spaces with underscores
    clean_title = re.sub(r'[^\w\s]', '', title).lower()
    slug = re.sub(r'\s+', '_', clean_title)
    
    guessed_url = f"https://www.rottentomatoes.com/m/{slug}"
    
    try:
        # We just ping the header to see if the page exists (faster)
        response = requests.get(guessed_url, headers=HEADERS, timeout=3)
        if response.status_code == 200:
            return guessed_url, "Free Guess"
    except:
        pass

    # --- STEP 2: PAID SEARCH (Fallback) ---
    # Only runs if the guess above failed (404)
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
                    return link, "Paid Search"
    except:
        pass
        
    return None, "Failed"

def scrape_rt_source(url):
    """
    Downloads source and finds 'criticsAll':{'averageRating':'8.8'}
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code == 200:
            html = response.text
            
            # The specific JSON pattern you found
            pattern = r'"criticsAll"\s*:\s*\{[^}]*"averageRating"\s*:\s*"(\d+\.?\d*)"'
            match = re.search(pattern, html)
            if match:
                return f"{match.group(1)}/10"
            
            # Backup pattern
            backup = r'"criticsScore"\s*:\s*\{[^}]*"averageRating"\s*:\s*"(\d+\.?\d*)"'
            match_back = re.search(backup, html)
            if match_back:
                return f"{match_back.group(1)}/10"

    except Exception as e:
        print(f"Scrape Error: {e}")
        
    return "N/A"

# --- APP INTERFACE ---
st.title("🍿 True Critic Ratings")
st.caption("Now with 'Smart Guessing' to save your API credits.")

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
            
            for i, movie in enumerate(movies):
                # 2. Smart Find URL (Mostly Free)
                rt_url, method = get_rt_url_smart(movie)
                rating = "N/A"
                
                # 3. Scrape Source (Free)
                if rt_url:
                    rating = scrape_rt_source(rt_url)
                
                # Sorting helper
                sort_val = 0.0
                try:
                    sort_val = float(rating.split("/")[0])
                except:
                    pass
                
                data.append({
                    "Movie": movie,
                    "True Rating": rating,
                    "Source": method, # Shows you if it was Free or Paid
                    "_sort": sort_val,
                    "Link": rt_url
                })
                progress.progress((i + 1) / len(movies))
            
            progress.empty()
            data.sort(key=lambda x: x["_sort"], reverse=True)
            
            st.dataframe(
                data,
                column_config={
                    "Movie": st.column_config.TextColumn("Movie"),
                    "True Rating": st.column_config.TextColumn("Avg Score (x/10)"),
                    "Source": st.column_config.TextColumn("Cost Method", help="Free Guess = $0. Paid Search = 1 Credit."),
                    "Link": st.column_config.LinkColumn("Verify"),
                    "_sort": None
                },
                hide_index=True,
                use_container_width=True
            )