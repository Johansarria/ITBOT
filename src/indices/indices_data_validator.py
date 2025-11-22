"""
SICAR Indices Data Validator
Sistema de validación de datos para fuentes de índices (Yahoo Finance/IEX)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from enum import Enum
import warnings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Niveles de validación de datos"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    COMPREHENSIVE = "comprehensive"

class DataQuality(Enum):
    """Calidad de los datos"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    INVALID = "invalid"

@dataclass
class ValidationResult:
    """Resultado de validación de datos"""
    symbol: str
    quality: DataQuality
    score: float
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    data_points: int
    completeness: float
    consistency: float
    accuracy: float
    timeliness: float

class IndicesDataValidator:
    """
    Validador de datos para índices
    Valida calidad, integridad y consistencia de datos de Yahoo Finance/IEX
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.validation_level = validation_level
        self.logger = logging.getLogger(__name__)
        
        # Configuración de validación por nivel
        self.validation_config = {
            ValidationLevel.BASIC: {
                'min_data_points': 50,
                'max_missing_pct': 10.0,
                'min_volume_threshold': 1000,
                'price_change_threshold': 0.20,  # 20%
                'check_duplicates': True,
                'check_outliers': False,
                'check_consistency': False
            },
            ValidationLevel.STANDARD: {
                'min_data_points': 100,
                'max_missing_pct': 5.0,
                'min_volume_threshold': 10000,
                'price_change_threshold': 0.15,  # 15%
                'check_duplicates': True,
                'check_outliers': True,
                'check_consistency': True
            },
            ValidationLevel.STRICT: {
                'min_data_points': 200,
                'max_missing_pct': 2.0,
                'min_volume_threshold': 50000,
                'price_change_threshold': 0.10,  # 10%
                'check_duplicates': True,
                'check_outliers': True,
                'check_consistency': True
            },
            ValidationLevel.COMPREHENSIVE: {
                'min_data_points': 500,
                'max_missing_pct': 1.0,
                'min_volume_threshold': 100000,
                'price_change_threshold': 0.08,  # 8%
                'check_duplicates': True,
                'check_outliers': True,
                'check_consistency': True
            }
        }
        
        # Rangos esperados para índices principales
        self.index_ranges = {
            'SPY': {'min_price': 100, 'max_price': 600, 'typical_volume': 50000000},
            'QQQ': {'min_price': 200, 'max_price': 500, 'typical_volume': 30000000},
            'IWM': {'min_price': 100, 'max_price': 300, 'typical_volume': 20000000},
            'DIA': {'min_price': 200, 'max_price': 400, 'typical_volume': 5000000},
            'VTI': {'min_price': 150, 'max_price': 300, 'typical_volume': 3000000}
        }
    
    def validate_data(self, data: pd.DataFrame, symbol: str) -> ValidationResult:
        """
        Validar datos de un índice
        
        Args:
            data: DataFrame con datos OHLCV
            symbol: Símbolo del índice
            
        Returns:
            ValidationResult con resultados de validación
        """
        try:
            issues = []
            warnings = []
            recommendations = []
            
            # Validaciones básicas
            completeness = self._check_completeness(data, issues, warnings)
            consistency = self._check_consistency(data, symbol, issues, warnings)
            accuracy = self._check_accuracy(data, symbol, issues, warnings)
            timeliness = self._check_timeliness(data, issues, warnings)
            
            # Validaciones específicas según nivel
            config = self.validation_config[self.validation_level]
            
            if config['check_duplicates']:
                self._check_duplicates(data, issues, warnings)
            
            if config['check_outliers']:
                self._check_outliers(data, symbol, issues, warnings)
            
            if config['check_consistency']:
                self._check_price_consistency(data, issues, warnings)
            
            # Calcular score general
            score = (completeness + consistency + accuracy + timeliness) / 4
            
            # Determinar calidad
            quality = self._determine_quality(score, len(issues))
            
            # Generar recomendaciones
            self._generate_recommendations(data, symbol, score, recommendations)
            
            return ValidationResult(
                symbol=symbol,
                quality=quality,
                score=score,
                issues=issues,
                warnings=warnings,
                recommendations=recommendations,
                data_points=len(data),
                completeness=completeness,
                consistency=consistency,
                accuracy=accuracy,
                timeliness=timeliness
            )
            
        except Exception as e:
            self.logger.error(f"Error validando datos para {symbol}: {e}")
            return ValidationResult(
                symbol=symbol,
                quality=DataQuality.INVALID,
                score=0.0,
                issues=[f"Error de validación: {str(e)}"],
                warnings=[],
                recommendations=["Revisar datos de entrada"],
                data_points=0,
                completeness=0.0,
                consistency=0.0,
                accuracy=0.0,
                timeliness=0.0
            )
    
    def _check_completeness(self, data: pd.DataFrame, issues: List[str], warnings: List[str]) -> float:
        """Verificar completitud de datos"""
        config = self.validation_config[self.validation_level]
        
        # Verificar cantidad mínima de datos
        if len(data) < config['min_data_points']:
            issues.append(f"Datos insuficientes: {len(data)} < {config['min_data_points']}")
        
        # Verificar columnas requeridas
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            issues.append(f"Columnas faltantes: {missing_cols}")
        
        # Verificar valores faltantes
        missing_pct = (data[required_cols].isnull().sum().sum() / 
                      (len(data) * len(required_cols))) * 100
        
        if missing_pct > config['max_missing_pct']:
            issues.append(f"Demasiados valores faltantes: {missing_pct:.2f}%")
        elif missing_pct > config['max_missing_pct'] / 2:
            warnings.append(f"Valores faltantes detectados: {missing_pct:.2f}%")
        
        # Score de completitud
        completeness = max(0, 1 - (missing_pct / 100) - 
                          max(0, (config['min_data_points'] - len(data)) / config['min_data_points']))
        
        return completeness
    
    def _check_consistency(self, data: pd.DataFrame, symbol: str, 
                          issues: List[str], warnings: List[str]) -> float:
        """Verificar consistencia de datos"""
        consistency_score = 1.0
        
        if len(data) == 0:
            return 0.0
        
        # Verificar orden cronológico
        if not data.index.is_monotonic_increasing:
            issues.append("Datos no están en orden cronológico")
            consistency_score -= 0.3
        
        # Verificar relaciones OHLC
        invalid_ohlc = (
            (data['High'] < data['Low']) |
            (data['High'] < data['Open']) |
            (data['High'] < data['Close']) |
            (data['Low'] > data['Open']) |
            (data['Low'] > data['Close'])
        ).sum()
        
        if invalid_ohlc > 0:
            issues.append(f"Relaciones OHLC inválidas: {invalid_ohlc} registros")
            consistency_score -= min(0.5, invalid_ohlc / len(data))
        
        # Verificar volumen negativo
        negative_volume = (data['Volume'] < 0).sum()
        if negative_volume > 0:
            issues.append(f"Volumen negativo: {negative_volume} registros")
            consistency_score -= min(0.2, negative_volume / len(data))
        
        # Verificar precios negativos
        negative_prices = (
            (data['Open'] <= 0) | (data['High'] <= 0) | 
            (data['Low'] <= 0) | (data['Close'] <= 0)
        ).sum()
        
        if negative_prices > 0:
            issues.append(f"Precios negativos o cero: {negative_prices} registros")
            consistency_score -= min(0.4, negative_prices / len(data))
        
        return max(0, consistency_score)
    
    def _check_accuracy(self, data: pd.DataFrame, symbol: str, 
                       issues: List[str], warnings: List[str]) -> float:
        """Verificar precisión de datos"""
        accuracy_score = 1.0
        
        if len(data) == 0 or symbol not in self.index_ranges:
            return 0.8  # Score neutro si no hay rangos definidos
        
        ranges = self.index_ranges[symbol]
        
        # Verificar rangos de precios
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if col in data.columns:
                out_of_range = (
                    (data[col] < ranges['min_price']) | 
                    (data[col] > ranges['max_price'])
                ).sum()
                
                if out_of_range > 0:
                    warnings.append(f"{col} fuera de rango esperado: {out_of_range} registros")
                    accuracy_score -= min(0.1, out_of_range / len(data))
        
        # Verificar volumen típico
        if 'Volume' in data.columns:
            avg_volume = data['Volume'].mean()
            expected_volume = ranges['typical_volume']
            
            volume_ratio = avg_volume / expected_volume
            if volume_ratio < 0.1 or volume_ratio > 10:
                warnings.append(f"Volumen atípico: {avg_volume:.0f} vs esperado {expected_volume:.0f}")
                accuracy_score -= 0.1
        
        return max(0, accuracy_score)
    
    def _check_timeliness(self, data: pd.DataFrame, issues: List[str], warnings: List[str]) -> float:
        """Verificar actualidad de datos"""
        if len(data) == 0:
            return 0.0
        
        # Verificar fecha más reciente
        latest_date = data.index.max()
        now = datetime.now()
        
        # Calcular días de retraso
        if isinstance(latest_date, pd.Timestamp):
            days_old = (now - latest_date.to_pydatetime()).days
        else:
            days_old = (now - latest_date).days
        
        if days_old > 7:
            issues.append(f"Datos desactualizados: {days_old} días")
            return max(0, 1 - (days_old / 30))
        elif days_old > 3:
            warnings.append(f"Datos con retraso: {days_old} días")
            return max(0.7, 1 - (days_old / 14))
        
        return 1.0
    
    def _check_duplicates(self, data: pd.DataFrame, issues: List[str], warnings: List[str]):
        """Verificar registros duplicados"""
        duplicates = data.index.duplicated().sum()
        if duplicates > 0:
            issues.append(f"Registros duplicados: {duplicates}")
    
    def _check_outliers(self, data: pd.DataFrame, symbol: str, 
                       issues: List[str], warnings: List[str]):
        """Verificar valores atípicos"""
        config = self.validation_config[self.validation_level]
        
        if 'Close' in data.columns and len(data) > 1:
            # Calcular cambios porcentuales
            returns = data['Close'].pct_change().dropna()
            
            # Detectar cambios extremos
            extreme_changes = (abs(returns) > config['price_change_threshold']).sum()
            
            if extreme_changes > len(returns) * 0.05:  # Más del 5% son extremos
                warnings.append(f"Cambios de precio extremos: {extreme_changes} registros")
    
    def _check_price_consistency(self, data: pd.DataFrame, issues: List[str], warnings: List[str]):
        """Verificar consistencia de precios"""
        if len(data) < 2:
            return
        
        # Verificar gaps excesivos
        if 'Close' in data.columns:
            prev_close = data['Close'].shift(1)
            next_open = data['Open']
            
            gaps = abs((next_open - prev_close) / prev_close).dropna()
            large_gaps = (gaps > 0.05).sum()  # Gaps > 5%
            
            if large_gaps > len(gaps) * 0.02:  # Más del 2% son gaps grandes
                warnings.append(f"Gaps de precio significativos: {large_gaps} registros")
    
    def _determine_quality(self, score: float, issues_count: int) -> DataQuality:
        """Determinar calidad de datos basada en score e issues"""
        if issues_count > 5 or score < 0.3:
            return DataQuality.INVALID
        elif issues_count > 3 or score < 0.5:
            return DataQuality.POOR
        elif issues_count > 1 or score < 0.7:
            return DataQuality.ACCEPTABLE
        elif score < 0.9:
            return DataQuality.GOOD
        else:
            return DataQuality.EXCELLENT
    
    def _generate_recommendations(self, data: pd.DataFrame, symbol: str, 
                                score: float, recommendations: List[str]):
        """Generar recomendaciones de mejora"""
        if score < 0.5:
            recommendations.append("Considerar cambiar fuente de datos")
        
        if len(data) < 200:
            recommendations.append("Obtener más datos históricos")
        
        if 'Volume' in data.columns and data['Volume'].mean() < 10000:
            recommendations.append("Verificar liquidez del instrumento")
        
        missing_pct = data.isnull().sum().sum() / (len(data) * len(data.columns)) * 100
        if missing_pct > 2:
            recommendations.append("Implementar interpolación de datos faltantes")
    
    def validate_multiple_symbols(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, ValidationResult]:
        """
        Validar datos para múltiples símbolos
        
        Args:
            data_dict: Diccionario {symbol: DataFrame}
            
        Returns:
            Diccionario con resultados de validación
        """
        results = {}
        
        for symbol, data in data_dict.items():
            self.logger.info(f"Validando datos para {symbol}")
            results[symbol] = self.validate_data(data, symbol)
        
        return results
    
    def generate_validation_report(self, results: Dict[str, ValidationResult]) -> str:
        """Generar reporte de validación"""
        report = []
        report.append("=" * 60)
        report.append("REPORTE DE VALIDACIÓN DE DATOS - ÍNDICES")
        report.append("=" * 60)
        report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Nivel de validación: {self.validation_level.value}")
        report.append("")
        
        # Resumen general
        total_symbols = len(results)
        quality_counts = {}
        for result in results.values():
            quality = result.quality.value
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
        
        report.append("RESUMEN GENERAL:")
        report.append(f"Total de símbolos validados: {total_symbols}")
        for quality, count in quality_counts.items():
            report.append(f"  {quality.upper()}: {count} ({count/total_symbols*100:.1f}%)")
        report.append("")
        
        # Detalles por símbolo
        report.append("DETALLES POR SÍMBOLO:")
        report.append("-" * 40)
        
        for symbol, result in results.items():
            report.append(f"\n{symbol}:")
            report.append(f"  Calidad: {result.quality.value.upper()}")
            report.append(f"  Score: {result.score:.3f}")
            report.append(f"  Puntos de datos: {result.data_points}")
            report.append(f"  Completitud: {result.completeness:.3f}")
            report.append(f"  Consistencia: {result.consistency:.3f}")
            report.append(f"  Precisión: {result.accuracy:.3f}")
            report.append(f"  Actualidad: {result.timeliness:.3f}")
            
            if result.issues:
                report.append("  Issues:")
                for issue in result.issues:
                    report.append(f"    - {issue}")
            
            if result.warnings:
                report.append("  Warnings:")
                for warning in result.warnings:
                    report.append(f"    - {warning}")
            
            if result.recommendations:
                report.append("  Recomendaciones:")
                for rec in result.recommendations:
                    report.append(f"    - {rec}")
        
        return "\n".join(report)

# Función de utilidad para validación rápida
def quick_validate(data: pd.DataFrame, symbol: str, 
                  level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationResult:
    """Validación rápida de datos"""
    validator = IndicesDataValidator(level)
    return validator.validate_data(data, symbol)