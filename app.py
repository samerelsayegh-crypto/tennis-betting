import streamlit as st
import pandas as pd
import plotly.express as px
from src.api.rankings import get_atp_rankings
from src.api.odds import get_upcoming_matches
from src.engine.backtester import StrategyBacktester
from src.engine.ai_agent import LiveBettingAgent
import time

st.set_page_config(page_title="Tennis Betting Analytics", layout="wide", page_icon="🎾")

st.title("🎾 Tennis Betting Analytics & Backtesting Dashboard")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Rankings & Odds", "⚙️ Strategy Backtester", "📈 Backtest Results", "🤖 AI Live Agent"])

with tab1:
    st.header("Top 200 Players & Form")
    st.write("Live premium API fallback simulation.")
    df_rankings = get_atp_rankings(200)
    st.dataframe(df_rankings, use_container_width=True)
    
    st.markdown("---")
    st.header("Upcoming Matches & Odds")
    df_odds = get_upcoming_matches()
    st.dataframe(df_odds, use_container_width=True)

with tab2:
    st.header("Strategy Configuration")
    
    strategy_name = st.selectbox(
        "Select Betting Strategy Matrix:", 
        [
            "Doubling Strategy", 
            "Flat Betting (Unit System)", 
            "Kelly Criterion"
        ],
        help="Strategies curated from the Tennis Betting Strategy manual."
    )
    
    # Dynamic strategy description
    if strategy_name == "Doubling Strategy":
        st.info("**Doubling Strategy:** Bet Base Amount. On Win, take profit and reset. On Loss, EXACTLY DOUBLE previous bet amount to recover.")
    elif strategy_name == "Flat Betting (Unit System)":
        st.info("**Flat Betting:** Strict bankroll management. Bet exactly 1 Unit (Base Bet Amount) on every single point regardless of confidence.")
    elif strategy_name == "Kelly Criterion":
        st.info("**Kelly Criterion:** Dynamically changes bet sizing based on mathematical edge: `Stake = [Bankroll × (Odds × Win Prob – 1)] ÷ (Odds – 1)`")

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        base_bet = st.number_input("Base Bet Amount ($)", min_value=1.0, value=1.0, step=1.0)
    with col2:
        default_odds = st.number_input("Average Point Odds (Decimal)", min_value=1.01, value=1.90, step=0.01)
        
    # Additional Kelly Criterion Parameters
    kelly_bankroll = 1000.0
    kelly_win_prob = 0.55
    if strategy_name == "Kelly Criterion":
        st.markdown("##### Kelly Strategy Parameters")
        kcol1, kcol2 = st.columns(2)
        with kcol1:
            kelly_bankroll = st.number_input("Starting Bankroll ($)", min_value=10.0, value=1000.0, step=100.0)
        with kcol2:
            kelly_win_prob = st.slider("Assumed Win Probability (%)", min_value=10, max_value=99, value=55, step=1) / 100.0
            st.caption(f"Calculated Edge based on Odds: {round((kelly_win_prob * default_odds) - 1.0, 3)}")

    st.markdown("---")
    st.subheader("Historical Match Selection")
    
    def load_backtester():
        return StrategyBacktester("current")
        
    with st.spinner("Fetching Jeff Sackmann play-by-play datasets (this may take a moment on first load)..."):
        try:
            bt = load_backtester()
            matches = bt.get_match_list()
        except Exception as e:
            st.error(f"Failed to fetch historical data: {e}")
            matches = []

    if matches:
        match_displays = [m['display'] for m in matches]
        selected_match_str = st.selectbox("Select a Historical Match:", match_displays)
        
        selected_match = next(m for m in matches if m['display'] == selected_match_str)
        p1 = selected_match['p1']
        p2 = selected_match['p2']
        
        target_player = st.selectbox("Assign Target Player (Strategy will bet on this player to win points):", [p1, p2])
        
        if st.button("Run Simulation", type="primary"):
            with st.spinner(f"Simulating point-by-point {strategy_name}..."):
                results = bt.run_backtest(
                    match_index=selected_match['index'], 
                    target_player=target_player, 
                    strategy_name=strategy_name,
                    base_bet=base_bet, 
                    odds=default_odds,
                    kelly_bankroll=kelly_bankroll,
                    kelly_win_prob=kelly_win_prob
                )
                st.session_state['results'] = results
                st.success("Simulation complete! Check the '📈 Backtest Results' tab.")
                
with tab3:
    st.header("Backtest Simulation Results")
    if 'results' in st.session_state:
        res = st.session_state['results']
        
        st.subheader(f"Strategy: {res.get('strategy_name', 'Strategy')} | Match: {res['match_info']}")
        st.write(f"Target Player: **{res['target_player']}**")
        
        # Stats Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Net Profit/Loss ($)", f"{res['total_net_profit']:,.2f}")
        c2.metric("Max Bet Placed ($)", f"{res['max_bet_placed']:,.2f}")
        c3.metric("Max Drawdown/Capital Req ($)", f"{res['capital_required']:,.2f}")
        c4.metric("Longest Losing Streak", res['longest_losing_streak'])
        
        st.markdown("---")
        st.subheader("Bankroll Fluctuation Over Match")
        df_history = res['history_df']
        
        fig = px.line(df_history, x='Point', y='Bankroll_After', title='Bankroll over Time', 
                      labels={'Bankroll_After': 'Bankroll ($)', 'Point': 'Point Number'})
        fig.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Point-by-Point Log")
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("Run a simulation in the '⚙️ Strategy Backtester' tab first to view results here.")

with tab4:
    st.header("🤖 Autonomous AI Betting Agent")
    st.write("Deploy the AI to watch an upcoming match and execute trades autonomously via paper-trading.")
    
    st.subheader("1. Select Target Match")
    try:
        df_upcoming = get_upcoming_matches()
        if df_upcoming is not None and not df_upcoming.empty:
            match_options = df_upcoming.apply(lambda row: f"{row['Player 1']} vs {row['Player 2']} ({row['Date/Time']})", axis=1).tolist()
            selected_match_str = st.selectbox("Select Match to Monitor:", match_options)
            
            selected_row = df_upcoming.iloc[match_options.index(selected_match_str)]
            p1 = selected_row['Player 1']
            p2 = selected_row['Player 2']
            p1_odds = float(selected_row['P1 Est. Point Odds']) if 'P1 Est. Point Odds' in selected_row else 1.90
            
            st.subheader("2. Configure Agent Parameters")
            col1, col2 = st.columns(2)
            with col1:
                target_player = st.selectbox("Player to Back:", [p1, p2])
                agent_strategy = st.selectbox("Agent Betting Strategy:", ["Doubling Strategy", "Flat Betting (Unit System)", "Kelly Criterion"])
                
            with col2:
                agent_base_bet = st.number_input("Starting Base Bet ($)", min_value=1.0, value=10.0, step=5.0)
                # Assign assumed odds for point simulation
                agent_odds = p1_odds if target_player == p1 else 1.90
                st.metric("Estimated Point Odds", round(agent_odds, 2))
                
            st.markdown("---")
            
            if st.button("🚀 Deploy AI Agent", type="primary"):
                st.subheader("🔴 Live Agent Console")
                # Setup UI container for logs
                terminal_container = st.empty()
                terminal_container.info("Initializing Agent Engine...")
                
                # Create the agent instance
                agent = LiveBettingAgent(
                    target_player=target_player,
                    strategy_name=agent_strategy,
                    base_bet=agent_base_bet,
                    avg_odds=agent_odds
                )
                
                # Simulation loop
                max_points_to_simulate = 20
                
                full_log = ""
                for i in range(max_points_to_simulate):
                    # Agent runs a single step
                    step_log = agent.run_simulation_step()
                    full_log = f"{step_log}\n\n---\n\n" + full_log
                    
                    # Update container with markdown log
                    terminal_container.markdown(f"```text\n{full_log}\n```")
                    
                    if agent.bankroll <= 0:
                        st.error("📉 Bankroll depleted. Agent automatically shut down.")
                        break
                        
                st.success(f"Simulation completed. Final Bankroll: ${agent.bankroll:,.2f} | Wins: {agent.wins} | Losses: {agent.losses}")
                    
        else:
            st.info("No upcoming matches available to monitor right now.")
    except Exception as e:
         st.error(f"Could not load upcoming matches for the agent: {e}")
