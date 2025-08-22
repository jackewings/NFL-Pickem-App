import pytest
import pandas as pd
from src.core.scoring import calculate_scores, determine_result

@pytest.fixture
def sample_picks():
    return pd.DataFrame({
        "week": [1, 1],
        "user": ["user1", "user1"],
        "game": ["NYJ @ BUF", "KC @ DET"],
        "pick": ["BUF", "KC"]
    })

@pytest.fixture
def sample_results():
    return pd.DataFrame({
        "week": [1, 1],
        "game": ["NYJ @ BUF", "KC @ DET"],
        "covered": ["BUF", "DET"]
    })

def test_determine_result():
    assert determine_result({"covered": "BUF", "pick": "BUF"}) == "correct"
    assert determine_result({"covered": "BUF", "pick": "NYJ"}) == "incorrect"
    assert determine_result({"covered": "PUSH", "pick": "BUF"}) == "push"
    assert determine_result({"covered": None, "pick": "BUF"}) is None

def test_calculate_scores(sample_picks, sample_results):
    result = calculate_scores(sample_picks, sample_results)
    
    assert not result.weekly.empty
    assert not result.total.empty
    
    weekly = result.weekly.iloc[0]
    assert weekly["correct"] == 1
    assert weekly["total"] == 2
    assert weekly["correct_pct"] == 50.0