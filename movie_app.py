import streamlit as st
import requests
import re
import datetime
from serpapi import GoogleSearch

# --- CONFIGURATION ---
st.set_page_config(page_title="RT Critic Ratings", page_icon="🍅", layout="wide")

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

def run_search_query(query, match_date_string=None):
    """
    Runs search. Returns a Tuple: (List of Movies, Boolean is_fallback)
    """
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
        specific_movies = []
        fallback_movies = []
        
        # 1. SCAN FOR SPECIFIC DATE
        if match_date_string and "showtimes" in results:
            for day_block in results["showtimes"]:
                day_header = day_block.get("day", "").lower()
                if match_date_string.lower() in day_header:
                    if "movies" in day_block:
                        for m in day_block["movies"]:
                            specific_movies.append(m["name"])
        
        # 2. IF FOUND, RETURN IMMEDIATELY
        if specific_movies:
            return specific_movies, False
            
        # 3. IF NOT FOUND, GRAB FALLBACK
        if "knowledge_graph" in results and "movies_playing" in results["knowledge_graph"]:
            for m in results["knowledge_graph"]["movies_playing"]:
                fallback_movies.append(m["name"])
                
        if not fallback_movies and "showtimes" in results:
             for day_block in results["showtimes"]:
                 if "movies" in day_block:
                     for m in day_block["movies"]:
                         fallback_movies.append(m["name"])
                     break 
        
        return list(set(fallback_movies)), True

    except:
        return [], False

def get_movies_at_theater(theater_name, location, target_date_short=None, target_date_long=None):
    if target_date_long:
        query = f"showtimes for {theater_name} {location} on {target_date_long}"
        movies, is_fallback = run_search_query(query, match_date_string=target_date_short)
        return movies, is_fallback
    else:
        query = f"movies playing at {theater_name} {location}"
        movies, _ = run_search_query(query)
        
        if len(set(movies)) < 4:
            movies_tomorrow, _ = run_search_query(f"movies playing at {theater_name} {location} tomorrow")
            movies.extend(movies_tomorrow)
            
        return list(set(movies)), False

def guess_rt_url(title):
    clean_title = re.sub(r'[^\w\s]', '', title).lower()
    slug = re.sub(r'\s+', '_', clean_title)
    current_year = datetime.date.today().year
    
    potential_urls = [
        f"https://www.rottentomatoes.com/m/{slug}_{current_year + 1}",
        f"https://www.rottentomatoes.com/m/{slug}_{current_year}",
        f"https://www.rottentomatoes.com/m/{slug}_{current_year - 1}",
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
    """
    Extracts TWO values:
    1. Average Rating (e.g. "8.8/10")
    2. Review Count (e.g. "245")
    """
    if not url: return "N/A", "N/A"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code == 200:
            html = response.text
            
            rating = "N/A"
            count = "N/A"
            
            # Regex for RATING
            # Looks for "averageRating":"8.8" inside criticsAll block
            match_rating = re.search(r'"criticsAll"\s*:\s*\{[^}]*?"averageRating"\s*:\s*"(\d+\.?\d*)"', html)
            if match_rating:
                rating = f"{match_rating.group(1)}/10"
                
            # Regex for REVIEW COUNT
            # Looks for "reviewCount":123 inside criticsAll block
            match_count = re.search(r'"criticsAll"\s*:\s*\{[^}]*?"reviewCount"\s*:\s*(\d+)', html)
            if match_count:
                count = match_count.group(1)
            
            # Backup: Check "criticsScore" block if criticsAll fails
            if rating == "N/A":
                 match_rating_back = re.search(r'"criticsScore"\s*:\s*\{[^}]*?"averageRating"\s*:\s*"(\d+\.?\d*)"', html)
                 if match_rating_back: rating = f"{match_rating_back.group(1)}/10"

            return rating, count
            
    except:
        pass
        
    return "N/A", "N/A"

def get_next_thursday_data():
    today = datetime.date.today()
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0: 
        days_ahead += 7
    next_thurs = today + datetime.timedelta(days=days_ahead)
    
    long_fmt = next_thurs.strftime("%B ") + str(next_thurs.day)
    short_fmt = next_thurs.strftime("%b ") + str(next_thurs.day)
    
    return short_fmt, long_fmt, days_ahead

# --- APP INTERFACE ---
st.title("🍅 Rotten Tomatoes All Critics Average Ratings")
st.caption("Select a theater in the **sidebar menu** to see real critic scores.")

with st.sidebar:
    st.header("Settings")
    selected_theater_name = st.selectbox("Choose Theater", options=list(THEATERS.keys()))
    selected_zip = THEATERS[selected_theater_name]
    
    st.markdown("---")
    
    date_mode = st.radio("When to check?", ["Today", "Next Thursday"], horizontal=True)
    
    target_short = None
    target_long = None
    
    if date_mode == "Next Thursday":
        target_short, target_long, days_away = get_next_thursday_data()
        st.info(f"Checking for: **Thursday, {target_long}**")
        if days_away > 5:
            st.warning("⚠️ Early Check: Schedule might not be posted yet.")
    else:
        st.info(f"Checking: **{selected_theater_name}**")

if st.button("Get True Ratings", type="primary"):
    with st.spinner(f"Checking schedule..."):
        
        movies, is_fallback = get_movies_at_theater(selected_theater_name, selected_zip, target_short, target_long)
        
        if not movies:
            st.error("No movies found at all.")
        else:
            if is_fallback:
                st.warning(f"⚠️ Schedule for **{target_long}** is not posted yet. Showing **Today's** movies so your credit isn't wasted.")
            else:
                if date_mode == "Next Thursday":
                    st.success(f"✅ Found specific schedule for **{target_long}**!")
                else:
                    st.info(f"Found {len(movies)} movies.")

            data = []
            progress = st.progress(0)
            status_text = st.empty()
            
            for i, movie in enumerate(movies):
                status_text.text(f"Checking: {movie}")
                
                # Phase 1: Free Guess
                url = guess_rt_url(movie)
                method = "Free Guess"
                # Scrape both rating and count
                rating, count = scrape_rt_source(url)
                
                # Phase 2: Paid Fallback
                if rating == "N/A" and (date_mode == "Today" or is_fallback):
                    url = find_rt_url_paid(movie)
                    method = "Paid Search"
                    rating, count = scrape_rt_source(url)
                
                sort_val = 0.0
                try:
                    sort_val = float(rating.split("/")[0])
                except:
                    pass
                
                data.append({
                    "Movie": movie,
                    "True Rating": rating,
                    "Reviews": count,  # New Field
                    "Source": method,
                    "_sort": sort_val,
                    "Link": url
                })
                progress.progress((i + 1) / len(movies))
            
            progress.empty()
            status_text.empty()
            data.sort(key=lambda x: x["_sort"], reverse=True)
            
            # Display with new column
            st.dataframe(
                data,
                column_order=["Movie", "True Rating", "Reviews", "Source", "Link"], 
                column_config={
                    "Movie": st.column_config.TextColumn("Movie", width="medium"),
                    "True Rating": st.column_config.TextColumn("Score", width="small"),
                    "Reviews": st.column_config.TextColumn("Count", width="small"), # New Column Config
                    "Source": st.column_config.TextColumn("Method", width="small"),
                    "Link": st.column_config.LinkColumn("Verify"),
                    "_sort": None
                },
                hide_index=True,
                use_container_width=True
            )
