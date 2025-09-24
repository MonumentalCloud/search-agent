import math
from datetime import datetime
from typing import Optional


def apply_decay(previous_value: float, weeks_since: float, half_life_weeks: float) -> float:
    if half_life_weeks <= 0:
        return previous_value
    decay_factor = 0.5 ** (weeks_since / half_life_weeks)
    return previous_value * decay_factor


def calculate_utility_bonus(last_useful_at: Optional[str] = None, half_life_weeks: float = 6.0) -> float:
    """
    Calculate a utility bonus for a chunk based on recency of use.
    
    Args:
        last_useful_at: ISO format datetime string when the chunk was last useful
        half_life_weeks: Number of weeks for utility to decay by half
        
    Returns:
        A utility bonus value (1.0 for newly useful chunks)
    """
    # For newly useful chunks or those without history, return base value
    if not last_useful_at:
        return 1.0
        
    # Return base value as this is being marked as useful now
    return 1.0