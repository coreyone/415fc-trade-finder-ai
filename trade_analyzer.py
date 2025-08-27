"""Trade analysis engine for calculating needs, surplus, and generating trades."""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from config import LINEUP_CONFIG, FAIRNESS_THRESHOLD, MIN_STARTER_GAIN


def calculate_starter_values(team_roster: Dict, player_values: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate starter values for a team using 1QB/2RB/2WR/1TE/1FLEX lineup.
    
    Args:
        team_roster: Dictionary with team's player_ids and other roster info
        player_values: DataFrame with player values and positions
        
    Returns:
        Dictionary with starter values by position and total
    """
    player_ids = team_roster.get('players', [])
    if not player_ids:
        return {pos: 0.0 for pos in ['QB', 'RB', 'WR', 'TE', 'FLEX', 'TOTAL']}
    
    # Filter player values to only include team's players
    team_players = player_values[player_values['sleeper_id'].isin(player_ids)].copy()
    
    if team_players.empty:
        return {pos: 0.0 for pos in ['QB', 'RB', 'WR', 'TE', 'FLEX', 'TOTAL']}
    
    # Sort players by value within each position
    team_players = team_players.sort_values(['position', 'value'], ascending=[True, False])
    
    starter_values = {'QB': 0.0, 'RB': 0.0, 'WR': 0.0, 'TE': 0.0, 'FLEX': 0.0}
    used_players = []
    flex_eligible = []
    
    # Calculate starter values by position
    for position in ['QB', 'RB', 'WR', 'TE']:
        pos_players = team_players[team_players['position'] == position].copy()
        required_starters = LINEUP_CONFIG[position]
        
        # Take top players for starting positions
        starters = pos_players.head(required_starters)
        starter_values[position] = starters['value'].sum()
        used_players.extend(starters['sleeper_id'].tolist())
        
        # Remaining players are eligible for FLEX (except QB)
        if position != 'QB':
            remaining = pos_players.iloc[required_starters:]
            flex_eligible.extend(remaining.to_dict('records'))
    
    # Calculate FLEX value (best remaining RB/WR/TE)
    if flex_eligible:
        flex_eligible = sorted(flex_eligible, key=lambda x: x['value'], reverse=True)
        best_flex = flex_eligible[0]
        starter_values['FLEX'] = best_flex['value']
        used_players.append(best_flex['sleeper_id'])
    
    # Calculate total starter value
    starter_values['TOTAL'] = sum(starter_values.values())
    
    return starter_values


def compute_positional_deltas(all_team_starters: Dict[str, Dict], league_medians: Dict[str, float] = None) -> Dict[str, Dict]:
    """
    Compare each team's starter values vs league median by position.
    
    Args:
        all_team_starters: Dictionary of team_name -> {position: value} mappings
        league_medians: Dictionary of position -> median_value mappings (optional, will compute if None)
        
    Returns:
        Dictionary of team_name -> {position: delta} mappings
    """
    if not all_team_starters:
        return {}
    
    # Calculate league medians if not provided
    if league_medians is None:
        league_medians = _calculate_league_medians(all_team_starters)
    
    team_deltas = {}
    
    for team_name, starter_values in all_team_starters.items():
        team_deltas[team_name] = {}
        
        for position in ['QB', 'RB', 'WR', 'TE', 'FLEX', 'TOTAL']:
            team_value = starter_values.get(position, 0.0)
            median_value = league_medians.get(position, 0.0)
            delta = team_value - median_value
            team_deltas[team_name][position] = round(delta, 1)
    
    return team_deltas


def _calculate_league_medians(all_team_starters: Dict[str, Dict]) -> Dict[str, float]:
    """
    Calculate league median values by position.
    
    Args:
        all_team_starters: Dictionary of team_name -> {position: value} mappings
        
    Returns:
        Dictionary of position -> median_value mappings
    """
    position_values = {pos: [] for pos in ['QB', 'RB', 'WR', 'TE', 'FLEX', 'TOTAL']}
    
    # Collect all values by position
    for team_starters in all_team_starters.values():
        for position in position_values.keys():
            value = team_starters.get(position, 0.0)
            position_values[position].append(value)
    
    # Calculate medians
    league_medians = {}
    for position, values in position_values.items():
        if values:
            league_medians[position] = round(np.median(values), 1)
        else:
            league_medians[position] = 0.0
    
    return league_medians


def identify_needs_surplus(team_deltas: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Identify needs (negative deltas) and surplus (positive deltas) for each team.
    
    Args:
        team_deltas: Dictionary of team_name -> {position: delta} mappings
        
    Returns:
        Dictionary of team_name -> {'needs': [positions], 'surplus': [positions]}
    """
    team_needs_surplus = {}
    
    for team_name, deltas in team_deltas.items():
        needs = []
        surplus = []
        
        # Only consider tradeable positions (exclude TOTAL)
        tradeable_positions = ['QB', 'RB', 'WR', 'TE', 'FLEX']
        
        for position in tradeable_positions:
            delta = deltas.get(position, 0.0)
            
            # Negative delta indicates need, positive indicates surplus
            if delta < -2.0:  # Threshold for significant need
                needs.append(position)
            elif delta > 2.0:  # Threshold for significant surplus
                surplus.append(position)
        
        # Sort by magnitude of delta (most significant first)
        needs.sort(key=lambda pos: deltas.get(pos, 0.0))  # Most negative first
        surplus.sort(key=lambda pos: deltas.get(pos, 0.0), reverse=True)  # Most positive first
        
        team_needs_surplus[team_name] = {
            'needs': needs,
            'surplus': surplus,
            'deltas': deltas  # Include original deltas for reference
        }
    
    return team_needs_surplus


def generate_candidate_trades(team_needs_surplus: Dict, player_values: pd.DataFrame, enriched_data: Dict = None) -> List[Dict]:
    """
    Generate candidate trades between teams with complementary needs/surplus.
    
    Args:
        team_needs_surplus: Dictionary of team needs and surplus
        player_values: DataFrame with player values
        enriched_data: Dictionary of team_name -> team_data with actual rosters
        
    Returns:
        List of candidate trade dictionaries
    """
    candidate_trades = []
    team_names = list(team_needs_surplus.keys())
    
    # Create player lookup for quick access
    player_lookup = player_values.set_index('sleeper_id').to_dict('index')
    
    for i, team_a in enumerate(team_names):
        for team_b in team_names[i+1:]:  # Avoid duplicate pairs
            team_a_data = team_needs_surplus[team_a]
            team_b_data = team_needs_surplus[team_b]
            
            # Check for complementary needs/surplus
            trades = _find_complementary_trades(
                team_a, team_a_data,
                team_b, team_b_data,
                player_values, player_lookup, enriched_data
            )
            
            candidate_trades.extend(trades)
    
    return candidate_trades


def _find_complementary_trades(team_a: str, team_a_data: Dict, team_b: str, team_b_data: Dict,
                              player_values: pd.DataFrame, player_lookup: Dict, enriched_data: Dict = None) -> List[Dict]:
    """
    Find trades between two teams with complementary needs.
    
    Args:
        team_a: Team A name
        team_a_data: Team A needs/surplus data
        team_b: Team B name  
        team_b_data: Team B needs/surplus data
        player_values: DataFrame with player values
        player_lookup: Dictionary for quick player lookup
        
    Returns:
        List of trade dictionaries between these two teams
    """
    trades = []
    
    # Find positions where Team A has surplus and Team B has need
    a_surplus = set(team_a_data['surplus'])
    b_needs = set(team_b_data['needs'])
    a_to_b_positions = a_surplus.intersection(b_needs)
    
    # Find positions where Team B has surplus and Team A has need
    b_surplus = set(team_b_data['surplus'])
    a_needs = set(team_a_data['needs'])
    b_to_a_positions = b_surplus.intersection(a_needs)
    
    # Only proceed if there are complementary positions BOTH ways (perfect two-way match)
    if not (a_to_b_positions and b_to_a_positions):
        return trades
    
    # Get players for each team by position
    team_a_players = _get_team_players_by_position(team_a, player_values, enriched_data)
    team_b_players = _get_team_players_by_position(team_b, player_values, enriched_data)
    
    # Generate 1-for-1 trades
    trades.extend(_generate_1_for_1_trades(
        team_a, team_a_players, a_to_b_positions,
        team_b, team_b_players, b_to_a_positions,
        player_lookup
    ))
    
    # Generate 2-for-2 trades (prefer these)
    trades.extend(_generate_2_for_2_trades(
        team_a, team_a_players, a_to_b_positions,
        team_b, team_b_players, b_to_a_positions,
        player_lookup
    ))
    
    return trades


def _get_team_players_by_position(team_name: str, player_values: pd.DataFrame, enriched_data: Dict = None) -> Dict[str, List]:
    """Get team's players organized by position."""
    team_players = {}
    
    if enriched_data and team_name in enriched_data:
        # Use actual team roster from enriched data
        team_roster = enriched_data[team_name]['players']
        
        # Organize players by position
        for position in ['QB', 'RB', 'WR', 'TE']:
            pos_players = [p for p in team_roster if p.get('position') == position]
            # Sort by value descending
            pos_players = sorted(pos_players, key=lambda x: x.get('value', 0), reverse=True)
            team_players[position] = pos_players
    else:
        # Fallback: return empty lists for each position
        for position in ['QB', 'RB', 'WR', 'TE']:
            team_players[position] = []
    
    return team_players


def _generate_1_for_1_trades(team_a: str, team_a_players: Dict, a_positions: set,
                            team_b: str, team_b_players: Dict, b_positions: set,
                            player_lookup: Dict) -> List[Dict]:
    """Generate 1-for-1 trade candidates."""
    trades = []
    
    for a_pos in a_positions:
        for b_pos in b_positions:
            a_players = team_a_players.get(a_pos, [])[:3]  # Top 3 players only
            b_players = team_b_players.get(b_pos, [])[:3]  # Top 3 players only
            
            for a_player in a_players:
                for b_player in b_players:
                    trade = {
                        'type': '1-for-1',
                        'team_a': team_a,
                        'team_b': team_b,
                        'team_a_sends': [a_player],
                        'team_b_sends': [b_player],
                        'positions_addressed': {
                            team_a: [b_pos],  # Team A gets help at b_pos
                            team_b: [a_pos]   # Team B gets help at a_pos
                        }
                    }
                    trades.append(trade)
    
    return trades


def _generate_2_for_2_trades(team_a: str, team_a_players: Dict, a_positions: set,
                            team_b: str, team_b_players: Dict, b_positions: set,
                            player_lookup: Dict) -> List[Dict]:
    """Generate 2-for-2 trade candidates (preferred)."""
    trades = []
    
    # Generate trades where each team sends 2 players and receives 2
    a_positions_list = list(a_positions)
    b_positions_list = list(b_positions)
    
    # Try combinations of positions
    for i, a_pos1 in enumerate(a_positions_list):
        for a_pos2 in a_positions_list[i:]:  # Allow same position twice
            for j, b_pos1 in enumerate(b_positions_list):
                for b_pos2 in b_positions_list[j:]:  # Allow same position twice
                    
                    # Get top 2 players from each position
                    a_players1 = team_a_players.get(a_pos1, [])[:2]
                    a_players2 = team_a_players.get(a_pos2, [])[:2] if a_pos2 != a_pos1 else team_a_players.get(a_pos2, [])[1:3]
                    
                    b_players1 = team_b_players.get(b_pos1, [])[:2]
                    b_players2 = team_b_players.get(b_pos2, [])[:2] if b_pos2 != b_pos1 else team_b_players.get(b_pos2, [])[1:3]
                    
                    # Generate specific 2-for-2 combinations
                    for a_p1 in a_players1:
                        for a_p2 in a_players2:
                            if a_p1['sleeper_id'] == a_p2['sleeper_id']:
                                continue  # Skip same player twice
                            
                            for b_p1 in b_players1:
                                for b_p2 in b_players2:
                                    if b_p1['sleeper_id'] == b_p2['sleeper_id']:
                                        continue  # Skip same player twice
                                    
                                    trade = {
                                        'type': '2-for-2',
                                        'team_a': team_a,
                                        'team_b': team_b,
                                        'team_a_sends': [a_p1, a_p2],
                                        'team_b_sends': [b_p1, b_p2],
                                        'positions_addressed': {
                                            team_a: [b_pos1, b_pos2],
                                            team_b: [a_pos1, a_pos2]
                                        }
                                    }
                                    trades.append(trade)
    
    return trades


def score_trade(trade: Dict, team_a_gains: float, team_b_gains: float, value_delta_pct: float) -> float:
    """
    Score a trade based on mutual gains and fairness.
    
    Args:
        trade: Trade dictionary
        team_a_gains: Starter value improvement for team A
        team_b_gains: Starter value improvement for team B
        value_delta_pct: Percentage value difference
        
    Returns:
        Trade score (higher is better)
    """
    # Base score: sum of mutual gains
    base_score = team_a_gains + team_b_gains
    
    # Fairness penalty: higher penalty for larger value differences
    fairness_penalty = 0.0
    abs_delta_pct = abs(value_delta_pct)
    if abs_delta_pct > FAIRNESS_THRESHOLD:
        # Heavy penalty for trades outside fairness threshold
        fairness_penalty = (abs_delta_pct - FAIRNESS_THRESHOLD) * 50.0
    else:
        # Smaller penalty for trades within threshold but not perfectly balanced
        fairness_penalty = abs_delta_pct * 10.0
    
    # Risk flags penalty
    risk_penalty = 0.0
    
    # Penalty for very low starter gains (not meaningful enough)
    if team_a_gains < MIN_STARTER_GAIN or team_b_gains < MIN_STARTER_GAIN:
        risk_penalty += 20.0
    
    # Penalty for trades involving too many players (complexity)
    total_players = len(trade.get('team_a_sends', [])) + len(trade.get('team_b_sends', []))
    if total_players > 4:  # 2-for-2 is max preferred
        risk_penalty += (total_players - 4) * 5.0
    
    # Bonus for 2-for-2 trades (preferred format)
    format_bonus = 0.0
    if trade.get('type') == '2-for-2':
        format_bonus = 5.0
    
    # Calculate final score
    final_score = base_score + format_bonus - fairness_penalty - risk_penalty
    
    return max(0.0, final_score)  # Ensure non-negative score


def check_fairness_constraint(trade: Dict, player_values: pd.DataFrame) -> Tuple[bool, float]:
    """
    Check if trade meets fairness constraint (≤12% value delta).
    
    Args:
        trade: Trade dictionary
        player_values: DataFrame with player values
        
    Returns:
        Tuple of (is_fair: bool, value_delta_pct: float)
    """
    # Calculate total value for each side of trade
    team_a_value = _calculate_trade_side_value(trade.get('team_a_sends', []), player_values)
    team_b_value = _calculate_trade_side_value(trade.get('team_b_sends', []), player_values)
    
    if team_a_value == 0 or team_b_value == 0:
        return False, 100.0  # Invalid trade if either side has no value
    
    # Calculate percentage difference
    # Use the higher value as the denominator to get more conservative estimates
    higher_value = max(team_a_value, team_b_value)
    value_difference = abs(team_a_value - team_b_value)
    value_delta_pct = (value_difference / higher_value) * 100.0
    
    # Check if within fairness threshold
    is_fair = value_delta_pct <= (FAIRNESS_THRESHOLD * 100)
    
    return is_fair, round(value_delta_pct, 1)


def _calculate_trade_side_value(players: List[Dict], player_values: pd.DataFrame) -> float:
    """
    Calculate total value for one side of a trade.
    
    Args:
        players: List of player dictionaries
        player_values: DataFrame with player values
        
    Returns:
        Total value for this side of the trade
    """
    if not players:
        return 0.0
    
    total_value = 0.0
    
    for player in players:
        sleeper_id = player.get('sleeper_id')
        if sleeper_id:
            # Look up player value
            player_row = player_values[player_values['sleeper_id'] == sleeper_id]
            if not player_row.empty:
                value = player_row.iloc[0]['value']
                total_value += float(value)
            else:
                # Fallback: use value from player dict if available
                total_value += float(player.get('value', 0))
        else:
            # Fallback: use value from player dict
            total_value += float(player.get('value', 0))
    
    return total_value


def calculate_starter_impact(trade: Dict, team_rosters: Dict, player_values: pd.DataFrame) -> Tuple[float, float]:
    """
    Calculate the starter lineup impact for both teams in a trade.
    
    Args:
        trade: Trade dictionary
        team_rosters: Dictionary of team_name -> roster_dict mappings
        player_values: DataFrame with player values
        
    Returns:
        Tuple of (team_a_gain, team_b_gain) in starter value points
    """
    team_a = trade['team_a']
    team_b = trade['team_b']
    
    # Get current rosters
    team_a_roster = team_rosters.get(team_a, {})
    team_b_roster = team_rosters.get(team_b, {})
    
    if not team_a_roster or not team_b_roster:
        return 0.0, 0.0
    
    # Calculate current starter values
    team_a_current = calculate_starter_values(team_a_roster, player_values)
    team_b_current = calculate_starter_values(team_b_roster, player_values)
    
    # Simulate the trade by updating rosters
    team_a_new_roster = _simulate_trade_roster(
        team_a_roster.copy(),
        removes=trade.get('team_a_sends', []),
        adds=trade.get('team_b_sends', [])
    )
    
    team_b_new_roster = _simulate_trade_roster(
        team_b_roster.copy(),
        removes=trade.get('team_b_sends', []),
        adds=trade.get('team_a_sends', [])
    )
    
    # Calculate new starter values
    team_a_new = calculate_starter_values(team_a_new_roster, player_values)
    team_b_new = calculate_starter_values(team_b_new_roster, player_values)
    
    # Calculate gains
    team_a_gain = team_a_new['TOTAL'] - team_a_current['TOTAL']
    team_b_gain = team_b_new['TOTAL'] - team_b_current['TOTAL']
    
    return round(team_a_gain, 1), round(team_b_gain, 1)


def _simulate_trade_roster(roster: Dict, removes: List[Dict], adds: List[Dict]) -> Dict:
    """
    Simulate a trade by updating a team's roster.
    
    Args:
        roster: Team roster dictionary
        removes: Players to remove from roster
        adds: Players to add to roster
        
    Returns:
        Updated roster dictionary
    """
    updated_roster = roster.copy()
    player_ids = updated_roster.get('players', []).copy()
    
    # Remove traded away players
    for player in removes:
        sleeper_id = player.get('sleeper_id')
        if sleeper_id and sleeper_id in player_ids:
            player_ids.remove(sleeper_id)
    
    # Add received players
    for player in adds:
        sleeper_id = player.get('sleeper_id')
        if sleeper_id:
            player_ids.append(sleeper_id)
    
    updated_roster['players'] = player_ids
    return updated_roster


def check_meaningful_impact(trade: Dict, team_rosters: Dict, player_values: pd.DataFrame) -> bool:
    """
    Check if trade has meaningful impact (at least one projected starter per side).
    
    Args:
        trade: Trade dictionary
        team_rosters: Dictionary of team_name -> roster_dict mappings
        player_values: DataFrame with player values
        
    Returns:
        True if trade has meaningful impact, False otherwise
    """
    team_a_gain, team_b_gain = calculate_starter_impact(trade, team_rosters, player_values)
    
    # Both teams must gain at least minimum starter improvement
    has_meaningful_impact = (
        team_a_gain >= MIN_STARTER_GAIN and 
        team_b_gain >= MIN_STARTER_GAIN
    )
    
    return has_meaningful_impact


def check_roster_viability(trade: Dict, team_rosters: Dict) -> bool:
    """
    Check if trade leaves both teams with minimum required starters at each position.
    
    Args:
        trade: Trade dictionary
        team_rosters: Dictionary of team_name -> roster_dict mappings
        
    Returns:
        True if both teams retain minimum starters, False otherwise
    """
    from config import LINEUP_CONFIG
    
    # Minimum required starters per position (1QB, 2RB, 2WR, 1TE)
    min_starters = {
        'QB': LINEUP_CONFIG['QB'],
        'RB': LINEUP_CONFIG['RB'], 
        'WR': LINEUP_CONFIG['WR'],
        'TE': LINEUP_CONFIG['TE']
    }
    
    team_a = trade['team_a']
    team_b = trade['team_b']
    
    # Check both teams
    for team_name, sends_players, receives_players in [
        (team_a, trade['team_a_sends'], trade['team_b_sends']),
        (team_b, trade['team_b_sends'], trade['team_a_sends'])
    ]:
        if team_name not in team_rosters:
            continue
            
        # Get current roster
        current_roster = team_rosters[team_name]['players']
        
        # Count players by position after trade
        position_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
        
        for player in current_roster:
            pos = player.get('position')
            if pos in position_counts:
                position_counts[pos] += 1
        
        # Subtract players being sent away
        for player in sends_players:
            pos = player.get('position')
            if pos in position_counts:
                position_counts[pos] -= 1
        
        # Add players being received
        for player in receives_players:
            pos = player.get('position')
            if pos in position_counts:
                position_counts[pos] += 1
        
        # Check if team has minimum required starters at each position
        for pos, min_required in min_starters.items():
            if position_counts[pos] < min_required:
                return False
    
    return True


def filter_valid_trades(candidate_trades: List[Dict], team_rosters: Dict, player_values: pd.DataFrame) -> List[Dict]:
    """
    Filter candidate trades to only include valid, fair, and meaningful trades.
    
    Args:
        candidate_trades: List of candidate trade dictionaries
        team_rosters: Dictionary of team_name -> roster_dict mappings
        player_values: DataFrame with player values
        
    Returns:
        List of validated trade dictionaries with scores
    """
    valid_trades = []
    
    for trade in candidate_trades:
        # Check fairness constraint
        is_fair, value_delta_pct = check_fairness_constraint(trade, player_values)
        if not is_fair:
            continue
        
        # Check roster viability (teams retain minimum starters)
        if not check_roster_viability(trade, team_rosters):
            continue
        
        # Check meaningful impact
        if not check_meaningful_impact(trade, team_rosters, player_values):
            continue
        
        # Calculate starter impact for scoring
        team_a_gain, team_b_gain = calculate_starter_impact(trade, team_rosters, player_values)
        
        # Calculate trade score
        trade_score = score_trade(trade, team_a_gain, team_b_gain, value_delta_pct)
        
        # Add metadata to trade
        trade_with_meta = trade.copy()
        trade_with_meta.update({
            'team_a_gain': team_a_gain,
            'team_b_gain': team_b_gain,
            'value_delta_pct': value_delta_pct,
            'trade_score': trade_score,
            'is_fair': is_fair
        })
        
        valid_trades.append(trade_with_meta)
    
    # Sort by trade score (descending)
    valid_trades.sort(key=lambda t: t['trade_score'], reverse=True)
    
    return valid_trades
