"""Data fetching module for FantasyCalc and Sleeper APIs."""

import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
import time
from config import (
    FANTASYCALC_API_URL, FANTASYCALC_PARAMS, SLEEPER_API_BASE_URL,
    LEAGUE_ID, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
)


def fetch_fantasycalc_values() -> pd.DataFrame:
    """
    Fetch current player values from FantasyCalc API.
    
    Returns:
        DataFrame with player values including sleeper_id, name, position, value
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                FANTASYCALC_API_URL,
                params=FANTASYCALC_PARAMS,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the nested API response structure
            parsed_data = []
            players_list = data.get('players', []) if isinstance(data, dict) else data
            
            for item in players_list:
                try:
                    player_info = item.get('player', {})
                    parsed_item = {
                        'sleeper_id': player_info.get('sleeperId', ''),
                        'player': player_info.get('name', ''),
                        'position': player_info.get('position', ''),
                        'value': item.get('redraftValue', 0),  # Use redraftValue as-is
                        'redraft_value': item.get('redraftValue', 0),
                        'dynasty_value': item.get('value', 0),  # Keep original value as dynasty_value
                        'team': player_info.get('maybeTeam', ''),
                        'overall_rank': item.get('overallRank', 0),
                        'position_rank': item.get('positionRank', 0),
                        'age': player_info.get('maybeAge', 0),
                        'college': player_info.get('maybeCollege', ''),
                        'experience': player_info.get('maybeYoe', 0),
                        'trend_30_day': item.get('trend30Day', 0),
                        'combined_value': item.get('combinedValue', 0),
                        'tier': item.get('maybeTier', 0),
                        'trade_frequency': item.get('maybeTradeFrequency', 0.0)
                    }
                    
                    # Only include players with valid data
                    if (parsed_item['sleeper_id'] and 
                        parsed_item['player'] and 
                        parsed_item['position'] and 
                        parsed_item['value'] > 0):
                        parsed_data.append(parsed_item)
                        
                except (KeyError, TypeError) as e:
                    print(f"Warning: Skipping malformed player data: {e}")
                    continue
            
            # Convert to DataFrame
            df = pd.DataFrame(parsed_data)
            
            if df.empty:
                raise ValueError("No valid player data found in API response")
            
            # Filter to only relevant positions
            relevant_positions = ['QB', 'RB', 'WR', 'TE']
            df = df[df['position'].isin(relevant_positions)].copy()
            
            # Ensure numeric value column
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna(subset=['value'])
            
            print(f"Successfully fetched {len(df)} player values from FantasyCalc")
            return df
            
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise Exception(f"Failed to fetch FantasyCalc data after {MAX_RETRIES} attempts")
    
    return pd.DataFrame()  # Fallback empty DataFrame


def fetch_sleeper_rosters(league_id: str = LEAGUE_ID) -> List[Dict]:
    """
    Fetch league rosters from Sleeper API.
    
    Args:
        league_id: Sleeper league ID
    
    Returns:
        List of roster dictionaries with owner_id, player_ids, etc.
    """
    url = f"{SLEEPER_API_BASE_URL}/league/{league_id}/rosters"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            rosters = response.json()
            
            if not isinstance(rosters, list):
                raise ValueError("Expected list of rosters from Sleeper API")
            
            print(f"Successfully fetched {len(rosters)} team rosters from Sleeper")
            return rosters
            
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise Exception(f"Failed to fetch Sleeper rosters after {MAX_RETRIES} attempts")
    
    return []  # Fallback empty list


def fetch_sleeper_users(league_id: str = LEAGUE_ID) -> Dict[str, str]:
    """
    Fetch league users to map user IDs to display names.
    
    Args:
        league_id: Sleeper league ID
    
    Returns:
        Dictionary mapping user_id to display_name
    """
    url = f"{SLEEPER_API_BASE_URL}/league/{league_id}/users"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            users = response.json()
            
            if not isinstance(users, list):
                raise ValueError("Expected list of users from Sleeper API")
            
            # Create mapping from user_id to display_name
            user_mapping = {}
            for user in users:
                user_id = user.get('user_id')
                display_name = user.get('display_name') or user.get('username', f"User_{user_id}")
                if user_id:
                    user_mapping[user_id] = display_name
            
            print(f"Successfully fetched {len(user_mapping)} user mappings from Sleeper")
            return user_mapping
            
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise Exception(f"Failed to fetch Sleeper users after {MAX_RETRIES} attempts")
    
    return {}  # Fallback empty dict


def join_player_data(team_rosters: Dict, player_values: pd.DataFrame, user_mappings: Dict) -> Dict:
    """
    Join FantasyCalc values with Sleeper roster data using sleeper_id.
    
    Args:
        team_rosters: Dictionary of team rosters from Sleeper
        player_values: DataFrame with player values from FantasyCalc
        user_mappings: Dictionary mapping user IDs to display names
        
    Returns:
        Dictionary of enriched team data with player values
    """
    # Create player value lookup by sleeper_id
    player_values_dict = {}
    for _, player in player_values.iterrows():
        sleeper_id = str(player.get('sleeper_id', ''))
        if sleeper_id:
            player_values_dict[sleeper_id] = {
                'player': player.get('player', ''),
                'position': player.get('position', ''),
                'value': player.get('value', 0.0),
                'team': player.get('team', ''),
                'overall_rank': player.get('overall_rank', 0),
                'position_rank': player.get('position_rank', 0),
                'age': player.get('age', 0),
                'college': player.get('college', ''),
                'experience': player.get('experience', 0),
                'trend_30_day': player.get('trend_30_day', 0),
                'combined_value': player.get('combined_value', 0),
                'tier': player.get('tier', 0),
                'trade_frequency': player.get('trade_frequency', 0.0)
            }
    
    # Build enriched team data structure
    enriched_teams = {}
    
    for roster in team_rosters:
        owner_id = roster.get('owner_id')
        roster_id = roster.get('roster_id')
        player_ids = roster.get('players', [])
        
        # Get team display name from user mappings
        team_name = user_mappings.get(owner_id, f"Team {roster_id}")
        
        # Enrich players with values
        enriched_players = []
        for player_id in player_ids:
            player_id_str = str(player_id)
            if player_id_str in player_values_dict:
                player_data = player_values_dict[player_id_str].copy()
                player_data['sleeper_id'] = player_id_str
                enriched_players.append(player_data)
        
        enriched_teams[team_name] = {
            'roster_id': roster_id,
            'owner_id': owner_id,
            'players': enriched_players
        }
    
    print(f"Successfully enriched {len(enriched_teams)} teams with player values")
    return enriched_teams
