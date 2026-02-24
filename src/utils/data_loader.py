import pandas as pd
import requests
from io import StringIO
import os
import streamlit as st

CACHE_DIR = "data"

@st.cache_data
def load_sackmann_pbp(year="current"):
    """
    Fetches the Jeff Sackmann ATP main play-by-play data for a specific year.
    Returns a pandas DataFrame.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    filename = f"pbp_matches_atp_main_{year}.csv"
    filepath = os.path.join(CACHE_DIR, filename)

    if os.path.exists(filepath):
        print(f"Loading {filename} from cache...")
        df = pd.read_csv(filepath)
    else:
        print(f"Downloading {filename} from Jeff Sackmann's GitHub...")
        url = f"https://raw.githubusercontent.com/JeffSackmann/tennis_pointbypoint/master/{filename}"
        response = requests.get(url)
        response.raise_for_status()
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        df.to_csv(filepath, index=False)
        print(f"Saved {filename} to {CACHE_DIR}.")

    return df

def parse_pbp_string(pbp_string: str, p1_is_server1: bool) -> list:
    """
    Parses a Sackmann pbp string (e.g. 'SSDSRRSRRR;RSSSRS;') into a list of 1s and 0s
    indicating if the selected player won the point.
    
    In Sackmann's logic:
    - Points in a game are characters until the next ';', '.', or '/'.
    - 'S' or 'A' means the Server of that game won the point.
    - 'R' or 'D' means the Returner of that game won the point.
    - server1 serves the first game of the match. Service alternates every game.
    (This is a simplified assumption that generally holds, apart from tiebreaks where standard alternating is 2 points, but the string is often split correctly or we just alternate by game block).
    
    For sake of dashboard demonstration, we will rely on game blocks.
    """
    if not isinstance(pbp_string, str):
        return []
        
    game_blocks = pbp_string.replace('.', ';').split(';')
    
    point_winners = []
    
    server1_serving = True  # the first game is served by server1
    
    for block in game_blocks:
        if not block:
            continue
            
        # Tiebreak formatting in Sackmann's files sometimes uses '/' to indicate point blocks
        points = block.replace('/', '')
        
        for p in points:
            if p in ["S", "A"]:
                # Current server won
                server1_won_point = server1_serving
            elif p in ["R", "D"]:
                # Current returner won
                server1_won_point = not server1_serving
            else:
                # Unknown character, skip
                continue
                
            if p1_is_server1:
                point_winners.append(1 if server1_won_point else 0)
            else:
                point_winners.append(0 if server1_won_point else 1)
                
        # Switch server after the game ends. Note: tiebreaks might mess with simple alternating server mapping but this is sufficient for backtesting general strategy.
        server1_serving = not server1_serving
        
    return point_winners

if __name__ == '__main__':
    # Test
    df = load_sackmann_pbp("current")
    if not df.empty:
        sample_match = df.iloc[0]
        print("Sample Match:", sample_match['server1'], "vs", sample_match['server2'])
        pbp_str = sample_match['pbp']
        print("PBP String:", pbp_str)
        p1_points = parse_pbp_string(pbp_str, p1_is_server1=True)
        print("P1 Points Array Length:", len(p1_points), "First 10:", p1_points[:10])
