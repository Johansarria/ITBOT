#!/usr/bin/env python3
"""
Aplicador de Configuración Optimizada SICAR
Aplica automáticamente los parámetros optimizados al sistema
"""

import json
import os
import shutil
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedConfigApplier:
    """
    Aplica configuraciones optimizadas al sistema SICAR
    """
    
    def __init__(self):
        self.config_file = "config.py"
        self.backup_dir = "config_backups"
        
        # Configuraciones optimizadas predefinidas para diferentes objetivos
        self.optimized_configs = {
            "aggressive_15_percent": {
                "description": "Configuración agresiva para 15% ROI mensual",
                "parameters": {
                    "RISK_PER_TRADE": 0.08,           # 8% riesgo por operación
                    "STOP_LOSS_PCT": 0.05,            # 5% stop loss
                    "TAKE_PROFIT_PCT": 0.20,          # 20% take profit
                    "POSITION_SIZE_PCT": 0.60,        # 60% del capital por posición
                    "CONFIDENCE_THRESHOLD": 0.60,     # 60% confianza mínima
                    "SIGNAL_QUALITY_MIN": 0.70,       # 70% calidad de señal
                    "MAX_POSITIONS": 3,               # Máximo 3 posiciones
                    "REBALANCE_FREQUENCY": 2,         # Rebalanceo cada 2 horas
                    "TIMEFRAME": "1h",                # Timeframe de 1 hora
                    "DRAWDOWN_LIMIT": 0.25,           # 25% drawdown máximo
                    "TRAILING_STOP": True,            # Activar trailing stop
                    "DYNAMIC_POSITION_SIZING": True   # Tamaño dinámico de posición
                }
            },
            "moderate_10_percent": {
                "description": "Configuración moderada para 10% ROI mensual",
                "parameters": {
                    "RISK_PER_TRADE": 0.05,
                    "STOP_LOSS_PCT": 0.06,
                    "TAKE_PROFIT_PCT": 0.15,
                    "POSITION_SIZE_PCT": 0.40,
                    "CONFIDENCE_THRESHOLD": 0.65,
                    "SIGNAL_QUALITY_MIN": 0.75,
                    "MAX_POSITIONS": 2,
                    "REBALANCE_FREQUENCY": 4,
                    "TIMEFRAME": "2h",
                    "DRAWDOWN_LIMIT": 0.20,
                    "TRAILING_STOP": True,
                    "DYNAMIC_POSITION_SIZING": False
                }
            },
            "conservative_5_percent": {
                "description": "Configuración conservadora para 5% ROI mensual",
                "parameters": {
                    "RISK_PER_TRADE": 0.03,
                    "STOP_LOSS_PCT": 0.08,
                    "TAKE_PROFIT_PCT": 0.12,
                    "POSITION_SIZE_PCT": 0.30,
                    "CONFIDENCE_THRESHOLD": 0.70,
                    "SIGNAL_QUALITY_MIN": 0.80,
                    "MAX_POSITIONS": 1,
                    "REBALANCE_FREQUENCY": 6,
                    "TIMEFRAME": "4h",
                    "DRAWDOWN_LIMIT": 0.15,
                    "TRAILING_STOP": False,
                    "DYNAMIC_POSITION_SIZING": False
                }
            }
        }
    
    def backup_current_config(self):
        """
        Crea backup de la configuración actual
        """
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"config_backup_{timestamp}.py")
        
        if os.path.exists(self.config_file):
            shutil.copy2(self.config_file, backup_path)
            logger.info(f"✅ Backup creado: {backup_path}")
            return backup_path
        else:
            logger.warning("⚠️ No se encontró config.py para hacer backup")
            return None
    
    def apply_optimized_config(self, config_name: str = "aggressive_15_percent"):
        """
        Aplica una configuración optimizada específica
        
        Args:
            config_name: Nombre de la configuración a aplicar
        """
        if config_name not in self.optimized_configs:
            logger.error(f"❌ Configuración '{config_name}' no encontrada")
            return False
        
        config = self.optimized_configs[config_name]
        logger.info(f"🔧 Aplicando configuración: {config['description']}")
        
        # Crear backup
        self.backup_current_config()
        
        # Leer configuración actual
        current_config = self._read_current_config()
        
        # Aplicar nuevos parámetros
        updated_config = self._update_config_parameters(current_config, config['parameters'])
        
        # Escribir nueva configuración
        self._write_config(updated_config)
        
        logger.info("✅ Configuración optimizada aplicada exitosamente")
        self._log_applied_changes(config['parameters'])
        
        return True
    
    def apply_custom_config(self, custom_parameters: dict):
        """
        Aplica una configuración personalizada
        
        Args:
            custom_parameters: Diccionario con parámetros personalizados
        """
        logger.info("🔧 Aplicando configuración personalizada")
        
        # Crear backup
        self.backup_current_config()
        
        # Leer configuración actual
        current_config = self._read_current_config()
        
        # Aplicar parámetros personalizados
        updated_config = self._update_config_parameters(current_config, custom_parameters)
        
        # Escribir nueva configuración
        self._write_config(updated_config)
        
        logger.info("✅ Configuración personalizada aplicada exitosamente")
        self._log_applied_changes(custom_parameters)
        
        return True
    
    def _read_current_config(self):
        """
        Lee la configuración actual del archivo config.py
        """
        config_lines = []
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_lines = f.readlines()
        
        return config_lines
    
    def _update_config_parameters(self, config_lines: list, new_parameters: dict):
        """
        Actualiza los parámetros en las líneas de configuración
        
        Args:
            config_lines: Líneas actuales del archivo de configuración
            new_parameters: Nuevos parámetros a aplicar
            
        Returns:
            Líneas de configuración actualizadas
        """
        updated_lines = []
        parameters_applied = set()
        
        for line in config_lines:
            line_updated = False
            
            for param_name, param_value in new_parameters.items():
                if line.strip().startswith(f"{param_name} ="):
                    # Actualizar parámetro existente
                    if isinstance(param_value, str):
                        updated_lines.append(f"{param_name} = '{param_value}'\n")
                    elif isinstance(param_value, bool):
                        updated_lines.append(f"{param_name} = {param_value}\n")
                    else:
                        updated_lines.append(f"{param_name} = {param_value}\n")
                    
                    parameters_applied.add(param_name)
                    line_updated = True
                    break
            
            if not line_updated:
                updated_lines.append(line)
        
        # Agregar parámetros nuevos que no existían
        for param_name, param_value in new_parameters.items():
            if param_name not in parameters_applied:
                if isinstance(param_value, str):
                    updated_lines.append(f"\n# Parámetro optimizado agregado\n{param_name} = '{param_value}'\n")
                elif isinstance(param_value, bool):
                    updated_lines.append(f"\n# Parámetro optimizado agregado\n{param_name} = {param_value}\n")
                else:
                    updated_lines.append(f"\n# Parámetro optimizado agregado\n{param_name} = {param_value}\n")
        
        return updated_lines
    
    def _write_config(self, config_lines: list):
        """
        Escribe las líneas de configuración al archivo
        """
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.writelines(config_lines)
    
    def _log_applied_changes(self, parameters: dict):
        """
        Registra los cambios aplicados
        """
        logger.info("📋 Parámetros aplicados:")
        for param_name, param_value in parameters.items():
            logger.info(f"   {param_name}: {param_value}")
    
    def list_available_configs(self):
        """
        Lista las configuraciones disponibles
        """
        logger.info("📋 Configuraciones optimizadas disponibles:")
        for config_name, config_data in self.optimized_configs.items():
            logger.info(f"   {config_name}: {config_data['description']}")
    
    def restore_backup(self, backup_file: str):
        """
        Restaura una configuración desde un backup
        
        Args:
            backup_file: Archivo de backup a restaurar
        """
        backup_path = os.path.join(self.backup_dir, backup_file)
        
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, self.config_file)
            logger.info(f"✅ Configuración restaurada desde: {backup_file}")
            return True
        else:
            logger.error(f"❌ Backup no encontrado: {backup_file}")
            return False

def main():
    """
    Función principal para aplicar configuraciones optimizadas
    """
    applier = OptimizedConfigApplier()
    
    logger.info("🎯 Sistema de Aplicación de Configuraciones Optimizadas SICAR")
    
    # Mostrar configuraciones disponibles
    applier.list_available_configs()
    
    # Aplicar configuración agresiva para 15% ROI mensual
    logger.info("\n🚀 Aplicando configuración agresiva para 15% ROI mensual...")
    success = applier.apply_optimized_config("aggressive_15_percent")
    
    if success:
        logger.info("✅ Configuración aplicada exitosamente")
        logger.info("🔄 Reinicia el bot para aplicar los cambios")
    else:
        logger.error("❌ Error aplicando configuración")

if __name__ == "__main__":
    main()