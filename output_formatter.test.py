"""Unit tests for output_formatter module."""

import pytest
import datetime
from unittest.mock import patch
from output_formatter import (
    generate_starter_snapshot,
    format_trade_recommendations,
    generate_trade_rationales,
    format_complete_report
)


class TestGenerateStarterSnapshot:
    """Test starter snapshot generation functionality."""
    
    def test_generate_starter_snapshot_basic(self, sample_team_deltas):
        """Test basic starter snapshot generation."""
        result = generate_starter_snapshot(sample_team_deltas)
        
        assert isinstance(result, str)
        assert "TEAM STARTER SNAPSHOT" in result
        assert "Team1" in result
        assert "Team2" in result
        assert "QB:" in result
        assert "RB:" in result
        assert "WR:" in result
        assert "TE:" in result
    
    def test_generate_starter_snapshot_positive_negative(self):
        """Test snapshot with positive and negative deltas."""
        team_deltas = {
            'Team1': {'QB': 5.2, 'RB': -3.1, 'WR': 2.0, 'TE': -1.5},
            'Team2': {'QB': -2.3, 'RB': 4.8, 'WR': -0.5, 'TE': 1.2}
        }
        
        result = generate_starter_snapshot(team_deltas)
        
        # Check for proper sign formatting
        assert "+5.2" in result
        assert "-3.1" in result
        assert "+2.0" in result
        assert "-1.5" in result
        assert "-2.3" in result
        assert "+4.8" in result
    
    def test_generate_starter_snapshot_empty_input(self):
        """Test handling of empty team deltas."""
        result = generate_starter_snapshot({})
        
        assert isinstance(result, str)
        assert "TEAM STARTER SNAPSHOT" in result
    
    def test_generate_starter_snapshot_sorted_teams(self):
        """Test that teams are sorted alphabetically."""
        team_deltas = {
            'ZTeam': {'QB': 1.0}, 
            'ATeam': {'QB': 2.0}, 
            'MTeam': {'QB': 3.0}
        }
        
        result = generate_starter_snapshot(team_deltas)
        
        # Find positions of team names in output
        a_pos = result.find('ATeam')
        m_pos = result.find('MTeam') 
        z_pos = result.find('ZTeam')
        
        assert a_pos < m_pos < z_pos


class TestFormatTradeRecommendations:
    """Test trade recommendations formatting functionality."""
    
    def test_format_trade_recommendations_basic(self, sample_trades):
        """Test basic trade recommendations formatting."""
        result = format_trade_recommendations(sample_trades)
        
        assert isinstance(result, str)
        assert "TRADE RECOMMENDATIONS" in result
        assert "Trade #1:" in result
        assert "Trade #2:" in result
        assert "sends:" in result
        assert "Projected Gains:" in result
        assert "Fairness:" in result
    
    def test_format_trade_recommendations_empty_input(self):
        """Test handling of empty trades list."""
        result = format_trade_recommendations([])
        
        assert result == "No trade recommendations available."
    
    def test_format_trade_recommendations_player_details(self):
        """Test formatting of player details."""
        trades = [{
            'team_a': 'Team1', 
            'team_b': 'Team2',
            'team_a_sends': [{'player': 'Josh Allen', 'position': 'QB', 'value': 45.0}],
            'team_b_sends': [{'player': 'CMC', 'position': 'RB', 'value': 50.0}],
            'team_a_gain': 4.5,
            'team_b_gain': 3.2,
            'value_delta_pct': 10.0,
            'trade_score': 15.5
        }]
        
        result = format_trade_recommendations(trades)
        
        assert "Josh Allen (QB) - $45.0" in result
        assert "CMC (RB) - $50.0" in result
        assert "+4.5 pts/week" in result
        assert "+3.2 pts/week" in result
        assert "10.0% value difference" in result
    
    def test_format_trade_recommendations_missing_data(self):
        """Test handling of trades with missing player data."""
        trades = [{
            'team_a': 'Team1',
            'team_b': 'Team2', 
            'team_a_sends': [{'sleeper_id': '123'}],  # Missing player name/position
            'team_b_sends': [{'player': 'Player B'}],  # Missing position/value
            'team_a_gain': 2.0,
            'team_b_gain': 1.5
        }]
        
        result = format_trade_recommendations(trades)
        
        # Should handle missing data gracefully
        assert "Unknown (N/A)" in result
        assert "Player B (N/A)" in result
        assert "$0.0" in result


class TestGenerateTradeRationales:
    """Test trade rationales generation functionality."""
    
    def test_generate_trade_rationales_basic(self, sample_trades, sample_needs_surplus):
        """Test basic trade rationales generation."""
        result = generate_trade_rationales(sample_trades, sample_needs_surplus)
        
        assert isinstance(result, str)
        assert "TRADE RATIONALES" in result
        assert "Trade #1 Rationale:" in result
        assert "Why this works:" in result
        assert "has needs at:" in result or "has surplus at:" in result
    
    def test_generate_trade_rationales_empty_trades(self):
        """Test handling of empty trades list."""
        result = generate_trade_rationales([], {})
        
        assert result == "No trade rationales available."
    
    def test_generate_trade_rationales_mutual_benefit(self):
        """Test explanation of mutual benefit."""
        trades = [{
            'team_a': 'Team1',
            'team_b': 'Team2',
            'team_a_gain': 3.0,
            'team_b_gain': 4.0,
            'value_delta_pct': 8.5
        }]
        
        needs_surplus = {
            'Team1': {'needs': ['RB'], 'surplus': ['WR']},
            'Team2': {'needs': ['WR'], 'surplus': ['RB']}
        }
        
        result = generate_trade_rationales(trades, needs_surplus)
        
        assert "Team1 has needs at: RB" in result
        assert "Team1 has surplus at: WR" in result
        assert "Team2 has needs at: WR" in result
        assert "Team2 has surplus at: RB" in result
        assert "Both teams improve" in result
        assert "Fair value exchange (8.5% difference)" in result
        assert "Combined weekly gain: +7.0 pts" in result
    
    def test_generate_trade_rationales_missing_needs_surplus(self):
        """Test handling when team needs/surplus data is missing."""
        trades = [{'team_a': 'Team1', 'team_b': 'Team2', 'team_a_gain': 2.0, 'team_b_gain': 2.5}]
        
        result = generate_trade_rationales(trades, {})
        
        # Should still generate rationale without needs/surplus data
        assert "Trade #1 Rationale:" in result
        assert "Why this works:" in result


class TestFormatCompleteReport:
    """Test complete report formatting functionality."""
    
    @patch('output_formatter.datetime')
    def test_format_complete_report_basic(self, mock_datetime):
        """Test basic complete report formatting."""
        # Mock timestamp
        mock_datetime.datetime.now.return_value.strftime.return_value = "2024-01-15 10:30:00"
        
        snapshot = "Sample snapshot"
        recommendations = "Sample recommendations"
        rationales = "Sample rationales"
        
        result = format_complete_report(snapshot, recommendations, rationales)
        
        assert isinstance(result, str)
        assert "WEEKLY TRADE SUGGESTIONS" in result
        assert "Generated: 2024-01-15 10:30:00" in result
        assert "Sample snapshot" in result
        assert "Sample recommendations" in result
        assert "Sample rationales" in result
        assert "End of Trade Suggestions Report" in result
    
    def test_format_complete_report_empty_sections(self):
        """Test handling of empty sections."""
        result = format_complete_report("", "", "")
        
        assert "WEEKLY TRADE SUGGESTIONS" in result
        assert "End of Trade Suggestions Report" in result
        # Should not include empty sections
        assert result.count("\n\n\n") == 0  # No triple newlines from empty sections
    
    def test_format_complete_report_partial_sections(self):
        """Test with some sections empty."""
        snapshot = "Only snapshot"
        
        result = format_complete_report(snapshot, "", "")
        
        assert "Only snapshot" in result
        assert "WEEKLY TRADE SUGGESTIONS" in result
        assert "End of Trade Suggestions Report" in result


# Test fixtures
@pytest.fixture
def sample_team_deltas():
    """Sample team deltas for testing."""
    return {
        'Team1': {'QB': 2.5, 'RB': -1.2, 'WR': 3.8, 'TE': 0.5},
        'Team2': {'QB': -3.1, 'RB': 4.2, 'WR': -0.8, 'TE': -2.1},
        'Team3': {'QB': 1.0, 'RB': 2.3, 'WR': -1.5, 'TE': 1.8}
    }


@pytest.fixture  
def sample_trades():
    """Sample trades for testing."""
    return [
        {
            'team_a': 'Team1',
            'team_b': 'Team2',
            'team_a_sends': [
                {'player': 'Josh Allen', 'position': 'QB', 'value': 45.0}
            ],
            'team_b_sends': [
                {'player': 'Christian McCaffrey', 'position': 'RB', 'value': 50.0}
            ],
            'team_a_gain': 4.5,
            'team_b_gain': 3.8,
            'value_delta_pct': 10.0,
            'trade_score': 18.3
        },
        {
            'team_a': 'Team3',
            'team_b': 'Team4', 
            'team_a_sends': [
                {'player': 'CeeDee Lamb', 'position': 'WR', 'value': 48.0},
                {'player': 'Derrick Henry', 'position': 'RB', 'value': 38.0}
            ],
            'team_b_sends': [
                {'player': 'Travis Kelce', 'position': 'TE', 'value': 35.0},
                {'player': 'Tyreek Hill', 'position': 'WR', 'value': 46.0}
            ],
            'team_a_gain': 3.2,
            'team_b_gain': 4.8,
            'value_delta_pct': 6.2,
            'trade_score': 21.0
        }
    ]


@pytest.fixture
def sample_needs_surplus():
    """Sample needs and surplus for testing."""
    return {
        'Team1': {'needs': ['RB', 'TE'], 'surplus': ['QB']},
        'Team2': {'needs': ['QB'], 'surplus': ['RB', 'WR']},
        'Team3': {'needs': ['WR'], 'surplus': ['RB', 'TE']},
        'Team4': {'needs': ['TE'], 'surplus': ['WR']}
    }


# Integration tests
def test_complete_output_workflow():
    """Integration test for complete output formatting workflow."""
    
    # Sample data
    team_deltas = {
        'Team1': {'QB': 2.5, 'RB': -1.2, 'WR': 3.8, 'TE': 0.5}
    }
    
    trades = [{
        'team_a': 'Team1',
        'team_b': 'Team2', 
        'team_a_sends': [{'player': 'Test Player', 'position': 'QB', 'value': 40.0}],
        'team_b_sends': [{'player': 'Other Player', 'position': 'RB', 'value': 42.0}],
        'team_a_gain': 3.0,
        'team_b_gain': 2.5,
        'value_delta_pct': 5.0,
        'trade_score': 12.5
    }]
    
    needs_surplus = {
        'Team1': {'needs': ['RB'], 'surplus': ['QB']},
        'Team2': {'needs': ['QB'], 'surplus': ['RB']}
    }
    
    # Generate all sections
    snapshot = generate_starter_snapshot(team_deltas)
    recommendations = format_trade_recommendations(trades)
    rationales = generate_trade_rationales(trades, needs_surplus)
    complete_report = format_complete_report(snapshot, recommendations, rationales)
    
    # Verify complete workflow
    assert isinstance(complete_report, str)
    assert len(complete_report) > 0
    assert "WEEKLY TRADE SUGGESTIONS" in complete_report
    assert "TEAM STARTER SNAPSHOT" in complete_report
    assert "TRADE RECOMMENDATIONS" in complete_report 
    assert "TRADE RATIONALES" in complete_report
    assert "End of Trade Suggestions Report" in complete_report
    
    print("Integration test completed successfully")


def test_ascii_formatting():
    """Test that output uses ASCII-only characters."""
    team_deltas = {'Team1': {'QB': 2.5}}
    trades = [{
        'team_a': 'Team1', 'team_b': 'Team2',
        'team_a_sends': [{'player': 'Player A', 'position': 'QB', 'value': 40.0}],
        'team_b_sends': [{'player': 'Player B', 'position': 'RB', 'value': 42.0}],
        'team_a_gain': 2.0, 'team_b_gain': 1.5
    }]
    
    snapshot = generate_starter_snapshot(team_deltas)
    recommendations = format_trade_recommendations(trades) 
    complete_report = format_complete_report(snapshot, recommendations, "")
    
    # Verify ASCII-only (no Unicode characters above 127)
    for char in complete_report:
        assert ord(char) <= 127, f"Non-ASCII character found: {char} ({ord(char)})"
    
    print("ASCII formatting test passed")
