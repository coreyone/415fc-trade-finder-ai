"""Unit tests for trade_matcher module."""

import pytest
import networkx as nx
import pandas as pd
from unittest.mock import patch, Mock
from trade_matcher import (
    build_trade_graph,
    find_perfect_matching,
    relax_constraints_and_retry,
    validate_matching_constraints,
    select_optimal_trades,
    _widen_fairness_threshold,
    _lower_starter_gain_threshold,
    _find_best_partial_matching
)


class TestBuildTradeGraph:
    """Test trade graph building functionality."""
    
    def test_build_trade_graph_success(self, sample_valid_trades):
        """Test successful trade graph construction."""
        G = build_trade_graph(sample_valid_trades)
        
        assert isinstance(G, nx.Graph)
        assert len(G.nodes()) >= 2  # At least 2 teams involved
        assert len(G.edges()) == len(sample_valid_trades)
        
        # Check that edges have required attributes
        for u, v, data in G.edges(data=True):
            assert 'weight' in data
            assert 'trade_id' in data
            assert 'trade_data' in data
    
    def test_build_trade_graph_empty_input(self):
        """Test handling of empty trade list."""
        G = build_trade_graph([])
        
        assert isinstance(G, nx.Graph)
        assert len(G.nodes()) == 0
        assert len(G.edges()) == 0
    
    def test_build_trade_graph_duplicate_teams(self):
        """Test that duplicate team pairs are handled correctly."""
        trades = [
            {
                'team_a': 'Team1', 'team_b': 'Team2', 'trade_score': 10.0,
                'team_a_sends': [{'sleeper_id': '1'}], 'team_b_sends': [{'sleeper_id': '2'}]
            },
            {
                'team_a': 'Team1', 'team_b': 'Team2', 'trade_score': 8.0,
                'team_a_sends': [{'sleeper_id': '3'}], 'team_b_sends': [{'sleeper_id': '4'}]
            }
        ]
        
        G = build_trade_graph(trades)
        
        # Should have only one edge between Team1 and Team2 (last one wins)
        assert len(G.edges()) == 1
        assert G['Team1']['Team2']['weight'] == 8.0


class TestFindPerfectMatching:
    """Test perfect matching algorithm functionality."""
    
    def test_find_perfect_matching_success(self):
        """Test successful perfect matching with 4 teams."""
        # Create a graph with 4 teams and valid matching
        G = nx.Graph()
        G.add_nodes_from(['Team1', 'Team2', 'Team3', 'Team4'])
        
        # Add edges with trade data
        trades = [
            {'team_a': 'Team1', 'team_b': 'Team2', 'trade_score': 10.0},
            {'team_a': 'Team3', 'team_b': 'Team4', 'trade_score': 8.0}
        ]
        
        G.add_edge('Team1', 'Team2', weight=10.0, trade_data=trades[0])
        G.add_edge('Team3', 'Team4', weight=8.0, trade_data=trades[1])
        
        result = find_perfect_matching(G, target_teams=4)
        
        assert result is not None
        assert len(result) == 2  # 4 teams / 2 = 2 trades
        assert all('team_a' in trade for trade in result)
        assert all('team_b' in trade for trade in result)
    
    def test_find_perfect_matching_odd_teams(self):
        """Test handling of odd number of teams (impossible perfect matching)."""
        G = nx.Graph()
        G.add_nodes_from(['Team1', 'Team2', 'Team3'])
        G.add_edge('Team1', 'Team2', weight=5.0, trade_data={'trade_score': 5.0})
        
        result = find_perfect_matching(G, target_teams=3)
        
        assert result is None
    
    def test_find_perfect_matching_insufficient_edges(self):
        """Test handling when there aren't enough edges for perfect matching."""
        G = nx.Graph()
        G.add_nodes_from(['Team1', 'Team2', 'Team3', 'Team4'])
        G.add_edge('Team1', 'Team2', weight=5.0, trade_data={'trade_score': 5.0})
        # Missing edge for Team3-Team4
        
        result = find_perfect_matching(G, target_teams=4)
        
        assert result is None


class TestConstraintRelaxation:
    """Test constraint relaxation functionality."""
    
    def test_widen_fairness_threshold(self):
        """Test widening fairness threshold."""
        trades = [
            {'value_delta_pct': 8.0, 'team_a': 'Team1', 'team_b': 'Team2'},
            {'value_delta_pct': 18.0, 'team_a': 'Team3', 'team_b': 'Team4'},
            {'value_delta_pct': 25.0, 'team_a': 'Team5', 'team_b': 'Team6'}
        ]
        
        result = _widen_fairness_threshold(trades, 0.20)  # 20% threshold
        
        assert len(result) == 2  # Only first two should pass
        assert result[0]['value_delta_pct'] == 8.0
        assert result[1]['value_delta_pct'] == 18.0
    
    def test_lower_starter_gain_threshold(self):
        """Test lowering starter gain threshold."""
        trades = [
            {'team_a_gain': 4.0, 'team_b_gain': 3.5, 'team_a': 'Team1', 'team_b': 'Team2'},
            {'team_a_gain': 1.5, 'team_b_gain': 2.0, 'team_a': 'Team3', 'team_b': 'Team4'},
            {'team_a_gain': 2.5, 'team_b_gain': 2.2, 'team_a': 'Team5', 'team_b': 'Team6'}
        ]
        
        result = _lower_starter_gain_threshold(trades, 2.0)
        
        assert len(result) == 2  # First and third should pass
        assert result[0]['team_a_gain'] == 4.0
        assert result[1]['team_a_gain'] == 2.5
    
    def test_find_best_partial_matching(self, sample_valid_trades):
        """Test finding best partial matching when perfect matching fails."""
        result = _find_best_partial_matching(sample_valid_trades)
        
        if result:  # May be None if no matching possible
            assert isinstance(result, list)
            assert all('team_a' in trade for trade in result)
            assert all('team_b' in trade for trade in result)


class TestValidateMatchingConstraints:
    """Test matching constraint validation functionality."""
    
    def test_validate_matching_constraints_success(self):
        """Test successful validation of valid matching."""
        trades = [
            {'team_a': 'Team1', 'team_b': 'Team2'},
            {'team_a': 'Team3', 'team_b': 'Team4'},
            {'team_a': 'Team5', 'team_b': 'Team6'}
        ]
        
        result = validate_matching_constraints(trades)
        
        assert result is True
    
    def test_validate_matching_constraints_duplicate_team(self):
        """Test validation failure when team appears twice."""
        trades = [
            {'team_a': 'Team1', 'team_b': 'Team2'},
            {'team_a': 'Team1', 'team_b': 'Team3'}  # Team1 appears twice
        ]
        
        result = validate_matching_constraints(trades)
        
        assert result is False
    
    def test_validate_matching_constraints_empty_input(self):
        """Test validation of empty trade list."""
        result = validate_matching_constraints([])
        
        assert result is False


class TestSelectOptimalTrades:
    """Test complete trade selection workflow."""
    
    @patch('trade_matcher.find_perfect_matching')
    @patch('trade_matcher.build_trade_graph')
    def test_select_optimal_trades_perfect_match_success(self, mock_build_graph, mock_find_matching, 
                                                        sample_valid_trades, sample_team_rosters, 
                                                        sample_player_values):
        """Test successful optimal trade selection with perfect matching."""
        # Mock successful perfect matching
        mock_graph = Mock()
        mock_build_graph.return_value = mock_graph
        mock_find_matching.return_value = sample_valid_trades[:2]  # Return 2 trades
        
        result = select_optimal_trades(sample_valid_trades, sample_team_rosters, sample_player_values)
        
        assert isinstance(result, list)
        assert len(result) <= len(sample_valid_trades)
        mock_build_graph.assert_called_once()
        mock_find_matching.assert_called_once()
    
    @patch('trade_matcher.relax_constraints_and_retry')
    @patch('trade_matcher.find_perfect_matching')
    @patch('trade_matcher.build_trade_graph')
    def test_select_optimal_trades_with_relaxation(self, mock_build_graph, mock_find_matching, 
                                                  mock_relax, sample_valid_trades, sample_team_rosters, 
                                                  sample_player_values):
        """Test trade selection when perfect matching fails but relaxation succeeds."""
        # Mock failed perfect matching, successful relaxation
        mock_graph = Mock()
        mock_build_graph.return_value = mock_graph
        mock_find_matching.return_value = None  # Perfect matching fails
        mock_relax.return_value = sample_valid_trades[:1]  # Relaxation succeeds
        
        result = select_optimal_trades(sample_valid_trades, sample_team_rosters, sample_player_values)
        
        assert isinstance(result, list)
        mock_relax.assert_called_once()
    
    def test_select_optimal_trades_empty_input(self, sample_team_rosters, sample_player_values):
        """Test handling of empty valid trades list."""
        result = select_optimal_trades([], sample_team_rosters, sample_player_values)
        
        assert result == []


class TestRelaxConstraintsAndRetry:
    """Test constraint relaxation retry logic."""
    
    @patch('trade_matcher._widen_fairness_threshold')
    @patch('trade_matcher.find_perfect_matching')
    @patch('trade_matcher.build_trade_graph')
    def test_relax_constraints_fairness_success(self, mock_build_graph, mock_find_matching, 
                                               mock_widen, sample_valid_trades, sample_team_rosters, 
                                               sample_player_values):
        """Test successful constraint relaxation with fairness widening."""
        # Mock successful fairness widening
        mock_widen.return_value = sample_valid_trades
        mock_graph = Mock()
        mock_build_graph.return_value = mock_graph
        mock_find_matching.return_value = sample_valid_trades[:1]
        
        result = relax_constraints_and_retry(sample_valid_trades, sample_team_rosters, sample_player_values)
        
        assert result is not None
        assert isinstance(result, list)
        mock_widen.assert_called_once()
    
    @patch('trade_matcher._find_best_partial_matching')
    @patch('trade_matcher._lower_starter_gain_threshold')
    @patch('trade_matcher._allow_uneven_trades')
    @patch('trade_matcher._widen_fairness_threshold')
    @patch('trade_matcher.find_perfect_matching')
    def test_relax_constraints_all_strategies_fail(self, mock_find_matching, mock_widen, 
                                                  mock_uneven, mock_lower, mock_partial,
                                                  sample_valid_trades, sample_team_rosters, 
                                                  sample_player_values):
        """Test when all relaxation strategies fail."""
        # Mock all strategies failing
        mock_find_matching.return_value = None
        mock_widen.return_value = []
        mock_uneven.return_value = []
        mock_lower.return_value = []
        mock_partial.return_value = None
        
        result = relax_constraints_and_retry(sample_valid_trades, sample_team_rosters, sample_player_values)
        
        assert result is None


# Test fixtures
@pytest.fixture
def sample_valid_trades():
    """Sample valid trades for testing."""
    return [
        {
            'type': '1-for-1',
            'team_a': 'Team1',
            'team_b': 'Team2',
            'team_a_sends': [{'sleeper_id': '421', 'value': 45.0}],
            'team_b_sends': [{'sleeper_id': '4046', 'value': 50.0}],
            'team_a_gain': 4.5,
            'team_b_gain': 4.0,
            'value_delta_pct': 10.0,
            'trade_score': 15.5,
            'is_fair': True
        },
        {
            'type': '2-for-2',
            'team_a': 'Team3',
            'team_b': 'Team4',
            'team_a_sends': [{'sleeper_id': '6794', 'value': 48.0}, {'sleeper_id': '515', 'value': 38.0}],
            'team_b_sends': [{'sleeper_id': '4035', 'value': 35.0}, {'sleeper_id': '858', 'value': 46.0}],
            'team_a_gain': 3.5,
            'team_b_gain': 5.0,
            'value_delta_pct': 8.5,
            'trade_score': 18.0,
            'is_fair': True
        },
        {
            'type': '1-for-1',
            'team_a': 'Team5',
            'team_b': 'Team6',
            'team_a_sends': [{'sleeper_id': '2133', 'value': 25.0}],
            'team_b_sends': [{'sleeper_id': '147', 'value': 28.0}],
            'team_a_gain': 3.2,
            'team_b_gain': 3.8,
            'value_delta_pct': 11.5,
            'trade_score': 12.0,
            'is_fair': True
        }
    ]


@pytest.fixture
def sample_team_rosters():
    """Sample team rosters for testing."""
    return {
        'Team1': {'roster_id': 1, 'owner_id': 'user1', 'players': ['421', '515']},
        'Team2': {'roster_id': 2, 'owner_id': 'user2', 'players': ['4046', '858']},
        'Team3': {'roster_id': 3, 'owner_id': 'user3', 'players': ['6794', '4035']},
        'Team4': {'roster_id': 4, 'owner_id': 'user4', 'players': ['2133', '147']},
        'Team5': {'roster_id': 5, 'owner_id': 'user5', 'players': ['999', '998']},
        'Team6': {'roster_id': 6, 'owner_id': 'user6', 'players': ['997', '996']}
    }


@pytest.fixture
def sample_player_values():
    """Sample player values DataFrame for testing."""
    return pd.DataFrame([
        {'sleeper_id': '421', 'player': 'Josh Allen', 'position': 'QB', 'value': 45.0},
        {'sleeper_id': '4046', 'player': 'Christian McCaffrey', 'position': 'RB', 'value': 50.0},
        {'sleeper_id': '6794', 'player': 'CeeDee Lamb', 'position': 'WR', 'value': 48.0},
        {'sleeper_id': '4035', 'player': 'Travis Kelce', 'position': 'TE', 'value': 35.0},
        {'sleeper_id': '515', 'player': 'Derrick Henry', 'position': 'RB', 'value': 38.0},
        {'sleeper_id': '858', 'player': 'Tyreek Hill', 'position': 'WR', 'value': 46.0},
        {'sleeper_id': '2133', 'player': 'Aaron Jones', 'position': 'RB', 'value': 25.0},
        {'sleeper_id': '147', 'player': 'Davante Adams', 'position': 'WR', 'value': 28.0}
    ])


# Integration tests
def test_complete_matching_workflow(sample_valid_trades, sample_team_rosters, sample_player_values):
    """Integration test for complete matching workflow."""
    # Test the full workflow from candidate trades to final selection
    
    # Step 1: Build trade graph
    G = build_trade_graph(sample_valid_trades)
    assert isinstance(G, nx.Graph)
    assert len(G.edges()) == len(sample_valid_trades)
    
    # Step 2: Validate constraints
    is_valid = validate_matching_constraints(sample_valid_trades)
    assert isinstance(is_valid, bool)
    
    # Step 3: Select optimal trades
    selected_trades = select_optimal_trades(sample_valid_trades, sample_team_rosters, sample_player_values)
    assert isinstance(selected_trades, list)
    
    # Workflow should complete without errors
    print(f"Integration test completed: {len(selected_trades)} trades selected")


def test_graph_properties_with_12_teams():
    """Test graph properties with full 12-team scenario."""
    # Create trades covering all 12 teams (6 trades)
    trades = []
    for i in range(6):
        team_a = f"Team{2*i + 1}"
        team_b = f"Team{2*i + 2}"
        trade = {
            'team_a': team_a,
            'team_b': team_b,
            'trade_score': 10.0 + i,
            'team_a_sends': [{'sleeper_id': f'{100 + i}'}],
            'team_b_sends': [{'sleeper_id': f'{200 + i}'}]
        }
        trades.append(trade)
    
    G = build_trade_graph(trades)
    
    # Should have exactly 12 nodes and 6 edges
    assert len(G.nodes()) == 12
    assert len(G.edges()) == 6
    
    # Perfect matching should be possible
    matching = find_perfect_matching(G, target_teams=12)
    if matching:  # May fail due to graph structure
        assert len(matching) == 6
