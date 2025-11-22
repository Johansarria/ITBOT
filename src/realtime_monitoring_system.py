#!/usr/bin/env python3
"""
Sistema de Monitoreo en Tiempo Real para SICAR
Integración de factores de mercado externos
Monitoreo continuo de performance y condiciones de mercado
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# APIs y datos en tiempo real
import yfinance as yf
import requests
import json
import time
import threading
from queue import Queue

# Análisis técnico
import talib

# Visualización en tiempo real
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

logger = logging.getLogger(__name__)

class RealtimeMonitoringSystem:
    def __init__(self, update_interval=60):
        """Inicializar sistema de monitoreo en tiempo real"""
        self.update_interval = update_interval  # segundos
        self.is_monitoring = False
        self.data_queue = Queue()
        
        # Datos de mercado
        self.market_data = {}
        self.external_factors = {}
        self.sentiment_data = {}
        
        # Métricas de performance
        self.performance_metrics = {}
        self.alerts = []
        
        # Configuración de APIs
        self.apis = {
            'fear_greed_index': 'https://api.alternative.me/fng/',
            'crypto_news': 'https://newsapi.org/v2/everything',
            'market_cap': 'https://api.coingecko.com/api/v3/global',
            'dominance': 'https://api.coingecko.com/api/v3/global'
        }
        
        # Símbolos a monitorear
        self.symbols = ['BTC-USD', 'ETH-USD', 'ADA-USD', 'SOL-USD', 'XRP-USD']
        
        # Factores de mercado
        self.market_factors = {
            'fear_greed_index': 50,
            'btc_dominance': 50,
            'total_market_cap': 0,
            'volume_24h': 0,
            'news_sentiment': 0,
            'volatility_index': 0,
            'correlation_index': 0
        }
        
        logger.info("Sistema de monitoreo en tiempo real inicializado")

    def fetch_fear_greed_index(self):
        """Obtener índice de miedo y codicia"""
        try:
            response = requests.get(self.apis['fear_greed_index'], timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    fgi = int(data['data'][0]['value'])
                    self.market_factors['fear_greed_index'] = fgi
                    logger.info(f"Fear & Greed Index: {fgi}")
                    return fgi
        except Exception as e:
            logger.error(f"Error obteniendo Fear & Greed Index: {e}")
        return 50

    def fetch_market_dominance(self):
        """Obtener dominancia de Bitcoin y datos globales"""
        try:
            response = requests.get(self.apis['dominance'], timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    btc_dominance = data['data'].get('market_cap_percentage', {}).get('btc', 50)
                    total_market_cap = data['data'].get('total_market_cap', {}).get('usd', 0)
                    volume_24h = data['data'].get('total_volume', {}).get('usd', 0)
                    
                    self.market_factors['btc_dominance'] = btc_dominance
                    self.market_factors['total_market_cap'] = total_market_cap
                    self.market_factors['volume_24h'] = volume_24h
                    
                    logger.info(f"BTC Dominance: {btc_dominance:.1f}%")
                    return True
        except Exception as e:
            logger.error(f"Error obteniendo dominancia de mercado: {e}")
        return False

    def fetch_realtime_prices(self):
        """Obtener precios en tiempo real"""
        try:
            price_data = {}
            
            for symbol in self.symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    
                    if 'regularMarketPrice' in info:
                        price_data[symbol] = {
                            'price': info['regularMarketPrice'],
                            'change': info.get('regularMarketChange', 0),
                            'change_percent': info.get('regularMarketChangePercent', 0),
                            'volume': info.get('regularMarketVolume', 0),
                            'timestamp': datetime.now()
                        }
                except Exception as e:
                    logger.warning(f"Error obteniendo precio para {symbol}: {e}")
            
            self.market_data.update(price_data)
            return price_data
            
        except Exception as e:
            logger.error(f"Error obteniendo precios en tiempo real: {e}")
            return {}

    def calculate_market_volatility(self):
        """Calcular índice de volatilidad del mercado"""
        try:
            volatilities = []
            
            for symbol in self.symbols:
                try:
                    # Obtener datos históricos recientes
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='5d', interval='1h')
                    
                    if not hist.empty:
                        returns = hist['Close'].pct_change().dropna()
                        volatility = returns.std() * np.sqrt(24)  # Volatilidad diaria
                        volatilities.append(volatility)
                        
                except Exception as e:
                    logger.warning(f"Error calculando volatilidad para {symbol}: {e}")
            
            if volatilities:
                market_volatility = np.mean(volatilities)
                self.market_factors['volatility_index'] = market_volatility
                return market_volatility
            
            return 0.02  # Default 2%
            
        except Exception as e:
            logger.error(f"Error calculando volatilidad de mercado: {e}")
            return 0.02

    def calculate_correlation_index(self):
        """Calcular índice de correlación entre activos"""
        try:
            returns_data = {}
            
            for symbol in self.symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='30d', interval='1d')
                    
                    if not hist.empty:
                        returns = hist['Close'].pct_change().dropna()
                        if len(returns) > 10:
                            returns_data[symbol] = returns
                            
                except Exception as e:
                    logger.warning(f"Error obteniendo retornos para {symbol}: {e}")
            
            if len(returns_data) >= 2:
                # Crear DataFrame de retornos
                returns_df = pd.DataFrame(returns_data)
                
                # Calcular matriz de correlación
                corr_matrix = returns_df.corr()
                
                # Calcular correlación promedio (excluyendo diagonal)
                mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
                avg_correlation = corr_matrix.where(mask).stack().mean()
                
                self.market_factors['correlation_index'] = avg_correlation
                return avg_correlation
            
            return 0.5  # Default
            
        except Exception as e:
            logger.error(f"Error calculando índice de correlación: {e}")
            return 0.5

    def analyze_news_sentiment(self):
        """Analizar sentimiento de noticias (simplificado)"""
        try:
            # Simulación de análisis de sentimiento
            # En implementación real, usaría APIs de noticias y NLP
            
            # Factores que afectan el sentimiento
            fgi = self.market_factors.get('fear_greed_index', 50)
            
            # Convertir FGI a sentimiento (-1 a 1)
            sentiment = (fgi - 50) / 50
            
            self.market_factors['news_sentiment'] = sentiment
            return sentiment
            
        except Exception as e:
            logger.error(f"Error analizando sentimiento: {e}")
            return 0

    def detect_market_regime(self):
        """Detectar régimen de mercado actual"""
        try:
            # Factores para determinar régimen
            fgi = self.market_factors.get('fear_greed_index', 50)
            volatility = self.market_factors.get('volatility_index', 0.02)
            correlation = self.market_factors.get('correlation_index', 0.5)
            sentiment = self.market_factors.get('news_sentiment', 0)
            
            # Clasificar régimen
            if fgi < 25 and volatility > 0.04:
                regime = 'crisis'
            elif fgi > 75 and correlation > 0.8:
                regime = 'euphoria'
            elif volatility < 0.015 and abs(sentiment) < 0.2:
                regime = 'stable'
            elif volatility > 0.03:
                regime = 'volatile'
            else:
                regime = 'normal'
            
            return regime
            
        except Exception as e:
            logger.error(f"Error detectando régimen de mercado: {e}")
            return 'normal'

    def generate_market_score(self):
        """Generar score general del mercado"""
        try:
            # Pesos para diferentes factores
            weights = {
                'fear_greed': 0.3,
                'volatility': 0.2,
                'sentiment': 0.2,
                'dominance': 0.15,
                'correlation': 0.15
            }
            
            # Normalizar factores a escala 0-100
            fgi_score = self.market_factors.get('fear_greed_index', 50)
            
            # Volatilidad (invertida - menos volatilidad = mejor score)
            vol = self.market_factors.get('volatility_index', 0.02)
            vol_score = max(0, 100 - (vol * 2500))  # Escalar volatilidad
            
            # Sentimiento (convertir de -1,1 a 0,100)
            sentiment = self.market_factors.get('news_sentiment', 0)
            sentiment_score = (sentiment + 1) * 50
            
            # Dominancia BTC (estabilidad cuando está entre 40-60%)
            dominance = self.market_factors.get('btc_dominance', 50)
            dominance_score = 100 - abs(dominance - 50) * 2
            
            # Correlación (menos correlación = mejor diversificación)
            correlation = self.market_factors.get('correlation_index', 0.5)
            correlation_score = (1 - correlation) * 100
            
            # Calcular score ponderado
            market_score = (
                fgi_score * weights['fear_greed'] +
                vol_score * weights['volatility'] +
                sentiment_score * weights['sentiment'] +
                dominance_score * weights['dominance'] +
                correlation_score * weights['correlation']
            )
            
            return max(0, min(100, market_score))
            
        except Exception as e:
            logger.error(f"Error generando score de mercado: {e}")
            return 50

    def check_alerts(self):
        """Verificar condiciones de alerta"""
        try:
            alerts = []
            
            # Alerta de volatilidad extrema
            volatility = self.market_factors.get('volatility_index', 0.02)
            if volatility > 0.05:
                alerts.append({
                    'type': 'HIGH_VOLATILITY',
                    'message': f'Volatilidad extrema detectada: {volatility:.1%}',
                    'severity': 'HIGH',
                    'timestamp': datetime.now()
                })
            
            # Alerta de miedo extremo
            fgi = self.market_factors.get('fear_greed_index', 50)
            if fgi < 20:
                alerts.append({
                    'type': 'EXTREME_FEAR',
                    'message': f'Miedo extremo en el mercado: FGI = {fgi}',
                    'severity': 'MEDIUM',
                    'timestamp': datetime.now()
                })
            elif fgi > 80:
                alerts.append({
                    'type': 'EXTREME_GREED',
                    'message': f'Codicia extrema en el mercado: FGI = {fgi}',
                    'severity': 'MEDIUM',
                    'timestamp': datetime.now()
                })
            
            # Alerta de correlación alta
            correlation = self.market_factors.get('correlation_index', 0.5)
            if correlation > 0.9:
                alerts.append({
                    'type': 'HIGH_CORRELATION',
                    'message': f'Correlación muy alta entre activos: {correlation:.2f}',
                    'severity': 'MEDIUM',
                    'timestamp': datetime.now()
                })
            
            # Agregar nuevas alertas
            self.alerts.extend(alerts)
            
            # Mantener solo las últimas 50 alertas
            self.alerts = self.alerts[-50:]
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error verificando alertas: {e}")
            return []

    def update_market_data(self):
        """Actualizar todos los datos de mercado"""
        try:
            logger.info("Actualizando datos de mercado...")
            
            # Obtener datos en paralelo
            tasks = [
                self.fetch_fear_greed_index,
                self.fetch_market_dominance,
                self.fetch_realtime_prices,
                self.calculate_market_volatility,
                self.calculate_correlation_index,
                self.analyze_news_sentiment
            ]
            
            for task in tasks:
                try:
                    task()
                except Exception as e:
                    logger.error(f"Error en tarea {task.__name__}: {e}")
            
            # Detectar régimen y generar score
            regime = self.detect_market_regime()
            market_score = self.generate_market_score()
            
            # Verificar alertas
            new_alerts = self.check_alerts()
            
            # Actualizar métricas
            self.external_factors = {
                'regime': regime,
                'market_score': market_score,
                'last_update': datetime.now(),
                'factors': self.market_factors.copy()
            }
            
            logger.info(f"Datos actualizados - Régimen: {regime}, Score: {market_score:.1f}")
            
            if new_alerts:
                logger.warning(f"Nuevas alertas: {len(new_alerts)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando datos de mercado: {e}")
            return False

    def start_monitoring(self):
        """Iniciar monitoreo en tiempo real"""
        try:
            if self.is_monitoring:
                logger.warning("El monitoreo ya está activo")
                return
            
            self.is_monitoring = True
            logger.info("Iniciando monitoreo en tiempo real...")
            
            def monitoring_loop():
                while self.is_monitoring:
                    try:
                        self.update_market_data()
                        time.sleep(self.update_interval)
                    except Exception as e:
                        logger.error(f"Error en loop de monitoreo: {e}")
                        time.sleep(self.update_interval)
            
            # Iniciar thread de monitoreo
            self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("Monitoreo iniciado exitosamente")
            
        except Exception as e:
            logger.error(f"Error iniciando monitoreo: {e}")
            self.is_monitoring = False

    def stop_monitoring(self):
        """Detener monitoreo"""
        try:
            self.is_monitoring = False
            logger.info("Monitoreo detenido")
            
        except Exception as e:
            logger.error(f"Error deteniendo monitoreo: {e}")

    def get_market_conditions(self):
        """Obtener condiciones actuales de mercado"""
        try:
            return {
                'external_factors': self.external_factors,
                'market_data': self.market_data,
                'alerts': self.alerts[-10:],  # Últimas 10 alertas
                'is_monitoring': self.is_monitoring
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo condiciones de mercado: {e}")
            return {}

    def generate_dashboard_data(self):
        """Generar datos para dashboard en tiempo real"""
        try:
            dashboard_data = {
                'timestamp': datetime.now().isoformat(),
                'market_score': self.external_factors.get('market_score', 50),
                'regime': self.external_factors.get('regime', 'normal'),
                'factors': self.market_factors.copy(),
                'prices': {},
                'alerts_count': len(self.alerts),
                'monitoring_status': self.is_monitoring
            }
            
            # Agregar precios actuales
            for symbol, data in self.market_data.items():
                if isinstance(data, dict) and 'price' in data:
                    dashboard_data['prices'][symbol] = {
                        'price': data['price'],
                        'change_percent': data.get('change_percent', 0)
                    }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error generando datos de dashboard: {e}")
            return {}

    def export_monitoring_data(self, filepath):
        """Exportar datos de monitoreo"""
        try:
            export_data = {
                'external_factors': self.external_factors,
                'market_factors': self.market_factors,
                'market_data': self.market_data,
                'alerts': self.alerts,
                'export_timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Datos de monitoreo exportados a: {filepath}")
            
        except Exception as e:
            logger.error(f"Error exportando datos: {e}")

def main():
    """Función de prueba"""
    try:
        # Crear sistema de monitoreo
        monitor = RealtimeMonitoringSystem(update_interval=30)
        
        # Actualizar datos una vez
        success = monitor.update_market_data()
        print(f"Actualización exitosa: {success}")
        
        # Mostrar condiciones de mercado
        conditions = monitor.get_market_conditions()
        print(f"Condiciones de mercado: {conditions}")
        
        # Generar datos de dashboard
        dashboard = monitor.generate_dashboard_data()
        print(f"Dashboard data: {dashboard}")
        
        print("Prueba de monitoreo en tiempo real completada")
        
    except Exception as e:
        print(f"Error en prueba: {e}")

if __name__ == "__main__":
    main()