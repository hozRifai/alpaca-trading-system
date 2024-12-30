import asyncio
import asyncpg
import pandas as pd

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .polygon_client import PolygonClient
from .utils import get_date_range, validate_timeframe, format_market_data, calculate_technical_indicators

app = FastAPI(title="Market Data Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

polygon_client = PolygonClient()
db_pool = None

async def connect_with_retry(retries=5, delay=5):
    """Connect to the database with retries"""
    for attempt in range(retries):
        try:
            pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=5,
                max_size=20
            )
            print(f"Successfully connected to database on attempt {attempt + 1}")
            return pool
        except Exception as e:
            if attempt == retries - 1:  # Last attempt
                print(f"Failed to connect to database after {retries} attempts")
                raise  # Re-raise the last exception
            print(f"Database connection attempt {attempt + 1} failed. Retrying in {delay} seconds...")
            print(f"Error: {str(e)}")
            await asyncio.sleep(delay)

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await connect_with_retry()
    await initialize_database()

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()


async def initialize_database():
    """Initialize database tables"""
    async with db_pool.acquire() as conn:
        # Create market data table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                symbol TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume BIGINT NOT NULL
            );
        ''')
        
        # Create hypertable
        try:
            await conn.execute('''
                SELECT create_hypertable('market_data', 'timestamp', 
                    chunk_time_interval => INTERVAL '1 day',
                    if_not_exists => TRUE);
            ''')
        except Exception as e:
            print(f"Note: Hypertable might already exist: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/market-data/{symbol}")
async def get_market_data(
    symbol: str,
    timeframe: str = "10",
    days: int = 30
) -> dict:
    """Get market data for a symbol"""
    if not validate_timeframe(timeframe):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe. Must be one of: 1, 5, 10, 15, 30"
        )

    start_date, end_date = get_date_range(days)
    
    # First try to get data from database
    async with db_pool.acquire() as conn:
        records = await conn.fetch('''
            SELECT * FROM market_data 
            WHERE symbol = $1 
            AND timestamp BETWEEN $2 AND $3 
            ORDER BY timestamp ASC
        ''', symbol, start_date, end_date)
        
        if not records:
            # If no data in database, fetch from Polygon
            data = await polygon_client.get_market_data(
                symbol=symbol,
                timespan=timeframe,
                from_date=start_date,
                to_date=end_date
            )
            
            if not data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data found for symbol {symbol}"
                )
                
            # Store in database
            await conn.executemany('''
                INSERT INTO market_data (symbol, timestamp, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (symbol, timestamp) DO UPDATE 
                SET open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume
            ''', [(
                symbol,
                record['timestamp'],
                record['open'],
                record['high'],
                record['low'],
                record['close'],
                record['volume']
            ) for record in data])
            
            df = format_market_data(data)
        else:
            # Convert database records to DataFrame
            df = pd.DataFrame(records, columns=['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df.set_index('timestamp', inplace=True)
        
        # Calculate technical indicators
        df = calculate_technical_indicators(df)
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": df.reset_index().to_dict(orient='records')
        }

@app.get("/latest-price/{symbol}")
async def get_latest_price(symbol: str) -> dict:
    """Get latest price for a symbol"""
    async with db_pool.acquire() as conn:
        record = await conn.fetchrow('''
            SELECT close, timestamp 
            FROM market_data 
            WHERE symbol = $1 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', symbol)
        
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for symbol {symbol}"
            )
            
        return {
            "symbol": symbol,
            "price": record['close'],
            "timestamp": record['timestamp'].isoformat()
        }
