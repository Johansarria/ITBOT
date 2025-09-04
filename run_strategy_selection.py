# run_strategy_selection.py

import asyncio
import logging
import os
import sys

# --- Pre-configuración para Backtesting ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if os.getenv("DB_TYPE") == "postgresql" and not all(os.getenv(k) for k in ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]):
    print("Advertencia: Faltan variables de entorno para PostgreSQL. Forzando DB_TYPE=sqlite.")
    os.environ["DB_TYPE"] = "sqlite"

from strategies.strategy_manager import StrategyManager

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    """
    Ejecuta el proceso de selección de la mejor estrategia.
    """
    logger = logging.getLogger("StrategySelection")
    logger.info("--- Iniciando el Proceso de Selección de Estrategia ---")
    
    try:
        # Obtener la instancia del StrategyManager
        strategy_manager = StrategyManager()
        
        # Listar las estrategias descubiertas
        available_strategies = strategy_manager.list_available_strategies()
        logger.info(f"Estrategias descubiertas: {len(available_strategies)}")
        print(f"Estrategias a evaluar: {available_strategies}")

        # Ejecutar el proceso de selección
        # Esto internamente correrá el backtest para cada una y las clasificará
        best_strategy_name = await strategy_manager.select_best_strategy()
        
        print("\n--- Proceso de Evaluación Completado ---")

        # Obtener y mostrar el ranking de rendimiento
        performance_results = strategy_manager.get_strategies_with_performance()

        if not performance_results:
            print("No se pudo generar el ranking de rendimiento.")
            return

        # Ordenar por Sharpe Ratio para el reporte
        sorted_results = sorted(
            performance_results, 
            key=lambda x: (
                x.get("performance", {}).get("sharpe_ratio", -999),
                x.get("performance", {}).get("total_return_pct", -999)
            ), 
            reverse=True
        )

        print("\n--- Ranking de Estrategias (por Sharpe Ratio) ---")
        for result in sorted_results:
            name = result.get("name", "N/A")
            perf = result.get("performance", {})
            sharpe = perf.get("sharpe_ratio", "N/A")
            ret_pct = perf.get("total_return_pct", "N/A")
            trades = perf.get("total_trades", "N/A")
            win_rate = perf.get("win_rate_pct", "N/A")
            print(f"- Estrategia: {name}\n" \
                  f"  - Sharpe Ratio: {sharpe}\n" \
                  f"  - Retorno Total: {ret_pct}%\n" \
                  f"  - Tasa de Acierto: {win_rate}%\n" \
                  f"  - Operaciones Totales: {trades}\n")

        if best_strategy_name:
            print(f"\n🏆 Mejor estrategia seleccionada y activada: {best_strategy_name}")
        else:
            active_strategy = strategy_manager.get_active_strategy()
            print(f"\nℹ️ No hubo cambio de estrategia. La mejor ({sorted_results[0]['name']}) ya estaba activa.")

    except Exception as e:
        logger.exception(f"Ocurrió un error durante la selección de estrategia: {e}")

if __name__ == "__main__":
    asyncio.run(main())
