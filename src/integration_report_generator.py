#!/usr/bin/env python3
"""
Generador de Reportes de Integración para SICAR Paper Trading
Genera reportes detallados del estado del sistema y performance
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/integration_reports.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntegrationReportGenerator:
    """Generador de reportes de integración del sistema SICAR."""
    
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        self.reports_dir = os.path.join(self.logs_dir, 'integration_reports')
        
        # Crear directorios si no existen
        os.makedirs(self.reports_dir, exist_ok=True)
        
        logger.info("🔄 Integration Report Generator inicializado")
    
    def load_paper_trading_session(self) -> Optional[Dict]:
        """Carga la sesión actual de paper trading."""
        try:
            session_file = os.path.join(self.data_dir, 'paper_trading_session.json')
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning("❌ Archivo de sesión de paper trading no encontrado")
                return None
        except Exception as e:
            logger.error(f"Error cargando sesión de paper trading: {e}")
            return None
    
    def load_trade_logs(self) -> List[Dict]:
        """Carga los logs de trading desde el archivo JSON."""
        try:
            trades_file = os.path.join(self.logs_dir, 'trades_data.jsonl')
            trades = []
            
            if os.path.exists(trades_file):
                with open(trades_file, 'r') as f:
                    for line in f:
                        try:
                            trade = json.loads(line.strip())
                            trades.append(trade)
                        except json.JSONDecodeError:
                            continue
                            
                logger.info(f"✅ Cargados {len(trades)} trades desde logs")
                return trades
            else:
                logger.warning("❌ Archivo de trades no encontrado")
                return []
                
        except Exception as e:
            logger.error(f"Error cargando trade logs: {e}")
            return []
    
    def analyze_trading_performance(self, trades: List[Dict]) -> Dict[str, Any]:
        """Analiza la performance de trading."""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_trade_value': 0.0
            }
        
        try:
            # Filtrar solo trades de paper trading
            paper_trades = [t for t in trades if t.get('session_type') == 'paper_trading']
            
            if not paper_trades:
                return {'error': 'No paper trading trades found'}
            
            # Calcular métricas básicas
            total_trades = len(paper_trades)
            total_volume = sum(t.get('trade_value', 0) for t in paper_trades)
            avg_trade_value = total_volume / total_trades if total_trades > 0 else 0
            
            # Agrupar por símbolo
            symbols = {}
            for trade in paper_trades:
                symbol = trade.get('symbol', 'UNKNOWN')
                if symbol not in symbols:
                    symbols[symbol] = {'count': 0, 'volume': 0}
                symbols[symbol]['count'] += 1
                symbols[symbol]['volume'] += trade.get('trade_value', 0)
            
            # Análisis temporal
            recent_trades = [
                t for t in paper_trades 
                if datetime.fromisoformat(t.get('timestamp', '2020-01-01')) > 
                datetime.now() - timedelta(hours=24)
            ]
            
            return {
                'total_trades': total_trades,
                'total_volume': total_volume,
                'avg_trade_value': avg_trade_value,
                'symbols_traded': len(symbols),
                'symbol_breakdown': symbols,
                'recent_24h_trades': len(recent_trades),
                'last_trade_time': paper_trades[-1].get('timestamp') if paper_trades else None
            }
            
        except Exception as e:
            logger.error(f"Error analizando performance: {e}")
            return {'error': str(e)}
    
    def check_system_health(self) -> Dict[str, Any]:
        """Verifica la salud del sistema."""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'issues': []
        }
        
        try:
            # Verificar archivos críticos
            critical_files = [
                ('data/paper_trading_session.json', 'Sesión de paper trading'),
                ('sicar_config.json', 'Configuración principal'),
                ('logs/trades_detailed.log', 'Log de trades detallado')
            ]
            
            for file_path, description in critical_files:
                full_path = os.path.join(self.base_dir, file_path)
                if not os.path.exists(full_path):
                    health['issues'].append(f"❌ {description} no encontrado: {file_path}")
                    health['status'] = 'warning'
                else:
                    # Verificar si el archivo es reciente (modificado en las últimas 24h)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(full_path))
                    if datetime.now() - mod_time > timedelta(hours=24):
                        health['issues'].append(f"⚠️ {description} no actualizado en 24h: {file_path}")
            
            # Verificar logs directory
            if not os.path.exists(self.logs_dir):
                health['issues'].append("❌ Directorio de logs no existe")
                health['status'] = 'critical'
            
            # Verificar espacio en disco (básico)
            try:
                import shutil
                total, used, free = shutil.disk_usage(self.base_dir)
                free_gb = free // (1024**3)
                if free_gb < 1:  # Menos de 1GB libre
                    health['issues'].append(f"⚠️ Poco espacio en disco: {free_gb}GB libres")
                    health['status'] = 'warning'
            except:
                pass
            
            if not health['issues']:
                health['status'] = 'healthy'
                health['issues'].append("✅ Todos los sistemas funcionando correctamente")
                
        except Exception as e:
            health['status'] = 'error'
            health['issues'].append(f"❌ Error verificando salud del sistema: {e}")
        
        return health
    
    def generate_integration_report(self) -> Dict[str, Any]:
        """Genera un reporte completo de integración."""
        logger.info("📊 Generando reporte de integración...")
        
        report = {
            'report_id': f"integration_{int(datetime.now().timestamp())}",
            'timestamp': datetime.now().isoformat(),
            'report_type': 'integration_status',
            'version': '1.0'
        }
        
        try:
            # Cargar datos
            session_data = self.load_paper_trading_session()
            trade_logs = self.load_trade_logs()
            
            # Análisis de sesión
            if session_data:
                report['session_status'] = {
                    'active': session_data.get('session_active', False),
                    'auto_trading': session_data.get('auto_trading', False),
                    'initial_capital': session_data.get('initial_capital', 0),
                    'current_capital': session_data.get('current_capital', 0),
                    'total_trades': len(session_data.get('trades', [])),
                    'last_restart': session_data.get('restart_reason', 'Unknown')
                }
            else:
                report['session_status'] = {'error': 'No session data available'}
            
            # Análisis de performance
            report['trading_performance'] = self.analyze_trading_performance(trade_logs)
            
            # Salud del sistema
            report['system_health'] = self.check_system_health()
            
            # Estadísticas de archivos
            report['file_stats'] = self._get_file_statistics()
            
            # Resumen ejecutivo
            report['executive_summary'] = self._generate_executive_summary(report)
            
            logger.info("✅ Reporte de integración generado exitosamente")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            report['error'] = str(e)
            return report
    
    def _get_file_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas de archivos del sistema."""
        stats = {
            'logs_count': 0,
            'data_files_count': 0,
            'total_log_size_mb': 0
        }
        
        try:
            # Contar archivos de logs
            if os.path.exists(self.logs_dir):
                log_files = [f for f in os.listdir(self.logs_dir) if f.endswith('.log')]
                stats['logs_count'] = len(log_files)
                
                # Calcular tamaño total de logs
                total_size = 0
                for log_file in log_files:
                    file_path = os.path.join(self.logs_dir, log_file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
                stats['total_log_size_mb'] = round(total_size / (1024*1024), 2)
            
            # Contar archivos de datos
            if os.path.exists(self.data_dir):
                data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
                stats['data_files_count'] = len(data_files)
                
        except Exception as e:
            stats['error'] = str(e)
        
        return stats
    
    def _generate_executive_summary(self, report: Dict[str, Any]) -> Dict[str, str]:
        """Genera un resumen ejecutivo del reporte."""
        summary = {}
        
        try:
            # Estado general
            session = report.get('session_status', {})
            if session.get('active') and session.get('auto_trading'):
                summary['status'] = "🟢 Sistema activo y operando"
            elif session.get('active'):
                summary['status'] = "🟡 Sistema activo, auto-trading deshabilitado"
            else:
                summary['status'] = "🔴 Sistema inactivo"
            
            # Performance
            performance = report.get('trading_performance', {})
            total_trades = performance.get('total_trades', 0)
            if total_trades > 0:
                summary['activity'] = f"📈 {total_trades} trades ejecutados"
            else:
                summary['activity'] = "📊 Sin actividad de trading reciente"
            
            # Salud del sistema
            health = report.get('system_health', {})
            if health.get('status') == 'healthy':
                summary['health'] = "✅ Sistema saludable"
            elif health.get('status') == 'warning':
                summary['health'] = "⚠️ Advertencias detectadas"
            else:
                summary['health'] = "❌ Problemas críticos detectados"
                
        except Exception as e:
            summary['error'] = f"Error generando resumen: {e}"
        
        return summary
    
    def save_report(self, report: Dict[str, Any]) -> str:
        """Guarda el reporte en un archivo."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"integration_report_{timestamp}.json"
            filepath = os.path.join(self.reports_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Reporte guardado en: {filepath}")
            
            # También crear un archivo de log legible
            log_filename = f"integration_report_{timestamp}.log"
            log_filepath = os.path.join(self.reports_dir, log_filename)
            
            with open(log_filepath, 'w', encoding='utf-8') as f:
                f.write(f"REPORTE DE INTEGRACIÓN SICAR\n")
                f.write(f"{'='*50}\n")
                f.write(f"Timestamp: {report.get('timestamp')}\n")
                f.write(f"Report ID: {report.get('report_id')}\n\n")
                
                # Resumen ejecutivo
                summary = report.get('executive_summary', {})
                f.write("RESUMEN EJECUTIVO:\n")
                for key, value in summary.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
                
                # Estado de sesión
                session = report.get('session_status', {})
                f.write("ESTADO DE SESIÓN:\n")
                for key, value in session.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
                
                # Salud del sistema
                health = report.get('system_health', {})
                f.write("SALUD DEL SISTEMA:\n")
                f.write(f"  Estado: {health.get('status', 'unknown')}\n")
                issues = health.get('issues', [])
                for issue in issues:
                    f.write(f"  {issue}\n")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error guardando reporte: {e}")
            return ""

def main():
    """Función principal para generar reporte."""
    try:
        generator = IntegrationReportGenerator()
        report = generator.generate_integration_report()
        filepath = generator.save_report(report)
        
        print("\n" + "="*60)
        print("📊 REPORTE DE INTEGRACIÓN GENERADO")
        print("="*60)
        
        # Mostrar resumen ejecutivo
        summary = report.get('executive_summary', {})
        for key, value in summary.items():
            print(f"{value}")
        
        print(f"\n💾 Reporte completo guardado en: {filepath}")
        print("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error en main: {e}")
        return False

if __name__ == "__main__":
    main()