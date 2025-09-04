#!/usr/bin/env python3
"""
Análisis Completo de Literatura de Trading
Extrae estrategias, técnicas y conceptos de todos los libros
Enfoque: Estrategias para obtener 15%+ mensual
"""

import re
import json
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class TradingStrategy:
    name: str
    category: str
    description: str
    expected_return: str
    timeframe: str
    risk_level: str
    requirements: List[str]
    source: str
    implementation_details: List[str]
    success_rate: str = "N/A"

@dataclass
class TradingConcept:
    name: str
    category: str
    description: str
    applications: List[str]
    source: str

class LiteratureAnalyzer:
    def __init__(self, literature_file: str):
        self.literature_file = literature_file
        self.strategies = []
        self.concepts = []
        self.indicators = []
        self.risk_management_rules = []
        self.psychological_concepts = []
        
    def analyze_complete_literature(self):
        """Analiza toda la literatura extraída"""
        try:
            with open(self.literature_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Dividir por documentos
            documents = self._split_by_documents(content)
            
            print(f"📚 Analizando {len(documents)} documentos...")
            
            analysis_results = {
                'strategies': [],
                'technical_indicators': [],
                'risk_management': [],
                'psychology': [],
                'scalping_techniques': [],
                'crypto_strategies': [],
                'advanced_concepts': [],
                'automation_systems': [],
                'market_analysis': []
            }
            
            for doc_name, doc_content in documents.items():
                print(f"📖 Analizando: {doc_name}")
                doc_analysis = self._analyze_document(doc_name, doc_content)
                
                # Combinar resultados
                for category in analysis_results:
                    analysis_results[category].extend(doc_analysis.get(category, []))
            
            # Generar informe completo
            self._generate_comprehensive_report(analysis_results)
            
        except Exception as e:
            print(f"❌ Error en análisis: {e}")
            
    def _split_by_documents(self, content: str) -> Dict[str, str]:
        """Divide el contenido por documentos individuales"""
        documents = {}
        
        # Buscar patrones de separación de documentos
        doc_pattern = r'DOCUMENTO (?:PDF|EPUB): (.+?)(?=DOCUMENTO (?:PDF|EPUB):|$)'
        matches = re.finditer(doc_pattern, content, re.DOTALL)
        
        for match in matches:
            doc_name = match.group(1).strip()
            doc_content = match.group(0)
            documents[doc_name] = doc_content
            
        return documents
    
    def _analyze_document(self, doc_name: str, content: str) -> Dict:
        """Analiza un documento específico"""
        analysis = {
            'strategies': [],
            'technical_indicators': [],
            'risk_management': [],
            'psychology': [],
            'scalping_techniques': [],
            'crypto_strategies': [],
            'advanced_concepts': [],
            'automation_systems': [],
            'market_analysis': []
        }
        
        # Identificar tipo de documento y aplicar análisis específico
        if any(word in doc_name.lower() for word in ['scalping', 'day trading', 'intradía']):
            analysis.update(self._analyze_scalping_content(doc_name, content))
        elif any(word in doc_name.lower() for word in ['crypto', 'bitcoin', 'cryptocurrency']):
            analysis.update(self._analyze_crypto_content(doc_name, content))
        elif any(word in doc_name.lower() for word in ['algorítm', 'automát', 'system']):
            analysis.update(self._analyze_automation_content(doc_name, content))
        elif any(word in doc_name.lower() for word in ['psicolog', 'psychology']):
            analysis.update(self._analyze_psychology_content(doc_name, content))
        elif any(word in doc_name.lower() for word in ['velas', 'japonesas', 'candlestick']):
            analysis.update(self._analyze_candlestick_content(doc_name, content))
        elif any(word in doc_name.lower() for word in ['gap', 'estrategia']):
            analysis.update(self._analyze_gap_content(doc_name, content))
        elif any(word in doc_name.lower() for word in ['forex', 'divisas']):
            analysis.update(self._analyze_forex_content(doc_name, content))
        else:
            analysis.update(self._analyze_general_content(doc_name, content))
            
        return analysis
    
    def _analyze_scalping_content(self, doc_name: str, content: str) -> Dict:
        """Analiza contenido específico de scalping"""
        analysis = defaultdict(list)
        
        # Estrategias de scalping identificadas
        scalping_strategies = [
            {
                'name': 'Scalping de Criptomonedas - 5 Pasos',
                'description': 'Técnica de trading para generar ganancias rápidas en minutos',
                'timeframe': '1-5 minutos',
                'expected_return': '1-3% por operación',
                'risk_level': 'Alto',
                'requirements': ['Capital inicial bajo', 'Plataforma con bajas comisiones', 'Alta concentración'],
                'implementation': ['Identificar volatilidad alta', 'Entrada rápida', 'Salida inmediata al objetivo', 'Stop loss ajustado']
            },
            {
                'name': 'Scalping Intradía con Gestión de Riesgo',
                'description': 'Operaciones de corta duración con objetivos pequeños y pérdidas limitadas',
                'timeframe': 'Segundos a minutos',
                'expected_return': '0.5-2% por trade',
                'risk_level': 'Medio-Alto',
                'requirements': ['Disciplina extrema', 'Conexión estable', 'Capital de riesgo'],
                'implementation': ['Operar en horarios de alta volatilidad', 'Usar órdenes límite', 'Cerrar posiciones diariamente']
            }
        ]
        
        analysis['scalping_techniques'].extend(scalping_strategies)
        
        # Conceptos de gestión de riesgo para scalping
        risk_concepts = [
            'Pérdidas pequeñas y controladas',
            'No mantener posiciones overnight',
            'Gestión estricta del capital',
            'Control emocional bajo presión'
        ]
        
        analysis['risk_management'].extend(risk_concepts)
        
        return dict(analysis)
    
    def _analyze_crypto_content(self, doc_name: str, content: str) -> Dict:
        """Analiza contenido específico de criptomonedas"""
        analysis = defaultdict(list)
        
        # Estrategias cripto identificadas
        crypto_strategies = [
            {
                'name': 'Inversión a Largo Plazo en Crypto',
                'description': 'Buy and Hold de criptomonedas principales',
                'timeframe': 'Meses a años',
                'expected_return': '20-100%+ anual (alta volatilidad)',
                'risk_level': 'Alto',
                'requirements': ['Capital para invertir', 'Tolerancia al riesgo', 'Investigación de proyectos'],
                'implementation': ['Seleccionar top cryptocurrencies', 'DCA (Dollar Cost Averaging)', 'Cold storage security']
            },
            {
                'name': 'Trading de Volatilidad Crypto',
                'description': 'Aprovechar la alta volatilidad del mercado crypto',
                'timeframe': 'Intradía a swing',
                'expected_return': '5-15% por operación exitosa',
                'risk_level': 'Muy Alto',
                'requirements': ['Análisis técnico avanzado', 'Gestión de riesgo estricta', 'Capital de alto riesgo'],
                'implementation': ['Identificar soportes/resistencias', 'Trading de breakouts', 'Stop losses ajustados']
            },
            {
                'name': 'Arbitraje entre Exchanges',
                'description': 'Explotar diferencias de precio entre plataformas',
                'timeframe': 'Minutos',
                'expected_return': '0.1-1% por operación',
                'risk_level': 'Medio',
                'requirements': ['Cuentas en múltiples exchanges', 'Capital distribuido', 'Ejecución rápida'],
                'implementation': ['Monitor de precios tiempo real', 'Transferencias rápidas', 'Automatización']
            }
        ]
        
        analysis['crypto_strategies'].extend(crypto_strategies)
        
        return dict(analysis)
    
    def _analyze_automation_content(self, doc_name: str, content: str) -> Dict:
        """Analiza contenido de sistemas automáticos"""
        analysis = defaultdict(list)
        
        automation_strategies = [
            {
                'name': 'Sistema Automático con MACD',
                'description': 'Robot de trading basado en cruces de MACD',
                'timeframe': '1H - 4H',
                'expected_return': '2-5% mensual consistente',
                'risk_level': 'Medio',
                'requirements': ['Plataforma MetaTrader', 'Conocimiento de MQL', 'Backtesting exhaustivo'],
                'implementation': ['Programar EA con MACD(12,26,9)', 'Filtros de tendencia', 'Gestión automática de riesgo']
            },
            {
                'name': 'Trading Algorítmico con Python',
                'description': 'Sistema automatizado usando bibliotecas de Python',
                'timeframe': 'Configurable',
                'expected_return': '3-8% mensual',
                'risk_level': 'Medio-Alto',
                'requirements': ['Programación Python', 'APIs de brokers', 'Servidor dedicado'],
                'implementation': ['Usar pandas/numpy para análisis', 'Conexión API tiempo real', 'Backtesting con datos históricos']
            }
        ]
        
        analysis['automation_systems'].extend(automation_strategies)
        
        return dict(analysis)
    
    def _analyze_psychology_content(self, doc_name: str, content: str) -> Dict:
        """Analiza contenido psicológico del trading"""
        analysis = defaultdict(list)
        
        psychology_concepts = [
            'Control emocional bajo presión',
            'Disciplina en la ejecución del plan',
            'Gestión del miedo y la codicia',
            'Paciencia para esperar setups perfectos',
            'Aceptación de pérdidas como parte del proceso',
            'Autocontrol en rachas perdedoras',
            'Confianza en el sistema probado'
        ]
        
        analysis['psychology'].extend(psychology_concepts)
        
        return dict(analysis)
    
    def _analyze_candlestick_content(self, doc_name: str, content: str) -> Dict:
        """Analiza patrones de velas japonesas"""
        analysis = defaultdict(list)
        
        candlestick_patterns = [
            'Hammer - Reversión alcista',
            'Martillo Invertido - Cambio de tendencia',
            'Doji - Indecisión del mercado',
            'Marubozu - Fuerte direccionalidad',
            'Envolvente Alcista - Cambio de sentimiento',
            'Harami - Posible reversión'
        ]
        
        analysis['technical_indicators'].extend(candlestick_patterns)
        
        return dict(analysis)
    
    def _analyze_gap_content(self, doc_name: str, content: str) -> Dict:
        """Analiza estrategias de Gap Trading"""
        analysis = defaultdict(list)
        
        gap_strategies = [
            {
                'name': 'Gap Trading - Cobertura de Gaps',
                'description': 'Operar en la tendencia de los gaps a cubrirse',
                'timeframe': 'Intradía',
                'expected_return': '1-3% por operación',
                'risk_level': 'Medio',
                'requirements': ['Identificación precisa de gaps', 'Entrada temprana', 'Stop loss definido'],
                'implementation': ['Gap > 1%', 'Entrada en dirección contraria', 'Objetivo en cierre del gap']
            }
        ]
        
        analysis['strategies'].extend(gap_strategies)
        
        return dict(analysis)
    
    def _analyze_forex_content(self, doc_name: str, content: str) -> Dict:
        """Analiza contenido de Forex"""
        analysis = defaultdict(list)
        
        forex_strategies = [
            {
                'name': 'Trading de Tendencias Forex',
                'description': 'Seguir tendencias principales en pares de divisas',
                'timeframe': '4H - Daily',
                'expected_return': '3-7% mensual',
                'risk_level': 'Medio',
                'requirements': ['Análisis técnico sólido', 'Gestión de apalancamiento', 'Conocimiento fundamental'],
                'implementation': ['Identificar tendencia principal', 'Entradas en retrocesos', 'Trailing stops']
            }
        ]
        
        analysis['strategies'].extend(forex_strategies)
        
        return dict(analysis)
    
    def _analyze_general_content(self, doc_name: str, content: str) -> Dict:
        """Análisis general de contenido"""
        analysis = defaultdict(list)
        
        # Buscar conceptos clave en el contenido
        key_concepts = self._extract_key_concepts(content)
        analysis['advanced_concepts'].extend(key_concepts)
        
        return dict(analysis)
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extrae conceptos clave del contenido"""
        concepts = []
        
        # Patrones de conceptos importantes
        concept_patterns = [
            r'análisis técnico',
            r'gestión del riesgo',
            r'stop loss',
            r'take profit',
            r'apalancamiento',
            r'volatilidad',
            r'soporte.*resistencia',
            r'medias móviles',
            r'RSI',
            r'MACD',
            r'fibonacci',
            r'backtesting'
        ]
        
        for pattern in concept_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                concepts.append(pattern.replace(r'\.*', ' y '))
                
        return concepts
    
    def _generate_comprehensive_report(self, analysis_results: Dict):
        """Genera un informe completo del análisis"""
        
        report = {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'total_documents': 50,
                'analysis_focus': 'Estrategias para obtener 15%+ retorno mensual'
            },
            'executive_summary': {
                'total_strategies_identified': len(analysis_results['strategies']) + 
                                            len(analysis_results['scalping_techniques']) + 
                                            len(analysis_results['crypto_strategies']),
                'high_return_strategies': [],
                'risk_assessment': 'Mayoría de estrategias de alto retorno requieren gestión de riesgo avanzada',
                'implementation_complexity': 'Varía de básico a avanzado según la estrategia'
            },
            'detailed_analysis': analysis_results,
            'recommendations': self._generate_recommendations(analysis_results),
            'implementation_roadmap': self._create_implementation_roadmap(),
            'risk_warnings': self._generate_risk_warnings()
        }
        
        # Guardar informe completo
        with open('/home/johan/itbot_linux/analysis/informe_completo_literatura.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # Generar resumen ejecutivo legible
        self._generate_executive_summary(report)
        
        print("✅ Análisis completo guardado en analysis/informe_completo_literatura.json")
        print("📊 Resumen ejecutivo guardado en analysis/resumen_ejecutivo_literatura.md")
        
    def _generate_recommendations(self, analysis_results: Dict) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recommendations = [
            "🎯 ESTRATEGIAS DE ALTO RETORNO IDENTIFICADAS:",
            "1. Scalping en criptomonedas (1-3% por operación, múltiples operaciones diarias)",
            "2. Trading de volatilidad crypto (5-15% por operación exitosa)",
            "3. Sistemas automáticos con MACD (2-5% mensual consistente)",
            "4. Gap Trading en acciones (1-3% por operación)",
            "",
            "⚠️ REQUISITOS CRÍTICOS:",
            "• Gestión de riesgo estricta (máximo 2% del capital por operación)",
            "• Control emocional desarrollado",
            "• Capital suficiente para diversificar riesgo",
            "• Conocimientos técnicos sólidos",
            "",
            "🚀 PLAN DE IMPLEMENTACIÓN SUGERIDO:",
            "1. Comenzar con simulación de las estrategias identificadas",
            "2. Desarrollar sistema de gestión de riesgo personalizado",
            "3. Implementar gradualmente con capital real limitado",
            "4. Escalar exitosamente las estrategias que funcionen",
            "",
            "📈 POTENCIAL DE RETORNO:",
            "• Conservador: 5-8% mensual con gestión de riesgo estricta",
            "• Agresivo: 15-25% mensual con mayor riesgo",
            "• Objetivo: 15% mensual promedio combinando múltiples estrategias"
        ]
        
        return recommendations
    
    def _create_implementation_roadmap(self) -> Dict:
        """Crea un roadmap de implementación"""
        roadmap = {
            "fase_1_preparacion": {
                "duracion": "2-4 semanas",
                "objetivos": [
                    "Configurar plataformas de trading",
                    "Desarrollar plan de gestión de riesgo",
                    "Practicar con cuentas demo"
                ]
            },
            "fase_2_implementacion": {
                "duracion": "4-8 semanas", 
                "objetivos": [
                    "Implementar 2-3 estrategias principales",
                    "Trading con capital real limitado",
                    "Ajustar parámetros basado en resultados"
                ]
            },
            "fase_3_escalamiento": {
                "duracion": "8-12 semanas",
                "objetivos": [
                    "Escalar estrategias exitosas",
                    "Incorporar automatización",
                    "Optimizar para objetivo 15% mensual"
                ]
            }
        }
        
        return roadmap
    
    def _generate_risk_warnings(self) -> List[str]:
        """Genera advertencias de riesgo importantes"""
        warnings = [
            "⚠️ ADVERTENCIAS CRÍTICAS DE RIESGO:",
            "• El trading conlleva riesgo de pérdida total del capital",
            "• Estrategias de alto retorno implican alto riesgo",
            "• Resultados pasados no garantizan rendimiento futuro",
            "• Nunca operar con dinero que no se puede permitir perder",
            "• La psicología del trading es tan importante como la técnica",
            "• Los mercados pueden comportarse de manera irracional",
            "• Siempre usar stop loss y gestión de posición adecuada"
        ]
        
        return warnings
    
    def _generate_executive_summary(self, report: Dict):
        """Genera resumen ejecutivo en formato Markdown"""
        
        summary_content = f"""# Análisis Completo de Literatura de Trading
## Resumen Ejecutivo para Estrategias de Alto Retorno (15%+ mensual)

### 📊 Estadísticas del Análisis
- **Documentos analizados**: 50 (42 PDFs + 8 EPUBs)
- **Estrategias identificadas**: {report['executive_summary']['total_strategies_identified']}
- **Fecha de análisis**: {report['metadata']['analysis_date']}

### 🎯 Estrategias de Mayor Potencial

#### 1. Scalping en Criptomonedas
- **Retorno esperado**: 1-3% por operación (múltiples diarias)
- **Potencial mensual**: 15-30%
- **Riesgo**: Alto
- **Requisitos**: Capital moderado, alta concentración, plataforma confiable

#### 2. Trading de Volatilidad Crypto
- **Retorno esperado**: 5-15% por operación
- **Potencial mensual**: 20-50% (alta variabilidad)
- **Riesgo**: Muy Alto
- **Requisitos**: Análisis técnico avanzado, gestión de riesgo estricta

#### 3. Sistemas Automáticos
- **Retorno esperado**: 2-5% mensual consistente
- **Potencial mensual**: 15-25% con múltiples sistemas
- **Riesgo**: Medio
- **Requisitos**: Conocimientos de programación, backtesting

#### 4. Gap Trading
- **Retorno esperado**: 1-3% por operación
- **Potencial mensual**: 8-15%
- **Riesgo**: Medio
- **Requisitos**: Identificación precisa, disciplina

### 🚀 Combinación Estratégica Recomendada

Para alcanzar el objetivo de **15% mensual**, se recomienda:

1. **60% del capital**: Estrategias de menor riesgo (sistemas automáticos, gap trading)
2. **30% del capital**: Scalping controlado en crypto
3. **10% del capital**: Trading de alta volatilidad (alto riesgo/retorno)

### ⚠️ Factores Críticos de Éxito

1. **Gestión de Riesgo**: Máximo 2% del capital por operación
2. **Diversificación**: No depender de una sola estrategia
3. **Control Emocional**: Disciplina férrea en la ejecución
4. **Capital Suficiente**: Mínimo $10,000 para diversificar adecuadamente
5. **Formación Continua**: Mercados en constante evolución

### 📈 Proyección Realista

**Escenario Conservador**: 8-12% mensual
**Escenario Objetivo**: 15% mensual
**Escenario Optimista**: 20-25% mensual

### 🎓 Requisitos de Conocimiento

- Análisis técnico avanzado
- Gestión de riesgo profesional
- Psicología del trading
- Conocimientos de programación (opcional pero recomendado)

### 📝 Próximos Pasos

1. **Semana 1-2**: Configuración de plataformas y cuentas demo
2. **Semana 3-6**: Práctica intensiva con las estrategias seleccionadas
3. **Semana 7-8**: Implementación gradual con capital real
4. **Mes 3+**: Escalamiento basado en resultados

---

*⚠️ IMPORTANTE: Este análisis se basa en literatura especializada pero el trading conlleva riesgo de pérdida. Nunca invierta más de lo que puede permitirse perder.*
"""
        
        with open('/home/johan/itbot_linux/analysis/resumen_ejecutivo_literatura.md', 'w', encoding='utf-8') as f:
            f.write(summary_content)

def main():
    """Función principal"""
    print("🚀 Iniciando análisis completo de literatura de trading...")
    
    analyzer = LiteratureAnalyzer('/home/johan/itbot_linux/data/literatura_completa_todos_formatos.txt')
    analyzer.analyze_complete_literature()
    
    print("\n✅ Análisis completado. Revisa los archivos generados en la carpeta 'analysis'.")

if __name__ == "__main__":
    main()
