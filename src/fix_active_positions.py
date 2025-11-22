#!/usr/bin/env python3
"""
Script para corregir el problema de posiciones activas que se muestran incorrectamente.
Sincroniza las posiciones en memoria con el estado real de la base de datos.
"""

import sqlite3
import json
import os
import signal
import sys
from datetime import datetime
from typing import Dict, List

class ActivePositionsFixer:
    """Corrige el problema de posiciones activas desincronizadas"""
    
    def __init__(self):
        self.db_path = "auto_trading_alerts.db"
        self.forex_db_path = "forex_metals_trading.db"
        
    def check_all_databases(self) -> Dict:
        """Verifica el estado de todas las bases de datos"""
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "databases_checked": [],
            "total_active_positions": 0,
            "issues_found": []
        }
        
        # 1. Verificar base de datos principal
        if os.path.exists(self.db_path):
            main_db_status = self._check_database(self.db_path, "executed_trades")
            report["databases_checked"].append({
                "database": "auto_trading_alerts.db",
                "status": main_db_status
            })
            report["total_active_positions"] += main_db_status["active_positions"]
        
        # 2. Verificar base de datos de forex/metales
        if os.path.exists(self.forex_db_path):
            forex_db_status = self._check_database(self.forex_db_path, "forex_metals_signals")
            report["databases_checked"].append({
                "database": "forex_metals_trading.db", 
                "status": forex_db_status
            })
            
        return report
    
    def _check_database(self, db_path: str, table_name: str) -> Dict:
        """Verifica una base de datos específica"""
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar si la tabla existe
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                return {"error": f"Tabla {table_name} no encontrada", "active_positions": 0}
            
            # Obtener estructura de la tabla
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            
            result = {
                "table": table_name,
                "columns": columns,
                "total_records": 0,
                "active_positions": 0,
                "closed_positions": 0
            }
            
            # Contar registros totales
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            result["total_records"] = cursor.fetchone()[0]
            
            # Si tiene columna status, contar por estado
            if "status" in columns:
                cursor.execute(f"SELECT status, COUNT(*) FROM {table_name} GROUP BY status")
                status_counts = cursor.fetchall()
                
                for status, count in status_counts:
                    if status == 'ACTIVE':
                        result["active_positions"] = count
                    elif status == 'CLOSED':
                        result["closed_positions"] = count
            
            conn.close()
            return result
            
        except Exception as e:
            return {"error": str(e), "active_positions": 0}
    
    def stop_running_systems(self) -> List[str]:
        """Detiene los sistemas que están ejecutándose y causando el problema"""
        
        stopped_systems = []
        
        print("🛑 DETENIENDO SISTEMAS EN EJECUCIÓN...")
        
        # Lista de procesos que pueden estar causando el problema
        problematic_processes = [
            "forex_metals_trading_system.py",
            "alerta_auto_trading_integrada.py", 
            "enhanced_trading_system.py",
            "sicar_active_trading_demo.py"
        ]
        
        try:
            import psutil
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = ' '.join(cmdline)
                        
                        for problematic in problematic_processes:
                            if problematic in cmdline_str:
                                print(f"   🔴 Deteniendo: {problematic} (PID: {proc.info['pid']})")
                                proc.terminate()
                                stopped_systems.append(f"{problematic} (PID: {proc.info['pid']})")
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except ImportError:
            print("   ⚠️ psutil no disponible, no se pueden detener procesos automáticamente")
            print("   📝 Detén manualmente los sistemas en ejecución desde las terminales")
        
        return stopped_systems
    
    def clear_memory_positions(self) -> bool:
        """Limpia las posiciones en memoria de todos los sistemas"""
        
        print("🧹 LIMPIANDO POSICIONES EN MEMORIA...")
        
        # Archivos que pueden tener posiciones en memoria
        memory_files = [
            "forex_metals_positions.json",
            "active_positions.json", 
            "trading_state.json",
            "system_state.json"
        ]
        
        cleared_files = []
        
        for filename in memory_files:
            if os.path.exists(filename):
                try:
                    # Respaldar antes de limpiar
                    backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(filename, backup_name)
                    
                    # Crear archivo limpio
                    with open(filename, 'w') as f:
                        json.dump({"active_positions": {}, "timestamp": datetime.now().isoformat()}, f)
                    
                    cleared_files.append(filename)
                    print(f"   ✅ Limpiado: {filename} (respaldo: {backup_name})")
                    
                except Exception as e:
                    print(f"   ❌ Error limpiando {filename}: {e}")
        
        return len(cleared_files) > 0
    
    def fix_active_positions_issue(self) -> Dict:
        """Función principal para corregir el problema de posiciones activas"""
        
        print("🔧 INICIANDO CORRECCIÓN DE POSICIONES ACTIVAS")
        print("=" * 60)
        
        # 1. Verificar estado actual
        print("\n1️⃣ VERIFICANDO ESTADO ACTUAL...")
        initial_report = self.check_all_databases()
        
        print(f"   📊 Total posiciones activas encontradas: {initial_report['total_active_positions']}")
        
        for db_info in initial_report["databases_checked"]:
            db_name = db_info["database"]
            status = db_info["status"]
            if "error" not in status:
                print(f"   📁 {db_name}: {status['active_positions']} activas, {status['closed_positions']} cerradas")
            else:
                print(f"   ❌ {db_name}: {status['error']}")
        
        # 2. Detener sistemas en ejecución
        print("\n2️⃣ DETENIENDO SISTEMAS EN EJECUCIÓN...")
        stopped_systems = self.stop_running_systems()
        
        if stopped_systems:
            print(f"   ✅ Sistemas detenidos: {len(stopped_systems)}")
            for system in stopped_systems:
                print(f"      • {system}")
        else:
            print("   ℹ️ No se encontraron sistemas problemáticos en ejecución")
        
        # 3. Limpiar posiciones en memoria
        print("\n3️⃣ LIMPIANDO POSICIONES EN MEMORIA...")
        memory_cleared = self.clear_memory_positions()
        
        # 4. Verificar estado final
        print("\n4️⃣ VERIFICANDO ESTADO FINAL...")
        final_report = self.check_all_databases()
        
        print(f"   📊 Total posiciones activas después de la corrección: {final_report['total_active_positions']}")
        
        # 5. Generar reporte final
        fix_report = {
            "timestamp": datetime.now().isoformat(),
            "initial_state": initial_report,
            "final_state": final_report,
            "stopped_systems": stopped_systems,
            "memory_cleared": memory_cleared,
            "success": final_report['total_active_positions'] == 0,
            "recommendations": []
        }
        
        # Agregar recomendaciones
        if final_report['total_active_positions'] > 0:
            fix_report["recommendations"].append("Verificar manualmente las bases de datos")
            fix_report["recommendations"].append("Reiniciar los sistemas de trading")
        else:
            fix_report["recommendations"].append("Problema resuelto - sistemas listos para usar")
            fix_report["recommendations"].append("Usar 'python start_trading_system.py' para iniciar")
        
        # Guardar reporte
        with open("active_positions_fix_report.json", "w", encoding="utf-8") as f:
            json.dump(fix_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte guardado en: active_positions_fix_report.json")
        
        # Mostrar resultado final
        if fix_report["success"]:
            print("\n✅ PROBLEMA RESUELTO EXITOSAMENTE")
            print("   🎉 No hay posiciones activas falsas")
            print("   🚀 Los sistemas están listos para usar")
        else:
            print("\n⚠️ PROBLEMA PARCIALMENTE RESUELTO")
            print("   📝 Revisa el reporte para más detalles")
        
        return fix_report

def main():
    """Función principal"""
    
    try:
        fixer = ActivePositionsFixer()
        report = fixer.fix_active_positions_issue()
        
        return 0 if report["success"] else 1
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Operación cancelada por el usuario")
        return 1
    except Exception as e:
        print(f"\n❌ Error durante la corrección: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())