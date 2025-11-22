#!/usr/bin/env python3
"""
Sistema de Gestión de Riesgo Avanzada para SICAR
Sin apalancamiento - Enfoque en preservación de capital
Gestión dinámica de riesgo y optimización de portfolio
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Optimización de portfolio
from scipy.optimize import minimize
from scipy import stats

logger = logging.getLogger(__name__)

class AdvancedRiskManager:
    def __init__(self, initial_capital=10000):
        """Inicializar gestor de riesgo avanzado"""
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Parámetros de riesgo
        self.max_portfolio_risk = 0.02  # 2% VaR diario máximo
        self.max_position_size = 0.1    # 10% máximo por posición
        self.max_sector_exposure = 0.3  # 30% máximo por sector
        self.max_daily_loss = 0.05      # 5% pérdida diaria máxima
        self.max_drawdown = 0.15        # 15% drawdown máximo
        
        # Límites dinámicos
        self.dynamic_limits = {}
        self.risk_metrics = {}
        self.portfolio_state = {}
        
        # Histórico de riesgo
        self.risk_history = []
        self.drawdown_periods = []
        self.volatility_regimes = []
        
        logger.info("Gestor de riesgo avanzado inicializado")

    def calculate_var(self, returns, confidence_level=0.05):
        """Calcular Value at Risk (VaR)"""
        try:
            if len(returns) < 10:
                return 0
            
            # VaR paramétrico (asumiendo distribución normal)
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            var_parametric = mean_return - stats.norm.ppf(1 - confidence_level) * std_return
            
            # VaR histórico
            var_historical = np.percentile(returns, confidence_level * 100)
            
            # VaR modificado (Cornish-Fisher)
            skewness = stats.skew(returns)
            kurtosis = stats.kurtosis(returns)
            
            z_score = stats.norm.ppf(1 - confidence_level)
            z_cf = (z_score + 
                   (z_score**2 - 1) * skewness / 6 +
                   (z_score**3 - 3*z_score) * kurtosis / 24 -
                   (2*z_score**3 - 5*z_score) * skewness**2 / 36)
            
            var_modified = mean_return - z_cf * std_return
            
            # Usar el más conservador
            var_final = min(var_parametric, var_historical, var_modified)
            
            return var_final
            
        except Exception as e:
            logger.error(f"Error calculando VaR: {e}")
            return 0

    def calculate_expected_shortfall(self, returns, confidence_level=0.05):
        """Calcular Expected Shortfall (CVaR)"""
        try:
            if len(returns) < 10:
                return 0
            
            var = self.calculate_var(returns, confidence_level)
            
            # ES como promedio de pérdidas que exceden VaR
            tail_losses = returns[returns <= var]
            
            if len(tail_losses) > 0:
                expected_shortfall = np.mean(tail_losses)
            else:
                expected_shortfall = var
            
            return expected_shortfall
            
        except Exception as e:
            logger.error(f"Error calculando Expected Shortfall: {e}")
            return 0

    def detect_volatility_regime(self, returns, window=20):
        """Detectar régimen de volatilidad"""
        try:
            if len(returns) < window * 2:
                return 'normal'
            
            # Calcular volatilidad rolling
            rolling_vol = pd.Series(returns).rolling(window).std()
            current_vol = rolling_vol.iloc[-1]
            
            # Percentiles históricos
            vol_25 = rolling_vol.quantile(0.25)
            vol_75 = rolling_vol.quantile(0.75)
            
            # Clasificar régimen
            if current_vol <= vol_25:
                regime = 'low_vol'
            elif current_vol >= vol_75:
                regime = 'high_vol'
            else:
                regime = 'normal'
            
            return regime
            
        except Exception as e:
            logger.error(f"Error detectando régimen de volatilidad: {e}")
            return 'normal'

    def calculate_correlation_risk(self, positions, price_data):
        """Calcular riesgo de correlación del portfolio"""
        try:
            if len(positions) < 2:
                return 0
            
            # Obtener retornos de las posiciones
            returns_data = {}
            for symbol in positions.keys():
                if symbol in price_data:
                    prices = price_data[symbol]['close']
                    returns = prices.pct_change().dropna()
                    if len(returns) > 10:
                        returns_data[symbol] = returns
            
            if len(returns_data) < 2:
                return 0
            
            # Crear matriz de correlación
            returns_df = pd.DataFrame(returns_data)
            correlation_matrix = returns_df.corr()
            
            # Calcular riesgo de concentración
            # Eigenvalues de la matriz de correlación
            eigenvalues = np.linalg.eigvals(correlation_matrix)
            
            # Índice de diversificación
            diversification_ratio = len(eigenvalues) / np.sum(eigenvalues)
            
            # Riesgo de correlación (1 - diversification_ratio)
            correlation_risk = 1 - diversification_ratio
            
            return correlation_risk
            
        except Exception as e:
            logger.error(f"Error calculando riesgo de correlación: {e}")
            return 0

    def calculate_position_size(self, signal_strength, volatility, correlation_risk, 
                              current_positions, available_capital):
        """Calcular tamaño de posición con gestión de riesgo avanzada"""
        try:
            # Tamaño base según Kelly Criterion modificado
            win_rate = 0.6  # Estimado conservador
            avg_win = 0.03  # 3% ganancia promedio
            avg_loss = 0.02  # 2% pérdida promedio
            
            # Kelly fraction
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Limitar a 25%
            
            # Ajustar por fuerza de señal
            signal_multiplier = 0.5 + (signal_strength * 0.5)  # 0.5x a 1x
            
            # Ajustar por volatilidad
            vol_multiplier = max(0.3, 1 - (volatility * 5))  # Reducir en alta volatilidad
            
            # Ajustar por correlación
            corr_multiplier = max(0.5, 1 - correlation_risk)
            
            # Ajustar por concentración actual
            position_count = len(current_positions)
            concentration_multiplier = min(1.0, 5 / max(1, position_count))
            
            # Calcular tamaño final
            base_size = available_capital * kelly_fraction
            adjusted_size = (base_size * signal_multiplier * vol_multiplier * 
                           corr_multiplier * concentration_multiplier)
            
            # Aplicar límites absolutos
            max_position = available_capital * self.max_position_size
            final_size = min(adjusted_size, max_position)
            
            # Mínimo viable
            min_size = available_capital * 0.01  # 1% mínimo
            final_size = max(final_size, min_size)
            
            return final_size
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return available_capital * 0.02

    def check_risk_limits(self, proposed_trade, current_positions, portfolio_value):
        """Verificar límites de riesgo antes de ejecutar trade"""
        try:
            checks = {
                'position_size': True,
                'portfolio_concentration': True,
                'daily_loss': True,
                'var_limit': True,
                'correlation': True
            }
            
            # 1. Verificar tamaño de posición
            position_size_pct = proposed_trade['value'] / portfolio_value
            if position_size_pct > self.max_position_size:
                checks['position_size'] = False
                logger.warning(f"Posición excede límite: {position_size_pct:.1%} > {self.max_position_size:.1%}")
            
            # 2. Verificar concentración del portfolio
            symbol = proposed_trade['symbol']
            current_exposure = 0
            if symbol in current_positions:
                current_exposure = current_positions[symbol]['value'] / portfolio_value
            
            new_exposure = current_exposure + position_size_pct
            if new_exposure > self.max_position_size:
                checks['portfolio_concentration'] = False
                logger.warning(f"Concentración excede límite: {new_exposure:.1%}")
            
            # 3. Verificar pérdida diaria
            daily_pnl = self.calculate_daily_pnl(portfolio_value)
            daily_loss_pct = abs(daily_pnl) / self.initial_capital
            if daily_pnl < 0 and daily_loss_pct > self.max_daily_loss:
                checks['daily_loss'] = False
                logger.warning(f"Pérdida diaria excede límite: {daily_loss_pct:.1%}")
            
            # 4. Verificar VaR del portfolio
            portfolio_var = self.calculate_portfolio_var(current_positions, proposed_trade)
            if portfolio_var > self.max_portfolio_risk:
                checks['var_limit'] = False
                logger.warning(f"VaR excede límite: {portfolio_var:.1%}")
            
            # Resultado final
            all_checks_passed = all(checks.values())
            
            return all_checks_passed, checks
            
        except Exception as e:
            logger.error(f"Error verificando límites de riesgo: {e}")
            return False, {}

    def calculate_portfolio_var(self, current_positions, proposed_trade=None):
        """Calcular VaR del portfolio completo"""
        try:
            # Simplificado - en implementación real usaría datos históricos
            position_count = len(current_positions)
            if proposed_trade:
                position_count += 1
            
            # VaR base por diversificación
            base_var = 0.03  # 3% base
            diversification_factor = max(0.5, 1 / np.sqrt(position_count))
            
            portfolio_var = base_var * diversification_factor
            
            return portfolio_var
            
        except Exception as e:
            logger.error(f"Error calculando VaR del portfolio: {e}")
            return 0.05

    def calculate_daily_pnl(self, current_portfolio_value):
        """Calcular P&L diario"""
        try:
            if not hasattr(self, 'previous_portfolio_value'):
                self.previous_portfolio_value = self.initial_capital
            
            daily_pnl = current_portfolio_value - self.previous_portfolio_value
            self.previous_portfolio_value = current_portfolio_value
            
            return daily_pnl
            
        except Exception as e:
            logger.error(f"Error calculando P&L diario: {e}")
            return 0

    def calculate_stop_loss(self, entry_price, volatility, position_type='long'):
        """Calcular stop loss dinámico"""
        try:
            # Stop loss basado en ATR (Average True Range)
            base_stop = 0.02  # 2% base
            volatility_stop = volatility * 2  # 2x volatilidad
            
            # Usar el mayor para mayor protección
            stop_distance = max(base_stop, volatility_stop)
            
            if position_type == 'long':
                stop_loss = entry_price * (1 - stop_distance)
            else:  # short
                stop_loss = entry_price * (1 + stop_distance)
            
            return stop_loss
            
        except Exception as e:
            logger.error(f"Error calculando stop loss: {e}")
            return entry_price * 0.95 if position_type == 'long' else entry_price * 1.05

    def calculate_take_profit(self, entry_price, stop_loss, position_type='long', risk_reward_ratio=2.0):
        """Calcular take profit dinámico"""
        try:
            if position_type == 'long':
                risk = entry_price - stop_loss
                take_profit = entry_price + (risk * risk_reward_ratio)
            else:  # short
                risk = stop_loss - entry_price
                take_profit = entry_price - (risk * risk_reward_ratio)
            
            return take_profit
            
        except Exception as e:
            logger.error(f"Error calculando take profit: {e}")
            return entry_price * 1.04 if position_type == 'long' else entry_price * 0.96

    def update_dynamic_limits(self, portfolio_performance, market_conditions):
        """Actualizar límites dinámicos basados en performance"""
        try:
            # Ajustar límites según performance
            if portfolio_performance > 0.1:  # Si ganancia > 10%
                # Ser más agresivo
                self.max_position_size = min(0.15, self.max_position_size * 1.1)
                self.max_portfolio_risk = min(0.03, self.max_portfolio_risk * 1.1)
            elif portfolio_performance < -0.05:  # Si pérdida > 5%
                # Ser más conservador
                self.max_position_size = max(0.05, self.max_position_size * 0.9)
                self.max_portfolio_risk = max(0.01, self.max_portfolio_risk * 0.9)
            
            # Ajustar según condiciones de mercado
            if market_conditions.get('volatility_regime') == 'high_vol':
                self.max_position_size *= 0.8
                self.max_portfolio_risk *= 0.8
            elif market_conditions.get('volatility_regime') == 'low_vol':
                self.max_position_size *= 1.1
                self.max_portfolio_risk *= 1.1
            
            # Registrar cambios
            self.dynamic_limits[datetime.now()] = {
                'max_position_size': self.max_position_size,
                'max_portfolio_risk': self.max_portfolio_risk,
                'reason': f"Performance: {portfolio_performance:.1%}, Market: {market_conditions.get('volatility_regime', 'normal')}"
            }
            
        except Exception as e:
            logger.error(f"Error actualizando límites dinámicos: {e}")

    def emergency_stop(self, portfolio_value, reason=""):
        """Activar parada de emergencia"""
        try:
            current_drawdown = (self.initial_capital - portfolio_value) / self.initial_capital
            
            emergency_conditions = [
                current_drawdown > self.max_drawdown,
                portfolio_value < self.initial_capital * 0.8,  # 20% pérdida total
            ]
            
            if any(emergency_conditions):
                logger.critical(f"PARADA DE EMERGENCIA ACTIVADA: {reason}")
                logger.critical(f"Drawdown actual: {current_drawdown:.1%}")
                logger.critical(f"Valor portfolio: ${portfolio_value:,.2f}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error en parada de emergencia: {e}")
            return False

    def generate_risk_report(self):
        """Generar reporte de riesgo"""
        try:
            report = []
            report.append("=" * 60)
            report.append("REPORTE DE GESTIÓN DE RIESGO")
            report.append("=" * 60)
            report.append("")
            
            # Límites actuales
            report.append("LÍMITES ACTUALES:")
            report.append(f"Máximo por posición: {self.max_position_size:.1%}")
            report.append(f"Máximo riesgo portfolio: {self.max_portfolio_risk:.1%}")
            report.append(f"Máxima pérdida diaria: {self.max_daily_loss:.1%}")
            report.append(f"Máximo drawdown: {self.max_drawdown:.1%}")
            report.append("")
            
            # Métricas de riesgo
            if self.risk_metrics:
                report.append("MÉTRICAS DE RIESGO:")
                for metric, value in self.risk_metrics.items():
                    if isinstance(value, float):
                        report.append(f"{metric}: {value:.3f}")
                    else:
                        report.append(f"{metric}: {value}")
                report.append("")
            
            # Historial de límites dinámicos
            if self.dynamic_limits:
                report.append("HISTORIAL DE LÍMITES DINÁMICOS:")
                for timestamp, limits in list(self.dynamic_limits.items())[-5:]:
                    report.append(f"{timestamp}: {limits['reason']}")
                report.append("")
            
            report.append("=" * 60)
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Error generando reporte de riesgo: {e}")
            return "Error generando reporte"

    def optimize_portfolio_weights(self, expected_returns, covariance_matrix, risk_aversion=1.0):
        """Optimizar pesos del portfolio usando teoría moderna de portfolios"""
        try:
            n_assets = len(expected_returns)
            
            # Función objetivo: maximizar utilidad (retorno - riesgo)
            def objective(weights):
                portfolio_return = np.dot(weights, expected_returns)
                portfolio_variance = np.dot(weights.T, np.dot(covariance_matrix, weights))
                utility = portfolio_return - 0.5 * risk_aversion * portfolio_variance
                return -utility  # Minimizar el negativo
            
            # Restricciones
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # Suma = 1
            ]
            
            # Límites (0 a max_position_size por activo)
            bounds = [(0, self.max_position_size) for _ in range(n_assets)]
            
            # Pesos iniciales iguales
            initial_weights = np.array([1/n_assets] * n_assets)
            
            # Optimizar
            result = minimize(
                objective, initial_weights, method='SLSQP',
                bounds=bounds, constraints=constraints
            )
            
            if result.success:
                return result.x
            else:
                logger.warning("Optimización de portfolio falló, usando pesos iguales")
                return initial_weights
            
        except Exception as e:
            logger.error(f"Error optimizando portfolio: {e}")
            return np.array([1/len(expected_returns)] * len(expected_returns))

def main():
    """Función de prueba"""
    try:
        # Crear gestor de riesgo
        risk_manager = AdvancedRiskManager(initial_capital=10000)
        
        # Simular datos de prueba
        returns = np.random.normal(0.001, 0.02, 100)  # Retornos diarios simulados
        
        # Calcular métricas de riesgo
        var = risk_manager.calculate_var(returns)
        es = risk_manager.calculate_expected_shortfall(returns)
        regime = risk_manager.detect_volatility_regime(returns)
        
        print(f"VaR (5%): {var:.4f}")
        print(f"Expected Shortfall: {es:.4f}")
        print(f"Régimen de volatilidad: {regime}")
        
        # Simular trade propuesto
        proposed_trade = {
            'symbol': 'BTC-USD',
            'value': 1000,
            'type': 'long'
        }
        
        current_positions = {}
        portfolio_value = 10000
        
        # Verificar límites
        passed, checks = risk_manager.check_risk_limits(
            proposed_trade, current_positions, portfolio_value
        )
        
        print(f"Límites de riesgo pasados: {passed}")
        print(f"Verificaciones: {checks}")
        
        # Generar reporte
        report = risk_manager.generate_risk_report()
        print("\n" + report)
        
        print("Prueba de gestión de riesgo completada")
        
    except Exception as e:
        print(f"Error en prueba: {e}")

if __name__ == "__main__":
    main()