# app/data_models.py
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional

@dataclass
class Attraction:
    """Standardized model for a location/activity."""
    id: int
    name: str
    latitude: float
    longitude: float
    rating: float             # e.g., 4.5
    review_count: int
    open_time: int            # Minutes from midnight (e.g., 9:00 = 540)
    close_time: int           # Minutes from midnight (e.g., 17:00 = 1020)
    avg_visit_duration: int   # In minutes
    price_level: int          # 1 to 4 ($ to $$$$)
    themes: List[str]         # e.g., ['historical', 'culture', 'museum']
    sentiment_score: float    # -1.0 (Negative) to 1.0 (Positive)
    
@dataclass
class ItineraryRequest:
    """User input model for the planning request."""
    city: str
    start_date: str           # YYYY-MM-DD
    end_date: str             # YYYY-MM-DD
    budget: int               # 1 to 4
    preferences: List[str]    # e.g., ['historical', 'food', 'family-friendly']
    daily_start_hour: int = 9  # 9 AM
    daily_end_hour: int = 21   # 9 PM
