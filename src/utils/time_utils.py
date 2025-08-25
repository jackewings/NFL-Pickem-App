from datetime import datetime
import pytz
from typing import Optional
import logging

logger = logging.getLogger(__name__)

CENTRAL_TZ = pytz.timezone('America/Chicago')
UTC_TZ = pytz.UTC

def get_current_time_ct() -> datetime:
    """Get current time in Central Time."""
    now = datetime.now(UTC_TZ)
    return now.astimezone(CENTRAL_TZ)

def format_timestamp_ct(dt: datetime) -> str:
    """Format datetime to ISO format string in Central Time."""
    if dt.tzinfo is None:
        dt = UTC_TZ.localize(dt)
    ct_time = dt.astimezone(CENTRAL_TZ)
    return ct_time.isoformat()

def parse_utc_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse UTC timestamp string to datetime object.
    Handles API's 'Z' format and ISO format strings.
    """
    try:
        clean_ts = timestamp_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(clean_ts)
        
        if dt.tzinfo is None:
            dt = UTC_TZ.localize(dt)
            
        return dt
    except Exception as e:
        logger.error(f"Error parsing timestamp {timestamp_str}: {str(e)}")
        return None

def format_display_time(dt: datetime) -> str:
    """Format datetime for display in app (e.g., '2025-08-21 11:30 AM CT')"""
    if dt.tzinfo is None:
        dt = UTC_TZ.localize(dt)
    ct_time = dt.astimezone(CENTRAL_TZ)
    return ct_time.strftime('%Y-%m-%d %I:%M %p CT')

def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """Check if two datetimes are on the same day in Central Time."""
    if dt1.tzinfo is None:
        dt1 = UTC_TZ.localize(dt1)
    if dt2.tzinfo is None:
        dt2 = UTC_TZ.localize(dt2)
        
    ct1 = dt1.astimezone(CENTRAL_TZ)
    ct2 = dt2.astimezone(CENTRAL_TZ)
    return ct1.date() == ct2.date()