# PRD: Win-Win Trade Suggestions — Sleeper + FantasyCalc

## Introduction/Overview

This feature will create an automated system that generates fair, mutually beneficial fantasy football trades for a 12-team Sleeper league. The system uses FantasyCalc redraft player values combined with league roster data to identify each team's positional strengths and weaknesses, then proposes trades that address complementary needs while maintaining fairness within a 10-12% value delta.

**Problem Statement:** Fantasy football managers struggle to identify fair trades that benefit both parties, often leading to lopsided proposals or missed opportunities for roster improvement.

**Solution:** An automated weekly trade generator that analyzes positional needs vs. surplus across all teams and creates 6 balanced trades involving all 12 teams.

## Goals

1. **Generate 6 fair trades weekly** that involve all 12 teams (one trade per team)
2. **Maintain trade fairness** with value differences ≤ 10-12%
3. **Improve both teams' starting lineups** in each proposed trade
4. **Provide clear rationales** for why each trade benefits both parties
5. **Automate the entire process** with minimal manual intervention
6. **Output ready-to-share results** in plain text format

## User Stories

**As a league commissioner, I want to:**
- Generate weekly trade suggestions automatically so I can facilitate league activity
- See fair value assessments for all proposed trades so I can verify equity
- Get plain text output that I can easily copy/paste to league communications

**As a league member, I want to:**
- Receive trade suggestions that actually improve my team so I'm motivated to participate
- Understand why a trade benefits me through clear explanations
- See my team's positional strengths/weaknesses compared to league median

**As a fantasy football enthusiast, I want to:**
- Use current market values (FantasyCalc) rather than outdated rankings
- Have trades consider my actual roster construction and starting lineup needs
- Participate in trades that don't feel one-sided or exploitative

## Functional Requirements

### Data Integration
1. **The system must fetch current FantasyCalc redraft values** via API endpoint `https://api.fantasycalc.com/values/current` with parameters: `isDynasty=false`, `numQbs=1`, `numTeams=12`, `ppr=1`
2. **The system must retrieve Sleeper league rosters** via API endpoint `https://api.sleeper.app/v1/league/{league_id}/rosters`
3. **The system must join player data** using `sleeper_id` as the primary key, with name/position matching as fallback. 
4. **The system must map team owners to display names** using Sleeper users endpoint

### Analysis Engine
5. **The system must calculate starter values** for each team using standard lineup: 1QB, 2RB, 2WR, 1TE, 1FLEX (RB/WR/TE)
6. **The system must compute positional deltas** vs league median for each team (QB, RB, WR, TE, FLEX)
7. **The system must identify needs and surplus** where negative delta = need, positive delta = strength
8. **The system must generate candidate trades** that swap surplus positions for needed positions between teams

### Trade Generation
9. **The system must prefer 2-for-2 trades** with 1-for-1 as fallback option
10. **The system must enforce fairness constraints** with value difference ≤ 12%
11. **The system must require meaningful impact** where at least one projected starter is included per side
12. **The system must use maximum-weight perfect matching** to select exactly 6 disjoint trades covering all 12 teams
13. **The system must relax constraints progressively** if perfect matching fails (widen fairness band, allow 2-for-1, lower starter gain threshold)

### Output Generation
14. **The system must produce a starter vs median snapshot** showing each team's positional deltas
15. **The system must list 6 recommended trades** with fairness percentages and starter gains
16. **The system must provide trade rationales** explaining how each team benefits
17. **The system must format output as plain text** with no markup, tabs, or special formatting
18. **The system must save results to specified file path** for easy sharing

## Technical Approach

### Architecture
- **Single Python script** (`weekly_trades.py`) for simplicity
- **Command-line interface** with arguments for values file, league ID, and output path
- **Minimal dependencies**: pandas, numpy, networkx, requests, python-dateutil

### Data Flow
1. **API Integration**: Fetch FantasyCalc values (JSON) and Sleeper rosters/users
2. **Data Processing**: Join player data, calculate starter values and positional deltas
3. **Trade Generation**: Create candidate trades, score by mutual benefit and fairness
4. **Graph Matching**: Build weighted graph and run maximum-weight perfect matching
5. **Output Formatting**: Generate plain text report with specified format

### Key Algorithms
- **Starter Calculation**: Sort players by value per position, sum top starters + best FLEX
- **Need/Surplus Identification**: Compare team starter values to league median by position
- **Trade Scoring**: `gain_A + gain_B - penalty_fairness - risk_flags`
- **Perfect Matching**: NetworkX maximum-weight matching for 6 disjoint trades

### Configuration
- **League ID**: 1240782642371104768 (hardcoded for personal use)
- **Lineup Format**: 1QB/2RB/2WR/1TE/1FLEX standard redraft
- **Fairness Threshold**: ≤12% value delta
- **Minimum Starter Gain**: ≥3.0 points improvement

## Non-Goals (Out of Scope)

1. **Multiple league support** - designed for single league use
2. **Dynasty league formats** - focused on redraft only
3. **Complex UI/web interface** - command-line tool with text output
4. **Real-time trade tracking** - weekly batch processing only
5. **Historical trade equity analysis** - no long-term tracking
6. **Integration with other platforms** - Sleeper + FantasyCalc only
7. **Manual trade evaluation** - automated suggestions only
8. **Injury/news context** - relies purely on FantasyCalc values
9. **Playoff schedule optimization** - season-long value focus
10. **Custom scoring systems** - PPR format only

## Design Considerations

### Output Format
- **Plain ASCII text only** for universal compatibility
- **Structured sections**: Snapshot, Trades, Rationales, Notes
- **Consistent formatting**: One decimal place for deltas, clear team/player identification
- **Copy-paste ready** for league communications

### User Experience
- **Single command execution** for weekly generation
- **Clear error messages** if API calls fail or constraints can't be met
- **Fallback options** listed if fewer than 6 trades possible
- **Readable rationales** explaining mutual benefits

## Technical Considerations

### API Dependencies
- **FantasyCalc API stability** - monitor for endpoint changes
- **Sleeper API rate limits** - implement appropriate delays if needed
- **Network error handling** - retry logic for failed requests

### Data Quality
- **Player ID matching** - robust fallback to name/position matching
- **Value data freshness** - FantasyCalc updates regularly
- **Roster synchronization** - handle mid-week roster changes

### Performance
- **Candidate generation limits** - restrict to top K bench assets per position (K=3)
- **Graph size management** - 12 teams = 66 possible pairs, manageable
- **Memory usage** - minimal for single league processing

## Open Questions

1. **How should the system handle bye weeks** when calculating starter values?
2. **Should there be position-specific fairness bands** (e.g., stricter for QB trades)?
3. **How to handle players with zero FantasyCalc value** (deep bench, rookies)?
4. **Should the system consider recent trade history** to avoid repeat pairings?
5. **What happens if a team has no clear surplus or need** (balanced roster)?
6. **Should kickers and defense be included** in trade calculations?
7. **How to handle injured players** with outdated values?
8. **Should there be a minimum roster size requirement** after trades?

## Success Metrics

- **Trade acceptance rate** by league members
- **Fairness validation** - all trades within 12% value delta
- **Coverage completeness** - all 12 teams included weekly
- **Processing time** - complete analysis in under 2 minutes
- **Data accuracy** - successful API integration and player matching
- **Output quality** - clear, actionable trade rationales
