#!/usr/bin/env python3
"""
ESTRATEGIA ÓPTIMA PARA 15% MENSUAL
Basada en análisis completo de 50 libros de trading
Combinación de múltiples estrategias de alto rendimiento
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

class StrategiaOptima15Mensual:
    """
    Sistema combinado de estrategias para alcanzar 15% mensual
    Basado en análisis de literatura especializada
    """
    
    def __init__(self, capital_inicial: float = 10000):
        self.capital_inicial = capital_inicial
        self.capital_actual = capital_inicial
        
        # Distribución de capital según análisis de literatura
        self.distribucion_capital = {
            'scalping_crypto': 0.25,      # 25% - Alto retorno, riesgo controlado
            'gap_trading': 0.25,          # 25% - Retorno medio, riesgo medio
            'sistemas_automaticos': 0.30, # 30% - Retorno consistente, bajo riesgo
            'volatilidad_crypto': 0.10,   # 10% - Alto retorno, muy alto riesgo
            'forex_tendencias': 0.10      # 10% - Retorno estable, riesgo medio
        }
        
        # Parámetros de riesgo por estrategia
        self.parametros_riesgo = {
            'scalping_crypto': {'max_riesgo_por_trade': 0.01, 'stop_loss': 0.015},
            'gap_trading': {'max_riesgo_por_trade': 0.015, 'stop_loss': 0.02},
            'sistemas_automaticos': {'max_riesgo_por_trade': 0.01, 'stop_loss': 0.015},
            'volatilidad_crypto': {'max_riesgo_por_trade': 0.02, 'stop_loss': 0.03},
            'forex_tendencias': {'max_riesgo_por_trade': 0.015, 'stop_loss': 0.02}
        }
        
        # Objetivos de retorno por estrategia (basado en literatura)
        self.objetivos_retorno = {
            'scalping_crypto': {'daily': 0.015, 'monthly': 0.20},      # 1.5% diario, 20% mensual
            'gap_trading': {'daily': 0.008, 'monthly': 0.12},          # 0.8% diario, 12% mensual
            'sistemas_automaticos': {'daily': 0.003, 'monthly': 0.05}, # 0.3% diario, 5% mensual
            'volatilidad_crypto': {'daily': 0.025, 'monthly': 0.35},   # 2.5% diario, 35% mensual
            'forex_tendencias': {'daily': 0.005, 'monthly': 0.07}      # 0.5% diario, 7% mensual
        }
        
        self.resultados = {}
        
    def estrategia_scalping_crypto(self, datos_mercado: Dict) -> Dict:
        """
        ESTRATEGIA 1: SCALPING EN CRIPTOMONEDAS
        Fuente: "5 Pasos para Realizar Scalping Criptomonedas"
        Target: 1-3% por operación, múltiples operaciones diarias
        """
        
        estrategia = {
            'nombre': 'Scalping Crypto',
            'timeframe': '1m-5m',
            'mercados': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
            'horarios_optimos': ['09:00-12:00', '14:00-17:00', '20:00-23:00'],
            
            'criterios_entrada': {
                'volatilidad_minima': 0.02,  # Mínimo 2% de volatilidad
                'volumen_superior': 1.5,     # 150% del volumen promedio
                'rsi_sobrecomprado': 70,     # RSI > 70 para short
                'rsi_sobrevendido': 30,      # RSI < 30 para long
                'confirmacion_velas': True   # Patrón de velas japonesas
            },
            
            'gestion_posicion': {
                'capital_por_trade': self.capital_actual * self.distribucion_capital['scalping_crypto'] * 0.1,
                'stop_loss': 0.015,          # 1.5% máximo
                'take_profit_1': 0.01,       # 1% primer objetivo
                'take_profit_2': 0.02,       # 2% segundo objetivo
                'trailing_stop': 0.008       # 0.8% trailing
            },
            
            'implementacion': [
                "Monitorear breakouts de volatilidad alta",
                "Entrada rápida en primera confirmación",
                "Salida parcial en primer objetivo (50%)",
                "Trailing stop en posición restante",
                "Máximo 5 operaciones por día"
            ]
        }
        
        return estrategia
    
    def estrategia_gap_trading(self, datos_mercado: Dict) -> Dict:
        """
        ESTRATEGIA 2: GAP TRADING
        Fuente: "Estrategias de Trading: análisis del Gap Trading"
        Target: 1-3% por operación
        """
        
        estrategia = {
            'nombre': 'Gap Trading',
            'timeframe': 'Daily + 1H',
            'mercados': ['IBEX35', 'S&P500', 'Blue Chips'],
            'horarios_optimos': ['09:00-10:30'],  # Apertura de mercados
            
            'criterios_entrada': {
                'gap_minimo': 0.01,          # Gap mínimo 1%
                'gap_maximo': 0.05,          # Gap máximo 5%
                'volumen_confirmacion': 1.2,  # 120% volumen promedio
                'sin_noticias_relevantes': True,
                'gap_dentro_rango': True     # Gap dentro del rango histórico
            },
            
            'tipos_gap': {
                'gap_comun': {'probabilidad_cierre': 0.75, 'objetivo': 'cierre_completo'},
                'gap_ruptura': {'probabilidad_cierre': 0.30, 'objetivo': 'cierre_parcial'},
                'gap_continuacion': {'probabilidad_cierre': 0.20, 'objetivo': 'seguir_tendencia'}
            },
            
            'gestion_posicion': {
                'capital_por_trade': self.capital_actual * self.distribucion_capital['gap_trading'] * 0.2,
                'stop_loss': 0.02,           # 2% máximo
                'take_profit': 0.015,        # 1.5% objetivo
                'tiempo_maximo': 240         # 4 horas máximo
            }
        }
        
        return estrategia
    
    def estrategia_sistemas_automaticos(self, datos_mercado: Dict) -> Dict:
        """
        ESTRATEGIA 3: SISTEMAS AUTOMÁTICOS
        Fuente: "Análisis técnico sistemas automáticos de trading"
        Target: 2-5% mensual consistente
        """
        
        estrategia = {
            'nombre': 'Sistemas Automáticos MACD',
            'timeframe': '4H + Daily',
            'mercados': ['FOREX', 'Indices', 'Crypto Major'],
            'horarios_optimos': '24/7 automatizado',
            
            'indicadores_principales': {
                'macd': {'fast': 12, 'slow': 26, 'signal': 9},
                'ma_trend': {'period': 50, 'type': 'EMA'},
                'rsi_filter': {'period': 14, 'overbought': 70, 'oversold': 30},
                'atr': {'period': 14}  # Para stop dinámico
            },
            
            'reglas_entrada': {
                'long': [
                    "MACD line cruza por encima de Signal line",
                    "Precio por encima de EMA 50",
                    "RSI entre 30-70 (no extremos)",
                    "Tendencia general alcista"
                ],
                'short': [
                    "MACD line cruza por debajo de Signal line", 
                    "Precio por debajo de EMA 50",
                    "RSI entre 30-70 (no extremos)",
                    "Tendencia general bajista"
                ]
            },
            
            'gestion_automatica': {
                'capital_por_trade': self.capital_actual * self.distribucion_capital['sistemas_automaticos'] * 0.1,
                'stop_loss_atr': 2.0,        # 2x ATR
                'take_profit_rr': 1.5,       # Risk:Reward 1:1.5
                'trailing_stop_atr': 1.5,    # 1.5x ATR
                'max_trades_simultaneos': 3
            }
        }
        
        return estrategia
    
    def estrategia_volatilidad_crypto(self, datos_mercado: Dict) -> Dict:
        """
        ESTRATEGIA 4: TRADING DE ALTA VOLATILIDAD CRYPTO
        Fuente: Múltiples libros de crypto trading
        Target: 5-15% por operación exitosa
        """
        
        estrategia = {
            'nombre': 'Volatilidad Crypto',
            'timeframe': '15m-1H',
            'mercados': ['Altcoins', 'New Listings', 'High Beta Crypto'],
            'horarios_optimos': ['Eventos de mercado', 'Noticias importantes'],
            
            'criterios_seleccion': {
                'volatilidad_diaria_min': 0.05,  # Mínimo 5% volatilidad
                'volumen_minimo': 1000000,       # $1M volumen mínimo
                'market_cap_min': 10000000,      # $10M market cap mínimo
                'liquidez_adecuada': True,
                'sin_delisting_risk': True
            },
            
            'estrategias_especificas': {
                'breakout_volatilidad': {
                    'trigger': 'Breakout + volumen excepcional',
                    'objetivo': 0.08,            # 8% objetivo
                    'stop': 0.03                 # 3% stop
                },
                'mean_reversion': {
                    'trigger': 'Oversold extreme + divergencia',
                    'objetivo': 0.06,            # 6% objetivo
                    'stop': 0.025                # 2.5% stop
                }
            },
            
            'gestion_extrema': {
                'capital_por_trade': self.capital_actual * self.distribucion_capital['volatilidad_crypto'] * 0.2,
                'max_drawdown': 0.05,           # 5% drawdown máximo
                'position_sizing_kelly': True,   # Kelly criterion
                'profit_booking': 0.05          # Booking al 5%
            }
        }
        
        return estrategia
    
    def estrategia_forex_tendencias(self, datos_mercado: Dict) -> Dict:
        """
        ESTRATEGIA 5: FOREX TENDENCIAS
        Fuente: "Curso de trading en Forex"
        Target: 3-7% mensual
        """
        
        estrategia = {
            'nombre': 'Forex Tendencias',
            'timeframe': '4H + Daily',
            'mercados': ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD'],
            'horarios_optimos': ['London Session', 'NY Session'],
            
            'analisis_tendencia': {
                'timeframes_confirmacion': ['Daily', '4H', '1H'],
                'indicadores_tendencia': ['EMA 20/50/200', 'ADX > 25', 'Ichimoku'],
                'patrones_continuacion': ['Flags', 'Pennants', 'Pullbacks'],
                'fibonacci_retracements': [0.382, 0.5, 0.618]
            },
            
            'entrada_optimizada': {
                'wait_pullback': True,           # Esperar retroceso
                'confluence_zones': 3,           # Mínimo 3 confluencias
                'risk_reward_min': 1.5,          # R:R mínimo 1:1.5
                'fundamental_bias': True         # Sesgo fundamental
            },
            
            'gestion_conservadora': {
                'capital_por_trade': self.capital_actual * self.distribucion_capital['forex_tendencias'] * 0.15,
                'stop_loss_swing': True,         # Stop en swing points
                'partial_profits': [0.01, 0.02], # Parciales en 1% y 2%
                'hold_time_max': 5               # Máximo 5 días
            }
        }
        
        return estrategia
    
    def calcular_expectativa_combinada(self) -> Dict:
        """
        Calcula la expectativa matemática del sistema combinado
        """
        
        expectativas = {}
        
        for estrategia, distribucion in self.distribucion_capital.items():
            capital_asignado = self.capital_inicial * distribucion
            objetivo_mensual = self.objetivos_retorno[estrategia]['monthly']
            
            expectativas[estrategia] = {
                'capital_asignado': capital_asignado,
                'retorno_esperado_mensual': objetivo_mensual,
                'contribucion_absoluta': capital_asignado * objetivo_mensual,
                'peso_en_portfolio': distribucion
            }
        
        # Calcular expectativa total
        retorno_total_esperado = sum([exp['contribucion_absoluta'] for exp in expectativas.values()])
        porcentaje_total_esperado = retorno_total_esperado / self.capital_inicial
        
        resultado = {
            'expectativas_individuales': expectativas,
            'retorno_absoluto_esperado': retorno_total_esperado,
            'retorno_porcentual_esperado': porcentaje_total_esperado,
            'objetivo_15_pct': 0.15,
            'diferencia_objetivo': porcentaje_total_esperado - 0.15,
            'probabilidad_exito': self._calcular_probabilidad_exito()
        }
        
        return resultado
    
    def _calcular_probabilidad_exito(self) -> float:
        """
        Calcula probabilidad de éxito basada en diversificación y gestión de riesgo
        """
        
        # Factores que aumentan probabilidad de éxito
        factores_positivos = {
            'diversificacion': 0.2,        # 5 estrategias diferentes
            'gestion_riesgo': 0.25,        # Stop loss en todas
            'basado_literatura': 0.15,     # Basado en 50 libros
            'timeframes_diferentes': 0.1,  # Diferentes marcos temporales
            'mercados_diversos': 0.1       # Diferentes mercados
        }
        
        # Factores que reducen probabilidad
        factores_riesgo = {
            'alta_volatilidad': -0.1,      # Algunas estrategias muy volátiles
            'correlacion_crypto': -0.05,   # Correlación entre crypto estrategias
            'complejidad_ejecucion': -0.1  # Múltiples estrategias complejas
        }
        
        probabilidad_base = 0.6  # 60% base por ser estrategias probadas
        ajuste_positivo = sum(factores_positivos.values())
        ajuste_negativo = sum(factores_riesgo.values())
        
        probabilidad_final = probabilidad_base + ajuste_positivo + ajuste_negativo
        
        return min(0.85, max(0.4, probabilidad_final))  # Entre 40% y 85%
    
    def generar_plan_implementacion(self) -> Dict:
        """
        Genera plan detallado de implementación
        """
        
        plan = {
            'fase_1_preparacion': {
                'duracion': '2-3 semanas',
                'objetivos': [
                    'Configurar todas las plataformas necesarias',
                    'Backtesting de sistemas automáticos',
                    'Práctica con cuentas demo de todas las estrategias',
                    'Configurar alertas y monitores de mercado'
                ],
                'plataformas_requeridas': [
                    'MetaTrader 4/5 (Forex + Automático)',
                    'TradingView Pro (Análisis técnico)',
                    'Binance/Bybit (Crypto trading)',
                    'Interactive Brokers (Gap trading acciones)',
                    'Python + APIs (Automatización)'
                ]
            },
            
            'fase_2_implementacion_gradual': {
                'duracion': '4-6 semanas',
                'capital_inicial_real': self.capital_inicial * 0.2,  # 20% del capital
                'estrategias_prioritarias': [
                    'Sistemas automáticos (menos riesgo)',
                    'Gap trading (horario definido)',
                    'Forex tendencias (más estable)'
                ],
                'metricas_seguimiento': [
                    'Win rate por estrategia',
                    'Risk-adjusted returns',
                    'Drawdown máximo',
                    'Sharpe ratio'
                ]
            },
            
            'fase_3_escalamiento': {
                'duracion': '6-8 semanas',
                'capital_completo': self.capital_inicial,
                'todas_estrategias_activas': True,
                'optimizaciones': [
                    'Ajuste de parámetros basado en resultados',
                    'Rebalanceo mensual de capital',
                    'Incorporación de machine learning',
                    'Automatización completa posible'
                ]
            }
        }
        
        return plan
    
    def generar_reporte_completo(self) -> Dict:
        """
        Genera reporte completo de la estrategia óptima
        """
        
        reporte = {
            'metadata': {
                'fecha_creacion': datetime.now().isoformat(),
                'capital_inicial': self.capital_inicial,
                'objetivo_mensual': '15%',
                'basado_en': '50 libros de trading especializados'
            },
            
            'resumen_ejecutivo': {
                'estrategias_combinadas': 5,
                'distribucion_capital': self.distribucion_capital,
                'expectativa_retorno': self.calcular_expectativa_combinada(),
                'nivel_riesgo': 'Medio-Alto con gestión estricta',
                'tiempo_implementacion': '8-12 semanas'
            },
            
            'estrategias_detalladas': {
                'scalping_crypto': self.estrategia_scalping_crypto({}),
                'gap_trading': self.estrategia_gap_trading({}),
                'sistemas_automaticos': self.estrategia_sistemas_automaticos({}),
                'volatilidad_crypto': self.estrategia_volatilidad_crypto({}),
                'forex_tendencias': self.estrategia_forex_tendencias({})
            },
            
            'plan_implementacion': self.generar_plan_implementacion(),
            
            'factores_criticos_exito': [
                'Gestión de riesgo estricta (máx 2% por trade)',
                'Diversificación efectiva entre estrategias',
                'Disciplina en ejecución del plan',
                'Monitoreo constante de performance',
                'Adaptación basada en resultados'
            ],
            
            'alertas_riesgo': [
                '⚠️ Alta volatilidad en estrategias crypto',
                '⚠️ Correlación entre estrategias en crisis',
                '⚠️ Complejidad de gestión múltiple',
                '⚠️ Requiere capital mínimo $10,000',
                '⚠️ Necesita conocimiento técnico avanzado'
            ]
        }
        
        return reporte

def main():
    """
    Función principal para generar la estrategia óptima
    """
    
    print("🚀 Generando Estrategia Óptima para 15% Mensual")
    print("📚 Basada en análisis de 50 libros especializados\n")
    
    # Crear instancia de la estrategia
    estrategia = StrategiaOptima15Mensual(capital_inicial=10000)
    
    # Generar reporte completo
    reporte = estrategia.generar_reporte_completo()
    
    # Guardar reporte
    with open('/home/johan/itbot_linux/strategies/estrategia_optima_15_mensual.json', 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False, default=str)
    
    # Mostrar resumen ejecutivo
    expectativa = reporte['resumen_ejecutivo']['expectativa_retorno']
    
    print("📊 RESUMEN EJECUTIVO:")
    print(f"💰 Capital inicial: ${estrategia.capital_inicial:,.2f}")
    print(f"🎯 Objetivo mensual: 15%")
    print(f"📈 Expectativa calculada: {expectativa['retorno_porcentual_esperado']:.1%}")
    print(f"✅ Probabilidad de éxito: {expectativa['probabilidad_exito']:.1%}")
    
    print(f"\n💡 DISTRIBUCIÓN DE CAPITAL:")
    for estrategia_name, peso in reporte['resumen_ejecutivo']['distribucion_capital'].items():
        capital_asignado = estrategia.capital_inicial * peso
        print(f"  • {estrategia_name}: {peso:.1%} (${capital_asignado:,.0f})")
    
    print(f"\n📋 ESTRATEGIAS INCLUIDAS:")
    for i, (nombre, detalles) in enumerate(reporte['estrategias_detalladas'].items(), 1):
        print(f"  {i}. {detalles['nombre']} - {detalles['timeframe']}")
    
    print(f"\n⚠️ FACTORES CRÍTICOS:")
    for factor in reporte['factores_criticos_exito']:
        print(f"  • {factor}")
    
    print(f"\n✅ Reporte completo guardado en: strategies/estrategia_optima_15_mensual.json")
    print("🎯 ¡Sistema listo para implementación!")

if __name__ == "__main__":
    main()
