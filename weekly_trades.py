#!/usr/bin/env python3
"""
Weekly Trade Suggestions CLI Script

Main entry point for generating fantasy football trade recommendations
using FantasyCalc values and Sleeper league data.
"""

import argparse
import sys
import os
from typing import Optional

# Local module imports
from config import SLEEPER_LEAGUE_ID, DEFAULT_OUTPUT_PATH
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


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate weekly fantasy football trade suggestions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use defaults
  %(prog)s --league 1240782642371104768       # Specify league ID
  %(prog)s --out trades_week12.txt            # Specify output file
  %(prog)s --values custom_values.csv         # Use custom player values
        """
    )
    
    parser.add_argument(
        '--values',
        type=str,
        help='Path to custom player values CSV file (default: fetch from FantasyCalc)'
    )
    
    parser.add_argument(
        '--league',
        type=str,
        default=SLEEPER_LEAGUE_ID,
        help=f'Sleeper league ID (default: {SLEEPER_LEAGUE_ID})'
    )
    
    parser.add_argument(
        '--out',
        type=str,
        default=DEFAULT_OUTPUT_PATH,
        help=f'Output file path (default: {DEFAULT_OUTPUT_PATH})'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run analysis but do not write output file'
    )
    
    return parser.parse_args()


def load_player_values(values_path: Optional[str], verbose: bool = False) -> Optional[object]:
    """
    Load player values either from custom file or FantasyCalc API.
    
    Args:
        values_path: Path to custom CSV file, or None to fetch from API
        verbose: Whether to print detailed progress
        
    Returns:
        DataFrame with player values or None on error
    """
    try:
        if values_path:
            if verbose:
                print(f"Loading custom player values from: {values_path}")
            
            if not os.path.exists(values_path):
                print(f"Error: Values file not found: {values_path}")
                return None
                
            import pandas as pd
            return pd.read_csv(values_path)
        else:
            if verbose:
                print("Fetching player values from FantasyCalc API...")
            
            return fetch_fantasycalc_values()
            
    except Exception as e:
        print(f"Error loading player values: {e}")
        return None


def load_league_data(league_id: str, verbose: bool = False) -> tuple:
    """
    Load team rosters and user mappings from Sleeper API.
    
    Args:
        league_id: Sleeper league ID
        verbose: Whether to print detailed progress
        
    Returns:
        Tuple of (team_rosters, user_mappings) or (None, None) on error
    """
    try:
        if verbose:
            print(f"Fetching league data for league ID: {league_id}")
        
        # Fetch rosters and users
        rosters = fetch_sleeper_rosters(league_id)
        users = fetch_sleeper_users(league_id)
        
        if not rosters or not users:
            print("Error: Failed to fetch league data from Sleeper API")
            return None, None
            
        if verbose:
            print(f"Loaded {len(rosters)} team rosters and {len(users)} users")
            
        return rosters, users
        
    except Exception as e:
        print(f"Error loading league data: {e}")
        return None, None


def run_trade_analysis(player_values, team_rosters, user_mappings, verbose: bool = False) -> tuple:
    """
    Run complete trade analysis pipeline.
    
    Args:
        player_values: DataFrame with player values
        team_rosters: Dictionary of team rosters
        user_mappings: Dictionary mapping user IDs to display names
        verbose: Whether to print detailed progress
        
    Returns:
        Tuple of (team_deltas, needs_surplus, selected_trades) or (None, None, None) on error
    """
    try:
        if verbose:
            print("Joining player data...")
        
        # Join player data with values
        enriched_data = join_player_data(team_rosters, player_values, user_mappings)
        
        if verbose:
            print("Calculating starter values...")
        
        # Calculate starter values for each team
        all_team_starters = {}
        for team_name, team_data in enriched_data.items():
            # Convert enriched team data to format expected by calculate_starter_values
            team_roster = {
                'players': [player['sleeper_id'] for player in team_data['players']]
            }
            starter_values = calculate_starter_values(team_roster, player_values)
            all_team_starters[team_name] = starter_values
        
        if verbose:
            print("Computing positional deltas...")
        
        # Compute positional deltas vs league median
        team_deltas = compute_positional_deltas(all_team_starters)
        
        if verbose:
            print("Identifying needs and surplus...")
        
        # Identify team needs and surplus
        needs_surplus = identify_needs_surplus(team_deltas)
        
        if verbose:
            print("Generating candidate trades...")
        
        # Generate candidate trades
        candidate_trades = generate_candidate_trades(needs_surplus, player_values, enriched_data)
        
        if verbose:
            print(f"Generated {len(candidate_trades)} candidate trades")
        
        # Filter valid trades
        valid_trades = filter_valid_trades(candidate_trades, enriched_data, player_values)
        
        if verbose:
            print(f"Filtered to {len(valid_trades)} valid trades")
        
        if not valid_trades:
            print("Warning: No valid trades found")
            return team_deltas, needs_surplus, []
        
        if verbose:
            print("Selecting optimal trade matching...")
        
        # Select optimal trades using matching algorithm
        selected_trades = select_optimal_trades(valid_trades, enriched_data, player_values)
        
        if verbose:
            print(f"Selected {len(selected_trades)} optimal trades")
        
        return team_deltas, needs_surplus, selected_trades
        
    except Exception as e:
        print(f"Error in trade analysis: {e}")
        return None, None, None


def generate_output(team_deltas, needs_surplus, selected_trades, verbose: bool = False) -> str:
    """
    Generate formatted output report.
    
    Args:
        team_deltas: Team positional deltas
        needs_surplus: Team needs and surplus
        selected_trades: List of selected trades
        verbose: Whether to print detailed progress
        
    Returns:
        Formatted report string
    """
    try:
        if verbose:
            print("Generating output report...")
        
        # Generate individual sections
        snapshot = generate_starter_snapshot(team_deltas)
        recommendations = format_trade_recommendations(selected_trades, needs_surplus)
        
        # Combine into complete report
        complete_report = format_complete_report(snapshot, recommendations)
        
        return complete_report
        
    except Exception as e:
        print(f"Error generating output: {e}")
        return ""


def write_output_file(content: str, output_path: str, verbose: bool = False) -> bool:
    """
    Write content to output file.
    
    Args:
        content: Report content to write
        output_path: Path to output file
        verbose: Whether to print detailed progress
        
    Returns:
        True on success, False on error
    """
    try:
        if verbose:
            print(f"Writing output to: {output_path}")
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        # Write content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if verbose:
            print(f"Successfully wrote {len(content)} characters to {output_path}")
        
        return True
        
    except Exception as e:
        print(f"Error writing output file: {e}")
        return False


def main() -> int:
    """Main entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    if args.verbose:
        print("Weekly Trade Suggestions Generator")
        print("=" * 40)
    
    # Load player values
    player_values = load_player_values(args.values, args.verbose)
    if player_values is None:
        print("Failed to load player values")
        return 1
    
    # Load league data
    team_rosters, user_mappings = load_league_data(args.league, args.verbose)
    if team_rosters is None or user_mappings is None:
        print("Failed to load league data")
        return 1
    
    # Run trade analysis
    team_deltas, needs_surplus, selected_trades = run_trade_analysis(
        player_values, team_rosters, user_mappings, args.verbose
    )
    
    if team_deltas is None:
        print("Trade analysis failed")
        return 1
    
    # Generate output
    report_content = generate_output(team_deltas, needs_surplus, selected_trades, args.verbose)
    
    if not report_content:
        print("Failed to generate output report")
        return 1
    
    # Handle output
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - Output preview:")
        print("=" * 60)
        print(report_content[:1000] + "..." if len(report_content) > 1000 else report_content)
        print("=" * 60)
        print(f"Report contains {len(report_content)} characters")
    else:
        success = write_output_file(report_content, args.out, args.verbose)
        if not success:
            return 1
        
        print(f"Trade suggestions generated successfully: {args.out}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
