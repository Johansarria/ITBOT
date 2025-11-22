"""
Script para cerrar manualmente las posiciones activas
y calcular las pérdidas finales
"""

import sqlite3
import requests
from datetime import datetime
import json

class PositionCloser:
    def __init__(self, db_path="auto_trading_alerts.db"):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        """Configura la base de datos agregando columnas necesarias"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar columnas existentes
            cursor.execute("PRAGMA table_info(executed_trades)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Agregar columnas faltantes
            if 'exit_price' not in columns:
                cursor.execute("ALTER TABLE executed_trades ADD COLUMN exit_price REAL")
                print("✅ Columna 'exit_price' agregada")
            
            if 'exit_timestamp' not in columns:
                cursor.execute("ALTER TABLE executed_trades ADD COLUMN exit_timestamp TEXT")
                print("✅ Columna 'exit_timestamp' agregada")
            
            if 'pnl' not in columns:
                cursor.execute("ALTER TABLE executed_trades ADD COLUMN pnl REAL")
                print("✅ Columna 'pnl' agregada")
            
            if 'close_reason' not in columns:
                cursor.execute("ALTER TABLE executed_trades ADD COLUMN close_reason TEXT")
                print("✅ Columna 'close_reason' agregada")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error configurando base de datos: {e}")
        
    def get_current_price(self, symbol):
        """Obtiene el precio actual de Binance"""
        try:
            url = "https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': symbol}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return float(response.json()['price'])
        except Exception as e:
            print(f"❌ Error obteniendo precio de {symbol}: {e}")
            return None
    
    def calculate_pnl(self, entry_price, current_price, quantity, side):
        """Calcula el PnL de una posición"""
        if side.lower() == 'sell':
            # Para posiciones SELL: ganancia cuando el precio baja
            pnl_per_unit = entry_price - current_price
        else:
            # Para posiciones BUY: ganancia cuando el precio sube
            pnl_per_unit = current_price - entry_price
        
        total_pnl = pnl_per_unit * quantity
        pnl_percentage = (pnl_per_unit / entry_price) * 100
        
        return {
            'pnl_per_unit': pnl_per_unit,
            'total_pnl': total_pnl,
            'pnl_percentage': pnl_percentage
        }
    
    def close_position(self, position_id, current_price, reason="Manual closure"):
        """Cierra una posición y actualiza la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener datos de la posición
            cursor.execute("SELECT * FROM executed_trades WHERE id = ?", (position_id,))
            position = cursor.fetchone()
            
            if not position:
                print(f"❌ No se encontró la posición con ID {position_id}")
                return False
            
            # Calcular PnL
            entry_price = position[5]  # entry_price
            quantity = position[4]     # quantity
            side = position[3]         # side
            symbol = position[2]       # symbol
            
            pnl_data = self.calculate_pnl(entry_price, current_price, quantity, side)
            
            # Actualizar la posición en la base de datos
            close_timestamp = datetime.now().isoformat()
            cursor.execute("""
                UPDATE executed_trades 
                SET status = 'CLOSED', 
                    exit_price = ?,
                    exit_timestamp = ?,
                    pnl = ?,
                    close_reason = ?
                WHERE id = ?
            """, (current_price, close_timestamp, pnl_data['total_pnl'], reason, position_id))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Posición {symbol} cerrada exitosamente")
            print(f"   💰 PnL: ${pnl_data['total_pnl']:.2f} ({pnl_data['pnl_percentage']:.2f}%)")
            
            return {
                'symbol': symbol,
                'side': side,
                'entry_price': entry_price,
                'exit_price': current_price,
                'quantity': quantity,
                'pnl_data': pnl_data,
                'close_timestamp': close_timestamp
            }
            
        except Exception as e:
            print(f"❌ Error cerrando posición {position_id}: {e}")
            return False
    
    def close_all_active_positions(self):
        """Cierra todas las posiciones activas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener todas las posiciones activas
            cursor.execute("SELECT * FROM executed_trades WHERE status = 'ACTIVE'")
            active_positions = cursor.fetchall()
            conn.close()
            
            if not active_positions:
                print("✅ No hay posiciones activas para cerrar")
                return []
            
            print(f"🔄 Cerrando {len(active_positions)} posiciones activas...")
            print("=" * 60)
            
            closed_positions = []
            total_pnl = 0
            
            for position in active_positions:
                position_id = position[0]
                symbol = position[2]
                side = position[3]
                entry_price = position[5]
                
                print(f"\n📊 Cerrando {symbol} {side.upper()}...")
                print(f"   Precio de entrada: ${entry_price}")
                
                # Obtener precio actual
                current_price = self.get_current_price(symbol)
                if current_price is None:
                    print(f"   ❌ No se pudo obtener precio actual, saltando...")
                    continue
                
                print(f"   Precio actual: ${current_price}")
                
                # Cerrar posición
                result = self.close_position(position_id, current_price, "Manual closure - Risk management")
                
                if result:
                    closed_positions.append(result)
                    total_pnl += result['pnl_data']['total_pnl']
            
            print("\n" + "=" * 60)
            print(f"📈 RESUMEN DE CIERRE:")
            print(f"   Posiciones cerradas: {len(closed_positions)}")
            print(f"   PnL total: ${total_pnl:.2f}")
            
            if total_pnl < 0:
                print(f"   🔴 Pérdida total: ${abs(total_pnl):.2f}")
            else:
                print(f"   🟢 Ganancia total: ${total_pnl:.2f}")
            
            return closed_positions
            
        except Exception as e:
            print(f"❌ Error cerrando posiciones: {e}")
            return []
    
    def generate_closure_report(self, closed_positions):
        """Genera un reporte detallado del cierre de posiciones"""
        if not closed_positions:
            return
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_positions_closed': len(closed_positions),
            'positions': closed_positions,
            'summary': {
                'total_pnl': sum(pos['pnl_data']['total_pnl'] for pos in closed_positions),
                'average_pnl_percentage': sum(pos['pnl_data']['pnl_percentage'] for pos in closed_positions) / len(closed_positions)
            }
        }
        
        # Guardar reporte
        with open('position_closure_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\n💾 Reporte guardado en 'position_closure_report.json'")
        
        return report

def main():
    print("🚨 CIERRE MANUAL DE POSICIONES ACTIVAS")
    print("=" * 50)
    
    closer = PositionCloser()
    
    # Cerrar todas las posiciones activas
    closed_positions = closer.close_all_active_positions()
    
    # Generar reporte
    if closed_positions:
        closer.generate_closure_report(closed_positions)
    
    print("\n🏁 Proceso de cierre completado")

if __name__ == "__main__":
    main()