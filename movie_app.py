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

def run_search_query(query, target_date_str=None):
    """
    Greedy Search 4.0:
    1. Grabs ALL movies from ALL days returned (Today + Tomorrow + ...).
    2. This effectively "backfills" any movies that are sold out/past for today
       by finding them in tomorrow's list.
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
        movies = set() 
        found_date = "Unknown Date"
        
        # SOURCE 1: SHOWTIMES LIST
        date_match_found = False
        if "showtimes" in results:
            for day_block in results["showtimes"]:
                day_header = day_block.get("day", "").lower()
                
                # LOGIC BRANCH:
                if target_date_str:
                    # STRICT MODE: Only grab if header matches target (e.g. "Jan 8")
                    if target_date_str.lower() in day_header:
                        found_date = day_block.get("day", "Target Date")
                        if "movies" in day_block:
                            for m in day_block["movies"]:
                                movies.add(m["name"])
                        date_match_found = True
                        break 
                else:
                    # TODAY/ALL MODE: Grab EVERYTHING.
                    if "movies" in day_block:
                        for m in day_block["movies"]:
                            movies.add(m["name"])
                    found_date = "Today +"

        # SOURCE 2: KNOWLEDGE GRAPH (Carousel)
        if "knowledge_graph" in results and "movies_playing" in results["knowledge_graph"]:
            for m in results["knowledge_graph"]["movies_
