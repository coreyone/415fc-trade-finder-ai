"""Output formatting module for generating plain text reports."""

import pandas as pd
from typing import Dict, List
from config import OUTPUT_DECIMAL_PLACES, ASCII_ONLY


def generate_starter_snapshot(team_deltas: Dict[str, Dict]) -> str:
    """
    Generate mobile-friendly starter snapshot.
    
    Args:
        team_deltas: Dictionary of team_name -> {position: delta} mappings
        
    Returns:
        Mobile-friendly formatted snapshot
    """
    if not team_deltas:
        return "No team data available."
    
    lines = []
    lines.append("📊 TEAM STRENGTHS")
    lines.append("")
    
    for team_name, deltas in team_deltas.items():
        # Truncate long team names
        team_short = team_name[:15]
        lines.append(f"{team_short}:")
        
        # Group positive and negative deltas
        strengths = []
        needs = []
        
        for position, delta in deltas.items():
            if delta > 500:  # Significant strength
                strengths.append(f"{position} +{delta:.0f}")
            elif delta < -500:  # Significant need
                needs.append(f"{position} {delta:.0f}")
        
        if strengths:
            lines.append(f"Strong: {', '.join(strengths[:2])}")  # Limit to 2
        if needs:
            lines.append(f"Weak: {', '.join(needs[:2])}")  # Limit to 2
        
        lines.append("")
    
    return "\n".join(lines)


def format_trade_recommendations(trades: List[Dict], team_needs_surplus: Dict = None) -> str:
    """
    Format trade recommendations optimized for mobile/iMessage.
    
    Args:
        trades: List of recommended trade dictionaries
        team_needs_surplus: Team needs and surplus data
        
    Returns:
        Mobile-friendly formatted trade recommendations
    """
    if not trades:
        return "No trades available."
    
    lines = []
    lines.append("📈 TRADE SUGGESTIONS")
    lines.append("")
    
    for i, trade in enumerate(trades, 1):
        # Trade header - short and clear
        team_a_short = trade['team_a'][:12]  # Truncate long names
        team_b_short = trade['team_b'][:12]
        lines.append(f"Trade #{i}")
        lines.append(f"{team_a_short} ↔ {team_b_short}")
        lines.append("")
        
        # Players being traded - one per line, short format
        for player in trade['team_a_sends']:
            name = player.get('player', 'Unknown')[:20]  # Truncate long names
            pos = player.get('position', 'N/A')
            value = player.get('value', 0)
            lines.append(f"→ {name} ({pos})")
            lines.append(f"   Value: {value:.0f}")
        
        lines.append("")
        lines.append("for")
        lines.append("")
        
        for player in trade['team_b_sends']:
            name = player.get('player', 'Unknown')[:20]
            pos = player.get('position', 'N/A')
            value = player.get('value', 0)
            lines.append(f"← {name} ({pos})")
            lines.append(f"   Value: {value:.0f}")
        
        lines.append("")
        
        # Needs summary - mobile friendly
        if team_needs_surplus:
            team_a = trade['team_a']
            team_b = trade['team_b']
            team_a_needs = team_needs_surplus.get(team_a, {}).get('needs', [])
            team_b_needs = team_needs_surplus.get(team_b, {}).get('needs', [])
            
            if team_a_needs or team_b_needs:
                lines.append("Why it works:")
                if team_a_needs:
                    needs_str = ", ".join(team_a_needs[:3])  # Limit to 3 positions
                    lines.append(f"• {team_a_short} needs {needs_str}")
                if team_b_needs:
                    needs_str = ", ".join(team_b_needs[:3])
                    lines.append(f"• {team_b_short} needs {needs_str}")
                lines.append("")
        
        # Fairness - simple format
        fairness_pct = trade.get('value_delta_pct', 0)
        lines.append(f"Fairness: {fairness_pct:.1f}%")
        
        # Add separator between trades
        if i < len(trades):
            lines.append("")
            lines.append("—" * 20)
            lines.append("")
    
    return "\n".join(lines)


def generate_trade_rationales(trades: List[Dict], team_needs_surplus: Dict) -> str:
    """
    Generate trade rationales explaining mutual benefits.
    
    Args:
        trades: List of trade dictionaries
        team_needs_surplus: Dictionary of team needs and surplus
        
    Returns:
        Formatted plain text rationales
    """
    if not trades:
        return "No trade rationales available."
    
    lines = []
    lines.append("TRADE RATIONALES")
    lines.append("=" * 20)
    lines.append("")
    
    for i, trade in enumerate(trades, 1):
        lines.append(f"Trade #{i} Rationale:")
        lines.append(f"{trade['team_a']} <-> {trade['team_b']}")
        lines.append("-" * 30)
        
        team_a = trade['team_a']
        team_b = trade['team_b']
        
        # Get team needs and surplus for context
        team_a_needs = team_needs_surplus.get(team_a, {}).get('needs', [])
        team_a_surplus = team_needs_surplus.get(team_a, {}).get('surplus', [])
        team_b_needs = team_needs_surplus.get(team_b, {}).get('needs', [])
        team_b_surplus = team_needs_surplus.get(team_b, {}).get('surplus', [])
        
        # Concise trade explanation
        team_a_needs_str = ", ".join(team_a_needs) if team_a_needs else "None"
        team_b_needs_str = ", ".join(team_b_needs) if team_b_needs else "None"
        
        lines.append(f"{team_a} needs: {team_a_needs_str} | {team_b} needs: {team_b_needs_str}")
        lines.append(f"Fair value exchange ({trade.get('value_delta_pct', 0):.1f}% difference)")
        
        lines.append("")
    
    return "\n".join(lines)


def format_complete_report(snapshot: str, recommendations: str) -> str:
    """
    Combine all sections into final plain text report.
    
    Args:
        snapshot: Starter snapshot text
        recommendations: Trade recommendations text
        
    Returns:
        Complete formatted report
    """
    sections = []
    
    if snapshot:
        sections.append(snapshot)
    
    if recommendations:
        sections.append(recommendations)
    
    # Join sections with double line breaks
    report = "\n\n\n".join(sections)
    
    # Add final formatting
    lines = report.split("\n")
    formatted_lines = []
    
    for line in lines:
        # Ensure ASCII-only output if configured
        if ASCII_ONLY:
            # Replace any non-ASCII characters with closest ASCII equivalent
            line = line.encode('ascii', 'ignore').decode('ascii')
        
        formatted_lines.append(line)
    
    return "\n".join(formatted_lines)
