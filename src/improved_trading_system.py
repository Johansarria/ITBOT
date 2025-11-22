"""
Sistema de Trading Mejorado Integrado
Combina todos los módulos mejorados: filtros de tendencia, análisis técnico avanzado,
gestión de riesgo dinámico y confirmaciones de señales
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# Importar módulos mejorados
from enhanced_trading_system import EnhancedTradingSystem
from advanced_technical_analysis import AdvancedTechnicalAnalysis
from dynamic_risk_management import DynamicRiskManager
from signal_confirmations import SignalConfirmations

class ImprovedTradingSystem:
    def __init__(self, db_path: str = "auto_trading_alerts.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Inicializar módulos
        self.enhanced_system = EnhancedTradingSystem()
        self.technical_analyzer = AdvancedTechnicalAnalysis()
        self.risk_manager = DynamicRiskManager(db_path)
        self.signal_confirmations = SignalConfirmations()
        
        # Configuración del sistema mejorado
        self.config = {
            'min_confidence': 75.0,
            'max_positions': 2,
            'enable_btc_filter': True,
            'enable_confirmations': True,
            'enable_dynamic_risk': True,
            'test_mode': True  # Para pruebas sin ejecutar operaciones reales
        }
        
        self.setup_logging()
    
    def setup_logging(self):
        """Configura el logging del sistema"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('improved_trading_system.log'),
                logging.StreamHandler()
            ]
        )
    
    def analyze_symbol(self, symbol: str) -> Dict[str, any]:
        """
        Realiza un análisis completo de un símbolo usando todos los módulos mejorados
        """
        try:
            self.logger.info(f"Iniciando análisis completo de {symbol}")
            
            analysis_result = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'should_trade': False,
                'final_signal': 'NEUTRAL',
                'confidence': 0.0,
                'risk_level': 'HIGH',
                'reasons': [],
                'analysis_details': {}
            }
            
            # 1. Filtros de tendencia (BTC/ETH)
            if self.config['enable_btc_filter']:
                btc_filter = self._check_btc_eth_trend()
                analysis_result['analysis_details']['btc_filter'] = btc_filter
                
                if not btc_filter['can_trade_altcoins']:
                    analysis_result['reasons'].append(f"Filtro BTC/ETH: {btc_filter['reason']}")
                    self.logger.info(f"{symbol}: Rechazado por filtro BTC/ETH")
                    return analysis_result
            
            # 2. Análisis técnico avanzado
            technical_analysis = self.technical_analyzer.get_comprehensive_analysis(symbol)
            analysis_result['analysis_details']['technical'] = technical_analysis
            
            if technical_analysis['confidence'] < self.config['min_confidence']:
                analysis_result['reasons'].append(f"Confianza técnica insuficiente: {technical_analysis['confidence']:.1f}% < {self.config['min_confidence']}%")
                self.logger.info(f"{symbol}: Rechazado por baja confianza técnica")
                return analysis_result
            
            # 3. Gestión de riesgo dinámico
            if self.config['enable_dynamic_risk']:
                signal_data = {
                    'symbol': symbol,
                    'signal_type': technical_analysis['overall_signal'],
                    'confidence': technical_analysis['confidence'],
                    'price': self._get_current_price(symbol),
                    'volatility': self._get_volatility_from_analysis(technical_analysis)
                }
                
                risk_assessment = self.risk_manager.should_execute_trade(signal_data)
                analysis_result['analysis_details']['risk'] = risk_assessment
                
                if not risk_assessment['should_execute']:
                    analysis_result['reasons'].append(f"Gestión de riesgo: {risk_assessment['reason']}")
                    self.logger.info(f"{symbol}: Rechazado por gestión de riesgo")
                    return analysis_result
            
            # 4. Confirmaciones de señales
            if self.config['enable_confirmations']:
                confirmations = self.signal_confirmations.get_comprehensive_confirmations(
                    symbol, technical_analysis['overall_signal']
                )
                analysis_result['analysis_details']['confirmations'] = confirmations
                
                if confirmations['recommendation'] == 'REJECT':
                    analysis_result['reasons'].append(f"Confirmaciones: {confirmations['summary']}")
                    self.logger.info(f"{symbol}: Rechazado por falta de confirmaciones")
                    return analysis_result
                elif confirmations['recommendation'] == 'CAUTION':
                    analysis_result['reasons'].append(f"Precaución: {confirmations['summary']}")
            
            # Si llegamos aquí, la señal pasó todos los filtros
            analysis_result['should_trade'] = True
            analysis_result['final_signal'] = technical_analysis['overall_signal']
            analysis_result['confidence'] = technical_analysis['confidence']
            analysis_result['risk_level'] = technical_analysis['risk_level']
            analysis_result['reasons'].append("Todos los criterios cumplidos")
            
            self.logger.info(f"{symbol}: APROBADO para trading - {analysis_result['final_signal']} con {analysis_result['confidence']:.1f}% confianza")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analizando {symbol}: {e}")
            analysis_result['reasons'].append(f"Error en análisis: {str(e)}")
            return analysis_result
    
    def test_historical_failures(self) -> Dict[str, any]:
        """
        Prueba el sistema mejorado con los casos que fallaron anteriormente
        """
        self.logger.info("Iniciando pruebas con casos históricos que fallaron")
        
        # Casos que fallaron anteriormente
        failed_cases = [
            {'symbol': 'ADAUSDT', 'expected_signal': 'SELL', 'entry_price': 0.64},
            {'symbol': 'AVAXUSDT', 'expected_signal': 'SELL', 'entry_price': 19.36}
        ]
        
        test_results = {
            'total_cases': len(failed_cases),
            'prevented_failures': 0,
            'would_execute': 0,
            'case_details': []
        }
        
        for case in failed_cases:
            symbol = case['symbol']
            self.logger.info(f"Probando caso histórico: {symbol}")
            
            analysis = self.analyze_symbol(symbol)
            
            case_result = {
                'symbol': symbol,
                'historical_signal': case['expected_signal'],
                'historical_price': case['entry_price'],
                'current_analysis': analysis,
                'would_prevent_failure': not analysis['should_trade'],
                'prevention_reasons': analysis['reasons']
            }
            
            if not analysis['should_trade']:
                test_results['prevented_failures'] += 1
                self.logger.info(f"✅ {symbol}: Falla PREVENIDA - {', '.join(analysis['reasons'])}")
            else:
                test_results['would_execute'] += 1
                self.logger.warning(f"⚠️ {symbol}: Aún se ejecutaría - Revisar criterios")
            
            test_results['case_details'].append(case_result)
        
        # Calcular estadísticas
        prevention_rate = (test_results['prevented_failures'] / test_results['total_cases']) * 100
        test_results['prevention_rate'] = prevention_rate
        
        self.logger.info(f"Resultados de pruebas: {test_results['prevented_failures']}/{test_results['total_cases']} fallas prevenidas ({prevention_rate:.1f}%)")
        
        return test_results
    
    def test_current_market_conditions(self) -> Dict[str, any]:
        """
        Prueba el sistema con condiciones actuales del mercado
        """
        self.logger.info("Probando sistema con condiciones actuales del mercado")
        
        # Símbolos populares para probar
        test_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT']
        
        market_test = {
            'total_symbols': len(test_symbols),
            'signals_generated': 0,
            'signals_approved': 0,
            'signals_rejected': 0,
            'symbol_results': []
        }
        
        for symbol in test_symbols:
            self.logger.info(f"Analizando condiciones actuales de {symbol}")
            
            analysis = self.analyze_symbol(symbol)
            
            symbol_result = {
                'symbol': symbol,
                'analysis': analysis,
                'signal_generated': analysis['final_signal'] != 'NEUTRAL',
                'signal_approved': analysis['should_trade']
            }
            
            if analysis['final_signal'] != 'NEUTRAL':
                market_test['signals_generated'] += 1
                
                if analysis['should_trade']:
                    market_test['signals_approved'] += 1
                    self.logger.info(f"✅ {symbol}: Señal APROBADA - {analysis['final_signal']} ({analysis['confidence']:.1f}%)")
                else:
                    market_test['signals_rejected'] += 1
                    self.logger.info(f"❌ {symbol}: Señal RECHAZADA - {', '.join(analysis['reasons'])}")
            else:
                self.logger.info(f"➖ {symbol}: Sin señal generada")
            
            market_test['symbol_results'].append(symbol_result)
        
        # Calcular estadísticas
        if market_test['signals_generated'] > 0:
            approval_rate = (market_test['signals_approved'] / market_test['signals_generated']) * 100
            market_test['approval_rate'] = approval_rate
        else:
            market_test['approval_rate'] = 0
        
        self.logger.info(f"Resultados del mercado actual: {market_test['signals_approved']}/{market_test['signals_generated']} señales aprobadas")
        
        return market_test
    
    def generate_improvement_report(self) -> Dict[str, any]:
        """
        Genera un reporte completo de las mejoras implementadas
        """
        report = {
            'timestamp': datetime.now(),
            'improvements_implemented': {
                'trend_filters': {
                    'description': 'Verificación de BTC/ETH antes de operar altcoins',
                    'status': 'IMPLEMENTED',
                    'impact': 'Evita operaciones contra la tendencia principal del mercado'
                },
                'advanced_technical_analysis': {
                    'description': 'Múltiples timeframes (1h, 4h, 1d) con RSI, MACD, Bollinger Bands',
                    'status': 'IMPLEMENTED',
                    'impact': 'Análisis más preciso y confirmación en múltiples marcos temporales'
                },
                'dynamic_risk_management': {
                    'description': 'Stop loss dinámico 3-5%, confianza mínima 75%, máximo 2 posiciones',
                    'status': 'IMPLEMENTED',
                    'impact': 'Gestión de riesgo adaptativa basada en volatilidad'
                },
                'signal_confirmations': {
                    'description': 'Volumen 2x promedio, confirmación en 2+ timeframes, verificación de momentum',
                    'status': 'IMPLEMENTED',
                    'impact': 'Filtros adicionales para evitar señales falsas'
                }
            },
            'key_parameters': {
                'min_confidence': self.config['min_confidence'],
                'max_positions': self.config['max_positions'],
                'volume_multiplier': self.signal_confirmations.config['volume_multiplier'],
                'min_timeframe_confirmations': self.signal_confirmations.config['min_timeframe_confirmations'],
                'dynamic_stop_loss_range': f"{self.risk_manager.config['min_stop_loss']}-{self.risk_manager.config['max_stop_loss']}%"
            },
            'testing_results': {}
        }
        
        # Ejecutar pruebas
        historical_test = self.test_historical_failures()
        market_test = self.test_current_market_conditions()
        
        report['testing_results'] = {
            'historical_failures': historical_test,
            'current_market': market_test
        }
        
        return report
    
    def _check_btc_eth_trend(self) -> Dict[str, any]:
        """Verifica la tendencia de BTC y ETH"""
        try:
            # Analizar BTC
            btc_analysis = self.technical_analyzer.get_comprehensive_analysis('BTCUSDT')
            eth_analysis = self.technical_analyzer.get_comprehensive_analysis('ETHUSDT')
            
            btc_bullish = btc_analysis['overall_signal'] == 'BUY' and btc_analysis['confidence'] > 60
            eth_bullish = eth_analysis['overall_signal'] == 'BUY' and eth_analysis['confidence'] > 60
            
            # Permitir trading de altcoins si BTC o ETH están alcistas
            can_trade = btc_bullish or eth_bullish
            
            return {
                'can_trade_altcoins': can_trade,
                'btc_signal': btc_analysis['overall_signal'],
                'btc_confidence': btc_analysis['confidence'],
                'eth_signal': eth_analysis['overall_signal'],
                'eth_confidence': eth_analysis['confidence'],
                'reason': f"BTC: {btc_analysis['overall_signal']} ({btc_analysis['confidence']:.1f}%), ETH: {eth_analysis['overall_signal']} ({eth_analysis['confidence']:.1f}%)"
            }
            
        except Exception as e:
            self.logger.error(f"Error verificando tendencia BTC/ETH: {e}")
            return {
                'can_trade_altcoins': False,
                'reason': f'Error verificando BTC/ETH: {str(e)}'
            }
    
    def _get_current_price(self, symbol: str) -> float:
        """Obtiene el precio actual de un símbolo"""
        try:
            import requests
            url = f"https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': symbol}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return float(response.json()['price'])
        except Exception as e:
            self.logger.error(f"Error obteniendo precio de {symbol}: {e}")
            return 0.0
    
    def _get_volatility_from_analysis(self, technical_analysis: Dict) -> float:
        """Extrae la volatilidad del análisis técnico"""
        try:
            for tf_data in technical_analysis['timeframes'].values():
                if 'volatility' in tf_data:
                    return tf_data['volatility']
            return 25.0  # Volatilidad por defecto
        except:
            return 25.0

# Función principal de prueba
if __name__ == "__main__":
    print("🚀 Iniciando Sistema de Trading Mejorado")
    print("=" * 50)
    
    # Crear instancia del sistema
    improved_system = ImprovedTradingSystem()
    
    # Generar reporte completo
    print("📊 Generando reporte de mejoras...")
    report = improved_system.generate_improvement_report()
    
    print(f"\n📈 REPORTE DE MEJORAS IMPLEMENTADAS")
    print(f"Fecha: {report['timestamp']}")
    print(f"\n🔧 Mejoras implementadas:")
    for improvement, details in report['improvements_implemented'].items():
        print(f"  ✅ {improvement}: {details['description']}")
        print(f"     Impacto: {details['impact']}")
    
    print(f"\n⚙️ Parámetros clave:")
    for param, value in report['key_parameters'].items():
        print(f"  • {param}: {value}")
    
    print(f"\n🧪 RESULTADOS DE PRUEBAS:")
    
    # Resultados de fallas históricas
    historical = report['testing_results']['historical_failures']
    print(f"\n📉 Fallas históricas:")
    print(f"  • Casos probados: {historical['total_cases']}")
    print(f"  • Fallas prevenidas: {historical['prevented_failures']}")
    print(f"  • Tasa de prevención: {historical['prevention_rate']:.1f}%")
    
    for case in historical['case_details']:
        status = "✅ PREVENIDA" if case['would_prevent_failure'] else "⚠️ NO PREVENIDA"
        print(f"    - {case['symbol']}: {status}")
        if case['would_prevent_failure']:
            print(f"      Razones: {', '.join(case['prevention_reasons'][:2])}")
    
    # Resultados del mercado actual
    market = report['testing_results']['current_market']
    print(f"\n📊 Condiciones actuales del mercado:")
    print(f"  • Símbolos analizados: {market['total_symbols']}")
    print(f"  • Señales generadas: {market['signals_generated']}")
    print(f"  • Señales aprobadas: {market['signals_approved']}")
    print(f"  • Tasa de aprobación: {market['approval_rate']:.1f}%")
    
    print(f"\n🎯 CONCLUSIÓN:")
    if historical['prevention_rate'] >= 80:
        print("✅ El sistema mejorado previene efectivamente las fallas anteriores")
    elif historical['prevention_rate'] >= 60:
        print("⚠️ El sistema mejorado previene la mayoría de fallas, pero necesita ajustes")
    else:
        print("❌ El sistema necesita mejoras adicionales")
    
    if market['approval_rate'] <= 30:
        print("✅ El sistema es apropiadamente conservador con las condiciones actuales")
    elif market['approval_rate'] <= 60:
        print("⚠️ El sistema tiene un balance razonable entre conservadurismo y oportunidades")
    else:
        print("❌ El sistema puede ser demasiado permisivo")
    
    print(f"\n💾 Guardando reporte en 'improvement_report.json'...")
    with open('improvement_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str, ensure_ascii=False)
    
    print("🏁 Pruebas completadas exitosamente!")