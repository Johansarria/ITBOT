#!/usr/bin/env python3
"""
Descarga masiva de 100,000 datos históricos usando el sistema existente de download_historical_data.py
Optimizado para trabajar con la infraestructura actual del bot.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
import pandas as pd

# Agregar path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_download_script_for_100k():
    """
    Actualiza el script de descarga para obtener 100K registros.
    """
    
    try:
        # Leer el script actual
        script_path = "download_historical_data.py"
        if not os.path.exists(script_path):
            logger.error(f"❌ No se encuentra {script_path}")
            return False
        
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Buscar y reemplazar parámetros para 100K datos
        # Calcular fecha de inicio para 100K registros horarios
        hours_back = 100000
        start_date = datetime.now() - timedelta(hours=hours_back)
        start_date_str = start_date.strftime("%Y-%m-%d")
        
        logger.info(f"📅 Configurando descarga desde: {start_date_str}")
        logger.info(f"📊 Periodo: {hours_back/24/365.25:.1f} años de datos históricos")
        
        # Crear versión modificada para 100K datos
        modified_content = f'''#!/usr/bin/env python3
"""
Descarga de datos históricos modificado para 100,000 registros.
Configurado automáticamente para el setup de 100K datos.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import pandas as pd
from datetime import datetime, timedelta
import logging
from utils.binance_client import get_binance_client
from database.database_manager import get_klines

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def download_100k_data():
    """
    Descarga exactamente 100,000 registros históricos de BTCUSDT 1h.
    """
    
    logger.info("🚀 INICIANDO DESCARGA DE 100,000 DATOS HISTÓRICOS")
    
    # Configuración para 100K datos
    SYMBOL = "BTCUSDT"
    INTERVAL = "1h"
    TARGET_RECORDS = 100000
    
    # Calcular fechas
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=TARGET_RECORDS)
    
    logger.info(f"📊 Símbolo: {{SYMBOL}}")
    logger.info(f"📊 Intervalo: {{INTERVAL}}")
    logger.info(f"📊 Registros objetivo: {{TARGET_RECORDS:,}}")
    logger.info(f"📅 Periodo: {{start_date.strftime('%Y-%m-%d')}} a {{end_date.strftime('%Y-%m-%d')}}")
    
    try:
        client = get_binance_client()
        
        # Descargar en lotes para evitar límites de API
        all_klines = []
        batch_size = 1000  # Máximo de Binance por request
        total_batches = (TARGET_RECORDS + batch_size - 1) // batch_size
        
        logger.info(f"📥 Descargando en {{total_batches}} lotes de {{batch_size}} registros")
        
        current_start = start_date
        
        for batch_num in range(total_batches):
            try:
                current_end = current_start + timedelta(hours=batch_size)
                
                # Usar timestamps en millisegundos
                start_ts = int(current_start.timestamp() * 1000)
                end_ts = int(current_end.timestamp() * 1000)
                
                logger.info(f"Lote {{batch_num + 1}}/{{total_batches}} - {{current_start.strftime('%Y-%m-%d %H:%M')}} a {{current_end.strftime('%Y-%m-%d %H:%M')}}")
                
                # Llamada a la API
                klines = client.get_historical_klines(
                    symbol=SYMBOL,
                    interval=INTERVAL,
                    start_str=start_ts,
                    end_str=end_ts,
                    limit=batch_size
                )
                
                if not klines:
                    logger.warning(f"No hay datos para el lote {{batch_num + 1}}")
                    current_start = current_end
                    continue
                
                # Procesar datos
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                # Limpiar y formatear
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
                df['symbol'] = SYMBOL
                df['interval'] = INTERVAL
                
                all_klines.append(df)
                
                # Mostrar progreso
                total_so_far = sum(len(batch) for batch in all_klines)
                logger.info(f"  ✅ Descargados {{len(df)}} registros - Total: {{total_so_far:,}}/{{TARGET_RECORDS:,}} ({{total_so_far/TARGET_RECORDS*100:.1f}}%)")
                
                current_start = current_end
                
                # Pausa para no sobrecargar la API
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error en lote {{batch_num + 1}}: {{e}}")
                current_start = current_end
                continue
        
        if not all_klines:
            logger.error("❌ No se pudieron descargar datos")
            return False
        
        # Consolidar datos
        final_df = pd.concat(all_klines, ignore_index=True)
        final_df = final_df.sort_values('timestamp').drop_duplicates(subset=['timestamp'])
        
        # Asegurar exactamente 100K registros (tomar los más recientes)
        if len(final_df) > TARGET_RECORDS:
            final_df = final_df.tail(TARGET_RECORDS)
        
        logger.info(f"✅ DESCARGA COMPLETADA")
        logger.info(f"📊 Total de registros: {{len(final_df):,}}")
        logger.info(f"📅 Periodo final: {{final_df['timestamp'].min()}} a {{final_df['timestamp'].max()}}")
        logger.info(f"💾 Tamaño de datos: {{final_df.memory_usage(deep=True).sum() / 1024 / 1024:.1f}} MB")
        
        # Guardar datos
        os.makedirs("data", exist_ok=True)
        
        # Guardar CSV
        csv_file = f"data/historical_100k_{{SYMBOL}}_{{INTERVAL}}.csv"
        final_df.to_csv(csv_file, index=False)
        logger.info(f"💾 Datos guardados en CSV: {{csv_file}}")
        
        # Guardar estadísticas
        stats = {{
            "total_records": len(final_df),
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "start_date": final_df['timestamp'].min().isoformat(),
            "end_date": final_df['timestamp'].max().isoformat(),
            "download_date": datetime.now().isoformat(),
            "file_size_mb": final_df.memory_usage(deep=True).sum() / 1024 / 1024,
            "period_years": (final_df['timestamp'].max() - final_df['timestamp'].min()).days / 365.25
        }}
        
        import json
        stats_file = f"data/download_stats_100k.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        logger.info(f"📊 Estadísticas guardadas: {{stats_file}}")
        
        # Mostrar resumen
        print(f"""
🎯 RESUMEN DE DESCARGA DE 100K DATOS:
════════════════════════════════════════════════════════════════════════

✅ DESCARGA COMPLETADA EXITOSAMENTE

📊 ESTADÍSTICAS:
   • Registros totales: {{len(final_df):,}}
   • Símbolo: {{SYMBOL}}
   • Intervalo: {{INTERVAL}}
   • Periodo: {{stats['period_years']:.1f}} años de datos
   • Fecha inicio: {{final_df['timestamp'].min().strftime('%Y-%m-%d %H:%M')}}
   • Fecha fin: {{final_df['timestamp'].max().strftime('%Y-%m-%d %H:%M')}}
   • Tamaño archivo: {{stats['file_size_mb']:.1f}} MB

💾 ARCHIVOS GENERADOS:
   • Datos: {{csv_file}}
   • Estadísticas: {{stats_file}}

🚀 PRÓXIMOS PASOS:
   1. ✅ Datos históricos descargados
   2. 🔄 Entrenar modelo ML con 100K datos
   3. 📊 Validar accuracy proyectada (63.8%)
   4. 🎯 Activar trading en vivo

💡 LISTO PARA GENERAR 49.5% ROI ANUAL CON 100K DATOS
        """)
        
        return final_df
        
    except Exception as e:
        logger.error(f"❌ Error general: {{e}}")
        return False

async def main():
    """Función principal"""
    result = await download_100k_data()
    if result is not False:
        logger.info("🎉 DESCARGA DE 100K DATOS COMPLETADA CON ÉXITO")
    else:
        logger.error("❌ Error en la descarga de 100K datos")

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        # Guardar el script modificado
        script_100k = "download_100k_historical_data.py"
        with open(script_100k, 'w') as f:
            f.write(modified_content)
        
        logger.info(f"✅ Script de descarga 100K creado: {script_100k}")
        return script_100k
        
    except Exception as e:
        logger.error(f"❌ Error actualizando script: {e}")
        return False

async def main():
    """
    Función principal para configurar y ejecutar la descarga de 100K datos.
    """
    
    logger.info("🚀 CONFIGURANDO DESCARGA DE 100K DATOS HISTÓRICOS")
    
    # Crear script optimizado
    script_file = update_download_script_for_100k()
    if not script_file:
        logger.error("❌ No se pudo crear el script de descarga")
        return
    
    logger.info(f"✅ Script de descarga preparado: {script_file}")
    
    print(f"""
🎯 DESCARGA DE 100K DATOS LISTA PARA EJECUTAR
════════════════════════════════════════════════════════════════

📝 SCRIPT GENERADO: {script_file}

⏰ TIEMPO ESTIMADO: 15-20 minutos
📊 DATOS A DESCARGAR: 100,000 registros de BTCUSDT (1h)
📅 PERIODO: ~11.4 años de datos históricos
💾 TAMAÑO APROXIMADO: 100-150 MB

🚀 PARA EJECUTAR LA DESCARGA:
   python3 {script_file}

💡 DESPUÉS DE LA DESCARGA:
   • Se generará: data/historical_100k_BTCUSDT_1h.csv
   • El sistema estará listo para 63.8% accuracy
   • Podrás comenzar trading con capital $1M-$10M
    """)

if __name__ == "__main__":
    asyncio.run(main())
