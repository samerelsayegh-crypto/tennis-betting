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
    Client that connects directly to the Betfair Exchange API-NG.
    Uses Interactive Login to authenticate and then queries live tennis markets.
    """

    LOGIN_URL = "https://identitysso.betfair.com/api/login"
    API_URL = "https://api.betfair.com/exchange/betting/json-rpc/v1"
    KEEPALIVE_URL = "https://identitysso.betfair.com/api/keepAlive"

    # Betfair Event Type ID for Tennis
    TENNIS_EVENT_TYPE_ID = "2"

    def __init__(self):
        self.app_key = self._get_secret("BETFAIR_APP_KEY")
        self.username = self._get_secret("BETFAIR_USERNAME")
        self.password = self._get_secret("BETFAIR_PASSWORD")
        self.session_token = None

    @staticmethod
    def _get_secret(key: str) -> str:
        """Read from os.getenv first, then fall back to Streamlit secrets."""
        val = os.getenv(key, "")
        if val:
            return val
        try:
            import streamlit as st
            return st.secrets.get(key, "")
        except Exception:
            return ""

    def login(self) -> tuple[bool, str]:
        """
        Authenticate with Betfair using the Interactive Login endpoint.
        Returns (success: bool, message: str).
        """
        if not self.app_key:
            return False, "BETFAIR_APP_KEY is not set in .env"
        if not self.username or not self.password:
            return False, "BETFAIR_USERNAME or BETFAIR_PASSWORD is not set in .env"

        headers = {
            "X-Application": self.app_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        payload = {
            "username": self.username,
            "password": self.password,
        }

        try:
            resp = requests.post(self.LOGIN_URL, headers=headers, data=payload, timeout=15)

            if resp.status_code == 403:
                return False, "Betfair Geo-Restriction: Betfair has blocked this server's IP because it is hosted in a restricted country (e.g. US). This app must be run locally with a UK/EU VPN to connect to the Betfair Exchange. Using Mock Data instead."
            if resp.status_code != 200:
                return False, f"Login HTTP error {resp.status_code}"

            data = resp.json()
            status = data.get("status", "")
            if status == "SUCCESS":
                self.session_token = data.get("token")
                logger.info("Betfair login successful.")
                return True, "Logged in to Betfair Exchange successfully."
            else:
                error = data.get("error", "Unknown error")
                return False, f"Betfair login failed: {error}"

        except requests.exceptions.ConnectionError:
            return False, "Connection error: Could not reach Betfair login servers. Check your VPN or internet connection."
        except Exception as e:
            return False, f"Unexpected login error: {str(e)}"

    def _api_call(self, method: str, params: dict) -> tuple[dict | list | None, str | None]:
        """
        Make a JSON-RPC call to the Betfair Exchange API.
        """
        if not self.session_token:
            ok, msg = self.login()
            if not ok:
                return None, msg

        headers = {
            "X-Application": self.app_key,
            "X-Authentication": self.session_token,
            "Content-Type": "application/json",
        }

        payload = {
            "jsonrpc": "2.0",
            "method": f"SportsAPING/v1.0/{method}",
            "params": params,
            "id": 1,
        }

        try:
            resp = requests.post(self.API_URL, json=payload, headers=headers, timeout=15)

            if resp.status_code != 200:
                return None, f"Betfair API HTTP error {resp.status_code}: {resp.text}"

            data = resp.json()

            if "error" in data:
                error_detail = data["error"]
                return None, f"Betfair API error: {error_detail}"

            return data.get("result"), None

        except requests.exceptions.ConnectionError:
            return None, "Connection error reaching Betfair API. Check VPN/internet."
        except Exception as e:
            return None, f"Unexpected API error: {str(e)}"

    def get_tennis_odds(self) -> tuple[pd.DataFrame | None, str | None]:
        """
        Fetches live tennis match odds from the Betfair Exchange.
        Returns (DataFrame of matches, error message if failed).
        """
        # Step 1: Login if needed
        if not self.session_token:
            ok, msg = self.login()
            if not ok:
                return None, msg

        # Step 2: Get upcoming tennis Match Odds markets
        market_filter = {
            "eventTypeIds": [self.TENNIS_EVENT_TYPE_ID],
            "marketTypeCodes": ["MATCH_ODDS"],
            "inPlayOnly": False,
        }

        catalogue_result, err = self._api_call("listMarketCatalogue", {
            "filter": market_filter,
            "maxResults": "50",
            "marketProjection": [
                "EVENT",
                "RUNNER_DESCRIPTION",
                "MARKET_START_TIME",
                "COMPETITION",
            ],
            "sort": "FIRST_TO_START",
        })

        if err:
            return None, err

        if not catalogue_result:
            return None, "No tennis markets found on Betfair Exchange right now."

        # Step 3: Get prices for these markets
        market_ids = [m["marketId"] for m in catalogue_result]

        # Fetch in batches of 10 (Betfair recommendation)
        all_books = []
        for i in range(0, len(market_ids), 10):
            batch = market_ids[i:i + 10]
            book_result, err = self._api_call("listMarketBook", {
                "marketIds": batch,
                "priceProjection": {
                    "priceData": ["EX_BEST_OFFERS"],
                },
            })
            if err:
                logger.warning(f"Error fetching market book batch: {err}")
                continue
            if book_result:
                all_books.extend(book_result)

        # Step 4: Build a lookup from marketId -> book
        book_lookup = {b["marketId"]: b for b in all_books}

        # Step 5: Build the DataFrame
        matches_data = []
        for market in catalogue_result:
            market_id = market["marketId"]
            event = market.get("event", {})
            runners = market.get("runners", [])
            start_time_str = market.get("marketStartTime", "")
            competition = market.get("competition", {}).get("name", "")

            if len(runners) < 2:
                continue

            p1_name = runners[0].get("runnerName", "Player 1")
            p2_name = runners[1].get("runnerName", "Player 2")

            p1_odds = 0.0
            p2_odds = 0.0
            in_play = False

            book = book_lookup.get(market_id)
            if book:
                in_play = book.get("inPlay", False)
                book_runners = book.get("runners", [])
                for br in book_runners:
                    back_prices = br.get("ex", {}).get("availableToBack", [])
                    best_back = back_prices[0]["price"] if back_prices else 0.0

                    # Match by selectionId
                    if br["selectionId"] == runners[0]["selectionId"]:
                        p1_odds = best_back
                    elif br["selectionId"] == runners[1]["selectionId"]:
                        p2_odds = best_back

            # Parse start time
            try:
                dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                display_time = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                display_time = start_time_str

            matches_data.append({
                "Match ID": market_id,
                "Competition": competition,
                "Date/Time": display_time,
                "In Play": in_play,
                "Player 1": p1_name,
                "Player 2": p2_name,
                "P1 Selection ID": runners[0]["selectionId"],
                "P2 Selection ID": runners[1]["selectionId"],
                "P1 Win Odds": round(p1_odds, 2) if p1_odds else "-",
                "P2 Win Odds": round(p2_odds, 2) if p2_odds else "-",
                "P1 Est. Point Odds": round(1.0 + (p1_odds - 1.0) * 0.25, 2) if p1_odds else 1.90,
            })

        if not matches_data:
            return None, "Connected to Betfair successfully, but no active Tennis Match Odds markets were found."

        return pd.DataFrame(matches_data), None

    # ── Real Betting Methods ──────────────────────────────────────────

    def get_account_balance(self) -> tuple[float | None, str | None]:
        """Fetch the available balance from the user's Betfair account."""
        ACCOUNT_URL = "https://api.betfair.com/exchange/account/json-rpc/v1"
        if not self.session_token:
            ok, msg = self.login()
            if not ok:
                return None, msg

        headers = {
            "X-Application": self.app_key,
            "X-Authentication": self.session_token,
            "Content-Type": "application/json",
        }
        payload = {
            "jsonrpc": "2.0",
            "method": "AccountAPING/v1.0/getAccountFunds",
            "params": {},
            "id": 1,
        }
        try:
            resp = requests.post(ACCOUNT_URL, json=payload, headers=headers, timeout=10)
            data = resp.json()
            if "error" in data:
                return None, f"Account API error: {data['error']}"
            result = data.get("result", {})
            return result.get("availableToBetBalance", 0.0), None
        except Exception as e:
            return None, f"Failed to fetch balance: {str(e)}"

    def get_market_odds(self, market_id: str) -> tuple[dict | None, str | None]:
        """
        Poll a single market for current back/lay prices.
        Returns dict: {selectionId: {"back": price, "lay": price, "status": str}, ...}
        """
        result, err = self._api_call("listMarketBook", {
            "marketIds": [market_id],
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS"],
            },
        })
        if err:
            return None, err
        if not result:
            return None, "Market not found."

        book = result[0]
        market_status = book.get("status", "UNKNOWN")

        odds_data = {"marketStatus": market_status, "runners": {}}
        for runner in book.get("runners", []):
            sel_id = runner["selectionId"]
            back_prices = runner.get("ex", {}).get("availableToBack", [])
            lay_prices = runner.get("ex", {}).get("availableToLay", [])
            odds_data["runners"][sel_id] = {
                "back": back_prices[0]["price"] if back_prices else 0.0,
                "lay": lay_prices[0]["price"] if lay_prices else 0.0,
                "status": runner.get("status", "ACTIVE"),
            }
        return odds_data, None

    def place_bet(self, market_id: str, selection_id: int, side: str,
                  price: float, size: float) -> tuple[dict | None, str | None]:
        """
        Place a real bet on the Betfair Exchange.
        side: "BACK" or "LAY"
        price: the odds (decimal)
        size: stake in account currency (GBP)
        """
        result, err = self._api_call("placeOrders", {
            "marketId": market_id,
            "instructions": [{
                "selectionId": selection_id,
                "handicap": "0",
                "side": side,
                "orderType": "LIMIT",
                "limitOrder": {
                    "size": round(size, 2),
                    "price": price,
                    "persistenceType": "LAPSE",
                },
            }],
        })
        if err:
            return None, err
        if not result:
            return None, "No response from placeOrders."

        status = result.get("status", "UNKNOWN")
        if status == "SUCCESS":
            instruction_reports = result.get("instructionReports", [{}])
            report = instruction_reports[0] if instruction_reports else {}
            return {
                "status": "SUCCESS",
                "betId": report.get("betId", "N/A"),
                "placedDate": report.get("placedDate", ""),
                "averagePriceMatched": report.get("averagePriceMatched", 0),
                "sizeMatched": report.get("sizeMatched", 0),
            }, None
        else:
            error_code = result.get("errorCode", "UNKNOWN")
            instruction_reports = result.get("instructionReports", [{}])
            instr_error = instruction_reports[0].get("errorCode", "") if instruction_reports else ""
            return None, f"Bet placement failed: {error_code} / {instr_error}"
