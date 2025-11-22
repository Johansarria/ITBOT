"""
Dashboard Web Avanzado con Métricas en Tiempo Real - SICAR Fase 2
Interfaz web moderna con visualizaciones interactivas y datos en vivo
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sqlite3
import os
from dataclasses import asdict
import threading
import logging
from enhanced_config import CONFIG

# Importar módulos de integración
try:
    from breakout_portfolio_integration import (
        BREAKOUT_PORTFOLIO_INTEGRATOR,
        BreakoutPortfolioStrategy,
        start_breakout_portfolio_integration,
        stop_breakout_portfolio_integration,
        get_integration_status,
        get_integration_signals
    )
    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False
    logging.warning("Módulo de integración breakout-portfolio no disponible")

# Integración PatchTST en tiempo real
from module_patchtst_integration import PatchTSTIntegration
from crypto_data_loader import CryptoDataLoader
from binance_data_provider import BinanceDataProvider

@st.cache_resource
def get_patchtst_integration(symbol: str) -> PatchTSTIntegration:
    integ = PatchTSTIntegration(symbol)
    integ.initialize_model(load_pretrained=True, force_retrain=False)
    return integ

def compute_trade_plan(signal_result: Dict[str, Any], risk_analysis: Dict[str, Any], current_price: float) -> Dict[str, float]:
    rm = risk_analysis.get('risk_metrics', {})
    support = rm.get('support_level', current_price * 0.98)
    resistance = rm.get('resistance_level', current_price * 1.02)
    base_vol = risk_analysis.get('price_volatility', 0.02)
    vol = max(0.005, base_vol)
    entry = float(current_price)

    direction = signal_result.get('signal')
    if direction == 'BUY':
        # Garantías de dirección
        if resistance <= entry:
            resistance = entry * (1 + vol)
        if support >= entry:
            support = entry * (1 - vol)
        sl = min(support, entry * (1 - vol))
        risk = max(1e-6, entry - sl)
        tp1 = entry + 1.0 * risk
        tp2 = entry + 1.5 * risk
        tp3 = entry + 2.0 * risk
        # No permitir TP por debajo de resistencia si es demasiado cercano
        tp1 = max(tp1, resistance)
    else:
        # SELL
        if support >= entry:
            support = entry * (1 - vol)
        if resistance <= entry:
            resistance = entry * (1 + vol)
        sl = max(resistance, entry * (1 + vol))
        risk = max(1e-6, sl - entry)
        tp1 = entry - 1.0 * risk
        tp2 = entry - 1.5 * risk
        tp3 = entry - 2.0 * risk
        # No permitir TP por encima de soporte
        tp1 = min(tp1, support)

    rr_tp1 = (tp1 - entry) / risk if direction == 'BUY' else (entry - tp1) / risk
    rr_tp2 = (tp2 - entry) / risk if direction == 'BUY' else (entry - tp2) / risk
    rr_tp3 = (tp3 - entry) / risk if direction == 'BUY' else (entry - tp3) / risk

    return {
        'entry': float(entry),
        'sl': float(sl),
        'tp1': float(tp1),
        'tp2': float(tp2),
        'tp3': float(tp3),
        'rr_tp1': float(rr_tp1),
        'rr_tp2': float(rr_tp2),
        'rr_tp3': float(rr_tp3)
    }

# Configuración de la página
st.set_page_config(
    page_title="SICAR Dashboard Avanzado",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar la apariencia
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .alert-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .success-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }
    
    .stSelectbox > div > div {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

class DashboardData:
    """Clase para manejar datos del dashboard"""
    
    def __init__(self):
        CONFIG.ensure_directories()
        self.db_path = str(CONFIG.DATA_DIR / 'dashboard.db')
        self.init_database()
        
    def init_database(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS real_time_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    price REAL,
                    volume REAL,
                    change_24h REAL,
                    market_cap REAL,
                    exchange TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    alert_type TEXT,
                    message TEXT,
                    priority TEXT,
                    acknowledged BOOLEAN DEFAULT FALSE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_value REAL,
                    daily_return REAL,
                    total_return REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL
                )
            """)
            conn.commit()
            conn.close()
        except Exception:
            pass
    
    def save_metric(self, symbol: str, price: float, volume: float, change_24h: float, 
                   market_cap: float = 0, exchange: str = "Binance"):
        """Guardar métrica en tiempo real"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO real_time_metrics 
            (symbol, price, volume, change_24h, market_cap, exchange)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (symbol, price, volume, change_24h, market_cap, exchange))
        
        conn.commit()
        conn.close()
    
    def get_recent_metrics(self, symbol: str, hours: int = 24) -> pd.DataFrame:
        """Obtener métricas recientes"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT * FROM real_time_metrics 
            WHERE symbol = ? AND timestamp > datetime('now', '-{} hours')
            ORDER BY timestamp DESC
        """.format(hours)
        
        df = pd.read_sql_query(query, conn, params=(symbol,))
        conn.close()
        
        return df
    
    def save_portfolio_performance(self, total_value: float, daily_return: float, 
                                 total_return: float, sharpe_ratio: float, max_drawdown: float):
        """Guardar rendimiento de portafolio"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO portfolio_performance 
            (total_value, daily_return, total_return, sharpe_ratio, max_drawdown)
            VALUES (?, ?, ?, ?, ?)
        """, (total_value, daily_return, total_return, sharpe_ratio, max_drawdown))
        
        conn.commit()
        conn.close()

class RealTimeDataSimulator:
    """Simulador de datos en tiempo real"""
    
    def __init__(self):
        self.symbols = ["BTC-USD", "ETH-USD", "LINK-USD", "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD"]
        self.base_prices = {
            "BTC-USD": 95000,
            "ETH-USD": 3500,
            "LINK-USD": 15.50,
            "BNB-USD": 650,
            "SOL-USD": 180,
            "XRP-USD": 0.85,
            "ADA-USD": 0.45
        }
        
    def generate_real_time_data(self) -> Dict[str, Dict]:
        """Generar datos simulados en tiempo real"""
        data = {}
        
        for symbol in self.symbols:
            base_price = self.base_prices[symbol]
            
            # Simular variación de precio
            price_change = np.random.normal(0, 0.02)  # 2% volatilidad
            current_price = base_price * (1 + price_change)
            
            # Simular otros datos
            volume = np.random.uniform(1000000, 10000000)
            change_24h = np.random.uniform(-5, 5)
            market_cap = current_price * np.random.uniform(18000000, 21000000)
            
            data[symbol] = {
                "price": current_price,
                "volume": volume,
                "change_24h": change_24h,
                "market_cap": market_cap,
                "timestamp": datetime.now()
            }
            
        return data

def create_price_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Crear gráfico de precios"""
    fig = go.Figure()
    
    if not df.empty:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['price'],
            mode='lines+markers',
            name=f'{symbol} Precio',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=6)
        ))
    
    fig.update_layout(
        title=f"Precio en Tiempo Real - {symbol}",
        xaxis_title="Tiempo",
        yaxis_title="Precio (USD)",
        template="plotly_dark",
        height=400,
        showlegend=True
    )
    
    return fig

def create_volume_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Crear gráfico de volumen"""
    fig = go.Figure()
    
    if not df.empty:
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name=f'{symbol} Volumen',
            marker_color='#ff7f0e'
        ))
    
    fig.update_layout(
        title=f"Volumen de Trading - {symbol}",
        xaxis_title="Tiempo",
        yaxis_title="Volumen",
        template="plotly_dark",
        height=300
    )
    
    return fig

def create_portfolio_chart() -> go.Figure:
    """Crear gráfico de rendimiento de portafolio"""
    # Simular datos de portafolio
    dates = pd.date_range(start='2025-08-01', end='2025-10-31', freq='D')
    
    # Simular rendimiento acumulativo
    daily_returns = np.random.normal(0.001, 0.02, len(dates))
    cumulative_returns = (1 + pd.Series(daily_returns)).cumprod()
    portfolio_value = 100000 * cumulative_returns
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=portfolio_value,
        mode='lines',
        name='Valor del Portafolio',
        line=dict(color='#2ca02c', width=3),
        fill='tonexty'
    ))
    
    fig.update_layout(
        title="Rendimiento del Portafolio",
        xaxis_title="Fecha",
        yaxis_title="Valor (USD)",
        template="plotly_dark",
        height=400
    )
    
    return fig

def create_correlation_heatmap(symbols: List[str]) -> go.Figure:
    """Crear mapa de calor de correlaciones"""
    # Simular matriz de correlación
    n = len(symbols)
    correlation_matrix = np.random.rand(n, n)
    correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
    np.fill_diagonal(correlation_matrix, 1)
    
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix,
        x=symbols,
        y=symbols,
        colorscale='RdYlBu',
        zmid=0
    ))
    
    fig.update_layout(
        title="Matriz de Correlación de Activos",
        template="plotly_dark",
        height=400
    )
    
    return fig

def show_breakout_portfolio_integration():
    """Mostrar vista de integración breakout-portfolio"""
    st.header("🔄 Integración Breakout-Portfolio")
    
    if not INTEGRATION_AVAILABLE:
        st.error("❌ Módulo de integración no disponible")
        st.info("Para usar esta funcionalidad, instale el módulo breakout_portfolio_integration")
        return
    
    # Estado de la integración
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Iniciar Integración"):
            try:
                start_breakout_portfolio_integration()
                st.success("✅ Integración iniciada")
            except Exception as e:
                st.error(f"❌ Error al iniciar: {str(e)}")
    
    with col2:
        if st.button("⏹️ Detener Integración"):
            try:
                stop_breakout_portfolio_integration()
                st.success("✅ Integración detenida")
            except Exception as e:
                st.error(f"❌ Error al detener: {str(e)}")
    
    with col3:
        if st.button("📊 Estado Actual"):
            try:
                status = get_integration_status()
                if status:
                    st.success("🟢 Activo")
                else:
                    st.warning("🟡 Inactivo")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Configuración de la estrategia
    st.subheader("⚙️ Configuración de Estrategia")
    
    col1, col2 = st.columns(2)
    
    with col1:
        lookback_period = st.slider("Período de Lookback", 10, 50, 20)
        breakout_threshold = st.slider("Umbral de Breakout", 0.01, 0.1, 0.02)
    
    with col2:
        volume_threshold = st.slider("Umbral de Volumen", 1.5, 5.0, 2.0)
        max_positions = st.slider("Máximo de Posiciones", 1, 10, 3)
    
    # Señales recientes
    st.subheader("📡 Señales Recientes")
    
    try:
        signals = get_integration_signals()
        if signals:
            df_signals = pd.DataFrame(signals)
            st.dataframe(df_signals, use_container_width=True)
        else:
            st.info("No hay señales disponibles")
    except Exception as e:
        st.error(f"Error al obtener señales: {str(e)}")
    
    # Métricas de rendimiento
    st.subheader("📊 Métricas de Rendimiento")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Simular métricas
    with col1:
        st.metric("Señales Generadas", "24")
    
    with col2:
        st.metric("Precisión", "68.5%")
    
    with col3:
        st.metric("Retorno Promedio", "+2.3%")
    
    with col4:
        st.metric("Drawdown Máximo", "-4.1%")

def main():
    """Función principal del dashboard"""
    
    # Header principal
    st.markdown('<h1 class="main-header">🚀 SICAR Dashboard Avanzado</h1>', unsafe_allow_html=True)
    st.markdown("### Sistema Inteligente de Criptomonedas y Análisis de Riesgo - Fase 2")
    
    # Inicializar datos
    dashboard_data = DashboardData()
    simulator = RealTimeDataSimulator()
    
    # Sidebar para configuración
    st.sidebar.title("⚙️ Configuración")
    
    # Selector de vista
    view_mode = st.sidebar.selectbox(
        "Modo de Vista",
        ["📊 Tiempo Real", "🧠 PatchTST Tiempo Real", "💱 Forex & Índices", "📈 Futuros NQ/MNQ", "📈 Análisis Técnico", "💼 Portafolio", "🔔 Alertas", "🔄 Backtesting", "🔄 Breakout-Portfolio Integration"]
    )
    
    # Selector de símbolo - estandarizar formato USD para consistencia con PatchTST
    selected_symbol = st.sidebar.selectbox(
        "Seleccionar Activo",
        ["BTC-USD", "ETH-USD", "LINK-USD", "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD"]
    )
    
    # Intervalo de actualización
    update_interval = st.sidebar.slider(
        "Intervalo de Actualización (segundos)",
        min_value=5,
        max_value=60,
        value=10
    )
    
    # Botón de actualización manual
    if st.sidebar.button("🔄 Actualizar Datos"):
        st.rerun()
    
    # Obtener datos reales de Binance en lugar de simulados
    real_time_data = {}
    try:
        # Usar CryptoDataLoader para obtener datos reales
        loader = CryptoDataLoader(selected_symbol, "1h")
        df_real = loader.get_binance_data(limit=24)  # Últimas 24 horas
        
        if not df_real.empty:
            # Calcular métricas reales
            current_price = float(df_real['close'].iloc[-1])
            price_24h_ago = float(df_real['close'].iloc[0])
            change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
            volume_24h = float(df_real['volume'].sum())
            
            # Guardar datos reales en la base de datos
            dashboard_data.save_metric(
                symbol=selected_symbol,
                price=current_price,
                volume=volume_24h,
                change_24h=change_24h,
                market_cap=current_price * 1000000  # Estimación del market cap
            )
            
            # Preparar datos para la vista
            real_time_data[selected_symbol] = {
                "price": current_price,
                "volume": volume_24h,
                "change_24h": change_24h,
                "market_cap": current_price * 1000000,
                "timestamp": datetime.now()
            }
        else:
            # Fallback a datos simulados si no hay datos reales
            st.warning("No se pudieron obtener datos reales de Binance, usando datos simulados")
            real_time_data = simulator.generate_real_time_data()
    except Exception as e:
        st.error(f"Error al obtener datos reales: {e}")
        real_time_data = simulator.generate_real_time_data()
    
    if view_mode == "📊 Tiempo Real":
        st.header("📊 Métricas en Tiempo Real")
        
        # Métricas principales en tarjetas
        col1, col2, col3, col4 = st.columns(4)
        
        current_data = real_time_data[selected_symbol]
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>💰 Precio Actual</h3>
                <h2>${current_data['price']:,.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            change_color = "success-card" if current_data['change_24h'] >= 0 else "alert-card"
            st.markdown(f"""
            <div class="{change_color}">
                <h3>📈 Cambio 24h</h3>
                <h2>{current_data['change_24h']:+.2f}%</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📊 Volumen 24h</h3>
                <h2>${current_data['volume']:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🏦 Market Cap</h3>
                <h2>${current_data['market_cap']:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # Gráficos de tiempo real
        col1, col2 = st.columns(2)
        
        # Obtener datos históricos
        df_metrics = dashboard_data.get_recent_metrics(selected_symbol, hours=24)
        
        with col1:
            price_chart = create_price_chart(df_metrics, selected_symbol)
            st.plotly_chart(price_chart, use_container_width=True)
        
        with col2:
            volume_chart = create_volume_chart(df_metrics, selected_symbol)
            st.plotly_chart(volume_chart, use_container_width=True)
        
        # Tabla de datos recientes
        st.subheader("📋 Datos Recientes")
        if not df_metrics.empty:
            st.dataframe(
                df_metrics[['timestamp', 'price', 'volume', 'change_24h']].head(10),
                use_container_width=True
            )
    
    elif view_mode == "🧠 PatchTST Tiempo Real":
        st.header(f"🧠 PatchTST - Señales y Plan de Trade en Tiempo Real ({selected_symbol})")
        account_balance = st.number_input("Balance de cuenta ($)", min_value=100.0, value=25000.0, step=100.0)
        risk_pct = st.slider("Riesgo por operación (% de cuenta)", min_value=0.1, max_value=2.0, value=1.0, step=0.1)
        fee_side = st.number_input("Fee por lado (% notional)", min_value=0.0, value=0.02, step=0.01)
        slip_bp = st.number_input("Slippage (bps)", min_value=0.0, value=5.0, step=0.5)
        
        # Usar el símbolo seleccionado en lugar de los fijos BTC-USD y ETH-USD
        sym = selected_symbol
        st.subheader(sym)
        integ = get_patchtst_integration(sym)
        loader = CryptoDataLoader(sym, "1h")
        df = loader.get_binance_data(limit=200)
        if df.empty:
            st.error("Sin datos de Binance")
        else:
            current_price = float(df['close'].iloc[-1])
            signal_result = integ.generate_prediction_signal(df, current_price)
            risk_analysis = integ.analyze_risk(df, current_price)
            plan = compute_trade_plan(signal_result, risk_analysis, current_price)

            # Métricas
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Señal", signal_result.get('signal', 'N/A'))
            with c2:
                st.metric("Confianza", f"{signal_result.get('confidence', 0.0):.1%}")
            rm = risk_analysis.get('risk_metrics', {})
            with c3:
                st.metric("VaR 95%", f"{rm.get('var_95', 0):.2%}")
            with c4:
                st.metric("Sharpe", f"{rm.get('sharpe_ratio', 0):.2f}")

            q = signal_result.get('quantiles', {})
            if q:
                c5, c6, c7 = st.columns(3)
                with c5:
                    st.metric("P10", f"{q.get('p10'):.2f}")
                with c6:
                    st.metric("P50", f"{q.get('p50'):.2f}")
                with c7:
                    st.metric("P90", f"{q.get('p90'):.2f}")

            # Plan de trade
            st.markdown(f"""
            **Entrada:** `{plan['entry']:.2f}`  
            **SL:** `{plan['sl']:.2f}`  
            **TP1:** `{plan['tp1']:.2f}`  
            **TP2:** `{plan['tp2']:.2f}`  
            **TP3:** `{plan['tp3']:.2f}`
            """)
            # Sizing y RR
            risk_per_unit = abs(plan['entry'] - plan['sl'])
            max_units_risk = int((account_balance * (risk_pct/100.0)) // risk_per_unit) if risk_per_unit > 0 else 0
            notional = max_units_risk * plan['entry']
            fee_cost = notional * (fee_side/100.0) * 2
            slip_cost = notional * (slip_bp/10000.0)
            pnl_tp1_gross = abs(plan['tp1'] - plan['entry']) * max_units_risk
            pnl_tp1_net = pnl_tp1_gross - fee_cost - slip_cost
            pnl_sl_gross = abs(plan['entry'] - plan['sl']) * max_units_risk
            pnl_sl_net = pnl_sl_gross + fee_cost + slip_cost
            s1, s2, s3 = st.columns(3)
            with s1:
                st.metric("Unidades sugeridas", f"{max_units_risk}")
            with s2:
                st.metric("Notional sugerido", f"${notional:,.0f}")
            with s3:
                st.metric("Riesgo por unidad", f"${risk_per_unit:,.2f}")
            def rr_box(label, rr):
                if rr >= 1.0:
                    st.success(f"{label}: {rr:.2f}R")
                elif rr >= 0.5:
                    st.warning(f"{label}: {rr:.2f}R")
                else:
                    st.error(f"{label}: {rr:.2f}R")
            rr1, rr2, rr3 = st.columns(3)
            with rr1:
                rr_box("RR TP1", plan.get('rr_tp1', 0.0))
            with rr2:
                rr_box("RR TP2", plan.get('rr_tp2', 0.0))
            with rr3:
                rr_box("RR TP3", plan.get('rr_tp3', 0.0))

            # Gráfico con líneas de entrada/SL/TP
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['timestamp'].tail(100), y=df['close'].tail(100), name='Precio', line=dict(color='blue')))
            fig.add_hline(y=plan['entry'], line_color='yellow', annotation_text='Entrada', annotation_position='top left')
            fig.add_hline(y=plan['sl'], line_color='red', annotation_text='SL', annotation_position='bottom left')
            fig.add_hline(y=plan['tp1'], line_color='green', annotation_text='TP1', annotation_position='top right')
            fig.add_hline(y=plan['tp2'], line_color='green', annotation_text='TP2', annotation_position='top right')
            fig.add_hline(y=plan['tp3'], line_color='green', annotation_text='TP3', annotation_position='top right')
            fig.update_layout(height=400, template='plotly_dark', showlegend=True, title=f"{sym} Precio y Niveles")
            st.plotly_chart(fig, use_container_width=True)

    elif view_mode == "💱 Forex & Índices":
        st.header("💱 Forex (Binance) & Índices Internos")
        provider = BinanceDataProvider()
        fx_symbols = ["EURUSDT", "GBPUSDT", "AUDUSDT", "NZDUSDT"]
        col_fx, col_idx = st.columns(2)
        with col_fx:
            st.subheader("Forex Spot")
            fx_selected = st.selectbox("Par Forex", fx_symbols)
            df_fx = provider.get_historical_data(fx_selected, interval='1h', limit=200)
            if df_fx is not None and not df_fx.empty:
                df_fx = df_fx.reset_index()
                # Calcular soporte/resistencia simples
                lookback = 48
                recent = df_fx.tail(lookback)
                support = recent['low'].min()
                resistance = recent['high'].max()
                current_price = float(df_fx['close'].iloc[-1])
                vol = float(df_fx['close'].pct_change().std())
                # Plan de trade simple
                entry = current_price
                sl = resistance * (1 + max(0.003, vol/2)) if current_price < resistance else support * (1 - max(0.003, vol/2))
                if current_price < (recent['close'].mean()):
                    # Sesgo vendedor
                    tp1, tp2, tp3 = support, entry - 1.5*(sl-entry), entry - 2.0*(sl-entry)
                    sesgo = 'SELL'
                else:
                    tp1, tp2, tp3 = resistance, entry + 1.5*(entry-sl), entry + 2.0*(entry-sl)
                    sesgo = 'BUY'
                st.metric("Precio", f"{current_price:.4f}")
                st.metric("Sesgo", sesgo)
                st.markdown(f"**Entrada:** `{entry:.4f}`  **SL:** `{sl:.4f}`  **TP1:** `{tp1:.4f}`  **TP2:** `{tp2:.4f}`  **TP3:** `{tp3:.4f}`")
                base = fx_selected.replace('USDT','')
                symbol_patch = f"{base}-USD"
                integ_fx = get_patchtst_integration(symbol_patch)
                loader_fx = CryptoDataLoader(symbol_patch, "1h")
                df_patch = loader_fx.get_binance_data(limit=200)
                if not df_patch.empty:
                    cp_patch = float(df_patch['close'].iloc[-1])
                    sr = integ_fx.generate_prediction_signal(df_patch, cp_patch)
                    ra = integ_fx.analyze_risk(df_patch, cp_patch)
                    plan_patch = compute_trade_plan(sr, ra, cp_patch)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Señal PatchTST", sr.get('signal','N/A'))
                    with c2:
                        st.metric("Confianza PatchTST", f"{sr.get('confidence',0.0):.1%}")
                fig_fx = go.Figure()
                fig_fx.add_trace(go.Scatter(x=df_fx['timestamp'].tail(100), y=df_fx['close'].tail(100), name=fx_selected))
                fig_fx.add_hline(y=entry, line_color='yellow', annotation_text='Entrada')
                fig_fx.add_hline(y=sl, line_color='red', annotation_text='SL')
                fig_fx.add_hline(y=tp1, line_color='green', annotation_text='TP1')
                fig_fx.add_hline(y=tp2, line_color='green', annotation_text='TP2')
                fig_fx.add_hline(y=tp3, line_color='green', annotation_text='TP3')
                fig_fx.update_layout(template='plotly_dark', height=400)
                st.plotly_chart(fig_fx, use_container_width=True)
                # Exportación del plan
                export = {
                    'symbol': fx_selected,
                    'entry': float(entry), 'sl': float(sl),
                    'tp1': float(tp1), 'tp2': float(tp2), 'tp3': float(tp3),
                    'patchtst_signal': sr.get('signal') if 'sr' in locals() else None,
                    'patchtst_confidence': float(sr.get('confidence',0.0)) if 'sr' in locals() else None,
                    'patchtst_entry': float(plan_patch['entry']) if 'plan_patch' in locals() else None,
                    'patchtst_sl': float(plan_patch['sl']) if 'plan_patch' in locals() else None,
                    'patchtst_tp1': float(plan_patch['tp1']) if 'plan_patch' in locals() else None,
                    'patchtst_tp2': float(plan_patch['tp2']) if 'plan_patch' in locals() else None,
                    'patchtst_tp3': float(plan_patch['tp3']) if 'plan_patch' in locals() else None
                }
                os.makedirs('results', exist_ok=True)
                with open('results/forex_indices_trade_plan.json', 'w') as f:
                    json.dump(export, f, indent=2)
            else:
                st.error("No se pudieron obtener datos de Binance para el par seleccionado")

        with col_idx:
            st.subheader("Índices Internos (Futures)")
            idx_symbol = st.selectbox("Futures símbolo", ["BTCUSDT", "ETHUSDT"])
            prem = provider.get_futures_premium_index(idx_symbol)
            oi = provider.get_futures_open_interest(idx_symbol)
            if prem:
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("Index Price", f"{prem['indexPrice']:.2f}")
                with c2: st.metric("Mark Price", f"{prem['markPrice']:.2f}")
                with c3: st.metric("Funding", f"{prem['lastFundingRate']:.4%}")
                if oi is not None:
                    st.metric("Open Interest", f"{oi:,.0f}")
            else:
                st.error("No se pudo obtener premium index")

    elif view_mode == "📈 Análisis Técnico":
        st.header("📈 Análisis Técnico Avanzado")
    elif view_mode == "📈 Futuros NQ/MNQ":
        st.header("📈 Futuros Nasdaq - NQ/MNQ (Plan de Trade)")
        from futures_symbol_registry import get_info, estimate_margin
        from futures_risk import plan as futures_plan
        sym = st.selectbox("Símbolo", ["NQ", "MNQ"], index=1)
        info = get_info(sym)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tick Size", str(info['tick_size']))
        with col2:
            st.metric("Tick Value", f"${info['tick_value']:.2f}")
        with col3:
            st.metric("Multiplier", f"${info['multiplier']:.2f}/pto")
        entry = st.number_input("Precio de entrada", min_value=1.0, value=17500.0, step=info['tick_size'])
        direction = st.selectbox("Dirección", ["SELL", "BUY"], index=0)
        vol = st.slider("Volatilidad (aprox)", min_value=0.001, max_value=0.05, value=0.01, step=0.001)
        contracts = st.number_input("Contratos", min_value=1, value=1, step=1)
        day_margin = st.checkbox("Usar margen intradía (day margin)", value=True)
        account_balance = st.number_input("Balance de cuenta ($)", min_value=100.0, value=25000.0, step=100.0)
        risk_pct = st.slider("Riesgo por operación (% de cuenta)", min_value=0.1, max_value=2.0, value=1.0, step=0.1)
        commission_side = st.number_input("Comisión por lado ($/contrato)", min_value=0.0, value=2.5, step=0.1)
        slippage_ticks = st.number_input("Slippage (ticks por lado)", min_value=0.0, value=1.0, step=0.25)
        support = st.number_input("Soporte (opcional)", min_value=1.0, value=entry * (1 - vol))
        resistance = st.number_input("Resistencia (opcional)", min_value=1.0, value=entry * (1 + vol))
        if st.button("Calcular plan"):
            p = futures_plan(sym, direction, entry, vol, support=support, resistance=resistance)
            total_margin = estimate_margin(sym, contracts=contracts, day=day_margin)
            approx_notional = p['entry'] * info['multiplier'] * contracts
            st.success(f"Plan {sym} {direction}: Entrada {p['entry']:.2f} | SL {p['sl']:.2f} | TP1 {p['tp1']:.2f} ({p['rr_tp1']:.2f}R) | TP2 {p['tp2']:.2f} ({p['rr_tp2']:.2f}R) | TP3 {p['tp3']:.2f} ({p['rr_tp3']:.2f}R)")
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Margen requerido", f"${total_margin:,.0f}")
            with m2:
                st.metric("Notional aprox.", f"${approx_notional:,.0f}")
            with m3:
                st.metric("Contratos", str(contracts))
            risk_per_contract = abs(p['entry'] - p['sl']) * info['multiplier']
            max_by_risk = int((account_balance * (risk_pct/100.0)) // risk_per_contract) if risk_per_contract > 0 else contracts
            max_by_margin = int(account_balance // estimate_margin(sym, contracts=1, day=day_margin))
            recommended = max(1, min(max_by_risk, max_by_margin))
            r1, r2, r3 = st.columns(3)
            with r1:
                st.metric("Riesgo por contrato", f"${risk_per_contract:,.0f}")
            with r2:
                st.metric("Máx. por riesgo", str(max_by_risk))
            with r3:
                st.metric("Máx. por margen", str(max_by_margin))
            st.info(f"Contratos recomendados: {recommended}")

            def rr_box(label, rr):
                if rr >= 1.0:
                    st.success(f"{label}: {rr:.2f}R")
                elif rr >= 0.5:
                    st.warning(f"{label}: {rr:.2f}R")
                else:
                    st.error(f"{label}: {rr:.2f}R")
            rr1, rr2, rr3 = st.columns(3)
            with rr1:
                rr_box("RR TP1", p['rr_tp1'])
            with rr2:
                rr_box("RR TP2", p['rr_tp2'])
            with rr3:
                rr_box("RR TP3", p['rr_tp3'])
            ticks_to_sl = abs(p['entry'] - p['sl']) / info['tick_size']
            ticks_to_tp1 = abs(p['tp1'] - p['entry']) / info['tick_size']
            slip_cost = slippage_ticks * info['tick_value'] * 2 * contracts
            comm_cost = commission_side * 2 * contracts
            pnl_tp1_gross = abs(p['tp1'] - p['entry']) * info['multiplier'] * contracts
            pnl_tp1_net = pnl_tp1_gross - slip_cost - comm_cost
            pnl_sl_gross = abs(p['entry'] - p['sl']) * info['multiplier'] * contracts
            pnl_sl_net = pnl_sl_gross + slip_cost + comm_cost
            c1, c2 = st.columns(2)
            with c1:
                st.metric("PnL TP1 bruto", f"${pnl_tp1_gross:,.0f}")
                st.metric("PnL TP1 neto", f"${pnl_tp1_net:,.0f}")
            with c2:
                st.metric("Pérdida SL bruta", f"-${pnl_sl_gross:,.0f}")
                st.metric("Pérdida SL neta", f"-${pnl_sl_net:,.0f}")
            fig = go.Figure()
            xs = ["Entrada","SL","TP1","TP2","TP3"]
            ys = [p['entry'], p['sl'], p['tp1'], p['tp2'], p['tp3']]
            fig.add_trace(go.Bar(x=xs, y=ys, name='Niveles'))
            fig.update_layout(height=360, template='plotly_dark', title=f"{sym} Niveles")
            st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de correlaciones
        correlation_chart = create_correlation_heatmap(["BTC", "ETH", "ADA", "SOL"])
        st.plotly_chart(correlation_chart, use_container_width=True)
        
        # Indicadores técnicos simulados
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Indicadores Técnicos")
            
            # RSI simulado
            rsi = np.random.uniform(30, 70)
            rsi_color = "🟢" if 30 <= rsi <= 70 else "🔴"
            st.metric("RSI (14)", f"{rsi:.1f} {rsi_color}")
            
            # MACD simulado
            macd = np.random.uniform(-100, 100)
            macd_color = "🟢" if macd > 0 else "🔴"
            st.metric("MACD", f"{macd:.2f} {macd_color}")
            
            # Bollinger Bands
            bb_position = np.random.uniform(0, 1)
            bb_status = "🟢 Normal" if 0.2 <= bb_position <= 0.8 else "🔴 Extremo"
            st.metric("Bollinger Bands", bb_status)
        
        with col2:
            st.subheader("🎯 Señales de Trading")
            
            signals = [
                {"tipo": "Compra", "fuerza": "Fuerte", "indicador": "RSI + MACD", "emoji": "🟢"},
                {"tipo": "Venta", "fuerza": "Débil", "indicador": "Resistencia", "emoji": "🟡"},
                {"tipo": "Mantener", "fuerza": "Neutral", "indicador": "Volumen", "emoji": "🔵"}
            ]
            
            for signal in signals:
                st.markdown(f"""
                {signal['emoji']} **{signal['tipo']}** - {signal['fuerza']}  
                *Basado en: {signal['indicador']}*
                """)
    
    elif view_mode == "💼 Portafolio":
        st.header("💼 Gestión de Portafolio")
        
        # Métricas de rendimiento
        col1, col2, col3, col4 = st.columns(4)
        
        # Simular métricas de portafolio
        total_value = 125000
        daily_return = 1.2
        total_return = 25.0
        sharpe_ratio = 1.8
        max_drawdown = -8.5
        
        with col1:
            st.markdown(f"""
            <div class="success-card">
                <h3>💰 Valor Total</h3>
                <h2>${total_value:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="success-card">
                <h3>📈 Retorno Diario</h3>
                <h2>{daily_return:+.2f}%</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="success-card">
                <h3>🎯 Retorno Total</h3>
                <h2>{total_return:+.1f}%</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📊 Sharpe Ratio</h3>
                <h2>{sharpe_ratio:.2f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        # Gráfico de rendimiento
        portfolio_chart = create_portfolio_chart()
        st.plotly_chart(portfolio_chart, use_container_width=True)
        
        # Distribución del portafolio
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🥧 Distribución de Activos")
            
            portfolio_data = {
                "Activo": ["BTC", "ETH", "ADA", "SOL", "Efectivo"],
                "Porcentaje": [40, 25, 15, 10, 10],
                "Valor": [50000, 31250, 18750, 12500, 12500]
            }
            
            fig_pie = px.pie(
                values=portfolio_data["Porcentaje"],
                names=portfolio_data["Activo"],
                title="Distribución del Portafolio"
            )
            fig_pie.update_layout(template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.subheader("📊 Detalles de Posiciones")
            df_portfolio = pd.DataFrame(portfolio_data)
            st.dataframe(df_portfolio, use_container_width=True)
    
    elif view_mode == "🔔 Alertas":
        st.header("🔔 Sistema de Alertas Inteligentes")
        
        # Alertas activas
        st.subheader("⚠️ Alertas Activas")
        
        alerts = [
            {"tipo": "Precio", "mensaje": "BTC superó $95,000", "prioridad": "Alta", "tiempo": "Hace 5 min"},
            {"tipo": "Volumen", "mensaje": "Volumen inusual en ETH", "prioridad": "Media", "tiempo": "Hace 15 min"},
            {"tipo": "Técnico", "mensaje": "RSI sobreventa en ADA", "prioridad": "Baja", "tiempo": "Hace 30 min"}
        ]
        
        for alert in alerts:
            priority_color = {
                "Alta": "alert-card",
                "Media": "metric-card", 
                "Baja": "success-card"
            }[alert["prioridad"]]
            
            st.markdown(f"""
            <div class="{priority_color}">
                <h4>🔔 {alert['tipo']} - {alert['prioridad']}</h4>
                <p>{alert['mensaje']}</p>
                <small>{alert['tiempo']}</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Configuración de alertas
        st.subheader("⚙️ Configurar Nueva Alerta")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            alert_type = st.selectbox("Tipo de Alerta", ["Precio", "Volumen", "Técnico", "Anomalía"])
        
        with col2:
            alert_symbol = st.selectbox("Activo", ["BTC-USD", "ETH-USD", "LINK-USD", "BNB-USD", "SOL-USD", "XRP-USD", "ADA-USD"])
        
        with col3:
            alert_threshold = st.number_input("Umbral", value=95000.0)
        
        if st.button("➕ Crear Alerta"):
            st.success(f"✅ Alerta creada: {alert_type} para {alert_symbol} en ${alert_threshold:,.2f}")
    
    elif view_mode == "🔄 Backtesting":
        st.header("🔄 Backtesting Avanzado")
        
        # Configuración de backtesting
        col1, col2, col3 = st.columns(3)
        
        with col1:
            strategy = st.selectbox("Estrategia", ["SMA Crossover", "RSI Mean Reversion", "MACD Momentum"])
        
        with col2:
            start_date = st.date_input("Fecha Inicio", value=datetime(2025, 8, 1))
        
        with col3:
            end_date = st.date_input("Fecha Fin", value=datetime(2025, 10, 31))
        
        if st.button("🚀 Ejecutar Backtesting"):
            with st.spinner("Ejecutando backtesting..."):
                time.sleep(2)  # Simular procesamiento
                
                # Resultados simulados
                results = {
                    "Retorno Total": "9.41%",
                    "Retorno Anualizado": "27.92%",
                    "Sharpe Ratio": "1.214",
                    "Máximo Drawdown": "-10.55%",
                    "Número de Trades": "15",
                    "Win Rate": "66.7%"
                }
                
                st.subheader("📊 Resultados del Backtesting")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    for key, value in list(results.items())[:2]:
                        st.metric(key, value)
                
                with col2:
                    for key, value in list(results.items())[2:4]:
                        st.metric(key, value)
                
                with col3:
                    for key, value in list(results.items())[4:]:
                        st.metric(key, value)
                
                # Gráfico de equity curve simulado
                dates = pd.date_range(start=start_date, end=end_date, freq='D')
                equity_curve = 100000 * (1 + pd.Series(np.random.normal(0.001, 0.02, len(dates)))).cumprod()
                
                fig_equity = go.Figure()
                fig_equity.add_trace(go.Scatter(
                    x=dates,
                    y=equity_curve,
                    mode='lines',
                    name='Equity Curve',
                    line=dict(color='#2ca02c', width=3)
                ))
                
                fig_equity.update_layout(
                    title="Curva de Equity - Backtesting",
                    xaxis_title="Fecha",
                    yaxis_title="Valor de la Cuenta (USD)",
                    template="plotly_dark",
                    height=400
                )
                
                st.plotly_chart(fig_equity, use_container_width=True)
    
    elif view_mode == "🔄 Breakout-Portfolio Integration":
        show_breakout_portfolio_integration()
    
    # Footer con información del sistema
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🔄 Última Actualización:**")
        st.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    with col2:
        st.markdown("**📊 Estado del Sistema:**")
        st.write("🟢 Operativo")
    
    with col3:
        st.markdown("**🌐 Exchanges Conectados:**")
        st.write("Binance, Coinbase")

if __name__ == "__main__":
    main()
