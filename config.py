"""Configuration settings for Win-Win Trade Suggestions system."""

# League Configuration
LEAGUE_ID = "1240782642371104768"
SLEEPER_LEAGUE_ID = LEAGUE_ID  # Alias for CLI compatibility

# API Endpoints
FANTASYCALC_API_URL = "https://api.fantasycalc.com/values/current"
SLEEPER_API_BASE_URL = "https://api.sleeper.app/v1"

# FantasyCalc API Parameters
FANTASYCALC_PARAMS = {
    "isDynasty": False,
    "numQbs": 1,
    "numTeams": 12,
    "ppr": 1
}

# Lineup Configuration (standard redraft)
LINEUP_CONFIG = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 1  # RB/WR/TE eligible
}

# Trade Analysis Parameters
FAIRNESS_THRESHOLD = 0.12  # 12% maximum value delta
MIN_STARTER_GAIN = 3.0     # Minimum points improvement required
MAX_TRADES_PER_WEEK = 6    # Exactly 6 trades to cover all 12 teams
TOTAL_TEAMS = 12

# API Configuration
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# ChatGPT API Configuration
import os
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')  # Set via environment variable

# Output Configuration
OUTPUT_DECIMAL_PLACES = 1
ASCII_ONLY = True
DEFAULT_OUTPUT_PATH = "weekly_trades_output.txt"
