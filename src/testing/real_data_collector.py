"""
SICAR Real Data Collector - Phase 7-8
Comprehensive data collection system for 2020-2025 backtesting with 100% real market data
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
import yfinance as yf
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
import json
import logging
from pathlib import Path
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

class DataSource(Enum):
    YAHOO_FINANCE = "yahoo_finance"
    BINANCE = "binance"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    TWELVE_DATA = "twelve_data"

class DataQuality(Enum):
    EXCELLENT = "excellent"  # >99% completeness, <0.1% gaps
    GOOD = "good"           # >95% completeness, <1% gaps
    FAIR = "fair"           # >90% completeness, <5% gaps
    POOR = "poor"           # <90% completeness, >5% gaps

class AssetType(Enum):
    CRYPTO = "crypto"
    INDICES = "indices"
    FOREX = "forex"
    COMMODITIES = "commodities"

@dataclass
class DataPoint:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: DataSource
    symbol: str
    asset_type: AssetType
    quality_score: float = 1.0

@dataclass
class DataValidation:
    symbol: str
    start_date: datetime
    end_date: datetime
    total_points: int
    missing_points: int
    completeness: float
    quality: DataQuality
    gaps: List[Tuple[datetime, datetime]] = field(default_factory=list)
    anomalies: List[Dict] = field(default_factory=list)
    source_breakdown: Dict[DataSource, int] = field(default_factory=dict)

@dataclass
class CollectionStats:
    symbols_collected: int = 0
    total_data_points: int = 0
    avg_quality_score: float = 0.0
    collection_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    source_stats: Dict[DataSource, Dict] = field(default_factory=dict)

class RealDataCollector:
    """
    Comprehensive real data collector for SICAR backtesting
    Ensures 100% real market data with multiple source validation
    """
    
    def __init__(self, data_dir: str = "data/real_market_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Database for data storage and validation
        self.db_path = self.data_dir / "market_data.db"
        self.init_database()
        
        # Data sources configuration
        self.sources = {
            DataSource.YAHOO_FINANCE: self._collect_yahoo_data,
            DataSource.BINANCE: self._collect_binance_data,
            DataSource.ALPHA_VANTAGE: self._collect_alpha_vantage_data,
        }
        
        # Symbol mappings for different sources
        self.symbol_mappings = {
            # Crypto symbols
            "BTCUSDT": {
                DataSource.YAHOO_FINANCE: "BTC-USD",
                DataSource.BINANCE: "BTCUSDT",
            },
            "ETHUSDT": {
                DataSource.YAHOO_FINANCE: "ETH-USD",
                DataSource.BINANCE: "ETHUSDT",
            },
            # Indices symbols
            "NAS100": {
                DataSource.YAHOO_FINANCE: "^NDX",
            },
            "SPX500": {
                DataSource.YAHOO_FINANCE: "^GSPC",
            },
            "US30": {
                DataSource.YAHOO_FINANCE: "^DJI",
            },
        }
        
        # Quality thresholds
        self.quality_thresholds = {
            DataQuality.EXCELLENT: 0.99,
            DataQuality.GOOD: 0.95,
            DataQuality.FAIR: 0.90,
            DataQuality.POOR: 0.0,
        }
        
        self.logger = self._setup_logging()
        self.stats = CollectionStats()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for data collection"""
        logger = logging.getLogger("RealDataCollector")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler(self.data_dir / "collection.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def init_database(self):
        """Initialize SQLite database for data storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    source TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    quality_score REAL DEFAULT 1.0,
                    data_hash TEXT,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    UNIQUE(symbol, timestamp, source)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_validation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    start_date INTEGER NOT NULL,
                    end_date INTEGER NOT NULL,
                    total_points INTEGER NOT NULL,
                    missing_points INTEGER NOT NULL,
                    completeness REAL NOT NULL,
                    quality TEXT NOT NULL,
                    gaps TEXT,
                    anomalies TEXT,
                    source_breakdown TEXT,
                    validated_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON market_data(symbol, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON market_data(source)")
            
    async def collect_comprehensive_data(
        self,
        symbols: List[str],
        start_date: str = "2020-01-01",
        end_date: str = "2025-01-01",
        timeframe: str = "1h"
    ) -> Dict[str, DataValidation]:
        """
        Collect comprehensive market data for all symbols
        """
        start_time = time.time()
        self.logger.info(f"Starting comprehensive data collection for {len(symbols)} symbols")
        
        validations = {}
        
        for symbol in symbols:
            try:
                self.logger.info(f"Collecting data for {symbol}")
                validation = await self._collect_symbol_data(symbol, start_date, end_date, timeframe)
                validations[symbol] = validation
                self.stats.symbols_collected += 1
                
            except Exception as e:
                error_msg = f"Error collecting data for {symbol}: {str(e)}"
                self.logger.error(error_msg)
                self.stats.errors.append(error_msg)
                
        self.stats.collection_time = time.time() - start_time
        self.logger.info(f"Data collection completed in {self.stats.collection_time:.2f} seconds")
        
        return validations
        
    async def _collect_symbol_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str
    ) -> DataValidation:
        """Collect data for a single symbol from multiple sources"""
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_data = []
        source_breakdown = {}
        
        # Collect from all available sources
        for source in self.sources:
            if symbol in self.symbol_mappings and source in self.symbol_mappings[symbol]:
                try:
                    source_symbol = self.symbol_mappings[symbol][source]
                    data = await self.sources[source](source_symbol, start_date, end_date, timeframe)
                    
                    if data:
                        all_data.extend(data)
                        source_breakdown[source] = len(data)
                        self.logger.info(f"Collected {len(data)} points from {source.value} for {symbol}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to collect from {source.value} for {symbol}: {str(e)}")
                    
        # Merge and validate data
        merged_data = self._merge_multi_source_data(all_data, symbol)
        
        # Store in database
        self._store_data(merged_data)
        
        # Validate data quality
        validation = self._validate_data_quality(symbol, start_dt, end_dt, merged_data, source_breakdown)
        
        # Store validation results
        self._store_validation(validation)
        
        return validation
        
    async def _collect_yahoo_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str
    ) -> List[DataPoint]:
        """Collect data from Yahoo Finance"""
        
        try:
            # Map timeframe
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "4h": "4h", "1d": "1d"
            }
            interval = interval_map.get(timeframe, "1h")
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if df.empty:
                return []
                
            data_points = []
            asset_type = self._determine_asset_type(symbol)
            
            for timestamp, row in df.iterrows():
                if pd.notna(row['Close']):
                    data_point = DataPoint(
                        timestamp=timestamp.to_pydatetime(),
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=float(row['Volume']) if pd.notna(row['Volume']) else 0.0,
                        source=DataSource.YAHOO_FINANCE,
                        symbol=symbol,
                        asset_type=asset_type
                    )
                    data_points.append(data_point)
                    
            return data_points
            
        except Exception as e:
            self.logger.error(f"Yahoo Finance error for {symbol}: {str(e)}")
            return []
            
    async def _collect_binance_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str
    ) -> List[DataPoint]:
        """Collect data from Binance"""
        
        try:
            exchange = ccxt.binance()
            
            # Map timeframe
            timeframe_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "4h": "4h", "1d": "1d"
            }
            tf = timeframe_map.get(timeframe, "1h")
            
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
            
            all_ohlcv = []
            current_ts = start_ts
            
            while current_ts < end_ts:
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, tf, current_ts, limit=1000)
                    if not ohlcv:
                        break
                        
                    all_ohlcv.extend(ohlcv)
                    current_ts = ohlcv[-1][0] + 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.logger.warning(f"Binance fetch error: {str(e)}")
                    break
                    
            data_points = []
            for ohlcv in all_ohlcv:
                if ohlcv[4] is not None:  # Close price exists
                    data_point = DataPoint(
                        timestamp=datetime.fromtimestamp(ohlcv[0] / 1000),
                        open=float(ohlcv[1]),
                        high=float(ohlcv[2]),
                        low=float(ohlcv[3]),
                        close=float(ohlcv[4]),
                        volume=float(ohlcv[5]) if ohlcv[5] else 0.0,
                        source=DataSource.BINANCE,
                        symbol=symbol,
                        asset_type=AssetType.CRYPTO
                    )
                    data_points.append(data_point)
                    
            return data_points
            
        except Exception as e:
            self.logger.error(f"Binance error for {symbol}: {str(e)}")
            return []
            
    async def _collect_alpha_vantage_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str
    ) -> List[DataPoint]:
        """Collect data from Alpha Vantage (placeholder for API key implementation)"""
        
        # This would require an Alpha Vantage API key
        # For now, return empty list
        self.logger.info(f"Alpha Vantage collection not implemented for {symbol}")
        return []
        
    def _merge_multi_source_data(self, all_data: List[DataPoint], symbol: str) -> List[DataPoint]:
        """Merge data from multiple sources with conflict resolution"""
        
        if not all_data:
            return []
            
        # Group by timestamp
        timestamp_groups = {}
        for data_point in all_data:
            ts_key = data_point.timestamp.replace(second=0, microsecond=0)
            if ts_key not in timestamp_groups:
                timestamp_groups[ts_key] = []
            timestamp_groups[ts_key].append(data_point)
            
        merged_data = []
        
        for timestamp, points in timestamp_groups.items():
            if len(points) == 1:
                merged_data.append(points[0])
            else:
                # Resolve conflicts by source priority and data quality
                best_point = self._resolve_data_conflicts(points)
                merged_data.append(best_point)
                
        # Sort by timestamp
        merged_data.sort(key=lambda x: x.timestamp)
        
        return merged_data
        
    def _resolve_data_conflicts(self, points: List[DataPoint]) -> DataPoint:
        """Resolve conflicts between data points from different sources"""
        
        # Source priority (higher is better)
        source_priority = {
            DataSource.YAHOO_FINANCE: 3,
            DataSource.BINANCE: 2,
            DataSource.ALPHA_VANTAGE: 1,
        }
        
        # Sort by priority and quality
        points.sort(key=lambda p: (source_priority.get(p.source, 0), p.quality_score), reverse=True)
        
        best_point = points[0]
        
        # If multiple high-quality sources, average the prices
        if len(points) > 1 and points[1].quality_score > 0.9:
            avg_open = np.mean([p.open for p in points[:2]])
            avg_high = np.mean([p.high for p in points[:2]])
            avg_low = np.mean([p.low for p in points[:2]])
            avg_close = np.mean([p.close for p in points[:2]])
            avg_volume = np.mean([p.volume for p in points[:2]])
            
            best_point.open = avg_open
            best_point.high = avg_high
            best_point.low = avg_low
            best_point.close = avg_close
            best_point.volume = avg_volume
            best_point.quality_score = 0.95  # High quality merged data
            
        return best_point
        
    def _validate_data_quality(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        data: List[DataPoint],
        source_breakdown: Dict[DataSource, int]
    ) -> DataValidation:
        """Validate data quality and completeness"""
        
        if not data:
            return DataValidation(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                total_points=0,
                missing_points=0,
                completeness=0.0,
                quality=DataQuality.POOR,
                source_breakdown=source_breakdown
            )
            
        # Calculate expected data points (assuming 1-hour timeframe)
        total_hours = int((end_date - start_date).total_seconds() / 3600)
        actual_points = len(data)
        missing_points = max(0, total_hours - actual_points)
        completeness = actual_points / total_hours if total_hours > 0 else 0.0
        
        # Determine quality level
        quality = DataQuality.POOR
        for qual, threshold in self.quality_thresholds.items():
            if completeness >= threshold:
                quality = qual
                break
                
        # Find gaps in data
        gaps = self._find_data_gaps(data)
        
        # Detect anomalies
        anomalies = self._detect_anomalies(data)
        
        return DataValidation(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            total_points=actual_points,
            missing_points=missing_points,
            completeness=completeness,
            quality=quality,
            gaps=gaps,
            anomalies=anomalies,
            source_breakdown=source_breakdown
        )
        
    def _find_data_gaps(self, data: List[DataPoint]) -> List[Tuple[datetime, datetime]]:
        """Find gaps in the data timeline"""
        
        if len(data) < 2:
            return []
            
        gaps = []
        expected_interval = timedelta(hours=1)  # Assuming 1-hour data
        
        for i in range(1, len(data)):
            time_diff = data[i].timestamp - data[i-1].timestamp
            if time_diff > expected_interval * 2:  # Gap larger than 2 intervals
                gaps.append((data[i-1].timestamp, data[i].timestamp))
                
        return gaps
        
    def _detect_anomalies(self, data: List[DataPoint]) -> List[Dict]:
        """Detect price anomalies in the data"""
        
        if len(data) < 10:
            return []
            
        anomalies = []
        prices = [d.close for d in data]
        
        # Calculate rolling statistics
        df = pd.DataFrame({'price': prices, 'timestamp': [d.timestamp for d in data]})
        df['rolling_mean'] = df['price'].rolling(window=24).mean()  # 24-hour rolling mean
        df['rolling_std'] = df['price'].rolling(window=24).std()
        
        # Detect outliers (price > 3 standard deviations from mean)
        for i, row in df.iterrows():
            if pd.notna(row['rolling_std']) and row['rolling_std'] > 0:
                z_score = abs(row['price'] - row['rolling_mean']) / row['rolling_std']
                if z_score > 3:
                    anomalies.append({
                        'timestamp': row['timestamp'],
                        'price': row['price'],
                        'z_score': z_score,
                        'type': 'price_outlier'
                    })
                    
        return anomalies
        
    def _determine_asset_type(self, symbol: str) -> AssetType:
        """Determine asset type based on symbol"""
        
        crypto_indicators = ['BTC', 'ETH', 'USDT', 'USD']
        indices_indicators = ['NDX', 'GSPC', 'DJI', 'NAS', 'SPX', 'US30']
        
        symbol_upper = symbol.upper()
        
        if any(indicator in symbol_upper for indicator in crypto_indicators):
            return AssetType.CRYPTO
        elif any(indicator in symbol_upper for indicator in indices_indicators):
            return AssetType.INDICES
        else:
            return AssetType.FOREX
            
    def _store_data(self, data: List[DataPoint]):
        """Store data points in database"""
        
        if not data:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            for point in data:
                # Create data hash for integrity
                data_str = f"{point.timestamp}{point.open}{point.high}{point.low}{point.close}{point.volume}"
                data_hash = hashlib.md5(data_str.encode()).hexdigest()
                
                conn.execute("""
                    INSERT OR REPLACE INTO market_data 
                    (symbol, timestamp, open, high, low, close, volume, source, asset_type, quality_score, data_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    point.symbol,
                    int(point.timestamp.timestamp()),
                    point.open,
                    point.high,
                    point.low,
                    point.close,
                    point.volume,
                    point.source.value,
                    point.asset_type.value,
                    point.quality_score,
                    data_hash
                ))
                
        self.stats.total_data_points += len(data)
        
    def _store_validation(self, validation: DataValidation):
        """Store validation results in database"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO data_validation 
                (symbol, start_date, end_date, total_points, missing_points, completeness, quality, gaps, anomalies, source_breakdown)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                validation.symbol,
                int(validation.start_date.timestamp()),
                int(validation.end_date.timestamp()),
                validation.total_points,
                validation.missing_points,
                validation.completeness,
                validation.quality.value,
                json.dumps([(g[0].isoformat(), g[1].isoformat()) for g in validation.gaps]),
                json.dumps(validation.anomalies, default=str),
                json.dumps({k.value: v for k, v in validation.source_breakdown.items()})
            ))
            
    def get_data_summary(self) -> Dict[str, Any]:
        """Get comprehensive data collection summary"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Get basic statistics
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT symbol) as unique_symbols,
                    COUNT(*) as total_data_points,
                    AVG(quality_score) as avg_quality,
                    MIN(timestamp) as earliest_data,
                    MAX(timestamp) as latest_data
                FROM market_data
            """)
            basic_stats = cursor.fetchone()
            
            # Get quality distribution
            cursor = conn.execute("""
                SELECT quality, COUNT(*) as count
                FROM data_validation
                GROUP BY quality
            """)
            quality_dist = dict(cursor.fetchall())
            
            # Get source statistics
            cursor = conn.execute("""
                SELECT source, COUNT(*) as count, AVG(quality_score) as avg_quality
                FROM market_data
                GROUP BY source
            """)
            source_stats = {row[0]: {'count': row[1], 'avg_quality': row[2]} for row in cursor.fetchall()}
            
        return {
            'basic_statistics': {
                'unique_symbols': basic_stats[0] if basic_stats[0] else 0,
                'total_data_points': basic_stats[1] if basic_stats[1] else 0,
                'average_quality': basic_stats[2] if basic_stats[2] else 0.0,
                'earliest_data': datetime.fromtimestamp(basic_stats[3]).isoformat() if basic_stats[3] else None,
                'latest_data': datetime.fromtimestamp(basic_stats[4]).isoformat() if basic_stats[4] else None,
            },
            'quality_distribution': quality_dist,
            'source_statistics': source_stats,
            'collection_stats': {
                'symbols_collected': self.stats.symbols_collected,
                'collection_time': self.stats.collection_time,
                'errors': self.stats.errors
            }
        }
        
    def export_data_to_csv(self, symbol: str, output_path: str):
        """Export symbol data to CSV for external analysis"""
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("""
                SELECT timestamp, open, high, low, close, volume, source, quality_score
                FROM market_data
                WHERE symbol = ?
                ORDER BY timestamp
            """, conn, params=(symbol,))
            
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.to_csv(output_path, index=False)
            self.logger.info(f"Exported {len(df)} data points for {symbol} to {output_path}")
        else:
            self.logger.warning(f"No data found for symbol {symbol}")

# Demo and testing functions
async def demo_real_data_collection():
    """Demonstrate comprehensive real data collection"""
    
    print("🔄 SICAR Real Data Collector - Phase 7-8 Demo")
    print("=" * 60)
    
    # Initialize collector
    collector = RealDataCollector("data/phase7_8_real_data")
    
    # Define symbols for comprehensive testing
    test_symbols = [
        "BTCUSDT",  # Crypto
        "ETHUSDT",  # Crypto
        "NAS100",   # Index
        "SPX500",   # Index
        "US30",     # Index
    ]
    
    print(f"📊 Collecting real market data for {len(test_symbols)} symbols")
    print(f"📅 Period: 2020-2025 (5 years of data)")
    print(f"⏱️  Timeframe: 1-hour intervals")
    print()
    
    # Collect comprehensive data
    validations = await collector.collect_comprehensive_data(
        symbols=test_symbols,
        start_date="2020-01-01",
        end_date="2025-01-01",
        timeframe="1h"
    )
    
    print("📈 Data Collection Results:")
    print("-" * 40)
    
    for symbol, validation in validations.items():
        print(f"Symbol: {symbol}")
        print(f"  📊 Data Points: {validation.total_points:,}")
        print(f"  ✅ Completeness: {validation.completeness:.2%}")
        print(f"  🎯 Quality: {validation.quality.value}")
        print(f"  📉 Missing Points: {validation.missing_points:,}")
        print(f"  🔍 Data Gaps: {len(validation.gaps)}")
        print(f"  ⚠️  Anomalies: {len(validation.anomalies)}")
        print(f"  📡 Sources: {list(validation.source_breakdown.keys())}")
        print()
        
    # Get comprehensive summary
    summary = collector.get_data_summary()
    
    print("📊 Overall Collection Summary:")
    print("-" * 40)
    print(f"Total Symbols: {summary['basic_statistics']['unique_symbols']}")
    print(f"Total Data Points: {summary['basic_statistics']['total_data_points']:,}")
    print(f"Average Quality: {summary['basic_statistics']['average_quality']:.3f}")
    print(f"Collection Time: {summary['collection_stats']['collection_time']:.2f} seconds")
    print()
    
    print("🎯 Quality Distribution:")
    for quality, count in summary['quality_distribution'].items():
        print(f"  {quality}: {count} symbols")
    print()
    
    print("📡 Source Statistics:")
    for source, stats in summary['source_statistics'].items():
        print(f"  {source}: {stats['count']:,} points (avg quality: {stats['avg_quality']:.3f})")
    print()
    
    # Export sample data
    if validations:
        sample_symbol = list(validations.keys())[0]
        export_path = f"data/phase7_8_real_data/{sample_symbol}_sample.csv"
        collector.export_data_to_csv(sample_symbol, export_path)
        print(f"📁 Sample data exported to: {export_path}")
    
    print("✅ Real data collection demonstration completed!")
    return collector, validations, summary

if __name__ == "__main__":
    asyncio.run(demo_real_data_collection())