# /src/module_1_causal.py
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None

import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import json
import os
import sys
import logging
from typing import List, Dict, Tuple, Optional, Any
import networkx as nx
from datetime import datetime
import re
from openai import OpenAI
import time

# Agregar el directorio padre al path para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SPACY_MODEL

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CausalCartographer:
    """
    Módulo 1: Cartógrafo Causal
    
    Utiliza NLP y análisis de texto para construir un mapa de relaciones
    de causa y efecto en tiempo real a partir de noticias y datos alternativos.
    """
    
    def __init__(self):
        """Inicializa el cartógrafo causal."""
        self.nlp = None
        self.financial_keywords = self._load_financial_keywords()
        self.causal_patterns = self._load_causal_patterns()
        self.entity_graph = nx.DiGraph()
        self.co_occurrence_matrix = defaultdict(int)
        self.sentiment_scores = {}
        
        # Inicializar cliente Grok xAI
        self.grok_client = None
        self._initialize_grok_client()
        
        self._initialize_nlp()
    
    def _initialize_nlp(self):
        """Inicializa el modelo de spaCy."""
        if not SPACY_AVAILABLE or spacy is None:
            logger.warning("spaCy no está disponible, usando procesamiento básico de texto")
            self.nlp = None
            return
            
        try:
            self.nlp = spacy.load(SPACY_MODEL)
            logger.info(f"Modelo {SPACY_MODEL} cargado exitosamente")
        except OSError:
            logger.warning(f"Modelo {SPACY_MODEL} no encontrado.")
            # Fallback a modelo en inglés si está disponible
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.warning("Usando modelo en inglés como fallback")
            except OSError:
                try:
                    # Intentar con modelo básico
                    self.nlp = spacy.blank("en")
                    logger.warning("Usando modelo básico de spaCy sin entidades")
                except Exception:
                    logger.warning("spaCy no disponible, usando procesamiento básico de texto")
                    self.nlp = None
    
    def _initialize_grok_client(self):
        """Inicializa el cliente de Grok xAI."""
        try:
            grok_api_key = os.getenv('GROK_API_KEY')
            grok_base_url = os.getenv('GROK_BASE_URL', 'https://api.x.ai/v1')
            
            if grok_api_key:
                self.grok_client = OpenAI(
                    api_key=grok_api_key,
                    base_url=grok_base_url
                )
                logger.info("Cliente Grok xAI inicializado exitosamente")
            else:
                logger.warning("GROK_API_KEY no encontrada en variables de entorno")
                self.grok_client = None
                
        except Exception as e:
            logger.error(f"Error inicializando cliente Grok xAI: {str(e)}")
            self.grok_client = None
    
    def _load_financial_keywords(self) -> Dict[str, List[str]]:
        """Carga palabras clave financieras categorizadas."""
        return {
            'cryptocurrencies': [
                'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'criptomoneda',
                'blockchain', 'defi', 'nft', 'altcoin', 'stablecoin'
            ],
            'institutions': [
                'fed', 'federal reserve', 'banco central', 'sec', 'cftc',
                'treasury', 'tesoro', 'gobierno', 'regulador'
            ],
            'economic_indicators': [
                'inflación', 'inflation', 'pib', 'gdp', 'empleo', 'unemployment',
                'tipos de interés', 'interest rates', 'cpi', 'ipc'
            ],
            'market_sentiment': [
                'miedo', 'fear', 'pánico', 'panic', 'euforia', 'euphoria',
                'optimismo', 'optimism', 'pesimismo', 'pessimism', 'volatilidad'
            ],
            'events': [
                'halving', 'fork', 'actualización', 'upgrade', 'hack', 'hackeo',
                'adopción', 'adoption', 'prohibición', 'ban', 'regulación'
            ]
        }
    
    def _load_causal_patterns(self) -> List[str]:
        """Carga patrones lingüísticos que indican causalidad."""
        return [
            r'debido a',
            r'a causa de',
            r'por culpa de',
            r'como resultado de',
            r'provocó',
            r'causó',
            r'llevó a',
            r'resultó en',
            r'impulsó',
            r'desencadenó',
            r'because of',
            r'due to',
            r'caused by',
            r'led to',
            r'resulted in',
            r'triggered',
            r'drove',
            r'sparked'
        ]
    
    def analyze_text_for_entities(self, text: str) -> Dict[str, Any]:
        """
        Analiza un texto para extraer entidades financieras relevantes.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Diccionario con entidades extraídas y metadatos
        """
        if not self.nlp:
            logger.warning("Modelo NLP no disponible")
            return {'entities': [], 'sentiment': 0, 'causal_relations': []}
        
        try:
            doc = self.nlp(text.lower())
            
            # Extraer entidades nombradas
            named_entities = [ent.text for ent in doc.ents 
                            if ent.label_ in ['ORG', 'PERSON', 'GPE', 'MONEY']]
            
            # Extraer palabras clave financieras
            financial_entities = []
            for category, keywords in self.financial_keywords.items():
                for keyword in keywords:
                    if keyword in text.lower():
                        financial_entities.append(keyword)
            
            # Combinar entidades
            all_entities = list(set(named_entities + financial_entities))
            
            # Filtrar entidades muy cortas o genéricas
            relevant_entities = [ent for ent in all_entities if len(ent) > 2]
            
            # Análisis de sentimiento básico (usando palabras clave)
            sentiment = self._calculate_basic_sentiment(text)
            
            # Detectar relaciones causales
            causal_relations = self._extract_causal_relations(text, relevant_entities)
            
            return {
                'entities': relevant_entities,
                'sentiment': sentiment,
                'causal_relations': causal_relations,
                'text_length': len(text),
                'entity_count': len(relevant_entities)
            }
            
        except Exception as e:
            logger.error(f"Error analizando texto: {str(e)}")
            return {'entities': [], 'sentiment': 0, 'causal_relations': []}
    
    def _calculate_basic_sentiment(self, text: str) -> float:
        """
        Calcula un sentimiento básico usando palabras clave.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Puntuación de sentimiento (-1 a 1)
        """
        positive_words = [
            'subida', 'alza', 'crecimiento', 'optimismo', 'positivo',
            'bull', 'bullish', 'rally', 'pump', 'moon', 'gains'
        ]
        
        negative_words = [
            'caída', 'baja', 'crash', 'pánico', 'miedo', 'negativo',
            'bear', 'bearish', 'dump', 'crash', 'fear', 'losses'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(text.split())
        if total_words == 0:
            return 0
        
        sentiment = (positive_count - negative_count) / max(total_words, 1)
        return max(-1, min(1, sentiment * 10))  # Normalizar entre -1 y 1
    
    def _extract_causal_relations(self, text: str, entities: List[str]) -> List[Dict[str, str]]:
        """
        Extrae relaciones causales del texto.
        
        Args:
            text: Texto a analizar
            entities: Lista de entidades encontradas
            
        Returns:
            Lista de relaciones causales encontradas
        """
        causal_relations = []
        text_lower = text.lower()
        
        for pattern in self.causal_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                # Buscar entidades antes y después del patrón causal
                start_pos = max(0, match.start() - 100)
                end_pos = min(len(text), match.end() + 100)
                context = text_lower[start_pos:end_pos]
                
                # Encontrar entidades en el contexto
                context_entities = [ent for ent in entities if ent in context]
                
                if len(context_entities) >= 2:
                    causal_relations.append({
                        'pattern': pattern,
                        'entities': context_entities,
                        'context': context.strip(),
                        'confidence': 0.7  # Confianza básica
                    })
        
        return causal_relations
    
    def analyze_market_narrative_with_grok(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Analiza la narrativa del mercado en tiempo real usando Grok xAI.
        
        Args:
            symbol: Símbolo del activo a analizar
            
        Returns:
            Diccionario con análisis de narrativa y sentimiento
        """
        if not self.grok_client:
            logger.warning("Cliente Grok xAI no disponible")
            return self._get_fallback_analysis()
        
        try:
            # Crear prompt para análisis de narrativa de mercado
            prompt = f"""
            Analiza la narrativa actual del mercado para {symbol} basándote en las tendencias y conversaciones más recientes en redes sociales y noticias financieras.

            Proporciona un análisis estructurado que incluya:

            1. **Sentimiento General** (escala -1 a 1):
            2. **Factores Causales Principales** (máximo 3):
            3. **Narrativa Dominante** (resumen en 2-3 oraciones):
            4. **Nivel de Confianza** (0-1):
            5. **Palabras Clave** (5-7 términos relevantes):

            Enfócate en:
            - Movimientos de precio recientes
            - Noticias regulatorias
            - Adopción institucional
            - Desarrollos tecnológicos
            - Sentimiento de la comunidad crypto

            Responde en formato JSON válido con las claves: sentiment_score, causal_factors, market_narrative, confidence_level, keywords.
            """
            
            # Llamar a Grok xAI
            response = self.grok_client.chat.completions.create(
                model=os.getenv('GROK_MODEL', 'grok-4-fast-reasoning'),
                messages=[
                    {
                        "role": "system", 
                        "content": "Eres un analista financiero experto especializado en criptomonedas y análisis de sentimiento de mercado. Proporciona análisis precisos y basados en datos."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Procesar respuesta
            grok_response = response.choices[0].message.content
            logger.info(f"Respuesta de Grok recibida para {symbol}")
            
            # Intentar parsear JSON
            try:
                analysis = json.loads(grok_response)
                
                # Validar y normalizar datos
                normalized_analysis = {
                    'sentiment_score': float(analysis.get('sentiment_score', 0)),
                    'causal_factors': analysis.get('causal_factors', []),
                    'market_narrative': analysis.get('market_narrative', ''),
                    'confidence_level': float(analysis.get('confidence_level', 0)),
                    'keywords': analysis.get('keywords', []),
                    'source': 'grok_xai',
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol
                }
                
                logger.info(f"Análisis Grok completado - Sentimiento: {normalized_analysis['sentiment_score']:.2f}")
                return normalized_analysis
                
            except json.JSONDecodeError:
                logger.warning("Respuesta de Grok no es JSON válido, procesando como texto")
                return self._parse_grok_text_response(grok_response, symbol)
                
        except Exception as e:
            logger.error(f"Error analizando narrativa con Grok: {str(e)}")
            return self._get_fallback_analysis()
    
    def _parse_grok_text_response(self, response_text: str, symbol: str) -> Dict[str, Any]:
        """
        Parsea respuesta de texto de Grok cuando no es JSON válido.
        
        Args:
            response_text: Texto de respuesta de Grok
            symbol: Símbolo del activo
            
        Returns:
            Diccionario con análisis parseado
        """
        try:
            # Extraer sentimiento usando regex
            sentiment_match = re.search(r'sentimiento.*?(-?\d+\.?\d*)', response_text.lower())
            sentiment = float(sentiment_match.group(1)) if sentiment_match else 0.0
            
            # Extraer factores causales
            factors = []
            if 'factores' in response_text.lower() or 'factors' in response_text.lower():
                lines = response_text.split('\n')
                for line in lines:
                    if any(word in line.lower() for word in ['factor', 'causa', 'debido', 'por']):
                        clean_factor = re.sub(r'^[-*•]\s*', '', line.strip())
                        if len(clean_factor) > 10:
                            factors.append(clean_factor[:100])
            
            # Extraer narrativa principal
            narrative_lines = []
            lines = response_text.split('\n')
            for line in lines:
                if len(line.strip()) > 20 and not line.strip().startswith(('1.', '2.', '3.', '-', '*')):
                    narrative_lines.append(line.strip())
            
            narrative = ' '.join(narrative_lines[:3]) if narrative_lines else "Análisis de narrativa no disponible"
            
            return {
                'sentiment_score': max(-1, min(1, sentiment)),
                'causal_factors': factors[:3],
                'market_narrative': narrative[:500],
                'confidence_level': 0.7,
                'keywords': ['bitcoin', 'crypto', 'mercado'],
                'source': 'grok_xai_parsed',
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol
            }
            
        except Exception as e:
            logger.error(f"Error parseando respuesta de Grok: {str(e)}")
            return self._get_fallback_analysis()
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """
        Proporciona análisis de respaldo cuando Grok no está disponible.
        
        Returns:
            Diccionario con análisis básico de respaldo
        """
        return {
            'sentiment_score': 0.0,
            'causal_factors': ['Análisis limitado - Grok no disponible'],
            'market_narrative': 'Análisis de narrativa no disponible en este momento',
            'confidence_level': 0.1,
            'keywords': ['mercado', 'análisis', 'limitado'],
            'source': 'fallback',
            'timestamp': datetime.now().isoformat(),
            'symbol': 'UNKNOWN'
        }
    
    def build_causal_graph_lite(self, texts: List[str]) -> pd.DataFrame:
        """
        Construye una matriz de co-ocurrencia como un grafo causal simplificado.
        
        Args:
            texts_corpus: Lista de textos (ej. titulares de noticias)
            
        Returns:
            DataFrame con relaciones entre entidades
        """
        try:
            logger.info(f"Construyendo grafo causal con {len(texts_corpus)} textos...")
            
            all_entities = []
            all_relations = []
            sentiment_by_entity = defaultdict(list)
            
            # Procesar cada texto
            for i, text in enumerate(texts_corpus):
                if i % 10 == 0:
                    logger.info(f"Procesando texto {i+1}/{len(texts_corpus)}")
                
                analysis = self.analyze_text_for_entities(text)
                entities = analysis['entities']
                sentiment = analysis['sentiment']
                causal_relations = analysis['causal_relations']
                
                all_entities.extend(entities)
                all_relations.extend(causal_relations)
                
                # Asociar sentimiento con entidades
                for entity in entities:
                    sentiment_by_entity[entity].append(sentiment)
                
                # Generar pares de co-ocurrencia
                for i in range(len(entities)):
                    for j in range(i + 1, len(entities)):
                        pair = tuple(sorted((entities[i], entities[j])))
                        self.co_occurrence_matrix[pair] += 1
            
            # Crear DataFrame de co-ocurrencias
            if not self.co_occurrence_matrix:
                logger.warning("No se encontraron co-ocurrencias")
                return pd.DataFrame(columns=['entity1', 'entity2', 'weight', 'avg_sentiment'])
            
            # Convertir a DataFrame
            cooccurrence_data = []
            for (entity1, entity2), weight in self.co_occurrence_matrix.items():
                # Calcular sentimiento promedio para las entidades
                sent1 = np.mean(sentiment_by_entity.get(entity1, [0]))
                sent2 = np.mean(sentiment_by_entity.get(entity2, [0]))
                avg_sentiment = (sent1 + sent2) / 2
                
                cooccurrence_data.append({
                    'entity1': entity1,
                    'entity2': entity2,
                    'weight': weight,
                    'avg_sentiment': avg_sentiment
                })
            
            df = pd.DataFrame(cooccurrence_data)
            
            # Filtrar relaciones débiles (menos de 2 co-ocurrencias)
            df = df[df['weight'] >= 2]
            
            # Ordenar por peso
            df = df.sort_values('weight', ascending=False)
            
            logger.info(f"Grafo causal construido: {len(df)} relaciones encontradas")
            
            # Guardar el grafo
            self._save_causal_graph(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error construyendo grafo causal: {str(e)}")
            return pd.DataFrame(columns=['entity1', 'entity2', 'weight', 'avg_sentiment'])
    
    def _save_causal_graph(self, df: pd.DataFrame):
        """Guarda el grafo causal en archivos."""
        try:
            # Crear directorio de salida
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")
            os.makedirs(output_dir, exist_ok=True)
            
            # Guardar como CSV
            csv_path = os.path.join(output_dir, "causal_graph.csv")
            df.to_csv(csv_path, index=False)
            
            # Guardar estadísticas
            stats = {
                'total_relations': len(df),
                'unique_entities': len(set(df['entity1'].tolist() + df['entity2'].tolist())),
                'avg_weight': df['weight'].mean(),
                'avg_sentiment': df['avg_sentiment'].mean(),
                'generated_at': datetime.now().isoformat()
            }
            
            stats_path = os.path.join(output_dir, "causal_graph_stats.json")
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Grafo causal guardado en {csv_path}")
            logger.info(f"Estadísticas guardadas en {stats_path}")
            
        except Exception as e:
            logger.error(f"Error guardando grafo causal: {str(e)}")
    
    def get_entity_influence_score(self, entity: str, df: pd.DataFrame) -> float:
        """
        Calcula un puntaje de influencia para una entidad específica.
        
        Args:
            entity: Nombre de la entidad
            df: DataFrame con el grafo causal
            
        Returns:
            Puntaje de influencia (0-1)
        """
        try:
            # Filtrar relaciones que involucran la entidad
            entity_relations = df[
                (df['entity1'] == entity) | (df['entity2'] == entity)
            ]
            
            if len(entity_relations) == 0:
                return 0.0
            
            # Calcular influencia basada en peso y sentimiento
            total_weight = entity_relations['weight'].sum()
            avg_sentiment = entity_relations['avg_sentiment'].mean()
            connection_count = len(entity_relations)
            
            # Normalizar puntaje
            max_weight = df['weight'].max() if len(df) > 0 else 1
            max_connections = df.groupby('entity1').size().max() if len(df) > 0 else 1
            
            weight_score = total_weight / max_weight
            connection_score = connection_count / max_connections
            sentiment_score = (avg_sentiment + 1) / 2  # Normalizar de [-1,1] a [0,1]
            
            # Combinar puntajes
            influence_score = (weight_score * 0.4 + connection_score * 0.4 + sentiment_score * 0.2)
            
            return min(1.0, influence_score)
            
        except Exception as e:
            logger.error(f"Error calculando influencia para {entity}: {str(e)}")
            return 0.0
    
    def analyze_causal_factors(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analiza factores causales basados en datos de mercado y narrativa en tiempo real con Grok xAI.
        
        Args:
            market_data: DataFrame con datos de mercado (OHLCV)
            
        Returns:
            Diccionario con factores causales identificados
        """
        try:
            logger.info("Analizando factores causales con Grok xAI...")
            
            # 1. Análisis de narrativa en tiempo real con Grok xAI
            symbol = os.getenv('SYMBOL', 'BTCUSDT')
            grok_analysis = self.analyze_market_narrative_with_grok(symbol)
            
            # 2. Análisis tradicional como respaldo
            simulated_news = self._generate_market_based_news(market_data)
            causal_graph = self.build_causal_graph_lite(simulated_news)
            
            # 3. Combinar análisis de Grok con análisis tradicional
            causal_factors = {
                'primary_factors': [],
                'secondary_factors': [],
                'sentiment_score': 0.0,
                'causal_strength': 0.0,
                'market_narrative': '',
                'total_relations': len(causal_graph) if len(causal_graph) > 0 else 0,
                'grok_analysis': grok_analysis,
                'confidence_level': grok_analysis.get('confidence_level', 0.1)
            }
            
            # Priorizar análisis de Grok si está disponible y es confiable
            if grok_analysis['source'] == 'grok_xai' and grok_analysis['confidence_level'] > 0.5:
                logger.info("Usando análisis de Grok xAI como fuente principal")
                
                # Usar datos de Grok como primarios
                causal_factors['sentiment_score'] = grok_analysis['sentiment_score']
                causal_factors['primary_factors'] = grok_analysis['causal_factors']
                causal_factors['market_narrative'] = grok_analysis['market_narrative']
                causal_factors['causal_strength'] = grok_analysis['confidence_level']
                
                # Complementar con análisis tradicional
                if len(causal_graph) > 0:
                    all_entities = causal_graph['entity1'].tolist() + causal_graph['entity2'].tolist()
                    entity_counts = Counter(all_entities)
                    causal_factors['secondary_factors'] = [
                        entity for entity, _ in entity_counts.most_common(3)
                    ]
                else:
                    causal_factors['secondary_factors'] = grok_analysis.get('keywords', [])
                    
            else:
                logger.info("Usando análisis tradicional como fuente principal")
                
                # Usar análisis tradicional como primario
                if len(causal_graph) > 0:
                    top_relations = causal_graph.nlargest(3, 'weight')
                    causal_factors['primary_factors'] = [
                        f"{row['entity1']} -> {row['entity2']}" 
                        for _, row in top_relations.iterrows()
                    ]
                    
                    all_entities = causal_graph['entity1'].tolist() + causal_graph['entity2'].tolist()
                    entity_counts = Counter(all_entities)
                    causal_factors['secondary_factors'] = [
                        entity for entity, _ in entity_counts.most_common(5)
                    ]
                    
                    causal_factors['sentiment_score'] = causal_graph['avg_sentiment'].mean()
                    causal_factors['causal_strength'] = min(1.0, causal_graph['weight'].mean() / 10.0)
                    causal_factors['market_narrative'] = self._generate_market_narrative(causal_graph, market_data)
                else:
                    # Usar Grok como respaldo si no hay análisis tradicional
                    causal_factors['sentiment_score'] = grok_analysis['sentiment_score']
                    causal_factors['primary_factors'] = grok_analysis['causal_factors']
                    causal_factors['market_narrative'] = grok_analysis['market_narrative']
                    causal_factors['secondary_factors'] = grok_analysis.get('keywords', [])
            
            logger.info(f"Análisis causal completado - Sentimiento: {causal_factors['sentiment_score']:.2f}, Confianza: {causal_factors['confidence_level']:.2f}")
            return causal_factors
            
        except Exception as e:
            logger.error(f"Error analizando factores causales: {str(e)}")
            return {
                'primary_factors': ['Error en análisis'],
                'secondary_factors': [],
                'sentiment_score': 0.0,
                'causal_strength': 0.0,
                'market_narrative': 'Error en análisis causal',
                'total_relations': 0,
                'grok_analysis': self._get_fallback_analysis(),
                'confidence_level': 0.0
            }
    
    def _generate_market_based_news(self, market_data: pd.DataFrame) -> List[str]:
        """
        Genera noticias simuladas basadas en movimientos del mercado.
        
        Args:
            market_data: DataFrame con datos de mercado
            
        Returns:
            Lista de noticias simuladas
        """
        try:
            news = []
            
            # Detectar nombres de columnas (manejo de mayúsculas/minúsculas)
            close_col = 'Close' if 'Close' in market_data.columns else 'close'
            volume_col = 'Volume' if 'Volume' in market_data.columns else 'volume'
            
            # Calcular cambios de precio
            price_change = market_data[close_col].pct_change().iloc[-1] * 100
            volatility = market_data[close_col].pct_change().rolling(20).std().iloc[-1] * 100
            volume_change = market_data[volume_col].pct_change().iloc[-1] * 100
            
            # Generar noticias basadas en movimientos
            if price_change > 5:
                news.append("Bitcoin experimenta fuerte rally debido a adopción institucional")
                news.append("Optimismo en el mercado impulsa las criptomonedas al alza")
            elif price_change < -5:
                news.append("Caída en Bitcoin causada por preocupaciones regulatorias")
                news.append("Pánico en el mercado provoca liquidaciones masivas")
            else:
                news.append("Bitcoin mantiene estabilidad en medio de incertidumbre")
            
            if volatility > 3:
                news.append("Alta volatilidad en el mercado genera oportunidades de trading")
                news.append("Fluctuaciones extremas reflejan sentimiento mixto del mercado")
            
            if volume_change > 50:
                news.append("Volumen de trading aumenta significativamente")
                news.append("Actividad institucional impulsa el volumen de transacciones")
            elif volume_change < -30:
                news.append("Disminución en volumen sugiere consolidación del mercado")
            
            # Agregar noticias genéricas del contexto cripto
            news.extend([
                "La Fed mantiene tasas de interés afectando activos de riesgo",
                "Desarrollos en DeFi continúan atrayendo inversión",
                "Regulación de criptomonedas sigue siendo tema de debate",
                "Adopción de blockchain crece en sectores tradicionales"
            ])
            
            return news[:10]  # Limitar a 10 noticias
            
        except Exception as e:
            logger.error(f"Error generando noticias basadas en mercado: {str(e)}")
            return ["Análisis de mercado en progreso"]
    
    def _generate_market_narrative(self, causal_graph: pd.DataFrame, market_data: pd.DataFrame) -> str:
        """
        Genera una narrativa del mercado basada en el grafo causal.
        
        Args:
            causal_graph: DataFrame con relaciones causales
            market_data: DataFrame con datos de mercado
            
        Returns:
            Narrativa textual del mercado
        """
        try:
            if len(causal_graph) == 0:
                return "Mercado en estado neutral sin factores causales dominantes"
            
            # Obtener la relación más fuerte
            strongest_relation = causal_graph.loc[causal_graph['weight'].idxmax()]
            
            # Calcular cambio de precio reciente
            close_col = 'Close' if 'Close' in market_data.columns else 'close'
            price_change = market_data[close_col].pct_change().iloc[-1] * 100
            
            # Generar narrativa
            sentiment_desc = "positivo" if strongest_relation['avg_sentiment'] > 0 else "negativo"
            price_desc = "al alza" if price_change > 0 else "a la baja"
            
            narrative = f"El mercado muestra tendencia {price_desc} con sentimiento {sentiment_desc}. "
            narrative += f"La relación causal dominante es {strongest_relation['entity1']} -> {strongest_relation['entity2']} "
            narrative += f"con fuerza {strongest_relation['weight']}. "
            narrative += f"Se identificaron {len(causal_graph)} relaciones causales activas."
            
            return narrative
            
        except Exception as e:
            logger.error(f"Error generando narrativa: {str(e)}")
            return "Narrativa del mercado no disponible"

    def analyze_news_corpus(self, news_file_path: str) -> pd.DataFrame:
        """
        Analiza un corpus de noticias desde un archivo JSON.
        
        Args:
            news_file_path: Ruta al archivo JSON con noticias
            
        Returns:
            DataFrame con el grafo causal generado
        """
        try:
            logger.info(f"Analizando corpus de noticias: {news_file_path}")
            
            # Cargar noticias
            with open(news_file_path, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
            
            # Extraer textos
            texts = []
            if 'articles' in news_data:
                for article in news_data['articles']:
                    title = article.get('title', '')
                    description = article.get('description', '')
                    content = article.get('content', '')
                    
                    # Combinar título, descripción y contenido
                    full_text = f"{title}. {description}. {content}".strip()
                    if full_text and len(full_text) > 10:
                        texts.append(full_text)
            
            logger.info(f"Procesando {len(texts)} artículos de noticias")
            
            # Construir grafo causal
            causal_graph = self.build_causal_graph_lite(texts)
            
            return causal_graph
            
        except Exception as e:
            logger.error(f"Error analizando corpus de noticias: {str(e)}")
            return pd.DataFrame(columns=['entity1', 'entity2', 'weight', 'avg_sentiment'])

def main():
    """Función principal para probar el cartógrafo causal."""
    cartographer = CausalCartographer()
    
    # Ejemplo de uso con noticias de muestra
    sample_news = [
        "Bitcoin sube debido a la adopción institucional de Tesla",
        "La Fed aumenta las tasas de interés causando pánico en crypto",
        "Ethereum se beneficia del crecimiento de DeFi y NFTs",
        "El halving de Bitcoin impulsa el optimismo del mercado",
        "Regulación de la SEC provoca caída en altcoins",
        "La inflación lleva a más inversión en criptomonedas",
        "El hack de un exchange desencadena volatilidad en el mercado"
    ]
    
    logger.info("Ejecutando ejemplo del Cartógrafo Causal...")
    causal_graph = cartographer.build_causal_graph_lite(sample_news)
    
    print("\n=== GRAFO CAUSAL GENERADO ===")
    print(causal_graph.head(10))
    
    if len(causal_graph) > 0:
        print(f"\n=== ESTADÍSTICAS ===")
        print(f"Total de relaciones: {len(causal_graph)}")
        print(f"Entidades únicas: {len(set(causal_graph['entity1'].tolist() + causal_graph['entity2'].tolist()))}")
        print(f"Peso promedio: {causal_graph['weight'].mean():.2f}")
        print(f"Sentimiento promedio: {causal_graph['avg_sentiment'].mean():.2f}")
        
        # Mostrar entidades más influyentes
        print(f"\n=== ENTIDADES MÁS CONECTADAS ===")
        all_entities = causal_graph['entity1'].tolist() + causal_graph['entity2'].tolist()
        entity_counts = Counter(all_entities)
        for entity, count in entity_counts.most_common(5):
            influence = cartographer.get_entity_influence_score(entity, causal_graph)
            print(f"{entity}: {count} conexiones, influencia: {influence:.3f}")

if __name__ == '__main__':
    main()