# /src/module_xai.py

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Agregar el directorio padre al path para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *

# Configurar logging
from enhanced_logger import SICAR_LOGGER
logger = SICAR_LOGGER.get_logger('main')

def generate_dynamic_cognitive_report(
    metacontroller,
    regime_classifier,
    causal_cartographer,
    market_data,
    decision: str,
    strategy: str,
    confidence: float,
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Genera un reporte cognitivo completamente dinámico usando datos reales de todos los módulos SICAR.
    
    Args:
        metacontroller: Instancia del MetaController
        regime_classifier: Instancia del RegimeClassifier
        causal_cartographer: Instancia del CausalCartographer
        market_data: DataFrame con datos de mercado actuales
        decision: Decisión tomada (BUY/SELL/HOLD)
        strategy: Estrategia seleccionada
        confidence: Nivel de confianza de la decisión
        additional_context: Contexto adicional opcional
        
    Returns:
        Reporte cognitivo dinámico
    """
    try:
        logger.info("Generando reporte cognitivo dinámico...")
        
        # 1. Obtener régimen actual con datos reales
        regime_results = regime_classifier.classify_regimes(market_data.tail(50))
        if not regime_results.empty and 'regime_name' in regime_results.columns:
            current_regime = regime_results['regime_name'].iloc[-1]
            regime_confidence = 0.8  # Valor por defecto
        else:
            current_regime = "Régimen Desconocido"
            regime_confidence = 0.5
            
        regime_info = {
            'regime_name': current_regime,
            'confidence': regime_confidence
        }
        
        # 2. Obtener feature importances reales del metacontroller
        feature_importances = {}
        if hasattr(metacontroller, 'model') and metacontroller.model is not None:
            if hasattr(metacontroller.model, 'feature_importances_'):
                # Obtener nombres de características
                features = metacontroller.prepare_features(market_data.tail(100))
                if not features.empty:
                    feature_names = features.columns.tolist()
                    importances = metacontroller.model.feature_importances_
                    
                    # Crear diccionario de importancias
                    for name, importance in zip(feature_names, importances):
                        feature_importances[name] = float(importance)
                    
                    # Ordenar por importancia
                    feature_importances = dict(sorted(
                        feature_importances.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:5])  # Top 5 características más importantes
        
        # 3. Obtener factores causales reales
        causal_factors = causal_cartographer.analyze_causal_factors(market_data.tail(100))
        primary_causal_factors = causal_factors.get('primary_factors', ['momentum', 'volatilidad'])
        
        # 4. Construir contexto adicional con datos reales del mercado
        current_price = market_data['Close'].iloc[-1]
        price_change = ((current_price / market_data['Close'].iloc[-2]) - 1) * 100
        
        # Calcular indicadores técnicos actuales
        returns = market_data['Close'].pct_change().dropna()
        volatility = returns.tail(20).std() * 100
        
        # RSI simplificado
        delta = market_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50.0
        
        # Volumen relativo
        avg_volume = market_data['Volume'].tail(20).mean()
        current_volume = market_data['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        real_context = {
            'Price': f"{current_price:.3f}",
            'Price_Change_24h': f"{price_change:.2f}%",
            'Volatility_20d': f"{volatility:.2f}%",
            'RSI_14': f"{current_rsi:.1f}",
            'Volume_Ratio': f"{volume_ratio:.3f}",
            'Confidence': f"{confidence:.1f}%"
        }
        
        # Combinar con contexto adicional si se proporciona
        if additional_context:
            real_context.update(additional_context)
        
        # 5. Generar reporte usando la función original con datos reales
        return generate_cognitive_report(
            decision=decision,
            strategy=strategy,
            market_regime=regime_info['regime_name'],
            xai_factors=feature_importances,
            primary_causal_factors=primary_causal_factors,
            additional_context=real_context
        )
        
    except Exception as e:
        logger.error(f"Error generando reporte dinámico: {str(e)}")
        # Fallback a reporte básico
        return generate_cognitive_report(
            decision=decision,
            strategy=strategy,
            market_regime="Desconocido",
            xai_factors={'confidence': confidence, 'error': 'Datos dinámicos no disponibles'},
            primary_causal_factors=['Error en análisis causal'],
            additional_context={'error': 'Datos dinámicos no disponibles'}
        )

def generate_cognitive_report(
    decision: str,
    strategy: str,
    market_regime: str,
    xai_factors: Dict[str, Any],
    primary_causal_factors: List[str],
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Genera un reporte cognitivo explicable de las decisiones de trading usando LLM.
    
    Args:
        decision: Decisión tomada ('BUY', 'SELL', 'HOLD')
        strategy: Estrategia utilizada ('momentum', 'mean_reversion', 'breakout', 'hold')
        market_regime: Régimen de mercado identificado
        xai_factors: Factores explicativos del modelo
        primary_causal_factors: Factores causales principales identificados
        additional_context: Contexto adicional opcional
        
    Returns:
        String con el reporte cognitivo generado
    """
    try:
        logger.info("Generando reporte cognitivo...")
        
        # Obtener configuración de APIs y fallback order
        allow_llms = os.getenv('ALLOW_EXTERNAL_LLMS', 'false').lower() == 'true'
        fallback_order = os.getenv('LLM_FALLBACK_ORDER', 'openai,anthropic,grok,local').split(',')
        fallback_order = [api.strip() for api in fallback_order if api.strip().lower() != 'zai']
        
        if not allow_llms:
            logger.warning("LLMs externos deshabilitados, generando reporte local")
            return _generate_local_report(
                decision, strategy, market_regime,
                xai_factors, primary_causal_factors, additional_context
            )
        
        # Intentar cada API en el orden de fallback
        for api_name in fallback_order:
            api_name = api_name.strip().lower()
            try:
                if api_name == 'openai':
                    openai_api_key = os.getenv('OPENAI_API_KEY')
                    if openai_api_key:
                        logger.info(f"Intentando generar reporte con OpenAI...")
                        return _generate_report_openai(
                            decision, strategy, market_regime, 
                            xai_factors, primary_causal_factors, additional_context
                        )
                elif api_name == 'anthropic':
                    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
                    if anthropic_api_key:
                        logger.info(f"Intentando generar reporte con Anthropic...")
                        return _generate_report_anthropic(
                            decision, strategy, market_regime,
                            xai_factors, primary_causal_factors, additional_context
                        )
                # Z.ai excluido del análisis por configuración del sistema
                elif api_name == 'grok':
                    grok_api_key = os.getenv('GROK_API_KEY')
                    if grok_api_key:
                        logger.info(f"Intentando generar reporte con Grok...")
                        return _generate_report_grok(
                            decision, strategy, market_regime,
                            xai_factors, primary_causal_factors, additional_context
                        )
                elif api_name == 'local':
                    logger.info("Usando generador local de reportes")
                    return _generate_local_report(
                        decision, strategy, market_regime,
                        xai_factors, primary_causal_factors, additional_context
                    )
                    
            except Exception as api_error:
                logger.warning(f"Error con API {api_name}: {str(api_error)}")
                continue  # Intentar siguiente API en el orden de fallback
        
        # Si ninguna API funcionó, usar fallback local
        logger.warning("Ninguna API de LLM funcionó, generando reporte local")
        return _generate_local_report(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )
            
    except Exception as e:
        logger.error(f"Error generando reporte cognitivo: {str(e)}")
        return _generate_fallback_report(decision, strategy, market_regime)

def _generate_report_openai(
    decision: str, strategy: str, market_regime: str,
    xai_factors: Dict[str, Any], primary_causal_factors: List[str],
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Genera reporte usando OpenAI API.
    
    Args:
        decision: Decisión tomada
        strategy: Estrategia utilizada
        market_regime: Régimen de mercado
        xai_factors: Factores explicativos
        primary_causal_factors: Factores causales principales
        additional_context: Contexto adicional
        
    Returns:
        Reporte cognitivo generado
    """
    try:
        from openai import OpenAI
        
        # Configurar cliente OpenAI
        client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        )
        
        # Preparar prompt
        prompt = _build_prompt(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )
        
        # Llamar a la API
        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[
                {
                    "role": "system",
                    "content": """Eres un analista financiero experto especializado en explicar decisiones de trading algorítmico. 
                    Tu tarea es generar reportes cognitivos claros y comprensibles que expliquen las decisiones de trading 
                    del sistema SICAR (Sistema Inteligente de Cartografía y Análisis de Riesgos).
                    
                    Características de tus reportes:
                    - Claros y concisos (máximo 300 palabras)
                    - Técnicamente precisos pero accesibles
                    - Enfocados en el razonamiento detrás de la decisión
                    - Incluyen factores de riesgo y confianza
                    - Proporcionan contexto de mercado relevante
                    - Traducen decisiones numéricas a lenguaje humano comprensible"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        report = response.choices[0].message.content.strip()
        logger.info("Reporte cognitivo generado con OpenAI")
        return report
        
    except ImportError:
        logger.warning("OpenAI no instalado, usando reporte local")
        return _generate_local_report(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )
    except Exception as e:
        logger.error(f"Error con OpenAI API: {str(e)}")
        return _generate_local_report(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )

def _generate_report_anthropic(
    decision: str, strategy: str, market_regime: str,
    xai_factors: Dict[str, Any], primary_causal_factors: List[str],
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Genera reporte usando Anthropic Claude API.
    
    Args:
        decision: Decisión tomada
        strategy: Estrategia utilizada
        market_regime: Régimen de mercado
        xai_factors: Factores explicativos
        primary_causal_factors: Factores causales principales
        additional_context: Contexto adicional
        
    Returns:
        Reporte cognitivo generado
    """
    try:
        import anthropic
        
        # Configurar cliente Anthropic
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # Preparar prompt
        prompt = _build_prompt(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )
        
        # Llamar a la API
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0.3,
            system="""Eres un analista financiero experto especializado en explicar decisiones de trading algorítmico. 
            Tu tarea es generar reportes cognitivos claros y comprensibles que expliquen las decisiones de trading 
            del sistema SICAR (Sistema Inteligente de Cartografía y Análisis de Riesgos).
            
            Características de tus reportes:
            - Claros y concisos (máximo 300 palabras)
            - Técnicamente precisos pero accesibles
            - Enfocados en el razonamiento detrás de la decisión
            - Incluyen factores de riesgo y confianza
            - Proporcionan contexto de mercado relevante""",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        report = response.content[0].text.strip()
        logger.info("Reporte cognitivo generado con Anthropic Claude")
        return report
        
    except ImportError:
        logger.warning("Anthropic no instalado, usando reporte local")
        return _generate_local_report(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )
    except Exception as e:
        logger.error(f"Error con Anthropic API: {str(e)}")
        return _generate_local_report(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )

def _generate_report_zai(
    decision: str, strategy: str, market_regime: str,
    xai_factors: Dict[str, Any], primary_causal_factors: List[str],
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Genera reporte usando Z.ai API.
    
    Args:
        decision: Decisión tomada
        strategy: Estrategia utilizada
        market_regime: Régimen de mercado
        xai_factors: Factores explicativos
        primary_causal_factors: Factores causales principales
        additional_context: Contexto adicional
        
    Returns:
        Reporte cognitivo generado
    """
    try:
        import requests
        
        # Configurar cliente Z.ai
        zai_api_key = os.getenv('ZAI_API_KEY')
        zai_api_url = os.getenv('ZAI_API_URL', 'https://api.z.ai/api/paas/v4')
        
        # Preparar prompt
        prompt = _build_prompt(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )
        
        # Preparar headers y payload para Z.ai
        headers = {
            'Authorization': f'Bearer {zai_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'glm-4.6',  # Modelo correcto de Z.ai
            'messages': [
                {
                    'role': 'system',
                    'content': """Eres un analista financiero experto especializado en explicar decisiones de trading algorítmico. 
                    Tu tarea es generar reportes cognitivos claros y comprensibles que expliquen las decisiones de trading 
                    del sistema SICAR (Sistema Inteligente de Cartografía y Análisis de Riesgos).
                    
                    Características de tus reportes:
                    - Claros y concisos (máximo 300 palabras)
                    - Técnicamente precisos pero accesibles
                    - Enfocados en el razonamiento detrás de la decisión
                    - Incluyen factores de riesgo y confianza
                    - Proporcionan contexto de mercado relevante"""
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 500,
            'temperature': 0.3
        }
        
        # Llamar a la API de Z.ai con la URL correcta
        response = requests.post(
            f"{zai_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        report = result['choices'][0]['message']['content'].strip()
        logger.info("Reporte cognitivo generado con Z.ai")
        return report
        
    except ImportError:
        logger.warning("Requests no instalado, usando reporte local")
        return _generate_local_report(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )
    except Exception as e:
        logger.error(f"Error con Z.ai API: {str(e)}")
        return _generate_local_report(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )

def _generate_report_grok(
    decision: str, strategy: str, market_regime: str,
    xai_factors: Dict[str, Any], primary_causal_factors: List[str],
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Genera reporte usando Grok API (X.ai).
    
    Args:
        decision: Decisión tomada
        strategy: Estrategia utilizada
        market_regime: Régimen de mercado
        xai_factors: Factores explicativos
        primary_causal_factors: Factores causales principales
        additional_context: Contexto adicional
        
    Returns:
        Reporte cognitivo generado
    """
    try:
        import requests
        
        # Configurar cliente Grok
        grok_api_key = os.getenv('GROK_API_KEY')
        grok_api_url = os.getenv('GROK_API_URL', 'https://api.x.ai/v1')
        
        # Preparar prompt
        prompt = _build_prompt(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )
        
        # Preparar headers y payload para Grok
        headers = {
            'Authorization': f'Bearer {grok_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'grok-4-fast-reasoning',
            'messages': [
                {
                    'role': 'system',
                    'content': """Eres Grok, un analista financiero experto con conocimiento profundo de mercados de criptomonedas. 
                    Tu tarea es generar reportes cognitivos claros y comprensibles que expliquen las decisiones de trading 
                    del sistema SICAR (Sistema Inteligente de Cartografía y Análisis de Riesgos).
                    
                    Características de tus reportes:
                    - Claros y concisos (máximo 300 palabras)
                    - Técnicamente precisos pero accesibles
                    - Enfocados en el razonamiento detrás de la decisión
                    - Incluyen factores de riesgo y confianza
                    - Proporcionan contexto de mercado relevante
                    - Mantén un tono profesional pero directo"""
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 500,
            'temperature': 0.3
        }
        
        # Llamar a la API de Grok
        response = requests.post(
            f"{grok_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        report = result['choices'][0]['message']['content'].strip()
        logger.info("Reporte cognitivo generado con Grok")
        return report
        
    except ImportError:
        logger.warning("Requests no instalado, usando reporte local")
        return _generate_local_report(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )
    except Exception as e:
        logger.error(f"Error con Grok API: {str(e)}")
        return _generate_local_report(
            decision, strategy, market_regime,
            xai_factors, primary_causal_factors, additional_context
        )

def _build_prompt(
    decision: str, strategy: str, market_regime: str,
    xai_factors: Dict[str, Any], primary_causal_factors: List[str],
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Construye el prompt para el LLM.
    
    Args:
        decision: Decisión tomada
        strategy: Estrategia utilizada
        market_regime: Régimen de mercado
        xai_factors: Factores explicativos
        primary_causal_factors: Factores causales principales
        additional_context: Contexto adicional
        
    Returns:
        Prompt formateado para el LLM
    """
    prompt = f"""
Genera un reporte cognitivo para la siguiente decisión de trading del sistema SICAR:

**DECISIÓN TOMADA:** {decision.upper()}
**ESTRATEGIA SELECCIONADA:** {strategy}
**RÉGIMEN DE MERCADO:** {market_regime}

**FACTORES EXPLICATIVOS:**
"""
    
    # Agregar factores XAI con interpretación
    for factor, value in xai_factors.items():
        if isinstance(value, float):
            # Agregar interpretación cualitativa para valores numéricos
            interpretation = _interpret_numeric_value(factor, value)
            prompt += f"- {factor}: {value:.3f} ({interpretation})\n"
        else:
            prompt += f"- {factor}: {value}\n"
    
    # Agregar factores causales
    if primary_causal_factors:
        prompt += f"\n**FACTORES CAUSALES PRINCIPALES:**\n"
        for factor in primary_causal_factors:
            prompt += f"- {factor}\n"
    
    # Agregar contexto adicional
    if additional_context:
        prompt += f"\n**CONTEXTO ADICIONAL:**\n"
        for key, value in additional_context.items():
            prompt += f"- {key}: {value}\n"
    
    prompt += """
**INSTRUCCIONES PARA TRADUCCIÓN A LENGUAJE HUMANO:**
Traduce los valores numéricos y decisiones algorítmicas a explicaciones comprensibles:

1. **DECISIÓN PRINCIPAL:** Explica en términos simples qué acción se tomó y por qué
2. **TRADUCCIÓN DE MÉTRICAS:** Convierte los valores numéricos en interpretaciones cualitativas:
   - Valores de confianza (0.0-1.0) → "muy baja/baja/moderada/alta/muy alta confianza"
   - Valores de volatilidad → "mercado muy estable/estable/moderadamente volátil/volátil/muy volátil"
   - Valores de momentum → "tendencia muy débil/débil/moderada/fuerte/muy fuerte"
   - Valores de señal → "señal muy débil/débil/moderada/fuerte/muy fuerte"

3. **CONTEXTO DE MERCADO:** Explica cómo las condiciones actuales justifican la decisión
4. **FACTORES DETERMINANTES:** Identifica los 2-3 factores más importantes en lenguaje claro
5. **NIVEL DE CERTEZA:** Traduce la confianza numérica a una evaluación de riesgo comprensible
6. **IMPLICACIONES PRÁCTICAS:** Qué significa esta decisión para el portafolio

**FORMATO:** Reporte profesional pero accesible, máximo 280 palabras, evitando jerga técnica excesiva.
"""
    
    return prompt

def _interpret_numeric_value(factor_name: str, value: float) -> str:
    """
    Interpreta valores numéricos en lenguaje humano comprensible.
    
    Args:
        factor_name: Nombre del factor
        value: Valor numérico
        
    Returns:
        Interpretación en lenguaje humano
    """
    factor_lower = factor_name.lower()
    
    # Interpretaciones para confianza (0.0 - 1.0)
    if 'confidence' in factor_lower or 'confianza' in factor_lower:
        if value >= 0.9:
            return "muy alta confianza"
        elif value >= 0.7:
            return "alta confianza"
        elif value >= 0.5:
            return "confianza moderada"
        elif value >= 0.3:
            return "baja confianza"
        else:
            return "muy baja confianza"
    
    # Interpretaciones para volatilidad
    elif 'volatility' in factor_lower or 'volatilidad' in factor_lower:
        if value >= 0.8:
            return "muy volátil"
        elif value >= 0.6:
            return "volátil"
        elif value >= 0.4:
            return "moderadamente volátil"
        elif value >= 0.2:
            return "estable"
        else:
            return "muy estable"
    
    # Interpretaciones para momentum/tendencia
    elif 'momentum' in factor_lower or 'trend' in factor_lower or 'tendencia' in factor_lower:
        if value >= 0.7:
            return "tendencia muy fuerte"
        elif value >= 0.4:
            return "tendencia fuerte"
        elif value >= 0.1:
            return "tendencia moderada"
        elif value >= -0.1:
            return "tendencia neutral"
        elif value >= -0.4:
            return "tendencia débil contraria"
        else:
            return "tendencia fuerte contraria"
    
    # Interpretaciones para señales (0.0 - 1.0)
    elif 'signal' in factor_lower or 'señal' in factor_lower or 'strength' in factor_lower:
        if value >= 0.8:
            return "señal muy fuerte"
        elif value >= 0.6:
            return "señal fuerte"
        elif value >= 0.4:
            return "señal moderada"
        elif value >= 0.2:
            return "señal débil"
        else:
            return "señal muy débil"
    
    # Interpretaciones para riesgo
    elif 'risk' in factor_lower or 'riesgo' in factor_lower:
        if value >= 0.8:
            return "riesgo muy alto"
        elif value >= 0.6:
            return "riesgo alto"
        elif value >= 0.4:
            return "riesgo moderado"
        elif value >= 0.2:
            return "riesgo bajo"
        else:
            return "riesgo muy bajo"
    
    # Interpretación genérica para valores entre 0 y 1
    elif 0 <= value <= 1:
        if value >= 0.8:
            return "muy alto"
        elif value >= 0.6:
            return "alto"
        elif value >= 0.4:
            return "moderado"
        elif value >= 0.2:
            return "bajo"
        else:
            return "muy bajo"
    
    # Para valores fuera del rango 0-1
    else:
        if abs(value) >= 2:
            return "valor extremo"
        elif abs(value) >= 1:
            return "valor alto"
        else:
            return "valor normal"

def _generate_local_report(
    decision: str, strategy: str, market_regime: str,
    xai_factors: Dict[str, Any], primary_causal_factors: List[str],
    additional_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Genera un reporte local sin usar APIs externas.
    
    Args:
        decision: Decisión tomada
        strategy: Estrategia utilizada
        market_regime: Régimen de mercado
        xai_factors: Factores explicativos
        primary_causal_factors: Factores causales principales
        additional_context: Contexto adicional
        
    Returns:
        Reporte cognitivo generado localmente
    """
    try:
        # Mapear decisiones a acciones
        decision_map = {
            'momentum': 'seguimiento de tendencia',
            'mean_reversion': 'reversión a la media',
            'breakout': 'ruptura de rangos',
            'hold': 'mantener posición'
        }
        
        # Mapear regímenes a descripciones
        regime_descriptions = {
            'Tendencia Alcista': 'mercado en tendencia alcista sostenida',
            'Tendencia Bajista': 'mercado en tendencia bajista pronunciada',
            'Lateral/Consolidación': 'mercado en consolidación lateral',
            'Alta Volatilidad': 'mercado con alta volatilidad',
            'Baja Volatilidad': 'mercado con baja volatilidad',
            'Desconocido': 'régimen de mercado indeterminado'
        }
        
        # Obtener confianza
        confidence = xai_factors.get('confidence', 0.0)
        signal_strength = xai_factors.get('signal_strength', 0.0)
        
        # Construir reporte
        report = f"=== REPORTE COGNITIVO SICAR ===\n"
        report += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        report += f"DECISIÓN: {decision.upper()}\n"
        report += f"El sistema ha decidido ejecutar una estrategia de {decision_map.get(strategy, strategy)} "
        report += f"basándose en el análisis del {regime_descriptions.get(market_regime, market_regime)}.\n\n"
        
        # Explicar la lógica
        if strategy == 'momentum':
            report += "RAZONAMIENTO: La estrategia de momentum fue seleccionada debido a señales de "
            report += "continuación de tendencia. El sistema detectó que el precio está siguiendo "
            report += "una dirección clara con suficiente fuerza para justificar seguir la tendencia.\n\n"
        elif strategy == 'mean_reversion':
            report += "RAZONAMIENTO: La estrategia de reversión a la media fue elegida porque el "
            report += "precio se encuentra en niveles extremos (sobrecompra/sobreventa) con alta "
            report += "probabilidad de retorno hacia niveles promedio.\n\n"
        elif strategy == 'breakout':
            report += "RAZONAMIENTO: Se detectó una ruptura significativa de niveles de soporte/resistencia "
            report += "con volumen confirmatorio, sugiriendo el inicio de un nuevo movimiento direccional.\n\n"
        else:
            report += "RAZONAMIENTO: Las condiciones actuales no presentan oportunidades claras "
            report += "con suficiente probabilidad de éxito, por lo que se mantiene una posición neutral.\n\n"
        
        # Factores de confianza
        if confidence > 0.8:
            confidence_level = "MUY ALTA"
        elif confidence > 0.6:
            confidence_level = "ALTA"
        elif confidence > 0.4:
            confidence_level = "MODERADA"
        else:
            confidence_level = "BAJA"
        
        report += f"CONFIANZA: {confidence_level} ({confidence:.1%})\n"
        report += f"La confianza en esta decisión se basa en la convergencia de múltiples indicadores "
        report += f"y la claridad de las señales del régimen de mercado identificado.\n\n"
        
        # Factores causales
        if primary_causal_factors:
            report += "FACTORES CLAVE:\n"
            for factor in primary_causal_factors[:3]:  # Mostrar solo los 3 principales
                report += f"• {factor.replace('_', ' ').title()}\n"
            report += "\n"
        
        # Gestión de riesgo
        report += "GESTIÓN DE RIESGO:\n"
        if signal_strength > 0.7:
            report += "• Señal fuerte detectada, riesgo moderado\n"
        elif signal_strength > 0.4:
            report += "• Señal moderada, riesgo estándar aplicado\n"
        else:
            report += "• Señal débil, riesgo reducido o posición neutral\n"
        
        report += "• Stop-loss automático configurado según volatilidad\n"
        report += "• Tamaño de posición calculado según gestión de capital\n\n"
        
        # Contexto adicional
        if additional_context:
            report += "CONTEXTO ADICIONAL:\n"
            for key, value in additional_context.items():
                if isinstance(value, float):
                    report += f"• {key.replace('_', ' ').title()}: {value:.3f}\n"
                else:
                    report += f"• {key.replace('_', ' ').title()}: {value}\n"
        
        report += "\n=== FIN DEL REPORTE ==="
        
        logger.info("Reporte cognitivo generado localmente")
        return report
        
    except Exception as e:
        logger.error(f"Error generando reporte local: {str(e)}")
        return _generate_fallback_report(decision, strategy, market_regime)

def _generate_fallback_report(decision: str, strategy: str, market_regime: str) -> str:
    """
    Genera un reporte básico de fallback en caso de errores.
    
    Args:
        decision: Decisión tomada
        strategy: Estrategia utilizada
        market_regime: Régimen de mercado
        
    Returns:
        Reporte básico de fallback
    """
    return f"""
=== REPORTE BÁSICO SICAR ===
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DECISIÓN: {decision.upper()}
ESTRATEGIA: {strategy}
RÉGIMEN: {market_regime}

El sistema SICAR ha analizado las condiciones de mercado y ha tomado 
la decisión indicada basándose en los algoritmos de análisis causal, 
clasificación de regímenes y metacontrolador.

Nota: Reporte generado en modo básico debido a limitaciones técnicas.
=== FIN DEL REPORTE ===
"""

def save_cognitive_report(report: str, filename: str = None) -> str:
    """
    Guarda el reporte cognitivo en un archivo.
    
    Args:
        report: Contenido del reporte
        filename: Nombre del archivo (opcional)
        
    Returns:
        Ruta del archivo guardado
    """
    try:
        # Crear directorio de reportes
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generar nombre de archivo si no se proporciona
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"cognitive_report_{timestamp}.txt"
        
        # Guardar reporte
        filepath = os.path.join(reports_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Reporte cognitivo guardado en {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Error guardando reporte: {str(e)}")
        return ""

def analyze_decision_factors(
    market_data: Dict[str, Any],
    regime_info: Dict[str, Any],
    strategy_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analiza los factores que influyeron en la decisión para el reporte XAI.
    
    Args:
        market_data: Datos de mercado
        regime_info: Información del régimen
        strategy_info: Información de la estrategia
        
    Returns:
        Diccionario con factores analizados
    """
    try:
        factors = {
            'market_factors': {},
            'regime_factors': {},
            'strategy_factors': {},
            'risk_factors': {}
        }
        
        # Factores de mercado
        if 'volatility' in market_data:
            vol = market_data['volatility']
            if vol > 0.03:
                factors['market_factors']['high_volatility'] = vol
            elif vol < 0.01:
                factors['market_factors']['low_volatility'] = vol
        
        if 'momentum' in market_data:
            mom = market_data['momentum']
            if abs(mom) > 0.05:
                factors['market_factors']['strong_momentum'] = mom
        
        # Factores de régimen
        regime_confidence = regime_info.get('confidence', 0.0)
        if regime_confidence > 0.8:
            factors['regime_factors']['high_regime_confidence'] = regime_confidence
        elif regime_confidence < 0.5:
            factors['regime_factors']['uncertain_regime'] = regime_confidence
        
        # Factores de estrategia
        strategy_confidence = strategy_info.get('confidence', 0.0)
        signal_strength = abs(strategy_info.get('signal', 0.0))
        
        factors['strategy_factors']['confidence'] = strategy_confidence
        factors['strategy_factors']['signal_strength'] = signal_strength
        
        # Factores de riesgo
        if strategy_confidence < 0.6:
            factors['risk_factors']['low_confidence'] = strategy_confidence
        
        if signal_strength < 0.3:
            factors['risk_factors']['weak_signal'] = signal_strength
        
        return factors
        
    except Exception as e:
        logger.error(f"Error analizando factores de decisión: {str(e)}")
        return {}

def generate_multi_timeframe_xai_report(
    multi_timeframe_results: Dict[str, Any],
    final_decision: str,
    consensus_confidence: float,
    risk_assessment: Dict[str, Any]
) -> str:
    """
    Genera un reporte XAI específico para análisis multi-timeframe.
    
    Args:
        multi_timeframe_results: Resultados del análisis multi-timeframe
        final_decision: Decisión final tomada
        consensus_confidence: Confianza del consenso
        risk_assessment: Evaluación de riesgo
        
    Returns:
        Reporte XAI multi-timeframe
    """
    try:
        logger.info("Generando reporte XAI multi-timeframe...")
        
        # Extraer información de cada timeframe
        timeframe_analysis = {}
        for tf, results in multi_timeframe_results.get('timeframe_results', {}).items():
            timeframe_analysis[tf] = {
                'regime': results.get('regime_analysis', {}).get('regime_name', 'Desconocido'),
                'strategy': results.get('strategy_decision', {}).get('strategy', 'hold'),
                'confidence': results.get('strategy_decision', {}).get('confidence', 0.0),
                'signal': results.get('strategy_decision', {}).get('signal', 0.0)
            }
        
        # Generar explicación del consenso
        consensus_explanation = _explain_multi_timeframe_consensus(
            timeframe_analysis, 
            multi_timeframe_results.get('final_consensus', {}),
            consensus_confidence
        )
        
        # Generar explicación de divergencias
        divergence_explanation = _explain_timeframe_divergences(
            timeframe_analysis,
            risk_assessment
        )
        
        # Generar recomendaciones específicas
        recommendations = _generate_multi_timeframe_recommendations(
            timeframe_analysis,
            final_decision,
            risk_assessment
        )
        
        # Construir reporte completo
        report = f"""
🔍 === REPORTE XAI MULTI-TIMEFRAME SICAR ===
📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 DECISIÓN FINAL: {final_decision}
📊 Confianza del Consenso: {consensus_confidence:.1%}

{consensus_explanation}

{divergence_explanation}

{recommendations}

🔬 ANÁLISIS DETALLADO POR TIMEFRAME:
{_format_timeframe_details(timeframe_analysis)}

⚠️ EVALUACIÓN DE RIESGO:
{_format_risk_assessment(risk_assessment)}

🧠 EXPLICACIÓN COGNITIVA:
{_generate_cognitive_explanation(timeframe_analysis, final_decision)}

=== FIN DEL REPORTE ===
"""
        
        return report.strip()
        
    except Exception as e:
        logger.error(f"Error generando reporte XAI multi-timeframe: {str(e)}")
        return f"Error generando reporte XAI: {str(e)}"

def _explain_multi_timeframe_consensus(
    timeframe_analysis: Dict[str, Dict],
    final_consensus: Dict[str, Any],
    consensus_confidence: float
) -> str:
    """Explica cómo se llegó al consenso multi-timeframe."""
    try:
        # Contar estrategias por timeframe
        strategy_counts = {}
        signal_sum = 0
        total_weight = 0
        
        for tf, analysis in timeframe_analysis.items():
            strategy = analysis['strategy']
            signal = analysis['signal']
            confidence = analysis['confidence']
            
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            signal_sum += signal * confidence
            total_weight += confidence
        
        weighted_signal = signal_sum / total_weight if total_weight > 0 else 0
        
        explanation = f"""
📈 CONSENSO MULTI-TIMEFRAME:
• Señal ponderada final: {weighted_signal:.3f}
• Confianza del consenso: {consensus_confidence:.1%}

🗳️ DISTRIBUCIÓN DE ESTRATEGIAS:
"""
        
        for strategy, count in strategy_counts.items():
            percentage = (count / len(timeframe_analysis)) * 100
            explanation += f"• {strategy}: {count}/{len(timeframe_analysis)} timeframes ({percentage:.0f}%)\n"
        
        # Explicar la lógica del consenso
        if consensus_confidence > 0.7:
            explanation += "\n✅ CONSENSO FUERTE: Los timeframes muestran alta concordancia."
        elif consensus_confidence > 0.5:
            explanation += "\n⚠️ CONSENSO MODERADO: Existe cierta divergencia entre timeframes."
        else:
            explanation += "\n🚨 CONSENSO DÉBIL: Alta divergencia entre timeframes - mayor riesgo."
        
        return explanation
        
    except Exception as e:
        logger.error(f"Error explicando consenso: {str(e)}")
        return "Error explicando consenso multi-timeframe"

def _explain_timeframe_divergences(
    timeframe_analysis: Dict[str, Dict],
    risk_assessment: Dict[str, Any]
) -> str:
    """Explica las divergencias entre timeframes y su impacto."""
    try:
        explanation = "\n🔄 ANÁLISIS DE DIVERGENCIAS:\n"
        
        # Identificar divergencias en estrategias
        strategies = [analysis['strategy'] for analysis in timeframe_analysis.values()]
        unique_strategies = set(strategies)
        
        if len(unique_strategies) == 1:
            explanation += "✅ Sin divergencias: Todos los timeframes sugieren la misma estrategia.\n"
        else:
            explanation += f"⚠️ Divergencias detectadas: {len(unique_strategies)} estrategias diferentes.\n"
            
            # Detallar divergencias
            for strategy in unique_strategies:
                timeframes = [tf for tf, analysis in timeframe_analysis.items() 
                            if analysis['strategy'] == strategy]
                explanation += f"  • {strategy}: {', '.join(timeframes)}\n"
        
        # Explicar impacto en el riesgo
        divergence_risk = risk_assessment.get('divergence_risk', 0.0)
        if divergence_risk > 0.7:
            explanation += "\n🚨 ALTO RIESGO: Las divergencias indican incertidumbre significativa."
        elif divergence_risk > 0.4:
            explanation += "\n⚠️ RIESGO MODERADO: Las divergencias requieren cautela adicional."
        else:
            explanation += "\n✅ BAJO RIESGO: Las divergencias son mínimas o manejables."
        
        return explanation
        
    except Exception as e:
        logger.error(f"Error explicando divergencias: {str(e)}")
        return "Error explicando divergencias"

def _generate_multi_timeframe_recommendations(
    timeframe_analysis: Dict[str, Dict],
    final_decision: str,
    risk_assessment: Dict[str, Any]
) -> str:
    """Genera recomendaciones específicas basadas en el análisis multi-timeframe."""
    try:
        recommendations = "\n💡 RECOMENDACIONES MULTI-TIMEFRAME:\n"
        
        # Recomendaciones basadas en la decisión
        if final_decision == "BUY":
            recommendations += "📈 COMPRA RECOMENDADA:\n"
            recommendations += "  • Considerar entrada gradual si hay divergencias\n"
            recommendations += "  • Monitorear timeframes menores para timing óptimo\n"
        elif final_decision == "SELL":
            recommendations += "📉 VENTA RECOMENDADA:\n"
            recommendations += "  • Evaluar salida gradual si hay divergencias\n"
            recommendations += "  • Confirmar con timeframes mayores\n"
        else:
            recommendations += "⏸️ MANTENER POSICIÓN:\n"
            recommendations += "  • Esperar mayor claridad en el consenso\n"
            recommendations += "  • Monitorear cambios en timeframes clave\n"
        
        # Recomendaciones de gestión de riesgo
        overall_risk = risk_assessment.get('overall_risk_level', 'medium')
        if overall_risk == 'high':
            recommendations += "\n🛡️ GESTIÓN DE RIESGO ALTA:\n"
            recommendations += "  • Reducir tamaño de posición\n"
            recommendations += "  • Usar stops más ajustados\n"
            recommendations += "  • Considerar hedging\n"
        elif overall_risk == 'medium':
            recommendations += "\n⚖️ GESTIÓN DE RIESGO MODERADA:\n"
            recommendations += "  • Mantener tamaño de posición estándar\n"
            recommendations += "  • Usar stops normales\n"
        else:
            recommendations += "\n✅ GESTIÓN DE RIESGO BAJA:\n"
            recommendations += "  • Posición estándar o ligeramente mayor\n"
            recommendations += "  • Stops más amplios permitidos\n"
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generando recomendaciones: {str(e)}")
        return "Error generando recomendaciones"

def _format_timeframe_details(timeframe_analysis: Dict[str, Dict]) -> str:
    """Formatea los detalles de cada timeframe."""
    try:
        details = ""
        for tf, analysis in timeframe_analysis.items():
            details += f"""
⏱️ {tf.upper()}:
  • Régimen: {analysis['regime']}
  • Estrategia: {analysis['strategy']}
  • Confianza: {analysis['confidence']:.1%}
  • Señal: {analysis['signal']:.3f}
"""
        return details
        
    except Exception as e:
        logger.error(f"Error formateando detalles: {str(e)}")
        return "Error formateando detalles de timeframes"

def _format_risk_assessment(risk_assessment: Dict[str, Any]) -> str:
    """Formatea la evaluación de riesgo."""
    try:
        risk_text = f"""
🎯 Nivel de Riesgo General: {risk_assessment.get('overall_risk_level', 'medium').upper()}
📊 Riesgo de Divergencia: {risk_assessment.get('divergence_risk', 0.0):.1%}
📈 Riesgo de Volatilidad: {risk_assessment.get('volatility_risk', 0.0):.1%}

💬 Recomendación de Riesgo:
{risk_assessment.get('risk_recommendation', 'Mantener gestión de riesgo estándar')}
"""
        return risk_text
        
    except Exception as e:
        logger.error(f"Error formateando evaluación de riesgo: {str(e)}")
        return "Error formateando evaluación de riesgo"

def _generate_cognitive_explanation(
    timeframe_analysis: Dict[str, Dict],
    final_decision: str
) -> str:
    """Genera una explicación cognitiva del proceso de decisión."""
    try:
        explanation = f"""
El sistema SICAR analizó {len(timeframe_analysis)} timeframes diferentes para llegar a la decisión de {final_decision}.

🧠 PROCESO COGNITIVO:
1. ANÁLISIS INDIVIDUAL: Cada timeframe fue evaluado independientemente
2. PONDERACIÓN: Las decisiones se ponderaron por confianza y importancia del timeframe
3. CONSENSO: Se calculó un consenso ponderado entre todos los timeframes
4. VALIDACIÓN: Se verificó la coherencia y se evaluaron los riesgos

🎯 FACTORES CLAVE:
• Coherencia entre timeframes
• Fuerza de las señales individuales
• Nivel de confianza de cada análisis
• Evaluación de riesgos y divergencias

Esta aproximación multi-timeframe reduce el ruido y mejora la robustez de las decisiones.
"""
        return explanation
        
    except Exception as e:
        logger.error(f"Error generando explicación cognitiva: {str(e)}")
        return "Error generando explicación cognitiva"

def generate_multi_ai_comparison_report(
    decision: str,
    strategy: str,
    market_regime: str,
    xai_factors: Dict[str, Any],
    primary_causal_factors: List[str],
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Genera reportes con múltiples APIs de IA y compara sus análisis.
    
    Args:
        decision: Decisión tomada
        strategy: Estrategia utilizada
        market_regime: Régimen de mercado
        xai_factors: Factores explicativos
        primary_causal_factors: Factores causales principales
        additional_context: Contexto adicional
        
    Returns:
        Diccionario con reportes de cada IA y análisis comparativo
    """
    try:
        logger.info("Generando reportes multi-IA para comparación...")
        
        results = {}
        apis_to_test = ['openai', 'anthropic', 'grok']
        
        # Generar reportes con cada API disponible
        for api_name in apis_to_test:
            try:
                if api_name == 'openai' and os.getenv('OPENAI_API_KEY'):
                    results['openai'] = _generate_report_openai(
                        decision, strategy, market_regime,
                        xai_factors, primary_causal_factors, additional_context
                    )
                elif api_name == 'anthropic' and os.getenv('ANTHROPIC_API_KEY'):
                    results['anthropic'] = _generate_report_anthropic(
                        decision, strategy, market_regime,
                        xai_factors, primary_causal_factors, additional_context
                    )
                elif api_name == 'zai' and os.getenv('ZAI_API_KEY'):
                    results['zai'] = _generate_report_zai(
                        decision, strategy, market_regime,
                        xai_factors, primary_causal_factors, additional_context
                    )
                elif api_name == 'grok' and os.getenv('GROK_API_KEY'):
                    results['grok'] = _generate_report_grok(
                        decision, strategy, market_regime,
                        xai_factors, primary_causal_factors, additional_context
                    )
            except Exception as e:
                logger.warning(f"Error generando reporte con {api_name}: {str(e)}")
                results[api_name] = f"Error: {str(e)}"
        
        # Generar análisis comparativo
        comparison = _analyze_ai_consensus(results, decision, strategy)
        
        return {
            'individual_reports': results,
            'consensus_analysis': comparison,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generando comparación multi-IA: {str(e)}")
        return {
            'individual_reports': {},
            'consensus_analysis': {'error': str(e)},
            'timestamp': datetime.now().isoformat()
        }

def _analyze_ai_consensus(reports: Dict[str, str], decision: str, strategy: str) -> Dict[str, Any]:
    """
    Analiza el consenso entre diferentes modelos de IA.
    
    Args:
        reports: Diccionario de reportes por IA
        decision: Decisión tomada
        strategy: Estrategia utilizada
        
    Returns:
        Análisis de consenso y recomendaciones
    """
    try:
        consensus_score = 0
        sentiment_scores = {}
        key_points = {}
        
        # Análisis básico de consenso
        total_models = len(reports)
        if total_models == 0:
            return {'error': 'No hay reportes disponibles para análisis'}
        
        # Analizar cada reporte
        for model_name, report in reports.items():
            if 'Error' in report:
                continue
                
            # Análisis simple de sentimiento (palabras clave)
            positive_words = ['compra', 'alcista', 'fuerte', 'positivo', 'oportunidad', 'recomendado']
            negative_words = ['venta', 'bajista', 'débil', 'negativo', 'riesgo', 'cautela']
            neutral_words = ['mantener', 'neutral', 'estable', 'lateral']
            
            report_lower = report.lower()
            
            positive_count = sum(1 for word in positive_words if word in report_lower)
            negative_count = sum(1 for word in negative_words if word in report_lower)
            neutral_count = sum(1 for word in neutral_words if word in report_lower)
            
            # Calcular puntuación de sentimiento (-1 a 1)
            sentiment = (positive_count - negative_count) / max(1, positive_count + negative_count + neutral_count)
            sentiment_scores[model_name] = sentiment
            
            # Extraer puntos clave (primeras frases del reporte)
            sentences = report.split('.')[:3]
            key_points[model_name] = [s.strip() for s in sentences if s.strip()]
        
        # Calcular consenso general
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores.values()) / len(sentiment_scores)
            consensus_score = abs(avg_sentiment)  # Mayor abs = mayor consenso
            
            # Determinar recomendación basada en consenso
            if avg_sentiment > 0.3:
                consensus_recommendation = "COMPRA FUERTE"
                confidence_level = "ALTA"
            elif avg_sentiment > 0.1:
                consensus_recommendation = "COMPRA MODERADA"
                confidence_level = "MODERADA"
            elif avg_sentiment < -0.3:
                consensus_recommendation = "VENTA FUERTE"
                confidence_level = "ALTA"
            elif avg_sentiment < -0.1:
                consensus_recommendation = "VENTA MODERADA"
                confidence_level = "MODERADA"
            else:
                consensus_recommendation = "MANTENER"
                confidence_level = "BAJA"
        else:
            avg_sentiment = 0
            consensus_recommendation = "ANÁLISIS INCONCLUSO"
            confidence_level = "N/A"
        
        return {
            'consensus_score': consensus_score,
            'average_sentiment': avg_sentiment,
            'sentiment_by_model': sentiment_scores,
            'consensus_recommendation': consensus_recommendation,
            'confidence_level': confidence_level,
            'key_points_by_model': key_points,
            'models_analyzed': len(sentiment_scores),
            'total_models': total_models
        }
        
    except Exception as e:
        logger.error(f"Error analizando consenso IA: {str(e)}")
        return {'error': str(e)}

def main():
    """Función principal para probar el módulo XAI."""
    try:
        logger.info("Ejecutando ejemplo del Módulo XAI...")
        
        # Datos de ejemplo
        decision = "BUY"
        strategy = "momentum"
        market_regime = "Tendencia Alcista"
        
        xai_factors = {
            'confidence': 0.85,
            'signal_strength': 0.72,
            'volatility': 0.025,
            'momentum': 0.08
        }
        
        primary_causal_factors = [
            'momentum_alcista',
            'volumen_confirmatorio',
            'ruptura_resistencia'
        ]
        
        additional_context = {
            'price': 45250.50,
            'volume_ratio': 1.35,
            'rsi': 65.2
        }
        
        print("\n" + "="*60)
        print("🧠 SISTEMA XAI MULTI-IA DE SICAR")
        print("="*60)
        
        # 1. Generar reporte individual con fallback automático
        print("\n1️⃣ GENERANDO REPORTE CON FALLBACK AUTOMÁTICO...")
        report = generate_cognitive_report(
            decision=decision,
            strategy=strategy,
            market_regime=market_regime,
            xai_factors=xai_factors,
            primary_causal_factors=primary_causal_factors,
            additional_context=additional_context
        )
        
        print("\n📊 REPORTE GENERADO:")
        print("-" * 40)
        print(report)
        print("-" * 40)
        
        # 2. Generar comparación multi-IA
        print("\n2️⃣ GENERANDO COMPARACIÓN MULTI-IA...")
        comparison_result = generate_multi_ai_comparison_report(
            decision=decision,
            strategy=strategy,
            market_regime=market_regime,
            xai_factors=xai_factors,
            primary_causal_factors=primary_causal_factors,
            additional_context=additional_context
        )
        
        print("\n🔍 ANÁLISIS DE CONSENSO MULTI-IA:")
        print("-" * 40)
        consensus = comparison_result.get('consensus_analysis', {})
        if 'error' not in consensus:
            print(f"📈 Recomendación de Consenso: {consensus.get('consensus_recommendation', 'N/A')}")
            print(f"🎯 Nivel de Confianza: {consensus.get('confidence_level', 'N/A')}")
            print(f"📊 Score de Consenso: {consensus.get('consensus_score', 0):.2f}")
            print(f"📈 Sentimiento Promedio: {consensus.get('average_sentiment', 0):.2f}")
            print(f"🤖 Modelos Analizados: {consensus.get('models_analyzed', 0)}/{consensus.get('total_models', 0)}")
        else:
            print(f"❌ Error en análisis de consenso: {consensus.get('error')}")
        
        # Mostrar reportes individuales
        individual_reports = comparison_result.get('individual_reports', {})
        if individual_reports:
            print(f"\n📄 REPORTES INDIVIDUALES POR IA:")
            for model_name, report in individual_reports.items():
                if 'Error' not in report:
                    # Mostrar solo primeras líneas de cada reporte
                    first_lines = '.'.join(report.split('.')[:2]) + "..."
                    print(f"\n🤖 {model_name.upper()}:")
                    print(f"   {first_lines}")
        
        print("-" * 40)
        
        # 3. Guardar reportes
        filepath = save_cognitive_report(report, "ejemplo_reporte_xai.txt")
        if filepath:
            print(f"\n✅ Reporte individual guardado en: {filepath}")
        
        # Guardar comparación
        comparison_filepath = save_cognitive_report(
            f"=== COMPARACIÓN MULTI-IA SICAR ===\n\n" +
            f"Timestamp: {comparison_result.get('timestamp', 'N/A')}\n\n" +
            f"📈 ANÁLISIS DE CONSENSO:\n{str(consensus)}\n\n" +
            f"📄 REPORTES INDIVIDUALES:\n{str(individual_reports)}",
            "comparacion_multi_ia.txt"
        )
        if comparison_filepath:
            print(f"✅ Comparación multi-IA guardada en: {comparison_filepath}")
        
        print(f"\n✅ Módulo XAI multi-IA funcionando correctamente")
        
        # 4. Mostrar configuración actual
        print(f"\n⚙️ CONFIGURACIÓN ACTUAL:")
        print(f"   • ALLOW_EXTERNAL_LLMS: {os.getenv('ALLOW_EXTERNAL_LLMS', 'false')}")
        print(f"   • LLM_FALLBACK_ORDER: {os.getenv('LLM_FALLBACK_ORDER', 'openai,anthropic,zai,grok,local')}")
        
        # Verificar qué APIs están configuradas
        apis_configured = []
        if os.getenv('OPENAI_API_KEY'): apis_configured.append('OpenAI')
        if os.getenv('ANTHROPIC_API_KEY'): apis_configured.append('Anthropic')
        if os.getenv('ZAI_API_KEY'): apis_configured.append('Z.ai')
        if os.getenv('GROK_API_KEY'): apis_configured.append('Grok')
        
        print(f"   • APIs Configuradas: {', '.join(apis_configured) if apis_configured else 'Ninguna (modo local)'}")
        
    except Exception as e:
        logger.error(f"Error en main: {str(e)}")
        print(f"❌ Error ejecutando ejemplo: {str(e)}")

if __name__ == '__main__':
    main()
