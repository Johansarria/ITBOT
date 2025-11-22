"""
Generador de Datos de Mercado 2025 - SICAR
Simula datos realistas de criptomonedas para octubre 2025
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
import random
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataGenerator2025:
    """Generador de datos de mercado para 2025"""
    
    def __init__(self):
        """Inicializa el generador con parámetros de mercado 2025"""
        
        # Precios base actualizados para octubre 2025
        self.base_prices = {
            'BTCUSDT': 85000.0,    # Bitcoin ha crecido significativamente
            'ETHUSDT': 4200.0,     # Ethereum también ha subido
            'ADAUSDT': 1.85,       # Cardano ha tenido un buen año
            'SOLUSDT': 180.0,      # Solana sigue fuerte
            'DOTUSDT': 12.5,       # Polkadot estable
        }
        
        # Volatilidades ajustadas para 2025 (mercado más maduro)
        self.volatilities = {
            'BTCUSDT': 0.025,      # Bitcoin menos volátil
            'ETHUSDT': 0.035,      # Ethereum moderadamente volátil
            'ADAUSDT': 0.045,      # Altcoins más volátiles
            'SOLUSDT': 0.040,
            'DOTUSDT': 0.050,
        }
        
        # Tendencias de mercado para 2025
        self.market_trends = {
            'BTCUSDT': 0.0002,     # Tendencia alcista moderada
            'ETHUSDT': 0.0003,     # Ethereum con mejor tendencia
            'ADAUSDT': 0.0001,     # Crecimiento estable
            'SOLUSDT': 0.0002,
            'DOTUSDT': 0.0001,
        }
        
        logger.info("✅ MarketDataGenerator2025 inicializado")
    
    def generate_realistic_data(self, 
                              symbols: List[str],
                              start_date: str = "2025-01-01",
                              end_date: str = "2025-10-31",
                              timeframe: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        Genera datos de mercado realistas para 2025
        """
        
        logger.info(f"🔄 Generando datos para {len(symbols)} símbolos desde {start_date} hasta {end_date}")
        
        # Crear rango de fechas
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        market_data = {}
        
        for symbol in symbols:
            if symbol not in self.base_prices:
                logger.warning(f"⚠️ Símbolo {symbol} no reconocido, usando valores por defecto")
                continue
            
            df = self._generate_symbol_data(symbol, date_range)
            market_data[symbol] = df
            
            logger.info(f"✅ Generados {len(df)} períodos para {symbol}")
        
        return market_data
    
    def _generate_symbol_data(self, symbol: str, date_range: pd.DatetimeIndex) -> pd.DataFrame:
        """Genera datos para un símbolo específico"""
        
        base_price = self.base_prices[symbol]
        volatility = self.volatilities[symbol]
        trend = self.market_trends[symbol]
        
        n_periods = len(date_range)
        
        # Generar retornos con tendencia y volatilidad
        returns = np.random.normal(trend, volatility, n_periods)
        
        # Generar precios usando walk aleatorio
        prices = [base_price]
        for i in range(n_periods):
            new_price = prices[-1] * (1 + returns[i])
            prices.append(new_price)
        
        # Crear datos OHLC
        data = []
        for i in range(n_periods):
            open_price = prices[i]
            close_price = prices[i + 1]
            
            # Generar high y low
            daily_volatility = volatility / 4
            high_factor = 1 + abs(np.random.normal(0, daily_volatility))
            low_factor = 1 - abs(np.random.normal(0, daily_volatility))
            
            high = max(open_price, close_price) * high_factor
            low = min(open_price, close_price) * low_factor
            
            # Generar volumen
            base_volume = 50000 if symbol == 'BTCUSDT' else 80000
            volume_factor = 1 + abs(returns[i]) * 5
            volume = base_volume * volume_factor * np.random.lognormal(0, 0.5)
            
            data.append({
                'timestamp': date_range[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        
        # Agregar indicadores técnicos básicos
        df = self._add_technical_indicators(df)
        
        return df
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Agrega indicadores técnicos básicos"""
        
        # SMA
        df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['sma_50'] = df['close'].rolling(window=50, min_periods=1).mean()
        
        # EMA
        df['ema_12'] = df['close'].ewm(span=12, min_periods=1).mean()
        df['ema_26'] = df['close'].ewm(span=26, min_periods=1).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / (loss + 1e-10)  # Evitar división por cero
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, min_periods=1).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20, min_periods=1).mean()
        bb_std = df['close'].rolling(window=20, min_periods=1).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        return df
    
    def save_data_to_files(self, market_data: Dict[str, pd.DataFrame], output_dir: str = "data/2025"):
        """Guarda los datos generados en archivos"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for symbol, df in market_data.items():
            file_path = output_path / f"{symbol}_2025.csv"
            df.to_csv(file_path, index=False)
            logger.info(f"💾 Datos de {symbol} guardados en {file_path}")
        
        # Guardar metadatos
        metadata = {
            'generation_date': datetime.now().isoformat(),
            'symbols': list(market_data.keys()),
            'base_prices': self.base_prices,
            'volatilities': self.volatilities,
            'market_trends': self.market_trends
        }
        
        metadata_path = output_path / "metadata_2025.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"📋 Metadatos guardados en {metadata_path}")

def test_data_generator_2025():
    """Función de prueba del generador de datos 2025"""
    
    print("🚀 Iniciando prueba del Generador de Datos 2025...")
    
    # Crear generador
    generator = MarketDataGenerator2025()
    
    # Símbolos a generar
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
    
    # Generar datos para los últimos 3 meses de 2025
    market_data = generator.generate_realistic_data(
        symbols=symbols,
        start_date="2025-08-01",
        end_date="2025-10-31",
        timeframe="1d"
    )
    
    # Mostrar estadísticas
    print(f"\n📊 Datos generados para {len(market_data)} símbolos:")
    
    for symbol, df in market_data.items():
        print(f"\n📈 {symbol}:")
        print(f"   Períodos: {len(df)}")
        print(f"   Precio inicial: ${df['close'].iloc[0]:,.2f}")
        print(f"   Precio final: ${df['close'].iloc[-1]:,.2f}")
        print(f"   Retorno total: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%")
        print(f"   Volatilidad: {df['close'].pct_change().std() * 100:.2f}%")
        print(f"   Volumen promedio: {df['volume'].mean():,.0f}")
        print(f"   RSI final: {df['rsi'].iloc[-1]:.1f}")
    
    # Guardar datos
    generator.save_data_to_files(market_data)
    
    print(f"\n✅ Prueba del Generador de Datos 2025 completada!")
    return market_data

if __name__ == "__main__":
    test_data_generator_2025()