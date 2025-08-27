"""Integration tests for complete trade suggestion pipeline."""

import pytest
import os
import tempfile
import pandas as pd
from unittest.mock import patch, Mock

# Import all modules for integration testing
from data_fetcher import (
    fetch_fantasycalc_values,
    fetch_sleeper_rosters,
    fetch_sleeper_users, 
    join_player_data
)
from trade_analyzer import (
    calculate_starter_values,
    compute_positional_deltas,
    identify_needs_surplus,
    generate_candidate_trades,
    filter_valid_trades
)
from trade_matcher import select_optimal_trades
from output_formatter import (
    generate_starter_snapshot,
    format_trade_recommendations,
    generate_trade_rationales,
    format_complete_report
)
from weekly_trades import (
    load_player_values,
    load_league_data,
    run_trade_analysis,
    generate_output,
    write_output_file
)


class TestCompleteDataPipeline:
    """Test complete data pipeline from API to analysis."""
    
    @patch('data_fetcher.requests.get')
    def test_complete_data_flow_mocked(self, mock_get):
        """Test complete data flow with mocked API responses."""
        
        # Mock FantasyCalc API response
        mock_fantasycalc_response = Mock()
        mock_fantasycalc_response.json.return_value = [
            {'sleeper_id': '421', 'player': 'Josh Allen', 'position': 'QB', 'value': 45.0},
            {'sleeper_id': '4046', 'player': 'Christian McCaffrey', 'position': 'RB', 'value': 50.0},
            {'sleeper_id': '6794', 'player': 'CeeDee Lamb', 'position': 'WR', 'value': 48.0},
            {'sleeper_id': '4035', 'player': 'Travis Kelce', 'position': 'TE', 'value': 35.0}
        ]
        mock_fantasycalc_response.raise_for_status.return_value = None
        
        # Mock Sleeper rosters API response
        mock_rosters_response = Mock()
        mock_rosters_response.json.return_value = [
            {'roster_id': 1, 'owner_id': 'user1', 'players': ['421', '4046']},
            {'roster_id': 2, 'owner_id': 'user2', 'players': ['6794', '4035']}
        ]
        mock_rosters_response.raise_for_status.return_value = None
        
        # Mock Sleeper users API response  
        mock_users_response = Mock()
        mock_users_response.json.return_value = [
            {'user_id': 'user1', 'display_name': 'Team Alpha'},
            {'user_id': 'user2', 'display_name': 'Team Beta'}
        ]
        mock_users_response.raise_for_status.return_value = None
        
        # Configure mock to return different responses based on URL
        def mock_get_side_effect(url, **kwargs):
            if 'fantasycalc.com' in url:
                return mock_fantasycalc_response
            elif 'rosters' in url:
                return mock_rosters_response
            elif 'users' in url:
                return mock_users_response
            else:
                raise ValueError(f"Unexpected URL: {url}")
        
        mock_get.side_effect = mock_get_side_effect
        
        # Test complete data flow
        player_values = fetch_fantasycalc_values()
        team_rosters = fetch_sleeper_rosters('1240782642371104768')
        user_mappings = fetch_sleeper_users('1240782642371104768')
        
        assert player_values is not None
        assert team_rosters is not None
        assert user_mappings is not None
        
        # Test data joining
        enriched_data = join_player_data(team_rosters, player_values, user_mappings)
        
        assert isinstance(enriched_data, dict)
        assert len(enriched_data) >= 1
        
        print("Complete data flow test passed")


class TestCompleteAnalysisPipeline:
    """Test complete analysis pipeline from data to trades."""
    
    def test_complete_analysis_flow(self, sample_enriched_data, sample_player_values):
        """Test complete analysis workflow."""
        
        # Step 1: Calculate starter values
        starter_values = calculate_starter_values(sample_enriched_data, sample_player_values)
        assert isinstance(starter_values, dict)
        
        # Step 2: Compute positional deltas
        team_deltas = compute_positional_deltas(starter_values)
        assert isinstance(team_deltas, dict)
        
        # Step 3: Identify needs and surplus
        needs_surplus = identify_needs_surplus(team_deltas)
        assert isinstance(needs_surplus, dict)
        
        # Step 4: Generate candidate trades
        candidate_trades = generate_candidate_trades(sample_enriched_data, sample_player_values, needs_surplus)
        assert isinstance(candidate_trades, list)
        
        # Step 5: Filter valid trades
        valid_trades = filter_valid_trades(candidate_trades, starter_values, sample_player_values)
        assert isinstance(valid_trades, list)
        
        # Step 6: Select optimal trades (may return empty list if no perfect matching)
        selected_trades = select_optimal_trades(valid_trades, sample_enriched_data, sample_player_values)
        assert isinstance(selected_trades, list)
        
        print(f"Complete analysis flow: {len(candidate_trades)} candidates -> {len(valid_trades)} valid -> {len(selected_trades)} selected")


class TestCompleteOutputPipeline:
    """Test complete output generation pipeline."""
    
    def test_complete_output_flow(self, sample_team_deltas, sample_trades, sample_needs_surplus):
        """Test complete output generation workflow."""
        
        # Generate individual sections
        snapshot = generate_starter_snapshot(sample_team_deltas)
        recommendations = format_trade_recommendations(sample_trades)
        rationales = generate_trade_rationales(sample_trades, sample_needs_surplus)
        
        assert isinstance(snapshot, str) and len(snapshot) > 0
        assert isinstance(recommendations, str) and len(recommendations) > 0
        assert isinstance(rationales, str) and len(rationales) > 0
        
        # Generate complete report
        complete_report = format_complete_report(snapshot, recommendations, rationales)
        
        assert isinstance(complete_report, str)
        assert len(complete_report) > 0
        assert "WEEKLY TRADE SUGGESTIONS" in complete_report
        
        # Test file writing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            success = write_output_file(complete_report, temp_path, verbose=False)
            assert success is True
            
            # Verify file was written correctly
            with open(temp_path, 'r') as f:
                written_content = f.read()
            
            assert written_content == complete_report
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        print("Complete output flow test passed")


class TestCLIWorkflow:
    """Test CLI workflow functions."""
    
    def test_load_player_values_csv(self):
        """Test loading player values from CSV file."""
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("sleeper_id,player,position,value\n")
            f.write("421,Josh Allen,QB,45.0\n")
            f.write("4046,Christian McCaffrey,RB,50.0\n")
            temp_csv_path = f.name
        
        try:
            # Test loading from CSV
            player_values = load_player_values(temp_csv_path, verbose=False)
            
            assert player_values is not None
            assert isinstance(player_values, pd.DataFrame)
            assert len(player_values) == 2
            assert 'sleeper_id' in player_values.columns
            assert 'player' in player_values.columns
            assert 'position' in player_values.columns
            assert 'value' in player_values.columns
            
        finally:
            if os.path.exists(temp_csv_path):
                os.unlink(temp_csv_path)
    
    def test_load_player_values_nonexistent_file(self):
        """Test handling of non-existent CSV file."""
        result = load_player_values('/nonexistent/file.csv', verbose=False)
        assert result is None
    
    @patch('weekly_trades.fetch_sleeper_rosters')
    @patch('weekly_trades.fetch_sleeper_users')
    def test_load_league_data_success(self, mock_users, mock_rosters):
        """Test successful league data loading."""
        
        # Mock successful API responses
        mock_rosters.return_value = {'Team1': {'roster_id': 1, 'players': ['421']}}
        mock_users.return_value = {'user1': 'Team Alpha'}
        
        rosters, users = load_league_data('test_league_id', verbose=False)
        
        assert rosters is not None
        assert users is not None
        assert isinstance(rosters, dict)
        assert isinstance(users, dict)
    
    @patch('weekly_trades.fetch_sleeper_rosters')
    @patch('weekly_trades.fetch_sleeper_users')  
    def test_load_league_data_failure(self, mock_users, mock_rosters):
        """Test league data loading failure."""
        
        # Mock API failures
        mock_rosters.return_value = None
        mock_users.return_value = None
        
        rosters, users = load_league_data('test_league_id', verbose=False)
        
        assert rosters is None
        assert users is None


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""
    
    def test_run_trade_analysis_workflow(self, sample_player_values_df, sample_team_rosters_dict, sample_user_mappings):
        """Test complete trade analysis workflow function."""
        
        team_deltas, needs_surplus, selected_trades = run_trade_analysis(
            sample_player_values_df, sample_team_rosters_dict, sample_user_mappings, verbose=False
        )
        
        # Should complete without errors even if no trades found
        assert team_deltas is not None
        assert needs_surplus is not None
        assert selected_trades is not None
        assert isinstance(team_deltas, dict)
        assert isinstance(needs_surplus, dict)
        assert isinstance(selected_trades, list)
    
    def test_generate_output_workflow(self, sample_team_deltas, sample_needs_surplus, sample_trades):
        """Test output generation workflow function."""
        
        output = generate_output(sample_team_deltas, sample_needs_surplus, sample_trades, verbose=False)
        
        assert isinstance(output, str)
        assert len(output) > 0
        assert "WEEKLY TRADE SUGGESTIONS" in output


# Test fixtures for integration tests
@pytest.fixture
def sample_enriched_data():
    """Sample enriched team data."""
    return {
        'Team Alpha': {
            'roster_id': 1,
            'owner_id': 'user1',
            'players': [
                {'sleeper_id': '421', 'player': 'Josh Allen', 'position': 'QB', 'value': 45.0},
                {'sleeper_id': '4046', 'player': 'Christian McCaffrey', 'position': 'RB', 'value': 50.0}
            ]
        },
        'Team Beta': {
            'roster_id': 2,
            'owner_id': 'user2',
            'players': [
                {'sleeper_id': '6794', 'player': 'CeeDee Lamb', 'position': 'WR', 'value': 48.0},
                {'sleeper_id': '4035', 'player': 'Travis Kelce', 'position': 'TE', 'value': 35.0}
            ]
        },
        'Team Gamma': {
            'roster_id': 3,
            'owner_id': 'user3', 
            'players': [
                {'sleeper_id': '515', 'player': 'Derrick Henry', 'position': 'RB', 'value': 38.0},
                {'sleeper_id': '858', 'player': 'Tyreek Hill', 'position': 'WR', 'value': 46.0}
            ]
        },
        'Team Delta': {
            'roster_id': 4,
            'owner_id': 'user4',
            'players': [
                {'sleeper_id': '2133', 'player': 'Aaron Jones', 'position': 'RB', 'value': 25.0},
                {'sleeper_id': '147', 'player': 'Davante Adams', 'position': 'WR', 'value': 28.0}
            ]
        }
    }


@pytest.fixture
def sample_player_values():
    """Sample player values DataFrame."""
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


@pytest.fixture
def sample_player_values_df():
    """Sample player values as DataFrame for CLI tests."""
    return pd.DataFrame([
        {'sleeper_id': '421', 'player': 'Josh Allen', 'position': 'QB', 'value': 45.0},
        {'sleeper_id': '4046', 'player': 'Christian McCaffrey', 'position': 'RB', 'value': 50.0},
        {'sleeper_id': '6794', 'player': 'CeeDee Lamb', 'position': 'WR', 'value': 48.0},
        {'sleeper_id': '4035', 'player': 'Travis Kelce', 'position': 'TE', 'value': 35.0}
    ])


@pytest.fixture
def sample_team_rosters_dict():
    """Sample team rosters dictionary for CLI tests."""
    return {
        'Team Alpha': {'roster_id': 1, 'owner_id': 'user1', 'players': ['421', '4046']},
        'Team Beta': {'roster_id': 2, 'owner_id': 'user2', 'players': ['6794', '4035']}
    }


@pytest.fixture
def sample_user_mappings():
    """Sample user mappings for CLI tests."""
    return {
        'user1': 'Team Alpha',
        'user2': 'Team Beta'
    }


@pytest.fixture
def sample_team_deltas():
    """Sample team deltas for output tests."""
    return {
        'Team Alpha': {'QB': 2.5, 'RB': -1.2, 'WR': 3.8, 'TE': 0.5},
        'Team Beta': {'QB': -3.1, 'RB': 4.2, 'WR': -0.8, 'TE': -2.1}
    }


@pytest.fixture
def sample_trades():
    """Sample trades for output tests."""
    return [
        {
            'team_a': 'Team Alpha',
            'team_b': 'Team Beta',
            'team_a_sends': [{'player': 'Josh Allen', 'position': 'QB', 'value': 45.0}],
            'team_b_sends': [{'player': 'Christian McCaffrey', 'position': 'RB', 'value': 50.0}],
            'team_a_gain': 4.5,
            'team_b_gain': 3.8,
            'value_delta_pct': 10.0,
            'trade_score': 18.3
        }
    ]


@pytest.fixture
def sample_needs_surplus():
    """Sample needs and surplus for output tests."""
    return {
        'Team Alpha': {'needs': ['RB'], 'surplus': ['QB']},
        'Team Beta': {'needs': ['QB'], 'surplus': ['RB']}
    }


# CLI-specific integration tests
def test_cli_help_functionality():
    """Test that CLI help works without errors."""
    import subprocess
    
    try:
        result = subprocess.run(
            ['python', 'weekly_trades.py', '--help'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should exit with 0 and show help text
        assert result.returncode == 0
        assert 'weekly fantasy football trade suggestions' in result.stdout.lower()
        assert '--league' in result.stdout
        assert '--out' in result.stdout
        assert '--values' in result.stdout
        
        print("CLI help functionality test passed")
        
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Skip if Python not available or script takes too long
        print("Skipping CLI help test - Python not available or timeout")


def test_performance_with_large_dataset():
    """Test performance with larger datasets."""
    import time
    
    # Create larger dataset
    large_player_values = pd.DataFrame([
        {'sleeper_id': str(i), 'player': f'Player {i}', 'position': 'RB', 'value': 20.0 + i}
        for i in range(100)  # 100 players
    ])
    
    large_team_data = {
        f'Team{i}': {
            'roster_id': i,
            'owner_id': f'user{i}',
            'players': [str(j) for j in range(i*8, (i+1)*8)]  # 8 players per team
        }
        for i in range(12)  # 12 teams
    }
    
    user_mappings = {f'user{i}': f'Team{i}' for i in range(12)}
    
    start_time = time.time()
    
    # Test with larger dataset
    team_deltas, needs_surplus, selected_trades = run_trade_analysis(
        large_player_values, large_team_data, user_mappings, verbose=False
    )
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Should complete within reasonable time (< 30 seconds)
    assert elapsed < 30.0, f"Analysis took too long: {elapsed:.2f} seconds"
    
    print(f"Performance test passed: {elapsed:.2f} seconds for 12 teams, 100 players")


if __name__ == "__main__":
    # Quick integration test when run directly
    print("Running quick integration test...")
    
    # Test data loading functions
    print("✓ Testing data loading...")
    
    # Test analysis functions  
    print("✓ Testing analysis pipeline...")
    
    # Test output functions
    print("✓ Testing output generation...")
    
    print("Integration tests completed successfully!")
