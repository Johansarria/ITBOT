#!/usr/bin/env python3
"""
Sistema de Market Making SICAR - Estrategia Avanzada
Proporciona liquidez al mercado con spreads dinámicos
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
        logging.FileHandler('market_making_sicar_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.robust_data_fetcher import RobustDataFetcher

class MarketMakingSicarSystem:
    def __init__(self, initial_capital=500, leverage=1.0):
        """
        Sistema de Market Making con SICAR
        
        Args:
            initial_capital: Capital inicial en USD
            leverage: Apalancamiento (5x para market making agresivo)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.leverage = leverage
        self.fee_rate = 0.0005  # 0.05% por operación (maker fee)
        
        # Configuración de market making
        self.base_spread = 0.001  # 0.1% spread base
        self.max_spread = 0.005   # 0.5% spread máximo
        self.min_spread = 0.0005  # 0.05% spread mínimo
        self.inventory_target = 0.5  # 50% del capital en inventario
        self.max_position_size = 0.2  # 20% del capital por posición
        
        # Parámetros dinámicos
        self.volatility_multiplier = 2.0
        self.volume_threshold = 1000000  # Umbral de volumen
        self.rebalance_threshold = 0.1   # 10% desbalance para rebalancear
        
        # Tracking
        self.operations = []
        self.positions = {}
        self.inventory = {'base': 0, 'quote': 0}
        self.total_fees = 0
        self.active_orders = {'buy': [], 'sell': []}
        
        logging.info(f"🚀 Sistema de Market Making SICAR iniciado")
        logging.info(f"💰 Capital inicial: ${initial_capital}")
        logging.info(f"⚡ Apalancamiento: {leverage}x")
        logging.info(f"📊 Spread base: {self.base_spread*100:.3f}%")

    def calculate_volatility(self, data, window=20):
        """
        Calcula la volatilidad del mercado
        
        Args:
            data: DataFrame con datos de precios
            window: Ventana para calcular volatilidad
            
        Returns:
            float: Volatilidad normalizada
        """
        if len(data) < window:
            return 0.01  # Volatilidad por defecto
        
        returns = data['close'].pct_change().dropna()
        volatility = returns.rolling(window=window).std().iloc[-1]
        
        return min(max(volatility, 0.005), 0.05)  # Entre 0.5% y 5%

    def calculate_dynamic_spread(self, current_price, volatility, volume):
        """
        Calcula el spread dinámico basado en condiciones de mercado
        
        Args:
            current_price: Precio actual
            volatility: Volatilidad del mercado
            volume: Volumen de trading
            
        Returns:
            float: Spread dinámico
        """
        # Spread base ajustado por volatilidad
        volatility_spread = self.base_spread * (1 + volatility * self.volatility_multiplier)
        
        # Ajuste por volumen (menor volumen = mayor spread)
        volume_factor = max(0.5, min(2.0, self.volume_threshold / max(volume, 1)))
        volume_spread = volatility_spread * volume_factor
        
        # Ajuste por inventario (desequilibrio = mayor spread)
        inventory_imbalance = abs(self.inventory['base'] - self.inventory['quote']) / max(self.current_capital, 1)
        inventory_factor = 1 + inventory_imbalance
        
        final_spread = volume_spread * inventory_factor
        
        # Limitar spread entre mínimo y máximo
        return max(self.min_spread, min(final_spread, self.max_spread))

    def calculate_optimal_quotes(self, current_price, spread):
        """
        Calcula las cotizaciones óptimas de compra y venta
        
        Args:
            current_price: Precio actual del mercado
            spread: Spread a aplicar
            
        Returns:
            tuple: (precio_compra, precio_venta)
        """
        half_spread = spread / 2
        
        buy_price = current_price * (1 - half_spread)
        sell_price = current_price * (1 + half_spread)
        
        return buy_price, sell_price

    def calculate_position_size(self, price, side):
        """
        Calcula el tamaño de posición óptimo para market making
        
        Args:
            price: Precio de la orden
            side: 'buy' o 'sell'
            
        Returns:
            float: Tamaño de posición en USD
        """
        # Tamaño base
        base_size = self.current_capital * self.max_position_size
        
        # Ajustar según inventario
        if side == 'buy':
            # Si tenemos mucho quote, reducir compras
            quote_ratio = self.inventory['quote'] / max(self.current_capital, 1)
            size_factor = max(0.3, 1 - quote_ratio)
        else:
            # Si tenemos mucho base, reducir ventas
            base_ratio = self.inventory['base'] / max(self.current_capital, 1)
            size_factor = max(0.3, 1 - base_ratio)
        
        # Aplicar apalancamiento
        position_size = base_size * size_factor * self.leverage
        
        # Limitar al capital disponible
        max_size = self.current_capital * self.leverage * 0.3  # 30% del capital apalancado
        
        return min(position_size, max_size)

    def execute_market_making_cycle(self, current_price, volatility, volume, timestamp):
        """
        Ejecuta un ciclo completo de market making
        
        Args:
            current_price: Precio actual
            volatility: Volatilidad del mercado
            volume: Volumen de trading
            timestamp: Timestamp actual
        """
        # Calcular spread dinámico
        spread = self.calculate_dynamic_spread(current_price, volatility, volume)
        
        # Calcular cotizaciones
        buy_price, sell_price = self.calculate_optimal_quotes(current_price, spread)
        
        # Simular ejecución de órdenes (probabilidad basada en spread)
        execution_probability = max(0.1, min(0.9, 1 - (spread / self.max_spread)))
        
        # Ejecutar órdenes de compra
        if np.random.random() < execution_probability:
            buy_size = self.calculate_position_size(buy_price, 'buy')
            if buy_size > 50:  # Mínimo $50
                self.execute_buy_order(buy_price, buy_size, timestamp, spread)
        
        # Ejecutar órdenes de venta
        if np.random.random() < execution_probability:
            sell_size = self.calculate_position_size(sell_price, 'sell')
            if sell_size > 50:  # Mínimo $50
                self.execute_sell_order(sell_price, sell_size, timestamp, spread)

    def execute_buy_order(self, price, size, timestamp, spread):
        """Ejecuta una orden de compra"""
        quantity = size / price
        fee = size * self.fee_rate
        
        # Actualizar inventario
        self.inventory['base'] += quantity
        self.inventory['quote'] -= (size + fee)
        
        # Registrar operación
        operation = {
            'timestamp': timestamp,
            'type': 'BUY_MM',
            'price': price,
            'quantity': quantity,
            'size': size,
            'fee': fee,
            'spread': spread,
            'inventory_base': self.inventory['base'],
            'inventory_quote': self.inventory['quote']
        }
        
        self.operations.append(operation)
        self.total_fees += fee
        
        logging.info(f"📈 MM BUY: ${size:.2f} @ ${price:.2f} | Spread: {spread*100:.3f}%")

    def execute_sell_order(self, price, size, timestamp, spread):
        """Ejecuta una orden de venta"""
        quantity = size / price
        fee = size * self.fee_rate
        
        # Verificar si tenemos suficiente inventario base
        if self.inventory['base'] >= quantity:
            # Actualizar inventario
            self.inventory['base'] -= quantity
            self.inventory['quote'] += (size - fee)
            
            # Registrar operación
            operation = {
                'timestamp': timestamp,
                'type': 'SELL_MM',
                'price': price,
                'quantity': quantity,
                'size': size,
                'fee': fee,
                'spread': spread,
                'inventory_base': self.inventory['base'],
                'inventory_quote': self.inventory['quote']
            }
            
            self.operations.append(operation)
            self.total_fees += fee
            
            logging.info(f"📉 MM SELL: ${size:.2f} @ ${price:.2f} | Spread: {spread*100:.3f}%")

    def rebalance_inventory(self, current_price, timestamp):
        """
        Rebalancea el inventario cuando hay desequilibrio
        
        Args:
            current_price: Precio actual
            timestamp: Timestamp actual
        """
        total_value = self.inventory['quote'] + (self.inventory['base'] * current_price)
        target_base_value = total_value * self.inventory_target
        current_base_value = self.inventory['base'] * current_price
        
        imbalance = abs(current_base_value - target_base_value) / total_value
        
        if imbalance > self.rebalance_threshold:
            if current_base_value > target_base_value:
                # Vender exceso de base
                excess_quantity = (current_base_value - target_base_value) / current_price
                if excess_quantity > 0:
                    self.execute_rebalance_sell(current_price, excess_quantity, timestamp)
            else:
                # Comprar más base
                needed_value = target_base_value - current_base_value
                if needed_value > 0 and self.inventory['quote'] >= needed_value:
                    needed_quantity = needed_value / current_price
                    self.execute_rebalance_buy(current_price, needed_quantity, timestamp)

    def execute_rebalance_buy(self, price, quantity, timestamp):
        """Ejecuta compra de rebalanceo"""
        size = quantity * price
        fee = size * self.fee_rate
        
        self.inventory['base'] += quantity
        self.inventory['quote'] -= (size + fee)
        self.total_fees += fee
        
        operation = {
            'timestamp': timestamp,
            'type': 'REBALANCE_BUY',
            'price': price,
            'quantity': quantity,
            'size': size,
            'fee': fee,
            'spread': 0,
            'inventory_base': self.inventory['base'],
            'inventory_quote': self.inventory['quote']
        }
        
        self.operations.append(operation)
        logging.info(f"⚖️ REBALANCE BUY: {quantity:.6f} @ ${price:.2f}")

    def execute_rebalance_sell(self, price, quantity, timestamp):
        """Ejecuta venta de rebalanceo"""
        size = quantity * price
        fee = size * self.fee_rate
        
        self.inventory['base'] -= quantity
        self.inventory['quote'] += (size - fee)
        self.total_fees += fee
        
        operation = {
            'timestamp': timestamp,
            'type': 'REBALANCE_SELL',
            'price': price,
            'quantity': quantity,
            'size': size,
            'fee': fee,
            'spread': 0,
            'inventory_base': self.inventory['base'],
            'inventory_quote': self.inventory['quote']
        }
        
        self.operations.append(operation)
        logging.info(f"⚖️ REBALANCE SELL: {quantity:.6f} @ ${price:.2f}")

    def run_backtest(self, symbol='BTCUSDT', days=60):
        """
        Ejecuta backtest del sistema de market making
        
        Args:
            symbol: Par de trading
            days: Días de backtest
        """
        logging.info(f"🔄 Iniciando backtest de market making para {symbol}")
        
        # Obtener datos
        fetcher = RobustDataFetcher()
        data = fetcher.get_market_data(symbol, '15m', limit=days*24*4)  # 15 minutos para mayor frecuencia
        
        if data is None or data.empty:
            logging.error(f"❌ No se pudieron obtener datos para {symbol}")
            return
        
        # Normalizar datos
        data.columns = data.columns.str.lower()
        if data.index.name == 'timestamp' or 'timestamp' in str(data.index.name).lower():
            data.reset_index(inplace=True)
        
        # Inicializar inventario
        initial_base_value = self.initial_capital * self.inventory_target
        initial_quote_value = self.initial_capital * (1 - self.inventory_target)
        
        self.inventory['base'] = initial_base_value / data['close'].iloc[0]
        self.inventory['quote'] = initial_quote_value
        
        logging.info(f"📊 Datos obtenidos: {len(data)} velas de 15m")
        logging.info(f"💰 Inventario inicial: {self.inventory['base']:.6f} {symbol[:3]}, ${self.inventory['quote']:.2f}")
        
        # Procesar cada vela
        for idx, row in data.iterrows():
            if idx < 20:  # Período de calentamiento
                continue
                
            current_price = row['close']
            volume = row.get('volume', 1000000)
            timestamp = row.get('timestamp', idx)
            
            # Calcular volatilidad
            volatility = self.calculate_volatility(data.iloc[max(0, idx-20):idx+1])
            
            # Ejecutar ciclo de market making
            self.execute_market_making_cycle(current_price, volatility, volume, timestamp)
            
            # Rebalancear inventario cada 4 horas (16 velas de 15m)
            if idx % 16 == 0:
                self.rebalance_inventory(current_price, timestamp)
        
        # Liquidar inventario al final
        final_price = data['close'].iloc[-1]
        self.liquidate_inventory(final_price, data.index[-1])
        
        # Calcular métricas finales
        self.calculate_final_metrics(days)

    def liquidate_inventory(self, final_price, timestamp):
        """Liquida todo el inventario al final del backtest"""
        if self.inventory['base'] > 0:
            final_value = self.inventory['base'] * final_price
            fee = final_value * self.fee_rate
            
            self.inventory['quote'] += (final_value - fee)
            self.total_fees += fee
            
            operation = {
                'timestamp': timestamp,
                'type': 'LIQUIDATE',
                'price': final_price,
                'quantity': self.inventory['base'],
                'size': final_value,
                'fee': fee,
                'spread': 0,
                'inventory_base': 0,
                'inventory_quote': self.inventory['quote']
            }
            
            self.operations.append(operation)
            self.inventory['base'] = 0
            
            logging.info(f"🔚 LIQUIDACIÓN: ${final_value:.2f} @ ${final_price:.2f}")

    def calculate_final_metrics(self, days):
        """Calcula métricas finales del backtest"""
        if not self.operations:
            logging.warning("⚠️ No se generaron operaciones de market making")
            return
        
        # Capital final
        self.current_capital = self.inventory['quote']
        
        # Métricas básicas
        total_operations = len(self.operations)
        buy_ops = len([op for op in self.operations if 'BUY' in op['type']])
        sell_ops = len([op for op in self.operations if 'SELL' in op['type']])
        
        # Retornos
        net_pnl = self.current_capital - self.initial_capital
        net_return = (net_pnl / self.initial_capital) * 100
        
        # ROI mensual
        months = days / 30.44
        monthly_roi = (((self.current_capital / self.initial_capital) ** (1/months)) - 1) * 100
        
        # Gap al objetivo
        target_roi = 15.0
        roi_gap = target_roi - monthly_roi
        
        # Spreads promedio
        mm_ops = [op for op in self.operations if 'MM' in op['type']]
        avg_spread = np.mean([op['spread'] for op in mm_ops]) * 100 if mm_ops else 0
        
        # Logging de resultados
        logging.info("=" * 80)
        logging.info("RESULTADOS SISTEMA DE MARKET MAKING SICAR")
        logging.info("=" * 80)
        logging.info(f"💰 Capital inicial: ${self.initial_capital:.2f}")
        logging.info(f"💰 Capital final: ${self.current_capital:.2f}")
        logging.info(f"💸 Fees totales: ${self.total_fees:.2f}")
        logging.info(f"💵 PnL neto: ${net_pnl:.2f}")
        logging.info(f"📊 Retorno neto: {net_return:.2f}%")
        logging.info(f"🎯 ROI mensual: {monthly_roi:.2f}%")
        logging.info(f"🔄 Total operaciones: {total_operations}")
        logging.info(f"📈 Operaciones de compra: {buy_ops}")
        logging.info(f"📉 Operaciones de venta: {sell_ops}")
        logging.info(f"📊 Spread promedio: {avg_spread:.3f}%")
        logging.info(f"📅 Duración: {days} días ({months:.1f} meses)")
        logging.info(f"⚡ Apalancamiento: {self.leverage}x")
        logging.info(f"⚡ Gap al objetivo: {roi_gap:.2f}% (Objetivo: {target_roi}%)")
        logging.info("=" * 80)
        
        # Guardar resultados
        self.save_results()
        
        # Resumen final
        print(f"\n✅ Backtest de market making completado!")
        print(f"📊 ROI mensual: {monthly_roi:.2f}%")
        print(f"🎯 Objetivo: {target_roi}%")
        print(f"🔄 Total operaciones: {total_operations}")
        print(f"📊 Spread promedio: {avg_spread:.3f}%")
        print(f"⚡ Apalancamiento: {self.leverage}x")
        print(f"📁 Resultados guardados en: market_making_sicar_results.csv")

    def save_results(self):
        """Guarda los resultados en CSV"""
        if self.operations:
            df = pd.DataFrame(self.operations)
            df.to_csv('market_making_sicar_results.csv', index=False)
            logging.info("💾 Resultados guardados en market_making_sicar_results.csv")

def main():
    """Función principal"""
    try:
        # Crear y ejecutar sistema de market making
        system = MarketMakingSicarSystem(
            initial_capital=500,
            leverage=5.0  # Apalancamiento agresivo para market making
        )
        
        # Ejecutar backtest
        system.run_backtest(symbol='BTCUSDT', days=60)
        
    except Exception as e:
        logging.error(f"❌ Error en sistema de market making: {str(e)}")
        raise

if __name__ == "__main__":
    main()