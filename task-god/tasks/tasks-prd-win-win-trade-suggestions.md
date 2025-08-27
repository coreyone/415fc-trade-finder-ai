# Tasks: Win-Win Trade Suggestions — Sleeper + FantasyCalc

Based on the PRD: `prd-win-win-trade-suggestions.md`

## Relevant Files

- `weekly_trades.py` - Main script containing the complete trade generation pipeline
- `weekly_trades.test.py` - Unit tests for the main script functions
- `config.py` - Configuration settings for league ID, API endpoints, and parameters
- `data_fetcher.py` - Module for API calls to FantasyCalc and Sleeper
- `data_fetcher.test.py` - Unit tests for API integration functions
- `trade_analyzer.py` - Module for calculating starter values, needs, and generating trades
- `trade_analyzer.test.py` - Unit tests for trade analysis logic
- `output_formatter.py` - Module for generating plain text output in specified format
- `output_formatter.test.py` - Unit tests for output formatting
- `requirements.txt` - Python dependencies list
- `README.md` - Documentation for setup and usage

### Notes

- Unit tests should be placed alongside the code files they are testing
- Use `python -m pytest` to run all tests
- The main script should be executable via command line with arguments

## Tasks

- [x] 1.0 Set up project structure and dependencies
  - [x] 1.1 Create `requirements.txt` with dependencies: pandas, numpy, networkx, requests, python-dateutil
  - [x] 1.2 Create `config.py` with league ID (1240782642371104768), API endpoints, and lineup configuration
  - [x] 1.3 Set up basic project structure with separate modules for data fetching, analysis, and output
  - [x] 1.4 Create `README.md` with setup instructions and usage examples
  - [x] 1.5 Initialize pytest configuration for testing

- [x] 2.0 Implement data fetching from FantasyCalc and Sleeper APIs
  - [x] 2.1 Create `data_fetcher.py` module with API client functions
  - [x] 2.2 Implement `fetch_fantasycalc_values()` function with parameters: isDynasty=false, numQbs=1, numTeams=12, ppr=1
  - [x] 2.3 Implement `fetch_sleeper_rosters()` function to get league rosters via API
  - [x] 2.4 Implement `fetch_sleeper_users()` function to map user IDs to display names
  - [x] 2.5 Add error handling and retry logic for API calls with timeouts
  - [x] 2.6 Create `join_player_data()` function using sleeper_id as primary key with name/position fallback
  - [x] 2.7 Write unit tests in `data_fetcher.test.py` for all API functions

- [x] 3.0 Build trade analysis engine (starter calculations, needs identification, trade generation)
  - [x] 3.1 Create `trade_analyzer.py` module with core analysis functions
  - [x] 3.2 Implement `calculate_starter_values()` function for 1QB/2RB/2WR/1TE/1FLEX lineup
  - [x] 3.3 Implement `compute_positional_deltas()` function to compare each team vs league median
  - [x] 3.4 Implement `identify_needs_surplus()` function where negative delta = need, positive = surplus
  - [x] 3.5 Implement `generate_candidate_trades()` function for 1-for-1 and 2-for-2 trades
  - [x] 3.6 Add trade scoring logic: gain_A + gain_B - penalty_fairness - risk_flags
  - [x] 3.7 Implement fairness constraint checking (≤12% value delta)
  - [x] 3.8 Add requirement for meaningful impact (at least one projected starter per side)
  - [x] 3.9 Write comprehensive unit tests in `trade_analyzer.test.py`

- [x] 4.0 Implement trade matching algorithm with perfect matching
  - [x] 4.1 Implement `build_trade_graph()` function to create weighted graph from candidate trades
  - [x] 4.2 Implement `find_perfect_matching()` function using NetworkX maximum-weight matching
  - [x] 4.3 Add constraint relaxation logic if perfect matching fails (widen fairness, allow 2-for-1, lower gains)
  - [x] 4.4 Ensure exactly 6 disjoint trades covering all 12 teams
  - [x] 4.5 Add validation to prevent impossible matching scenarios
  - [x] 4.6 Write unit tests for matching algorithm with various team configurations

- [x] 5.0 Create output formatting and CLI interface  
  - [x] 5.1 Create `output_formatter.py` module for plain text generation
  - [x] 5.2 Implement `generate_starter_snapshot()` function showing team deltas vs league median
  - [x] 5.3 Implement `format_trade_recommendations()` function with fairness percentages and gains
  - [x] 5.4 Implement `generate_trade_rationales()` function explaining mutual benefits
  - [x] 5.5 Create `weekly_trades.py` main script with CLI argument parsing
  - [x] 5.6 Add CLI arguments: --values (path), --league (ID), --out (output path)
  - [x] 5.7 Implement complete pipeline orchestration in main script
  - [x] 5.8 Add plain text output format: ASCII only, one decimal precision, structured sections
  - [x] 5.9 Write integration tests for complete pipeline execution
  - [x] 5.10 Test CLI interface with sample data and verify output format
