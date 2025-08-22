import pandas as pd
from pathlib import Path
from datetime import datetime
import pytz
from . import data
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def update_spreads_and_results():
    """Update NFL spreads data from API"""
    try:
        logger.info("Starting data update...")
        spreads = data.get_weekly_spreads_from_api(save_csv=True)
        
        if spreads:
            logger.info(f"Successfully updated spreads data at {datetime.now(pytz.UTC)}")
            logger.info(f"Updated {len(spreads)} games")
            return True
        else:
            logger.warning("No spreads data received from API")
            return False
            
    except Exception as e:
        logger.error(f"Error updating data: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_spreads_and_results()
    exit(0 if success else 1)