# Tennis Betting Analytics & Backtesting Dashboard

A full-stack Python application utilizing Streamlit to provide mocked Top 200 ATP/WTA rankings, upcoming match betting odds, and a powerful **Historical Point-by-Point Backtester** utilizing the Martingale betting simulation.

## Features Added 
1. **Rankings Dashboard**: A fallback API generating Top 200 ATP tennis players data.
2. **Upcoming Matches Dashboard**: A mock odds API to fulfill initial structural requirements.
3. **Point-by-Point Strategy Engine**: Math simulation logic running the Martingale Betting Strategy.
4. **Historical Backtesting Engine**: Fetches data from Jeff Sackmann's `tennis_pointbypoint` github repository automatically, caching it locally in the `data/` folder, parsing the point-strings, and executing the Strategy logic.

## Run Instructions

1. Open your terminal and navigate to the project directory:
```bash
cd "/Users/sameralsayegh/Desktop/Tennis betting"
```

2. Create a virtual environment (optional but recommended):
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install the dependencies:
```bash
pip install -r requirements.txt
```

4. Launch the Dashboard:
```bash
streamlit run app.py
```

The browser will open right up to the interactive tabs where you can simulate matches immediately.
