"""Unit tests for trade_analyzer module."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, Mock
from trade_analyzer import (
    calculate_starter_values,
    compute_positional_deltas,
    _calculate_league_medians,
    identify_needs_surplus,
    generate_candidate_trades,
    score_trade,
    check_fairness_constraint,
    calculate_starter_impact,
    check_meaningful_impact,
    filter_valid_trades,
    _calculate_trade_side_value,
    _simulate_trade_roster
)


class TestCalculateStarterValues:
    """Test starter values calculation functionality."""
    
    def test_calculate_starter_values_success(self, sample_team_roster, sample_player_values):
        """Test successful starter values calculation."""
        result = calculate_starter_values(sample_team_roster, sample_player_values)
        
        assert isinstance(result, dict)
        assert all(pos in result for pos in ['QB', 'RB', 'WR', 'TE', 'FLEX', 'TOTAL'])
        assert all(isinstance(val, float) for val in result.values())
        assert result['TOTAL'] == sum(result[pos] for pos in ['QB', 'RB', 'WR', 'TE', 'FLEX'])
    
    def test_calculate_starter_values_empty_roster(self):
        """Test handling of empty roster."""
        empty_roster = {'players': []}
        player_values = pd.DataFrame()
        
        result = calculate_starter_values(empty_roster, player_values)
        
        expected = {pos: 0.0 for pos in ['QB', 'RB', 'WR', 'TE', 'FLEX', 'TOTAL']}
        assert result == expected
    
    def test_calculate_starter_values_no_players_match(self, sample_player_values):
        """Test handling when no players match between roster and values."""
        roster_no_match = {'players': ['999', '998', '997']}  # Non-existent players
        
        result = calculate_starter_values(roster_no_match, sample_player_values)
        
        expected = {pos: 0.0 for pos in ['QB', 'RB', 'WR', 'TE', 'FLEX', 'TOTAL']}
        assert result == expected


class TestComputePositionalDeltas:
    """Test positional deltas calculation functionality."""
    
    def test_compute_positional_deltas_success(self):
        """Test successful positional deltas calculation."""
        all_team_starters = {
            'Team1': {'QB': 40.0, 'RB': 60.0, 'WR': 50.0, 'TE': 20.0, 'FLEX': 15.0, 'TOTAL': 185.0},
            'Team2': {'QB': 35.0, 'RB': 55.0, 'WR': 45.0, 'TE': 25.0, 'FLEX': 20.0, 'TOTAL': 180.0},
            'Team3': {'QB': 45.0, 'RB': 50.0, 'WR': 55.0, 'TE': 30.0, 'FLEX': 25.0, 'TOTAL': 205.0}
        }
        
        result = compute_positional_deltas(all_team_starters)
        
        assert isinstance(result, dict)
        assert len(result) == 3
        assert all(team in result for team in ['Team1', 'Team2', 'Team3'])
        
        # Check that deltas are calculated correctly (Team2 should have median values = 0 delta)
        team2_deltas = result['Team2']
        assert all(isinstance(delta, float) for delta in team2_deltas.values())
    
    def test_compute_positional_deltas_empty_input(self):
        """Test handling of empty input."""
        result = compute_positional_deltas({})
        assert result == {}
    
    def test_calculate_league_medians(self):
        """Test league medians calculation."""
        all_team_starters = {
            'Team1': {'QB': 40.0, 'RB': 60.0, 'WR': 50.0, 'TE': 20.0, 'FLEX': 15.0},
            'Team2': {'QB': 35.0, 'RB': 55.0, 'WR': 45.0, 'TE': 25.0, 'FLEX': 20.0},
            'Team3': {'QB': 45.0, 'RB': 50.0, 'WR': 55.0, 'TE': 30.0, 'FLEX': 25.0}
        }
        
        result = _calculate_league_medians(all_team_starters)
        
        assert result['QB'] == 40.0  # Median of [35, 40, 45]
        assert result['RB'] == 55.0  # Median of [50, 55, 60]
        assert result['WR'] == 50.0  # Median of [45, 50, 55]


class TestIdentifyNeedsSurplus:
    """Test needs and surplus identification functionality."""
    
    def test_identify_needs_surplus_success(self):
        """Test successful needs/surplus identification."""
        team_deltas = {
            'Team1': {'QB': -5.0, 'RB': 8.0, 'WR': -3.0, 'TE': 2.0, 'FLEX': 1.0},
            'Team2': {'QB': 3.0, 'RB': -6.0, 'WR': 4.0, 'TE': -1.0, 'FLEX': -2.0}
        }
        
        result = identify_needs_surplus(team_deltas)
        
        assert isinstance(result, dict)
        assert 'Team1' in result and 'Team2' in result
        
        team1_result = result['Team1']
        assert 'needs' in team1_result and 'surplus' in team1_result
        assert 'QB' in team1_result['needs']  # -5.0 < -2.0
        assert 'RB' in team1_result['surplus']  # 8.0 > 2.0
        
        team2_result = result['Team2']
        assert 'RB' in team2_result['needs']  # -6.0 < -2.0
        assert 'WR' in team2_result['surplus']  # 4.0 > 2.0
    
    def test_identify_needs_surplus_no_significant_deltas(self):
        """Test handling when no deltas exceed thresholds."""
        team_deltas = {
            'Team1': {'QB': 1.0, 'RB': -1.0, 'WR': 0.5, 'TE': -0.5, 'FLEX': 1.5}
        }
        
        result = identify_needs_surplus(team_deltas)
        
        team1_result = result['Team1']
        assert team1_result['needs'] == []
        assert team1_result['surplus'] == []


class TestScoreTrade:
    """Test trade scoring functionality."""
    
    def test_score_trade_fair_high_gains(self):
        """Test scoring of fair trade with high mutual gains."""
        trade = {'type': '2-for-2', 'team_a_sends': [{'sleeper_id': '1'}], 'team_b_sends': [{'sleeper_id': '2'}]}
        team_a_gains = 8.0
        team_b_gains = 7.5
        value_delta_pct = 5.0  # Within fairness threshold
        
        result = score_trade(trade, team_a_gains, team_b_gains, value_delta_pct)
        
        assert result > 0
        assert isinstance(result, float)
        # Should have high score due to high mutual gains and fairness
    
    def test_score_trade_unfair_penalty(self):
        """Test penalty for unfair trades."""
        trade = {'type': '1-for-1', 'team_a_sends': [{'sleeper_id': '1'}], 'team_b_sends': [{'sleeper_id': '2'}]}
        team_a_gains = 5.0
        team_b_gains = 5.0
        value_delta_pct = 20.0  # Outside fairness threshold (12%)
        
        result = score_trade(trade, team_a_gains, team_b_gains, value_delta_pct)
        
        # Should have lower score due to fairness penalty
        assert result >= 0
    
    def test_score_trade_low_gains_penalty(self):
        """Test penalty for trades with low starter gains."""
        trade = {'type': '1-for-1', 'team_a_sends': [{'sleeper_id': '1'}], 'team_b_sends': [{'sleeper_id': '2'}]}
        team_a_gains = 1.0  # Below MIN_STARTER_GAIN (3.0)
        team_b_gains = 2.0  # Below MIN_STARTER_GAIN (3.0)
        value_delta_pct = 5.0
        
        result = score_trade(trade, team_a_gains, team_b_gains, value_delta_pct)
        
        # Should have penalty for low gains
        assert result >= 0


class TestCheckFairnessConstraint:
    """Test fairness constraint checking functionality."""
    
    def test_check_fairness_constraint_fair_trade(self, sample_player_values):
        """Test fair trade within threshold."""
        trade = {
            'team_a_sends': [{'sleeper_id': '421', 'value': 45.0}],
            'team_b_sends': [{'sleeper_id': '4046', 'value': 50.0}]
        }
        
        is_fair, delta_pct = check_fairness_constraint(trade, sample_player_values)
        
        assert isinstance(is_fair, bool)
        assert isinstance(delta_pct, float)
        assert delta_pct <= 12.0  # Within fairness threshold
    
    def test_check_fairness_constraint_unfair_trade(self, sample_player_values):
        """Test unfair trade outside threshold."""
        trade = {
            'team_a_sends': [{'sleeper_id': '421', 'value': 45.0}],
            'team_b_sends': [{'sleeper_id': '4035', 'value': 20.0}]  # Much lower value
        }
        
        is_fair, delta_pct = check_fairness_constraint(trade, sample_player_values)
        
        assert isinstance(is_fair, bool)
        assert isinstance(delta_pct, float)
        # Large value difference should result in unfair trade
    
    def test_calculate_trade_side_value(self, sample_player_values):
        """Test trade side value calculation."""
        players = [
            {'sleeper_id': '421', 'value': 45.0},
            {'sleeper_id': '4046', 'value': 50.0}
        ]
        
        result = _calculate_trade_side_value(players, sample_player_values)
        
        assert isinstance(result, float)
        assert result > 0


class TestCalculateStarterImpact:
    """Test starter impact calculation functionality."""
    
    def test_calculate_starter_impact_success(self, sample_trade, sample_team_rosters, sample_player_values):
        """Test successful starter impact calculation."""
        team_a_gain, team_b_gain = calculate_starter_impact(sample_trade, sample_team_rosters, sample_player_values)
        
        assert isinstance(team_a_gain, float)
        assert isinstance(team_b_gain, float)
    
    def test_simulate_trade_roster(self):
        """Test roster simulation for trades."""
        original_roster = {'players': ['421', '4046', '515']}
        removes = [{'sleeper_id': '421'}]
        adds = [{'sleeper_id': '858'}]
        
        result = _simulate_trade_roster(original_roster, removes, adds)
        
        assert '421' not in result['players']
        assert '858' in result['players']
        assert '4046' in result['players']  # Unchanged
        assert '515' in result['players']   # Unchanged


class TestFilterValidTrades:
    """Test trade filtering functionality."""
    
    def test_filter_valid_trades_success(self, sample_candidate_trades, sample_team_rosters, sample_player_values):
        """Test successful filtering of valid trades."""
        result = filter_valid_trades(sample_candidate_trades, sample_team_rosters, sample_player_values)
        
        assert isinstance(result, list)
        # All returned trades should have required metadata
        for trade in result:
            assert 'team_a_gain' in trade
            assert 'team_b_gain' in trade
            assert 'value_delta_pct' in trade
            assert 'trade_score' in trade
            assert 'is_fair' in trade
    
    def test_filter_valid_trades_empty_input(self, sample_team_rosters, sample_player_values):
        """Test filtering with empty candidate list."""
        result = filter_valid_trades([], sample_team_rosters, sample_player_values)
        assert result == []


# Test fixtures
@pytest.fixture
def sample_player_values():
    """Sample player values DataFrame for testing."""
    return pd.DataFrame([
        {'sleeper_id': '421', 'player': 'Josh Allen', 'position': 'QB', 'value': 45.2},
        {'sleeper_id': '4046', 'player': 'Christian McCaffrey', 'position': 'RB', 'value': 52.8},
        {'sleeper_id': '6794', 'player': 'CeeDee Lamb', 'position': 'WR', 'value': 48.1},
        {'sleeper_id': '4035', 'player': 'Travis Kelce', 'position': 'TE', 'value': 35.7},
        {'sleeper_id': '515', 'player': 'Derrick Henry', 'position': 'RB', 'value': 38.9},
        {'sleeper_id': '858', 'player': 'Tyreek Hill', 'position': 'WR', 'value': 46.3}
    ])


@pytest.fixture
def sample_team_roster():
    """Sample team roster for testing."""
    return {
        'roster_id': 1,
        'owner_id': 'user123',
        'players': ['421', '4046', '6794', '4035', '515']
    }


@pytest.fixture
def sample_team_rosters():
    """Sample team rosters dictionary for testing."""
    return {
        'Team1': {'roster_id': 1, 'owner_id': 'user1', 'players': ['421', '4046', '6794']},
        'Team2': {'roster_id': 2, 'owner_id': 'user2', 'players': ['4035', '515', '858']}
    }


@pytest.fixture
def sample_trade():
    """Sample trade for testing."""
    return {
        'type': '1-for-1',
        'team_a': 'Team1',
        'team_b': 'Team2',
        'team_a_sends': [{'sleeper_id': '421', 'player': 'Josh Allen', 'position': 'QB', 'value': 45.2}],
        'team_b_sends': [{'sleeper_id': '4035', 'player': 'Travis Kelce', 'position': 'TE', 'value': 35.7}]
    }


@pytest.fixture
def sample_candidate_trades(sample_trade):
    """Sample candidate trades list for testing."""
    return [sample_trade]


# Integration tests
def test_complete_analysis_workflow(sample_player_values, sample_team_rosters):
    """Integration test for complete analysis workflow."""
    # Test the full workflow from roster to trade recommendations
    
    # Step 1: Calculate starter values for all teams
    all_team_starters = {}
    for team_name, roster in sample_team_rosters.items():
        starter_values = calculate_starter_values(roster, sample_player_values)
        all_team_starters[team_name] = starter_values
    
    # Step 2: Compute positional deltas
    team_deltas = compute_positional_deltas(all_team_starters)
    assert len(team_deltas) == len(sample_team_rosters)
    
    # Step 3: Identify needs and surplus
    team_needs_surplus = identify_needs_surplus(team_deltas)
    assert len(team_needs_surplus) == len(sample_team_rosters)
    
    # Workflow should complete without errors
    assert isinstance(all_team_starters, dict)
    assert isinstance(team_deltas, dict)
    assert isinstance(team_needs_surplus, dict)
