import pandas as pd
from pathlib import Path
from datetime import datetime
import pytz
import sys
from pathlib import Path
from src.config.settings import CURRENT_WEEK

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.core.data import nfl_data  
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
    """Update NFL spreads data from API and save results for completed games"""
    try:
        logger.info("Starting data update...")
        spreads = nfl_data.get_weekly_spreads_from_api(save_csv=True)
        if spreads:
            logger.info(f"Successfully updated spreads data at {datetime.now(pytz.UTC)}")
            logger.info(f"Updated {len(spreads)} games")
        else:
            logger.warning("No spreads data received from API")
        
        # Update results for the current week
        results = nfl_data.get_game_results(CURRENT_WEEK)
        if results:
            logger.info(f"Successfully updated results for week {CURRENT_WEEK}")
        else:
            logger.info(f"No results found for week {CURRENT_WEEK}")
        return True
    except Exception as e:
        logger.error(f"Error updating data: {str(e)}")
        return False

if __name__ == "__main__":
    success = update_spreads_and_results()
    exit(0 if success else 1)