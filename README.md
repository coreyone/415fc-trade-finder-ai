# Win-Win Trade Suggestions — Sleeper + FantasyCalc

Automated fantasy football trade generator that creates fair, mutually beneficial trades for a 12-team Sleeper league using FantasyCalc player values.

## Overview

This system analyzes each team's positional strengths and weaknesses by comparing starter values to the league median, then generates 6 weekly trades that benefit all parties involved.

## Features

- **Fair Trade Generation**: Uses FantasyCalc values with ≤12% value delta constraint
- **Complete League Coverage**: 6 trades involving all 12 teams weekly
- **Positional Analysis**: Identifies needs vs surplus by position (QB, RB, WR, TE, FLEX)
- **Plain Text Output**: Copy-paste ready format for league communications
- **Automated Workflow**: Single command execution for weekly trade suggestions

## Setup

### Prerequisites

- Python 3.10+
- Active Sleeper league (configured for league ID: 1240782642371104768)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/coreyone/415fc-trade-finder-ai.git
cd 415fc-trade-finder-ai
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
python weekly_trades.py --values path/to/values.csv --league 1240782642371104768 --out output.txt
```

### Parameters

- `--values`: Path to FantasyCalc values CSV file
- `--league`: Sleeper league ID (default: configured in config.py)
- `--out`: Output file path for trade recommendations

### Example Output

```
LEAGUE STARTER VS MEDIAN SNAPSHOT
team=TeamA, qb_delta=+2.1, rb_delta=-5.3, wr_delta=+8.2, te_delta=-1.0, flex_delta=+1.5, total_delta=+5.5

RECOMMENDED TRADES (6 TOTAL)
1) TeamA sends: Player1 (RB), Player2 (WR) ; receives: Player3 (RB), Player4 (WR) ; fairness_delta_pct=8.2% ; teamA_starter_gain=4.1 ; teamB_starter_gain=3.8

RATIONALES
1) TeamA-TeamB: TeamA addresses RB need, trades from WR surplus. TeamB addresses WR need, trades from RB surplus.
```

## Configuration

Edit `config.py` to modify:
- League ID
- API endpoints
- Lineup configuration (currently 1QB/2RB/2WR/1TE/1FLEX)
- Fairness thresholds
- Output formatting options

## Testing

Run all tests:
```bash
python -m pytest
```

Run specific test file:
```bash
python -m pytest data_fetcher.test.py
```

## Project Structure

```
├── weekly_trades.py       # Main CLI script
├── data_fetcher.py        # API integration (FantasyCalc, Sleeper)
├── trade_analyzer.py      # Core analysis engine
├── output_formatter.py    # Plain text output generation
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
└── tests/               # Unit tests
```

## API Dependencies

- **FantasyCalc API**: `https://api.fantasycalc.com/values/current`
- **Sleeper API**: `https://api.sleeper.app/v1`

## Technical Details

- **Lineup Format**: Standard redraft (1QB/2RB/2WR/1TE/1FLEX)
- **Matching Algorithm**: NetworkX maximum-weight perfect matching
- **Fairness Constraint**: ≤12% value difference between traded assets
- **Output Format**: Plain ASCII text, one decimal precision

## Troubleshooting

### Common Issues

1. **API Timeouts**: Check internet connection and API availability
2. **Player Matching Errors**: Verify sleeper_id consistency between data sources
3. **No Valid Trades**: Adjust fairness threshold or minimum starter gains in config.py

### Debug Mode

Add `--debug` flag for verbose logging:
```bash
python weekly_trades.py --debug --values data.csv --out debug_output.txt
```

## Contributing

This is a personal project for a single league. For modifications:

1. Fork the repository
2. Make changes for your league configuration
3. Test with your league data
4. Document any configuration changes needed

## License

Personal use project - modify as needed for your fantasy league.
