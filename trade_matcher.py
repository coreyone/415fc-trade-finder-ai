"""Trade matching module for finding optimal trade combinations using graph algorithms."""

import networkx as nx
import pandas as pd
from typing import Dict, List, Tuple, Optional
from itertools import combinations
from config import MAX_TRADES_PER_WEEK, TOTAL_TEAMS, FAIRNESS_THRESHOLD


def build_trade_graph(valid_trades: List[Dict]) -> nx.Graph:
    """
    Build weighted graph from candidate trades for perfect matching.
    
    Args:
        valid_trades: List of validated trade dictionaries with scores
        
    Returns:
        NetworkX graph where nodes are teams and edges are trades
    """
    # Create undirected graph
    G = nx.Graph()
    
    # Add all team nodes
    teams = set()
    for trade in valid_trades:
        teams.add(trade['team_a'])
        teams.add(trade['team_b'])
    
    G.add_nodes_from(teams)
    
    # Add edges for each trade (weighted by trade score)
    for i, trade in enumerate(valid_trades):
        team_a = trade['team_a']
        team_b = trade['team_b']
        weight = trade.get('trade_score', 0.0)
        
        # Add edge with trade metadata
        G.add_edge(team_a, team_b, 
                  weight=weight,
                  trade_id=i,
                  trade_data=trade)
    
    return G


def find_perfect_matching(G: nx.Graph, target_teams: int = TOTAL_TEAMS) -> Optional[List[Dict]]:
    """
    Find maximum-weight perfect matching to select exactly 6 disjoint trades.
    
    Args:
        G: NetworkX graph with teams as nodes and trades as edges
        target_teams: Number of teams that must be covered (default: 12)
        
    Returns:
        List of selected trade dictionaries, or None if no perfect matching exists
    """
    try:
        # Check if perfect matching is possible
        if len(G.nodes()) != target_teams:
            print(f"Warning: Graph has {len(G.nodes())} nodes, expected {target_teams}")
            return None
        
        if len(G.nodes()) % 2 != 0:
            print("Error: Cannot create perfect matching with odd number of teams")
            return None
        
        # Find maximum weight perfect matching
        matching = nx.algorithms.matching.max_weight_matching(G, maxcardinality=True)
        
        if len(matching) != target_teams // 2:
            print(f"Warning: Matching found {len(matching)} pairs, expected {target_teams // 2}")
            return None
        
        # Extract trades from matching
        selected_trades = []
        total_weight = 0.0
        
        for team_a, team_b in matching:
            edge_data = G[team_a][team_b]
            trade_data = edge_data['trade_data']
            selected_trades.append(trade_data)
            total_weight += edge_data['weight']
        
        print(f"Perfect matching found: {len(selected_trades)} trades, total weight: {total_weight:.1f}")
        return selected_trades
        
    except Exception as e:
        print(f"Error finding perfect matching: {e}")
        return None


def relax_constraints_and_retry(valid_trades: List[Dict], team_rosters: Dict, 
                               player_values: pd.DataFrame) -> Optional[List[Dict]]:
    """
    Progressively relax constraints if perfect matching fails.
    
    Args:
        valid_trades: List of validated trades
        team_rosters: Dictionary of team rosters
        player_values: DataFrame with player values
        
    Returns:
        List of selected trades after constraint relaxation, or None if still impossible
    """
    print("Perfect matching failed, attempting constraint relaxation...")
    
    # Strategy 1: Widen fairness band to 15%
    relaxed_trades = _widen_fairness_threshold(valid_trades, 0.15)
    print(f"Fairness relaxation: {len(relaxed_trades)} trades within 15.0% threshold")
    if relaxed_trades:
        G = build_trade_graph(relaxed_trades)
        result = find_perfect_matching(G)
        if result:
            print("Success with widened fairness threshold (15%)")
            return result
    
    # Strategy 2: Widen fairness even more to 20%
    relaxed_trades = _widen_fairness_threshold(valid_trades, 0.20)
    print(f"Fairness relaxation: {len(relaxed_trades)} trades within 20.0% threshold")
    if relaxed_trades:
        G = build_trade_graph(relaxed_trades)
        result = find_perfect_matching(G)
        if result:
            print("Success with widened fairness threshold (20%)")
            return result
    
    # Strategy 3: Lower minimum starter gain threshold significantly
    relaxed_trades = _lower_starter_gain_threshold(valid_trades, 1.0)
    print(f"Starter gain relaxation: {len(relaxed_trades)} trades with ≥1.0 gain")
    if relaxed_trades:
        G = build_trade_graph(relaxed_trades)
        result = find_perfect_matching(G)
        if result:
            print("Success with lowered starter gain threshold (1.0)")
            return result
    
    # Strategy 4: Allow some 2-for-1 trades
    relaxed_trades = _allow_uneven_trades(valid_trades, team_rosters, player_values)
    if relaxed_trades:
        G = build_trade_graph(relaxed_trades)
        result = find_perfect_matching(G)
        if result:
            print("Success with 2-for-1 trades allowed")
            return result
    
    # Strategy 5: Find best partial matching only as last resort
    partial_result = _find_best_partial_matching(valid_trades)
    if partial_result:
        print(f"Partial matching found: {len(partial_result)} trades")
        print(f"Warning: Found {len(partial_result)} trades, expected 6")
        print(f"Warning: Covering {len(partial_result) * 2} teams, expected 12")
        return partial_result
    
    print("No valid matching found even with relaxed constraints")
    return None


def _widen_fairness_threshold(trades: List[Dict], new_threshold: float) -> List[Dict]:
    """Relax fairness constraint to allow wider value differences."""
    relaxed_trades = []
    
    for trade in trades:
        value_delta_pct = trade.get('value_delta_pct', 0.0)
        if value_delta_pct <= (new_threshold * 100):
            relaxed_trades.append(trade)
    
    print(f"Fairness relaxation: {len(relaxed_trades)} trades within {new_threshold*100}% threshold")
    return relaxed_trades


def _allow_uneven_trades(trades: List[Dict], team_rosters: Dict, player_values: pd.DataFrame) -> List[Dict]:
    """Generate additional 2-for-1 trade options."""
    # This is a placeholder for generating 2-for-1 trades
    # In practice, you'd implement logic to create uneven trades
    print("2-for-1 trade generation not fully implemented - using existing trades")
    return trades


def _lower_starter_gain_threshold(trades: List[Dict], new_threshold: float) -> List[Dict]:
    """Lower the minimum starter gain requirement."""
    relaxed_trades = []
    
    for trade in trades:
        team_a_gain = trade.get('team_a_gain', 0.0)
        team_b_gain = trade.get('team_b_gain', 0.0)
        
        if team_a_gain >= new_threshold and team_b_gain >= new_threshold:
            relaxed_trades.append(trade)
    
    print(f"Starter gain relaxation: {len(relaxed_trades)} trades with ≥{new_threshold} gain")
    return relaxed_trades


def _find_best_partial_matching(trades: List[Dict]) -> Optional[List[Dict]]:
    """Find the best partial matching when perfect matching is impossible."""
    if not trades:
        return None
    
    # Build graph from all trades
    G = build_trade_graph(trades)
    
    # Find maximum matching (not necessarily perfect)
    matching = nx.algorithms.matching.max_weight_matching(G, maxcardinality=False)
    
    if not matching:
        return None
    
    # Extract trades from partial matching
    selected_trades = []
    for team_a, team_b in matching:
        edge_data = G[team_a][team_b]
        trade_data = edge_data['trade_data']
        selected_trades.append(trade_data)
    
    return selected_trades


def validate_matching_constraints(selected_trades: List[Dict]) -> bool:
    """
    Validate that the selected trades meet matching constraints.
    
    Args:
        selected_trades: List of selected trade dictionaries
        
    Returns:
        True if constraints are met, False otherwise
    """
    if not selected_trades:
        return False
    
    # Check that no team appears twice
    teams_involved = set()
    for trade in selected_trades:
        team_a = trade['team_a']
        team_b = trade['team_b']
        
        if team_a in teams_involved or team_b in teams_involved:
            print(f"Constraint violation: Team appears in multiple trades")
            return False
        
        teams_involved.add(team_a)
        teams_involved.add(team_b)
    
    # Check target number of trades
    expected_trades = MAX_TRADES_PER_WEEK
    if len(selected_trades) != expected_trades:
        print(f"Warning: Found {len(selected_trades)} trades, expected {expected_trades}")
        # This is a warning, not a failure
    
    # Check team coverage
    expected_teams = TOTAL_TEAMS
    if len(teams_involved) != expected_teams:
        print(f"Warning: Covering {len(teams_involved)} teams, expected {expected_teams}")
        # This is a warning, not a failure
    
    return True


def select_optimal_trades(valid_trades: List[Dict], team_rosters: Dict, 
                         player_values: pd.DataFrame) -> List[Dict]:
    """
    Select optimal set of trades using perfect matching algorithm.
    
    Args:
        valid_trades: List of validated trade dictionaries
        team_rosters: Dictionary of team rosters
        player_values: DataFrame with player values
        
    Returns:
        List of selected optimal trades
    """
    if not valid_trades:
        print("No valid trades available for matching")
        return []
    
    print(f"Starting trade selection from {len(valid_trades)} candidate trades")
    
    # Step 1: Try perfect matching with current constraints
    G = build_trade_graph(valid_trades)
    selected_trades = find_perfect_matching(G)
    
    # Step 2: If perfect matching fails, relax constraints
    if selected_trades is None:
        selected_trades = relax_constraints_and_retry(valid_trades, team_rosters, player_values)
    
    # Step 3: Validate results
    if selected_trades:
        if validate_matching_constraints(selected_trades):
            print(f"Successfully selected {len(selected_trades)} optimal trades")
            return selected_trades
        else:
            print("Selected trades failed validation")
            return []
    
    print("No valid trade matching found")
    return []
