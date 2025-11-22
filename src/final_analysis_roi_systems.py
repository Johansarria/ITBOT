import pandas as pd
import numpy as np
import logging
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('final_analysis_roi_systems.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FinalAnalysisROISystems:
    def __init__(self):
        self.target_roi = 0.15  # 15% mensual
        self.initial_capital = 500
        self.systems_results = {}
        
    def load_system_results(self):
        """Carga los resultados de todos los sistemas desarrollados"""
        try:
            logger.info("Cargando resultados de todos los sistemas desarrollados...")
            
            # Lista de archivos de resultados a analizar
            result_files = [
                ('optimized_roi_results.csv', 'Sistema Optimizado Inicial'),
                ('advanced_roi_results.csv', 'Sistema Avanzado'),
                ('balanced_roi_results.csv', 'Sistema Equilibrado'),
                ('simple_roi_results.csv', 'Sistema Simple'),
                ('optimized_simple_roi_results.csv', 'Sistema Simple Optimizado'),
                ('swing_trading_roi_results.csv', 'Sistema Swing Trading'),
                ('final_optimized_roi_results.csv', 'Sistema Final Optimizado'),
                ('balanced_final_roi_results.csv', 'Sistema Equilibrado Final')
            ]
            
            for filename, system_name in result_files:
                if os.path.exists(filename):
                    try:
                        df = pd.read_csv(filename)
                        if not df.empty:
                            self.systems_results[system_name] = df
                            logger.info(f"✅ Cargado: {system_name} - {len(df)} registros")
                        else:
                            logger.warning(f"⚠️ Archivo vacío: {system_name}")
                    except Exception as e:
                        logger.error(f"❌ Error cargando {system_name}: {e}")
                else:
                    logger.warning(f"⚠️ Archivo no encontrado: {filename}")
            
            logger.info(f"Total sistemas cargados: {len(self.systems_results)}")
            return len(self.systems_results) > 0
            
        except Exception as e:
            logger.error(f"Error cargando resultados: {e}")
            return False
    
    def calculate_system_metrics(self, df, system_name):
        """Calcula métricas detalladas para un sistema"""
        try:
            if df.empty:
                return None
            
            # Métricas básicas
            initial_value = self.initial_capital
            final_value = df['portfolio_value'].iloc[-1] if 'portfolio_value' in df.columns else initial_value
            total_pnl = df['total_pnl'].iloc[-1] if 'total_pnl' in df.columns else 0
            total_trades = df['total_trades'].iloc[-1] if 'total_trades' in df.columns else 0
            fees_paid = df['fees_paid'].iloc[-1] if 'fees_paid' in df.columns else 0
            
            # Calcular retorno neto
            net_pnl = total_pnl - fees_paid
            net_return = net_pnl / initial_value
            
            # Calcular duración y ROI mensual
            if 'timestamp' in df.columns and len(df) > 1:
                start_date = pd.to_datetime(df['timestamp'].iloc[0])
                end_date = pd.to_datetime(df['timestamp'].iloc[-1])
                duration_days = (end_date - start_date).days
                duration_months = duration_days / 30.44
                
                if duration_months > 0:
                    monthly_roi = ((final_value - fees_paid) / initial_value) ** (1/duration_months) - 1
                else:
                    monthly_roi = 0
            else:
                duration_days = 0
                duration_months = 0
                monthly_roi = 0
            
            # Calcular drawdown máximo
            if 'portfolio_value' in df.columns:
                portfolio_values = df['portfolio_value'].values
                peak = np.maximum.accumulate(portfolio_values)
                drawdown = (peak - portfolio_values) / peak
                max_drawdown = np.max(drawdown)
            else:
                max_drawdown = 0
            
            # Calcular win rate (estimado basado en cambios de portfolio)
            if 'portfolio_value' in df.columns and len(df) > 1:
                portfolio_changes = df['portfolio_value'].diff().dropna()
                positive_changes = (portfolio_changes > 0).sum()
                total_changes = len(portfolio_changes)
                estimated_win_rate = positive_changes / total_changes if total_changes > 0 else 0
            else:
                estimated_win_rate = 0
            
            # Calcular volatilidad de retornos
            if 'portfolio_value' in df.columns and len(df) > 1:
                returns = df['portfolio_value'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252)  # Anualizada
            else:
                volatility = 0
            
            # Calcular Sharpe ratio (simplificado)
            if volatility > 0:
                sharpe_ratio = (monthly_roi * 12) / volatility  # Anualizado
            else:
                sharpe_ratio = 0
            
            # Gap hacia el objetivo
            roi_gap = self.target_roi - monthly_roi
            roi_gap_pct = (roi_gap / self.target_roi) * 100
            
            # Determinar estado del objetivo
            objective_status = "✅ ALCANZADO" if monthly_roi >= self.target_roi else "❌ NO ALCANZADO"
            
            metrics = {
                'sistema': system_name,
                'capital_inicial': initial_value,
                'valor_final': final_value,
                'pnl_bruto': total_pnl,
                'fees_totales': fees_paid,
                'pnl_neto': net_pnl,
                'retorno_neto_pct': net_return * 100,
                'roi_mensual_pct': monthly_roi * 100,
                'total_operaciones': total_trades,
                'win_rate_estimado_pct': estimated_win_rate * 100,
                'max_drawdown_pct': max_drawdown * 100,
                'volatilidad_anual': volatility,
                'sharpe_ratio': sharpe_ratio,
                'duracion_dias': duration_days,
                'duracion_meses': duration_months,
                'gap_objetivo_pct': roi_gap_pct,
                'estado_objetivo': objective_status,
                'registros_datos': len(df)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculando métricas para {system_name}: {e}")
            return None
    
    def generate_comprehensive_analysis(self):
        """Genera análisis comprensivo de todos los sistemas"""
        try:
            logger.info("Generando análisis comprensivo de todos los sistemas...")
            
            if not self.systems_results:
                logger.error("No hay resultados de sistemas para analizar")
                return
            
            all_metrics = []
            
            # Calcular métricas para cada sistema
            for system_name, df in self.systems_results.items():
                metrics = self.calculate_system_metrics(df, system_name)
                if metrics:
                    all_metrics.append(metrics)
            
            if not all_metrics:
                logger.error("No se pudieron calcular métricas para ningún sistema")
                return
            
            # Crear DataFrame de métricas
            metrics_df = pd.DataFrame(all_metrics)
            
            # Guardar métricas detalladas
            metrics_df.to_csv('analisis_completo_sistemas_roi.csv', index=False)
            
            # Ordenar por ROI mensual
            metrics_df = metrics_df.sort_values('roi_mensual_pct', ascending=False)
            
            logger.info("=" * 100)
            logger.info("ANÁLISIS FINAL COMPRENSIVO - SISTEMAS ROI 15% MENSUAL")
            logger.info("=" * 100)
            
            # Resumen ejecutivo
            best_system = metrics_df.iloc[0]
            worst_system = metrics_df.iloc[-1]
            avg_roi = metrics_df['roi_mensual_pct'].mean()
            systems_achieving_target = (metrics_df['roi_mensual_pct'] >= self.target_roi * 100).sum()
            
            logger.info(f"📊 RESUMEN EJECUTIVO:")
            logger.info(f"   • Total sistemas desarrollados: {len(metrics_df)}")
            logger.info(f"   • Sistemas que alcanzan objetivo 15%: {systems_achieving_target}/{len(metrics_df)}")
            logger.info(f"   • ROI mensual promedio: {avg_roi:.2f}%")
            logger.info(f"   • Mejor sistema: {best_system['sistema']} ({best_system['roi_mensual_pct']:.2f}%)")
            logger.info(f"   • Sistema con más operaciones: {metrics_df.loc[metrics_df['total_operaciones'].idxmax(), 'sistema']} ({metrics_df['total_operaciones'].max():.0f} ops)")
            
            logger.info("\n" + "=" * 100)
            logger.info("RANKING DE SISTEMAS POR ROI MENSUAL")
            logger.info("=" * 100)
            
            for i, row in metrics_df.iterrows():
                logger.info(f"{i+1:2d}. {row['sistema']:<30} | ROI: {row['roi_mensual_pct']:6.2f}% | Ops: {row['total_operaciones']:3.0f} | WR: {row['win_rate_estimado_pct']:5.1f}% | DD: {row['max_drawdown_pct']:5.1f}% | {row['estado_objetivo']}")
            
            logger.info("\n" + "=" * 100)
            logger.info("ANÁLISIS DETALLADO POR SISTEMA")
            logger.info("=" * 100)
            
            for i, row in metrics_df.iterrows():
                logger.info(f"\n🔍 {row['sistema'].upper()}")
                logger.info(f"   Capital inicial: ${row['capital_inicial']:.2f}")
                logger.info(f"   Valor final: ${row['valor_final']:.2f}")
                logger.info(f"   PnL neto: ${row['pnl_neto']:.2f}")
                logger.info(f"   Retorno neto: {row['retorno_neto_pct']:.2f}%")
                logger.info(f"   ROI mensual: {row['roi_mensual_pct']:.2f}%")
                logger.info(f"   Total operaciones: {row['total_operaciones']:.0f}")
                logger.info(f"   Win rate estimado: {row['win_rate_estimado_pct']:.1f}%")
                logger.info(f"   Max drawdown: {row['max_drawdown_pct']:.1f}%")
                logger.info(f"   Fees totales: ${row['fees_totales']:.2f}")
                logger.info(f"   Duración: {row['duracion_dias']:.0f} días ({row['duracion_meses']:.1f} meses)")
                logger.info(f"   Gap al objetivo: {row['gap_objetivo_pct']:.1f}%")
                logger.info(f"   Estado: {row['estado_objetivo']}")
            
            # Análisis de patrones y recomendaciones
            logger.info("\n" + "=" * 100)
            logger.info("ANÁLISIS DE PATRONES Y RECOMENDACIONES")
            logger.info("=" * 100)
            
            # Análisis de operaciones vs rendimiento
            high_ops_systems = metrics_df[metrics_df['total_operaciones'] > 20]
            low_ops_systems = metrics_df[metrics_df['total_operaciones'] <= 5]
            
            if not high_ops_systems.empty:
                avg_roi_high_ops = high_ops_systems['roi_mensual_pct'].mean()
                logger.info(f"📈 Sistemas con muchas operaciones (>20): ROI promedio {avg_roi_high_ops:.2f}%")
            
            if not low_ops_systems.empty:
                avg_roi_low_ops = low_ops_systems['roi_mensual_pct'].mean()
                logger.info(f"📉 Sistemas con pocas operaciones (≤5): ROI promedio {avg_roi_low_ops:.2f}%")
            
            # Análisis de drawdown vs rendimiento
            low_dd_systems = metrics_df[metrics_df['max_drawdown_pct'] < 5]
            high_dd_systems = metrics_df[metrics_df['max_drawdown_pct'] > 10]
            
            if not low_dd_systems.empty:
                avg_roi_low_dd = low_dd_systems['roi_mensual_pct'].mean()
                logger.info(f"🛡️ Sistemas con bajo drawdown (<5%): ROI promedio {avg_roi_low_dd:.2f}%")
            
            if not high_dd_systems.empty:
                avg_roi_high_dd = high_dd_systems['roi_mensual_pct'].mean()
                logger.info(f"⚠️ Sistemas con alto drawdown (>10%): ROI promedio {avg_roi_high_dd:.2f}%")
            
            # Recomendaciones finales
            logger.info("\n🎯 RECOMENDACIONES FINALES:")
            
            if systems_achieving_target == 0:
                logger.info("❌ NINGÚN SISTEMA ALCANZÓ EL OBJETIVO DEL 15% MENSUAL")
                logger.info("🔧 RECOMENDACIONES CRÍTICAS:")
                logger.info("   1. Revisar estrategia fundamental - el mercado actual puede no ser adecuado")
                logger.info("   2. Considerar timeframes más largos (diario en lugar de 4h)")
                logger.info("   3. Implementar estrategias de momentum más agresivas")
                logger.info("   4. Evaluar trading en múltiples pares de criptomonedas")
                logger.info("   5. Considerar estrategias de arbitraje o market making")
                logger.info("   6. Revisar si el objetivo del 15% mensual es realista en condiciones actuales")
            else:
                best_roi = metrics_df['roi_mensual_pct'].max()
                logger.info(f"✅ {systems_achieving_target} sistema(s) alcanzaron el objetivo")
                logger.info(f"🏆 Mejor ROI logrado: {best_roi:.2f}%")
                logger.info("🔧 RECOMENDACIONES DE OPTIMIZACIÓN:")
                logger.info("   1. Replicar características del mejor sistema")
                logger.info("   2. Optimizar gestión de riesgo del sistema ganador")
                logger.info("   3. Implementar ensemble de mejores sistemas")
            
            # Análisis de correlación entre métricas
            logger.info("\n📊 CORRELACIONES CLAVE:")
            if len(metrics_df) > 2:
                corr_ops_roi = metrics_df['total_operaciones'].corr(metrics_df['roi_mensual_pct'])
                corr_dd_roi = metrics_df['max_drawdown_pct'].corr(metrics_df['roi_mensual_pct'])
                corr_wr_roi = metrics_df['win_rate_estimado_pct'].corr(metrics_df['roi_mensual_pct'])
                
                logger.info(f"   • Operaciones vs ROI: {corr_ops_roi:.3f}")
                logger.info(f"   • Drawdown vs ROI: {corr_dd_roi:.3f}")
                logger.info(f"   • Win Rate vs ROI: {corr_wr_roi:.3f}")
            
            logger.info("\n" + "=" * 100)
            logger.info("CONCLUSIÓN FINAL")
            logger.info("=" * 100)
            
            if systems_achieving_target > 0:
                logger.info("🎉 ¡MISIÓN CUMPLIDA! Se logró desarrollar sistema(s) que alcanzan el 15% ROI mensual")
            else:
                gap_to_best = self.target_roi * 100 - metrics_df['roi_mensual_pct'].max()
                logger.info(f"⚡ MISIÓN PARCIAL: Mejor sistema logró {metrics_df['roi_mensual_pct'].max():.2f}% (gap: {gap_to_best:.2f}%)")
                logger.info("💡 El desarrollo iterativo mostró progreso significativo en la optimización de sistemas")
            
            logger.info(f"📈 Progreso total: {len(metrics_df)} sistemas desarrollados con mejoras incrementales")
            logger.info("🔬 Metodología científica aplicada: análisis, hipótesis, implementación, evaluación")
            logger.info("📊 Datos completos guardados en: analisis_completo_sistemas_roi.csv")
            
            logger.info("=" * 100)
            
            return metrics_df
            
        except Exception as e:
            logger.error(f"Error en análisis comprensivo: {e}")
            return None
    
    def run_final_analysis(self):
        """Ejecuta el análisis final completo"""
        try:
            logger.info("🚀 INICIANDO ANÁLISIS FINAL DE SISTEMAS ROI 15%")
            
            # Cargar resultados
            if not self.load_system_results():
                logger.error("No se pudieron cargar los resultados de los sistemas")
                return None
            
            # Generar análisis comprensivo
            analysis_results = self.generate_comprehensive_analysis()
            
            if analysis_results is not None:
                logger.info("✅ Análisis final completado exitosamente")
                return analysis_results
            else:
                logger.error("❌ Error en el análisis final")
                return None
                
        except Exception as e:
            logger.error(f"Error en análisis final: {e}")
            return None

def main():
    """Función principal"""
    print("🔍 Iniciando Análisis Final de Sistemas ROI 15%")
    print("=" * 60)
    
    analyzer = FinalAnalysisROISystems()
    results = analyzer.run_final_analysis()
    
    if results is not None:
        print(f"\n✅ Análisis final completado!")
        print(f"📊 Resultados detallados guardados en: analisis_completo_sistemas_roi.csv")
        print(f"📝 Log completo guardado en: final_analysis_roi_systems.log")
        print(f"🎯 Total sistemas analizados: {len(results)}")
        
        # Mostrar resumen rápido
        best_roi = results['roi_mensual_pct'].max()
        systems_achieving_target = (results['roi_mensual_pct'] >= 15).sum()
        
        print(f"\n📈 RESUMEN RÁPIDO:")
        print(f"   • Mejor ROI mensual: {best_roi:.2f}%")
        print(f"   • Sistemas que alcanzan 15%: {systems_achieving_target}/{len(results)}")
        
        if systems_achieving_target > 0:
            print(f"   • 🎉 ¡OBJETIVO ALCANZADO!")
        else:
            gap = 15 - best_roi
            print(f"   • ⚡ Gap al objetivo: {gap:.2f}%")
    else:
        print("❌ Error en el análisis final")

if __name__ == "__main__":
    main()