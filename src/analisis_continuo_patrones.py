#!/usr/bin/env python3
"""
Sistema de Análisis Continuo de Patrones de Rompimiento con IA
Integración de Grok xAI y OpenAI para análisis inteligente
Actualización automática cada 60 segundos
"""

import time
import os
import sys
from datetime import datetime
import requests
import pandas as pd
import numpy as np
from colorama import init, Fore, Back, Style
import json
import io
from contextlib import redirect_stdout
import logging
from typing import Dict, List, Optional, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ Variables de entorno cargadas desde .env")
except ImportError:
    logger.warning("⚠️ python-dotenv no disponible, usando variables de entorno del sistema")

# Inicializar colorama para Windows
init(autoreset=True)

# Importar módulos de IA
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI no disponible")

# Configuración de APIs de IA
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_BASE_URL = os.getenv('GROK_BASE_URL', 'https://api.x.ai/v1')

class AnalisisContinuoPatrones:
    def __init__(self):
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        self.base_url = 'https://api.binance.com/api/v3'
        self.refresh_interval = 60  # 1 minuto
        self.iteration_count = 0
        self.log_file = "SICAR - ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO (1 minuto).txt"
        
        # Inicializar clientes de IA
        self.openai_client = None
        self.grok_client = None
        self.ai_enabled = False
        self._initialize_ai_clients()
        
        self.ensure_log_file()
        
    def ensure_log_file(self):
        """Asegurar que el archivo de log existe y crear encabezado si es nuevo"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("    SICAR - ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO CON IA    \n")
                f.write("="*80 + "\n")
                f.write(f"Archivo creado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("Integración: Grok xAI + OpenAI para análisis inteligente\n")
                f.write("="*80 + "\n\n")
    
    def _initialize_ai_clients(self):
        """Inicializar clientes de IA (OpenAI y Grok xAI)"""
        try:
            # Inicializar cliente OpenAI
            if OPENAI_AVAILABLE and OPENAI_API_KEY:
                self.openai_client = OpenAI(
                    api_key=OPENAI_API_KEY,
                    base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
                )
                logger.info("✅ Cliente OpenAI inicializado exitosamente")
            else:
                logger.warning("⚠️ OpenAI no disponible - falta API key o librería")
            
            # Inicializar cliente Grok xAI
            if OPENAI_AVAILABLE and GROK_API_KEY:
                self.grok_client = OpenAI(
                    api_key=GROK_API_KEY,
                    base_url=GROK_BASE_URL
                )
                logger.info("✅ Cliente Grok xAI inicializado exitosamente")
            else:
                logger.warning("⚠️ Grok xAI no disponible - falta API key")
            
            # Verificar si al menos uno está disponible
            self.ai_enabled = (self.openai_client is not None) or (self.grok_client is not None)
            
            if self.ai_enabled:
                logger.info("🧠 Sistema de IA habilitado para análisis inteligente")
            else:
                logger.warning("🔧 Sistema funcionará solo con análisis técnico tradicional")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando clientes de IA: {str(e)}")
            self.ai_enabled = False
    
    def save_analysis_to_file(self, content):
        """Guardar análisis en archivo"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                # Remover códigos de color ANSI para el archivo
                clean_content = self.remove_ansi_codes(content)
                f.write(clean_content)
                f.write("\n" + "="*80 + "\n\n")
                f.flush()
        except Exception as e:
            print(f"Error guardando en archivo: {e}")
    
    def remove_ansi_codes(self, text):
        """Remover códigos de color ANSI del texto"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def generate_ai_market_analysis(self, market_data: Dict[str, Any]) -> str:
        """Generar análisis inteligente del mercado usando IA"""
        if not self.ai_enabled:
            return "🔧 Análisis de IA no disponible - funcionando con análisis técnico tradicional"
        
        try:
            # Preparar contexto del mercado
            market_context = self._prepare_market_context(market_data)
            
            # Intentar análisis con Grok xAI primero (más especializado en tiempo real)
            if self.grok_client:
                grok_analysis = self._generate_grok_analysis(market_context)
                if grok_analysis:
                    return f"🧠 ANÁLISIS GROK xAI:\n{grok_analysis}"
            
            # Fallback a OpenAI si Grok no está disponible
            if self.openai_client:
                openai_analysis = self._generate_openai_analysis(market_context)
                if openai_analysis:
                    return f"🤖 ANÁLISIS OPENAI:\n{openai_analysis}"
            
            return "⚠️ Servicios de IA temporalmente no disponibles"
            
        except Exception as e:
            logger.error(f"Error en análisis de IA: {str(e)}")
            return f"❌ Error en análisis de IA: {str(e)}"
    
    def _prepare_market_context(self, market_data: Dict[str, Any]) -> str:
        """Preparar contexto del mercado para análisis de IA"""
        context_parts = []
        
        # Información general del mercado
        context_parts.append(f"📊 CONTEXTO DEL MERCADO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        context_parts.append(f"Símbolos analizados: {', '.join(self.symbols)}")
        
        # Datos por símbolo
        for symbol, data in market_data.items():
            if isinstance(data, dict):
                context_parts.append(f"\n{symbol}:")
                context_parts.append(f"  Precio: ${data.get('price', 'N/A')}")
                context_parts.append(f"  Resistencia: ${data.get('resistance', 'N/A')}")
                context_parts.append(f"  Soporte: ${data.get('support', 'N/A')}")
                context_parts.append(f"  RSI: {data.get('rsi', 'N/A')}")
                context_parts.append(f"  Volumen Ratio: {data.get('volume_ratio', 'N/A')}")
                context_parts.append(f"  Confianza: {data.get('confidence', 'N/A')}%")
                context_parts.append(f"  Patrones: {', '.join(data.get('patterns', []))}")
        
        # Resumen del mercado
        if 'market_summary' in market_data:
            summary = market_data['market_summary']
            context_parts.append(f"\n📈 RESUMEN DEL MERCADO:")
            context_parts.append(f"  Sentimiento: {summary.get('sentiment', 'N/A')}")
            context_parts.append(f"  Confianza promedio: {summary.get('avg_confidence', 'N/A')}%")
            context_parts.append(f"  Patrones activos: {summary.get('active_patterns', 'N/A')}")
            context_parts.append(f"  Símbolos destacados: {', '.join(summary.get('top_symbols', []))}")
        
        return "\n".join(context_parts)
    
    def _generate_grok_analysis(self, market_context: str) -> Optional[str]:
        """Generar análisis usando Grok xAI"""
        try:
            response = self.grok_client.chat.completions.create(
                model="grok-4-fast-reasoning",
                messages=[
                    {
                        "role": "system",
                        "content": """Eres Grok, un analista financiero experto especializado en criptomonedas y análisis técnico en tiempo real. 
                        Tu estilo es directo, perspicaz y ligeramente irreverente. Analiza los datos del mercado y proporciona:
                        
                        1. Interpretación inteligente de los patrones detectados
                        2. Análisis del sentimiento del mercado actual
                        3. Identificación de oportunidades y riesgos
                        4. Predicciones a corto plazo (próximos 60 minutos)
                        5. Recomendaciones de trading específicas
                        
                        Mantén tu respuesta concisa (máximo 200 palabras) pero informativa."""
                    },
                    {
                        "role": "user",
                        "content": f"Analiza este contexto del mercado de criptomonedas:\n\n{market_context}"
                    }
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error con Grok xAI: {str(e)}")
            return None
    
    def _generate_openai_analysis(self, market_context: str) -> Optional[str]:
        """Generar análisis usando OpenAI"""
        try:
            response = self.openai_client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                messages=[
                    {
                        "role": "system",
                        "content": """Eres un analista financiero experto especializado en análisis técnico de criptomonedas. 
                        Analiza los datos del mercado y proporciona:
                        
                        1. Interpretación profesional de los patrones técnicos
                        2. Evaluación del sentimiento del mercado
                        3. Análisis de riesgo/recompensa
                        4. Perspectivas para los próximos 60 minutos
                        5. Recomendaciones de gestión de riesgo
                        
                        Sé preciso, profesional y mantén tu análisis bajo 200 palabras."""
                    },
                    {
                        "role": "user",
                        "content": f"Analiza este contexto del mercado de criptomonedas:\n\n{market_context}"
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error con OpenAI: {str(e)}")
            return None
    
    def clear_screen(self):
        """Limpiar pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def get_klines(self, symbol, interval='1h', limit=100):
        """Obtener datos de velas de Binance"""
        try:
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir a tipos numéricos
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
                
            return df
            
        except Exception as e:
            print(f"Error obteniendo datos para {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df):
        """Calcular indicadores técnicos"""
        if df is None or len(df) < 20:
            return None
            
        # Medias móviles
        df['ma_20'] = df['close'].rolling(window=20).mean()
        df['ma_50'] = df['close'].rolling(window=50).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volumen promedio
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def detect_patterns(self, df, symbol):
        """Detectar patrones de rompimiento"""
        if df is None or len(df) < 50:
            return {
                'patterns': [],
                'confidence': 0,
                'current_price': 0,
                'resistance': 0,
                'support': 0
            }
        
        latest = df.iloc[-1]
        patterns = []
        confidence_factors = []
        
        # Precio actual
        current_price = latest['close']
        
        # Calcular soporte y resistencia
        recent_highs = df['high'].tail(20)
        recent_lows = df['low'].tail(20)
        resistance = recent_highs.max()
        support = recent_lows.min()
        
        # 1. Bollinger Bands Breakout
        if current_price > latest['bb_upper']:
            patterns.append('BB_Breakout_Upper')
            confidence_factors.append(15)
        elif current_price < latest['bb_lower']:
            patterns.append('BB_Breakout_Lower')
            confidence_factors.append(15)
        
        # 2. MA Crossover
        if latest['ma_20'] > latest['ma_50'] and df.iloc[-2]['ma_20'] <= df.iloc[-2]['ma_50']:
            patterns.append('MA_Golden_Cross')
            confidence_factors.append(20)
        elif latest['ma_20'] < latest['ma_50'] and df.iloc[-2]['ma_20'] >= df.iloc[-2]['ma_50']:
            patterns.append('MA_Death_Cross')
            confidence_factors.append(20)
        
        # 3. RSI Divergence
        if latest['rsi'] > 70:
            patterns.append('RSI_Overbought')
            confidence_factors.append(10)
        elif latest['rsi'] < 30:
            patterns.append('RSI_Oversold')
            confidence_factors.append(10)
        
        # 4. Volume Confirmation
        if latest['volume'] > latest['volume_ma'] * 1.5:
            patterns.append('Volume_Confirmation')
            confidence_factors.append(25)
        
        # 5. Resistance/Support Break
        if current_price > resistance * 1.001:  # 0.1% above resistance
            patterns.append('Resistance_Break')
            confidence_factors.append(30)
        elif current_price < support * 0.999:  # 0.1% below support
            patterns.append('Support_Break')
            confidence_factors.append(30)
        
        # Calcular confianza total
        total_confidence = min(sum(confidence_factors), 100)
        
        return {
            'patterns': patterns,
            'confidence': total_confidence,
            'current_price': current_price,
            'resistance': resistance,
            'support': support,
            'rsi': latest['rsi'],
            'volume_ratio': latest['volume'] / latest['volume_ma'] if latest['volume_ma'] > 0 else 1
        }
    
    def get_confidence_color(self, confidence):
        """Obtener color según nivel de confianza"""
        if confidence >= 70:
            return Fore.GREEN + Style.BRIGHT
        elif confidence >= 50:
            return Fore.YELLOW + Style.BRIGHT
        elif confidence >= 30:
            return Fore.CYAN
        else:
            return Fore.RED
    
    def get_pattern_emoji(self, pattern):
        """Obtener emoji para cada patrón"""
        emoji_map = {
            'BB_Breakout_Upper': '🚀',
            'BB_Breakout_Lower': '📉',
            'MA_Golden_Cross': '✨',
            'MA_Death_Cross': '💀',
            'RSI_Overbought': '🔥',
            'RSI_Oversold': '❄️',
            'Volume_Confirmation': '📊',
            'Resistance_Break': '⬆️',
            'Support_Break': '⬇️'
        }
        return emoji_map.get(pattern, '📈')
    
    def print_header(self):
        """Imprimir encabezado del análisis"""
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.WHITE}{Back.BLUE}{Style.BRIGHT}    SICAR - ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO    ")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.YELLOW}Iteración: {self.iteration_count} | Actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.YELLOW}Próxima actualización en: {self.refresh_interval} segundos")
        print(f"{Fore.CYAN}{'='*80}")
    
    def print_symbol_analysis(self, symbol, analysis):
        """Imprimir análisis de un símbolo"""
        confidence = analysis['confidence']
        color = self.get_confidence_color(confidence)
        
        print(f"\n{Fore.WHITE}{Style.BRIGHT}📊 {symbol}")
        print(f"{Fore.CYAN}{'─'*50}")
        
        # Información básica
        print(f"{Fore.WHITE}Precio Actual: {color}${analysis['current_price']:.4f}")
        print(f"{Fore.WHITE}Resistencia:   {Fore.RED}${analysis['resistance']:.4f}")
        print(f"{Fore.WHITE}Soporte:       {Fore.GREEN}${analysis['support']:.4f}")
        print(f"{Fore.WHITE}RSI:           {Fore.YELLOW}{analysis['rsi']:.1f}")
        print(f"{Fore.WHITE}Vol. Ratio:    {Fore.MAGENTA}{analysis['volume_ratio']:.2f}x")
        
        # Confianza
        confidence_level = "ALTA" if confidence >= 70 else "MEDIA" if confidence >= 50 else "BAJA"
        print(f"{Fore.WHITE}Confianza:     {color}{confidence:.1f}% ({confidence_level})")
        
        # Patrones detectados
        if analysis['patterns']:
            print(f"{Fore.WHITE}Patrones:")
            for pattern in analysis['patterns']:
                emoji = self.get_pattern_emoji(pattern)
                pattern_name = pattern.replace('_', ' ').title()
                print(f"  {emoji} {Fore.CYAN}{pattern_name}")
        else:
            print(f"{Fore.WHITE}{Style.DIM}Sin patrones detectados")
    
    def generate_analysis_text(self, all_analysis):
        """Generar texto completo del análisis para guardar en archivo"""
        output = []
        
        # Encabezado
        output.append("="*80)
        output.append("    SICAR - ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO    ")
        output.append("="*80)
        output.append(f"Iteración: {self.iteration_count} | Actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"Próxima actualización en: {self.refresh_interval} segundos")
        output.append("="*80)
        
        # Análisis por símbolo
        for symbol in self.symbols:
            if symbol in all_analysis:
                analysis = all_analysis[symbol]
                confidence = analysis['confidence']
                
                output.append(f"\n📊 {symbol}")
                output.append("─"*50)
                output.append(f"Precio Actual: ${analysis['current_price']:.4f}")
                output.append(f"Resistencia:   ${analysis['resistance']:.4f}")
                output.append(f"Soporte:       ${analysis['support']:.4f}")
                output.append(f"RSI:           {analysis['rsi']:.1f}")
                output.append(f"Vol. Ratio:    {analysis['volume_ratio']:.2f}x")
                
                confidence_level = "ALTA" if confidence >= 70 else "MEDIA" if confidence >= 50 else "BAJA"
                output.append(f"Confianza:     {confidence:.1f}% ({confidence_level})")
                
                if analysis['patterns']:
                    output.append("Patrones:")
                    for pattern in analysis['patterns']:
                        emoji = self.get_pattern_emoji(pattern)
                        pattern_name = pattern.replace('_', ' ').title()
                        output.append(f"  {emoji} {pattern_name}")
                else:
                    output.append("Sin patrones detectados")
        
        # Resumen del mercado
        output.append("\n" + "="*80)
        output.append("                    RESUMEN DEL MERCADO                    ")
        output.append("="*80)
        
        confidences = [analysis['confidence'] for analysis in all_analysis.values()]
        avg_confidence = np.mean(confidences) if confidences else 0
        total_patterns = sum(len(analysis['patterns']) for analysis in all_analysis.values())
        
        high_conf_count = sum(1 for conf in confidences if conf >= 70)
        if high_conf_count >= 3:
            sentiment = "ALCISTA"
        elif high_conf_count >= 1:
            sentiment = "NEUTRAL"
        else:
            sentiment = "BAJISTA"
        
        output.append(f"Sentimiento General: {sentiment}")
        output.append(f"Confianza Promedio:  {avg_confidence:.1f}%")
        output.append(f"Patrones Activos:    {total_patterns}")
        
        # Top 3 símbolos
        sorted_symbols = sorted(all_analysis.items(), key=lambda x: x[1]['confidence'], reverse=True)
        output.append("\n🏆 TOP 3 SÍMBOLOS POR CONFIANZA:")
        for i, (symbol, analysis) in enumerate(sorted_symbols[:3], 1):
            output.append(f"  {i}. {symbol}: {analysis['confidence']:.1f}%")
        
        # Alertas importantes
        alerts = []
        for symbol, analysis in all_analysis.items():
            if analysis['confidence'] >= 75:
                alerts.append(f"{symbol}: Confianza muy alta ({analysis['confidence']:.1f}%)")
            if 'Volume_Confirmation' in analysis['patterns'] and analysis['volume_ratio'] > 2:
                alerts.append(f"{symbol}: Volumen excepcional ({analysis['volume_ratio']:.1f}x)")
        
        if alerts:
            output.append("\n🚨 ALERTAS IMPORTANTES:")
            for alert in alerts:
                output.append(f"  • {alert}")
        
        # Análisis de IA
        if self.ai_enabled:
            output.append("\n" + "="*80)
            output.append("                    ANÁLISIS INTELIGENTE                    ")
            output.append("="*80)
            
            # Preparar datos para IA
            market_data = {}
            for symbol, analysis in all_analysis.items():
                market_data[symbol] = {
                    'price': analysis['current_price'],
                    'resistance': analysis['resistance'],
                    'support': analysis['support'],
                    'rsi': analysis['rsi'],
                    'volume_ratio': analysis['volume_ratio'],
                    'confidence': analysis['confidence'],
                    'patterns': analysis['patterns']
                }
            
            market_data['market_summary'] = {
                'sentiment': sentiment,
                'avg_confidence': avg_confidence,
                'active_patterns': total_patterns,
                'top_symbols': [symbol for symbol, _ in sorted_symbols[:3]]
            }
            
            # Generar análisis de IA
            ai_analysis = self.generate_ai_market_analysis(market_data)
            output.append(ai_analysis)
        else:
            output.append("\n🔧 Análisis de IA no disponible - funcionando con análisis técnico tradicional")
        
        return "\n".join(output)
    
    def print_market_summary(self, all_analysis):
        """Imprimir resumen del mercado"""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.WHITE}{Back.GREEN}{Style.BRIGHT}                    RESUMEN DEL MERCADO                    ")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        
        # Calcular estadísticas generales
        confidences = [analysis['confidence'] for analysis in all_analysis.values()]
        avg_confidence = np.mean(confidences) if confidences else 0
        
        total_patterns = sum(len(analysis['patterns']) for analysis in all_analysis.values())
        
        # Determinar sentimiento general
        high_conf_count = sum(1 for conf in confidences if conf >= 70)
        if high_conf_count >= 3:
            sentiment = "ALCISTA"
            sentiment_color = Fore.GREEN
        elif high_conf_count >= 1:
            sentiment = "NEUTRAL"
            sentiment_color = Fore.YELLOW
        else:
            sentiment = "BAJISTA"
            sentiment_color = Fore.RED
        
        print(f"{Fore.WHITE}Sentimiento General: {sentiment_color}{Style.BRIGHT}{sentiment}")
        print(f"{Fore.WHITE}Confianza Promedio:  {self.get_confidence_color(avg_confidence)}{avg_confidence:.1f}%")
        print(f"{Fore.WHITE}Patrones Activos:    {Fore.CYAN}{total_patterns}")
        
        # Top 3 símbolos por confianza
        sorted_symbols = sorted(all_analysis.items(), key=lambda x: x[1]['confidence'], reverse=True)
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}🏆 TOP 3 SÍMBOLOS POR CONFIANZA:")
        for i, (symbol, analysis) in enumerate(sorted_symbols[:3], 1):
            color = self.get_confidence_color(analysis['confidence'])
            print(f"  {i}. {symbol}: {color}{analysis['confidence']:.1f}%")
        
        # Alertas importantes
        alerts = []
        for symbol, analysis in all_analysis.items():
            if analysis['confidence'] >= 75:
                alerts.append(f"{symbol}: Confianza muy alta ({analysis['confidence']:.1f}%)")
            if 'Volume_Confirmation' in analysis['patterns'] and analysis['volume_ratio'] > 2:
                alerts.append(f"{symbol}: Volumen excepcional ({analysis['volume_ratio']:.1f}x)")
        
        if alerts:
            print(f"\n{Fore.RED}{Style.BRIGHT}🚨 ALERTAS IMPORTANTES:")
            for alert in alerts:
                print(f"  • {alert}")
    
    def print_ai_analysis(self, all_analysis):
        """Mostrar análisis de IA en pantalla"""
        print(f"\n{Fore.MAGENTA}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.WHITE}{Back.MAGENTA}{Style.BRIGHT}                    ANÁLISIS INTELIGENTE                    ")
        print(f"{Fore.MAGENTA}{Style.BRIGHT}{'='*80}")
        
        # Preparar datos para IA
        market_data = {}
        for symbol, analysis in all_analysis.items():
            market_data[symbol] = {
                'price': analysis['current_price'],
                'resistance': analysis['resistance'],
                'support': analysis['support'],
                'rsi': analysis['rsi'],
                'volume_ratio': analysis['volume_ratio'],
                'confidence': analysis['confidence'],
                'patterns': analysis['patterns']
            }
        
        # Calcular estadísticas para el resumen
        confidences = [analysis['confidence'] for analysis in all_analysis.values()]
        avg_confidence = np.mean(confidences) if confidences else 0
        total_patterns = sum(len(analysis['patterns']) for analysis in all_analysis.values())
        
        # Determinar sentimiento
        high_conf_count = sum(1 for conf in confidences if conf >= 70)
        if high_conf_count >= 3:
            sentiment = "ALCISTA"
        elif high_conf_count >= 1:
            sentiment = "NEUTRAL"
        else:
            sentiment = "BAJISTA"
        
        sorted_symbols = sorted(all_analysis.items(), key=lambda x: x[1]['confidence'], reverse=True)
        
        market_data['market_summary'] = {
            'sentiment': sentiment,
            'avg_confidence': avg_confidence,
            'active_patterns': total_patterns,
            'top_symbols': [symbol for symbol, _ in sorted_symbols[:3]]
        }
        
        # Generar y mostrar análisis de IA
        ai_analysis = self.generate_ai_market_analysis(market_data)
        
        # Colorear el análisis según el tipo de IA
        if "GROK xAI" in ai_analysis:
            print(f"{Fore.CYAN}{Style.BRIGHT}{ai_analysis}")
        elif "OPENAI" in ai_analysis:
            print(f"{Fore.GREEN}{Style.BRIGHT}{ai_analysis}")
        else:
            print(f"{Fore.YELLOW}{ai_analysis}")
    
    def run_analysis(self):
        """Ejecutar análisis completo"""
        all_analysis = {}
        
        for symbol in self.symbols:
            print(f"{Fore.WHITE}{Style.DIM}Analizando {symbol}...", end='\r')
            
            # Obtener datos
            df = self.get_klines(symbol)
            if df is None:
                continue
                
            # Calcular indicadores
            df = self.calculate_indicators(df)
            if df is None:
                continue
                
            # Detectar patrones
            analysis = self.detect_patterns(df, symbol)
            all_analysis[symbol] = analysis
        
        return all_analysis
    
    def run_continuous(self):
        """Ejecutar análisis continuo"""
        print(f"{Fore.GREEN}{Style.BRIGHT}🚀 Iniciando análisis continuo de patrones...")
        print(f"{Fore.YELLOW}Presiona Ctrl+C para detener")
        time.sleep(2)
        
        try:
            while True:
                self.iteration_count += 1
                
                # Limpiar pantalla
                self.clear_screen()
                
                # Imprimir encabezado
                self.print_header()
                
                # Ejecutar análisis
                all_analysis = self.run_analysis()
                
                if all_analysis:
                    # Generar texto completo para archivo
                    analysis_text = self.generate_analysis_text(all_analysis)
                    
                    # Guardar en archivo
                    self.save_analysis_to_file(analysis_text)
                    
                    # Mostrar análisis por símbolo
                    for symbol in self.symbols:
                        if symbol in all_analysis:
                            self.print_symbol_analysis(symbol, all_analysis[symbol])
                    
                    # Mostrar resumen del mercado
                    self.print_market_summary(all_analysis)
                    
                    # Mostrar análisis de IA
                    if self.ai_enabled:
                        self.print_ai_analysis(all_analysis)
                    else:
                        print(f"\n{Fore.YELLOW}🔧 Análisis de IA no disponible - funcionando con análisis técnico tradicional")
                    
                    # Confirmar guardado
                    print(f"\n{Fore.GREEN}✅ Análisis guardado en: {self.log_file}")
                else:
                    print(f"{Fore.RED}❌ No se pudieron obtener datos del mercado")
                
                # Countdown para próxima actualización
                print(f"\n{Fore.CYAN}{'='*80}")
                print(f"{Fore.YELLOW}Esperando {self.refresh_interval} segundos para próxima actualización...")
                
                # Esperar con countdown
                for remaining in range(self.refresh_interval, 0, -1):
                    print(f"\r{Fore.WHITE}{Style.DIM}Próxima actualización en: {remaining:02d} segundos", end='', flush=True)
                    time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n\n{Fore.GREEN}{Style.BRIGHT}✅ Análisis continuo detenido por el usuario")
            print(f"{Fore.YELLOW}Total de iteraciones ejecutadas: {self.iteration_count}")
            sys.exit(0)
        except Exception as e:
            print(f"\n\n{Fore.RED}❌ Error en análisis continuo: {e}")
            sys.exit(1)

def main():
    """Función principal"""
    analyzer = AnalisisContinuoPatrones()
    analyzer.run_continuous()

if __name__ == "__main__":
    main()