#!/usr/bin/env python3
"""
Sistema de Arbitraje SICAR - Estrategia Avanzada
Aprovecha diferencias de precios entre exchanges simulados
Objetivo: 15% ROI mensual con apalancamiento
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arbitrage_sicar_system.log'),
        logging.StreamHandler()
    ]
)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.robust_data_fetcher import RobustDataFetcher

class ArbitrageSicarSystem:
    def __init__(self, initial_capital=500, leverage=1.0):
        """
        Sistema de Arbitraje con SICAR
        
        Args:
            initial_capital: Capital inicial en USD
            leverage: Apalancamiento (4x para mayor agresividad)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.leverage = leverage
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Configuración de arbitraje
        self.min_spread = 0.002  # 0.2% spread mínimo
        self.max_position_size = 0.15  # 15% del capital por posición
        self.exchanges = ['binance', 'coinbase', 'kraken']  # Exchanges simulados
        
        # Tracking
        self.operations = []
        self.positions = {}
        self.total_fees = 0
        
        logging.info(f"🚀 Sistema de Arbitraje SICAR iniciado")
        logging.info(f"💰 Capital inicial: ${initial_capital}")
        logging.info(f"⚡ Apalancamiento: {leverage}x")
        logging.info(f"📊 Spread mínimo: {self.min_spread*100:.2f}%")

    def simulate_exchange_prices(self, base_price, volatility=0.001):
        """
        Simula precios en diferentes exchanges con spreads realistas
        
        Args:
            base_price: Precio base del activo
            volatility: Volatilidad entre exchanges
            
        Returns:
            dict: Precios por exchange
        """
        prices = {}
        
        # Binance (referencia)
        prices['binance'] = base_price
        
        # Coinbase (típicamente más alto)
        prices['coinbase'] = base_price * (1 + np.random.normal(0.0005, volatility))
        
        # Kraken (puede variar)
        prices['kraken'] = base_price * (1 + np.random.normal(0, volatility * 1.2))
        
        return prices

    def find_arbitrage_opportunities(self, prices):
        """
        Encuentra oportunidades de arbitraje entre exchanges
        
        Args:
            prices: Diccionario de precios por exchange
            
        Returns:
            list: Lista de oportunidades de arbitraje
        """
        opportunities = []
        
        exchanges = list(prices.keys())
        
        for i, buy_exchange in enumerate(exchanges):
            for j, sell_exchange in enumerate(exchanges):
                if i != j:
                    buy_price = prices[buy_exchange]
                    sell_price = prices[sell_exchange]
                    
                    # Calcular spread
                    spread = (sell_price - buy_price) / buy_price
                    
                    # Verificar si es rentable después de fees
                    net_spread = spread - (2 * self.fee_rate)  # Fees de compra y venta
                    
                    if net_spread > self.min_spread:
                        opportunities.append({
                            'buy_exchange': buy_exchange,
                            'sell_exchange': sell_exchange,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'spread': spread,
                            'net_spread': net_spread,
                            'profit_potential': net_spread * 100
                        })
        
        # Ordenar por rentabilidad
        opportunities.sort(key=lambda x: x['net_spread'], reverse=True)
        
        return opportunities

    def calculate_position_size(self, opportunity):
        """
        Calcula el tamaño de posición óptimo para arbitraje
        
        Args:
            opportunity: Oportunidad de arbitraje
            
        Returns:
            float: Tamaño de posición en USD
        """
        # Tamaño base según capital disponible
        base_size = self.current_capital * self.max_position_size
        
        # Ajustar según rentabilidad de la oportunidad
        profit_multiplier = min(opportunity['net_spread'] / self.min_spread, 3.0)
        
        # Aplicar apalancamiento
        position_size = base_size * profit_multiplier * self.leverage
        
        # Limitar al capital disponible con apalancamiento
        max_size = self.current_capital * self.leverage * 0.8  # 80% del capital apalancado
        
        return min(position_size, max_size)

    def execute_arbitrage(self, opportunity, position_size, timestamp):
        """
        Ejecuta una operación de arbitraje
        
        Args:
            opportunity: Oportunidad de arbitraje
            position_size: Tamaño de la posición
            timestamp: Timestamp de la operación
        """
        # Calcular cantidad de activo
        quantity = position_size / opportunity['buy_price']
        
        # Fees
        buy_fee = position_size * self.fee_rate
        sell_fee = (quantity * opportunity['sell_price']) * self.fee_rate
        total_fee = buy_fee + sell_fee
        
        # PnL bruto
        gross_pnl = quantity * (opportunity['sell_price'] - opportunity['buy_price'])
        
        # PnL neto
        net_pnl = gross_pnl - total_fee
        
        # Actualizar capital
        self.current_capital += net_pnl
        self.total_fees += total_fee
        
        # Registrar operación
        operation = {
            'timestamp': timestamp,
            'type': 'ARBITRAGE',
            'buy_exchange': opportunity['buy_exchange'],
            'sell_exchange': opportunity['sell_exchange'],
            'buy_price': opportunity['buy_price'],
            'sell_price': opportunity['sell_price'],
            'quantity': quantity,
            'position_size': position_size,
            'spread': opportunity['spread'],
            'net_spread': opportunity['net_spread'],
            'gross_pnl': gross_pnl,
            'fees': total_fee,
            'net_pnl': net_pnl,
            'capital_after': self.current_capital,
            'profit_pct': (net_pnl / position_size) * 100
        }
        
        self.operations.append(operation)
        
        logging.info(f"⚡ ARBITRAGE: {opportunity['buy_exchange']} → {opportunity['sell_exchange']} | "
                    f"Spread: {opportunity['spread']*100:.3f}% | PnL: ${net_pnl:.2f}")

    def run_backtest(self, symbol='BTCUSDT', days=60):
        """
        Ejecuta backtest del sistema de arbitraje
        
        Args:
            symbol: Par de trading
            days: Días de backtest
        """
        logging.info(f"🔄 Iniciando backtest de arbitraje para {symbol}")
        
        # Obtener datos
        fetcher = RobustDataFetcher()
        data = fetcher.get_market_data(symbol, '1h', limit=days*24)
        
        if data is None or data.empty:
            logging.error(f"❌ No se pudieron obtener datos para {symbol}")
            return
        
        # Normalizar datos
        data.columns = data.columns.str.lower()
        if data.index.name == 'timestamp' or 'timestamp' in str(data.index.name).lower():
            data.reset_index(inplace=True)
        
        logging.info(f"📊 Datos obtenidos: {len(data)} velas de 1h")
        
        # Procesar cada vela
        for idx, row in data.iterrows():
            if idx < 20:  # Período de calentamiento
                continue
                
            current_price = row['close']
            timestamp = row.get('timestamp', idx)
            
            # Simular precios en diferentes exchanges
            exchange_prices = self.simulate_exchange_prices(current_price)
            
            # Buscar oportunidades de arbitraje
            opportunities = self.find_arbitrage_opportunities(exchange_prices)
            
            # Ejecutar las mejores oportunidades
            for opportunity in opportunities[:2]:  # Máximo 2 operaciones por hora
                if opportunity['net_spread'] > self.min_spread:
                    position_size = self.calculate_position_size(opportunity)
                    
                    if position_size > 50:  # Mínimo $50 por operación
                        self.execute_arbitrage(opportunity, position_size, timestamp)
        
        # Calcular métricas finales
        self.calculate_final_metrics(days)

    def calculate_final_metrics(self, days):
        """Calcula métricas finales del backtest"""
        if not self.operations:
            logging.warning("⚠️ No se generaron operaciones de arbitraje")
            return
        
        # Métricas básicas
        total_operations = len(self.operations)
        winning_ops = len([op for op in self.operations if op['net_pnl'] > 0])
        losing_ops = total_operations - winning_ops
        win_rate = (winning_ops / total_operations) * 100 if total_operations > 0 else 0
        
        # Retornos
        gross_pnl = sum(op['gross_pnl'] for op in self.operations)
        net_pnl = self.current_capital - self.initial_capital
        net_return = (net_pnl / self.initial_capital) * 100
        
        # ROI mensual
        months = days / 30.44
        monthly_roi = (((self.current_capital / self.initial_capital) ** (1/months)) - 1) * 100
        
        # Gap al objetivo
        target_roi = 15.0
        roi_gap = target_roi - monthly_roi
        
        # Logging de resultados
        logging.info("=" * 80)
        logging.info("RESULTADOS SISTEMA DE ARBITRAJE SICAR")
        logging.info("=" * 80)
        logging.info(f"💰 Capital inicial: ${self.initial_capital:.2f}")
        logging.info(f"💰 Capital final: ${self.current_capital:.2f}")
        logging.info(f"📈 PnL bruto: ${gross_pnl:.2f}")
        logging.info(f"💸 Fees totales: ${self.total_fees:.2f}")
        logging.info(f"💵 PnL neto: ${net_pnl:.2f}")
        logging.info(f"📊 Retorno neto: {net_return:.2f}%")
        logging.info(f"🎯 ROI mensual: {monthly_roi:.2f}%")
        logging.info(f"🔄 Total operaciones: {total_operations}")
        logging.info(f"✅ Operaciones ganadoras: {winning_ops}")
        logging.info(f"❌ Operaciones perdedoras: {losing_ops}")
        logging.info(f"🏆 Win rate: {win_rate:.1f}%")
        logging.info(f"📅 Duración: {days} días ({months:.1f} meses)")
        logging.info(f"⚡ Apalancamiento: {self.leverage}x")
        logging.info(f"⚡ Gap al objetivo: {roi_gap:.2f}% (Objetivo: {target_roi}%)")
        logging.info("=" * 80)
        
        # Guardar resultados
        self.save_results()
        
        # Resumen final
        print(f"\n✅ Backtest de arbitraje completado!")
        print(f"📊 ROI mensual: {monthly_roi:.2f}%")
        print(f"🎯 Objetivo: {target_roi}%")
        print(f"🔄 Total operaciones: {total_operations}")
        print(f"🏆 Win rate: {win_rate:.1f}%")
        print(f"⚡ Apalancamiento: {self.leverage}x")
        print(f"📁 Resultados guardados en: arbitrage_sicar_results.csv")

    def save_results(self):
        """Guarda los resultados en CSV"""
        if self.operations:
            df = pd.DataFrame(self.operations)
            df.to_csv('arbitrage_sicar_results.csv', index=False)
            logging.info("💾 Resultados guardados en arbitrage_sicar_results.csv")

def main():
    """Función principal"""
    try:
        # Crear y ejecutar sistema de arbitraje
        system = ArbitrageSicarSystem(
            initial_capital=500,
            leverage=4.0  # Apalancamiento agresivo para arbitraje
        )
        
        # Ejecutar backtest
        system.run_backtest(symbol='BTCUSDT', days=60)
        
    except Exception as e:
        logging.error(f"❌ Error en sistema de arbitraje: {str(e)}")
        raise

if __name__ == "__main__":
    main()