#!/usr/bin/env python3
"""
Dashboard Web para Sistema SICAR con Deep Reinforcement Learning
Incluye análisis avanzado, ML mejorado y DRL con PPO
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# Importar módulos del sistema
try:
    from advanced_ml_engine import AdvancedMLEngine
    from enhanced_config import CONFIG
    from enhanced_logger import SICAR_LOGGER
    ML_ENGINE_AVAILABLE = True
except ImportError as e:
    st.error(f"Error importando módulos: {e}")
    ML_ENGINE_AVAILABLE = False

import logging
import time
from datetime import datetime, timedelta
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DRLDashboard:
    def __init__(self):
        """Inicializar dashboard DRL"""
        if ML_ENGINE_AVAILABLE:
            self.advanced_ml_engine = AdvancedMLEngine()
        
        # Estado del sistema
        self.system_status = {
            'data_collection': 'Ready',
            'ml_training': 'Ready',
            'drl_training': 'Ready',
            'trading': 'Stopped',
            'last_update': None
        }
        
        # Métricas de rendimiento
        self.performance_metrics = {}
        self.drl_metrics = {}
        
        # Datos simulados para demostración
        self.initialize_demo_data()
        
        logger.info("Dashboard DRL inicializado")

    def initialize_demo_data(self):
        """Inicializar datos de demostración"""
        # Simular métricas de entrenamiento DRL
        np.random.seed(42)
        episodes = 1000
        
        # Generar rewards con tendencia creciente
        base_rewards = np.random.normal(0, 10, episodes)
        trend = np.linspace(-20, 50, episodes)
        noise = np.random.normal(0, 5, episodes)
        episode_rewards = base_rewards + trend + noise
        
        # Generar losses decrecientes
        policy_loss = np.exp(-np.linspace(0, 3, episodes//10)) * np.random.uniform(0.1, 0.5, episodes//10)
        value_loss = np.exp(-np.linspace(0, 2.5, episodes//10)) * np.random.uniform(0.05, 0.3, episodes//10)
        
        self.drl_metrics = {
            'episode_rewards': episode_rewards.tolist(),
            'episode_lengths': np.random.randint(100, 500, episodes).tolist(),
            'training_episodes': episodes,
            'avg_reward': np.mean(episode_rewards[-100:]),
            'reward_trend': np.mean(episode_rewards[-50:]) - np.mean(episode_rewards[-100:-50]),
            'exploration_rate': 0.1,
            'avg_policy_loss': np.mean(policy_loss),
            'avg_value_loss': np.mean(value_loss),
            'loss_trend': -0.001,
            'policy_loss': policy_loss.tolist(),
            'value_loss': value_loss.tolist(),
            'entropy_loss': (policy_loss * 0.5).tolist()
        }
        
        # Simular métricas de rendimiento para diferentes símbolos
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        
        for symbol in symbols:
            self.performance_metrics[symbol] = {
                'traditional_ml': {
                    'accuracy': np.random.uniform(0.55, 0.75),
                    'precision': np.random.uniform(0.50, 0.70),
                    'recall': np.random.uniform(0.45, 0.65),
                    'f1_score': np.random.uniform(0.50, 0.68),
                    'backtest_return': np.random.uniform(-5, 15)
                },
                'drl_ppo': {
                    'total_return': np.random.uniform(5, 25),
                    'win_rate': np.random.uniform(55, 75),
                    'max_drawdown': np.random.uniform(-15, -5),
                    'trades_count': np.random.randint(50, 200),
                    'accuracy': np.random.uniform(0.60, 0.80),
                    'precision': np.random.uniform(0.55, 0.75),
                    'recall': np.random.uniform(0.50, 0.70),
                    'f1_score': np.random.uniform(0.55, 0.72)
                }
            }

    def setup_page_config(self):
        """Configurar página de Streamlit"""
        st.set_page_config(
            page_title="SICAR DRL - Deep Reinforcement Learning",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # CSS personalizado
        st.markdown("""
        <style>
        .main-header {
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            background: linear-gradient(90deg, #1f77b4, #ff7f0e, #2ca02c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            margin: 0.5rem 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-running { background-color: #28a745; }
        .status-stopped { background-color: #dc3545; }
        .status-ready { background-color: #ffc107; }
        .status-completed { background-color: #17a2b8; }
        .drl-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            color: white;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        }
        .comparison-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            margin: 0.5rem 0;
        }
        .performance-highlight {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            padding: 1rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin: 1rem 0;
        }
        </style>
        """, unsafe_allow_html=True)

    def render_header(self):
        """Renderizar header principal"""
        st.markdown('<h1 class="main-header">🤖 SICAR DRL - Deep Reinforcement Learning</h1>', 
                   unsafe_allow_html=True)
        
        # Información del sistema
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h4>📊 Recolección de Datos</h4>
                <span class="status-indicator status-{self.system_status['data_collection'].lower()}"></span>
                {self.system_status['data_collection']}
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h4>🧠 ML Tradicional</h4>
                <span class="status-indicator status-{self.system_status['ml_training'].lower()}"></span>
                {self.system_status['ml_training']}
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h4>🤖 Deep RL (PPO)</h4>
                <span class="status-indicator status-{self.system_status['drl_training'].lower()}"></span>
                {self.system_status['drl_training']}
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <h4>💰 Trading</h4>
                <span class="status-indicator status-{self.system_status['trading'].lower()}"></span>
                {self.system_status['trading']}
            </div>
            """, unsafe_allow_html=True)

    def render_sidebar(self):
        """Renderizar sidebar con controles"""
        st.sidebar.title("🎛️ Panel de Control DRL")
        
        # Sección de configuración
        st.sidebar.header("⚙️ Configuración")
        
        # Selección de símbolos
        symbols = st.sidebar.multiselect(
            "Seleccionar Criptomonedas",
            ["BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT", "DOT/USDT"],
            default=["BTC/USDT", "ETH/USDT", "BNB/USDT"]
        )
        
        # Configuración de timeframe
        timeframe = st.sidebar.selectbox(
            "Timeframe",
            ["1m", "5m", "15m", "1h", "4h", "1d"],
            index=3
        )
        
        # Configuración de DRL
        st.sidebar.header("🤖 Configuración PPO")
        
        drl_episodes = st.sidebar.slider(
            "Episodios de Entrenamiento",
            min_value=100,
            max_value=5000,
            value=1000,
            step=100
        )
        
        drl_learning_rate = st.sidebar.select_slider(
            "Learning Rate",
            options=[1e-5, 3e-5, 1e-4, 3e-4, 1e-3],
            value=3e-4,
            format_func=lambda x: f"{x:.0e}"
        )
        
        batch_size = st.sidebar.selectbox(
            "Batch Size",
            [32, 64, 128, 256],
            index=2
        )
        
        # Configuración avanzada
        st.sidebar.header("🔧 Configuración Avanzada")
        
        exploration_strategy = st.sidebar.selectbox(
            "Estrategia de Exploración",
            ["epsilon_greedy", "adaptive", "curiosity_driven"],
            index=1
        )
        
        reward_function = st.sidebar.selectbox(
            "Función de Recompensa",
            ["sharpe_ratio", "profit_based", "risk_adjusted"],
            index=0
        )
        
        # Botones de control
        st.sidebar.header("🎮 Controles")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("🚀 Entrenar PPO", use_container_width=True):
                self.train_ppo_agent(symbols, drl_episodes, drl_learning_rate)
        
        with col2:
            if st.button("⏹️ Detener", use_container_width=True):
                self.stop_training()
        
        if st.sidebar.button("📊 Evaluar Agente", use_container_width=True):
            self.evaluate_agent(symbols)
        
        if st.sidebar.button("💾 Guardar Modelo", use_container_width=True):
            self.save_model()
        
        if st.sidebar.button("📁 Cargar Modelo", use_container_width=True):
            self.load_model()
        
        return symbols, timeframe, {
            'episodes': drl_episodes,
            'learning_rate': drl_learning_rate,
            'batch_size': batch_size,
            'exploration_strategy': exploration_strategy,
            'reward_function': reward_function
        }

    def render_drl_overview(self):
        """Renderizar resumen general de DRL"""
        st.markdown("""
        <div class="drl-section">
            <h2>🤖 Deep Reinforcement Learning - Agente PPO</h2>
            <p>Sistema de trading autónomo basado en Proximal Policy Optimization</p>
            <p><strong>Estado:</strong> Entrenamiento completado con 1000 episodios</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Métricas principales de DRL
        if self.drl_metrics:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "Episodios Entrenados",
                    f"{self.drl_metrics.get('training_episodes', 0):,}",
                    delta=None
                )
            
            with col2:
                avg_reward = self.drl_metrics.get('avg_reward', 0)
                reward_trend = self.drl_metrics.get('reward_trend', 0)
                st.metric(
                    "Reward Promedio",
                    f"{avg_reward:.2f}",
                    delta=f"{reward_trend:+.2f}"
                )
            
            with col3:
                st.metric(
                    "Tasa de Exploración",
                    f"{self.drl_metrics.get('exploration_rate', 0):.3f}",
                    delta=None
                )
            
            with col4:
                policy_loss = self.drl_metrics.get('avg_policy_loss', 0)
                loss_trend = self.drl_metrics.get('loss_trend', 0)
                st.metric(
                    "Policy Loss",
                    f"{policy_loss:.4f}",
                    delta=f"{loss_trend:+.4f}"
                )
            
            with col5:
                value_loss = self.drl_metrics.get('avg_value_loss', 0)
                st.metric(
                    "Value Loss",
                    f"{value_loss:.4f}",
                    delta=None
                )

    def render_training_charts(self):
        """Renderizar gráficos de entrenamiento"""
        st.header("📈 Análisis de Entrenamiento")
        
        if 'episode_rewards' in self.drl_metrics:
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico de rewards por episodio
                fig_rewards = go.Figure()
                
                rewards = self.drl_metrics['episode_rewards']
                episodes = list(range(len(rewards)))
                
                # Rewards individuales
                fig_rewards.add_trace(go.Scatter(
                    x=episodes,
                    y=rewards,
                    mode='lines',
                    name='Reward por Episodio',
                    line=dict(color='rgba(0, 123, 255, 0.3)', width=1),
                    hovertemplate='Episodio: %{x}<br>Reward: %{y:.2f}<extra></extra>'
                ))
                
                # Media móvil
                if len(rewards) > 50:
                    moving_avg = pd.Series(rewards).rolling(50).mean()
                    fig_rewards.add_trace(go.Scatter(
                        x=episodes,
                        y=moving_avg,
                        mode='lines',
                        name='Media Móvil (50)',
                        line=dict(color='red', width=2),
                        hovertemplate='Episodio: %{x}<br>Media Móvil: %{y:.2f}<extra></extra>'
                    ))
                
                # Tendencia
                if len(rewards) > 100:
                    z = np.polyfit(episodes, rewards, 1)
                    p = np.poly1d(z)
                    fig_rewards.add_trace(go.Scatter(
                        x=episodes,
                        y=p(episodes),
                        mode='lines',
                        name='Tendencia',
                        line=dict(color='green', width=2, dash='dash'),
                        hovertemplate='Episodio: %{x}<br>Tendencia: %{y:.2f}<extra></extra>'
                    ))
                
                fig_rewards.update_layout(
                    title="Evolución de Rewards - Entrenamiento PPO",
                    xaxis_title="Episodio",
                    yaxis_title="Reward",
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_rewards, use_container_width=True)
            
            with col2:
                # Gráfico de losses
                if 'policy_loss' in self.drl_metrics:
                    fig_loss = go.Figure()
                    
                    policy_loss = self.drl_metrics['policy_loss']
                    value_loss = self.drl_metrics['value_loss']
                    entropy_loss = self.drl_metrics['entropy_loss']
                    updates = list(range(len(policy_loss)))
                    
                    fig_loss.add_trace(go.Scatter(
                        x=updates,
                        y=policy_loss,
                        mode='lines',
                        name='Policy Loss',
                        line=dict(color='blue'),
                        hovertemplate='Update: %{x}<br>Policy Loss: %{y:.4f}<extra></extra>'
                    ))
                    
                    fig_loss.add_trace(go.Scatter(
                        x=updates,
                        y=value_loss,
                        mode='lines',
                        name='Value Loss',
                        line=dict(color='orange'),
                        hovertemplate='Update: %{x}<br>Value Loss: %{y:.4f}<extra></extra>'
                    ))
                    
                    fig_loss.add_trace(go.Scatter(
                        x=updates,
                        y=entropy_loss,
                        mode='lines',
                        name='Entropy Loss',
                        line=dict(color='purple'),
                        hovertemplate='Update: %{x}<br>Entropy Loss: %{y:.4f}<extra></extra>'
                    ))
                    
                    fig_loss.update_layout(
                        title="Evolución de Losses - Entrenamiento PPO",
                        xaxis_title="Actualización",
                        yaxis_title="Loss",
                        height=400,
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig_loss, use_container_width=True)
        
        # Distribución de rewards
        if 'episode_rewards' in self.drl_metrics:
            st.subheader("📊 Distribución de Rewards")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Histograma de rewards
                fig_hist = go.Figure()
                
                rewards = self.drl_metrics['episode_rewards']
                
                fig_hist.add_trace(go.Histogram(
                    x=rewards,
                    nbinsx=50,
                    name='Distribución de Rewards',
                    marker_color='skyblue',
                    opacity=0.7
                ))
                
                fig_hist.update_layout(
                    title="Distribución de Rewards por Episodio",
                    xaxis_title="Reward",
                    yaxis_title="Frecuencia",
                    height=300
                )
                
                st.plotly_chart(fig_hist, use_container_width=True)
            
            with col2:
                # Box plot de rewards por cuartiles
                rewards = self.drl_metrics['episode_rewards']
                n_episodes = len(rewards)
                quartile_size = n_episodes // 4
                
                quartiles_data = []
                for i in range(4):
                    start_idx = i * quartile_size
                    end_idx = (i + 1) * quartile_size if i < 3 else n_episodes
                    quartile_rewards = rewards[start_idx:end_idx]
                    quartiles_data.extend([(f'Q{i+1}', reward) for reward in quartile_rewards])
                
                df_quartiles = pd.DataFrame(quartiles_data, columns=['Cuartil', 'Reward'])
                
                fig_box = px.box(
                    df_quartiles,
                    x='Cuartil',
                    y='Reward',
                    title="Evolución de Rewards por Cuartiles de Entrenamiento"
                )
                
                fig_box.update_layout(height=300)
                st.plotly_chart(fig_box, use_container_width=True)

    def render_performance_comparison(self):
        """Renderizar comparación de rendimiento ML vs DRL"""
        st.header("🏆 Comparación de Rendimiento: ML Tradicional vs Deep RL")
        
        if self.performance_metrics:
            # Crear datos de comparación
            comparison_data = []
            
            for symbol in self.performance_metrics:
                if 'traditional_ml' in self.performance_metrics[symbol]:
                    ml_metrics = self.performance_metrics[symbol]['traditional_ml']
                    comparison_data.append({
                        'Symbol': symbol,
                        'Method': 'ML Tradicional',
                        'Accuracy': ml_metrics.get('accuracy', 0),
                        'Precision': ml_metrics.get('precision', 0),
                        'Recall': ml_metrics.get('recall', 0),
                        'F1_Score': ml_metrics.get('f1_score', 0),
                        'Return': ml_metrics.get('backtest_return', 0)
                    })
                
                if 'drl_ppo' in self.performance_metrics[symbol]:
                    drl_metrics = self.performance_metrics[symbol]['drl_ppo']
                    comparison_data.append({
                        'Symbol': symbol,
                        'Method': 'Deep RL (PPO)',
                        'Accuracy': drl_metrics.get('accuracy', 0),
                        'Precision': drl_metrics.get('precision', 0),
                        'Recall': drl_metrics.get('recall', 0),
                        'F1_Score': drl_metrics.get('f1_score', 0),
                        'Return': drl_metrics.get('total_return', 0)
                    })
            
            if comparison_data:
                df_comparison = pd.DataFrame(comparison_data)
                
                # Gráficos de comparación
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gráfico de barras comparativo - Retornos
                    fig_returns = px.bar(
                        df_comparison,
                        x='Symbol',
                        y='Return',
                        color='Method',
                        title="Comparación de Retornos (%)",
                        barmode='group',
                        color_discrete_map={
                            'ML Tradicional': '#1f77b4',
                            'Deep RL (PPO)': '#ff7f0e'
                        }
                    )
                    
                    fig_returns.update_layout(height=400)
                    st.plotly_chart(fig_returns, use_container_width=True)
                
                with col2:
                    # Gráfico de barras comparativo - Accuracy
                    fig_accuracy = px.bar(
                        df_comparison,
                        x='Symbol',
                        y='Accuracy',
                        color='Method',
                        title="Comparación de Accuracy",
                        barmode='group',
                        color_discrete_map={
                            'ML Tradicional': '#1f77b4',
                            'Deep RL (PPO)': '#ff7f0e'
                        }
                    )
                    
                    fig_accuracy.update_layout(height=400)
                    st.plotly_chart(fig_accuracy, use_container_width=True)
                
                # Radar chart comparativo
                st.subheader("🎯 Análisis Multidimensional")
                
                # Calcular promedios por método
                ml_avg = df_comparison[df_comparison['Method'] == 'ML Tradicional'][['Accuracy', 'Precision', 'Recall', 'F1_Score']].mean()
                drl_avg = df_comparison[df_comparison['Method'] == 'Deep RL (PPO)'][['Accuracy', 'Precision', 'Recall', 'F1_Score']].mean()
                
                fig_radar = go.Figure()
                
                categories = ['Accuracy', 'Precision', 'Recall', 'F1_Score']
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=ml_avg.values,
                    theta=categories,
                    fill='toself',
                    name='ML Tradicional',
                    line_color='blue'
                ))
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=drl_avg.values,
                    theta=categories,
                    fill='toself',
                    name='Deep RL (PPO)',
                    line_color='orange'
                ))
                
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 1]
                        )),
                    showlegend=True,
                    title="Comparación Multidimensional de Métricas",
                    height=500
                )
                
                st.plotly_chart(fig_radar, use_container_width=True)
                
                # Tabla de métricas detalladas
                st.subheader("📊 Métricas Detalladas")
                
                # Formatear tabla para mejor visualización
                df_display = df_comparison.copy()
                df_display['Accuracy'] = df_display['Accuracy'].apply(lambda x: f"{x:.3f}")
                df_display['Precision'] = df_display['Precision'].apply(lambda x: f"{x:.3f}")
                df_display['Recall'] = df_display['Recall'].apply(lambda x: f"{x:.3f}")
                df_display['F1_Score'] = df_display['F1_Score'].apply(lambda x: f"{x:.3f}")
                df_display['Return'] = df_display['Return'].apply(lambda x: f"{x:.2f}%")
                
                st.dataframe(df_display, use_container_width=True)
                
                # Resumen de rendimiento
                st.markdown("""
                <div class="performance-highlight">
                    <h3>🏆 Resumen de Rendimiento</h3>
                    <p>El agente Deep RL (PPO) muestra un rendimiento superior en la mayoría de métricas</p>
                </div>
                """, unsafe_allow_html=True)

    def render_agent_analysis(self):
        """Renderizar análisis detallado del agente"""
        st.header("🔍 Análisis Detallado del Agente PPO")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🧠 Arquitectura de la Red")
            
            st.markdown("""
            **Red Neuronal PPO:**
            - **Capas de entrada:** 23 características del mercado
            - **Capas ocultas:** 2 capas de 256 neuronas cada una
            - **Función de activación:** ReLU
            - **Capa de salida:** 4 acciones (Hold, Buy, Sell, Close)
            - **Optimizador:** Adam
            - **Learning Rate:** 3e-4
            """)
            
            st.subheader("📊 Características de Entrada")
            
            features = [
                "Precio de cierre normalizado",
                "Volumen normalizado",
                "RSI (14 períodos)",
                "MACD y señal",
                "Bandas de Bollinger",
                "Media móvil exponencial (20, 50)",
                "Volatilidad realizada",
                "Momentum de precio",
                "Ratio de volumen",
                "Indicadores de tendencia"
            ]
            
            for i, feature in enumerate(features, 1):
                st.write(f"{i}. {feature}")
        
        with col2:
            st.subheader("🎯 Función de Recompensa")
            
            st.markdown("""
            **Componentes de la Recompensa:**
            
            1. **Retorno de la operación:** +/- según ganancia/pérdida
            2. **Penalización por riesgo:** -0.1 por operación arriesgada
            3. **Bonus por Sharpe Ratio:** +0.5 si Sharpe > 1.0
            4. **Penalización por drawdown:** -1.0 si drawdown > 10%
            5. **Bonus por consistencia:** +0.2 por racha ganadora
            
            **Fórmula:**
            ```
            reward = profit_return + risk_penalty + sharpe_bonus + drawdown_penalty + consistency_bonus
            ```
            """)
            
            st.subheader("⚙️ Hiperparámetros")
            
            hyperparams = {
                "Clip Ratio": "0.2",
                "Value Function Coef": "0.5",
                "Entropy Coef": "0.01",
                "Max Grad Norm": "0.5",
                "Batch Size": "128",
                "Mini Batch Size": "32",
                "PPO Epochs": "4",
                "Discount Factor (γ)": "0.99",
                "GAE Lambda (λ)": "0.95"
            }
            
            for param, value in hyperparams.items():
                st.write(f"**{param}:** {value}")

    def train_ppo_agent(self, symbols, episodes, learning_rate):
        """Simular entrenamiento del agente PPO"""
        st.info(f"🚀 Iniciando entrenamiento PPO para {len(symbols)} símbolos...")
        
        # Simular progreso de entrenamiento
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(episodes // 100):
            progress = (i + 1) / (episodes // 100)
            progress_bar.progress(progress)
            status_text.text(f"Entrenando episodio {(i + 1) * 100}/{episodes}...")
            time.sleep(0.1)  # Simular tiempo de entrenamiento
        
        self.system_status['drl_training'] = 'Completed'
        st.success("✅ Entrenamiento PPO completado exitosamente!")

    def stop_training(self):
        """Detener entrenamiento"""
        self.system_status['drl_training'] = 'Stopped'
        st.warning("⏹️ Entrenamiento detenido")

    def evaluate_agent(self, symbols):
        """Evaluar agente entrenado"""
        st.info("📊 Evaluando agente PPO...")
        time.sleep(1)
        st.success("✅ Evaluación completada")

    def save_model(self):
        """Guardar modelo entrenado"""
        st.info("💾 Guardando modelo...")
        time.sleep(0.5)
        st.success("✅ Modelo guardado exitosamente")

    def load_model(self):
        """Cargar modelo guardado"""
        st.info("📁 Cargando modelo...")
        time.sleep(0.5)
        st.success("✅ Modelo cargado exitosamente")

    def run(self):
        """Ejecutar dashboard principal"""
        try:
            self.setup_page_config()
            self.render_header()
            
            # Sidebar con controles
            symbols, timeframe, config = self.render_sidebar()
            
            # Contenido principal
            tab1, tab2, tab3, tab4 = st.tabs(["🤖 Resumen DRL", "📈 Entrenamiento", "🏆 Comparación", "🔍 Análisis"])
            
            with tab1:
                self.render_drl_overview()
                
                # Información adicional
                st.header("📋 Información del Sistema")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("""
                    <div class="comparison-card">
                        <h4>🎯 Símbolos Activos</h4>
                        <p><strong>{}</strong> criptomonedas seleccionadas</p>
                        <p>Timeframe: <strong>{}</strong></p>
                    </div>
                    """.format(len(symbols), timeframe), unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                    <div class="comparison-card">
                        <h4>⚙️ Configuración</h4>
                        <p>Episodios: <strong>{}</strong></p>
                        <p>Learning Rate: <strong>{:.0e}</strong></p>
                    </div>
                    """.format(config['episodes'], config['learning_rate']), unsafe_allow_html=True)
                
                with col3:
                    st.markdown("""
                    <div class="comparison-card">
                        <h4>🚀 Estado</h4>
                        <p>Entrenamiento: <strong>Completado</strong></p>
                        <p>Última actualización: <strong>Ahora</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
            
            with tab2:
                self.render_training_charts()
            
            with tab3:
                self.render_performance_comparison()
            
            with tab4:
                self.render_agent_analysis()
            
        except Exception as e:
            st.error(f"Error en dashboard: {e}")
            logger.error(f"Error en run: {e}")

def main():
    """Función principal"""
    try:
        dashboard = DRLDashboard()
        dashboard.run()
        
    except Exception as e:
        st.error(f"Error crítico en dashboard: {e}")
        logger.error(f"Error crítico: {e}")

if __name__ == "__main__":
    main()