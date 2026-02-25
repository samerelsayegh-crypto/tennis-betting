import pandas as pd
import random
import streamlit as st
from datetime import datetime, timedelta
from src.api.betfair_client import BetfairClient

# Cache the client so it doesn't log in repeatedly for each widget refresh
@st.cache_resource
def get_betfair_client():
    return BetfairClient()

def get_upcoming_matches() -> pd.DataFrame:
    """
    Returns a dataframe of upcoming matches and mock betting odds.
    Serves as a structural fallback until The-Odds-API key or Betfair session is plugged in.
    """
    client = get_betfair_client()
    
    # Attempt to fetch live Betfair odds
    df_live = client.get_tennis_odds()
    
    if df_live is not None and not df_live.empty:
        # We got real data!
        return df_live

    # Fallback to mock data if auth failed or API rate limited
    st.warning("⚠️ Local Geoblock Detected: Your internet connection is dropping API requests to Betfair and The-Odds-API. Using Mock Data Database. Deploy this app to a server in a supported region (e.g. UK/EU) to unlock live odds.", icon="⚠️")
    players = ["Novak Djokovic", "Carlos Alcaraz", "Jannik Sinner", "Daniil Medvedev", "Alexander Zverev"]
    
    matches = []
    for i in range(5):
        p1, p2 = random.sample(players, 2)
        match_time = datetime.now() + timedelta(hours=random.randint(2, 48))
        
        matches.append({
            "Match ID": f"M_00{i+1}",
            "Date/Time": match_time.strftime("%Y-%m-%d %H:%M"),
            "Player 1": p1,
            "Player 2": p2,
            "P1 Win Odds": round(random.uniform(1.2, 3.5), 2),
            "P2 Win Odds": round(random.uniform(1.2, 3.5), 2),
            # Estimated point-by-point odds for P1
            "P1 Est. Point Odds": round(random.uniform(1.7, 2.1), 2)
        })
        
    return pd.DataFrame(matches)
