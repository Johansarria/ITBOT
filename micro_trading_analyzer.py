#!/usr/bin/env python3
"""
Análisis de mercado para nuevas posiciones micro
- Evalúa oportunidades en símbolos permitidos
- Aplica límites estrictos de micro-trading ($0.75)
- Considera balance disponible y riesgo
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from binance import Client
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import requests

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MicroTradingAnalyzer:
    def __init__(self):
        self.client = Client(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_SECRET_KEY')
        )
        
        # Configuración micro-trading
        self.MICRO_MAX_USDT = 0.75  # Límite máximo por operación
        self.MIN_LEVERAGE = 5       # Apalancamiento mínimo
        self.MAX_LEVERAGE = 10      # Apalancamiento máximo
        
        # Símbolos permitidos para micro-trading
        self.ALLOWED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        # Filtros de calidad
        self.MIN_24H_VOLUME = 100000000  # $100M volumen mínimo
        self.MAX_SPREAD_PCT = 0.1        # 0.1% spread máximo
        self.MIN_VOLATILITY = 0.02       # 2% volatilidad mínima
        self.MAX_VOLATILITY = 0.08       # 8% volatilidad máxima
        
    async def get_account_status(self) -> Dict:
        """Obtener estado actual de cuenta"""
        try:
            account_info = self.client.futures_account()
            
            return {
                'total_balance': float(account_info['totalWalletBalance']),
                'available_balance': float(account_info['availableBalance']),
                'unrealized_pnl': float(account_info['totalUnrealizedProfit']),
                'margin_ratio': float(account_info.get('totalMaintMargin', 0))
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado: {e}")
            return {}
    
    async def get_current_positions(self) -> List[str]:
        """Obtener símbolos con posiciones actuales"""
        try:
            positions = self.client.futures_position_information()
            active_symbols = []
            
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    active_symbols.append(pos['symbol'])
            
            return active_symbols
        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return []
    
    async def analyze_market_conditions(self, symbol: str) -> Dict:
        """Analizar condiciones de mercado para un símbolo"""
        try:
            # Obtener datos de 24h - usando futures methods
            ticker_24h = self.client.futures_24hr_ticker(symbol=symbol)
            
            # Obtener orderbook para spread - usando futures methods
            orderbook = self.client.futures_order_book(symbol=symbol, limit=5)
            
            # Calcular métricas
            price = float(ticker_24h['lastPrice'])
            volume_24h = float(ticker_24h['quoteVolume'])
            price_change_pct = float(ticker_24h['priceChangePercent'])
            
            # Calcular spread
            best_bid = float(orderbook['bids'][0][0])
            best_ask = float(orderbook['asks'][0][0])
            spread_pct = ((best_ask - best_bid) / price) * 100
            
            # Volatilidad (aproximada por rango 24h)
            high_24h = float(ticker_24h['highPrice'])
            low_24h = float(ticker_24h['lowPrice'])
            volatility = ((high_24h - low_24h) / price) * 100
            
            return {
                'symbol': symbol,
                'price': price,
                'volume_24h': volume_24h,
                'price_change_pct': price_change_pct,
                'spread_pct': spread_pct,
                'volatility_pct': volatility / 100,  # Como decimal
                'high_24h': high_24h,
                'low_24h': low_24h,
                'analysis_time': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analizando {symbol}: {e}")
            return {}
    
    async def get_technical_signals(self, symbol: str) -> Dict:
        """Obtener señales técnicas básicas"""
        try:
            # Obtener datos de velas recientes - usando futures methods
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=Client.KLINE_INTERVAL_15MINUTE,
                limit=50
            )
            
            # Convertir a DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'buy_base_volume', 
                'buy_quote_volume', 'ignore'
            ])
            
            # Convertir precios a float
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            
            # Calcular medias móviles simples
            df['sma_10'] = df['close'].rolling(10).mean()
            df['sma_20'] = df['close'].rolling(20).mean()
            
            current_price = df['close'].iloc[-1]
            sma_10 = df['sma_10'].iloc[-1]
            sma_20 = df['sma_20'].iloc[-1]
            
            # Señales básicas
            signals = {
                'price': current_price,
                'sma_10': sma_10,
                'sma_20': sma_20,
                'trend': 'BULLISH' if sma_10 > sma_20 else 'BEARISH',
                'momentum': 'POSITIVE' if current_price > sma_10 else 'NEGATIVE',
                'strength': abs(current_price - sma_10) / sma_10
            }
            
            return signals
            
        except Exception as e:
            logger.error(f"Error obteniendo señales técnicas para {symbol}: {e}")
            return {}
    
    async def calculate_position_size(self, symbol: str, available_balance: float) -> Dict:
        """Calcular tamaño de posición óptimo"""
        try:
            # Obtener info del símbolo para precisión
            exchange_info = self.client.futures_exchange_info()
            symbol_info = exchange_info['symbols']
            symbol_data = next((s for s in symbol_info if s['symbol'] == symbol), None)
            
            if not symbol_data:
                return {}
            
            # Obtener precio actual - usando futures methods
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Filtros del símbolo
            filters = {f['filterType']: f for f in symbol_data['filters']}
            
            min_qty = float(filters['LOT_SIZE']['minQty'])
            step_size = float(filters['LOT_SIZE']['stepSize'])
            min_notional = float(filters['MIN_NOTIONAL']['notional'])
            
            # Calcular con diferentes apalancamientos
            position_options = []
            
            for leverage in range(self.MIN_LEVERAGE, self.MAX_LEVERAGE + 1):
                # Máximo que podemos usar (menor entre límite micro y disponible)
                max_usdt = min(self.MICRO_MAX_USDT, available_balance * 0.9)  # 90% del disponible
                
                # Cantidad con apalancamiento
                position_value = max_usdt * leverage
                quantity = position_value / current_price
                
                # Ajustar a step size
                quantity = (quantity // step_size) * step_size
                
                # Verificar límites mínimos
                actual_notional = quantity * current_price
                
                if quantity >= min_qty and actual_notional >= min_notional:
                    position_options.append({
                        'leverage': leverage,
                        'quantity': quantity,
                        'notional_value': actual_notional,
                        'margin_required': actual_notional / leverage,
                        'risk_per_1pct': actual_notional * 0.01  # Riesgo por 1% movimiento
                    })
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'min_qty': min_qty,
                'step_size': step_size,
                'min_notional': min_notional,
                'position_options': position_options
            }
            
        except Exception as e:
            logger.error(f"Error calculando tamaño posición para {symbol}: {e}")
            return {}
    
    async def evaluate_symbol_opportunity(self, symbol: str, available_balance: float) -> Dict:
        """Evaluar oportunidad completa para un símbolo"""
        try:
            print(f"\n🔍 Analizando {symbol}...")
            
            # Análisis de mercado
            market_data = await self.analyze_market_conditions(symbol)
            if not market_data:
                return {'symbol': symbol, 'viable': False, 'reason': 'Error datos mercado'}
            
            # Señales técnicas
            technical_signals = await self.get_technical_signals(symbol)
            if not technical_signals:
                return {'symbol': symbol, 'viable': False, 'reason': 'Error señales técnicas'}
            
            # Cálculo de posición
            position_calc = await self.calculate_position_size(symbol, available_balance)
            if not position_calc or not position_calc.get('position_options'):
                return {'symbol': symbol, 'viable': False, 'reason': 'Sin opciones de posición válidas'}
            
            # Evaluación de filtros
            quality_score = 0
            quality_details = []
            
            # Volumen (peso: 25%)
            if market_data['volume_24h'] >= self.MIN_24H_VOLUME:
                quality_score += 25
                quality_details.append(f"✅ Volumen: ${market_data['volume_24h']/1e6:.1f}M")
            else:
                quality_details.append(f"❌ Volumen bajo: ${market_data['volume_24h']/1e6:.1f}M")
            
            # Spread (peso: 20%)
            if market_data['spread_pct'] <= self.MAX_SPREAD_PCT:
                quality_score += 20
                quality_details.append(f"✅ Spread: {market_data['spread_pct']:.3f}%")
            else:
                quality_details.append(f"❌ Spread alto: {market_data['spread_pct']:.3f}%")
            
            # Volatilidad (peso: 25%)
            vol = market_data['volatility_pct']
            if self.MIN_VOLATILITY <= vol <= self.MAX_VOLATILITY:
                quality_score += 25
                quality_details.append(f"✅ Volatilidad: {vol*100:.2f}%")
            else:
                quality_details.append(f"❌ Volatilidad: {vol*100:.2f}% (fuera rango)")
            
            # Señales técnicas (peso: 30%)
            tech_score = 0
            if technical_signals['trend'] == 'BULLISH' and technical_signals['momentum'] == 'POSITIVE':
                tech_score = 30
                quality_details.append("✅ Técnico: Bullish + Momentum positivo")
            elif technical_signals['trend'] == 'BULLISH':
                tech_score = 20
                quality_details.append("⚠️ Técnico: Bullish pero momentum débil")
            elif technical_signals['momentum'] == 'POSITIVE':
                tech_score = 15
                quality_details.append("⚠️ Técnico: Momentum positivo pero trend bajista")
            else:
                quality_details.append("❌ Técnico: Bearish")
            
            quality_score += tech_score
            
            # Mejor opción de posición
            best_option = max(position_calc['position_options'], 
                            key=lambda x: x['notional_value'])  # Maximizar valor pero dentro límites
            
            return {
                'symbol': symbol,
                'viable': quality_score >= 60,  # Mínimo 60% calidad
                'quality_score': quality_score,
                'quality_details': quality_details,
                'market_data': market_data,
                'technical_signals': technical_signals,
                'recommended_position': best_option,
                'analysis_time': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error evaluando {symbol}: {e}")
            return {'symbol': symbol, 'viable': False, 'reason': f'Error análisis: {e}'}
    
    async def analyze_all_opportunities(self) -> Dict:
        """Analizar todas las oportunidades disponibles"""
        print("🚀 ANÁLISIS DE OPORTUNIDADES MICRO-TRADING")
        print("="*60)
        
        # Estado de cuenta
        account = await self.get_account_status()
        current_positions = await self.get_current_positions()
        
        print(f"💰 Balance disponible: ${account.get('available_balance', 0):.2f}")
        print(f"📊 Posiciones actuales: {len(current_positions)}")
        if current_positions:
            print(f"   Símbolos activos: {', '.join(current_positions)}")
        
        # Filtrar símbolos disponibles (excluir posiciones actuales)
        available_symbols = [s for s in self.ALLOWED_SYMBOLS if s not in current_positions]
        
        print(f"\n🎯 Símbolos a analizar: {', '.join(available_symbols)}")
        print(f"💵 Límite por operación: ${self.MICRO_MAX_USDT}")
        
        # Analizar cada símbolo
        opportunities = []
        for symbol in available_symbols:
            opportunity = await self.evaluate_symbol_opportunity(
                symbol, account.get('available_balance', 0)
            )
            opportunities.append(opportunity)
        
        # Ordenar por calidad
        viable_opportunities = [op for op in opportunities if op.get('viable', False)]
        viable_opportunities.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        
        return {
            'account_status': account,
            'current_positions': current_positions,
            'available_symbols': available_symbols,
            'all_opportunities': opportunities,
            'viable_opportunities': viable_opportunities,
            'analysis_time': datetime.now()
        }

def print_detailed_analysis(analysis: Dict):
    """Mostrar análisis detallado"""
    print("\n" + "="*60)
    print("📊 RESULTADOS DEL ANÁLISIS")
    print("="*60)
    
    viable = analysis['viable_opportunities']
    
    if not viable:
        print("❌ No se encontraron oportunidades viables en este momento")
        print("\n📋 RAZONES:")
        for op in analysis['all_opportunities']:
            if not op.get('viable', False):
                reason = op.get('reason', 'Calidad insuficiente')
                print(f"   {op['symbol']}: {reason}")
        return
    
    print(f"✅ {len(viable)} oportunidad(es) viable(s) encontrada(s)")
    
    for i, op in enumerate(viable, 1):
        print(f"\n🎯 OPORTUNIDAD #{i}: {op['symbol']}")
        print(f"   Calidad: {op['quality_score']}/100")
        
        # Detalles de calidad
        for detail in op['quality_details']:
            print(f"   {detail}")
        
        # Datos de mercado
        market = op['market_data']
        print(f"\n   📈 MERCADO:")
        print(f"      Precio actual: ${market['price']:.4f}")
        print(f"      Cambio 24h: {market['price_change_pct']:.2f}%")
        print(f"      Volumen 24h: ${market['volume_24h']/1e6:.1f}M")
        print(f"      Rango 24h: ${market['low_24h']:.4f} - ${market['high_24h']:.4f}")
        
        # Señales técnicas
        tech = op['technical_signals']
        print(f"\n   🔍 TÉCNICO:")
        print(f"      Trend: {tech['trend']}")
        print(f"      Momentum: {tech['momentum']}")
        print(f"      SMA10: ${tech['sma_10']:.4f} | SMA20: ${tech['sma_20']:.4f}")
        
        # Posición recomendada
        pos = op['recommended_position']
        print(f"\n   💰 POSICIÓN RECOMENDADA:")
        print(f"      Apalancamiento: {pos['leverage']}x")
        print(f"      Cantidad: {pos['quantity']:.6f}")
        print(f"      Valor nocional: ${pos['notional_value']:.2f}")
        print(f"      Margen requerido: ${pos['margin_required']:.2f}")
        print(f"      Riesgo por 1%: ${pos['risk_per_1pct']:.2f}")

async def main():
    """Función principal"""
    analyzer = MicroTradingAnalyzer()
    
    try:
        analysis = await analyzer.analyze_all_opportunities()
        print_detailed_analysis(analysis)
        
        # Recomendación final
        viable = analysis['viable_opportunities']
        if viable:
            best = viable[0]
            print("\n" + "="*60)
            print("🎯 RECOMENDACIÓN FINAL")
            print("="*60)
            print(f"✅ Mejor oportunidad: {best['symbol']}")
            print(f"📊 Calidad: {best['quality_score']}/100")
            
            pos = best['recommended_position']
            print(f"\n💡 SUGERENCIA DE APERTURA:")
            print(f"   Símbolo: {best['symbol']}")
            print(f"   Lado: LONG (basado en análisis técnico)")
            print(f"   Cantidad: {pos['quantity']:.6f}")
            print(f"   Apalancamiento: {pos['leverage']}x")
            print(f"   Margen: ${pos['margin_required']:.2f}")
            print(f"   Stop Loss sugerido: -2% (${pos['risk_per_1pct']*2:.2f})")
            print(f"   Take Profit sugerido: +4% (${pos['risk_per_1pct']*4:.2f})")
        else:
            print("\n" + "="*60)
            print("⏸️ RECOMENDACIÓN: ESPERAR")
            print("="*60)
            print("Sin oportunidades de calidad suficiente en este momento.")
            print("Sugerencia: Revisar en 15-30 minutos.")
        
    except Exception as e:
        logger.error(f"Error en análisis: {e}")
        print(f"❌ Error durante análisis: {e}")

if __name__ == "__main__":
    asyncio.run(main())
