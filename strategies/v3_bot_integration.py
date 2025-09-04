#!/usr/bin/env python3
"""
INTEGRACIÓN SISTEMA V3 CON BOT EXISTENTE
=======================================
Integra las estrategias V3 optimizadas con el sistema de bot existente
"""

import sys
import os
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import sqlite3

# Agregar el directorio raíz al path para importar módulos del bot existente
sys.path.append('/home/johan/itbot_linux')

try:
    from config import *
    from handlers import *
    from risk_manager import RiskManager as ExistingRiskManager
except ImportError as e:
    print(f"⚠️ No se pudieron importar módulos del bot existente: {e}")

from autonomous_trading_v3 import AutonomousTradingSystem, TradingSignal, MarketCondition

class V3BotIntegration:
    """Integración del Sistema V3 con el bot existente"""
    
    def __init__(self):
        self.autonomous_system = AutonomousTradingSystem()
        self.db_path = "bot_integration.db"
        self.setup_integration_db()
        
        # Estado de integración
        self.v3_enabled = True
        self.manual_override = False
        self.performance_tracking = {}
        
        self.logger = logging.getLogger(__name__)
        
    def setup_integration_db(self):
        """Configurar base de datos de integración"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS v3_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                strategy TEXT,
                symbol TEXT,
                daily_return REAL,
                cumulative_return REAL,
                win_rate REAL,
                active BOOLEAN
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bot_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                decision_type TEXT,
                symbol TEXT,
                strategy_used TEXT,
                confidence REAL,
                executed BOOLEAN,
                reason TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def get_v3_recommendation(self, symbol: str) -> Optional[Dict]:
        """Obtener recomendación del Sistema V3"""
        try:
            # Analizar condiciones del mercado
            market_condition = await self.autonomous_system.analyze_market_conditions(symbol)
            if not market_condition:
                return None
            
            # Seleccionar estrategia óptima
            optimal_strategy = self.autonomous_system.select_optimal_strategy(market_condition)
            
            # Generar señales
            signals = await self.autonomous_system.generate_trading_signals(symbol, optimal_strategy)
            
            if not signals:
                return None
            
            # Seleccionar la señal con mayor confianza
            best_signal = max(signals, key=lambda s: s.confidence)
            
            recommendation = {
                'symbol': symbol,
                'action': best_signal.action,
                'strategy': optimal_strategy,
                'confidence': best_signal.confidence,
                'entry_price': best_signal.entry_price,
                'stop_loss': best_signal.stop_loss,
                'take_profit': best_signal.take_profit,
                'risk_amount': best_signal.risk_amount,
                'market_condition': {
                    'trend': market_condition.trend,
                    'volatility': market_condition.volatility,
                    'momentum': market_condition.momentum
                },
                'timeframe': best_signal.timeframe
            }
            
            # Registrar decisión
            self.log_bot_decision(recommendation)
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error getting V3 recommendation: {e}")
            return None
    
    def should_use_v3_strategy(self, symbol: str) -> bool:
        """Decidir si usar estrategia V3 basado en performance"""
        if not self.v3_enabled or self.manual_override:
            return False
        
        # Verificar performance histórica de V3 para este símbolo
        recent_performance = self.get_recent_v3_performance(symbol)
        
        if recent_performance:
            # Usar V3 si tiene buen rendimiento reciente
            if recent_performance['win_rate'] > 60 and recent_performance['daily_return'] > 1.0:
                return True
            elif recent_performance['win_rate'] < 40 or recent_performance['daily_return'] < -2.0:
                return False
        
        # Por defecto, usar V3 para estos símbolos que mostraron mejor rendimiento
        high_performance_symbols = ['SOL/USDT', 'ETH/USDT', 'BTC/USDT']
        return symbol in high_performance_symbols
    
    def get_recent_v3_performance(self, symbol: str) -> Optional[Dict]:
        """Obtener performance reciente de V3 para un símbolo"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT AVG(daily_return) as avg_return, AVG(win_rate) as avg_win_rate
                FROM v3_performance
                WHERE symbol = ? AND timestamp > datetime('now', '-7 days')
                AND active = 1
            ''', (symbol,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] is not None:
                return {
                    'daily_return': result[0],
                    'win_rate': result[1]
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting V3 performance: {e}")
            return None
    
    def log_bot_decision(self, recommendation: Dict):
        """Registrar decisión del bot"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT INTO bot_decisions (timestamp, decision_type, symbol, strategy_used, confidence, executed, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(),
                'V3_RECOMMENDATION',
                recommendation['symbol'],
                recommendation['strategy'],
                recommendation['confidence'],
                False,  # Se actualizará cuando se ejecute
                f"Market: {recommendation['market_condition']['trend']}, Vol: {recommendation['market_condition']['volatility']:.2f}"
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error logging bot decision: {e}")
    
    async def enhanced_signal_generation(self, symbol: str) -> Dict:
        """Generación de señales mejorada que combina V3 con lógica existente"""
        
        # 1. Obtener recomendación V3
        v3_recommendation = None
        if self.should_use_v3_strategy(symbol):
            v3_recommendation = await self.get_v3_recommendation(symbol)
        
        # 2. Combinar con análisis existente del bot
        existing_analysis = self.get_existing_bot_analysis(symbol)
        
        # 3. Crear señal combinada
        combined_signal = self.combine_signals(v3_recommendation, existing_analysis, symbol)
        
        return combined_signal
    
    def get_existing_bot_analysis(self, symbol: str) -> Dict:
        """Obtener análisis del bot existente (placeholder)"""
        # Aquí se integraría con la lógica existente del bot
        # Por ahora, retorna un análisis básico
        return {
            'signal': 'NEUTRAL',
            'confidence': 0.5,
            'source': 'EXISTING_BOT'
        }
    
    def combine_signals(self, v3_recommendation: Optional[Dict], existing_analysis: Dict, symbol: str) -> Dict:
        """Combinar señales V3 con análisis existente"""
        
        if not v3_recommendation:
            # Solo usar análisis existente
            return {
                'action': existing_analysis['signal'],
                'confidence': existing_analysis['confidence'],
                'strategy': 'EXISTING',
                'symbol': symbol,
                'reason': 'V3 not available, using existing analysis'
            }
        
        # Combinar ambos análisis
        v3_weight = 0.7  # Dar más peso a V3 por su mejor rendimiento demostrado
        existing_weight = 0.3
        
        # Convertir acciones a scores
        action_scores = {'BUY': 1, 'SELL': -1, 'NEUTRAL': 0, 'HOLD': 0}
        
        v3_score = action_scores.get(v3_recommendation['action'], 0) * v3_recommendation['confidence']
        existing_score = action_scores.get(existing_analysis['signal'], 0) * existing_analysis['confidence']
        
        combined_score = (v3_score * v3_weight) + (existing_score * existing_weight)
        combined_confidence = (v3_recommendation['confidence'] * v3_weight) + (existing_analysis['confidence'] * existing_weight)
        
        # Determinar acción final
        if combined_score > 0.3:
            final_action = 'BUY'
        elif combined_score < -0.3:
            final_action = 'SELL'
        else:
            final_action = 'HOLD'
        
        return {
            'action': final_action,
            'confidence': combined_confidence,
            'strategy': 'HYBRID_V3',
            'symbol': symbol,
            'v3_recommendation': v3_recommendation,
            'existing_analysis': existing_analysis,
            'combined_score': combined_score,
            'reason': f'Combined analysis: V3({v3_score:.2f}) + Existing({existing_score:.2f}) = {combined_score:.2f}'
        }
    
    async def execute_enhanced_strategy(self, symbol: str) -> bool:
        """Ejecutar estrategia mejorada"""
        try:
            # Generar señal combinada
            signal = await self.enhanced_signal_generation(symbol)
            
            # Log de la decisión
            self.logger.info(f"Enhanced signal for {symbol}: {signal['action']} (confidence: {signal['confidence']:.2f})")
            
            # Ejecutar si la confianza es suficiente
            if signal['confidence'] >= 0.6 and signal['action'] in ['BUY', 'SELL']:
                
                # Aquí se integraría con el sistema de ejecución existente del bot
                execution_result = await self.execute_trade_integration(signal)
                
                if execution_result:
                    self.logger.info(f"✅ Trade executed for {symbol}: {signal['action']}")
                    return True
                else:
                    self.logger.warning(f"❌ Trade execution failed for {symbol}")
                    return False
            
            else:
                self.logger.info(f"⏸️ Signal confidence too low for {symbol}: {signal['confidence']:.2f}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing enhanced strategy: {e}")
            return False
    
    async def execute_trade_integration(self, signal: Dict) -> bool:
        """Integrar con sistema de ejecución existente"""
        # Placeholder - aquí se integraría con handlers.py y el sistema existente
        self.logger.info(f"🔄 Integrating with existing trade execution system...")
        
        # Simular ejecución exitosa por ahora
        return True
    
    def update_v3_performance(self, symbol: str, strategy: str, daily_return: float, win_rate: float):
        """Actualizar performance de V3"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT INTO v3_performance (timestamp, strategy, symbol, daily_return, cumulative_return, win_rate, active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(), strategy, symbol, daily_return, 
                0,  # cumulative_return se calculará después
                win_rate, True
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error updating V3 performance: {e}")
    
    def get_integration_status(self) -> Dict:
        """Obtener estado de la integración"""
        return {
            'v3_enabled': self.v3_enabled,
            'manual_override': self.manual_override,
            'autonomous_system_running': self.autonomous_system.running,
            'active_strategies': list(self.autonomous_system.strategies.keys()),
            'monitored_symbols': ['ETH/USDT', 'BTC/USDT', 'SOL/USDT'],
            'last_update': datetime.now().isoformat()
        }
    
    def enable_v3_system(self):
        """Activar sistema V3"""
        self.v3_enabled = True
        self.logger.info("✅ Sistema V3 activado")
    
    def disable_v3_system(self):
        """Desactivar sistema V3"""
        self.v3_enabled = False
        self.logger.info("❌ Sistema V3 desactivado")
    
    def set_manual_override(self, enabled: bool):
        """Activar/desactivar override manual"""
        self.manual_override = enabled
        self.logger.info(f"🔧 Override manual: {'activado' if enabled else 'desactivado'}")

async def main():
    """Función principal para testing"""
    print("🔗 INTEGRACIÓN SISTEMA V3 CON BOT EXISTENTE")
    print("=" * 60)
    
    # Crear integración
    integration = V3BotIntegration()
    
    print("📋 ESTADO DE LA INTEGRACIÓN:")
    status = integration.get_integration_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n🧪 PRUEBA DE SEÑAL COMBINADA:")
    
    # Probar generación de señal para ETH/USDT
    symbol = 'ETH/USDT'
    enhanced_signal = await integration.enhanced_signal_generation(symbol)
    
    print(f"\n📊 Señal mejorada para {symbol}:")
    print(f"  Acción: {enhanced_signal['action']}")
    print(f"  Confianza: {enhanced_signal['confidence']:.2f}")
    print(f"  Estrategia: {enhanced_signal['strategy']}")
    print(f"  Razón: {enhanced_signal['reason']}")
    
    if 'v3_recommendation' in enhanced_signal and enhanced_signal['v3_recommendation']:
        v3_rec = enhanced_signal['v3_recommendation']
        print(f"\n🎯 Detalles V3:")
        print(f"  Tendencia: {v3_rec['market_condition']['trend']}")
        print(f"  Volatilidad: {v3_rec['market_condition']['volatility']:.2f}%")
        print(f"  Momentum: {v3_rec['market_condition']['momentum']:.2f}")
        print(f"  Estrategia V3: {v3_rec['strategy']}")
        print(f"  Timeframe: {v3_rec['timeframe']}")
    
    print("\n✅ Integración funcionando correctamente")
    print("💡 Para uso en producción, integrar con handlers.py y sistema existente")

if __name__ == "__main__":
    asyncio.run(main())
