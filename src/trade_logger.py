# /src/trade_logger.py

import os
import json
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Configurar logging específico para trades
trade_logger = logging.getLogger('trade_logger')
trade_logger.setLevel(logging.INFO)

# Crear handler para archivo de trades si no existe
if not trade_logger.handlers:
    # Crear directorio de logs si no existe
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Handler para archivo de trades
    trade_file_handler = logging.FileHandler(
        os.path.join(log_dir, 'trades_detailed.log'),
        encoding='utf-8'
    )
    trade_file_handler.setLevel(logging.INFO)
    
    # Handler para archivo JSON de trades
    json_file_handler = logging.FileHandler(
        os.path.join(log_dir, 'trades_data.jsonl'),
        encoding='utf-8'
    )
    json_file_handler.setLevel(logging.INFO)
    
    # Formato para logs de texto
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    trade_file_handler.setFormatter(formatter)
    
    # Agregar handlers
    trade_logger.addHandler(trade_file_handler)
    trade_logger.addHandler(json_file_handler)

class TradeLogger:
    """
    Sistema de logging detallado para operaciones de trading con coordenadas exactas.
    """
    
    def __init__(self):
        self.trades_history = []
        self.current_trade_id = 0
        
    def log_trade_entry(
        self,
        symbol: str,
        position_type: str,
        entry_price: float,
        position_size: float,
        stop_loss: float,
        take_profit: float,
        strategy: str,
        confidence: float,
        regime: str,
        analysis_results: Dict[str, Any],
        order_id: Optional[str] = None,
        is_simulation: bool = True
    ) -> str:
        """
        Registra la entrada de una operación con coordenadas exactas.
        
        Args:
            symbol: Símbolo del activo
            position_type: Tipo de posición ('long' o 'short')
            entry_price: Precio de entrada exacto
            position_size: Tamaño de la posición
            stop_loss: Precio de stop loss
            take_profit: Precio de take profit
            strategy: Estrategia utilizada
            confidence: Nivel de confianza
            regime: Régimen de mercado
            analysis_results: Resultados completos del análisis
            order_id: ID de la orden (si aplica)
            is_simulation: Si es simulación o trading real
            
        Returns:
            ID único del trade
        """
        try:
            self.current_trade_id += 1
            trade_id = f"TRADE_{self.current_trade_id:06d}"
            
            # Calcular coordenadas técnicas
            risk_reward_ratio = abs(take_profit - entry_price) / abs(entry_price - stop_loss)
            risk_amount = abs(entry_price - stop_loss) / entry_price
            potential_profit = abs(take_profit - entry_price) / entry_price
            
            # Extraer indicadores técnicos del análisis
            technical_indicators = self._extract_technical_indicators(analysis_results)
            
            # Crear registro detallado
            trade_entry = {
                'trade_id': trade_id,
                'timestamp': datetime.now().isoformat(),
                'action': 'ENTRY',
                'symbol': symbol,
                'position_type': position_type.upper(),
                
                # Coordenadas exactas de entrada
                'entry_coordinates': {
                    'price': entry_price,
                    'timestamp': datetime.now().isoformat(),
                    'position_size': position_size,
                    'position_value': entry_price * position_size
                },
                
                # Coordenadas de gestión de riesgo
                'risk_coordinates': {
                    'stop_loss_price': stop_loss,
                    'take_profit_price': take_profit,
                    'risk_reward_ratio': risk_reward_ratio,
                    'risk_percentage': risk_amount * 100,
                    'potential_profit_percentage': potential_profit * 100,
                    'max_loss_amount': abs(entry_price - stop_loss) * position_size,
                    'max_profit_amount': abs(take_profit - entry_price) * position_size
                },
                
                # Contexto de la decisión
                'decision_context': {
                    'strategy': strategy,
                    'confidence': confidence,
                    'regime': regime,
                    'signal_strength': analysis_results.get('strategy_decision', {}).get('signal', 0.0)
                },
                
                # Indicadores técnicos en el momento de entrada
                'technical_context': technical_indicators,
                
                # Información de la orden
                'order_info': {
                    'order_id': order_id,
                    'is_simulation': is_simulation,
                    'execution_type': 'SIMULATION' if is_simulation else 'REAL'
                },
                
                # Análisis multi-timeframe (si está disponible)
                'multi_timeframe_analysis': self._extract_multi_timeframe_data(analysis_results)
            }
            
            # Agregar a historial
            self.trades_history.append(trade_entry)
            
            # Log en formato texto
            trade_logger.info(f"""
=== ENTRADA DE OPERACIÓN ===
Trade ID: {trade_id}
Símbolo: {symbol}
Tipo: {position_type.upper()}
Precio de Entrada: ${entry_price:.6f}
Tamaño: {position_size:.6f}
Valor de Posición: ${entry_price * position_size:.2f}
Stop Loss: ${stop_loss:.6f} ({risk_amount:.2%} riesgo)
Take Profit: ${take_profit:.6f} ({potential_profit:.2%} ganancia)
Risk/Reward: 1:{risk_reward_ratio:.2f}
Estrategia: {strategy}
Confianza: {confidence:.1%}
Régimen: {regime}
Modo: {'SIMULACIÓN' if is_simulation else 'REAL'}
""")
            
            # Log en formato JSON para análisis posterior
            json_handler = trade_logger.handlers[1]  # Handler JSON
            json_handler.emit(logging.LogRecord(
                name='trade_logger',
                level=logging.INFO,
                pathname='',
                lineno=0,
                msg=json.dumps(trade_entry, ensure_ascii=False),
                args=(),
                exc_info=None
            ))
            
            return trade_id
            
        except Exception as e:
            trade_logger.error(f"Error registrando entrada de trade: {str(e)}")
            return f"ERROR_{self.current_trade_id}"
    
    def log_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str,
        pnl_percentage: float,
        pnl_amount: float,
        portfolio_value: float,
        close_order_id: Optional[str] = None,
        is_simulation: bool = True,
        additional_context: Optional[Dict] = None
    ):
        """
        Registra la salida de una operación con coordenadas exactas.
        
        Args:
            trade_id: ID del trade
            exit_price: Precio de salida exacto
            exit_reason: Razón de la salida
            pnl_percentage: PnL en porcentaje
            pnl_amount: PnL en cantidad absoluta
            portfolio_value: Valor actual del portafolio
            close_order_id: ID de la orden de cierre
            is_simulation: Si es simulación
            additional_context: Contexto adicional
        """
        try:
            # Buscar el trade de entrada correspondiente
            entry_trade = None
            for trade in self.trades_history:
                if trade['trade_id'] == trade_id and trade['action'] == 'ENTRY':
                    entry_trade = trade
                    break
            
            if not entry_trade:
                trade_logger.error(f"No se encontró trade de entrada para ID: {trade_id}")
                return
            
            # Calcular métricas de la operación
            entry_price = entry_trade['entry_coordinates']['price']
            position_size = entry_trade['entry_coordinates']['position_size']
            duration = (datetime.now() - datetime.fromisoformat(entry_trade['timestamp'])).total_seconds()
            
            # Determinar si se alcanzó stop loss o take profit
            stop_loss = entry_trade['risk_coordinates']['stop_loss_price']
            take_profit = entry_trade['risk_coordinates']['take_profit_price']
            
            hit_stop_loss = False
            hit_take_profit = False
            
            if entry_trade['position_type'] == 'LONG':
                hit_stop_loss = exit_price <= stop_loss * 1.001  # Pequeño margen de tolerancia
                hit_take_profit = exit_price >= take_profit * 0.999
            else:  # SHORT
                hit_stop_loss = exit_price >= stop_loss * 0.999
                hit_take_profit = exit_price <= take_profit * 1.001
            
            # Crear registro de salida
            trade_exit = {
                'trade_id': trade_id,
                'timestamp': datetime.now().isoformat(),
                'action': 'EXIT',
                
                # Coordenadas exactas de salida
                'exit_coordinates': {
                    'price': exit_price,
                    'timestamp': datetime.now().isoformat(),
                    'position_size': position_size,
                    'position_value': exit_price * position_size
                },
                
                # Resultados de la operación
                'trade_results': {
                    'pnl_percentage': pnl_percentage,
                    'pnl_amount': pnl_amount,
                    'duration_seconds': duration,
                    'duration_hours': duration / 3600,
                    'exit_reason': exit_reason,
                    'hit_stop_loss': hit_stop_loss,
                    'hit_take_profit': hit_take_profit,
                    'portfolio_value_after': portfolio_value
                },
                
                # Análisis de ejecución
                'execution_analysis': {
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'price_movement': (exit_price - entry_price) / entry_price,
                    'slippage': 0.0,  # Calcular si hay datos de orden real
                    'execution_quality': self._assess_execution_quality(entry_trade, exit_price, exit_reason)
                },
                
                # Información de la orden de cierre
                'close_order_info': {
                    'close_order_id': close_order_id,
                    'is_simulation': is_simulation,
                    'execution_type': 'SIMULATION' if is_simulation else 'REAL'
                },
                
                # Contexto adicional
                'additional_context': additional_context or {}
            }
            
            # Agregar a historial
            self.trades_history.append(trade_exit)
            
            # Log en formato texto
            trade_logger.info(f"""
=== SALIDA DE OPERACIÓN ===
Trade ID: {trade_id}
Precio de Salida: ${exit_price:.6f}
Razón: {exit_reason}
PnL: {pnl_percentage:.2%} (${pnl_amount:.2f})
Duración: {duration/3600:.1f} horas
Stop Loss Alcanzado: {'SÍ' if hit_stop_loss else 'NO'}
Take Profit Alcanzado: {'SÍ' if hit_take_profit else 'NO'}
Valor del Portafolio: ${portfolio_value:.2f}
Modo: {'SIMULACIÓN' if is_simulation else 'REAL'}
""")
            
            # Log en formato JSON
            json_handler = trade_logger.handlers[1]
            json_handler.emit(logging.LogRecord(
                name='trade_logger',
                level=logging.INFO,
                pathname='',
                lineno=0,
                msg=json.dumps(trade_exit, ensure_ascii=False),
                args=(),
                exc_info=None
            ))
            
        except Exception as e:
            trade_logger.error(f"Error registrando salida de trade: {str(e)}")
    
    def _extract_technical_indicators(self, analysis_results: Dict) -> Dict:
        """Extrae indicadores técnicos del análisis."""
        try:
            indicators = {}
            
            # Extraer de diferentes fuentes en analysis_results
            if 'market_data' in analysis_results:
                # Agregar indicadores básicos si están disponibles
                pass
            
            if 'regime_analysis' in analysis_results:
                regime_data = analysis_results['regime_analysis']
                indicators['regime_confidence'] = regime_data.get('confidence', 0.0)
                indicators['volatility'] = regime_data.get('volatility', 0.0)
            
            if 'strategy_decision' in analysis_results:
                strategy_data = analysis_results['strategy_decision']
                indicators['signal_strength'] = strategy_data.get('signal', 0.0)
                indicators['strategy_confidence'] = strategy_data.get('confidence', 0.0)
            
            return indicators
            
        except Exception as e:
            trade_logger.error(f"Error extrayendo indicadores técnicos: {str(e)}")
            return {}
    
    def _extract_multi_timeframe_data(self, analysis_results: Dict) -> Dict:
        """Extrae datos del análisis multi-timeframe."""
        try:
            multi_tf_data = {}
            
            if 'timeframe_results' in analysis_results:
                tf_results = analysis_results['timeframe_results']
                for tf, data in tf_results.items():
                    multi_tf_data[tf] = {
                        'regime': data.get('regime_analysis', {}).get('regime_name', 'unknown'),
                        'strategy': data.get('strategy_decision', {}).get('strategy', 'hold'),
                        'confidence': data.get('strategy_decision', {}).get('confidence', 0.0),
                        'signal': data.get('strategy_decision', {}).get('signal', 0.0)
                    }
            
            if 'final_consensus' in analysis_results:
                multi_tf_data['consensus'] = analysis_results['final_consensus']
            
            return multi_tf_data
            
        except Exception as e:
            trade_logger.error(f"Error extrayendo datos multi-timeframe: {str(e)}")
            return {}
    
    def _assess_execution_quality(self, entry_trade: Dict, exit_price: float, exit_reason: str) -> str:
        """Evalúa la calidad de la ejecución del trade."""
        try:
            entry_price = entry_trade['entry_coordinates']['price']
            stop_loss = entry_trade['risk_coordinates']['stop_loss_price']
            take_profit = entry_trade['risk_coordinates']['take_profit_price']
            position_type = entry_trade['position_type']
            
            if exit_reason == 'take_profit':
                return 'EXCELLENT'
            elif exit_reason == 'stop_loss':
                return 'CONTROLLED_LOSS'
            else:
                # Evaluar si la salida manual fue buena
                if position_type == 'LONG':
                    if exit_price > entry_price:
                        return 'GOOD_MANUAL_EXIT'
                    else:
                        return 'POOR_MANUAL_EXIT'
                else:  # SHORT
                    if exit_price < entry_price:
                        return 'GOOD_MANUAL_EXIT'
                    else:
                        return 'POOR_MANUAL_EXIT'
                        
        except Exception as e:
            trade_logger.error(f"Error evaluando calidad de ejecución: {str(e)}")
            return 'UNKNOWN'
    
    def get_trades_summary(self) -> Dict:
        """Obtiene un resumen de todas las operaciones."""
        try:
            entries = [t for t in self.trades_history if t['action'] == 'ENTRY']
            exits = [t for t in self.trades_history if t['action'] == 'EXIT']
            
            total_trades = len(exits)
            if total_trades == 0:
                return {'total_trades': 0, 'message': 'No hay trades completados'}
            
            # Calcular métricas
            total_pnl = sum(t['trade_results']['pnl_amount'] for t in exits)
            winning_trades = len([t for t in exits if t['trade_results']['pnl_amount'] > 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            avg_duration = sum(t['trade_results']['duration_hours'] for t in exits) / total_trades
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'average_duration_hours': avg_duration,
                'last_portfolio_value': exits[-1]['trade_results']['portfolio_value_after'] if exits else 0
            }
            
        except Exception as e:
            trade_logger.error(f"Error generando resumen de trades: {str(e)}")
            return {'error': str(e)}
    
    def export_trades_to_csv(self, filename: Optional[str] = None) -> str:
        """Exporta los trades a un archivo CSV para análisis."""
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'trades_export_{timestamp}.csv'
            
            # Preparar datos para CSV
            csv_data = []
            
            # Combinar entradas y salidas
            trade_pairs = {}
            for trade in self.trades_history:
                trade_id = trade['trade_id']
                if trade_id not in trade_pairs:
                    trade_pairs[trade_id] = {}
                trade_pairs[trade_id][trade['action']] = trade
            
            # Crear filas para CSV
            for trade_id, pair in trade_pairs.items():
                if 'ENTRY' in pair and 'EXIT' in pair:
                    entry = pair['ENTRY']
                    exit_data = pair['EXIT']
                    
                    csv_row = {
                        'trade_id': trade_id,
                        'symbol': entry['symbol'],
                        'position_type': entry['position_type'],
                        'entry_timestamp': entry['timestamp'],
                        'entry_price': entry['entry_coordinates']['price'],
                        'position_size': entry['entry_coordinates']['position_size'],
                        'stop_loss': entry['risk_coordinates']['stop_loss_price'],
                        'take_profit': entry['risk_coordinates']['take_profit_price'],
                        'strategy': entry['decision_context']['strategy'],
                        'confidence': entry['decision_context']['confidence'],
                        'regime': entry['decision_context']['regime'],
                        'exit_timestamp': exit_data['timestamp'],
                        'exit_price': exit_data['exit_coordinates']['price'],
                        'exit_reason': exit_data['trade_results']['exit_reason'],
                        'pnl_percentage': exit_data['trade_results']['pnl_percentage'],
                        'pnl_amount': exit_data['trade_results']['pnl_amount'],
                        'duration_hours': exit_data['trade_results']['duration_hours'],
                        'hit_stop_loss': exit_data['trade_results']['hit_stop_loss'],
                        'hit_take_profit': exit_data['trade_results']['hit_take_profit'],
                        'execution_quality': exit_data['execution_analysis']['execution_quality']
                    }
                    csv_data.append(csv_row)
            
            # Crear DataFrame y exportar
            df = pd.DataFrame(csv_data)
            
            # Crear directorio de reportes si no existe
            reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            filepath = os.path.join(reports_dir, filename)
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            trade_logger.info(f"Trades exportados a: {filepath}")
            return filepath
            
        except Exception as e:
            trade_logger.error(f"Error exportando trades a CSV: {str(e)}")
            return ""

# Instancia global del logger
trade_logger_instance = TradeLogger()