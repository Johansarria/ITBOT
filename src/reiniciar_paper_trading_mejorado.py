#!/usr/bin/env python3
"""
Sistema de Reinicio Mejorado de Paper Trading
Reinicia la sesión con capital correcto e implementa mejoras avanzadas
"""

import json
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

# Configurar logging avanzado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('paper_trading_restart.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PaperTradingRestartManager:
    def __init__(self):
        self.config_file = 'sicar_config.json'
        self.session_file = 'data/paper_trading_session.json'
        self.backup_dir = 'session_backups'
        
        # Cargar configuración
        self.config = self.load_config()
        self.initial_capital = self.config.get('PAPER_TRADING_CONFIG', {}).get('initial_capital', 250.0)
        
        # Crear directorio de backups si no existe
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def load_config(self) -> Dict:
        """Cargar configuración del sistema"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return {}
    
    def backup_current_session(self) -> bool:
        """Crear backup de la sesión actual"""
        try:
            if os.path.exists(self.session_file):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(self.backup_dir, f"session_backup_{timestamp}.json")
                
                with open(self.session_file, 'r') as src:
                    session_data = json.load(src)
                
                with open(backup_file, 'w') as dst:
                    json.dump(session_data, dst, indent=2)
                
                logger.info(f"✅ Backup creado: {backup_file}")
                return True
            else:
                logger.info("ℹ️ No hay sesión existente para respaldar")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error creando backup: {e}")
            return False
    
    def create_fresh_session(self) -> bool:
        """Crear nueva sesión con capital correcto"""
        try:
            # Crear directorio data si no existe
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            
            fresh_session = {
                "timestamp": datetime.now().isoformat(),
                "initial_capital": self.initial_capital,
                "current_capital": self.initial_capital,
                "positions": [],
                "total_trades": 0,
                "auto_trading": True,
                "session_active": True,
                "current_session": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "last_sync": datetime.now().isoformat(),
                "restart_reason": "Capital adjustment to $250 USDT + Advanced improvements",
                "restart_timestamp": datetime.now().isoformat(),
                "advanced_features": {
                    "ia_filters_enabled": True,
                    "smart_alerts_enabled": True,
                    "enhanced_logging": True,
                    "market_preparation_mode": True
                }
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(fresh_session, f, indent=2)
            
            logger.info(f"✅ Nueva sesión creada con capital: ${self.initial_capital}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando nueva sesión: {e}")
            return False
    
    def verify_session_integrity(self) -> bool:
        """Verificar integridad de la nueva sesión"""
        try:
            with open(self.session_file, 'r') as f:
                session = json.load(f)
            
            # Verificaciones críticas
            checks = [
                session.get('initial_capital') == self.initial_capital,
                session.get('current_capital') == self.initial_capital,
                session.get('session_active') == True,
                'advanced_features' in session
            ]
            
            if all(checks):
                logger.info("✅ Verificación de integridad: EXITOSA")
                return True
            else:
                logger.error("❌ Verificación de integridad: FALLIDA")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando integridad: {e}")
            return False
    
    def display_session_status(self):
        """Mostrar estado detallado de la sesión"""
        try:
            with open(self.session_file, 'r') as f:
                session = json.load(f)
            
            print("\n" + "="*80)
            print("📊 ESTADO DE LA SESIÓN DE PAPER TRADING")
            print("="*80)
            print(f"💰 Capital Inicial: ${session.get('initial_capital', 0):.2f}")
            print(f"💵 Capital Actual: ${session.get('current_capital', 0):.2f}")
            print(f"📈 Posiciones Abiertas: {len(session.get('positions', []))}")
            print(f"🔄 Total de Trades: {session.get('total_trades', 0)}")
            print(f"🤖 Auto Trading: {'✅ ACTIVO' if session.get('auto_trading') else '❌ INACTIVO'}")
            print(f"🟢 Sesión Activa: {'✅ SÍ' if session.get('session_active') else '❌ NO'}")
            print(f"🆔 ID Sesión: {session.get('current_session', 'N/A')}")
            
            # Características avanzadas
            advanced = session.get('advanced_features', {})
            print(f"\n🚀 CARACTERÍSTICAS AVANZADAS:")
            print(f"   🧠 Filtros IA: {'✅' if advanced.get('ia_filters_enabled') else '❌'}")
            print(f"   🔔 Alertas Inteligentes: {'✅' if advanced.get('smart_alerts_enabled') else '❌'}")
            print(f"   📝 Logging Mejorado: {'✅' if advanced.get('enhanced_logging') else '❌'}")
            print(f"   🎯 Modo Preparación: {'✅' if advanced.get('market_preparation_mode') else '❌'}")
            
            print(f"\n⏰ Última Actualización: {session.get('last_sync', 'N/A')}")
            print("="*80)
            
        except Exception as e:
            logger.error(f"❌ Error mostrando estado: {e}")
    
    def restart_session(self) -> bool:
        """Proceso completo de reinicio"""
        logger.info("🔄 INICIANDO REINICIO DE SESIÓN DE PAPER TRADING")
        logger.info("="*60)
        
        # Paso 1: Backup
        logger.info("📦 Paso 1: Creando backup de sesión actual...")
        if not self.backup_current_session():
            return False
        
        # Paso 2: Crear nueva sesión
        logger.info("🆕 Paso 2: Creando nueva sesión...")
        if not self.create_fresh_session():
            return False
        
        # Paso 3: Verificar integridad
        logger.info("🔍 Paso 3: Verificando integridad...")
        if not self.verify_session_integrity():
            return False
        
        # Paso 4: Mostrar estado
        logger.info("📊 Paso 4: Mostrando estado final...")
        self.display_session_status()
        
        logger.info("✅ REINICIO COMPLETADO EXITOSAMENTE")
        return True

def main():
    """Función principal"""
    print("🚀 SISTEMA DE REINICIO MEJORADO DE PAPER TRADING")
    print("="*60)
    
    restart_manager = PaperTradingRestartManager()
    
    if restart_manager.restart_session():
        print("\n🎉 ¡REINICIO EXITOSO!")
        print("💡 El sistema está listo para operar con las mejoras implementadas")
        print("🔔 Alertas inteligentes y filtros IA están activados")
        print("📊 Logging avanzado habilitado para análisis posterior")
    else:
        print("\n❌ ERROR EN EL REINICIO")
        print("🔧 Revisa los logs para más detalles")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())