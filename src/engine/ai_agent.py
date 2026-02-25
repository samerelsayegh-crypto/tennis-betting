import time
from datetime import datetime


class LiveBettingAgent:
    """
    Real-money AI betting agent that connects to the Betfair Exchange.
    Monitors live odds, detects points via odds movement, and places
    real bets using the user's chosen strategy.
    """

    # Minimum odds shift (%) to consider a point scored
    POINT_DETECTION_THRESHOLD = 0.03  # 3%
    POLL_INTERVAL = 5  # seconds between odds checks

    def __init__(self, client, market_id: str, target_selection_id: int,
                 target_player: str, strategy_name: str, base_bet: float,
                 max_loss: float = 50.0, max_single_bet: float = 20.0):
        self.client = client
        self.market_id = market_id
        self.target_selection_id = target_selection_id
        self.target_player = target_player
        self.strategy_name = strategy_name
        self.base_bet = base_bet
        self.current_bet = base_bet
        self.max_loss = max_loss
        self.max_single_bet = max_single_bet

        self.cumulative_pnl = 0.0
        self.points_detected = 0
        self.wins = 0
        self.losses = 0
        self.bets_placed = []

        self.prev_odds = None  # previous back odds for target player
        self.running = True
        self.status = "INITIALIZING"

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def poll_and_act(self) -> str:
        """
        Single iteration of the agent loop.
        Returns a log string for the UI.
        """
        logs = []

        # ── 1. Poll current market odds ──
        odds_data, err = self.client.get_market_odds(self.market_id)
        if err:
            self.status = "ERROR"
            self.running = False
            return f"🔴 [{self._ts()}] **ERROR polling odds:** {err}. Agent stopped."

        market_status = odds_data.get("marketStatus", "UNKNOWN")

        # Check if market is closed (match is over)
        if market_status == "CLOSED":
            self.status = "MATCH_ENDED"
            self.running = False
            return f"🏁 [{self._ts()}] **Match has ended.** Market closed. Final P&L: £{self.cumulative_pnl:,.2f}"

        # If market is not yet in-play, wait
        if market_status not in ("OPEN", "SUSPENDED"):
            # "INACTIVE" means pre-match — keep waiting
            pass

        runners = odds_data.get("runners", {})
        target_runner = runners.get(self.target_selection_id)

        if not target_runner:
            return f"⏳ [{self._ts()}] Waiting for runner data..."

        current_back = target_runner.get("back", 0.0)

        if current_back == 0.0:
            return f"⏳ [{self._ts()}] No back price available yet. Market may be suspended."

        # ── 2. First poll: establish baseline ──
        if self.prev_odds is None:
            self.prev_odds = current_back
            self.status = "MONITORING"
            return f"🟢 [{self._ts()}] Agent LIVE. Baseline odds for **{self.target_player}**: **{current_back}**. Monitoring for points..."

        # ── 3. Detect point via odds shift ──
        odds_change = (current_back - self.prev_odds) / self.prev_odds if self.prev_odds else 0
        abs_change = abs(odds_change)

        if abs_change < self.POINT_DETECTION_THRESHOLD:
            # No significant change — market is stable
            logs.append(f"⏳ [{self._ts()}] Odds: {current_back} (Δ {odds_change:+.1%}). No point detected.")
            self.prev_odds = current_back
            return "\n\n".join(logs)

        # ── Point detected! ──
        self.points_detected += 1
        point_winner_is_target = odds_change < 0  # odds dropping = player got stronger = won

        if point_winner_is_target:
            self.wins += 1
            profit = self.current_bet * (self.prev_odds - 1.0)
            self.cumulative_pnl += profit
            logs.append(f"✅ [{self._ts()}] **POINT {self.points_detected}: {self.target_player} WON!** Odds shifted {self.prev_odds} → {current_back} ({odds_change:+.1%})")
            logs.append(f"💰 Virtual profit on last stake: +£{profit:,.2f} | Cumulative P&L: £{self.cumulative_pnl:,.2f}")

            # Strategy: reset on win
            if self.strategy_name == "Doubling Strategy":
                self.current_bet = self.base_bet
                logs.append(f"🔄 Martingale reset → next bet: £{self.current_bet:,.2f}")
        else:
            self.losses += 1
            self.cumulative_pnl -= self.current_bet
            logs.append(f"❌ [{self._ts()}] **POINT {self.points_detected}: {self.target_player} LOST.** Odds shifted {self.prev_odds} → {current_back} ({odds_change:+.1%})")
            logs.append(f"📉 Loss: -£{self.current_bet:,.2f} | Cumulative P&L: £{self.cumulative_pnl:,.2f}")

            # Strategy: double on loss
            if self.strategy_name == "Doubling Strategy":
                self.current_bet = min(self.current_bet * 2.0, self.max_single_bet)
                logs.append(f"📈 Martingale double → next bet: £{self.current_bet:,.2f}")

        # Kelly recalculation
        if self.strategy_name == "Kelly Criterion":
            total = self.wins + self.losses
            win_rate = self.wins / total if total > 0 else 0.55
            edge = (win_rate * current_back) - 1.0
            if edge > 0:
                kelly_fraction = edge / (current_back - 1.0)
                self.current_bet = max(self.base_bet, min(kelly_fraction * 100, self.max_single_bet))
            else:
                self.current_bet = self.base_bet
            logs.append(f"🧮 Kelly recalc → next bet: £{self.current_bet:,.2f} (win rate: {win_rate:.0%})")

        # ── 4. Safety: check max loss ──
        if self.cumulative_pnl <= -self.max_loss:
            self.running = False
            self.status = "STOPPED_MAX_LOSS"
            logs.append(f"🛑 **MAX LOSS REACHED (£{self.max_loss}).** Agent shutting down for safety.")
            self.prev_odds = current_back
            return "\n\n".join(logs)

        # ── 5. Place the REAL bet for the next point ──
        bet_size = min(self.current_bet, self.max_single_bet)
        bet_size = round(max(bet_size, 2.0), 2)  # Betfair minimum bet is £2

        logs.append(f"🤖 [{self._ts()}] **Placing REAL BET:** BACK {self.target_player} | £{bet_size} @ {current_back}")

        bet_result, bet_err = self.client.place_bet(
            market_id=self.market_id,
            selection_id=self.target_selection_id,
            side="BACK",
            price=current_back,
            size=bet_size,
        )

        if bet_err:
            logs.append(f"⚠️ Bet placement error: {bet_err}")
        elif bet_result:
            bet_id = bet_result.get("betId", "N/A")
            matched = bet_result.get("sizeMatched", 0)
            avg_price = bet_result.get("averagePriceMatched", 0)
            self.bets_placed.append(bet_result)
            logs.append(f"✅ **BET CONFIRMED** | ID: {bet_id} | Matched: £{matched} @ {avg_price}")

        self.prev_odds = current_back
        return "\n\n".join(logs)
