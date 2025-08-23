import asyncio
import os
import random
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from deap import base, creator, tools

# Importar funciones y objetos del módulo a probar
# Usar un alias para creator para evitar conflictos con pytest
from optimize_strategy import (
    RISK_THRESHOLDS_BOUNDS,
    _evaluate_thresholds_for_ga,
    creator as deap_creator,
    optimize_and_notify,
    optimize_risk_thresholds,
    optimize_risk_thresholds_ga,
    toolbox,
)


# --- Fixtures para mocks comunes ---
@pytest.fixture(autouse=True)
def mock_logger():
    """Mockea el logger para evitar escrituras reales y permitir aserciones."""
    with patch("optimize_strategy.logger", new_callable=MagicMock) as mock_log:
        yield mock_log


@pytest.fixture
def mock_ml_strategy():
    """Mockea la clase MLStrategy."""
    with patch("optimize_strategy.MLStrategy") as MockMLStrategy:
        yield MockMLStrategy


@pytest.fixture
def mock_backtester():
    """Mockea la clase Backtester."""
    with patch("optimize_strategy.Backtester") as MockBacktester:
        yield MockBacktester


@pytest.fixture
def mock_asyncio_run():
    """Mockea asyncio.run para controlar la ejecución de corutinas."""
    with patch("optimize_strategy.asyncio.run") as mock_run:
        yield mock_run


@pytest.fixture
def sample_historical_data():
    """Provee un DataFrame de pandas con datos históricos de ejemplo."""
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                pd.date_range(start="2023-01-01", periods=200, freq="H")
            ),
            "open": np.random.rand(200),
            "high": np.random.rand(200),
            "low": np.random.rand(200),
            "close": np.random.rand(200),
            "volume": np.random.rand(200),
        }
    )


# --- Tests para _evaluate_thresholds_for_ga ---


def test_evaluate_thresholds_for_ga_success(
    mock_ml_strategy,
    mock_backtester,
    mock_asyncio_run,
    mock_logger,
    sample_historical_data,
):
    # Arrange
    individual = (0.95, 0.75, 0.55)  # umbral_alto, umbral_medio, umbral_bajo
    mock_backtester_instance = mock_backtester.return_value
    mock_asyncio_run.return_value = {"total_return_pct": 10.0, "max_drawdown_pct": 2.0}

    # Act
    fitness_values = _evaluate_thresholds_for_ga(individual, sample_historical_data)

    # Assert
    mock_ml_strategy.assert_called_once_with(
        umbral_alto=individual[0], umbral_medio=individual[1], umbral_bajo=individual[2]
    )
    mock_backtester.assert_called_once_with(
        historical_data=sample_historical_data,
        initial_balance=1000.0,
        commission=0.001,
        warmup_period=100,
    )
    mock_asyncio_run.assert_called_once_with(
        mock_backtester_instance.run(mock_ml_strategy.return_value)
    )
    assert fitness_values == (10.0, -2.0)  # Maximizar retorno, minimizar drawdown
    mock_logger.debug.assert_called_with(
        f"Evaluando GA combinación: Alto={individual[0]:.2f}, Medio={individual[1]:.2f}, Bajo={individual[2]:.2f}"
    )


def test_evaluate_thresholds_for_ga_invalid_thresholds(
    mock_logger, sample_historical_data
):
    # Arrange
    individual = (0.75, 0.95, 0.55)  # Inválido: umbral_alto < umbral_medio

    # Act
    fitness_values = _evaluate_thresholds_for_ga(individual, sample_historical_data)

    # Assert
    assert fitness_values == (-float("inf"), float("inf"))  # Fitness pobre


def test_evaluate_thresholds_for_ga_backtest_no_metrics(
    mock_ml_strategy,
    mock_backtester,
    mock_asyncio_run,
    mock_logger,
    sample_historical_data,
):
    # Arrange
    individual = (0.95, 0.75, 0.55)
    mock_asyncio_run.return_value = None  # Simula que no se retornan métricas

    # Act
    fitness_values = _evaluate_thresholds_for_ga(individual, sample_historical_data)

    # Assert
    assert fitness_values == (-float("inf"), float("inf"))  # Fitness pobre
    mock_logger.debug.assert_called_once()


def test_evaluate_thresholds_for_ga_backtest_exception(
    mock_ml_strategy,
    mock_backtester,
    mock_asyncio_run,
    mock_logger,
    sample_historical_data,
):
    # Arrange
    individual = (0.95, 0.75, 0.55)
    mock_asyncio_run.side_effect = Exception("Backtest failed")

    # Act
    fitness_values = _evaluate_thresholds_for_ga(individual, sample_historical_data)

    # Assert
    assert fitness_values == (-float("inf"), float("inf"))  # Fitness pobre
    mock_logger.error.assert_called_once_with(
        f"Error durante la ejecución del backtest para GA: Backtest failed",
        exc_info=True,
    )


# --- Tests para optimize_risk_thresholds_ga ---


@pytest.mark.asyncio
async def test_optimize_risk_thresholds_ga_success(
    mock_logger, sample_historical_data, monkeypatch
):
    # Arrange
    with patch(
        "optimize_strategy.pd.read_parquet", return_value=sample_historical_data
    ), patch("optimize_strategy.tools.HallOfFame") as MockHallOfFame, patch(
        "optimize_strategy.tools.Statistics"
    ) as MockStatistics, patch(
        "optimize_strategy.algorithms.eaSimple", new_callable=MagicMock
    ) as mock_eaSimple, patch(
        "optimize_strategy.guardar_umbrales_optimizado"
    ) as mock_guardar_umbrales_optimizado, patch(
        "optimize_strategy.os.environ.get", return_value=None
    ):  # No en modo test
        # Mock de componentes de DEAP
        mock_best_individual = MagicMock()
        mock_best_individual.__iter__.return_value = iter((0.9, 0.7, 0.5))
        mock_best_individual.fitness.values = (15.0, -3.0)
        mock_hall_of_fame_instance = MagicMock()
        mock_hall_of_fame_instance.__getitem__.return_value = mock_best_individual
        MockHallOfFame.return_value = mock_hall_of_fame_instance

        mock_eaSimple.return_value = (MagicMock(), MagicMock())  # pop, log

        mock_population = [MagicMock() for _ in range(10)]  # POPULATION_SIZE = 10
        monkeypatch.setattr(
            "optimize_strategy.toolbox.population", MagicMock(return_value=mock_population)
        )

        # Act
        await optimize_risk_thresholds_ga()

        # Assert
        mock_logger.info.assert_any_call(
            "Iniciando optimización de umbrales de riesgo con Algoritmo Genético..."
        )
        mock_logger.info.assert_any_call(
            f"Datos históricos enriquecidos cargados desde Parquet. Filas: {len(sample_historical_data)}"
        )
        mock_eaSimple.assert_called_once()  # Verificar que el algoritmo GA se ejecutó
        mock_guardar_umbrales_optimizado.assert_called_once_with(
            {"umbral_alto": 0.9, "umbral_medio": 0.7, "umbral_bajo": 0.5}
        )
        mock_logger.info.assert_any_call(
            f"✅ Mejor combinación encontrada (GA): {{'umbral_alto': 0.9, 'umbral_medio': 0.7, 'umbral_bajo': 0.5}}"
        )
        mock_logger.info.assert_any_call(
            f"Fitness (Retorno, -Drawdown): (15.0, -3.0)"
        )


@pytest.mark.asyncio
async def test_optimize_risk_thresholds_ga_file_not_found(mock_logger):
    # Arrange
    with patch(
        "optimize_strategy.pd.read_parquet", side_effect=FileNotFoundError
    ) as mock_read_parquet, patch(
        "optimize_strategy.os.environ.get", return_value=None
    ):  # No en modo test
        # Act
        await optimize_risk_thresholds_ga()

        # Assert
        mock_read_parquet.assert_called_once_with(
            "data/features/klines_enriched.parquet"
        )
        mock_logger.error.assert_called_once_with(
            f"Archivo de datos enriquecidos no encontrado en data/features/klines_enriched.parquet"
        )


@pytest.mark.asyncio
async def test_optimize_risk_thresholds_ga_general_exception(
    mock_logger, sample_historical_data, monkeypatch
):
    # Arrange
    with patch(
        "optimize_strategy.pd.read_parquet", return_value=sample_historical_data
    ), patch(
        "optimize_strategy.algorithms.eaSimple", side_effect=Exception("GA failed")
    ) as mock_eaSimple, patch(
        "optimize_strategy.os.environ.get", return_value=None
    ):  # No en modo test
        
        monkeypatch.setattr("optimize_strategy.toolbox.population", MagicMock(return_value=[]))
        # Act
        await optimize_risk_thresholds_ga()

        # Assert
        mock_eaSimple.assert_called_once()
        mock_logger.error.assert_called_once_with(
            "Error inesperado durante la optimización GA: GA failed", exc_info=True
        )


@pytest.mark.asyncio
async def test_optimize_risk_thresholds_ga_test_mode(
    mock_logger, sample_historical_data, monkeypatch
):
    # Arrange
    with patch(
        "optimize_strategy.pd.read_parquet", return_value=sample_historical_data
    ), patch("optimize_strategy.tools.HallOfFame") as MockHallOfFame, patch(
        "optimize_strategy.tools.Statistics"
    ) as MockStatistics, patch(
        "optimize_strategy.algorithms.eaSimple", new_callable=MagicMock
    ) as mock_eaSimple, patch(
        "optimize_strategy.guardar_umbrales_optimizado"
    ), patch(
        "optimize_strategy.os.environ.get", return_value="True"
    ) as mock_os_environ_get:  # En modo test
        mock_best_individual = MagicMock()
        mock_best_individual.__iter__.return_value = iter((0.9, 0.7, 0.5))
        mock_best_individual.fitness.values = (15.0, -3.0)
        mock_hall_of_fame_instance = MagicMock()
        mock_hall_of_fame_instance.__getitem__.return_value = mock_best_individual
        MockHallOfFame.return_value = mock_hall_of_fame_instance

        mock_eaSimple.return_value = (MagicMock(), MagicMock())

        mock_population = [MagicMock() for _ in range(2)]  # POPULATION_SIZE = 2
        monkeypatch.setattr(
            "optimize_strategy.toolbox.population", MagicMock(return_value=mock_population)
        )

        # Act
        await optimize_risk_thresholds_ga()

        # Assert
        mock_os_environ_get.assert_called_with("ITBOT_TEST_MODE")
        # Verificar que POPULATION_SIZE y NUM_GENERATIONS se redujeron
        mock_eaSimple.assert_called_once_with(
            mock_population,
            toolbox,
            cxpb=0.7,
            mutpb=0.2,
            ngen=2,
            stats=MockStatistics.return_value,
            halloffame=mock_hall_of_fame_instance,
            verbose=True,
        )


# --- Tests para notificaciones de Telegram ---


@pytest.mark.asyncio
async def test_optimize_and_notify_confirmation_yes():
    # Arrange
    mock_bot = MagicMock()
    mock_chat_id = "123456"

    with patch("optimize_strategy.send_message") as mock_send_message, patch(
        "optimize_strategy.await_confirmation", return_value="sí"
    ), patch(
        "optimize_strategy.optimize_risk_thresholds_ga"
    ) as mock_optimize:
        # Act
        await optimize_and_notify(mock_bot, mock_chat_id)

        # Assert
        assert mock_send_message.call_count == 3
        mock_send_message.assert_any_call(
            mock_bot,
            mock_chat_id,
            "⚙️ La optimización de estrategias tomará aproximadamente 15 minutos. ¿Deseas continuar? (Responde 'sí' para proceder)",
        )
        mock_send_message.assert_any_call(
            mock_bot, mock_chat_id, "⏳ Iniciando la optimización de estrategias..."
        )
        mock_send_message.assert_any_call(
            mock_bot,
            mock_chat_id,
            "✅ Optimización completada exitosamente. Los umbrales han sido actualizados.",
        )
        mock_optimize.assert_called_once()


@pytest.mark.asyncio
async def test_optimize_and_notify_confirmation_no():
    # Arrange
    mock_bot = MagicMock()
    mock_chat_id = "123456"

    with patch("optimize_strategy.send_message") as mock_send_message, patch(
        "optimize_strategy.await_confirmation", return_value="no"
    ), patch("optimize_strategy.optimize_risk_thresholds_ga") as mock_optimize:
        # Act
        await optimize_and_notify(mock_bot, mock_chat_id)

        # Assert
        assert mock_send_message.call_count == 2
        mock_send_message.assert_any_call(
            mock_bot,
            mock_chat_id,
            "⚙️ La optimización de estrategias tomará aproximadamente 15 minutos. ¿Deseas continuar? (Responde 'sí' para proceder)",
        )
        mock_send_message.assert_any_call(
            mock_bot, mock_chat_id, "❌ Optimización cancelada por el usuario."
        )
        mock_optimize.assert_not_called()


@pytest.mark.asyncio
async def test_optimize_and_notify_error():
    # Arrange
    mock_bot = MagicMock()
    mock_chat_id = "123456"
    test_error = Exception("Test error")

    with patch("optimize_strategy.send_message") as mock_send_message, patch(
        "optimize_strategy.await_confirmation", return_value="sí"
    ), patch(
        "optimize_strategy.optimize_risk_thresholds_ga", side_effect=test_error
    ) as mock_optimize:
        # Act
        await optimize_and_notify(mock_bot, mock_chat_id)

        # Assert
        assert mock_send_message.call_count == 3
        mock_send_message.assert_any_call(
            mock_bot, mock_chat_id, "⏳ Iniciando la optimización de estrategias..."
        )
        mock_send_message.assert_any_call(
            mock_bot,
            mock_chat_id,
            f"❌ Error durante la optimización de estrategias: {test_error}",
        )
        mock_optimize.assert_called_once()


# --- Tests para componentes de DEAP ---


def test_individual_creation():
    # Arrange & Act
    individual = toolbox.individual()

    # Assert
    assert len(individual) == 3  # Debe tener 3 umbrales
    assert isinstance(individual[0], float)
    assert isinstance(individual[1], float)
    assert isinstance(individual[2], float)
    # Verificar límites
    bounds = RISK_THRESHOLDS_BOUNDS
    assert bounds["umbral_alto"]["min"] <= individual[0] <= bounds["umbral_alto"]["max"]
    assert (
        bounds["umbral_medio"]["min"] <= individual[1] <= bounds["umbral_medio"]["max"]
    )
    assert bounds["umbral_bajo"]["min"] <= individual[2] <= bounds["umbral_bajo"]["max"]


def test_population_creation():
    # Arrange & Act
    pop_size = 5
    population = toolbox.population(n=pop_size)

    # Assert
    assert len(population) == pop_size
    for ind in population:
        assert isinstance(ind, deap_creator.Individual)
        assert len(ind) == 3


def test_mate_operator():
    # Arrange
    random.seed(42)
    ind1 = deap_creator.Individual([0.90, 0.70, 0.50])
    ind2 = deap_creator.Individual([0.85, 0.65, 0.45])

    # Act
    child1, child2 = toolbox.mate(ind1, ind2)

    # Assert
    assert len(child1) == 3
    assert len(child2) == 3
    # Verificar que los valores de los hijos están entre los de los padres (cruce de mezcla)
    for i in range(3):
        min_val, max_val = min(ind1[i], ind2[i]), max(ind1[i], ind2[i])
        # Permitir que el cruce de mezcla se salga ligeramente del rango de los padres
        assert min_val - 0.1 <= child1[i] <= max_val + 0.1
        assert min_val - 0.1 <= child2[i] <= max_val + 0.1


def test_mutate_operator():
    # Arrange
    random.seed(42)
    original = deap_creator.Individual([0.90, 0.70, 0.50])
    mutated = toolbox.clone(original)

    # Act
    toolbox.mutate(mutated)

    # Assert
    assert len(mutated) == 3
    # Verificar que al menos un valor cambió (ocurrió la mutación)
    assert any(o != m for o, m in zip(original, mutated))
    # Verificar que los valores siguen dentro de rangos razonables
    for val in mutated:
        assert 0.0 <= val <= 1.0


def test_select_operator():
    # Arrange
    random.seed(42)
    population = []
    for i in range(5):
        ind = deap_creator.Individual([0.90 - i * 0.01, 0.70 - i * 0.01, 0.50 - i * 0.01])
        ind.fitness.values = (10 - i, -(2 + i))  # Valores de fitness decrecientes
        population.append(ind)

    # Act
    selected = toolbox.select(population, k=2)

    # Assert
    assert len(selected) == 2
    # La selección por torneo debe preferir individuos con mejor fitness
    assert selected[0].fitness.values[0] >= selected[1].fitness.values[0]