#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DASHBOARD DE MONITOREO EN TIEMPO REAL
====================================
Dashboard web para monitorear el sistema de paper trading
de primera vela en tiempo real
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import time
from datetime import datetime, timedelta
import requests
import asyncio
import threading

# Configuración de la página
st.set_page_config(
    page_title="Sistema Primera Vela - Tiempo Real",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

class RealTimeDashboard:
    """Dashboard de monitoreo en tiempo real"""
    
    def __init__(self):
        self.config = self.load_config()
        self.session_data = self.load_session_data()
        
    def load_config(self):
        """Carga configuración del sistema"""
        try:
            with open('first_candle_strategy_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def load_session_data(self):
        """Carga datos de la sesión actual"""
        try:
            with open('real_time_session_data.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                'current_capital': 250.0,
                'positions': {},
                'trades_history': [],
                'session_trades_count': 0
            }
    
    def get_binance_price(self, symbol):
        """Obtiene precio actual de Binance"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url)
            data = response.json()
            return float(data['price'])
        except:
            return 0.0
    
    def get_market_data(self, symbol, interval='1h', limit=24):
        """Obtiene datos de mercado"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except:
            return pd.DataFrame()

def main():
    """Función principal del dashboard"""
    
    # Título principal
    st.title("🚀 Sistema Primera Vela - Monitoreo en Tiempo Real")
    st.markdown("---")
    
    # Crear instancia del dashboard
    dashboard = RealTimeDashboard()
    
    # Sidebar con controles
    st.sidebar.header("⚙️ Configuración")
    
    # Auto-refresh
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Botón de refresh manual
    if st.sidebar.button("🔄 Actualizar Datos"):
        st.rerun()
    
    # Información del sistema
    st.sidebar.markdown("### 📊 Estado del Sistema")
    
    # Cargar datos actuales
    session_data = dashboard.load_session_data()
    config = dashboard.config
    
    if config:
        initial_capital = config.get('capital_management', {}).get('initial_capital', 250)
        current_capital = session_data.get('current_capital', initial_capital)
        total_return = ((current_capital - initial_capital) / initial_capital) * 100
        
        st.sidebar.metric("Capital Inicial", f"${initial_capital:.2f}")
        st.sidebar.metric("Capital Actual", f"${current_capital:.2f}")
        st.sidebar.metric("Retorno Total", f"{total_return:.2f}%")
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Capital Actual",
            f"${session_data.get('current_capital', 250):.2f}",
            delta=f"{total_return:.2f}%" if config else None
        )
    
    with col2:
        positions_count = len([p for p in session_data.get('positions', {}).values() 
                              if p.get('status') == 'OPEN'])
        st.metric("📈 Posiciones Abiertas", positions_count)
    
    with col3:
        trades_count = len(session_data.get('trades_history', []))
        st.metric("🔄 Total Trades", trades_count)
    
    with col4:
        session_trades = session_data.get('session_trades_count', 0)
        max_daily = config.get('risk_management', {}).get('max_daily_trades', 8) if config else 8
        st.metric("📅 Trades Hoy", f"{session_trades}/{max_daily}")
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Mercado", "💼 Posiciones", "📈 Historial", "⚙️ Configuración"])
    
    with tab1:
        st.header("📊 Datos de Mercado en Tiempo Real")
        
        if config and 'symbols' in config:
            symbols = config['symbols']
            
            # Selector de símbolo
            selected_symbol = st.selectbox("Seleccionar Símbolo", symbols)
            
            # Obtener datos del símbolo seleccionado
            market_data = dashboard.get_market_data(selected_symbol)
            current_price = dashboard.get_binance_price(selected_symbol)
            
            if not market_data.empty:
                # Gráfico de precios
                fig = go.Figure()
                
                fig.add_trace(go.Candlestick(
                    x=market_data['timestamp'],
                    open=market_data['open'],
                    high=market_data['high'],
                    low=market_data['low'],
                    close=market_data['close'],
                    name=selected_symbol
                ))
                
                fig.update_layout(
                    title=f"{selected_symbol} - Precio Actual: ${current_price:.4f}",
                    xaxis_title="Tiempo",
                    yaxis_title="Precio (USDT)",
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Métricas del símbolo
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Precio Actual", f"${current_price:.4f}")
                
                with col2:
                    change_24h = ((current_price - market_data.iloc[0]['close']) / 
                                 market_data.iloc[0]['close']) * 100
                    st.metric("Cambio 24h", f"{change_24h:.2f}%")
                
                with col3:
                    volume_24h = market_data['volume'].sum()
                    st.metric("Volumen 24h", f"{volume_24h:,.0f}")
                
                with col4:
                    volatility = market_data['close'].pct_change().std() * 100
                    st.metric("Volatilidad", f"{volatility:.2f}%")
    
    with tab2:
        st.header("💼 Posiciones Actuales")
        
        positions = session_data.get('positions', {})
        open_positions = {k: v for k, v in positions.items() if v.get('status') == 'OPEN'}
        
        if open_positions:
            positions_df = pd.DataFrame(open_positions.values())
            
            # Calcular P&L no realizado
            for idx, row in positions_df.iterrows():
                current_price = dashboard.get_binance_price(row['symbol'])
                entry_price = row['entry_price']
                
                if row['type'] == 'BUY':
                    unrealized_pnl = (current_price - entry_price) / entry_price * row['position_size']
                else:
                    unrealized_pnl = (entry_price - current_price) / entry_price * row['position_size']
                
                positions_df.at[idx, 'current_price'] = current_price
                positions_df.at[idx, 'unrealized_pnl'] = unrealized_pnl
                positions_df.at[idx, 'unrealized_pnl_pct'] = (unrealized_pnl / row['position_size']) * 100
            
            # Mostrar tabla de posiciones
            st.dataframe(
                positions_df[['symbol', 'type', 'entry_price', 'current_price', 
                             'position_size', 'stop_loss', 'take_profit', 
                             'unrealized_pnl', 'unrealized_pnl_pct']],
                use_container_width=True
            )
            
            # Gráfico de P&L no realizado
            fig = px.bar(
                positions_df,
                x='symbol',
                y='unrealized_pnl',
                color='unrealized_pnl',
                title="P&L No Realizado por Posición",
                color_continuous_scale=['red', 'yellow', 'green']
            )
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No hay posiciones abiertas actualmente")
    
    with tab3:
        st.header("📈 Historial de Trades")
        
        trades_history = session_data.get('trades_history', [])
        
        if trades_history:
            trades_df = pd.DataFrame(trades_history)
            
            # Métricas de rendimiento
            col1, col2, col3, col4 = st.columns(4)
            
            winning_trades = len([t for t in trades_history if t['result'] == 'WIN'])
            total_trades = len(trades_history)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = sum([t['pnl'] for t in trades_history])
            avg_profit = sum([t['pnl'] for t in trades_history if t['result'] == 'WIN']) / winning_trades if winning_trades > 0 else 0
            avg_loss = abs(sum([t['pnl'] for t in trades_history if t['result'] == 'LOSS']) / (total_trades - winning_trades)) if (total_trades - winning_trades) > 0 else 0
            
            with col1:
                st.metric("Tasa de Aciertos", f"{win_rate:.1f}%")
            
            with col2:
                st.metric("P&L Total", f"${total_pnl:.2f}")
            
            with col3:
                st.metric("Ganancia Promedio", f"${avg_profit:.2f}")
            
            with col4:
                st.metric("Pérdida Promedio", f"${avg_loss:.2f}")
            
            # Gráfico de evolución del capital
            trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
            trades_df['capital_evolution'] = initial_capital + trades_df['cumulative_pnl']
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=range(len(trades_df)),
                y=trades_df['capital_evolution'],
                mode='lines+markers',
                name='Evolución del Capital',
                line=dict(color='blue', width=2)
            ))
            
            fig.update_layout(
                title="Evolución del Capital",
                xaxis_title="Número de Trade",
                yaxis_title="Capital (USDT)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla de trades
            st.subheader("Detalle de Trades")
            st.dataframe(
                trades_df[['symbol', 'type', 'entry_price', 'exit_price', 
                          'pnl', 'pnl_pct', 'result', 'exit_reason']],
                use_container_width=True
            )
            
        else:
            st.info("No hay historial de trades disponible")
    
    with tab4:
        st.header("⚙️ Configuración del Sistema")
        
        if config:
            # Mostrar configuración actual
            st.subheader("📋 Configuración Actual")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**💰 Gestión de Capital**")
                st.write(f"Capital inicial: ${config.get('capital_management', {}).get('initial_capital', 0):.2f}")
                st.write(f"Capital mínimo: ${config.get('capital_management', {}).get('min_capital', 0):.2f}")
                st.write(f"Capital máximo: ${config.get('capital_management', {}).get('max_capital', 0):.2f}")
                
                st.markdown("**⚠️ Gestión de Riesgo**")
                risk_mgmt = config.get('risk_management', {})
                st.write(f"Riesgo por trade: {risk_mgmt.get('max_risk_per_trade', 0)*100:.1f}%")
                st.write(f"Stop loss: {risk_mgmt.get('stop_loss_pct', 0)*100:.1f}%")
                st.write(f"Take profit: {risk_mgmt.get('take_profit_pct', 0)*100:.1f}%")
                st.write(f"Trades diarios máx: {risk_mgmt.get('max_daily_trades', 0)}")
            
            with col2:
                st.markdown("**🎯 Parámetros de Estrategia**")
                strategy = config.get('strategy_parameters', {})
                st.write(f"Hora de sesión: {strategy.get('session_start_hour', 0)}:00")
                st.write(f"Umbral breakout: {strategy.get('breakout_threshold', 0)*100:.1f}%")
                st.write(f"Multiplicador volumen: {strategy.get('volume_multiplier', 0):.1f}x")
                
                st.markdown("**📊 Símbolos Monitoreados**")
                symbols = config.get('symbols', [])
                for symbol in symbols:
                    current_price = dashboard.get_binance_price(symbol)
                    st.write(f"{symbol}: ${current_price:.4f}")
            
            # Rendimiento validado
            st.subheader("✅ Rendimiento Validado")
            performance = config.get('performance_validated', {})
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Retorno Mensual", f"{performance.get('monthly_return', 0):.2f}%")
                st.metric("Total Trades", performance.get('total_trades', 0))
            
            with col2:
                st.metric("Tasa de Aciertos", f"{performance.get('win_rate', 0):.1f}%")
                st.metric("Factor de Ganancia", f"{performance.get('profit_factor', 0):.2f}")
            
            with col3:
                st.metric("Máx Drawdown", f"{performance.get('max_drawdown', 0):.2f}%")
                st.metric("Ratio Sharpe", f"{performance.get('sharpe_ratio', 0):.2f}")
        
        else:
            st.warning("No se pudo cargar la configuración del sistema")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "🤖 **Sistema de Primera Vela** | "
        f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        "🔄 Auto-refresh cada 30 segundos"
    )

if __name__ == "__main__":
    main()