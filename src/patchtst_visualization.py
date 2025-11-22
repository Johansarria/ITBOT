#!/usr/bin/env python3
"""
Visualización de predicciones PatchTST para SICAR
Crea gráficos interactivos de predicciones y análisis de trading
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class PatchTSTVisualizer:
    """
    Visualizador de predicciones y análisis de PatchTST
    """
    
    def __init__(self, style: str = "default"):
        self.style = style
        try:
            plt.style.use(style)
        except:
            plt.style.use("default")
        sns.set_palette("husl")
        
    def create_prediction_chart(self, 
                              historical_data: pd.DataFrame,
                              predictions: np.ndarray,
                              confidence_intervals: Optional[np.ndarray] = None,
                              title: str = "Predicción de Precios con PatchTST") -> go.Figure:
        """
        Crear gráfico interactivo de predicciones
        
        Args:
            historical_data: Datos históricos
            predictions: Predicciones del modelo
            confidence_intervals: Intervalos de confianza
            title: Título del gráfico
            
        Returns:
            Figura de Plotly
        """
        logger.info("Creando gráfico de predicciones")
        
        # Crear fechas para las predicciones
        last_date = historical_data['timestamp'].iloc[-1]
        pred_dates = pd.date_range(
            start=last_date + timedelta(hours=1), 
            periods=len(predictions), 
            freq='H'
        )
        
        # Crear figura con subplots
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=('Precio y Predicción', 'Volumen'),
            row_heights=[0.7, 0.3]
        )
        
        # Agregar datos históricos
        fig.add_trace(
            go.Scatter(
                x=historical_data['timestamp'],
                y=historical_data['close'],
                name='Precio Histórico',
                line=dict(color='blue', width=2),
                opacity=0.8
            ),
            row=1, col=1
        )
        
        # Agregar predicciones
        fig.add_trace(
            go.Scatter(
                x=pred_dates,
                y=predictions.flatten(),
                name='Predicción PatchTST',
                line=dict(color='red', width=3),
                mode='lines+markers'
            ),
            row=1, col=1
        )
        
        # Agregar intervalos de confianza si están disponibles
        if confidence_intervals is not None:
            upper_bound = predictions.flatten() + confidence_intervals
            lower_bound = predictions.flatten() - confidence_intervals
            
            fig.add_trace(
                go.Scatter(
                    x=pred_dates,
                    y=upper_bound,
                    name='Límite Superior',
                    line=dict(width=0),
                    showlegend=False
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=pred_dates,
                    y=lower_bound,
                    name='Intervalo de Confianza',
                    line=dict(width=0),
                    fill='tonexty',
                    fillcolor='rgba(255,0,0,0.2)',
                    mode='lines'
                ),
                row=1, col=1
            )
        
        # Agregar volumen
        fig.add_trace(
            go.Bar(
                x=historical_data['timestamp'],
                y=historical_data['volume'],
                name='Volumen',
                marker_color='lightblue',
                opacity=0.6
            ),
            row=2, col=1
        )
        
        # Actualizar layout
        fig.update_layout(
            title=title,
            xaxis_title="Fecha",
            yaxis_title="Precio (USD)",
            height=800,
            showlegend=True,
            hovermode='x unified'
        )
        
        return fig
    
    def create_technical_analysis_chart(self, 
                                       data: pd.DataFrame,
                                       indicators: Dict[str, pd.Series]) -> go.Figure:
        """
        Crear gráfico de análisis técnico
        
        Args:
            data: Datos OHLCV
            indicators: Diccionario de indicadores técnicos
            
        Returns:
            Figura de Plotly
        """
        logger.info("Creando gráfico de análisis técnico")
        
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=('Precio y Medias Móviles', 'RSI', 'MACD', 'Volatilidad'),
            row_heights=[0.4, 0.2, 0.2, 0.2]
        )
        
        # Precio y medias móviles
        fig.add_trace(
            go.Candlestick(
                x=data['timestamp'],
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name='Candlesticks'
            ),
            row=1, col=1
        )
        
        # Agregar indicadores si están disponibles
        if 'sma_20' in indicators:
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=indicators['sma_20'],
                    name='SMA 20',
                    line=dict(color='orange', width=2)
                ),
                row=1, col=1
            )
        
        if 'sma_50' in indicators:
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=indicators['sma_50'],
                    name='SMA 50',
                    line=dict(color='purple', width=2)
                ),
                row=1, col=1
            )
        
        # RSI
        if 'rsi' in indicators:
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=indicators['rsi'],
                    name='RSI',
                    line=dict(color='blue', width=2)
                ),
                row=2, col=1
            )
            
            # Líneas de referencia RSI
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        # MACD
        if 'macd' in indicators and 'macd_signal' in indicators:
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=indicators['macd'],
                    name='MACD',
                    line=dict(color='red', width=2)
                ),
                row=3, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=indicators['macd_signal'],
                    name='MACD Signal',
                    line=dict(color='blue', width=2)
                ),
                row=3, col=1
            )
        
        # Volatilidad
        if 'volatility' in indicators:
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=indicators['volatility'],
                    name='Volatilidad',
                    line=dict(color='purple', width=2)
                ),
                row=4, col=1
            )
        
        # Actualizar layout
        fig.update_layout(
            title="Análisis Técnico Completo",
            height=1200,
            showlegend=True,
            hovermode='x unified'
        )
        
        return fig
    
    def create_risk_analysis_dashboard(self, 
                                     risk_metrics: Dict[str, float],
                                     portfolio_value: float = 10000.0) -> go.Figure:
        """
        Crear dashboard de análisis de riesgo
        
        Args:
            risk_metrics: Métricas de riesgo (VaR, Sharpe, etc.)
            portfolio_value: Valor del portafolio
            
        Returns:
            Figura de Plotly
        """
        logger.info("Creando dashboard de análisis de riesgo")
        
        # Crear subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Métricas de Riesgo', 'Distribución de Retornos', 
                           'VaR por Confianza', 'Ratio de Sharpe'),
            specs=[[{"type": "indicator"}, {"type": "histogram"}],
                   [{"type": "scatter"}, {"type": "indicator"}]]
        )
        
        # Indicador de VaR
        var_value = risk_metrics.get('var_95', 0) * portfolio_value
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=var_value,
                title={'text': f"VaR 95%<br><span style='font-size:0.8em;color:gray'>Pérdida Máxima</span>"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={'axis': {'range': [None, portfolio_value * 0.2]},
                       'bar': {'color': "darkred"},
                       'steps': [
                           {'range': [0, portfolio_value * 0.05], 'color': "lightgray"},
                           {'range': [portfolio_value * 0.05, portfolio_value * 0.15], 'color': "yellow"}],
                       'threshold': {'line': {'color': "red", 'width': 4},
                                   'thickness': 0.75, 'value': portfolio_value * 0.1}}
            ),
            row=1, col=1
        )
        
        # Histograma de retornos (datos simulados)
        np.random.seed(42)
        returns = np.random.normal(0, risk_metrics.get('volatility', 0.02), 1000)
        fig.add_trace(
            go.Histogram(
                x=returns,
                nbinsx=30,
                name='Retornos',
                marker_color='lightblue'
            ),
            row=1, col=2
        )
        
        # VaR por niveles de confianza
        confidence_levels = [90, 95, 99]
        var_values = [risk_metrics.get(f'var_{level}', 0) * portfolio_value for level in confidence_levels]
        
        fig.add_trace(
            go.Scatter(
                x=confidence_levels,
                y=var_values,
                mode='lines+markers',
                name='VaR',
                line=dict(color='red', width=3)
            ),
            row=2, col=1
        )
        
        # Indicador de Sharpe Ratio
        sharpe = risk_metrics.get('sharpe_ratio', 0)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=sharpe,
                title={'text': f"Sharpe Ratio<br><span style='font-size:0.8em;color:gray'>Risk-Adjusted Return</span>"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={'axis': {'range': [None, 3]},
                       'bar': {'color': "green" if sharpe > 1 else "orange" if sharpe > 0 else "red"},
                       'steps': [
                           {'range': [0, 1], 'color': "lightgray"},
                           {'range': [1, 2], 'color': "lightgreen"}],
                       'threshold': {'line': {'color': "green", 'width': 4},
                                   'thickness': 0.75, 'value': 1}}
            ),
            row=2, col=2
        )
        
        # Actualizar layout
        fig.update_layout(
            title="Dashboard de Análisis de Riesgo - SICAR",
            height=800,
            showlegend=False
        )
        
        return fig
    
    def create_trading_signals_chart(self, 
                              data: pd.DataFrame,
                              signals: List[Dict],
                              title: str = "Señales de Trading PatchTST") -> go.Figure:
        """
        Crear gráfico de señales de trading
        
        Args:
            data: Datos de precios
            signals: Lista de señales de trading
            title: Título del gráfico
            
        Returns:
            Figura de Plotly
        """
        logger.info("Creando gráfico de señales de trading")
        
        fig = go.Figure()
        
        # Agregar precio
        fig.add_trace(
            go.Scatter(
                x=data['timestamp'],
                y=data['close'],
                name='Precio',
                line=dict(color='blue', width=2)
            )
        )
        
        # Agregar señales
        buy_signals = [s for s in signals if s['signal'] == 'BUY']
        sell_signals = [s for s in signals if s['signal'] == 'SELL']
        
        if buy_signals:
            buy_dates = [s['timestamp'] for s in buy_signals]
            buy_prices = [s['price'] for s in buy_signals]
            
            fig.add_trace(
                go.Scatter(
                    x=buy_dates,
                    y=buy_prices,
                    mode='markers',
                    name='Señal COMPRA',
                    marker=dict(color='green', size=12, symbol='triangle-up')
                )
            )
        
        if sell_signals:
            sell_dates = [s['timestamp'] for s in sell_signals]
            sell_prices = [s['price'] for s in sell_signals]
            
            fig.add_trace(
                go.Scatter(
                    x=sell_dates,
                    y=sell_prices,
                    mode='markers',
                    name='Señal VENTA',
                    marker=dict(color='red', size=12, symbol='triangle-down')
                )
            )
        
        # Actualizar layout
        fig.update_layout(
            title=title,
            xaxis_title="Fecha",
            yaxis_title="Precio (USD)",
            height=600,
            showlegend=True,
            hovermode='x unified'
        )
        
        return fig

    def create_multi_asset_realtime_chart(self,
                                          data_btc: pd.DataFrame,
                                          data_eth: pd.DataFrame,
                                          signals_btc: List[Dict],
                                          signals_eth: List[Dict],
                                          title: str = "BTC vs ETH - Tiempo Real y Señales") -> go.Figure:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=data_btc['timestamp'],
                y=data_btc['close'],
                name='BTC-USD',
                line=dict(color='blue', width=2)
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data_eth['timestamp'],
                y=data_eth['close'],
                name='ETH-USD',
                line=dict(color='orange', width=2)
            )
        )
        entradas_btc = [s for s in signals_btc if s['signal'] == 'BUY']
        salidas_btc = [s for s in signals_btc if s['signal'] == 'SELL']
        entradas_eth = [s for s in signals_eth if s['signal'] == 'BUY']
        salidas_eth = [s for s in signals_eth if s['signal'] == 'SELL']
        if entradas_btc:
            fig.add_trace(
                go.Scatter(
                    x=[s['timestamp'] for s in entradas_btc],
                    y=[s['price'] for s in entradas_btc],
                    mode='markers',
                    name='BTC Entrada',
                    marker=dict(color='green', size=12, symbol='triangle-up')
                )
            )
        if salidas_btc:
            fig.add_trace(
                go.Scatter(
                    x=[s['timestamp'] for s in salidas_btc],
                    y=[s['price'] for s in salidas_btc],
                    mode='markers',
                    name='BTC Salida',
                    marker=dict(color='red', size=12, symbol='triangle-down')
                )
            )
        if entradas_eth:
            fig.add_trace(
                go.Scatter(
                    x=[s['timestamp'] for s in entradas_eth],
                    y=[s['price'] for s in entradas_eth],
                    mode='markers',
                    name='ETH Entrada',
                    marker=dict(color='darkgreen', size=12, symbol='triangle-up')
                )
            )
        if salidas_eth:
            fig.add_trace(
                go.Scatter(
                    x=[s['timestamp'] for s in salidas_eth],
                    y=[s['price'] for s in salidas_eth],
                    mode='markers',
                    name='ETH Salida',
                    marker=dict(color='darkred', size=12, symbol='triangle-down')
                )
            )
        fig.update_layout(
            title=title,
            xaxis_title="Fecha",
            yaxis_title="Precio (USD)",
            height=700,
            showlegend=True,
            hovermode='x unified'
        )
        return fig
    
    def save_dashboard_html(self, 
                          figures: Dict[str, go.Figure], 
                          filename: str = "patchtst_dashboard.html",
                          extra_sections: Dict[str, str] | None = None):
        """
        Guardar dashboard completo como HTML
        
        Args:
            figures: Diccionario de figuras
            filename: Nombre del archivo
        """
        logger.info(f"Guardando dashboard HTML: {filename}")
        
        # Crear HTML completo
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PatchTST Dashboard - SICAR</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
                .header { text-align: center; color: #333; margin-bottom: 30px; }
                .chart-container { margin-bottom: 40px; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .metrics { display: flex; justify-content: space-around; margin: 20px 0; }
                .metric { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }
                .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
                .metric-label { font-size: 14px; color: #666; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 PatchTST Dashboard - SICAR Trading System</h1>
                <p>Análisis de predicciones y señales de trading con Inteligencia Artificial</p>
                <p id="timestamp"></p>
            </div>
        """
        
        # Agregar cada figura
        for name, fig in figures.items():
            html_content += f'<div class="chart-container">'
            html_content += f'<h2>{name.replace("_", " ").title()}</h2>'
            html_content += fig.to_html(include_plotlyjs='cdn', div_id=f"{name}_div")
            html_content += '</div>'

        if extra_sections:
            for sec_name, sec_content in extra_sections.items():
                html_content += f'<div class="chart-container">'
                html_content += f'<h2>{sec_name.replace("_", " ").title()}</h2>'
                html_content += f'<pre style="white-space: pre-wrap;">{sec_content}</pre>'
                html_content += '</div>'
        
        # Agregar script para timestamp
        html_content += """
            <script>
                document.getElementById('timestamp').textContent = 
                    'Última actualización: ' + new Date().toLocaleString('es-ES');
            </script>
        </body>
        </html>
        """
        
        # Guardar archivo
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Dashboard guardado exitosamente: {filename}")

def create_sample_visualization():
    """Crear visualización de ejemplo"""
    visualizer = PatchTSTVisualizer()
    
    # Crear datos de ejemplo
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    volume = np.random.randint(1000, 10000, 100)
    
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices - 50,
        'high': prices + 100,
        'low': prices - 150,
        'close': prices,
        'volume': volume
    })
    
    # Crear predicciones de ejemplo
    predictions = prices[-1] + np.cumsum(np.random.randn(24) * 50)
    
    # Crear figuras
    fig1 = visualizer.create_prediction_chart(sample_data, predictions)
    fig2 = visualizer.create_technical_analysis_chart(sample_data, {
        'rsi': 50 + np.random.randn(100) * 20,
        'macd': np.random.randn(100) * 0.1,
        'macd_signal': np.random.randn(100) * 0.05,
        'volatility': np.abs(np.random.randn(100) * 0.02)
    })
    
    risk_metrics = {
        'var_95': 0.05,
        'var_99': 0.08,
        'sharpe_ratio': 1.5,
        'volatility': 0.02
    }
    
    fig3 = visualizer.create_risk_analysis_dashboard(risk_metrics)
    
    # Guardar dashboard
    figures = {
        'predicciones': fig1,
        'analisis_tecnico': fig2,
        'riesgo': fig3
    }
    
    visualizer.save_dashboard_html(figures, "patchtst_demo.html")
    print("✅ Dashboard de demo creado: patchtst_demo.html")

if __name__ == '__main__':
    print("🎨 Visualizador PatchTST - SICAR")
    print("="*50)
    
    create_sample_visualization()
    
    print("\n✅ Demo completado exitosamente!")
    print("📊 Abre 'patchtst_demo.html' en tu navegador para ver los gráficos")
