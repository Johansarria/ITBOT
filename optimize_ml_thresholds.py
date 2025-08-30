#!/usr/bin/env python3
"""
Script de optimización de umbrales ML
Analiza el rendimiento histórico y sugiere umbrales óptimos
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def load_prediction_history(days: int = 30) -> pd.DataFrame:
    """Carga el historial de predicciones ML"""
    
    log_file = Path("logs/ml_predictions.jsonl")
    if not log_file.exists():
        raise FileNotFoundError("No se encontraron logs de predicciones ML")
    
    # Cargar predicciones recientes
    cutoff_time = datetime.now() - timedelta(days=days)
    predictions = []
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                pred_time = datetime.fromisoformat(entry['timestamp'])
                if pred_time >= cutoff_time:
                    predictions.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    
    if not predictions:
        raise ValueError(f"No se encontraron predicciones en los últimos {days} días")
    
    df = pd.DataFrame(predictions)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df

def simulate_threshold_performance(df: pd.DataFrame, 
                                 high_threshold: float,
                                 medium_threshold: float) -> Dict:
    """Simula el rendimiento con umbrales específicos"""
    
    results = []
    
    for _, row in df.iterrows():
        buy_prob = row['ml_buy_probability']
        sell_prob = row['ml_sell_probability']
        
        # Aplicar lógica de decisión
        if buy_prob >= high_threshold:
            decision = "COMPRAR"
            confidence = buy_prob
        elif buy_prob >= medium_threshold:
            decision = "COMPRAR_BAJO"
            confidence = buy_prob
        elif sell_prob >= high_threshold:
            decision = "VENDER"
            confidence = sell_prob
        elif sell_prob >= medium_threshold:
            decision = "VENDER_ALTO"
            confidence = sell_prob
        else:
            decision = "MANTENER"
            confidence = max(buy_prob, sell_prob)
        
        results.append({
            'decision': decision,
            'confidence': confidence,
            'buy_prob': buy_prob,
            'sell_prob': sell_prob,
            'max_prob': max(buy_prob, sell_prob)
        })
    
    results_df = pd.DataFrame(results)
    
    # Calcular métricas
    total_predictions = len(results_df)
    decision_counts = results_df['decision'].value_counts()
    
    metrics = {
        'total_predictions': total_predictions,
        'decision_distribution': decision_counts.to_dict(),
        'avg_confidence': results_df['confidence'].mean(),
        'high_confidence_trades': len(results_df[results_df['confidence'] >= high_threshold]),
        'medium_confidence_trades': len(results_df[results_df['confidence'] >= medium_threshold]),
        'inactive_rate': decision_counts.get('MANTENER', 0) / total_predictions,
        'trading_rate': 1 - (decision_counts.get('MANTENER', 0) / total_predictions),
        'strong_signal_rate': (
            decision_counts.get('COMPRAR', 0) + decision_counts.get('VENDER', 0)
        ) / total_predictions,
        'avg_probability_spread': (results_df['buy_prob'] - results_df['sell_prob']).abs().mean()
    }
    
    return metrics

def optimize_thresholds(df: pd.DataFrame) -> Dict:
    """Encuentra los umbrales óptimos usando búsqueda por grilla"""
    
    logger.info("🔍 Optimizando umbrales ML...")
    
    # Rangos de búsqueda
    high_thresholds = np.arange(0.75, 0.95, 0.05)
    medium_thresholds = np.arange(0.55, 0.80, 0.05)
    
    best_score = -1
    best_config = None
    results = []
    
    for high_thresh in high_thresholds:
        for medium_thresh in medium_thresholds:
            if medium_thresh >= high_thresh:
                continue
                
            metrics = simulate_threshold_performance(df, high_thresh, medium_thresh)
            
            # Función de puntuación (personalizable)
            # Favorece alto trading rate con alta confianza
            score = (
                metrics['trading_rate'] * 0.4 +  # Queremos actividad de trading
                metrics['avg_confidence'] * 0.3 +  # Con alta confianza
                metrics['strong_signal_rate'] * 0.2 +  # Preferencia por señales fuertes
                (1 - metrics['inactive_rate']) * 0.1  # Penalizar inactividad excesiva
            )
            
            config = {
                'high_threshold': high_thresh,
                'medium_threshold': medium_thresh,
                'score': score,
                **metrics
            }
            
            results.append(config)
            
            if score > best_score:
                best_score = score
                best_config = config.copy()
    
    # Ordenar resultados por puntuación
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'best_config': best_config,
        'top_configs': results[:5],  # Top 5 configuraciones
        'all_results': results
    }

def analyze_current_performance(df: pd.DataFrame) -> Dict:
    """Analiza el rendimiento con la configuración actual"""
    
    from config import settings
    
    current_high = settings.ML_THRESHOLD_HIGH
    current_medium = settings.ML_THRESHOLD_MEDIUM
    
    logger.info(f"📊 Analizando rendimiento actual: Alto={current_high}, Medio={current_medium}")
    
    current_metrics = simulate_threshold_performance(df, current_high, current_medium)
    current_metrics['high_threshold'] = current_high
    current_metrics['medium_threshold'] = current_medium
    
    return current_metrics

def generate_recommendations(current: Dict, optimized: Dict) -> List[str]:
    """Genera recomendaciones basadas en el análisis"""
    
    recommendations = []
    current_score = current.get('avg_confidence', 0) * current.get('trading_rate', 0)
    best_score = optimized['best_config']['score']
    
    improvement = ((best_score - current_score) / current_score * 100) if current_score > 0 else 0
    
    if improvement > 10:
        recommendations.append(
            f"🚀 MEJORA SIGNIFICATIVA POSIBLE: {improvement:.1f}% mejor rendimiento"
        )
        recommendations.append(
            f"   Cambiar umbrales: Alto {optimized['best_config']['high_threshold']:.2f}, "
            f"Medio {optimized['best_config']['medium_threshold']:.2f}"
        )
    elif improvement > 5:
        recommendations.append(
            f"⚡ MEJORA MODERADA POSIBLE: {improvement:.1f}% mejor rendimiento"
        )
    else:
        recommendations.append("✅ Configuración actual es óptima o casi óptima")
    
    # Análisis específico
    if current['inactive_rate'] > 0.8:
        recommendations.append("⚠️ ALTA INACTIVIDAD: Considerar reducir umbrales para más trading")
    
    if current['avg_confidence'] < 0.6:
        recommendations.append("⚠️ BAJA CONFIANZA: Considerar aumentar umbrales para mayor calidad de señales")
    
    if current['trading_rate'] < 0.2:
        recommendations.append("⚠️ BAJA ACTIVIDAD DE TRADING: Umbrales muy altos pueden limitar oportunidades")
    
    return recommendations

def main():
    """Función principal"""
    
    parser = argparse.ArgumentParser(description="Optimización de umbrales ML")
    parser.add_argument("--days", type=int, default=30, help="Días de historial a analizar")
    parser.add_argument("--save", action="store_true", help="Guardar configuración optimizada")
    parser.add_argument("--export", type=str, help="Exportar resultados a archivo JSON")
    
    args = parser.parse_args()
    
    try:
        logger.info("🚀 Iniciando optimización de umbrales ML")
        
        # Cargar datos históricos
        df = load_prediction_history(days=args.days)
        logger.info(f"📊 Cargadas {len(df)} predicciones de los últimos {args.days} días")
        
        # Analizar rendimiento actual
        current_performance = analyze_current_performance(df)
        
        # Optimizar umbrales
        optimization_results = optimize_thresholds(df)
        best_config = optimization_results['best_config']
        
        # Generar recomendaciones
        recommendations = generate_recommendations(current_performance, optimization_results)
        
        # Mostrar resultados
        print("\n" + "="*60)
        print("📊 ANÁLISIS DE UMBRALES ML")
        print("="*60)
        
        print(f"\n🔧 CONFIGURACIÓN ACTUAL:")
        print(f"   Alto: {current_performance['high_threshold']:.2f}")
        print(f"   Medio: {current_performance['medium_threshold']:.2f}")
        print(f"   Trading Rate: {current_performance['trading_rate']:.1%}")
        print(f"   Confianza Promedio: {current_performance['avg_confidence']:.3f}")
        print(f"   Inactividad: {current_performance['inactive_rate']:.1%}")
        
        print(f"\n🎯 CONFIGURACIÓN ÓPTIMA:")
        print(f"   Alto: {best_config['high_threshold']:.2f}")
        print(f"   Medio: {best_config['medium_threshold']:.2f}")
        print(f"   Trading Rate: {best_config['trading_rate']:.1%}")
        print(f"   Confianza Promedio: {best_config['avg_confidence']:.3f}")
        print(f"   Puntuación: {best_config['score']:.3f}")
        
        print(f"\n💡 RECOMENDACIONES:")
        for rec in recommendations:
            print(f"   {rec}")
        
        print(f"\n📈 TOP 5 CONFIGURACIONES:")
        for i, config in enumerate(optimization_results['top_configs'], 1):
            print(f"   {i}. Alto={config['high_threshold']:.2f}, Medio={config['medium_threshold']:.2f}, "
                  f"Score={config['score']:.3f}, Trading={config['trading_rate']:.1%}")
        
        # Exportar resultados si se solicita
        if args.export:
            with open(args.export, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'analysis_period_days': args.days,
                    'current_performance': current_performance,
                    'optimization_results': optimization_results,
                    'recommendations': recommendations
                }, f, indent=2)
            logger.info(f"📄 Resultados exportados a {args.export}")
        
        # Guardar configuración optimizada si se solicita
        if args.save:
            config_file = Path("config.py")
            if config_file.exists():
                # Leer archivo actual
                with open(config_file, 'r') as f:
                    content = f.read()
                
                # Actualizar umbrales
                new_content = content.replace(
                    f"ML_THRESHOLD_HIGH: float = {current_performance['high_threshold']}",
                    f"ML_THRESHOLD_HIGH: float = {best_config['high_threshold']:.2f}"
                ).replace(
                    f"ML_THRESHOLD_MEDIUM: float = {current_performance['medium_threshold']}",
                    f"ML_THRESHOLD_MEDIUM: float = {best_config['medium_threshold']:.2f}"
                )
                
                # Crear backup
                backup_file = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                with open(backup_file, 'w') as f:
                    f.write(content)
                
                # Guardar nueva configuración
                with open(config_file, 'w') as f:
                    f.write(new_content)
                
                logger.info(f"💾 Configuración actualizada (backup: {backup_file})")
            else:
                logger.warning("No se encontró archivo config.py para actualizar")
        
        logger.info("✅ Optimización completada")
        
    except Exception as e:
        logger.error(f"❌ Error durante la optimización: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
