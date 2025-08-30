"""
Sistema de monitoreo para el modelo ML
Registra predicciones, decisiones y métricas de rendimiento
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import pandas as pd

logger = logging.getLogger(__name__)

class MLMonitor:
    """Monitor de rendimiento del modelo ML"""
    
    def __init__(self, log_file: str = "logs/ml_predictions.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        
    def log_prediction(self, 
                      symbol: str,
                      timestamp: str,
                      buy_prob: float,
                      sell_prob: float,
                      decision: str,
                      score: float,
                      price: float,
                      indicators: Optional[Dict] = None) -> None:
        """Registra una predicción ML"""
        
        log_entry = {
            "timestamp": timestamp,
            "symbol": symbol,
            "ml_buy_probability": buy_prob,
            "ml_sell_probability": sell_prob,
            "decision": decision,
            "score": score,
            "price": price,
            "max_probability": max(buy_prob, sell_prob),
            "probability_diff": abs(buy_prob - sell_prob),
            "indicators": indicators or {}
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
            logger.debug(f"📊 ML prediction logged: {decision} ({score:.1f}) at {price}")
            
        except Exception as e:
            logger.error(f"Error logging ML prediction: {e}")
    
    def get_recent_stats(self, hours: int = 24) -> Dict:
        """Obtiene estadísticas recientes del modelo"""
        
        if not self.log_file.exists():
            return {"error": "No prediction logs found"}
            
        try:
            # Leer logs recientes
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_predictions = []
            
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        pred_time = datetime.fromisoformat(entry['timestamp'])
                        if pred_time >= cutoff_time:
                            recent_predictions.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            
            if not recent_predictions:
                return {"error": "No recent predictions found"}
            
            # Calcular estadísticas
            df = pd.DataFrame(recent_predictions)
            
            stats = {
                "period_hours": hours,
                "total_predictions": len(df),
                "decision_counts": df['decision'].value_counts().to_dict(),
                "avg_max_probability": df['max_probability'].mean(),
                "avg_probability_diff": df['probability_diff'].mean(),
                "high_confidence_predictions": len(df[df['max_probability'] >= 0.8]),
                "low_confidence_predictions": len(df[df['max_probability'] <= 0.6]),
                "avg_score": df['score'].mean(),
                "price_range": {
                    "min": df['price'].min(),
                    "max": df['price'].max(),
                    "current": df['price'].iloc[-1] if not df.empty else None
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating ML stats: {e}")
            return {"error": str(e)}
    
    def get_prediction_distribution(self) -> Dict:
        """Analiza la distribución de probabilidades del modelo"""
        
        if not self.log_file.exists():
            return {"error": "No prediction logs found"}
            
        try:
            predictions = []
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        predictions.append(entry)
                    except json.JSONDecodeError:
                        continue
            
            if not predictions:
                return {"error": "No predictions found"}
            
            df = pd.DataFrame(predictions)
            
            # Análisis de distribución
            buy_probs = df['ml_buy_probability']
            sell_probs = df['ml_sell_probability']
            
            distribution = {
                "total_predictions": len(df),
                "buy_probability_stats": {
                    "mean": buy_probs.mean(),
                    "std": buy_probs.std(),
                    "min": buy_probs.min(),
                    "max": buy_probs.max(),
                    "median": buy_probs.median()
                },
                "sell_probability_stats": {
                    "mean": sell_probs.mean(),
                    "std": sell_probs.std(),
                    "min": sell_probs.min(),
                    "max": sell_probs.max(),
                    "median": sell_probs.median()
                },
                "probability_ranges": {
                    "very_high_buy": len(df[df['ml_buy_probability'] >= 0.85]),
                    "high_buy": len(df[df['ml_buy_probability'] >= 0.70]),
                    "neutral": len(df[(df['ml_buy_probability'] < 0.70) & (df['ml_sell_probability'] < 0.70)]),
                    "high_sell": len(df[df['ml_sell_probability'] >= 0.70]),
                    "very_high_sell": len(df[df['ml_sell_probability'] >= 0.85])
                }
            }
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error analyzing prediction distribution: {e}")
            return {"error": str(e)}

# Instancia global del monitor
ml_monitor = MLMonitor()
