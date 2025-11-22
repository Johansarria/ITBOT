import pandas as pd
import numpy as np
import yfinance as yf
import warnings
from datetime import datetime, timedelta, time
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import pytz

warnings.filterwarnings('ignore')

class UltimateSicarSessionAnalyzer:
    """
    Analizador de sesiones de trading para optimizar horarios de operación
    Enfoque en sesión americana con capital base de $300
    """
    
    def __init__(self):
        self.est_tz = pytz.timezone('US/Eastern')
        self.session_data = {}
        
    def analyze_us_trading_sessions(self) -> Dict:
        """Analizar diferentes horarios de la sesión americana"""
        
        sessions = {
            'pre_market': {
                'start': time(4, 0),   # 4:00 AM EST
                'end': time(9, 30),    # 9:30 AM EST
                'description': 'Pre-market trading'
            },
            'market_open': {
                'start': time(9, 30),  # 9:30 AM EST
                'end': time(11, 0),    # 11:00 AM EST
                'description': 'Market opening - Alta volatilidad'
            },
            'mid_morning': {
                'start': time(11, 0),  # 11:00 AM EST
                'end': time(12, 0),    # 12:00 PM EST
                'description': 'Media mañana - Consolidación'
            },
            'lunch_time': {
                'start': time(12, 0),  # 12:00 PM EST
                'end': time(14, 0),    # 2:00 PM EST
                'description': 'Hora del almuerzo - Baja volatilidad'
            },
            'afternoon_power': {
                'start': time(14, 0),  # 2:00 PM EST
                'end': time(16, 0),    # 4:00 PM EST
                'description': 'Tarde activa - Segunda oportunidad'
            },
            'market_close': {
                'start': time(15, 30), # 3:30 PM EST
                'end': time(16, 0),    # 4:00 PM EST
                'description': 'Cierre de mercado - Alta volatilidad'
            },
            'after_hours': {
                'start': time(16, 0),  # 4:00 PM EST
                'end': time(20, 0),    # 8:00 PM EST
                'description': 'After hours trading'
            }
        }
        
        return sessions
    
    def get_optimal_trading_windows(self) -> Dict:
        """Identificar ventanas óptimas para trading con $300 base"""
        
        optimal_windows = {
            'high_probability': {
                'times': ['09:30-11:00', '14:00-16:00'],
                'characteristics': [
                    'Alta volatilidad',
                    'Mayor volumen',
                    'Movimientos direccionales claros',
                    'Mejor para scalping y day trading'
                ],
                'risk_level': 'Alto',
                'capital_allocation': 0.4  # 40% del capital ($120)
            },
            'medium_probability': {
                'times': ['11:00-12:00', '13:00-14:00'],
                'characteristics': [
                    'Volatilidad moderada',
                    'Movimientos más predecibles',
                    'Bueno para swing trades cortos'
                ],
                'risk_level': 'Medio',
                'capital_allocation': 0.3  # 30% del capital ($90)
            },
            'low_risk': {
                'times': ['12:00-13:00'],
                'characteristics': [
                    'Baja volatilidad',
                    'Movimientos laterales',
                    'Ideal para estrategias de reversión'
                ],
                'risk_level': 'Bajo',
                'capital_allocation': 0.3  # 30% del capital ($90)
            }
        }
        
        return optimal_windows
    
    def analyze_timeframe_effectiveness(self) -> Dict:
        """Analizar efectividad de diferentes timeframes"""
        
        timeframes = {
            '1m': {
                'best_for': 'Scalping extremo',
                'session_focus': 'market_open, market_close',
                'capital_requirement': 50,  # Mínimo $50 por trade
                'win_rate_target': 0.65,
                'risk_reward': '1:1',
                'max_trades_per_day': 10
            },
            '5m': {
                'best_for': 'Scalping y day trading',
                'session_focus': 'market_open, afternoon_power',
                'capital_requirement': 75,  # Mínimo $75 por trade
                'win_rate_target': 0.60,
                'risk_reward': '1:1.5',
                'max_trades_per_day': 6
            },
            '15m': {
                'best_for': 'Day trading balanceado',
                'session_focus': 'market_open, afternoon_power',
                'capital_requirement': 100,  # Mínimo $100 por trade
                'win_rate_target': 0.55,
                'risk_reward': '1:2',
                'max_trades_per_day': 4
            },
            '1h': {
                'best_for': 'Swing trading intraday',
                'session_focus': 'full_session',
                'capital_requirement': 150,  # Mínimo $150 por trade
                'win_rate_target': 0.50,
                'risk_reward': '1:2.5',
                'max_trades_per_day': 2
            },
            '4h': {
                'best_for': 'Swing trading multi-día',
                'session_focus': 'daily_analysis',
                'capital_requirement': 200,  # Mínimo $200 por trade
                'win_rate_target': 0.45,
                'risk_reward': '1:3',
                'max_trades_per_day': 1
            }
        }
        
        return timeframes
    
    def calculate_position_sizing_for_300_base(self, timeframe: str, risk_percentage: float = 0.02) -> Dict:
        """Calcular tamaño de posición para base de $300"""
        
        base_capital = 300
        risk_per_trade = base_capital * risk_percentage  # $6 por trade (2%)
        
        timeframe_configs = {
            '1m': {
                'stop_loss_points': 5,    # 5 puntos de stop loss
                'position_size': risk_per_trade / 5,
                'max_positions': 3,
                'recommended_capital_per_trade': 50
            },
            '5m': {
                'stop_loss_points': 10,   # 10 puntos de stop loss
                'position_size': risk_per_trade / 10,
                'max_positions': 2,
                'recommended_capital_per_trade': 75
            },
            '15m': {
                'stop_loss_points': 20,   # 20 puntos de stop loss
                'position_size': risk_per_trade / 20,
                'max_positions': 2,
                'recommended_capital_per_trade': 100
            },
            '1h': {
                'stop_loss_points': 40,   # 40 puntos de stop loss
                'position_size': risk_per_trade / 40,
                'max_positions': 1,
                'recommended_capital_per_trade': 150
            },
            '4h': {
                'stop_loss_points': 80,   # 80 puntos de stop loss
                'position_size': risk_per_trade / 80,
                'max_positions': 1,
                'recommended_capital_per_trade': 200
            }
        }
        
        return timeframe_configs.get(timeframe, timeframe_configs['15m'])
    
    def generate_session_strategy_recommendations(self) -> Dict:
        """Generar recomendaciones específicas por sesión"""
        
        recommendations = {
            'morning_strategy': {
                'time': '09:30-11:00 EST',
                'timeframes': ['1m', '5m'],
                'approach': 'Momentum breakout',
                'capital_allocation': 120,  # $120 (40% de $300)
                'max_risk_per_trade': 12,   # $12 (4% de $300)
                'expected_trades': 3-5,
                'target_return': '2-4%',
                'key_indicators': ['Volume spike', 'Gap analysis', 'Pre-market sentiment']
            },
            'midday_strategy': {
                'time': '11:00-14:00 EST',
                'timeframes': ['15m', '1h'],
                'approach': 'Range trading',
                'capital_allocation': 90,   # $90 (30% de $300)
                'max_risk_per_trade': 9,    # $9 (3% de $300)
                'expected_trades': 1-2,
                'target_return': '1-2%',
                'key_indicators': ['Support/Resistance', 'RSI divergence', 'Volume confirmation']
            },
            'afternoon_strategy': {
                'time': '14:00-16:00 EST',
                'timeframes': ['5m', '15m'],
                'approach': 'Trend continuation',
                'capital_allocation': 90,   # $90 (30% de $300)
                'max_risk_per_trade': 9,    # $9 (3% de $300)
                'expected_trades': 2-3,
                'target_return': '1.5-3%',
                'key_indicators': ['Trend strength', 'Institutional flow', 'End-of-day positioning']
            }
        }
        
        return recommendations
    
    def create_risk_management_rules(self) -> Dict:
        """Crear reglas de gestión de riesgo para $300 base"""
        
        risk_rules = {
            'daily_limits': {
                'max_daily_loss': 18,      # $18 (6% de $300)
                'max_daily_trades': 8,
                'max_consecutive_losses': 3,
                'profit_target': 15,       # $15 (5% de $300)
                'stop_trading_after_target': True
            },
            'position_limits': {
                'max_position_size': 100,   # $100 máximo por posición
                'max_open_positions': 3,
                'correlation_limit': 0.7,   # Máxima correlación entre posiciones
                'sector_concentration': 0.5 # Máximo 50% en un sector
            },
            'timeframe_rules': {
                '1m': {'max_trades': 4, 'max_risk': 6},
                '5m': {'max_trades': 3, 'max_risk': 9},
                '15m': {'max_trades': 2, 'max_risk': 12},
                '1h': {'max_trades': 1, 'max_risk': 15},
                '4h': {'max_trades': 1, 'max_risk': 18}
            },
            'session_rules': {
                'morning': {'max_risk': 12, 'max_trades': 5},
                'midday': {'max_risk': 9, 'max_trades': 2},
                'afternoon': {'max_risk': 9, 'max_trades': 3}
            }
        }
        
        return risk_rules
    
    def generate_comprehensive_report(self) -> str:
        """Generar reporte completo del análisis"""
        
        sessions = self.analyze_us_trading_sessions()
        windows = self.get_optimal_trading_windows()
        timeframes = self.analyze_timeframe_effectiveness()
        strategies = self.generate_session_strategy_recommendations()
        risk_rules = self.create_risk_management_rules()
        
        report = f"""
# 📊 ULTIMATE SICAR SYSTEM - ANÁLISIS DE SESIONES AMERICANAS
## Capital Base: $300 | Sin Apalancamiento | Enfoque Multi-Timeframe

## 🕐 HORARIOS ÓPTIMOS DE TRADING

### Sesiones de Mayor Oportunidad:
1. **APERTURA DE MERCADO (09:30-11:00 EST)**
   - Volatilidad: ALTA
   - Volumen: MÁXIMO
   - Oportunidades: Breakouts, Gap trading
   - Capital asignado: $120 (40%)
   - Timeframes recomendados: 1m, 5m

2. **PODER VESPERTINO (14:00-16:00 EST)**
   - Volatilidad: ALTA
   - Volumen: ALTO
   - Oportunidades: Continuación de tendencias
   - Capital asignado: $90 (30%)
   - Timeframes recomendados: 5m, 15m

3. **CONSOLIDACIÓN MEDIA (11:00-14:00 EST)**
   - Volatilidad: MEDIA
   - Volumen: MODERADO
   - Oportunidades: Range trading
   - Capital asignado: $90 (30%)
   - Timeframes recomendados: 15m, 1h

## 📈 ESTRATEGIAS POR TIMEFRAME

### 1 MINUTO - Scalping Extremo
- Capital mínimo por trade: $50
- Stop loss: 5 puntos
- Take profit: 5-8 puntos (1:1 a 1:1.6)
- Máximo 4 trades por día
- Win rate objetivo: 65%

### 5 MINUTOS - Scalping Balanceado
- Capital mínimo por trade: $75
- Stop loss: 10 puntos
- Take profit: 15-20 puntos (1:1.5 a 1:2)
- Máximo 3 trades por día
- Win rate objetivo: 60%

### 15 MINUTOS - Day Trading
- Capital mínimo por trade: $100
- Stop loss: 20 puntos
- Take profit: 40 puntos (1:2)
- Máximo 2 trades por día
- Win rate objetivo: 55%

### 1 HORA - Swing Intraday
- Capital mínimo por trade: $150
- Stop loss: 40 puntos
- Take profit: 100 puntos (1:2.5)
- Máximo 1 trade por día
- Win rate objetivo: 50%

## 💰 GESTIÓN DE CAPITAL PARA $300

### Distribución Diaria:
- **Riesgo máximo diario**: $18 (6%)
- **Objetivo de ganancia**: $15 (5%)
- **Capital por sesión**:
  - Mañana: $120 (40%)
  - Mediodía: $90 (30%)
  - Tarde: $90 (30%)

### Reglas de Posición:
- Máximo $100 por posición individual
- Máximo 3 posiciones abiertas simultáneamente
- Riesgo por trade: 2-4% del capital total
- Stop loss obligatorio en cada trade

## 🎯 OBJETIVOS DE RENDIMIENTO

### Objetivos Conservadores (Recomendado):
- Retorno diario: 2-5% ($6-$15)
- Retorno semanal: 10-20% ($30-$60)
- Retorno mensual: 30-50% ($90-$150)

### Objetivos Agresivos (Mayor riesgo):
- Retorno diario: 5-10% ($15-$30)
- Retorno semanal: 20-40% ($60-$120)
- Retorno mensual: 50-100% ($150-$300)

## ⚠️ REGLAS DE RIESGO ESTRICTAS

### Límites Diarios:
- Pérdida máxima: $18 (STOP TRADING)
- Trades consecutivos perdedores: 3 (PAUSA 1 HORA)
- Ganancia objetivo alcanzada: $15 (CONSIDERAR PARAR)

### Límites por Timeframe:
- 1m: Máximo $6 riesgo por trade
- 5m: Máximo $9 riesgo por trade
- 15m: Máximo $12 riesgo por trade
- 1h: Máximo $15 riesgo por trade

## 📋 PLAN DE IMPLEMENTACIÓN

### Semana 1-2: Preparación
- Configurar plataforma de trading
- Practicar con paper trading
- Familiarizarse con horarios EST

### Semana 3-4: Implementación Gradual
- Comenzar solo con timeframe 15m
- Capital inicial: $150 (50% del total)
- Máximo 1 trade por día

### Mes 2: Expansión
- Añadir timeframe 5m
- Incrementar a $225 (75% del total)
- Máximo 2 trades por día

### Mes 3+: Sistema Completo
- Todos los timeframes activos
- Capital completo $300
- Sistema multi-sesión completo

## 🔧 HERRAMIENTAS RECOMENDADAS

### Indicadores Principales:
- EMA 8, 21, 50 (tendencia)
- RSI 14 (momentum)
- Volume Profile (soporte/resistencia)
- VWAP (precio promedio ponderado)

### Confirmaciones:
- Volume spike (2x promedio)
- Price action patterns
- Support/Resistance levels
- Market sentiment indicators

---
*Nota: Este sistema está diseñado para capital pequeño sin apalancamiento. 
La disciplina y gestión de riesgo son fundamentales para el éxito.*
"""
        
        return report

def main():
    """Función principal para ejecutar el análisis"""
    
    print("🚀 ULTIMATE SICAR SYSTEM - ANÁLISIS DE SESIONES")
    print("=" * 60)
    
    analyzer = UltimateSicarSessionAnalyzer()
    
    # Generar reporte completo
    report = analyzer.generate_comprehensive_report()
    
    # Guardar reporte
    with open('ultimate_sicar_session_analysis.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("✅ Análisis completo generado:")
    print("   - ultimate_sicar_session_analysis.md")
    
    # Mostrar resumen ejecutivo
    print("\n" + "=" * 60)
    print("📋 RESUMEN EJECUTIVO")
    print("=" * 60)
    
    print("💰 CAPITAL BASE: $300 (Sin apalancamiento)")
    print("🎯 OBJETIVO DIARIO: $6-$15 (2-5%)")
    print("⏰ HORARIOS ÓPTIMOS:")
    print("   • 09:30-11:00 EST (Apertura) - $120 asignados")
    print("   • 14:00-16:00 EST (Tarde) - $90 asignados")
    print("   • 11:00-14:00 EST (Mediodía) - $90 asignados")
    
    print("\n📊 TIMEFRAMES RECOMENDADOS:")
    print("   • 1m: Scalping extremo ($50/trade)")
    print("   • 5m: Scalping balanceado ($75/trade)")
    print("   • 15m: Day trading ($100/trade)")
    print("   • 1h: Swing intraday ($150/trade)")
    
    print("\n⚠️ LÍMITES DE RIESGO:")
    print("   • Pérdida máxima diaria: $18 (6%)")
    print("   • Máximo 8 trades por día")
    print("   • Stop obligatorio en cada trade")
    
    print("\n🎉 Análisis completado exitosamente!")

if __name__ == "__main__":
    main()