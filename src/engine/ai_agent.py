import time
import random

class LiveBettingAgent:
    """
    Simulates a live AI betting agent hooked into a betting exchange.
    Since we don't have a real WebSocket for live points, this paper-trades 
    by simulating point generation and applying the chosen betting strategy autonomously.
    """
    def __init__(self, target_player: str, strategy_name: str, base_bet: float, avg_odds: float):
        self.target_player = target_player
        self.strategy_name = strategy_name
        self.base_bet = base_bet
        self.current_bet = base_bet
        self.avg_odds = avg_odds
        
        self.bankroll = 1000.0  # Starting simulation bankroll
        self.points_played = 0
        self.wins = 0
        self.losses = 0

    def run_simulation_step(self) -> str:
        """
        Simulates exactly one point being played and the agent reacting to it.
        Returns a formatted log string to feed into the Streamlit terminal.
        """
        time.sleep(1.2)  # Simulate time passing for the UI terminal feel
        self.points_played += 1
        
        # 1. Agent logs intent
        log_msgs = []
        log_msgs.append(f"🤖 **[Point {self.points_played}]** Placing bet: **${self.current_bet:,.2f}** on **{self.target_player}** at odds {self.avg_odds}.")
        
        # 2. Simulate the point outcome (50/50 chance for simulation purposes, or slightly weighted by odds)
        # Implied probability = 1 / odds
        implied_prob = 1.0 / self.avg_odds if self.avg_odds > 1.0 else 0.5
        won_point = random.random() < implied_prob
        
        # 3. Process outcome
        if won_point:
            profit = self.current_bet * (self.avg_odds - 1.0)
            self.bankroll += profit
            self.wins += 1
            log_msgs.append(f"✅ Target WON the point! Profit: **+${profit:,.2f}** | Bankroll: ${self.bankroll:,.2f}")
            
            # Reset bet according to strategy
            if self.strategy_name == "Doubling Strategy":
                self.current_bet = self.base_bet
                log_msgs.append(f"🔄 Strategy Reset: Returning to base bet of ${self.base_bet:,.2f}.")
                
        else:
            self.bankroll -= self.current_bet
            self.losses += 1
            log_msgs.append(f"❌ Target LOST the point. Loss: **-${self.current_bet:,.2f}** | Bankroll: ${self.bankroll:,.2f}")
            
            # Increase bet according to strategy
            if self.strategy_name == "Doubling Strategy":
                self.current_bet *= 2.0
                log_msgs.append(f"📈 Martingale Trigger: Doubling bet to ${self.current_bet:,.2f} to recover losses.")
                
        # For Flat Betting, current_bet stays the same.
        # For Kelly Criterion, simulate bankroll update (simplified vs full backtester)
        if self.strategy_name == "Kelly Criterion":
            # Kelly = Bankroll * (Expected Value) / (Odds - 1)
            # Assuming a fixed 55% win prob here just for the paper-trading simulation
            edge = (0.55 * self.avg_odds) - 1.0
            if edge > 0:
                self.current_bet = self.bankroll * (edge / (self.avg_odds - 1.0))
                # Protect from going all in too dangerously or betting less than base
                self.current_bet = max(self.base_bet, min(self.current_bet, self.bankroll * 0.1))
            else:
                self.current_bet = self.base_bet
            log_msgs.append(f"🧮 Kelly Recalculation: Next stake sized dynamically at ${self.current_bet:,.2f}.")
            
        # Add slight delay for readability
        time.sleep(0.5)
        
        return "\n\n".join(log_msgs)
