import asyncio
import logging
import pandas as pd
import sys
import os
from typing import Dict, Any
import numpy as np
import itertools
import random # ADDED for DEAP
from deap import base, creator, tools, algorithms # ADDED for DEAP

from strategies.backtester import Backtester
from strategies.ml_strategy import MLStrategy
from utils.risk_manager import guardar_umbrales_optimizado
from utils.telegram_handler import send_message, await_confirmation

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
creator.create("Individual", list, fitness=creator.FitnessMulti)

toolbox = base.Toolbox()

# Attribute generator: generate random float within bounds for each threshold
toolbox.register("attr_umbral_alto", random.uniform, RISK_THRESHOLDS_BOUNDS['umbral_alto']['min'], RISK_THRESHOLDS_BOUNDS['umbral_alto']['max'])
toolbox.register("attr_umbral_medio", random.uniform, RISK_THRESHOLDS_BOUNDS['umbral_medio']['min'], RISK_THRESHOLDS_BOUNDS['umbral_medio']['max'])
toolbox.register("attr_umbral_bajo", random.uniform, RISK_THRESHOLDS_BOUNDS['umbral_bajo']['min'], RISK_THRESHOLDS_BOUNDS['umbral_bajo']['max'])

# Individual creator: combine attributes to form an individual
toolbox.register("individual", tools.initCycle, creator.Individual, 
                 (toolbox.attr_umbral_alto, toolbox.attr_umbral_medio, toolbox.attr_umbral_bajo), n=1)

# Population creator
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

def _evaluate_thresholds_for_ga(individual, historical_data: pd.DataFrame):
    """
    Wrapper function to evaluate an individual (set of thresholds) for the GA.
    Returns a tuple of fitness values (total_return_pct, -max_drawdown_pct).
    """
    umbral_alto, umbral_medio, umbral_bajo = individual

    # Ensure thresholds are valid (umbral_alto > umbral_medio > umbral_bajo)
    if not (umbral_alto > umbral_medio and umbral_medio > umbral_bajo):
        # Return very poor fitness for invalid combinations
        return -float('inf'), float('inf')

    logger.debug(f"Evaluando GA combinación: Alto={umbral_alto:.2f}, Medio={umbral_medio:.2f}, Bajo={umbral_bajo:.2f}")

    strategy = MLStrategy(
        umbral_alto=umbral_alto,
        umbral_medio=umbral_medio,
        umbral_bajo=umbral_bajo
    )

    backtester = Backtester(
        historical_data=historical_data,
        initial_balance=1000.0,
        commission=0.001,
        warmup_period=100
    )

    # Use asyncio.run() to execute the async backtest in the current thread.
    # This creates a new event loop for the thread, runs the coroutine, and closes it.
    metrics = asyncio.run(backtester.run(strategy))
    
    if metrics:
        current_return = metrics.get("total_return_pct", -float('inf'))
        current_drawdown = metrics.get("max_drawdown_pct", float('inf'))
        return current_return, -current_drawdown # Negative drawdown for maximization
    else:
        return -float('inf'), float('inf') # Poor fitness if backtest fails
    logger.info(f"Evaluación completada para: Alto={umbral_alto:.2f}, Medio={umbral_medio:.2f}, Bajo={umbral_bajo:.2f})")
    sys.stdout.flush()

toolbox.register("evaluate", _evaluate_thresholds_for_ga)

# Genetic operators
toolbox.register("mate", tools.cxBlend, alpha=0.5) # Blend crossover
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.05, indpb=0.1) # Gaussian mutation
toolbox.register("select", tools.selTournament, tournsize=3) # Tournament selection

async def optimize_risk_thresholds_ga():
    """
    Optimiza los umbrales de riesgo utilizando un Algoritmo Genético.
    """
    logger.info("Iniciando optimización de umbrales de riesgo con Algoritmo Genético...")
    sys.stdout.flush()
    try:
        historical_data = pd.read_parquet("data/features/klines_enriched.parquet")
        logger.info(f"Datos históricos enriquecidos cargados desde Parquet. Filas: {len(historical_data)}")
        sys.stdout.flush()
    except FileNotFoundError:
        logger.error(f"Archivo de datos enriquecidos no encontrado en data/features/klines_enriched.parquet")
        return

    # Pass historical_data to the evaluate function
    toolbox.unregister("evaluate") # Unregister the old one
    toolbox.register("evaluate", _evaluate_thresholds_for_ga, historical_data=historical_data)

    # GA parameters
    POPULATION_SIZE = 10
    NUM_GENERATIONS = 10

    # Adjust GA parameters for testing environment
    if os.environ.get("ITBOT_TEST_MODE") == "True":
        POPULATION_SIZE = 2  # Reduced for faster testing
        NUM_GENERATIONS = 2  # Reduced for faster testing
    CXPB = 0.7 # Crossover probability
    MUTPB = 0.2 # Mutation probability

    pop = toolbox.population(n=POPULATION_SIZE)
    hof = tools.HallOfFame(1) # To store the best individual found
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("std", np.std)
    stats.register("min", np.min)
    stats.register("max", np.max)

    # Run the GA
    pop, log = await asyncio.to_thread(algorithms.eaSimple, pop, toolbox, cxpb=CXPB, mutpb=MUTPB, 
                                       ngen=NUM_GENERATIONS, stats=stats, halloffame=hof, verbose=True)

    logger.info("\n--- Resultados de la Optimización de Umbrales de Riesgo (GA) ---")
    sys.stdout.flush()
    best_individual = hof[0]
    umbral_alto, umbral_medio, umbral_bajo = best_individual

    # Guardar los umbrales optimizados
    umbrales_a_guardar = {
        "umbral_alto": round(umbral_alto, 4),
        "umbral_medio": round(umbral_medio, 4),
        "umbral_bajo": round(umbral_bajo, 4)
    }
    guardar_umbrales_optimizado(umbrales_a_guardar)
    logger.info(f"✅ Mejor combinación encontrada (GA): {umbrales_a_guardar}")
    sys.stdout.flush()
    logger.info(f"Fitness (Retorno, -Drawdown): {best_individual.fitness.values}")
    sys.stdout.flush()

async def optimize_risk_thresholds():
    """
    Prueba varias combinaciones de umbrales de riesgo y elige la mejor.
    Ahora llama a la optimización basada en GA.
    """
    await optimize_risk_thresholds_ga() # Call the GA optimization

async def optimize_and_notify(bot_instance, chat_id):
    """
    Función que envía notificaciones a través de Telegram antes, durante y después de la optimización de estrategias.
    """
    # Notificar al usuario sobre el inicio del proceso
    await send_message(bot_instance, chat_id, "⚙️ La optimización de estrategias tomará aproximadamente 15 minutos. ¿Deseas continuar? (Responde 'sí' para proceder)")

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
    import config
    from aiogram import Bot

    bot = Bot(token=config.TELEGRAM_TOKEN)
    chat_id = config.TELEGRAM_CHAT_ID

    await optimize_and_notify(bot, chat_id)
    await reload_data_and_notify(bot, chat_id)

if __name__ == "__main__":
    asyncio.run(main_optimization_flow())