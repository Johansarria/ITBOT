# tests/test_order_executor.py

import pytest
from utils.order_executor import calcular_cantidad_operar

# Casos de prueba parametrizados para cubrir diferentes escenarios
@pytest.mark.parametrize("balance, riesgo_pct, escudo, expected_amount", [
    # Escenario 1: Sin escudo, riesgo estándar
    (1000.0, 0.01, "ninguno", 10.00),
    
    # Escenario 2: Escudo conservador, reduce el riesgo a la mitad
    (1000.0, 0.01, "conservador", 5.00),
    
    # Escenario 3: Escudo agresivo, aumenta el riesgo en un 50%
    (1000.0, 0.01, "agresivo", 15.00),
    
    # Escenario 4: Riesgo más alto sin escudo
    (5000.0, 0.05, "ninguno", 250.00),
    
    # Escenario 5: Riesgo más alto con escudo conservador
    (5000.0, 0.05, "conservador", 125.00),
    
    # Escenario 6: Riesgo más alto con escudo agresivo
    (5000.0, 0.05, "agresivo", 375.00),
    
    # Escenario 7: Caso con balance cero
    (0.0, 0.02, "ninguno", 0.00),
    
    # Escenario 8: Caso con riesgo cero
    (1000.0, 0.0, "agresivo", 0.00),
    
    # Escenario 9: Caso con decimales
    (1234.56, 0.1, "ninguno", 123.46), # 123.456 se redondea a 123.46
])
def test_calcular_cantidad_operar(balance, riesgo_pct, escudo, expected_amount):
    """
    Verifica que la función `calcular_cantidad_operar` devuelve la cantidad correcta
    basada en el balance, el porcentaje de riesgo y el escudo aplicado.
    """
    # Llamar a la función que se está probando
    calculated_amount = calcular_cantidad_operar(balance, riesgo_pct, escudo)
    
    # Afirmar que el resultado calculado es igual al esperado
    assert calculated_amount == expected_amount

# Podríamos añadir más tests para otras funciones de este módulo en el futuro
