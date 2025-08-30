#!/usr/bin/env python3
"""
Monitor de Acertividad Institucional en Tiempo Real
Integra estándares institucionales en el sistema ML de trading
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class InstitutionalMLMonitor:
    """
    Monitor de acertividad ML con estándares institucionales integrado
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Archivo de métricas institucionales
        self.metrics_file = self.data_dir / "institutional_ml_metrics.json"
        self.predictions_file = self.data_dir / "ml_predictions_log.json"
        
        # Estándares institucionales (de institutional_ml_standards.py)
        self.standards = {
            "minimum": {
                "accuracy": 0.55, "precision": 0.52, "recall": 0.50,
                "sharpe_ratio": 1.5, "max_drawdown": 0.15, "hit_rate": 0.52,
                "profit_factor": 1.3, "min_data_points": 17520
            },
            "target": {
                "accuracy": 0.62, "precision": 0.60, "recall": 0.58,
                "sharpe_ratio": 2.0, "max_drawdown": 0.10, "hit_rate": 0.58,
                "profit_factor": 1.6
            },
            "elite": {
                "accuracy": 0.68, "precision": 0.65, "recall": 0.62,
                "sharpe_ratio": 2.5, "max_drawdown": 0.08, "hit_rate": 0.62,
                "profit_factor": 2.0
            }
        }
        
        # Inicializar archivos si no existen
        self._initialize_files()
    
    def _initialize_files(self):
        """Inicializar archivos de métricas si no existen"""
        if not self.metrics_file.exists():
            initial_metrics = {
                "created_at": datetime.now().isoformat(),
                "current_metrics": {},
                "historical_metrics": [],
                "compliance_history": [],
                "alerts": []
            }
            with open(self.metrics_file, 'w') as f:
                json.dump(initial_metrics, f, indent=2)
        
        if not self.predictions_file.exists():
            initial_predictions = {
                "created_at": datetime.now().isoformat(),
                "predictions": [],
                "performance_summary": {}
            }
            with open(self.predictions_file, 'w') as f:
                json.dump(initial_predictions, f, indent=2)
    
    def log_ml_prediction(self, symbol: str, timestamp: str, buy_prob: float, 
                         sell_prob: float, decision: str, score: float, 
                         price: float, data_points: int = None):
        """
        Registra predicción ML con validación institucional
        """
        try:
            # Cargar predicciones existentes
            with open(self.predictions_file, 'r') as f:
                data = json.load(f)
            
            # Calcular nivel de confianza institucional
            confidence_level = self._calculate_institutional_confidence(data_points or 0)
            
            # Crear registro de predicción
            prediction_record = {
                "timestamp": timestamp,
                "symbol": symbol,
                "buy_probability": buy_prob,
                "sell_probability": sell_prob,
                "decision": decision,
                "score": score,
                "price": price,
                "data_points": data_points,
                "institutional_confidence": confidence_level,
                "compliance_status": self._get_compliance_status(data_points or 0)
            }
            
            # Añadir predicción
            data["predictions"].append(prediction_record)
            
            # Mantener solo las últimas 10,000 predicciones
            if len(data["predictions"]) > 10000:
                data["predictions"] = data["predictions"][-10000:]
            
            # Actualizar resumen de performance cada 100 predicciones
            if len(data["predictions"]) % 100 == 0:
                data["performance_summary"] = self._calculate_performance_summary(data["predictions"])
            
            # Guardar
            with open(self.predictions_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Verificar si necesita alerta institucional
            self._check_institutional_alerts(prediction_record)
            
        except Exception as e:
            logger.error(f"Error logging ML prediction: {e}")
    
    def _calculate_institutional_confidence(self, data_points: int) -> str:
        """Calcula nivel de confianza según estándares institucionales"""
        if data_points >= self.standards["minimum"]["min_data_points"]:
            return "INSTITUTIONAL"
        elif data_points >= 8760:  # 1 año
            return "PROFESSIONAL"
        elif data_points >= 2000:  # 3 meses
            return "BASIC"
        else:
            return "INSUFFICIENT"
    
    def _get_compliance_status(self, data_points: int) -> str:
        """Obtiene estado de compliance institucional"""
        if data_points >= self.standards["minimum"]["min_data_points"]:
            return "COMPLIANT"
        else:
            needed = self.standards["minimum"]["min_data_points"] - data_points
            return f"NON_COMPLIANT_NEED_{needed}_MORE_POINTS"
    
    def _calculate_performance_summary(self, predictions: List[Dict]) -> Dict:
        """Calcula resumen de performance para las últimas predicciones"""
        if len(predictions) < 50:
            return {"status": "INSUFFICIENT_DATA", "predictions_count": len(predictions)}
        
        recent_predictions = predictions[-1000:]  # Últimas 1000 predicciones
        
        # Simular métricas básicas (en producción vendría de backtesting real)
        decisions = [p["decision"] for p in recent_predictions]
        scores = [p["score"] for p in recent_predictions]
        
        # Estadísticas básicas
        buy_decisions = len([d for d in decisions if "COMPRAR" in d])
        sell_decisions = len([d for d in decisions if "VENDER" in d])
        hold_decisions = len([d for d in decisions if d == "MANTENER"])
        
        avg_score = sum(scores) / len(scores)
        
        # Análisis de distribución de confidence
        confidence_levels = [p.get("institutional_confidence", "UNKNOWN") for p in recent_predictions]
        confidence_distribution = {}
        for conf in set(confidence_levels):
            confidence_distribution[conf] = confidence_levels.count(conf)
        
        return {
            "period_start": recent_predictions[0]["timestamp"],
            "period_end": recent_predictions[-1]["timestamp"],
            "total_predictions": len(recent_predictions),
            "decision_distribution": {
                "buy": buy_decisions,
                "sell": sell_decisions, 
                "hold": hold_decisions
            },
            "average_score": round(avg_score, 2),
            "confidence_distribution": confidence_distribution,
            "institutional_readiness": confidence_levels.count("INSTITUTIONAL") / len(confidence_levels) * 100,
            "last_updated": datetime.now().isoformat()
        }
    
    def _check_institutional_alerts(self, prediction: Dict):
        """Verifica si se necesitan alertas institucionales"""
        alerts = []
        
        # Alerta por datos insuficientes
        data_points = prediction.get("data_points", 0)
        if data_points < self.standards["minimum"]["min_data_points"]:
            alerts.append({
                "type": "INSUFFICIENT_DATA",
                "severity": "HIGH",
                "message": f"Datos insuficientes para estándares institucionales: {data_points} < {self.standards['minimum']['min_data_points']}",
                "timestamp": prediction["timestamp"]
            })
        
        # Alerta por score bajo en decisiones importantes
        if prediction["decision"] in ["COMPRAR", "VENDER"] and prediction["score"] < 70:
            alerts.append({
                "type": "LOW_CONFIDENCE_TRADE",
                "severity": "MEDIUM",
                "message": f"Decisión de trading con score bajo: {prediction['decision']} con score {prediction['score']:.1f}",
                "timestamp": prediction["timestamp"]
            })
        
        # Guardar alertas si existen
        if alerts:
            self._save_institutional_alerts(alerts)
    
    def _save_institutional_alerts(self, new_alerts: List[Dict]):
        """Guarda alertas institucionales"""
        try:
            with open(self.metrics_file, 'r') as f:
                data = json.load(f)
            
            data["alerts"].extend(new_alerts)
            
            # Mantener solo últimas 1000 alertas
            if len(data["alerts"]) > 1000:
                data["alerts"] = data["alerts"][-1000:]
            
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving institutional alerts: {e}")
    
    def get_institutional_status(self) -> Dict:
        """Obtiene estado actual de compliance institucional"""
        try:
            with open(self.predictions_file, 'r') as f:
                predictions_data = json.load(f)
            
            with open(self.metrics_file, 'r') as f:
                metrics_data = json.load(f)
            
            recent_predictions = predictions_data["predictions"][-100:] if predictions_data["predictions"] else []
            
            if not recent_predictions:
                return {
                    "status": "NO_DATA",
                    "message": "No hay predicciones ML registradas",
                    "compliance": "UNKNOWN"
                }
            
            # Analizar datos recientes
            data_points = recent_predictions[-1].get("data_points", 0)
            confidence_levels = [p.get("institutional_confidence", "UNKNOWN") for p in recent_predictions]
            
            institutional_pct = confidence_levels.count("INSTITUTIONAL") / len(confidence_levels) * 100
            
            # Determinar estado general
            if institutional_pct >= 80:
                status = "INSTITUTIONAL_READY"
                compliance = "FULL_COMPLIANCE"
            elif institutional_pct >= 50:
                status = "PARTIALLY_COMPLIANT"
                compliance = "PARTIAL_COMPLIANCE"
            elif data_points >= 8760:
                status = "PROFESSIONAL_LEVEL"
                compliance = "PROFESSIONAL_COMPLIANCE"
            else:
                status = "DEVELOPMENT_PHASE"
                compliance = "NON_COMPLIANT"
            
            return {
                "status": status,
                "compliance": compliance,
                "data_points": data_points,
                "institutional_readiness_pct": round(institutional_pct, 1),
                "recent_predictions": len(recent_predictions),
                "active_alerts": len([a for a in metrics_data.get("alerts", []) 
                                    if datetime.fromisoformat(a["timestamp"]) > datetime.now() - timedelta(hours=24)]),
                "last_prediction": recent_predictions[-1]["timestamp"] if recent_predictions else None,
                "recommendation": self._get_institutional_recommendation(data_points, institutional_pct)
            }
            
        except Exception as e:
            logger.error(f"Error getting institutional status: {e}")
            return {"status": "ERROR", "error": str(e)}
    
    def _get_institutional_recommendation(self, data_points: int, institutional_pct: float) -> str:
        """Genera recomendación basada en estado actual"""
        min_required = self.standards["minimum"]["min_data_points"]
        
        if data_points < min_required:
            needed = min_required - data_points
            return f"Descargar {needed:,} puntos adicionales para compliance institucional"
        elif institutional_pct < 80:
            return "Mantener calidad de datos y continuar monitoreo para full compliance"
        else:
            return "Sistema ready para trading institucional - mantener estándares actuales"
    
    def generate_compliance_dashboard(self) -> str:
        """Genera dashboard de compliance institucional"""
        status = self.get_institutional_status()
        
        dashboard = f"""
🏛️ DASHBOARD INSTITUCIONAL ML - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
════════════════════════════════════════════════════════════════

📊 ESTADO GENERAL:
   Status: {status.get('status', 'UNKNOWN')}
   Compliance: {status.get('compliance', 'UNKNOWN')}
   Readiness Institucional: {status.get('institutional_readiness_pct', 0):.1f}%

📈 MÉTRICAS ACTUALES:
   Puntos de Datos: {status.get('data_points', 0):,}
   Requerido Mínimo: {self.standards['minimum']['min_data_points']:,}
   Predicciones Recientes: {status.get('recent_predictions', 0)}
   Alertas Activas (24h): {status.get('active_alerts', 0)}

🎯 BENCHMARKS INSTITUCIONALES:
   
   MÍNIMO INSTITUCIONAL:
   • Accuracy: ≥55%     • Sharpe: ≥1.5     • Max DD: ≤15%
   • Hit Rate: ≥52%     • PF: ≥1.3         • Datos: 17,520+
   
   TARGET INSTITUCIONAL:
   • Accuracy: ≥62%     • Sharpe: ≥2.0     • Max DD: ≤10%
   • Hit Rate: ≥58%     • PF: ≥1.6         • Performance A+
   
   ÉLITE CUANTITATIVA:
   • Accuracy: ≥68%     • Sharpe: ≥2.5     • Max DD: ≤8%
   • Hit Rate: ≥62%     • PF: ≥2.0         • Top 1% Industria

💡 RECOMENDACIÓN ACTUAL:
   {status.get('recommendation', 'Contactar administrador del sistema')}

🔄 ÚLTIMA ACTUALIZACIÓN:
   {status.get('last_prediction', 'N/A')}
   
════════════════════════════════════════════════════════════════
"""
        return dashboard

# Instancia global del monitor institucional
institutional_monitor = InstitutionalMLMonitor()

# Funciones de integración para el sistema existente
def log_institutional_prediction(symbol: str, timestamp: str, buy_prob: float,
                                sell_prob: float, decision: str, score: float,
                                price: float, data_points: int = None):
    """Wrapper para logging con estándares institucionales"""
    institutional_monitor.log_ml_prediction(
        symbol, timestamp, buy_prob, sell_prob, 
        decision, score, price, data_points
    )

def get_institutional_compliance() -> Dict:
    """Obtiene estado de compliance institucional"""
    return institutional_monitor.get_institutional_status()

def print_institutional_dashboard():
    """Imprime dashboard institucional"""
    print(institutional_monitor.generate_compliance_dashboard())

if __name__ == "__main__":
    # Demo del monitor institucional
    print("🏛️ DEMO - MONITOR INSTITUCIONAL ML")
    print("=" * 50)
    
    # Simular algunas predicciones
    for i in range(5):
        institutional_monitor.log_ml_prediction(
            symbol="BTCUSDT",
            timestamp=datetime.now().isoformat(),
            buy_prob=0.6 + (i * 0.05),
            sell_prob=0.4 - (i * 0.05),
            decision="COMPRAR" if i % 2 == 0 else "MANTENER",
            score=70 + (i * 5),
            price=50000 + (i * 1000),
            data_points=1000 + (i * 500)  # Simulando crecimiento de datos
        )
    
    # Mostrar dashboard
    print_institutional_dashboard()
    
    # Mostrar status
    status = get_institutional_compliance()
    print(f"\n📊 Status: {status}")
