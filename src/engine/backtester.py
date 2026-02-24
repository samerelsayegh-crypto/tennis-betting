from src.utils.data_loader import load_sackmann_pbp, parse_pbp_string
from src.engine.strategy import DoublingStrategy, FlatBettingStrategy, KellyCriterionStrategy

class StrategyBacktester:
    def __init__(self, year="current"):
        self.year = year
        self.df = None
        self.matches = []
        
    def load_data(self):
        self.df = load_sackmann_pbp(self.year)
        # Drop rows with empty pbp strings
        self.df = self.df.dropna(subset=['pbp'])
        
    def get_match_list(self):
        """
        Returns a list of display strings for matches to populate UI dropdowns.
        """
        if self.df is None:
            self.load_data()
            
        matches_info = []
        for idx, row in self.df.iterrows():
            date = getattr(row, 'date', 'Unknown')
            tny = getattr(row, 'tny_name', 'Unknown')
            p1 = getattr(row, 'server1', 'P1')
            p2 = getattr(row, 'server2', 'P2')
            score = getattr(row, 'score', '')
            match_str = f"{date} | {tny} | {p1} vs {p2} | {score}"
            matches_info.append({"index": idx, "display": match_str, "p1": p1, "p2": p2})
            
        return matches_info

    def run_backtest(self, match_index: int, target_player: str, strategy_name: str, base_bet: float, odds: float, **kwargs) -> dict:
        """
        Run the strategy on a specific match for a specific player.
        """
        if self.df is None:
            self.load_data()
            
        row = self.df.loc[match_index]
        pbp_string = str(row['pbp'])
        
        server1 = row['server1']
        server2 = row['server2']
        
        # Determine if target player is server1 or server2
        p1_is_server1 = (target_player == server1)
        
        # Parse points
        point_winners = parse_pbp_string(pbp_string, p1_is_server1)
        
        # Select Strategy
        if strategy_name == "Doubling Strategy":
            engine = DoublingStrategy(base_bet=base_bet, odds=odds)
        elif strategy_name == "Flat Betting (Unit System)":
            engine = FlatBettingStrategy(base_bet=base_bet, odds=odds)
        elif strategy_name == "Kelly Criterion":
            bankroll = kwargs.get('kelly_bankroll', 1000.0)
            win_prob = kwargs.get('kelly_win_prob', 0.55)
            engine = KellyCriterionStrategy(base_bet=base_bet, odds=odds, bankroll=bankroll, win_prob=win_prob)
        else:
            engine = DoublingStrategy(base_bet=base_bet, odds=odds)
            
        results = engine.simulate_match(point_winners)
        
        # Append match info to results
        results['match_info'] = f"{server1} vs {server2}"
        results['target_player'] = target_player
        results['strategy_name'] = strategy_name
        
        return results

if __name__ == "__main__":
    import sys
    sys.path.append(".")
    backtester = StrategyBacktester("current")
    matches = backtester.get_match_list()
    # Run a test on the first match
    if matches:
        first_match = matches[0]
        print(f"Testing Backtester on: {first_match['display']}")
        res = backtester.run_backtest(first_match['index'], target_player=first_match['p1'], strategy_name="Doubling Strategy", base_bet=1.0, odds=2.0)
        print("Total Profit:", res['total_net_profit'])
        print("Max Drawdown:", res['capital_required'])
        print("Max Bet:", res['max_bet_placed'])
