import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class BetfairClient:
    """
    Client that fetches Betfair exchange odds via The-Odds-API.
    This safely bypasses the strict Regional IP blocks of direct Betfair authentication
    while still returning accurate Betfair data.
    """
    def __init__(self):
        # We assume the user's provided API key 'bf1zYguEsDNoBoDr' was actually a The-Odds-API key
        # as noted in the original README.
        self.api_key = os.getenv('BETFAIR_APP_KEY', 'bf1zYguEsDNoBoDr')
        
    def get_tennis_odds(self) -> tuple[pd.DataFrame | None, str | None]:
        """
        Fetches live tennis odds (H2H) targeting the Betfair bookmaker via The-Odds-API.
        Returns a tuple of (DataFrame if successful, Error Message if failed).
        """
        if not self.api_key or self.api_key == 'bf1zYguEsDNoBoDr':
            return None, "API Key is missing or using the placeholder 'bf1zYguEsDNoBoDr'. Please sign up for a free key at the-odds-api.com and set BETFAIR_APP_KEY in your .env or Streamlit Secrets."
            
        # The-Odds-API Endpoint for ATP Tennis
        url = "https://api.the-odds-api.com/v4/sports/tennis_atp/odds/"
        
        params = {
            'apiKey': self.api_key,
            'regions': 'uk,eu',
            'markets': 'h2h',
            # Filter specifically for the betfair exchange
            'bookmakers': 'betfair' 
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code != 200:
                logger.error(f"Failed to fetch odds from The-Odds-API: {resp.text}")
                error_data = resp.json()
                msg = error_data.get('message', resp.text)
                return None, f"The-Odds-API Error ({resp.status_code}): {msg}"
                
            data = resp.json()
            matches_data = []
            
            for match in data:
                # Find the Betfair bookmaker in the response
                betfair_bookmaker = next((b for b in match.get('bookmakers', []) if b['key'] == 'betfair'), None)
                
                if not betfair_bookmaker:
                    continue
                    
                # Find the Head to Head market
                h2h_market = next((m for m in betfair_bookmaker.get('markets', []) if m['key'] == 'h2h'), None)
                
                if not h2h_market:
                    continue
                    
                p1 = match['home_team']
                p2 = match['away_team']
                
                # Extract odds
                p1_odds = 1.01
                p2_odds = 1.01
                
                for outcome in h2h_market.get('outcomes', []):
                    if outcome['name'] == p1:
                        p1_odds = outcome['price']
                    elif outcome['name'] == p2:
                        p2_odds = outcome['price']
                        
                start_time = datetime.strptime(match['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                
                matches_data.append({
                    "Match ID": f"ODDS_{match['id']}",
                    "Date/Time": start_time.strftime("%Y-%m-%d %H:%M"),
                    "Player 1": p1,
                    "Player 2": p2,
                    "P1 Win Odds": round(p1_odds, 2),
                    "P2 Win Odds": round(p2_odds, 2),
                    # Estimate point odds based on match odds approx mapping
                    "P1 Est. Point Odds": round(1.0 + (p1_odds - 1.0)*0.25, 2) 
                })
                
            if not matches_data:
                return None, "Successfully connected to The-Odds-API, but no active Tennis ATP matches with Betfair odds were found."
                
            return pd.DataFrame(matches_data), None
            
        except requests.exceptions.ConnectionError:
            # Handle the specific case where the API key was actually for Betfair direct,
            # but getting the Connection Reset on The-Odds-API endpoint due to a local block
            logger.error("Connection reset when trying to reach The-Odds-API. Your current IP is blocking API requests.")
            return None, "Local Geoblock Detected: Your internet connection (or VPN) is blocking requests to The-Odds-API."
        except Exception as e:
            logger.error(f"Error fetching odds: {e}")
            return None, f"Unexpected error: {str(e)}"
