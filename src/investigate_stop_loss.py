"""
Script para investigar por qué el stop loss no se activó automáticamente
"""

import sqlite3
import requests
import json
from datetime import datetime, timedelta
import os

class StopLossInvestigator:
    def __init__(self, db_path="auto_trading_alerts.db"):
        self.db_path = db_path
        
    def get_position_details(self):
        """Obtiene detalles de las posiciones cerradas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, symbol, side, quantity, entry_price, stop_loss, take_profit, 
                       timestamp, status, exit_price, exit_timestamp, pnl, close_reason
                FROM executed_trades 
                WHERE close_reason = 'Manual closure - Risk management'
                ORDER BY id
            """)
            
            positions = cursor.fetchall()
            conn.close()
            
            return positions
            
        except Exception as e:
            print(f"❌ Error obteniendo detalles de posiciones: {e}")
            return []
    
    def get_historical_prices(self, symbol, start_time, end_time):
        """Obtiene precios históricos de Binance para verificar si se alcanzó el stop loss"""
        try:
            # Convertir timestamps a milisegundos
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': '1h',  # Intervalos de 1 hora
                'startTime': start_ms,
                'endTime': end_ms,
                'limit': 1000
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            klines = response.json()
            
            # Procesar datos: [timestamp, open, high, low, close, volume, ...]
            price_data = []
            for kline in klines:
                price_data.append({
                    'timestamp': datetime.fromtimestamp(kline[0] / 1000),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            return price_data
            
        except Exception as e:
            print(f"❌ Error obteniendo precios históricos de {symbol}: {e}")
            return []
    
    def check_stop_loss_trigger(self, position, price_data):
        """Verifica si el stop loss debería haberse activado"""
        symbol = position[1]
        side = position[2]
        entry_price = position[4]
        stop_loss = position[5]
        
        if not stop_loss:
            return {
                'should_trigger': False,
                'reason': 'No se definió stop loss',
                'triggered_at': None,
                'trigger_price': None
            }
        
        triggered_at = None
        trigger_price = None
        
        for candle in price_data:
            if side.lower() == 'sell':
                # Para posiciones SELL, stop loss se activa cuando el precio sube
                if candle['high'] >= stop_loss:
                    triggered_at = candle['timestamp']
                    trigger_price = candle['high']
                    break
            else:
                # Para posiciones BUY, stop loss se activa cuando el precio baja
                if candle['low'] <= stop_loss:
                    triggered_at = candle['timestamp']
                    trigger_price = candle['low']
                    break
        
        return {
            'should_trigger': triggered_at is not None,
            'reason': 'Stop loss alcanzado' if triggered_at else 'Stop loss no alcanzado',
            'triggered_at': triggered_at,
            'trigger_price': trigger_price
        }
    
    def check_system_files(self):
        """Verifica si existen archivos del sistema de trading automático"""
        files_to_check = [
            'alerta_auto_trading_integrada.py',
            'auto_trading_alerts.db',
            'trading_bot.py',
            'stop_loss_monitor.py'
        ]
        
        file_status = {}
        for file in files_to_check:
            file_path = os.path.join(os.getcwd(), file)
            file_status[file] = {
                'exists': os.path.exists(file_path),
                'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat() if os.path.exists(file_path) else None
            }
        
        return file_status
    
    def search_stop_loss_logic(self):
        """Busca lógica de stop loss en los archivos del sistema"""
        files_to_search = [
            'alerta_auto_trading_integrada.py',
            'trading_bot.py',
            'stop_loss_monitor.py'
        ]
        
        stop_loss_references = {}
        
        for file in files_to_search:
            if os.path.exists(file):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Buscar referencias a stop loss
                    lines_with_stop_loss = []
                    for i, line in enumerate(content.split('\n'), 1):
                        if 'stop_loss' in line.lower() or 'stop loss' in line.lower():
                            lines_with_stop_loss.append({
                                'line_number': i,
                                'content': line.strip()
                            })
                    
                    stop_loss_references[file] = lines_with_stop_loss
                    
                except Exception as e:
                    stop_loss_references[file] = f"Error leyendo archivo: {e}"
        
        return stop_loss_references
    
    def generate_investigation_report(self):
        """Genera un reporte completo de la investigación"""
        print("🔍 INVESTIGACIÓN DE STOP LOSS")
        print("=" * 60)
        
        # 1. Obtener detalles de posiciones
        positions = self.get_position_details()
        
        if not positions:
            print("❌ No se encontraron posiciones para investigar")
            return
        
        investigation_results = []
        
        for position in positions:
            position_id = position[0]
            symbol = position[1]
            side = position[2]
            entry_price = position[4]
            stop_loss = position[5]
            entry_timestamp = datetime.fromisoformat(position[7])
            exit_timestamp = datetime.fromisoformat(position[10])
            
            print(f"\n📊 Investigando {symbol} {side.upper()} (ID: {position_id})")
            print(f"   Precio entrada: ${entry_price}")
            print(f"   Stop loss: ${stop_loss if stop_loss else 'No definido'}")
            print(f"   Período: {entry_timestamp} - {exit_timestamp}")
            
            # Obtener precios históricos
            price_data = self.get_historical_prices(symbol, entry_timestamp, exit_timestamp)
            
            if price_data:
                print(f"   📈 Datos históricos: {len(price_data)} velas obtenidas")
                
                # Verificar si se activó el stop loss
                stop_loss_check = self.check_stop_loss_trigger(position, price_data)
                
                print(f"   🎯 Stop loss debería activarse: {'SÍ' if stop_loss_check['should_trigger'] else 'NO'}")
                print(f"   📝 Razón: {stop_loss_check['reason']}")
                
                if stop_loss_check['triggered_at']:
                    print(f"   ⏰ Momento de activación: {stop_loss_check['triggered_at']}")
                    print(f"   💰 Precio de activación: ${stop_loss_check['trigger_price']}")
                
                investigation_results.append({
                    'position': position,
                    'price_data_count': len(price_data),
                    'stop_loss_analysis': stop_loss_check
                })
            else:
                print(f"   ❌ No se pudieron obtener datos históricos")
        
        # 2. Verificar archivos del sistema
        print(f"\n🗂️ VERIFICACIÓN DE ARCHIVOS DEL SISTEMA")
        print("-" * 40)
        
        file_status = self.check_system_files()
        for file, status in file_status.items():
            if status['exists']:
                print(f"✅ {file} - Tamaño: {status['size']} bytes - Modificado: {status['modified']}")
            else:
                print(f"❌ {file} - No encontrado")
        
        # 3. Buscar lógica de stop loss
        print(f"\n🔍 BÚSQUEDA DE LÓGICA DE STOP LOSS")
        print("-" * 40)
        
        stop_loss_refs = self.search_stop_loss_logic()
        for file, refs in stop_loss_refs.items():
            if isinstance(refs, list):
                if refs:
                    print(f"\n📄 {file}:")
                    for ref in refs[:5]:  # Mostrar solo las primeras 5 referencias
                        print(f"   Línea {ref['line_number']}: {ref['content']}")
                    if len(refs) > 5:
                        print(f"   ... y {len(refs) - 5} referencias más")
                else:
                    print(f"📄 {file}: No se encontraron referencias a stop loss")
            else:
                print(f"📄 {file}: {refs}")
        
        # 4. Generar conclusiones
        print(f"\n🎯 CONCLUSIONES")
        print("-" * 40)
        
        conclusions = []
        
        # Verificar si hay sistema de monitoreo activo
        if not file_status.get('stop_loss_monitor.py', {}).get('exists', False):
            conclusions.append("❌ No se encontró archivo de monitoreo de stop loss")
        
        # Verificar si las posiciones tenían stop loss definido
        positions_without_stop_loss = [p for p in positions if not p[5]]
        if positions_without_stop_loss:
            conclusions.append(f"⚠️ {len(positions_without_stop_loss)} posiciones sin stop loss definido")
        
        # Verificar si el stop loss se debería haber activado
        should_trigger_count = sum(1 for result in investigation_results 
                                 if result['stop_loss_analysis']['should_trigger'])
        if should_trigger_count > 0:
            conclusions.append(f"🚨 {should_trigger_count} posiciones deberían haber activado stop loss")
        
        for conclusion in conclusions:
            print(f"   {conclusion}")
        
        # Guardar reporte
        report = {
            'timestamp': datetime.now().isoformat(),
            'positions_investigated': len(positions),
            'investigation_results': investigation_results,
            'file_status': file_status,
            'stop_loss_references': stop_loss_refs,
            'conclusions': conclusions
        }
        
        with open('stop_loss_investigation_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\n💾 Reporte completo guardado en 'stop_loss_investigation_report.json'")
        
        return report

def main():
    investigator = StopLossInvestigator()
    investigator.generate_investigation_report()

if __name__ == "__main__":
    main()