import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional

def get_date_range(days: int = 30) -> Tuple[str, str]:
    """Get from and to dates based on number of days"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

def validate_timeframe(timeframe: str) -> bool:
    """Validate if timeframe is supported"""
    return timeframe in ['1', '5', '10', '15', '30']

def format_market_data(data: list) -> Optional[pd.DataFrame]:
    """Format market data into a pandas DataFrame"""
    if not data:
        return None
        
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators for the data"""
    if df.empty:
        return df
        
    # Add EMA calculations
    df['EMA10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    return df