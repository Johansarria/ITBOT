#!/usr/bin/env python3
"""
Analizador de Correlaciones Multi-Asset para SICAR
==================================================

Analiza correlaciones entre diferentes clases de activos para:
- Optimizar diversificación de portfolio
- Identificar oportunidades de hedging
- Detectar cambios en correlaciones durante crisis
- Generar matrices de correlación dinámicas
- Sugerir combinaciones óptimas de activos

Clases de activos soportadas:
- Criptomonedas
- Forex
- Índices
- Commodities

Año: 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import json
import warnings
warnings.filterwarnings('ignore')

from multi_asset_data_system import MultiAssetDataSystem

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """
    Analizador de correlaciones entre múltiples clases de activos
    """
    
    def __init__(self, config_file: str = None):
        """
        Inicializar analizador de correlaciones
        
        Args:
            config_file: Archivo de configuración multi-asset
        """
        self.data_system = MultiAssetDataSystem(config_file)
        self.config = self.data_system.config
        
        # Cache de datos
        self.price_data = {}
        self.returns_data = {}
        
        # Matrices de correlación
        self.correlation_matrices = {}
        
        # Configuración de análisis
        self.analysis_periods = {
            'short_term': 30,    # 30 días
            'medium_term': 90,   # 3 meses
            'long_term': 252     # 1 año
        }
        
        logger.info("📊 Analizador de Correlaciones Multi-Asset inicializado")
        
    def load_price_data(self, symbols: List[str], interval: str = '1d', 
                       limit: int = 365) -> Dict[str, pd.DataFrame]:
        """
        Cargar datos de precios para múltiples símbolos
        
        Args:
            symbols: Lista de símbolos
            interval: Intervalo de tiempo
            limit: Número de períodos
            
        Returns:
            Diccionario con datos de precios por símbolo
        """
        logger.info(f"📊 Cargando datos de precios para {len(symbols)} símbolos...")
        
        price_data = {}
        
        for symbol in symbols:
            logger.info(f"📈 Cargando {symbol}...")
            
            # Intentar obtener datos
            data = self.data_system.get_multi_asset_data(symbol, interval, limit)
            
            if data is not None and len(data) > 0:
                # Asegurar que tenemos la columna de precio de cierre
                if 'close' in data.columns:
                    price_col = 'close'
                elif 'Close' in data.columns:
                    price_col = 'Close'
                else:
                    logger.warning(f"⚠️ No se encontró columna de precio para {symbol}")
                    continue
                
                # Crear serie de precios con timestamp
                if 'timestamp' in data.columns:
                    price_series = pd.Series(
                        data[price_col].values,
                        index=pd.to_datetime(data['timestamp']),
                        name=symbol
                    )
                else:
                    # Usar índice existente o crear uno
                    price_series = pd.Series(
                        data[price_col].values,
                        index=data.index,
                        name=symbol
                    )
                
                price_data[symbol] = price_series
                logger.info(f"✅ {symbol}: {len(price_series)} datos cargados")
                
            else:
                logger.warning(f"⚠️ No se pudieron cargar datos para {symbol}")
        
        self.price_data = price_data
        logger.info(f"✅ Datos cargados para {len(price_data)} símbolos")
        
        return price_data
        
    def calculate_returns(self, price_data: Dict[str, pd.Series] = None) -> pd.DataFrame:
        """
        Calcular retornos para todos los activos
        
        Args:
            price_data: Datos de precios (opcional, usa self.price_data si no se proporciona)
            
        Returns:
            DataFrame con retornos de todos los activos
        """
        if price_data is None:
            price_data = self.price_data
        
        if not price_data:
            logger.error("❌ No hay datos de precios disponibles")
            return pd.DataFrame()
        
        logger.info("📊 Calculando retornos...")
        
        # Crear DataFrame con todos los precios
        prices_df = pd.DataFrame(price_data)
        
        # Alinear fechas (usar intersección)
        prices_df = prices_df.dropna()
        
        if len(prices_df) < 30:
            logger.warning(f"⚠️ Pocos datos comunes: {len(prices_df)} períodos")
        
        # Calcular retornos logarítmicos
        returns_df = np.log(prices_df / prices_df.shift(1)).dropna()
        
        self.returns_data = returns_df
        logger.info(f"✅ Retornos calculados: {len(returns_df)} períodos, {len(returns_df.columns)} activos")
        
        return returns_df
        
    def calculate_correlation_matrix(self, period: str = 'medium_term', 
                                   method: str = 'pearson') -> pd.DataFrame:
        """
        Calcular matriz de correlación para un período específico
        
        Args:
            period: Período de análisis ('short_term', 'medium_term', 'long_term')
            method: Método de correlación ('pearson', 'spearman', 'kendall')
            
        Returns:
            Matriz de correlación
        """
        if self.returns_data.empty:
            logger.error("❌ No hay datos de retornos disponibles")
            return pd.DataFrame()
        
        # Obtener número de períodos
        periods = self.analysis_periods.get(period, 90)
        
        # Usar los últimos N períodos
        recent_returns = self.returns_data.tail(periods)
        
        if len(recent_returns) < 20:
            logger.warning(f"⚠️ Pocos datos para análisis: {len(recent_returns)} períodos")
        
        # Calcular correlación
        correlation_matrix = recent_returns.corr(method=method)
        
        # Guardar en cache
        self.correlation_matrices[f"{period}_{method}"] = correlation_matrix
        
        logger.info(f"✅ Matriz de correlación calculada ({period}, {method}): "
                   f"{correlation_matrix.shape[0]}x{correlation_matrix.shape[1]}")
        
        return correlation_matrix
        
    def analyze_correlations_by_asset_class(self) -> Dict[str, Dict]:
        """
        Analizar correlaciones agrupadas por clase de activo
        
        Returns:
            Diccionario con análisis por clase de activo
        """
        if self.returns_data.empty:
            logger.error("❌ No hay datos de retornos disponibles")
            return {}
        
        logger.info("📊 Analizando correlaciones por clase de activo...")
        
        # Agrupar símbolos por clase de activo
        asset_classes = {}
        for symbol in self.returns_data.columns:
            asset_class = self.data_system.get_asset_class(symbol)
            if asset_class not in asset_classes:
                asset_classes[asset_class] = []
            asset_classes[asset_class].append(symbol)
        
        analysis_results = {}
        
        for asset_class, symbols in asset_classes.items():
            if len(symbols) < 2:
                continue
                
            logger.info(f"📈 Analizando {asset_class}: {symbols}")
            
            # Datos de retornos para esta clase
            class_returns = self.returns_data[symbols]
            
            # Correlación intra-clase
            intra_correlation = class_returns.corr()
            
            # Estadísticas
            correlations_flat = intra_correlation.values[np.triu_indices_from(intra_correlation.values, k=1)]
            
            analysis_results[asset_class] = {
                'symbols': symbols,
                'count': len(symbols),
                'correlation_matrix': intra_correlation,
                'avg_correlation': np.mean(correlations_flat),
                'max_correlation': np.max(correlations_flat),
                'min_correlation': np.min(correlations_flat),
                'std_correlation': np.std(correlations_flat)
            }
            
            logger.info(f"   • Correlación promedio: {np.mean(correlations_flat):.3f}")
            logger.info(f"   • Rango: [{np.min(correlations_flat):.3f}, {np.max(correlations_flat):.3f}]")
        
        return analysis_results
        
    def find_diversification_opportunities(self, max_correlation: float = 0.3) -> List[Tuple[str, str, float]]:
        """
        Encontrar pares de activos con baja correlación para diversificación
        
        Args:
            max_correlation: Correlación máxima para considerar como diversificación
            
        Returns:
            Lista de tuplas (activo1, activo2, correlación)
        """
        if 'medium_term_pearson' not in self.correlation_matrices:
            self.calculate_correlation_matrix('medium_term', 'pearson')
        
        correlation_matrix = self.correlation_matrices['medium_term_pearson']
        
        if correlation_matrix.empty:
            return []
        
        opportunities = []
        
        # Buscar pares con baja correlación
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                asset1 = correlation_matrix.columns[i]
                asset2 = correlation_matrix.columns[j]
                correlation = correlation_matrix.iloc[i, j]
                
                if abs(correlation) <= max_correlation:
                    opportunities.append((asset1, asset2, correlation))
        
        # Ordenar por correlación absoluta (menor primero)
        opportunities.sort(key=lambda x: abs(x[2]))
        
        logger.info(f"🎯 Encontradas {len(opportunities)} oportunidades de diversificación "
                   f"(correlación ≤ {max_correlation})")
        
        return opportunities
        
    def detect_correlation_changes(self, window_size: int = 30) -> Dict[str, pd.Series]:
        """
        Detectar cambios en correlaciones a lo largo del tiempo
        
        Args:
            window_size: Tamaño de ventana móvil para calcular correlaciones
            
        Returns:
            Diccionario con series temporales de correlaciones
        """
        if self.returns_data.empty:
            logger.error("❌ No hay datos de retornos disponibles")
            return {}
        
        logger.info(f"📊 Detectando cambios en correlaciones (ventana: {window_size} días)...")
        
        rolling_correlations = {}
        symbols = list(self.returns_data.columns)
        
        # Calcular correlaciones móviles para pares importantes
        for i in range(len(symbols)):
            for j in range(i+1, len(symbols)):
                asset1, asset2 = symbols[i], symbols[j]
                pair_name = f"{asset1}_{asset2}"
                
                # Correlación móvil
                rolling_corr = self.returns_data[asset1].rolling(window=window_size).corr(
                    self.returns_data[asset2]
                ).dropna()
                
                if len(rolling_corr) > 0:
                    rolling_correlations[pair_name] = rolling_corr
        
        logger.info(f"✅ Calculadas correlaciones móviles para {len(rolling_correlations)} pares")
        
        return rolling_correlations
        
    def generate_portfolio_suggestions(self, target_assets: int = 5, 
                                     max_correlation: float = 0.4) -> Dict:
        """
        Generar sugerencias de portfolio diversificado
        
        Args:
            target_assets: Número objetivo de activos en el portfolio
            max_correlation: Correlación máxima permitida entre activos
            
        Returns:
            Diccionario con sugerencias de portfolio
        """
        if 'medium_term_pearson' not in self.correlation_matrices:
            self.calculate_correlation_matrix('medium_term', 'pearson')
        
        correlation_matrix = self.correlation_matrices['medium_term_pearson']
        
        if correlation_matrix.empty:
            return {}
        
        logger.info(f"🎯 Generando sugerencias de portfolio ({target_assets} activos, "
                   f"correlación máx: {max_correlation})...")
        
        # Algoritmo greedy para selección de activos
        available_assets = list(correlation_matrix.columns)
        selected_assets = []
        
        # Empezar con el activo que tenga menor correlación promedio
        avg_correlations = {}
        for asset in available_assets:
            correlations = correlation_matrix[asset].drop(asset)  # Excluir autocorrelación
            avg_correlations[asset] = correlations.abs().mean()
        
        # Seleccionar primer activo (menor correlación promedio)
        first_asset = min(avg_correlations, key=avg_correlations.get)
        selected_assets.append(first_asset)
        available_assets.remove(first_asset)
        
        # Seleccionar activos adicionales
        while len(selected_assets) < target_assets and available_assets:
            best_candidate = None
            best_score = float('inf')
            
            for candidate in available_assets:
                # Calcular correlación máxima con activos ya seleccionados
                max_corr_with_selected = 0
                for selected in selected_assets:
                    corr = abs(correlation_matrix.loc[candidate, selected])
                    max_corr_with_selected = max(max_corr_with_selected, corr)
                
                # Si la correlación máxima es aceptable, considerar este candidato
                if max_corr_with_selected <= max_correlation:
                    if max_corr_with_selected < best_score:
                        best_score = max_corr_with_selected
                        best_candidate = candidate
            
            if best_candidate:
                selected_assets.append(best_candidate)
                available_assets.remove(best_candidate)
            else:
                # Si no hay candidatos que cumplan el criterio, tomar el mejor disponible
                if available_assets:
                    remaining_scores = {}
                    for candidate in available_assets:
                        max_corr = 0
                        for selected in selected_assets:
                            corr = abs(correlation_matrix.loc[candidate, selected])
                            max_corr = max(max_corr, corr)
                        remaining_scores[candidate] = max_corr
                    
                    best_remaining = min(remaining_scores, key=remaining_scores.get)
                    selected_assets.append(best_remaining)
                    available_assets.remove(best_remaining)
                else:
                    break
        
        # Calcular estadísticas del portfolio sugerido
        portfolio_correlations = []
        for i in range(len(selected_assets)):
            for j in range(i+1, len(selected_assets)):
                corr = correlation_matrix.loc[selected_assets[i], selected_assets[j]]
                portfolio_correlations.append(abs(corr))
        
        # Agrupar por clase de activo
        asset_class_distribution = {}
        for asset in selected_assets:
            asset_class = self.data_system.get_asset_class(asset)
            asset_class_distribution[asset_class] = asset_class_distribution.get(asset_class, 0) + 1
        
        suggestions = {
            'selected_assets': selected_assets,
            'asset_count': len(selected_assets),
            'avg_correlation': np.mean(portfolio_correlations) if portfolio_correlations else 0,
            'max_correlation': np.max(portfolio_correlations) if portfolio_correlations else 0,
            'asset_class_distribution': asset_class_distribution,
            'diversification_score': 1 - (np.mean(portfolio_correlations) if portfolio_correlations else 0)
        }
        
        logger.info(f"✅ Portfolio sugerido: {selected_assets}")
        logger.info(f"   • Correlación promedio: {suggestions['avg_correlation']:.3f}")
        logger.info(f"   • Score de diversificación: {suggestions['diversification_score']:.3f}")
        
        return suggestions
        
    def plot_correlation_heatmap(self, period: str = 'medium_term', 
                               save_path: str = None) -> None:
        """
        Crear heatmap de correlaciones
        
        Args:
            period: Período de análisis
            save_path: Ruta para guardar el gráfico (opcional)
        """
        if f"{period}_pearson" not in self.correlation_matrices:
            self.calculate_correlation_matrix(period, 'pearson')
        
        correlation_matrix = self.correlation_matrices[f"{period}_pearson"]
        
        if correlation_matrix.empty:
            logger.error("❌ No hay matriz de correlación disponible")
            return
        
        # Crear figura
        plt.figure(figsize=(12, 10))
        
        # Crear heatmap
        mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
        sns.heatmap(
            correlation_matrix,
            mask=mask,
            annot=True,
            cmap='RdYlBu_r',
            center=0,
            square=True,
            fmt='.2f',
            cbar_kws={'label': 'Correlación'}
        )
        
        plt.title(f'Matriz de Correlación - {period.replace("_", " ").title()}')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"📊 Heatmap guardado en: {save_path}")
        
        plt.show()
        
    def generate_correlation_report(self) -> Dict:
        """
        Generar reporte completo de correlaciones
        
        Returns:
            Diccionario con reporte completo
        """
        logger.info("📊 Generando reporte completo de correlaciones...")
        
        # Calcular matrices para diferentes períodos
        for period in self.analysis_periods.keys():
            self.calculate_correlation_matrix(period, 'pearson')
        
        # Análisis por clase de activo
        asset_class_analysis = self.analyze_correlations_by_asset_class()
        
        # Oportunidades de diversificación
        diversification_opportunities = self.find_diversification_opportunities()
        
        # Sugerencias de portfolio
        portfolio_suggestions = self.generate_portfolio_suggestions()
        
        # Compilar reporte
        report = {
            'timestamp': datetime.now().isoformat(),
            'analysis_summary': {
                'total_assets': len(self.returns_data.columns) if not self.returns_data.empty else 0,
                'data_periods': len(self.returns_data) if not self.returns_data.empty else 0,
                'asset_classes': len(asset_class_analysis)
            },
            'correlation_matrices': {
                period: matrix.to_dict() 
                for period, matrix in self.correlation_matrices.items()
            },
            'asset_class_analysis': {
                asset_class: {
                    'symbols': analysis['symbols'],
                    'count': analysis['count'],
                    'avg_correlation': analysis['avg_correlation'],
                    'max_correlation': analysis['max_correlation'],
                    'min_correlation': analysis['min_correlation']
                }
                for asset_class, analysis in asset_class_analysis.items()
            },
            'diversification_opportunities': diversification_opportunities[:10],  # Top 10
            'portfolio_suggestions': portfolio_suggestions
        }
        
        logger.info("✅ Reporte de correlaciones generado")
        
        return report
        
    def save_report(self, report: Dict, filename: str = None) -> str:
        """
        Guardar reporte en archivo JSON
        
        Args:
            report: Reporte a guardar
            filename: Nombre del archivo (opcional)
            
        Returns:
            Ruta del archivo guardado
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"correlation_analysis_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Reporte guardado en: {filename}")
        return filename

def main():
    """Función principal de demostración"""
    print("📊 Iniciando Análisis de Correlaciones Multi-Asset...")
    
    try:
        # Inicializar analizador
        analyzer = CorrelationAnalyzer()
        
        # Obtener símbolos validados
        crypto_symbols = analyzer.data_system.get_validated_symbols('cryptocurrencies')
        
        if not crypto_symbols:
            print("⚠️ No hay símbolos validados disponibles")
            return
        
        # Usar los primeros símbolos para la demo
        test_symbols = crypto_symbols[:5]
        print(f"📊 Analizando correlaciones para: {test_symbols}")
        
        # Cargar datos de precios
        price_data = analyzer.load_price_data(test_symbols, interval='1d', limit=90)
        
        if not price_data:
            print("❌ No se pudieron cargar datos de precios")
            return
        
        # Calcular retornos
        returns_data = analyzer.calculate_returns(price_data)
        
        if returns_data.empty:
            print("❌ No se pudieron calcular retornos")
            return
        
        # Generar reporte completo
        report = analyzer.generate_correlation_report()
        
        # Mostrar resultados principales
        print("\n" + "="*60)
        print("📊 ANÁLISIS DE CORRELACIONES MULTI-ASSET")
        print("="*60)
        
        print(f"\n📈 RESUMEN:")
        print(f"   • Total activos: {report['analysis_summary']['total_assets']}")
        print(f"   • Períodos de datos: {report['analysis_summary']['data_periods']}")
        print(f"   • Clases de activos: {report['analysis_summary']['asset_classes']}")
        
        if 'portfolio_suggestions' in report and report['portfolio_suggestions']:
            suggestions = report['portfolio_suggestions']
            print(f"\n🎯 SUGERENCIAS DE PORTFOLIO:")
            print(f"   • Activos recomendados: {suggestions['selected_assets']}")
            print(f"   • Correlación promedio: {suggestions['avg_correlation']:.3f}")
            print(f"   • Score de diversificación: {suggestions['diversification_score']:.3f}")
        
        if 'diversification_opportunities' in report:
            opportunities = report['diversification_opportunities'][:3]
            print(f"\n🔍 TOP OPORTUNIDADES DE DIVERSIFICACIÓN:")
            for i, (asset1, asset2, corr) in enumerate(opportunities, 1):
                print(f"   {i}. {asset1} - {asset2}: {corr:.3f}")
        
        # Guardar reporte
        filename = analyzer.save_report(report)
        print(f"\n💾 Reporte completo guardado en: {filename}")
        
        print("\n" + "="*60)
        
        return analyzer
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de correlaciones: {e}")
        return None

if __name__ == "__main__":
    analyzer = main()