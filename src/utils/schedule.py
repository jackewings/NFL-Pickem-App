from datetime import datetime
from typing import Dict, Tuple, Optional
import pytz
import logging

logger = logging.getLogger(__name__)

# NFL season schedule mapping (start_date, end_date) for each week
NFL_WEEKS: Dict[int, Tuple[str, str]] = {
    1: ("2025-09-05", "2025-09-11"),
    2: ("2025-09-12", "2025-09-18"),
    3: ("2025-09-19", "2025-09-25"),
    4: ("2025-09-26", "2025-10-02"),
    5: ("2025-10-03", "2025-10-09"),
    6: ("2025-10-10", "2025-10-16"),
    7: ("2025-10-17", "2025-10-23"),
    8: ("2025-10-24", "2025-10-30"),
    9: ("2025-10-31", "2025-11-06"),
    10: ("2025-11-07", "2025-11-13"),
    11: ("2025-11-14", "2025-11-20"),
    12: ("2025-11-21", "2025-11-27"),
    13: ("2025-11-28", "2025-12-04"),
    14: ("2025-12-05", "2025-12-11"),
    15: ("2025-12-12", "2025-12-18"),
    16: ("2025-12-19", "2025-12-25"),
    17: ("2025-12-26", "2026-01-01"),
    18: ("2026-01-02", "2026-01-08"),
}

def parse_game_time(time_str: str) -> datetime:
    """Convert API time string to datetime object."""
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

def assign_week(commence_time_str: str) -> Optional[int]:
    """
    Determine NFL week number from game commence time.
    
    Args:
        commence_time_str: ISO format datetime string from API
        
    Returns:
        int: Week number (1-18) or None if outside season
    """
    try:
        game_date = parse_game_time(commence_time_str).date()
        
        for week, (start_str, end_str) in NFL_WEEKS.items():
            start = datetime.fromisoformat(start_str).date()
            end = datetime.fromisoformat(end_str).date()
            
            if start <= game_date <= end:
                return week
                
        logger.warning(f"Game date {game_date} not found in NFL schedule")
        return None
        
    except Exception as e:
        logger.error(f"Error assigning week for {commence_time_str}: {str(e)}")
        return None

def is_game_day() -> bool:
    """Check if there are any NFL games scheduled for today."""
    try:
        now = datetime.now(pytz.UTC)
        current_week = assign_week(now.isoformat())
        
        if current_week is None:
            return False
            
        today = now.date()
        start_str, end_str = NFL_WEEKS[current_week]
        week_start = datetime.fromisoformat(start_str).date()
        week_end = datetime.fromisoformat(end_str).date()
        
        return week_start <= today <= week_end
        
    except Exception as e:
        logger.error(f"Error checking game day: {str(e)}")
        return False

def get_current_week() -> Optional[int]:
    """Get the current NFL week number."""
    now = datetime.now(pytz.UTC)
    return assign_week(now.isoformat())