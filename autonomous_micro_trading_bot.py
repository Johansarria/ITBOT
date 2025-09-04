#!/usr/bin/env python3
"""
Bot Autónomo de Micro-Trading
- Monitorea oportunidades automáticamente
- Ejecuta operaciones cuando encuentra calidad suficiente
- Respeta límites estrictos de micro-trading
- Gestión automática de riesgo con SL/TP
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from binance import Client
from binance.exceptions import BinanceAPIException
import os
from typing import Dict, List, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutonomousMicroTradingBot:
    def __init__(self):
        self.client = Client(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_SECRET_KEY')
        )
        
        # Configuración del bot
        self.MICRO_MAX_USDT = 0.75         # Límite máximo por operación
        self.MIN_QUALITY_SCORE = 75        # Score mínimo para ejecutar (más estricto)
        self.MAX_DAILY_OPERATIONS = 5      # Máximo operaciones por día
        self.LEVERAGE = 10                 # Apalancamiento aumentado para alcanzar mínimos
        self.STOP_LOSS_PCT = 2.0          # Stop Loss 2%
        self.TAKE_PROFIT_PCT = 3.0        # Take Profit 3%
        self.MONITORING_INTERVAL = 300     # 5 minutos entre análisis
        self.COOLDOWN_AFTER_TRADE = 1800   # 30 min cooldown tras cada trade
        
        # Símbolos permitidos - SOLO SOLUSDT es viable con micro-capital
        self.ALLOWED_SYMBOLS = ["SOLUSDT"]  # BTC/ETH requieren más capital
        
        # Estado del bot
        self.daily_operations = 0
        self.last_trade_time = None
        self.active_analysis = False
        
        logger.info("🤖 Bot Autónomo de Micro-Trading inicializado")
    
    async def get_account_status(self) -> Dict:
        """Obtener estado de cuenta actual"""
        try:
            account_info = self.client.futures_account()
            return {
                'total_balance': float(account_info['totalWalletBalance']),
                'available_balance': float(account_info['availableBalance']),
                'unrealized_pnl': float(account_info['totalUnrealizedProfit']),
                'positions_count': len([p for p in self.client.futures_position_information() 
                                      if float(p['positionAmt']) != 0])
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado cuenta: {e}")
            return {}
    
    async def get_available_symbols(self) -> List[str]:
        """Obtener símbolos disponibles (sin posiciones activas)"""
        try:
            positions = self.client.futures_position_information()
            active_symbols = {pos['symbol'] for pos in positions if float(pos['positionAmt']) != 0}
            return [s for s in self.ALLOWED_SYMBOLS if s not in active_symbols]
        except Exception as e:
            logger.error(f"Error obteniendo símbolos disponibles: {e}")
            return []
    
    async def analyze_symbol_quality(self, symbol: str) -> Dict:
        """Análisis de calidad de un símbolo"""
        try:
            # Datos básicos
            ticker = self.client.get_ticker(symbol=symbol)
            klines = self.client.get_klines(symbol=symbol, interval='1h', limit=24)
            
            current_price = float(ticker['lastPrice'])
            price_change = float(ticker['priceChangePercent'])
            volume = float(ticker['quoteVolume'])
            
            # Volatilidad
            high_24h = float(ticker['highPrice'])
            low_24h = float(ticker['lowPrice'])
            volatility = ((high_24h - low_24h) / current_price) * 100
            
            # Tendencia
            closes = [float(k[4]) for k in klines]
            if len(closes) >= 12:
                recent_avg = sum(closes[-12:]) / 12
                older_avg = sum(closes[-24:-12]) / 12
                trend_strength = ((recent_avg - older_avg) / older_avg) * 100
                trend = "BULLISH" if trend_strength > 0.5 else "BEARISH"
            else:
                trend = "NEUTRAL"
                trend_strength = 0
            
            # Scoring
            score = 0
            reasons = []
            
            # Volumen (25 puntos)
            if volume > 2000000000:  # >$2B excelente
                score += 25
                reasons.append("✅ Volumen excelente")
            elif volume > 1000000000:  # >$1B bueno
                score += 20
                reasons.append("✅ Volumen bueno")
            elif volume > 500000000:  # >$500M aceptable
                score += 10
                reasons.append("⚠️ Volumen medio")
            else:
                reasons.append("❌ Volumen insuficiente")
            
            # Volatilidad (25 puntos)
            if 3 <= volatility <= 6:  # Rango óptimo
                score += 25
                reasons.append("✅ Volatilidad óptima")
            elif 2 <= volatility <= 8:  # Rango aceptable
                score += 15
                reasons.append("✅ Volatilidad aceptable")
            else:
                reasons.append("❌ Volatilidad fuera rango")
            
            # Movimiento precio (20 puntos)
            if -1 <= price_change <= 4:  # Movimiento controlado positivo
                score += 20
                reasons.append("✅ Movimiento controlado")
            elif -3 <= price_change <= 6:
                score += 10
                reasons.append("⚠️ Movimiento moderado")
            else:
                reasons.append("❌ Movimiento extremo")
            
            # Tendencia (30 puntos)
            if trend == "BULLISH" and trend_strength > 1:
                score += 30
                reasons.append("✅ Tendencia fuerte alcista")
            elif trend == "BULLISH":
                score += 20
                reasons.append("✅ Tendencia alcista")
            elif abs(trend_strength) < 0.5:
                score += 10
                reasons.append("⚠️ Tendencia neutral")
            else:
                reasons.append("❌ Tendencia bajista")
            
            return {
                'symbol': symbol,
                'score': score,
                'viable': score >= self.MIN_QUALITY_SCORE,
                'price': current_price,
                'change_24h': price_change,
                'volume': volume,
                'volatility': volatility,
                'trend': trend,
                'trend_strength': trend_strength,
                'reasons': reasons,
                'analysis_time': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analizando {symbol}: {e}")
            return {'symbol': symbol, 'viable': False, 'score': 0, 'reasons': [f"Error: {e}"]}
    
    async def calculate_position_params(self, symbol: str, price: float, available_balance: float) -> Dict:
        """Calcular parámetros de la posición con precisión correcta"""
        try:
            # Obtener info del símbolo para precisión
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
            
            if not symbol_info:
                return {}
            
            # Filtros del símbolo
            filters = {f['filterType']: f for f in symbol_info['filters']}
            lot_size = filters['LOT_SIZE']
            min_notional = filters['MIN_NOTIONAL']
            
            min_qty = float(lot_size['minQty'])
            step_size = float(lot_size['stepSize'])
            min_notional_value = float(min_notional['notional'])
            
            # Margen a utilizar
            margin_to_use = min(self.MICRO_MAX_USDT, available_balance * 0.8)
            
            # Valor de la posición con apalancamiento
            position_value = margin_to_use * self.LEVERAGE
            raw_quantity = position_value / price
            
            # Ajustar cantidad a step size
            adjusted_quantity = max(min_qty, (raw_quantity // step_size) * step_size)
            
            # Verificar notional mínimo
            actual_notional = adjusted_quantity * price
            if actual_notional < min_notional_value:
                # Ajustar para cumplir mínimo notional
                required_quantity = min_notional_value / price
                adjusted_quantity = max(min_qty, ((required_quantity + step_size - 1) // step_size) * step_size)
                actual_notional = adjusted_quantity * price
            
            # Recalcular margen real requerido
            actual_margin_required = actual_notional / self.LEVERAGE
            
            # Verificar que no excedemos balance disponible
            if actual_margin_required > available_balance * 0.9:
                logger.warning(f"Margen requerido ${actual_margin_required:.2f} excede disponible")
                return {}
            
            # Precios de SL y TP
            stop_loss_price = price * (1 - self.STOP_LOSS_PCT / 100)
            take_profit_price = price * (1 + self.TAKE_PROFIT_PCT / 100)
            
            # Pérdida/ganancia esperada
            max_loss = actual_notional * (self.STOP_LOSS_PCT / 100)
            target_profit = actual_notional * (self.TAKE_PROFIT_PCT / 100)
            
            return {
                'margin_required': actual_margin_required,
                'position_value': actual_notional,
                'quantity': adjusted_quantity,
                'leverage': self.LEVERAGE,
                'stop_loss_price': stop_loss_price,
                'take_profit_price': take_profit_price,
                'max_loss': max_loss,
                'target_profit': target_profit,
                'risk_reward_ratio': target_profit / max_loss,
                'min_notional_met': actual_notional >= min_notional_value
            }
            
        except Exception as e:
            logger.error(f"Error calculando posición para {symbol}: {e}")
            return {}
    
    def get_quantity_precision(self, symbol: str) -> int:
        """Obtener precisión de cantidad para un símbolo"""
        try:
            exchange_info = self.client.futures_exchange_info()
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
            if symbol_info:
                return symbol_info['quantityPrecision']
            return 6  # Default fallback
        except:
            return 6  # Default fallback
    
    async def execute_trade(self, symbol: str, analysis: Dict, position_params: Dict) -> bool:
        """Ejecutar operación completa con SL/TP"""
        try:
            logger.info(f"🚀 Ejecutando trade en {symbol}")
            
            # 1. Configurar apalancamiento
            self.client.futures_change_leverage(symbol=symbol, leverage=self.LEVERAGE)
            logger.info(f"⚙️ Apalancamiento configurado: {self.LEVERAGE}x")
            
            # 2. Orden principal LONG
            quantity_str = f"{position_params['quantity']:.{self.get_quantity_precision(symbol)}f}"
            main_order = self.client.futures_create_order(
                symbol=symbol,
                side='BUY',
                type='MARKET',
                quantity=quantity_str
            )
            
            logger.info(f"✅ Orden principal ejecutada: {main_order['orderId']}")
            
            # Esperar confirmación
            await asyncio.sleep(2)
            
            # 3. Configurar Stop Loss
            sl_order = self.client.futures_create_order(
                symbol=symbol,
                side='SELL',
                type='STOP_MARKET',
                quantity=quantity_str,
                stopPrice=f"{position_params['stop_loss_price']:.4f}",
                workingType='MARK_PRICE'
            )
            
            logger.info(f"🛡️ Stop Loss configurado: ${position_params['stop_loss_price']:.4f}")
            
            # 4. Configurar Take Profit
            tp_order = self.client.futures_create_order(
                symbol=symbol,
                side='SELL',
                type='TAKE_PROFIT_MARKET',
                quantity=quantity_str,
                stopPrice=f"{position_params['take_profit_price']:.4f}",
                workingType='CONTRACT_PRICE'
            )
            
            logger.info(f"🎯 Take Profit configurado: ${position_params['take_profit_price']:.4f}")
            
            # Actualizar estado del bot
            self.daily_operations += 1
            self.last_trade_time = datetime.now()
            
            # Log completo de la operación
            logger.info(f"📊 TRADE EJECUTADO EXITOSAMENTE:")
            logger.info(f"   Símbolo: {symbol}")
            logger.info(f"   Precio entrada: ${analysis['price']:.4f}")
            logger.info(f"   Cantidad: {position_params['quantity']:.6f}")
            logger.info(f"   Valor posición: ${position_params['position_value']:.2f}")
            logger.info(f"   Margen usado: ${position_params['margin_required']:.2f}")
            logger.info(f"   Pérdida máxima: ${position_params['max_loss']:.2f}")
            logger.info(f"   Ganancia objetivo: ${position_params['target_profit']:.2f}")
            logger.info(f"   Ratio R/R: 1:{position_params['risk_reward_ratio']:.2f}")
            
            return True
            
        except BinanceAPIException as e:
            logger.error(f"❌ Error API ejecutando trade en {symbol}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error inesperado ejecutando trade en {symbol}: {e}")
            return False
    
    async def should_trade_now(self) -> bool:
        """Verificar si es momento apropiado para operar"""
        # Verificar límite diario
        if self.daily_operations >= self.MAX_DAILY_OPERATIONS:
            logger.info(f"⏸️ Límite diario alcanzado: {self.daily_operations}/{self.MAX_DAILY_OPERATIONS}")
            return False
        
        # Verificar cooldown
        if self.last_trade_time:
            time_since_last = (datetime.now() - self.last_trade_time).total_seconds()
            if time_since_last < self.COOLDOWN_AFTER_TRADE:
                remaining = self.COOLDOWN_AFTER_TRADE - time_since_last
                logger.info(f"⏰ En cooldown: {remaining/60:.1f} min restantes")
                return False
        
        return True
    
    async def find_and_execute_opportunity(self):
        """Buscar y ejecutar oportunidades automáticamente"""
        if self.active_analysis:
            logger.info("⏳ Análisis ya en curso, saltando ciclo")
            return
        
        self.active_analysis = True
        
        try:
            # Verificar si debemos operar
            if not await self.should_trade_now():
                return
            
            # Estado de cuenta
            account = await self.get_account_status()
            if not account or account['available_balance'] < self.MICRO_MAX_USDT:
                logger.info(f"💰 Balance insuficiente: ${account.get('available_balance', 0):.2f}")
                return
            
            # Símbolos disponibles
            available_symbols = await self.get_available_symbols()
            if not available_symbols:
                logger.info("📊 No hay símbolos disponibles para nuevas posiciones")
                return
            
            logger.info(f"🔍 Analizando {len(available_symbols)} símbolos: {', '.join(available_symbols)}")
            
            # Analizar cada símbolo
            best_opportunity = None
            best_score = 0
            
            for symbol in available_symbols:
                analysis = await self.analyze_symbol_quality(symbol)
                
                logger.info(f"📊 {symbol}: Score {analysis['score']}/{self.MIN_QUALITY_SCORE}")
                for reason in analysis['reasons'][:3]:  # Solo primeras 3 razones
                    logger.info(f"   {reason}")
                
                if analysis['viable'] and analysis['score'] > best_score:
                    best_opportunity = analysis
                    best_score = analysis['score']
            
            # Ejecutar si encontramos buena oportunidad
            if best_opportunity:
                symbol = best_opportunity['symbol']
                logger.info(f"🎯 MEJOR OPORTUNIDAD: {symbol} (Score: {best_score})")
                
                # Calcular posición
                position_params = await self.calculate_position_params(
                    symbol, 
                    best_opportunity['price'],
                    account['available_balance']
                )
                
                if position_params:
                    logger.info(f"💡 Ejecutando trade automático en {symbol}")
                    success = await self.execute_trade(symbol, best_opportunity, position_params)
                    
                    if success:
                        logger.info(f"✅ Trade ejecutado exitosamente en {symbol}")
                    else:
                        logger.error(f"❌ Falló ejecución de trade en {symbol}")
                else:
                    logger.error(f"❌ No se pudieron calcular parámetros para {symbol}")
            else:
                logger.info("⏸️ Sin oportunidades de calidad suficiente en este momento")
                if available_symbols:
                    logger.info(f"💡 Mejor score disponible: {max(analysis['score'] for analysis in [await self.analyze_symbol_quality(s) for s in available_symbols[:1]])}")
                    
        except Exception as e:
            logger.error(f"❌ Error en búsqueda de oportunidades: {e}")
        finally:
            self.active_analysis = False
    
    async def run_autonomous_trading(self):
        """Ejecutar bot autónomo de trading"""
        logger.info("🚀 INICIANDO BOT AUTÓNOMO DE MICRO-TRADING")
        logger.info("="*60)
        logger.info(f"💰 Límite por operación: ${self.MICRO_MAX_USDT}")
        logger.info(f"📊 Score mínimo: {self.MIN_QUALITY_SCORE}/100")
        logger.info(f"🔄 Intervalo análisis: {self.MONITORING_INTERVAL/60:.0f} min")
        logger.info(f"⏰ Cooldown tras trade: {self.COOLDOWN_AFTER_TRADE/60:.0f} min")
        logger.info(f"📈 Apalancamiento: {self.LEVERAGE}x")
        logger.info(f"🛡️ Stop Loss: {self.STOP_LOSS_PCT}% | Take Profit: {self.TAKE_PROFIT_PCT}%")
        logger.info("="*60)
        
        cycle = 0
        
        while True:
            try:
                cycle += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                logger.info(f"\n🔄 CICLO #{cycle} - {current_time}")
                logger.info(f"📊 Operaciones diarias: {self.daily_operations}/{self.MAX_DAILY_OPERATIONS}")
                
                await self.find_and_execute_opportunity()
                
                logger.info(f"⏳ Próximo análisis en {self.MONITORING_INTERVAL/60:.0f} minutos...")
                await asyncio.sleep(self.MONITORING_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot detenido por usuario")
                break
            except Exception as e:
                logger.error(f"❌ Error en ciclo principal: {e}")
                await asyncio.sleep(60)  # Esperar 1 min antes de reintentar

async def main():
    """Función principal"""
    bot = AutonomousMicroTradingBot()
    await bot.run_autonomous_trading()

if __name__ == "__main__":
    asyncio.run(main())
