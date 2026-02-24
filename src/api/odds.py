import pandas as pd
import random
from datetime import datetime, timedelta

def get_upcoming_matches() -> pd.DataFrame:
    """
    Returns a dataframe of upcoming matches and mock betting odds.
    Serves as a structural fallback until The-Odds-API key is plugged in.
    """
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
