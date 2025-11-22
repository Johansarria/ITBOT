"""
Sistema de Monitoreo de Stop Loss Automático
Monitorea posiciones activas y ejecuta stop loss cuando es necesario
"""

import sqlite3
import requests
import time
import json
from datetime import datetime, timedelta
import threading
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stop_loss_monitor.log'),
        logging.StreamHandler()
    ]
)

class StopLossMonitor:
    def __init__(self, db_path="auto_trading_alerts.db", check_interval=60):
        self.db_path = db_path
        self.check_interval = check_interval  # segundos entre verificaciones
        self.running = False
        self.monitor_thread = None
        
    def get_current_price(self, symbol):
        """Obtiene el precio actual de Binance"""
        try:
            url = "https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': symbol}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return float(response.json()['price'])
        except Exception as e:
            logging.error(f"Error obteniendo precio de {symbol}: {e}")
            return None
    
    def get_active_positions(self):
        """Obtiene todas las posiciones activas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, symbol, side, quantity, entry_price, stop_loss, take_profit, timestamp
                FROM executed_trades 
                WHERE status = 'ACTIVE' AND stop_loss IS NOT NULL
            """)
            
            positions = cursor.fetchall()
            conn.close()
            
            return positions
            
        except Exception as e:
            logging.error(f"Error obteniendo posiciones activas: {e}")
            return []
    
    def should_trigger_stop_loss(self, position, current_price):
        """Determina si se debe activar el stop loss"""
        position_id, symbol, side, quantity, entry_price, stop_loss, take_profit, timestamp = position
        
        if side.lower() == 'sell':
            # Para posiciones SELL, stop loss se activa cuando el precio sube
            return current_price >= stop_loss
        else:
            # Para posiciones BUY, stop loss se activa cuando el precio baja
            return current_price <= stop_loss
    
    def should_trigger_take_profit(self, position, current_price):
        """Determina si se debe activar el take profit"""
        position_id, symbol, side, quantity, entry_price, stop_loss, take_profit, timestamp = position
        
        if not take_profit:
            return False
        
        if side.lower() == 'sell':
            # Para posiciones SELL, take profit se activa cuando el precio baja
            return current_price <= take_profit
        else:
            # Para posiciones BUY, take profit se activa cuando el precio sube
            return current_price >= take_profit
    
    def execute_stop_loss(self, position, current_price, trigger_type="STOP_LOSS"):
        """Ejecuta el cierre de posición por stop loss o take profit"""
        position_id, symbol, side, quantity, entry_price, stop_loss, take_profit, timestamp = position
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calcular PnL
            if side.lower() == 'sell':
                pnl_per_unit = entry_price - current_price
            else:
                pnl_per_unit = current_price - entry_price
            
            total_pnl = pnl_per_unit * quantity
            pnl_percentage = (pnl_per_unit / entry_price) * 100
            
            # Actualizar la posición
            close_timestamp = datetime.now().isoformat()
            cursor.execute("""
                UPDATE executed_trades 
                SET status = 'CLOSED',
                    exit_price = ?,
                    exit_timestamp = ?,
                    pnl = ?,
                    close_reason = ?
                WHERE id = ?
            """, (current_price, close_timestamp, total_pnl, f"Automatic {trigger_type}", position_id))
            
            conn.commit()
            conn.close()
            
            # Log del evento
            logging.info(f"🎯 {trigger_type} ejecutado para {symbol} {side.upper()}")
            logging.info(f"   Precio entrada: ${entry_price}")
            logging.info(f"   Precio cierre: ${current_price}")
            logging.info(f"   PnL: ${total_pnl:.2f} ({pnl_percentage:.2f}%)")
            
            # Guardar evento en archivo de log
            event = {
                'timestamp': close_timestamp,
                'position_id': position_id,
                'symbol': symbol,
                'side': side,
                'trigger_type': trigger_type,
                'entry_price': entry_price,
                'exit_price': current_price,
                'pnl': total_pnl,
                'pnl_percentage': pnl_percentage
            }
            
            self.log_stop_loss_event(event)
            
            return True
            
        except Exception as e:
            logging.error(f"Error ejecutando {trigger_type} para posición {position_id}: {e}")
            return False
    
    def log_stop_loss_event(self, event):
        """Registra eventos de stop loss en archivo JSON"""
        try:
            # Leer eventos existentes
            try:
                with open('stop_loss_events.json', 'r', encoding='utf-8') as f:
                    events = json.load(f)
            except FileNotFoundError:
                events = []
            
            # Agregar nuevo evento
            events.append(event)
            
            # Guardar eventos actualizados
            with open('stop_loss_events.json', 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2, default=str, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"Error guardando evento de stop loss: {e}")
    
    def monitor_positions(self):
        """Función principal de monitoreo"""
        logging.info("🚀 Iniciando monitoreo de stop loss")
        
        while self.running:
            try:
                # Obtener posiciones activas
                active_positions = self.get_active_positions()
                
                if not active_positions:
                    logging.debug("No hay posiciones activas para monitorear")
                else:
                    logging.info(f"📊 Monitoreando {len(active_positions)} posiciones activas")
                
                for position in active_positions:
                    position_id, symbol, side, quantity, entry_price, stop_loss, take_profit, timestamp = position
                    
                    # Obtener precio actual
                    current_price = self.get_current_price(symbol)
                    
                    if current_price is None:
                        logging.warning(f"No se pudo obtener precio para {symbol}")
                        continue
                    
                    logging.debug(f"   {symbol} {side.upper()}: ${current_price} (SL: ${stop_loss}, TP: ${take_profit or 'N/A'})")
                    
                    # Verificar stop loss
                    if self.should_trigger_stop_loss(position, current_price):
                        logging.warning(f"🚨 STOP LOSS activado para {symbol} {side.upper()}")
                        self.execute_stop_loss(position, current_price, "STOP_LOSS")
                        continue
                    
                    # Verificar take profit
                    if self.should_trigger_take_profit(position, current_price):
                        logging.info(f"🎯 TAKE PROFIT activado para {symbol} {side.upper()}")
                        self.execute_stop_loss(position, current_price, "TAKE_PROFIT")
                        continue
                
                # Esperar antes de la siguiente verificación
                time.sleep(self.check_interval)
                
            except Exception as e:
                logging.error(f"Error en el monitoreo: {e}")
                time.sleep(self.check_interval)
    
    def start_monitoring(self):
        """Inicia el monitoreo en un hilo separado"""
        if self.running:
            logging.warning("El monitoreo ya está en ejecución")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_positions, daemon=True)
        self.monitor_thread.start()
        
        logging.info(f"✅ Monitoreo de stop loss iniciado (intervalo: {self.check_interval}s)")
    
    def stop_monitoring(self):
        """Detiene el monitoreo"""
        if not self.running:
            logging.warning("El monitoreo no está en ejecución")
            return
        
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logging.info("🛑 Monitoreo de stop loss detenido")
    
    def get_monitoring_status(self):
        """Obtiene el estado del monitoreo"""
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'active_positions': len(self.get_active_positions()),
            'last_check': datetime.now().isoformat()
        }

def main():
    """Función principal para ejecutar el monitor"""
    print("🔧 SISTEMA DE MONITOREO DE STOP LOSS")
    print("=" * 50)
    
    # Crear monitor
    monitor = StopLossMonitor(check_interval=30)  # Verificar cada 30 segundos
    
    try:
        # Verificar posiciones activas
        active_positions = monitor.get_active_positions()
        print(f"📊 Posiciones activas encontradas: {len(active_positions)}")
        
        if active_positions:
            for position in active_positions:
                position_id, symbol, side, quantity, entry_price, stop_loss, take_profit, timestamp = position
                print(f"   {symbol} {side.upper()} - SL: ${stop_loss} - TP: ${take_profit or 'N/A'}")
        
        # Iniciar monitoreo
        monitor.start_monitoring()
        
        print("\n✅ Monitor iniciado. Presiona Ctrl+C para detener...")
        
        # Mantener el programa ejecutándose
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo monitor...")
        monitor.stop_monitoring()
        print("✅ Monitor detenido exitosamente")

if __name__ == "__main__":
    main()