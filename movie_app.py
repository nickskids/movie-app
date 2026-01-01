import streamlit as st
import requests
from serpapi import GoogleSearch

# --- PAGE SETUP ---
st.set_page_config(page_title="Theater Critic Check", page_icon="🍿")

# --- GET KEYS FROM SECURE CLOUD STORAGE ---
try:
    OMDB_API_KEY = st.secrets["OMDB_API_KEY"]
    SERPAPI_KEY = st.secrets["SERPAPI_KEY"]
except:
    st.error("API Keys not found! Please add them to Streamlit Secrets.")
    st.stop()

# --- FUNCTIONS ---
def get_showtimes_google(theater_name, location):
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
        
        # Check standard showtimes list
        if "showtimes" in results:
            for day in results["showtimes"]:
                if "movies" in day:
                    for movie in day["movies"]:
                        if "name" in movie:
                            movie_titles.append(movie["name"])
                    break 
        # Check knowledge graph fallback
        elif "knowledge_graph" in results and "movies_playing" in results["knowledge_graph"]:
             for movie in results["knowledge_graph"]["movies_playing"]:
                 movie_titles.append(movie["name"])

        return list(set(movie_titles))
    except Exception as e:
        st.error(f"Error fetching showtimes: {e}")
        return []

def get_movie_data(title):
    url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
    try:
        data = requests.get(url).json()
        if data.get("Response") == "True":
            rt_score = "N/A"
            for r in data.get("Ratings", []):
                if r["Source"] == "Rotten Tomatoes":
                    rt_score = r["Value"]
            return {
                "Title": data.get("Title"),
                "RT %": rt_score,
                "Metascore": data.get("Metascore", "N/A"),
                "IMDb": data.get("imdbRating", "N/A")
            }
    except:
        pass
    return None

# --- APP INTERFACE ---
st.title("🍿 Theater Critic Check")

with st.sidebar:
    st.header("Settings")
    theater_input = st.text_input("Theater Name", value="AMC DINE-IN Levittown 10")
    location_input = st.text_input("Location", value="11756")
    manual_mode = st.checkbox("Enter movies manually?")
    if manual_mode:
        manual_text = st.text_area("Paste Movie Names (one per line)", height=150)

if st.button("Get Ratings", type="primary"):
    movies_to_check = []
    
    if manual_mode and manual_text:
        movies_to_check = [line.strip() for line in manual_text.split('\n') if line.strip()]
    else:
        with st.spinner(f"Finding movies at {theater_input}..."):
            movies_to_check = get_showtimes_google(theater_input, location_input)
            if not movies_to_check:
                st.error("No movies found automatically. Try Manual Mode.")

    if movies_to_check:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, movie in enumerate(movies_to_check):
            status_text.text(f"Checking: {movie}")
            data = get_movie_data(movie)
            if data:
                results.append(data)
            progress_bar.progress((idx + 1) / len(movies_to_check))
            
        progress_bar.empty()
        status_text.empty()
        
        if results:
            st.dataframe(
                results, 
                column_config={
                    "RT %": st.column_config.TextColumn("Rotten Tomatoes", help="Tomatometer Score"),
                    "Metascore": st.column_config.NumberColumn("Critic Score (0-100)", format="%d"),
                },
                hide_index=True,
                use_container_width=True
            )