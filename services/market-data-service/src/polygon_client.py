import aiohttp
import pandas as pd

from .config import settings
from typing import Optional, List, Dict

class PolygonClient:
    def __init__(self):
        self.base_url = settings.POLYGON_BASE_URL
        self.api_key = settings.POLYGON_API_KEY
        self.request_limit = settings.POLYGON_REQUEST_LIMIT

    @staticmethod
    def is_valid_trading_time(row) -> bool:
        """Check if the timestamp is within valid trading hours (9:30 AM - 4:00 PM ET)"""
        time = ":".join(str(row['timestamp']).split(" ")[1].split(":")[:2])
        time_range = ("09:30", "15:59")
        if time_range[1] < time_range[0]:
            return time >= time_range[0] or time <= time_range[1]
        return time_range[0] <= time <= time_range[1]

    async def fetch_and_process_market_data(self, session: aiohttp.ClientSession, url: str) -> Optional[List[Dict]]:
        """Fetch and process market data from Polygon API"""
        try:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    print(f"Error fetching data: {response.status}")
                    return None
                    
                response_json = await response.json()
                if 'results' in response_json:
                    # Convert to DataFrame for easier processing
                    df = pd.DataFrame([{
                        'timestamp': pd.Timestamp(row['t'], unit='ms', tz='UTC'),
                        'open': row['o'],
                        'close': row['c'],
                        'high': row['h'],
                        'low': row['l'],
                        'volume': row['v']
                    } for row in response_json['results']])

                    if df.empty:
                        return None

                    # Convert timezone and process data
                    df['timestamp'] = df['timestamp'].dt.tz_convert("US/Eastern")
                    df['close'] = df['close'].map("{:.4f}".format).astype(float)
                    
                    # Filter for valid trading hours
                    df['isValidRecord'] = df.apply(self.is_valid_trading_time, axis=1)
                    df = df[df['isValidRecord']].drop('isValidRecord', axis=1)

                    if df.empty:
                        return None

                    return df.to_dict('records')
                return None
        except Exception as e:
            print(f"Error processing market data: {e}")
            return None

    def build_polygon_url(self, symbol: str, timespan: str, from_date: str, to_date: str) -> str:
        """Build Polygon API URL"""
        return (
            f"{self.base_url}/aggs/ticker/{symbol}/range/{timespan}/minute/"
            f"{from_date}/{to_date}?adjusted=true&limit={self.request_limit}"
            f"&apiKey={self.api_key}"
        )

    async def get_market_data(
        self, 
        symbol: str,
        timespan: str = "10",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Get market data for a symbol"""
        # Set default dates if not provided
        if not from_date:
            from_date = (pd.Timestamp.now() - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = pd.Timestamp.now().strftime('%Y-%m-%d')

        # Build URL and fetch data
        url = self.build_polygon_url(symbol, timespan, from_date, to_date)
        
        async with aiohttp.ClientSession() as session:
            data = await self.fetch_and_process_market_data(session, url)
            if not data:
                print(f"No valid data found for {symbol} between {from_date} and {to_date}")
                return None
            return data