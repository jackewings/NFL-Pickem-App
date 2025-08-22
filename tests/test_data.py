import pytest
from unittest.mock import Mock, patch
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from src.core.data import NFLData
from src.utils.time_utils import format_timestamp_ct

@pytest.fixture
def sample_api_response():
    return [
        {
            "id": "1",
            "home_team": "Buffalo Bills",
            "away_team": "New York Jets",
            "commence_time": "2025-09-08T00:20:00Z",
            "bookmakers": [
                {
                    "title": "DraftKings",
                    "markets": [
                        {
                            "outcomes": [
                                {"name": "Buffalo Bills", "point": -6.5}
                            ]
                        }
                    ]
                }
            ]
        }
    ]

@pytest.fixture
def nfl_data(tmp_path):
    """Create NFLData instance with temporary directory"""
    return NFLData(data_dir=str(tmp_path))

@pytest.fixture
def sample_spreads_df():
    return pd.DataFrame({
        "week": [1],
        "home_team": ["Buffalo Bills"],
        "away_team": ["New York Jets"],
        "commence_time": ["2025-09-08T00:20:00Z"],
        "spread": [-6.5],
        "bookmaker": ["DraftKings"],
        "game": ["New York Jets @ Buffalo Bills"],
        "last_updated": [format_timestamp_ct(datetime.now())]
    })

def test_init(tmp_path):
    """Test NFLData initialization"""
    data = NFLData(data_dir=str(tmp_path))
    assert data.data_dir == Path(tmp_path)
    assert data.spreads_file == Path(tmp_path) / "weekly_spreads.csv"
    assert data.data_dir.exists()

@patch('src.api.odds_api.OddsAPI.get_nfl_spreads')
def test_get_weekly_spreads_from_api(mock_get_spreads, nfl_data, sample_api_response):
    """Test fetching spreads from API"""
    mock_get_spreads.return_value = sample_api_response
    
    result = nfl_data.get_weekly_spreads_from_api()
    
    assert len(result) == 1
    assert result[0]["home_team"] == "Buffalo Bills"
    assert result[0]["away_team"] == "New York Jets"
    assert result[0]["spread"] == -6.5
    assert result[0]["week"] == 1

def test_save_spreads_to_csv(nfl_data, sample_spreads_df):
    """Test saving spreads to CSV"""
    spreads_list = sample_spreads_df.to_dict(orient="records")
    nfl_data._save_spreads_to_csv(spreads_list)
    
    assert nfl_data.spreads_file.exists()
    saved_df = pd.read_csv(nfl_data.spreads_file)
    assert len(saved_df) == 1
    assert saved_df.iloc[0]["home_team"] == "Buffalo Bills"

def test_get_weekly_spreads_from_cache(nfl_data, sample_spreads_df):
    """Test retrieving spreads from cache"""
    # Save test data to CSV
    sample_spreads_df.to_csv(nfl_data.spreads_file, index=False)
    
    result = nfl_data.get_weekly_spreads(week=1)
    
    assert len(result) == 1
    assert result[0]["home_team"] == "Buffalo Bills"
    assert result[0]["week"] == 1

@patch('src.api.odds_api.OddsAPI.get_nfl_spreads')
def test_get_weekly_spreads_api_fallback(mock_get_spreads, nfl_data, sample_api_response):
    """Test API fallback when cache miss"""
    mock_get_spreads.return_value = sample_api_response
    
    # No cache file exists yet
    result = nfl_data.get_weekly_spreads(week=1)
    
    assert len(result) == 1
    assert result[0]["home_team"] == "Buffalo Bills"
    mock_get_spreads.assert_called_once()

def test_error_handling(nfl_data):
    """Test error handling for invalid data"""
    # Test with invalid CSV
    nfl_data.spreads_file.write_text("invalid,csv,data")
    result = nfl_data.get_weekly_spreads(week=1)
    assert result == []
    
    # Test with empty response
    with patch('src.api.odds_api.OddsAPI.get_nfl_spreads', return_value=[]):
        result = nfl_data.get_weekly_spreads_from_api()
        assert result == []

def test_invalid_week(nfl_data, sample_spreads_df):
    """Test requesting invalid week number"""
    sample_spreads_df.to_csv(nfl_data.spreads_file, index=False)
    result = nfl_data.get_weekly_spreads(week=99)
    assert result == []

if __name__ == '__main__':
    pytest.main(['-v', __file__])