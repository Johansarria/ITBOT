import argparse
import asyncio
import logging
import pandas as pd
import sys
import os
from typing import Dict, Any
from typing import Dict, Any, Tuple
import numpy as np
import itertools
import random # ADDED for DEAP
from deap import base, creator, tools, algorithms # ADDED for DEAP

from build_feature_store import get_output_path as get_feature_store_path
from strategies.backtester import Backtester
from strategies.ml_strategy import MLStrategy
from utils.risk_manager import guardar_umbrales_optimizado
from utils.telegram_handler import send_message, await_confirmation
from config import settings

# Configuración del log
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Ruta a tus datos históricos
DATA_PATH = "data/analisis/historical_klines_BTCUSDT_4h_1_Jan_2022_now.csv"

# Parámetros de optimización para los umbrales de riesgo (para GA, estos son los límites del espacio de búsqueda)
RISK_THRESHOLDS_BOUNDS = {
    'umbral_alto': {'min': 0.80, 'max': 0.99},
    'umbral_medio': {'min': 0.60, 'max': 0.80},
    'umbral_bajo': {'min': 0.40, 'max': 0.60}
}

# --- DEAP Setup ---
# Define the fitness function: maximize total return, minimize max drawdown
creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0)) # Maximize return, minimize drawdown (negative weight)
# Define the individual: a list of floats (umbral_alto, umbral_medio, umbral_bajo)
# Define the fitness function: maximize Sharpe Ratio, minimize max drawdown
creator.create("FitnessMulti", base.Fitness, weights=(1.0, -0.5)) # Maximize Sharpe, minimize drawdown
# Define the individual: a list of floats (umbral_alto, umbral_medio)
creator.create("Individual", list, fitness=creator.FitnessMulti)

toolbox = base.Toolbox()

# Attribute generator: generate random float within bounds for each threshold
toolbox.register("attr_umbral_alto", random.uniform, RISK_THRESHOLDS_BOUNDS['umbral_alto']['min'], RISK_THRESHOLDS_BOUNDS['umbral_alto']['max'])
toolbox.register("attr_umbral_medio", random.uniform, RISK_THRESHOLDS_BOUNDS['umbral_medio']['min'], RISK_THRESHOLDS_BOUNDS['umbral_medio']['max'])
toolbox.register("attr_umbral_bajo", random.uniform, RISK_THRESHOLDS_BOUNDS['umbral_bajo']['min'], RISK_THRESHOLDS_BOUNDS['umbral_bajo']['max'])

# Individual creator: combine attributes to form an individual
toolbox.register("individual", tools.initCycle, creator.Individual, 
                 (toolbox.attr_umbral_alto, toolbox.attr_umbral_medio, toolbox.attr_umbral_bajo), n=1)
toolbox.register("individual", tools.initCycle, creator.Individual,
                 (toolbox.attr_umbral_alto, toolbox.attr_umbral_medio), n=1)

# Population creator
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

def _evaluate_thresholds_for_ga(individual, historical_data: pd.DataFrame):
    """
    Wrapper function to evaluate an individual (set of thresholds) for the GA.
    Returns a tuple of fitness values (total_return_pct, -max_drawdown_pct).
    Returns a tuple of fitness values (sharpe_ratio, max_drawdown_pct).
    """
    umbral_alto, umbral_medio, umbral_bajo = individual
    umbral_alto, umbral_medio = individual

    # Ensure thresholds are valid (umbral_alto > umbral_medio > umbral_bajo)
    if not (umbral_alto > umbral_medio and umbral_medio > umbral_bajo):
    # Ensure thresholds are valid (umbral_alto > umbral_medio)
    if not (umbral_alto > umbral_medio):
        # Return very poor fitness for invalid combinations
        return -float('inf'), float('inf')
        return -100.0, 100.0

    logger.debug(f"Evaluando GA combinación: Alto={umbral_alto:.2f}, Medio={umbral_medio:.2f}, Bajo={umbral_bajo:.2f}")
    logger.debug(f"Evaluando GA combinación: Alto={umbral_alto:.2f}, Medio={umbral_medio:.2f}")

    strategy = MLStrategy(
        umbral_alto=umbral_alto,
        umbral_medio=umbral_medio,
        umbral_bajo=umbral_bajo
        umbral_medio=umbral_medio
    )

    backtester = Backtester(
        historical_data=historical_data,
        initial_balance=1000.0,
        commission=0.001,
        warmup_period=100
    )

    # Use asyncio.run() to execute the async backtest in the current thread.
    # This creates a new event loop for the thread, runs the coroutine, and closes it.
    try:
        metrics = asyncio.run(backtester.run(strategy))
        
        if metrics:
            current_return = metrics.get("total_return_pct", -float('inf'))
            current_drawdown = metrics.get("max_drawdown_pct", float('inf'))
            return current_return, -current_drawdown # Negative drawdown for maximization
        if metrics and metrics.get("total_trades", 0) > 5: # Requiere un mínimo de operaciones
            sharpe = metrics.get("sharpe_ratio", -100.0)
            drawdown = metrics.get("max_drawdown_pct", 100.0)
            return sharpe, drawdown
        else:
            return -float('inf'), float('inf') # Poor fitness if backtest returns no metrics
            return -100.0, 100.0 # Poor fitness if backtest returns no metrics or not enough trades
    except Exception as e:
        logger.error(f"Error durante la ejecución del backtest para GA: {e}", exc_info=True)
        return -float('inf'), float('inf') # Poor fitness if backtest raises an exception
    logger.info(f"Evaluación completada para: Alto={umbral_alto:.2f}, Medio={umbral_medio:.2f}, Bajo={umbral_bajo:.2f})")
        return -100.0, 100.0 # Poor fitness if backtest raises an exception
    logger.info(f"Evaluación completada para: Alto={umbral_alto:.2f}, Medio={umbral_medio:.2f}")
    sys.stdout.flush()

toolbox.register("evaluate", _evaluate_thresholds_for_ga)

# Genetic operators
toolbox.register("mate", tools.cxBlend, alpha=0.5) # Blend crossover
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.05, indpb=0.1) # Gaussian mutation
toolbox.register("select", tools.selTournament, tournsize=3) # Tournament selection
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.1, indpb=0.2) # Gaussian mutation
toolbox.register("select", tools.selNSGA2) # NSGA-II selection for multi-objective

async def optimize_risk_thresholds_ga():
async def optimize_strategy_for_symbol(symbol: str, interval: str, generations: int):
    """
    Optimiza los umbrales de riesgo utilizando un Algoritmo Genético.
    Optimiza los umbrales de la estrategia ML para un símbolo específico.
    """
    logger.info("Iniciando optimización de umbrales de riesgo con Algoritmo Genético...")
    sys.stdout.flush()
    try:
        historical_data = pd.read_parquet("data/features/klines_enriched.parquet")
        feature_store_path = get_feature_store_path(symbol, interval)
        historical_data = pd.read_parquet(feature_store_path)
        logger.info(f"Datos históricos enriquecidos cargados desde Parquet. Filas: {len(historical_data)}")
        sys.stdout.flush()
    except FileNotFoundError:
        logger.error(f"Archivo de datos enriquecidos no encontrado en data/features/klines_enriched.parquet")
        logger.error(f"Archivo de datos enriquecidos no encontrado en {feature_store_path}")
        return

    # Pass historical_data to the evaluate function
    toolbox.unregister("evaluate") # Unregister the old one
    toolbox.register("evaluate", _evaluate_thresholds_for_ga, historical_data=historical_data)

    # GA parameters
    POPULATION_SIZE = 10
    NUM_GENERATIONS = 10
    POPULATION_SIZE = 40
    NUM_GENERATIONS = generations

    # Adjust GA parameters for testing environment
    if os.environ.get("ITBOT_TEST_MODE") == "True":
        POPULATION_SIZE = 2  # Reduced for faster testing
        NUM_GENERATIONS = 2  # Reduced for faster testing
    CXPB = 0.7 # Crossover probability
    CXPB = 0.6 # Crossover probability
    MUTPB = 0.2 # Mutation probability

    pop = toolbox.population(n=POPULATION_SIZE)
    hof = tools.HallOfFame(1) # To store the best individual found
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("std", np.std)
    stats.register("min", np.min)
    stats.register("max", np.max)

    # Run the GA
    try:
        pop, log = await asyncio.to_thread(
        final_pop, log = await asyncio.to_thread(
            algorithms.eaSimple,
            pop,
            toolbox,
            cxpb=CXPB,
            mutpb=MUTPB,
            ngen=NUM_GENERATIONS,
            stats=stats,
            halloffame=hof,
            verbose=True,
        )
    except Exception as e:
        logger.error(f"Error inesperado durante la optimización GA: {e}", exc_info=True)
        return

    logger.info("\n--- Resultados de la Optimización de Umbrales de Riesgo (GA) ---")
    logger.info("\n--- Resultados de la Optimización de Estrategia (GA) ---")
    sys.stdout.flush()
    best_individual = hof[0]
    umbral_alto, umbral_medio, umbral_bajo = best_individual
    umbral_alto, umbral_medio = best_individual
    best_fitness = best_individual.fitness.values

    # Guardar los umbrales optimizados
    umbrales_a_guardar = {
        "umbral_alto": round(umbral_alto, 4),
        "umbral_medio": round(umbral_medio, 4),
        "umbral_bajo": round(umbral_bajo, 4)
        "umbral_medio": round(umbral_medio, 4)
    }
    guardar_umbrales_optimizado(umbrales_a_guardar)
    logger.info(f"✅ Mejor combinación encontrada (GA): {umbrales_a_guardar}")
    # guardar_umbrales_optimizado(umbrales_a_guardar) # Opcional: guardar en un archivo
    
    print("\n" + "="*80)
    print(f"🎉 OPTIMIZACIÓN COMPLETADA PARA {symbol}-{interval} 🎉")
    print("="*80)
    print("\n🏆 MEJOR CONFIGURACIÓN ENCONTRADA:")
    print(f"   - Umbral Alto: {umbrales_a_guardar['umbral_alto']:.4f}")
    print(f"   - Umbral Medio: {umbrales_a_guardar['umbral_medio']:.4f}")
    print("\n📈 RENDIMIENTO ESPERADO CON ESTA CONFIGURACIÓN:")
    print(f"   - Sharpe Ratio: {best_fitness[0]:.2f}")
    print(f"   - Max Drawdown: {abs(best_fitness[1]):.2f}%")
    print("\n💡 ACCIÓN RECOMENDADA:")
    print("   - Actualiza los umbrales en tu archivo de configuración (`config.py`) para este par.")
    print("   - Considera crear perfiles de configuración por par si operas con varios simultáneamente.")
    print("="*80)
    
    sys.stdout.flush()
    logger.info(f"Fitness (Retorno, -Drawdown): {best_individual.fitness.values}")
    sys.stdout.flush()

async def optimize_risk_thresholds():
    """
    Prueba varias combinaciones de umbrales de riesgo y elige la mejor.
    Ahora llama a la optimización basada en GA.
    """
    await optimize_risk_thresholds_ga() # Call the GA optimization
async def main():
    parser = argparse.ArgumentParser(description="Optimiza la estrategia ML para un par específico.")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Símbolo a optimizar (ej. BTCUSDT)")
    parser.add_argument("--interval", type=str, default="1h", help="Intervalo de las velas (ej. 1h)")
    parser.add_argument("--generations", type=int, default=20, help="Número de generaciones para el algoritmo genético.")
    args = parser.parse_args()

async def optimize_and_notify(bot_instance, chat_id):
    """
    Función que envía notificaciones a través de Telegram antes, durante y después de la optimización de estrategias.
    """
    # Notificar al usuario sobre el inicio del proceso
    await send_message(bot_instance, chat_id, "⚙️ La optimización de estrategias tomará aproximadamente 15 minutos. ¿Deseas continuar? (Responde 'sí' para proceder)")
    await optimize_strategy_for_symbol(
        symbol=args.symbol,
        interval=args.interval,
        generations=args.generations
    )

    # Esperar confirmación del usuario
    confirmation = await await_confirmation(bot_instance, chat_id)
    if confirmation.lower() != 'sí':
        await send_message(bot_instance, chat_id, "❌ Optimización cancelada por el usuario.")
        return

    # Iniciar la optimización
    await send_message(bot_instance, chat_id, "⏳ Iniciando la optimización de estrategias...")
    try:
        await optimize_risk_thresholds()
        await send_message(bot_instance, chat_id, "✅ Optimización completada exitosamente. Los umbrales han sido actualizados.")
    except Exception as e:
        await send_message(bot_instance, chat_id, f"❌ Error durante la optimización de estrategias: {e}")

async def reload_data_and_notify(bot_instance, chat_id):
    """
    Función que envía notificaciones a través de Telegram antes, durante y después de recargar datos históricos.
    """
    # Notificar al usuario sobre el inicio del proceso
    await send_message(bot_instance, chat_id, "⚙️ La recarga de datos históricos tomará aproximadamente 5 minutos. ¿Deseas continuar? (Responde 'sí' para proceder)")

    # Esperar confirmación del usuario
    confirmation = await await_confirmation(bot_instance, chat_id)
    if confirmation.lower() != 'sí':
        await send_message(bot_instance, chat_id, "❌ Recarga de datos cancelada por el usuario.")
        return

    # Iniciar la recarga de datos
    # await send_message(bot_instance, chat_id, "⏳ Iniciando la recarga de datos históricos...")
    try:
        # Simular recarga de datos (reemplazar con lógica real si es necesario)
        # await asyncio.sleep(5 * 60)  # Pausa de simulación eliminada
        await send_message(bot_instance, chat_id, "✅ Recarga de datos históricos completada exitosamente.")
    except Exception as e:
        await send_message(bot_instance, chat_id, f"❌ Error durante la recarga de datos históricos: {e}")

async def main_optimization_flow():
    from aiogram import Bot

    bot = Bot(token=settings.TELEGRAM_TOKEN)
    chat_id = settings.TELEGRAM_CHAT_ID

    await optimize_and_notify(bot, chat_id)
    await reload_data_and_notify(bot, chat_id)

if __name__ == "__main__":
    asyncio.run(main_optimization_flow())
    asyncio.run(main())
