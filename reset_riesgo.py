# reset_riesgo.py

from utils.risk_manager import restaurar_riesgo_automatico

def main():
    """
    Resets the risk management to automatic mode.
    """
    restaurar_riesgo_automatico()
    print("El riesgo ha sido restaurado a modo automático.")

if __name__ == "__main__":
    main()
