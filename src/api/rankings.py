import pandas as pd
import random

def get_atp_rankings(limit: int = 200) -> pd.DataFrame:
    """
    Returns a dataframe of the Top ATP/WTA tennis players.
    Since live premium API keys are required for real-time data, this serves as a structural fallback.
    In production, this would make a request to Sportradar or RapidAPI's API-Tennis.
    """
    # Generate realistic sounding mock data for the dashboard demo
    first_names = ["Novak", "Carlos", "Jannik", "Daniil", "Alexander", "Andrey", "Holger", "Casper", "Hubert", "Taylor", "Alex", "Stefanos", "Grigor", "Tommy", "Karen"]
    last_names = ["Djokovic", "Alcaraz", "Sinner", "Medvedev", "Zverev", "Rublev", "Rune", "Ruud", "Hurkacz", "Fritz", "De Minaur", "Tsitsipas", "Dimitrov", "Paul", "Khachanov"]
    
    data = []
    points = 10000
    for i in range(1, limit + 1):
        # We ensure top 10 are realistic names, rest are randomized mixes
        if i <= len(first_names):
            name = f"{first_names[i-1]} {last_names[i-1]}"
        else:
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            
        data.append({
            "Global Rank": i,
            "Player Name": name,
            "Tour": "ATP",
            "Ranking Points": points
        })
        points -= random.randint(10, 200)
        
    df = pd.DataFrame(data)
    return df
