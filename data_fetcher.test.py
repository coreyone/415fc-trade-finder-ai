"""Unit tests for data_fetcher module."""

import pytest
import pandas as pd
import requests
from unittest.mock import patch, Mock
from data_fetcher import (
    fetch_fantasycalc_values,
    fetch_sleeper_rosters,
    fetch_sleeper_users,
    join_player_data
)


class TestFetchFantasyCalcValues:
    """Test FantasyCalc API integration."""
    
    @patch('data_fetcher.requests.get')
    def test_fetch_fantasycalc_values_success(self, mock_get):
        """Test successful FantasyCalc API call."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'sleeper_id': '421',
                'player': 'Josh Allen',
                'position': 'QB',
                'value': 45.2
            },
            {
                'sleeper_id': '4046',
                'player': 'Christian McCaffrey',
                'position': 'RB',
                'value': 52.8
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetch_fantasycalc_values()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'sleeper_id' in result.columns
        assert 'player' in result.columns
        assert 'position' in result.columns
        assert 'value' in result.columns
        
        # Verify API call parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert 'isDynasty' in call_args[1]['params']
        assert call_args[1]['params']['isDynasty'] is False
    
    @patch('data_fetcher.requests.get')
    def test_fetch_fantasycalc_values_retry_on_failure(self, mock_get):
        """Test retry logic on API failure."""
        # Mock failed then successful API response
        mock_get.side_effect = [
            requests.RequestException("Connection error"),
            requests.RequestException("Timeout"),
            Mock(json=lambda: [], raise_for_status=lambda: None)
        ]
        
        result = fetch_fantasycalc_values()
        
        assert isinstance(result, pd.DataFrame)
        assert mock_get.call_count == 3
    
    @patch('data_fetcher.requests.get')
    def test_fetch_fantasycalc_values_max_retries_exceeded(self, mock_get):
        """Test exception when max retries exceeded."""
        mock_get.side_effect = requests.RequestException("Connection error")
        
        with pytest.raises(Exception, match="Failed to fetch FantasyCalc data"):
            fetch_fantasycalc_values()
        
        assert mock_get.call_count == 3  # MAX_RETRIES


class TestFetchSleeperRosters:
    """Test Sleeper rosters API integration."""
    
    @patch('data_fetcher.requests.get')
    def test_fetch_sleeper_rosters_success(self, mock_get):
        """Test successful Sleeper rosters API call."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'roster_id': 1,
                'owner_id': 'user123',
                'players': ['421', '4046', '515']
            },
            {
                'roster_id': 2,
                'owner_id': 'user456',
                'players': ['147', '2133', '858']
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetch_sleeper_rosters()
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert 'roster_id' in result[0]
        assert 'owner_id' in result[0]
        assert 'players' in result[0]
    
    @patch('data_fetcher.requests.get')
    def test_fetch_sleeper_rosters_invalid_response(self, mock_get):
        """Test handling of invalid response format."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid format"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception, match="Failed to fetch Sleeper rosters"):
            fetch_sleeper_rosters()


class TestFetchSleeperUsers:
    """Test Sleeper users API integration."""
    
    @patch('data_fetcher.requests.get')
    def test_fetch_sleeper_users_success(self, mock_get):
        """Test successful Sleeper users API call."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'user_id': 'user123',
                'display_name': 'TeamOwner1',
                'username': 'owner1'
            },
            {
                'user_id': 'user456',
                'display_name': 'TeamOwner2',
                'username': 'owner2'
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetch_sleeper_users()
        
        assert isinstance(result, dict)
        assert len(result) == 2
        assert result['user123'] == 'TeamOwner1'
        assert result['user456'] == 'TeamOwner2'
    
    @patch('data_fetcher.requests.get')
    def test_fetch_sleeper_users_fallback_to_username(self, mock_get):
        """Test fallback to username when display_name is None."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'user_id': 'user123',
                'display_name': None,
                'username': 'fallback_user'
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = fetch_sleeper_users()
        
        assert result['user123'] == 'fallback_user'


class TestJoinPlayerData:
    """Test player data joining functionality."""
    
    def test_join_player_data_success(self):
        """Test successful joining of FantasyCalc and Sleeper data."""
        # Create test FantasyCalc DataFrame
        fantasycalc_df = pd.DataFrame([
            {
                'sleeper_id': '421',
                'player': 'Josh Allen',
                'position': 'QB',
                'value': 45.2
            },
            {
                'sleeper_id': '4046',
                'player': 'Christian McCaffrey',
                'position': 'RB',
                'value': 52.8
            }
        ])
        
        # Create test roster data
        rosters = [
            {
                'roster_id': 1,
                'owner_id': 'user123',
                'players': ['421', '515']
            },
            {
                'roster_id': 2,
                'owner_id': 'user456',
                'players': ['4046', '858']
            }
        ]
        
        result = join_player_data(fantasycalc_df, rosters)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'owner_id' in result.columns
        assert 'roster_id' in result.columns
        
        # Check specific joins
        josh_allen = result[result['sleeper_id'] == '421'].iloc[0]
        assert josh_allen['owner_id'] == 'user123'
        assert josh_allen['roster_id'] == 1
        
        cmc = result[result['sleeper_id'] == '4046'].iloc[0]
        assert cmc['owner_id'] == 'user456'
        assert cmc['roster_id'] == 2
    
    def test_join_player_data_no_matches(self):
        """Test handling when no players can be matched."""
        fantasycalc_df = pd.DataFrame([
            {
                'sleeper_id': '999',  # Non-existent player
                'player': 'Unknown Player',
                'position': 'QB',
                'value': 10.0
            }
        ])
        
        rosters = [
            {
                'roster_id': 1,
                'owner_id': 'user123',
                'players': ['421', '515']
            }
        ]
        
        result = join_player_data(fantasycalc_df, rosters)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0  # No matches found
    
    def test_join_player_data_empty_inputs(self):
        """Test handling of empty input data."""
        empty_df = pd.DataFrame()
        empty_rosters = []
        
        result = join_player_data(empty_df, empty_rosters)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


# Integration test fixtures
@pytest.fixture
def sample_fantasycalc_data():
    """Sample FantasyCalc data for testing."""
    return pd.DataFrame([
        {'sleeper_id': '421', 'player': 'Josh Allen', 'position': 'QB', 'value': 45.2},
        {'sleeper_id': '4046', 'player': 'Christian McCaffrey', 'position': 'RB', 'value': 52.8},
        {'sleeper_id': '6794', 'player': 'CeeDee Lamb', 'position': 'WR', 'value': 48.1},
        {'sleeper_id': '4035', 'player': 'Travis Kelce', 'position': 'TE', 'value': 35.7}
    ])


@pytest.fixture
def sample_roster_data():
    """Sample roster data for testing."""
    return [
        {'roster_id': 1, 'owner_id': 'user1', 'players': ['421', '6794']},
        {'roster_id': 2, 'owner_id': 'user2', 'players': ['4046', '4035']}
    ]


def test_integration_data_flow(sample_fantasycalc_data, sample_roster_data):
    """Integration test for complete data flow."""
    result = join_player_data(sample_fantasycalc_data, sample_roster_data)
    
    assert len(result) == 4
    assert all(col in result.columns for col in ['sleeper_id', 'player', 'position', 'value', 'owner_id', 'roster_id'])
    
    # Verify specific player assignments
    josh_allen = result[result['player'] == 'Josh Allen'].iloc[0]
    assert josh_allen['owner_id'] == 'user1'
    
    cmc = result[result['player'] == 'Christian McCaffrey'].iloc[0]
    assert cmc['owner_id'] == 'user2'
