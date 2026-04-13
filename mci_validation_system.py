#!/usr/bin/env python3
"""
Sistema de Validación del Índice de Condiciones de Mercado (MCI)
Validación aislada del MCI vs métodos alternativos de detección de régimen

Autor: Sistema de Trading Cuantitativo
Fecha: 2024
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import yfinance as yf
from hmmlearn import hmm
import talib

warnings.filterwarnings('ignore')

@dataclass
class RegimeLabel:
    """Estructura para etiquetas manuales de régimen"""
    start_date: str
    end_date: str
    regime: str  # 'tendencia', 'rango', 'whipsaw'
    confidence: float  # 0.0 a 1.0
    notes: str = ""

class MCICalculator:
    """Calculadora del Índice de Condiciones de Mercado (MCI)"""
    
    def __init__(self, adx_period: int = 14, bb_period: int = 20, atr_period: int = 14):
        self.adx_period = adx_period
        self.bb_period = bb_period
        self.atr_period = atr_period
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calcula el Average Directional Index (ADX)"""
        return talib.ADX(high.values, low.values, close.values, timeperiod=self.adx_period)
    
    def calculate_bb_width(self, close: pd.Series) -> pd.Series:
        """Calcula el ancho normalizado de las Bandas de Bollinger"""
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            close.values, timeperiod=self.bb_period, nbdevup=2, nbdevdn=2
        )
        bb_width = (bb_upper - bb_lower) / bb_middle
        return pd.Series(bb_width, index=close.index)
    
    def calculate_atr_normalized(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calcula el ATR normalizado por el precio"""
        atr = talib.ATR(high.values, low.values, close.values, timeperiod=self.atr_period)
        atr_normalized = atr / close.values
        return pd.Series(atr_normalized, index=close.index)
    
    def calculate_mci(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calcula el MCI completo"""
        adx = self.calculate_adx(high, low, close)
        bb_width = self.calculate_bb_width(close)
        atr_norm = self.calculate_atr_normalized(high, low, close)
        
        # Normalizar componentes a escala 0-100
        adx_norm = pd.Series(adx, index=close.index)
        bb_width_norm = (bb_width - bb_width.min()) / (bb_width.max() - bb_width.min()) * 100
        atr_norm_scaled = (atr_norm - atr_norm.min()) / (atr_norm.max() - atr_norm.min()) * 100
        
        # MCI = promedio ponderado de los componentes
        mci = (adx_norm * 0.5 + bb_width_norm * 0.3 + atr_norm_scaled * 0.2)
        return mci.fillna(0)

class SimpleATRRegimeDetector:
    """Detector de régimen simple basado en ATR"""
    
    def __init__(self, atr_period: int = 14, volatility_threshold: float = 0.02):
        self.atr_period = atr_period
        self.volatility_threshold = volatility_threshold
    
    def detect_regime(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Detecta régimen basado en volatilidad ATR"""
        atr = talib.ATR(high.values, low.values, close.values, timeperiod=self.atr_period)
        atr_normalized = atr / close.values
        
        # Clasificación simple basada en volatilidad
        regime = pd.Series(index=close.index, dtype=str)
        
        for i in range(len(atr_normalized)):
            if pd.isna(atr_normalized[i]):
                regime.iloc[i] = 'rango'
            elif atr_normalized[i] > self.volatility_threshold * 1.5:
                regime.iloc[i] = 'whipsaw'
            elif atr_normalized[i] > self.volatility_threshold:
                regime.iloc[i] = 'tendencia'
            else:
                regime.iloc[i] = 'rango'
        
        return regime

class HMMRegimeDetector:
    """Detector de régimen usando Hidden Markov Models"""
    
    def __init__(self, n_components: int = 3, random_state: int = 42):
        self.n_components = n_components
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
    
    def prepare_features(self, high: pd.Series, low: pd.Series, close: pd.Series) -> np.ndarray:
        """Prepara características para el modelo HMM"""
        returns = close.pct_change().fillna(0)
        volatility = returns.rolling(window=20).std().fillna(0)
        
        # ATR normalizado
        atr = talib.ATR(high.values, low.values, close.values, timeperiod=14)
        atr_norm = atr / close.values
        atr_norm = pd.Series(atr_norm, index=close.index).fillna(0)
        
        # Combinar características
        features = np.column_stack([returns.values, volatility.values, atr_norm.values])
        return self.scaler.fit_transform(features)
    
    def fit_and_predict(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Entrena el modelo HMM y predice regímenes"""
        features = self.prepare_features(high, low, close)
        
        # Entrenar modelo HMM
        self.model = hmm.GaussianHMM(
            n_components=self.n_components,
            covariance_type="full",
            random_state=self.random_state,
            n_iter=100
        )
        
        self.model.fit(features)
        states = self.model.predict(features)
        
        # Mapear estados a regímenes
        regime_mapping = self._map_states_to_regimes(states, features)
        regime_labels = [regime_mapping[state] for state in states]
        
        return pd.Series(regime_labels, index=close.index)
    
    def _map_states_to_regimes(self, states: np.ndarray, features: np.ndarray) -> Dict[int, str]:
        """Mapea estados HMM a regímenes interpretables"""
        state_stats = {}
        
        for state in range(self.n_components):
            mask = states == state
            if np.sum(mask) > 0:
                volatility_mean = np.mean(features[mask, 1])  # Volatilidad promedio
                returns_std = np.std(features[mask, 0])       # Variabilidad de retornos
                state_stats[state] = (volatility_mean, returns_std)
        
        # Ordenar estados por volatilidad
        sorted_states = sorted(state_stats.items(), key=lambda x: x[1][0])
        
        mapping = {}
        if len(sorted_states) >= 3:
            mapping[sorted_states[0][0]] = 'rango'      # Baja volatilidad
            mapping[sorted_states[1][0]] = 'tendencia'  # Volatilidad media
            mapping[sorted_states[2][0]] = 'whipsaw'    # Alta volatilidad
        elif len(sorted_states) == 2:
            mapping[sorted_states[0][0]] = 'rango'
            mapping[sorted_states[1][0]] = 'tendencia'
        else:
            mapping[sorted_states[0][0]] = 'rango'
        
        return mapping

class ManualRegimeLabelingSystem:
    """Sistema de etiquetado manual de regímenes históricos"""
    
    def __init__(self):
        self.labels: List[RegimeLabel] = []
    
    def add_label(self, start_date: str, end_date: str, regime: str, 
                  confidence: float = 1.0, notes: str = ""):
        """Añade una etiqueta manual de régimen"""
        if regime not in ['tendencia', 'rango', 'whipsaw']:
            raise ValueError("Régimen debe ser 'tendencia', 'rango' o 'whipsaw'")
        
        label = RegimeLabel(start_date, end_date, regime, confidence, notes)
        self.labels.append(label)
    
    def load_predefined_labels_btc(self):
        """Carga etiquetas predefinidas para BTC (ejemplos históricos)"""
        # Etiquetas para 2024 (período actual)
        self.add_label("2024-01-01", "2024-02-15", "tendencia", 0.9, "Rally inicio año ETF")
        self.add_label("2024-02-16", "2024-03-31", "whipsaw", 0.8, "Volatilidad post-halving")
        self.add_label("2024-04-01", "2024-05-15", "rango", 0.85, "Consolidación pre-halving")
        self.add_label("2024-05-16", "2024-07-31", "tendencia", 0.9, "Rally post-halving")
        self.add_label("2024-08-01", "2024-09-30", "rango", 0.8, "Consolidación verano")
        self.add_label("2024-10-01", "2024-12-31", "tendencia", 0.95, "Rally elecciones US")
        
        # Etiquetas adicionales para 2023 (datos históricos)
        self.add_label("2023-01-01", "2023-02-15", "rango", 0.9, "Consolidación post-FTX")
        self.add_label("2023-02-16", "2023-04-10", "tendencia", 0.95, "Rally alcista Q1")
        self.add_label("2023-04-11", "2023-05-30", "whipsaw", 0.8, "Volatilidad regulatoria")
        self.add_label("2023-06-01", "2023-07-15", "rango", 0.85, "Consolidación verano")
        self.add_label("2023-10-01", "2023-12-31", "tendencia", 0.9, "Rally ETF Bitcoin")
        
    def get_regime_for_date(self, date: pd.Timestamp) -> Optional[str]:
        """Obtiene el régimen etiquetado para una fecha específica"""
        # Asegurar que la fecha sea naive (sin timezone)
        if hasattr(date, 'tz') and date.tz is not None:
            date = date.tz_localize(None)
        elif hasattr(date, 'tzinfo') and date.tzinfo is not None:
            date = date.replace(tzinfo=None)
        
        for label in self.labels:
            start = pd.to_datetime(label.start_date).tz_localize(None)
            end = pd.to_datetime(label.end_date).tz_localize(None)
            if start <= date <= end:
                return label.regime
        return None
    
    def create_regime_series(self, date_index: pd.DatetimeIndex) -> pd.Series:
        """Crea una serie de regímenes para un índice de fechas"""
        # Crear una copia del índice sin timezone para comparaciones
        date_index_naive = date_index.copy()
        if date_index_naive.tz is not None:
            date_index_naive = date_index_naive.tz_localize(None)
        
        # Crear serie con el índice original (manteniendo timezone si existe)
        regime_series = pd.Series(index=date_index, dtype=str)
        
        for i, date in enumerate(date_index_naive):
            regime = self.get_regime_for_date(date)
            regime_series.iloc[i] = regime if regime else 'unknown'
        
        return regime_series

class MCIValidationSystem:
    """Sistema principal de validación del MCI"""
    
    def __init__(self):
        self.mci_calc = MCICalculator()
        self.atr_detector = SimpleATRRegimeDetector()
        self.hmm_detector = HMMRegimeDetector()
        self.labeling_system = ManualRegimeLabelingSystem()
        self.results = {}
    
    def load_market_data(self, symbol: str = "BTC-USD", period: str = "1y") -> pd.DataFrame:
        """Carga datos de mercado"""
        print(f"Cargando datos para {symbol}...")
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        return data
    
    def run_validation(self, symbol: str = "BTC-USD", period: str = "1y"):
        """Ejecuta la validación completa del MCI"""
        print("=== INICIANDO VALIDACIÓN DEL MCI ===")
        
        # 1. Cargar datos
        data = self.load_market_data(symbol, period)
        print(f"Datos cargados: {len(data)} registros")
        
        # 2. Cargar etiquetas manuales
        print(f"Rango de fechas en datos: {data.index.min()} a {data.index.max()}")
        self.labeling_system.load_predefined_labels_btc()
        manual_regimes = self.labeling_system.create_regime_series(data.index)
        
        # Debug: mostrar cuántas etiquetas válidas tenemos
        valid_labels = manual_regimes[manual_regimes != 'unknown']
        print(f"Etiquetas válidas encontradas: {len(valid_labels)}")
        if len(valid_labels) > 0:
            print(f"Rango de etiquetas: {valid_labels.index.min()} a {valid_labels.index.max()}")
            print(f"Distribución de regímenes: {valid_labels.value_counts().to_dict()}")
        
        # 3. Calcular MCI
        print("Calculando MCI...")
        mci_values = self.mci_calc.calculate_mci(data['High'], data['Low'], data['Close'])
        mci_regimes = self._mci_to_regime(mci_values)
        
        # 4. Detector ATR simple
        print("Ejecutando detector ATR...")
        atr_regimes = self.atr_detector.detect_regime(data['High'], data['Low'], data['Close'])
        
        # 5. Detector HMM
        print("Ejecutando detector HMM...")
        hmm_regimes = self.hmm_detector.fit_and_predict(data['High'], data['Low'], data['Close'])
        
        # 6. Alinear todos los índices y filtrar solo fechas con etiquetas manuales
        # Encontrar índice común
        common_index = manual_regimes.index.intersection(mci_regimes.index)
        common_index = common_index.intersection(atr_regimes.index)
        common_index = common_index.intersection(hmm_regimes.index)
        
        # Realinear todas las series al índice común
        manual_aligned = manual_regimes.reindex(common_index)
        mci_aligned = mci_regimes.reindex(common_index)
        atr_aligned = atr_regimes.reindex(common_index)
        hmm_aligned = hmm_regimes.reindex(common_index)
        
        # Filtrar solo fechas con etiquetas manuales válidas
        valid_mask = manual_aligned != 'unknown'
        
        if valid_mask.sum() == 0:
            print("⚠️ No hay etiquetas manuales válidas para el período")
            return
        
        manual_filtered = manual_aligned[valid_mask]
        mci_filtered = mci_aligned[valid_mask]
        atr_filtered = atr_aligned[valid_mask]
        hmm_filtered = hmm_aligned[valid_mask]
        
        # 7. Calcular métricas
        self.results = {
            'manual': manual_filtered,
            'mci': mci_filtered,
            'atr': atr_filtered,
            'hmm': hmm_filtered,
            'mci_values': mci_values,
            'data': data
        }
        
        self._calculate_metrics()
        self._generate_report()
    
    def _mci_to_regime(self, mci_values: pd.Series) -> pd.Series:
        """Convierte valores MCI a clasificaciones de régimen"""
        regime = pd.Series(index=mci_values.index, dtype=str)
        
        for i, value in enumerate(mci_values):
            if pd.isna(value):
                regime.iloc[i] = 'rango'
            elif value > 70:
                regime.iloc[i] = 'tendencia'
            elif value < 30:
                regime.iloc[i] = 'rango'
            else:
                regime.iloc[i] = 'whipsaw'
        
        return regime
    
    def _calculate_metrics(self):
        """Calcula métricas de precisión para todos los métodos"""
        manual = self.results['manual']
        
        methods = ['mci', 'atr', 'hmm']
        metrics = {}
        
        for method in methods:
            predicted = self.results[method]
            
            # Asegurar mismo índice
            common_idx = manual.index.intersection(predicted.index)
            manual_common = manual[common_idx]
            predicted_common = predicted[common_idx]
            
            if len(manual_common) > 0:
                accuracy = accuracy_score(manual_common, predicted_common)
                report = classification_report(manual_common, predicted_common, 
                                             output_dict=True, zero_division=0)
                cm = confusion_matrix(manual_common, predicted_common, 
                                    labels=['tendencia', 'rango', 'whipsaw'])
                
                metrics[method] = {
                    'accuracy': accuracy,
                    'classification_report': report,
                    'confusion_matrix': cm
                }
        
        self.results['metrics'] = metrics
    
    def _generate_report(self):
        """Genera reporte completo de validación"""
        print("\n=== REPORTE DE VALIDACIÓN DEL MCI ===")
        
        metrics = self.results['metrics']
        
        print("\n📊 PRECISIÓN GENERAL:")
        for method, data in metrics.items():
            print(f"{method.upper()}: {data['accuracy']:.3f} ({data['accuracy']*100:.1f}%)")
        
        print("\n📈 ANÁLISIS COMPARATIVO:")
        accuracies = {method: data['accuracy'] for method, data in metrics.items()}
        best_method = max(accuracies, key=accuracies.get)
        worst_method = min(accuracies, key=accuracies.get)
        
        print(f"🥇 Mejor método: {best_method.upper()} ({accuracies[best_method]:.3f})")
        print(f"🥉 Peor método: {worst_method.upper()} ({accuracies[worst_method]:.3f})")
        
        improvement = accuracies[best_method] - accuracies['mci']
        if improvement > 0:
            print(f"⚠️ MCI está {improvement:.3f} puntos por debajo del mejor método")
        else:
            print(f"✅ MCI es el mejor método o está muy cerca")
        
        # Análisis detallado por régimen
        print("\n🎯 PRECISIÓN POR RÉGIMEN:")
        for method, data in metrics.items():
            print(f"\n{method.upper()}:")
            report = data['classification_report']
            for regime in ['tendencia', 'rango', 'whipsaw']:
                if regime in report:
                    precision = report[regime]['precision']
                    recall = report[regime]['recall']
                    f1 = report[regime]['f1-score']
                    print(f"  {regime}: P={precision:.3f}, R={recall:.3f}, F1={f1:.3f}")
        
        self._plot_results()
    
    def _plot_results(self):
        """Genera visualizaciones de los resultados"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Validación del MCI - Resultados Comparativos', fontsize=16)
        
        # 1. Gráfico de precisión
        methods = list(self.results['metrics'].keys())
        accuracies = [self.results['metrics'][m]['accuracy'] for m in methods]
        
        axes[0, 0].bar(methods, accuracies, color=['blue', 'green', 'red'])
        axes[0, 0].set_title('Precisión General por Método')
        axes[0, 0].set_ylabel('Precisión')
        axes[0, 0].set_ylim(0, 1)
        
        for i, acc in enumerate(accuracies):
            axes[0, 0].text(i, acc + 0.01, f'{acc:.3f}', ha='center')
        
        # 2. Matriz de confusión MCI
        cm_mci = self.results['metrics']['mci']['confusion_matrix']
        sns.heatmap(cm_mci, annot=True, fmt='d', 
                   xticklabels=['tendencia', 'rango', 'whipsaw'],
                   yticklabels=['tendencia', 'rango', 'whipsaw'],
                   ax=axes[0, 1], cmap='Blues')
        axes[0, 1].set_title('Matriz de Confusión - MCI')
        
        # 3. Serie temporal MCI
        mci_values = self.results['mci_values']
        axes[1, 0].plot(mci_values.index, mci_values.values, label='MCI', color='blue')
        axes[1, 0].axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Umbral Alto')
        axes[1, 0].axhline(y=30, color='green', linestyle='--', alpha=0.7, label='Umbral Bajo')
        axes[1, 0].set_title('Evolución del MCI')
        axes[1, 0].set_ylabel('Valor MCI')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Comparación F1-Score por régimen
        regimes = ['tendencia', 'rango', 'whipsaw']
        x = np.arange(len(regimes))
        width = 0.25
        
        for i, method in enumerate(methods):
            f1_scores = []
            for regime in regimes:
                report = self.results['metrics'][method]['classification_report']
                f1 = report.get(regime, {}).get('f1-score', 0)
                f1_scores.append(f1)
            
            axes[1, 1].bar(x + i*width, f1_scores, width, label=method.upper())
        
        axes[1, 1].set_title('F1-Score por Régimen')
        axes[1, 1].set_ylabel('F1-Score')
        axes[1, 1].set_xticks(x + width)
        axes[1, 1].set_xticklabels(regimes)
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('mci_validation_results.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("\n📊 Gráficos guardados como 'mci_validation_results.png'")

def main():
    """Función principal"""
    print("🚀 Sistema de Validación del MCI")
    print("Validando efectividad del Índice de Condiciones de Mercado\n")
    
    validator = MCIValidationSystem()
    
    try:
        # Ejecutar validación con datos de Bitcoin
        validator.run_validation(symbol="BTC-USD", period="1y")
        
        print("\n✅ Validación completada exitosamente")
        print("\n🎯 CONCLUSIONES CLAVE:")
        print("1. Revisar si MCI supera métodos más simples")
        print("2. Evaluar si la complejidad está justificada")
        print("3. Considerar ajustes en umbrales o componentes")
        print("4. Validar en diferentes períodos y activos")
        
    except Exception as e:
        print(f"❌ Error durante la validación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()