import sys
import os
import argparse

# Añadir el directorio raíz al path para poder importar el módulo
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_path not in sys.path:
    sys.path.append(root_path)

from modules.node_anomaly.node_detector import NodeAnomalyDetector
from modules.node_anomaly.models import DetectionConfig
from sklearn.cluster import KMeans


def main():
    parser = argparse.ArgumentParser(
        description="Radar de Anomalías para Nodos (Mantenimiento Preventivo)"
    )
    parser.add_argument(
        "--data",
        type=str,
        default=r"C:\MLpractica2\data\processed\datos_jira_regresion.csv",
        help="Ruta al archivo CSV de datos"
    )
    parser.add_argument(
        "--clusters", type=int, default=3, help="Número de clusters"
    )
    parser.add_argument(
        "--threshold", type=int, default=5, help="Umbral mínimo"
    )

    args = parser.parse_args()

    print("1. INICIANDO RADAR DE ANOMALÍAS (Mantenimiento Preventivo)...")

    config = DetectionConfig(
        data_path=args.data,
        n_clusters=args.clusters,
        min_fallas_threshold=args.threshold
    )

    try:
        model = KMeans(
            n_clusters=config.n_clusters,
            random_state=config.random_state,
            n_init=10
        )
        detector = NodeAnomalyDetector(config, model)

        print("2. CONSTRUYENDO PERFILES DE SALUD POR NODO...")
        detector.load_and_prepare_data()

        print("\n3. AGRUPACIÓN ESPACIAL (Clustering K-Means)...")
        detector.train()

        critical_nodes = detector.get_critical_nodes(top_n=10)

        print("\n" + "="*65)
        print(" [!] RADAR DE MANTENIMIENTO PREVENTIVO (BOMBAS DE TIEMPO)")
        print("="*65)
        print(
            f"La IA ha detectado {len(critical_nodes)} Nodos "
            "con comportamiento anómalo y degradación.\n"
        )

        print(
            f"{'NODO AFECTADO':<30} | {'TOTAL FALLAS':<14} | {'% CRÍTICAS':<10}"
        )
        print("-" * 65)
        for node in critical_nodes:
            print(
                f"{node.nodo_id[:28]:<30} | "
                f"{node.total_fallas:<14} | "
                f"{node.porcentaje_critico:.1f}%"
            )

        print("="*65)
        print(
            ">>> Acción recomendada: Enviar cuadrillas a revisar "
            "empalmes y potencia en estos nodos."
        )

    except Exception as e:
        print(f"\n[X] Error durante la ejecución: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
