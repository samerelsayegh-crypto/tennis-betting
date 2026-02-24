import pandas as pd

class BaseStrategy:
    def __init__(self, base_bet: float = 1.0, odds: float = 1.90):
        self.base_bet = base_bet
        self.odds = odds
        self.reset_stats()

    def reset_stats(self):
        self.current_bet = self.base_bet
        self.current_bankroll = 0.0
        self.max_bet_placed = self.base_bet
        self.max_drawdown = 0.0
        self.current_losing_streak = 0
        self.longest_losing_streak = 0
        self.history = []

    def get_bet_amount(self) -> float:
        raise NotImplementedError

    def process_win(self, bet_placed: float) -> float:
        raise NotImplementedError

    def process_loss(self, bet_placed: float) -> float:
        raise NotImplementedError

    def simulate_match(self, point_winners: list) -> dict:
        self.reset_stats()

        for i, p1_won in enumerate(point_winners):
            point_num = i
            bet_this_round = self.get_bet_amount()
            
            p1_won_bool = bool(p1_won)
            
            if bet_this_round > self.max_bet_placed:
                self.max_bet_placed = bet_this_round
                
            if p1_won_bool:
                net_change = self.process_win(bet_this_round)
                self.current_bankroll += net_change
                self.current_losing_streak = 0
            else:
                net_change = self.process_loss(bet_this_round)
                self.current_bankroll += net_change
                self.current_losing_streak += 1
                if self.current_losing_streak > self.longest_losing_streak:
                    self.longest_losing_streak = self.current_losing_streak
                    
            if self.current_bankroll < self.max_drawdown:
                self.max_drawdown = self.current_bankroll
                
            self.history.append({
                "Point": point_num,
                "P1_Won": p1_won_bool,
                "Bet_Placed": round(bet_this_round, 2),
                "Win/Loss": round(net_change, 2),
                "Bankroll_After": round(self.current_bankroll, 2)
            })

        return {
            "total_net_profit": round(self.current_bankroll, 2),
            "max_bet_placed": round(self.max_bet_placed, 2),
            "capital_required": round(abs(self.max_drawdown), 2), 
            "longest_losing_streak": self.longest_losing_streak,
            "history_df": pd.DataFrame(self.history)
        }

class DoublingStrategy(BaseStrategy):
    """
    Formerly Martingale Strategy.
    Doubles bet on loss, resets to base bet on win.
    """
    def get_bet_amount(self) -> float:
        return self.current_bet

    def process_win(self, bet_placed: float) -> float:
        self.current_bet = self.base_bet
        return bet_placed * self.odds

    def process_loss(self, bet_placed: float) -> float:
        self.current_bet *= 2.0
        return -bet_placed

class FlatBettingStrategy(BaseStrategy):
    """
    Unit System Strategy.
    Bets exactly the base bet (1 Unit) on every single point regardless of outcome.
    """
    def get_bet_amount(self) -> float:
        return self.base_bet

    def process_win(self, bet_placed: float) -> float:
        return bet_placed * self.odds

    def process_loss(self, bet_placed: float) -> float:
        return -bet_placed

class KellyCriterionStrategy(BaseStrategy):
    """
    Calculates bet size purely dynamically based on the perceived edge.
    Formulary: Stake = [Bankroll * (Odds * Win Prob - 1)] / (Odds - 1)
    """
    def __init__(self, base_bet: float = 1.0, odds: float = 1.90, bankroll: float = 1000.0, win_prob: float = 0.55):
        super().__init__(base_bet, odds)
        self.starting_bankroll = bankroll
        self.win_prob = win_prob
        self.current_bet = 0.0

    def get_bet_amount(self) -> float:
        current_capital = self.starting_bankroll + self.current_bankroll
        if current_capital <= 0:
            return 0.0 # Bankrupt
            
        b = self.odds - 1.0
        if b <= 0:
            return 0.0
            
        kelly_frac = (self.win_prob * self.odds - 1.0) / b
        
        # If mathematically no edge exists, default to flat bet / action
        if kelly_frac <= 0:
            kelly_frac = 0.01 # 1% fraction fallback just to show mechanics
            
        # Optional: Half-Kelly or Fractional Kelly is safer. We will strictly use the formula.
        self.current_bet = current_capital * kelly_frac
        return self.current_bet

    def process_win(self, bet_placed: float) -> float:
        return bet_placed * self.odds

    def process_loss(self, bet_placed: float) -> float:
        return -bet_placed

if __name__ == '__main__':
    # Test suite
    seq = [0, 0, 1, 1, 0, 1]
    
    print("=== Doubling Strategy ===")
    res1 = DoublingStrategy(base_bet=1.0, odds=2.0).simulate_match(seq)
    print(res1['history_df'])
    
    print("\n=== Flat Betting Strategy ===")
    res2 = FlatBettingStrategy(base_bet=1.0, odds=2.0).simulate_match(seq)
    print(res2['history_df'])
    
    print("\n=== Kelly Criterion Strategy ===")
    res3 = KellyCriterionStrategy(base_bet=1.0, odds=2.0, bankroll=100.0, win_prob=0.55).simulate_match(seq)
    print(res3['history_df'])
