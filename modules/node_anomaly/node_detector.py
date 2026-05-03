import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from typing import List, Tuple
import logging
from .models import NodeProfile, DetectionConfig, ClusteringModel

# Configuración de logging básica
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class NodeAnomalyDetector:
    """
    Detector de anomalías para nodos de red utilizando K-Means.
    Refactorizado para cumplir con SOLID y AGENTES.md.
    """

    def __init__(self, config: DetectionConfig, model: ClusteringModel):
        self.config = config
        self.scaler = StandardScaler()
        self.model = model
        self._profiles_df: pd.DataFrame = pd.DataFrame()
        self._is_trained = False

    def load_and_prepare_data(self) -> pd.DataFrame:
        """Carga los datos y genera los perfiles de salud por nodo."""
        try:
            logger.info(f"Cargando datos desde {self.config.data_path}")
            df = pd.read_csv(self.config.data_path)
            
            # Agregación de perfiles
            profiles = df.groupby('Nodo').agg(
                total_fallas=('Tipo_Falla', 'count'),
                tiempo_promedio_minutos=('Minutos_Resolucion', 'mean'),
                fallas_criticas=(
                    'Prioridad', 
                    lambda x: (x.str.upper() == 'ALTA').sum() + 
                              (x.str.upper() == 'CRÍTICA').sum()
                )
            ).reset_index()

            # Cálculo de porcentaje crítico
            profiles['porcentaje_critico'] = (
                profiles['fallas_criticas'] / profiles['total_fallas']
            ) * 100
            
            # Filtrado por umbral mínimo
            initial_count = len(profiles)
            profiles = profiles[
                profiles['total_fallas'] > self.config.min_fallas_threshold
            ].reset_index(drop=True)
            logger.info(
                f"Nodos filtrados: {initial_count} -> {len(profiles)} "
                f"(umbral > {self.config.min_fallas_threshold})"
            )
            
            self._profiles_df = profiles
            return profiles
            
        except FileNotFoundError:
            logger.error(f"Error: No se encontró el archivo en {self.config.data_path}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al preparar datos: {str(e)}")
            raise

    def train(self) -> None:
        """
        Estandariza los datos y entrena el modelo de clustering.
        
        Nota de Negocio: Se utiliza estandarización (Z-score) porque las variables tienen escalas
        muy diferentes (ej. total fallas vs porcentaje). Sin esto, la variable con mayor magnitud
        dominaría el cálculo de distancia en el algoritmo de clustering.
        """
        if self._profiles_df.empty:
            raise ValueError("No hay datos cargados para entrenar el modelo.")

        features = ['total_fallas', 'tiempo_promedio_minutos', 'porcentaje_critico']
        data_to_scale = self._profiles_df[features]
        
        scaled_data = self.scaler.fit_transform(data_to_scale)
        self._profiles_df['grupo_ia'] = self.model.fit_predict(scaled_data)
        self._is_trained = True
        logger.info("Modelo entrenado exitosamente.")

    def get_critical_nodes(self, top_n: int = 10) -> List[NodeProfile]:
        """
        Identifica el cluster crítico y devuelve el top N de nodos en riesgo.
        
        Lógica de Negocio: 
        1. Se asume que el cluster con el promedio de 'total_fallas' más alto es la "Zona Roja".
        2. Dentro de ese cluster, se priorizan los nodos por volumen de fallas absoluto.
        Esto permite separar el ruido (fallas aisladas) de la degradación sistemática del nodo.
        """
        if not self._is_trained:
            raise RuntimeError("El modelo debe ser entrenado antes de obtener resultados.")

        # El grupo crítico es aquel con el promedio de fallas más alto
        promedios = self._profiles_df.groupby('grupo_ia')['total_fallas'].mean()
        grupo_critico = promedios.idxmax()

        nodos_peligro_df = self._profiles_df[
            self._profiles_df['grupo_ia'] == grupo_critico
        ]
        nodos_peligro_df = nodos_peligro_df.sort_values(
            by='total_fallas', ascending=False
        ).head(top_n)

        results = []
        for _, row in nodos_peligro_df.iterrows():
            results.append(NodeProfile(
                nodo_id=str(row['Nodo']),
                total_fallas=int(row['total_fallas']),
                tiempo_promedio_minutos=float(row['tiempo_promedio_minutos']),
                fallas_criticas=int(row['fallas_criticas']),
                porcentaje_critico=float(row['porcentaje_critico']),
                grupo_ia=int(row['grupo_ia'])
            ))

        return results
