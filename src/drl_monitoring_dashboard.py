#!/usr/bin/env python3
"""
SICAR - Dashboard de Monitoreo DRL en Tiempo Real
FASE 2: Dashboard interactivo para monitoreo de agentes DRL

Este módulo implementa un dashboard completo para monitorear agentes DRL que incluye:
- Métricas de rendimiento en tiempo real
- Visualización de curvas de aprendizaje
- Monitoreo de regímenes de mercado
- Análisis de estabilidad y robustez
- Alertas y notificaciones
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import threading
import queue
import warnings
warnings.filterwarnings('ignore')

# Configurar página
st.set_page_config(
    page_title="SICAR - DRL Monitoring Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importar módulos SICAR
try:
    from advanced_drl_system import AdvancedDRLAgent
    from drl_validation_system import DRLValidator, DRLValidationResult
    from module_2_regime import ExtremeNonStationarityDetector
except ImportError as e:
    st.error(f"Error importando módulos SICAR: {e}")

logger = logging.getLogger(__name__)

@dataclass
class DRLMetrics:
    """Métricas DRL para monitoreo"""
    timestamp: datetime
    episode: int
    total_reward: float
    avg_reward: float
    loss: float
    epsilon: float
    learning_rate: float
    portfolio_value: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    market_regime: str
    volatility: float
    
class DRLMonitor:
    """Monitor de agentes DRL en tiempo real"""
    
    def __init__(self):
        self.metrics_history = []
        self.alerts = []
        self.is_monitoring = False
        self.agent = None
        
        # Configuración de alertas
        self.alert_thresholds = {
            'max_drawdown': 0.15,
            'min_sharpe': 0.5,
            'max_loss': 1.0,
            'min_win_rate': 0.4
        }
    
    def start_monitoring(self, agent: AdvancedDRLAgent):
        """Iniciar monitoreo del agente"""
        self.agent = agent
        self.is_monitoring = True
        logger.info("Monitoreo DRL iniciado")
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.is_monitoring = False
        logger.info("Monitoreo DRL detenido")
    
    def add_metrics(self, metrics: DRLMetrics):
        """Agregar nuevas métricas"""
        self.metrics_history.append(metrics)
        
        # Mantener solo las últimas 1000 métricas
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        # Verificar alertas
        self._check_alerts(metrics)
    
    def _check_alerts(self, metrics: DRLMetrics):
        """Verificar condiciones de alerta"""
        alerts = []
        
        if metrics.max_drawdown > self.alert_thresholds['max_drawdown']:
            alerts.append({
                'type': 'warning',
                'message': f"Drawdown alto: {metrics.max_drawdown:.2%}",
                'timestamp': metrics.timestamp
            })
        
        if metrics.sharpe_ratio < self.alert_thresholds['min_sharpe']:
            alerts.append({
                'type': 'warning',
                'message': f"Sharpe ratio bajo: {metrics.sharpe_ratio:.3f}",
                'timestamp': metrics.timestamp
            })
        
        if metrics.loss > self.alert_thresholds['max_loss']:
            alerts.append({
                'type': 'error',
                'message': f"Loss alto: {metrics.loss:.4f}",
                'timestamp': metrics.timestamp
            })
        
        if metrics.win_rate < self.alert_thresholds['min_win_rate']:
            alerts.append({
                'type': 'warning',
                'message': f"Win rate bajo: {metrics.win_rate:.2%}",
                'timestamp': metrics.timestamp
            })
        
        self.alerts.extend(alerts)
        
        # Mantener solo las últimas 50 alertas
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
    
    def get_latest_metrics(self) -> Optional[DRLMetrics]:
        """Obtener las métricas más recientes"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_df(self) -> pd.DataFrame:
        """Obtener métricas como DataFrame"""
        if not self.metrics_history:
            return pd.DataFrame()
        
        return pd.DataFrame([asdict(m) for m in self.metrics_history])

# Inicializar monitor global
if 'drl_monitor' not in st.session_state:
    st.session_state.drl_monitor = DRLMonitor()

def generate_sample_metrics() -> DRLMetrics:
    """Generar métricas de ejemplo para demostración"""
    now = datetime.now()
    episode = len(st.session_state.drl_monitor.metrics_history) + 1
    
    # Simular métricas realistas
    base_reward = 0.02 + np.random.normal(0, 0.01)
    total_reward = base_reward * episode + np.random.normal(0, 0.1)
    
    return DRLMetrics(
        timestamp=now,
        episode=episode,
        total_reward=total_reward,
        avg_reward=total_reward / episode if episode > 0 else 0,
        loss=max(0.001, 0.1 * np.exp(-episode/100) + np.random.normal(0, 0.01)),
        epsilon=max(0.01, 0.9 * np.exp(-episode/50)),
        learning_rate=0.001,
        portfolio_value=10000 * (1 + total_reward),
        sharpe_ratio=max(0, 1.5 + np.random.normal(0, 0.3)),
        max_drawdown=min(0.3, max(0, 0.05 + abs(np.random.normal(0, 0.02)))),
        win_rate=max(0.3, min(0.8, 0.6 + np.random.normal(0, 0.1))),
        num_trades=episode * 2 + np.random.randint(-5, 5),
        market_regime=np.random.choice(['low_vol', 'normal', 'high_vol', 'extreme']),
        volatility=max(0.01, 0.02 + abs(np.random.normal(0, 0.005)))
    )

def render_header():
    """Renderizar header del dashboard"""
    st.title("🤖 SICAR - Dashboard de Monitoreo DRL")
    st.markdown("**Sistema Inteligente de Clasificación y Análisis de Riesgo - Fase 2**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("▶️ Iniciar Monitoreo", type="primary"):
            st.session_state.drl_monitor.is_monitoring = True
            st.success("Monitoreo iniciado")
    
    with col2:
        if st.button("⏹️ Detener Monitoreo"):
            st.session_state.drl_monitor.is_monitoring = False
            st.info("Monitoreo detenido")
    
    with col3:
        if st.button("📊 Generar Métricas"):
            metrics = generate_sample_metrics()
            st.session_state.drl_monitor.add_metrics(metrics)
            st.success("Métricas agregadas")
    
    with col4:
        if st.button("🗑️ Limpiar Datos"):
            st.session_state.drl_monitor.metrics_history = []
            st.session_state.drl_monitor.alerts = []
            st.success("Datos limpiados")

def render_status_cards():
    """Renderizar tarjetas de estado"""
    latest = st.session_state.drl_monitor.get_latest_metrics()
    
    if not latest:
        st.info("No hay métricas disponibles. Genere algunas métricas para comenzar.")
        return
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Valor del Portfolio",
            f"${latest.portfolio_value:,.2f}",
            f"{((latest.portfolio_value - 10000) / 10000) * 100:+.2f}%"
        )
    
    with col2:
        st.metric(
            "Sharpe Ratio",
            f"{latest.sharpe_ratio:.3f}",
            f"{latest.sharpe_ratio - 1.0:+.3f}"
        )
    
    with col3:
        color = "normal" if latest.max_drawdown < 0.1 else "inverse"
        st.metric(
            "Max Drawdown",
            f"{latest.max_drawdown:.2%}",
            delta_color=color
        )
    
    with col4:
        st.metric(
            "Win Rate",
            f"{latest.win_rate:.1%}",
            f"{(latest.win_rate - 0.5) * 100:+.1f}%"
        )
    
    with col5:
        st.metric(
            "Episodio Actual",
            f"{latest.episode:,}",
            f"+{1 if len(st.session_state.drl_monitor.metrics_history) > 1 else 0}"
        )

def render_performance_charts():
    """Renderizar gráficos de rendimiento"""
    df = st.session_state.drl_monitor.get_metrics_df()
    
    if df.empty:
        st.info("No hay datos para mostrar gráficos.")
        return
    
    # Gráfico de recompensas y pérdidas
    fig_rewards = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Recompensa Total', 'Pérdida de Entrenamiento', 
                       'Valor del Portfolio', 'Sharpe Ratio'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Recompensa total
    fig_rewards.add_trace(
        go.Scatter(x=df['episode'], y=df['total_reward'], 
                  name='Recompensa Total', line=dict(color='green')),
        row=1, col=1
    )
    
    # Pérdida
    fig_rewards.add_trace(
        go.Scatter(x=df['episode'], y=df['loss'], 
                  name='Loss', line=dict(color='red')),
        row=1, col=2
    )
    
    # Valor del portfolio
    fig_rewards.add_trace(
        go.Scatter(x=df['episode'], y=df['portfolio_value'], 
                  name='Portfolio Value', line=dict(color='blue')),
        row=2, col=1
    )
    
    # Sharpe ratio
    fig_rewards.add_trace(
        go.Scatter(x=df['episode'], y=df['sharpe_ratio'], 
                  name='Sharpe Ratio', line=dict(color='purple')),
        row=2, col=2
    )
    
    fig_rewards.update_layout(
        height=600,
        title_text="Métricas de Rendimiento DRL",
        showlegend=False
    )
    
    st.plotly_chart(fig_rewards, use_container_width=True)

def render_learning_progress():
    """Renderizar progreso de aprendizaje"""
    df = st.session_state.drl_monitor.get_metrics_df()
    
    if df.empty:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Epsilon decay
        fig_epsilon = go.Figure()
        fig_epsilon.add_trace(
            go.Scatter(x=df['episode'], y=df['epsilon'], 
                      name='Epsilon', line=dict(color='orange'))
        )
        fig_epsilon.update_layout(
            title="Decaimiento de Epsilon (Exploración)",
            xaxis_title="Episodio",
            yaxis_title="Epsilon",
            height=300
        )
        st.plotly_chart(fig_epsilon, use_container_width=True)
    
    with col2:
        # Win rate
        fig_winrate = go.Figure()
        fig_winrate.add_trace(
            go.Scatter(x=df['episode'], y=df['win_rate'], 
                      name='Win Rate', line=dict(color='green'))
        )
        fig_winrate.add_hline(y=0.5, line_dash="dash", line_color="gray", 
                             annotation_text="Break-even")
        fig_winrate.update_layout(
            title="Tasa de Acierto",
            xaxis_title="Episodio",
            yaxis_title="Win Rate",
            height=300
        )
        st.plotly_chart(fig_winrate, use_container_width=True)

def render_regime_analysis():
    """Renderizar análisis de regímenes de mercado"""
    df = st.session_state.drl_monitor.get_metrics_df()
    
    if df.empty:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribución de regímenes
        regime_counts = df['market_regime'].value_counts()
        fig_regime = px.pie(
            values=regime_counts.values,
            names=regime_counts.index,
            title="Distribución de Regímenes de Mercado"
        )
        st.plotly_chart(fig_regime, use_container_width=True)
    
    with col2:
        # Rendimiento por régimen
        regime_performance = df.groupby('market_regime')['avg_reward'].mean().reset_index()
        fig_perf = px.bar(
            regime_performance,
            x='market_regime',
            y='avg_reward',
            title="Rendimiento Promedio por Régimen",
            color='avg_reward',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_perf, use_container_width=True)

def render_alerts_panel():
    """Renderizar panel de alertas"""
    st.subheader("🚨 Alertas y Notificaciones")
    
    alerts = st.session_state.drl_monitor.alerts
    
    if not alerts:
        st.success("No hay alertas activas")
        return
    
    # Mostrar alertas recientes
    for alert in alerts[-10:]:  # Últimas 10 alertas
        alert_type = alert['type']
        message = alert['message']
        timestamp = alert['timestamp'].strftime('%H:%M:%S')
        
        if alert_type == 'error':
            st.error(f"[{timestamp}] {message}")
        elif alert_type == 'warning':
            st.warning(f"[{timestamp}] {message}")
        else:
            st.info(f"[{timestamp}] {message}")

def render_configuration_panel():
    """Renderizar panel de configuración"""
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        st.subheader("Umbrales de Alerta")
        
        new_thresholds = {}
        new_thresholds['max_drawdown'] = st.slider(
            "Máximo Drawdown (%)",
            min_value=5, max_value=50, 
            value=int(st.session_state.drl_monitor.alert_thresholds['max_drawdown'] * 100),
            step=1
        ) / 100
        
        new_thresholds['min_sharpe'] = st.slider(
            "Mínimo Sharpe Ratio",
            min_value=0.0, max_value=2.0,
            value=st.session_state.drl_monitor.alert_thresholds['min_sharpe'],
            step=0.1
        )
        
        new_thresholds['max_loss'] = st.slider(
            "Máximo Loss",
            min_value=0.1, max_value=5.0,
            value=st.session_state.drl_monitor.alert_thresholds['max_loss'],
            step=0.1
        )
        
        new_thresholds['min_win_rate'] = st.slider(
            "Mínimo Win Rate (%)",
            min_value=20, max_value=80,
            value=int(st.session_state.drl_monitor.alert_thresholds['min_win_rate'] * 100),
            step=5
        ) / 100
        
        if st.button("Actualizar Umbrales"):
            st.session_state.drl_monitor.alert_thresholds = new_thresholds
            st.success("Umbrales actualizados")
        
        st.subheader("Estado del Sistema")
        status = "🟢 Activo" if st.session_state.drl_monitor.is_monitoring else "🔴 Inactivo"
        st.write(f"Monitoreo: {status}")
        
        metrics_count = len(st.session_state.drl_monitor.metrics_history)
        st.write(f"Métricas: {metrics_count:,}")
        
        alerts_count = len(st.session_state.drl_monitor.alerts)
        st.write(f"Alertas: {alerts_count}")

def render_data_export():
    """Renderizar opciones de exportación"""
    st.subheader("📤 Exportar Datos")
    
    df = st.session_state.drl_monitor.get_metrics_df()
    
    if df.empty:
        st.info("No hay datos para exportar")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Exportar CSV
        csv = df.to_csv(index=False)
        st.download_button(
            label="Descargar CSV",
            data=csv,
            file_name=f"drl_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Exportar JSON
        json_data = df.to_json(orient='records', date_format='iso')
        st.download_button(
            label="Descargar JSON",
            data=json_data,
            file_name=f"drl_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

def main():
    """Función principal del dashboard"""
    # Header
    render_header()
    
    # Panel de configuración (sidebar)
    render_configuration_panel()
    
    # Tarjetas de estado
    render_status_cards()
    
    # Separador
    st.divider()
    
    # Gráficos de rendimiento
    st.subheader("📈 Rendimiento del Agente DRL")
    render_performance_charts()
    
    # Progreso de aprendizaje
    st.subheader("🧠 Progreso de Aprendizaje")
    render_learning_progress()
    
    # Análisis de regímenes
    st.subheader("🌊 Análisis de Regímenes de Mercado")
    render_regime_analysis()
    
    # Panel de alertas
    render_alerts_panel()
    
    # Exportación de datos
    render_data_export()
    
    # Auto-refresh si está monitoreando
    if st.session_state.drl_monitor.is_monitoring:
        time.sleep(1)
        st.rerun()

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar dashboard
    main()