# /src/analisis_integral_mercado_paper.py

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from binance_data_provider import BinanceDataProvider
from paper_trading_system import PaperTradingEngine, OrderType

class AnalisisIntegralMercadoPaper:
    def __init__(self):
        self.data_provider = BinanceDataProvider()
        
        # Cargar configuración correcta
        config_file = 'sicar_config.json'
        initial_capital = 250.0  # Valor por defecto según análisis previo
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                initial_capital = config.get('PAPER_TRADING_CONFIG', {}).get('initial_capital', 200.0)
        
        self.paper_engine = PaperTradingEngine(initial_capital=initial_capital)
        
        # Bases de datos disponibles
        self.db_paths = {
            'rompimientos': 'analisis_rompimientos_tiempo_real.db',
            'rupturas_velas': 'detector_rupturas_velas.db',
            'ia_continua': 'ia_continua_detecciones.db',
            'monitoreo': 'proactive_monitoring.db',
            'logging': 'advanced_logging.db'
        }
        
        # Símbolos principales
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 
                       'BNBUSDT', 'XRPUSDT', 'LINKUSDT', 'AVAXUSDT']
    
    def analizar_estado_mercado_actual(self):
        """Analiza el estado actual del mercado basado en todos los sistemas"""
        print("\n" + "="*100)
        print("📊 ANÁLISIS INTEGRAL DEL MERCADO ACTUAL")
        print("="*100)
        print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Análisis de rompimientos
        rompimientos_data = self._analizar_rompimientos()
        
        # 2. Análisis de rupturas de velas
        rupturas_data = self._analizar_rupturas_velas()
        
        # 3. Análisis de IA continua
        ia_data = self._analizar_ia_continua()
        
        # 4. Análisis de monitoreo proactivo
        monitoreo_data = self._analizar_monitoreo_proactivo()
        
        # 5. Consolidar análisis
        analisis_consolidado = self._consolidar_analisis(
            rompimientos_data, rupturas_data, ia_data, monitoreo_data
        )
        
        return analisis_consolidado
    
    def _analizar_rompimientos(self):
        """Analiza datos de rompimientos en tiempo real"""
        try:
            conn = sqlite3.connect(self.db_paths['rompimientos'])
            
            # Datos de las últimas 2 horas
            query = '''
                SELECT * FROM rompimientos_analisis 
                WHERE timestamp >= datetime('now', '-2 hours')
                ORDER BY timestamp DESC
            '''
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return {'status': 'sin_datos', 'total': 0}
            
            # Análisis estadístico
            stats = {
                'total_analisis': len(df),
                'rupturas_alcistas': len(df[df['tipo_rompimiento'].str.contains('ALCISTA', na=False)]),
                'rupturas_bajistas': len(df[df['tipo_rompimiento'].str.contains('BAJISTA', na=False)]),
                'neutrales': len(df[df['tipo_rompimiento'] == 'NEUTRAL']),
                'confianza_promedio': df['confianza'].mean(),
                'rsi_promedio': df['rsi'].mean(),
                'volumen_ratio_promedio': df['volumen_ratio'].mean(),
                'simbolos_activos': df['simbolo'].nunique(),
                'recomendaciones': df['recomendacion'].value_counts().to_dict()
            }
            
            return stats
            
        except Exception as e:
            return {'status': 'error', 'mensaje': str(e)}
    
    def _analizar_rupturas_velas(self):
        """Analiza datos del detector de rupturas de velas"""
        try:
            conn = sqlite3.connect(self.db_paths['rupturas_velas'])
            
            # Verificar tablas disponibles
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'detecciones_rupturas' in tables:
                query = '''
                    SELECT * FROM detecciones_rupturas 
                    WHERE timestamp >= datetime('now', '-2 hours')
                    ORDER BY timestamp DESC
                '''
                
                df = pd.read_sql_query(query, conn)
                
                if not df.empty:
                    stats = {
                        'total_detecciones': len(df),
                        'rupturas_confirmadas': len(df[df['tipo_ruptura'].str.contains('CONFIRMADA', na=False)]),
                        'rupturas_posibles': len(df[df['tipo_ruptura'].str.contains('POSIBLE', na=False)]),
                        'confianza_promedio': df['confianza'].mean() if 'confianza' in df.columns else 0,
                        'simbolos_detectados': df['simbolo'].nunique() if 'simbolo' in df.columns else 0
                    }
                else:
                    stats = {'status': 'sin_detecciones_recientes'}
            else:
                stats = {'status': 'tabla_no_encontrada', 'tablas_disponibles': tables}
            
            conn.close()
            return stats
            
        except Exception as e:
            return {'status': 'error', 'mensaje': str(e)}
    
    def _analizar_ia_continua(self):
        """Analiza datos de IA continua"""
        try:
            conn = sqlite3.connect(self.db_paths['ia_continua'])
            
            # Análisis de anomalías
            query_anomalias = '''
                SELECT * FROM anomalias_detectadas 
                WHERE timestamp >= datetime('now', '-2 hours')
                ORDER BY timestamp DESC
            '''
            
            df_anomalias = pd.read_sql_query(query_anomalias, conn)
            
            # Análisis de patrones
            query_patrones = '''
                SELECT * FROM patrones_detectados 
                WHERE timestamp >= datetime('now', '-2 hours')
                ORDER BY timestamp DESC
            '''
            
            df_patrones = pd.read_sql_query(query_patrones, conn)
            
            conn.close()
            
            stats = {
                'anomalias_detectadas': len(df_anomalias),
                'patrones_detectados': len(df_patrones),
                'simbolos_con_anomalias': df_anomalias['symbol'].nunique() if not df_anomalias.empty else 0,
                'simbolos_con_patrones': df_patrones['symbol'].nunique() if not df_patrones.empty else 0
            }
            
            return stats
            
        except Exception as e:
            return {'status': 'error', 'mensaje': str(e)}
    
    def _analizar_monitoreo_proactivo(self):
        """Analiza datos del monitoreo proactivo"""
        try:
            conn = sqlite3.connect(self.db_paths['monitoreo'])
            
            # Verificar tablas disponibles
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            stats = {'tablas_disponibles': tables}
            
            # Analizar alertas si existe la tabla
            if 'alertas' in tables:
                query = '''
                    SELECT * FROM alertas 
                    WHERE timestamp >= datetime('now', '-2 hours')
                    ORDER BY timestamp DESC
                '''
                
                df = pd.read_sql_query(query, conn)
                stats['alertas_recientes'] = len(df)
                stats['tipos_alertas'] = df['tipo'].value_counts().to_dict() if not df.empty else {}
            
            conn.close()
            return stats
            
        except Exception as e:
            return {'status': 'error', 'mensaje': str(e)}
    
    def _consolidar_analisis(self, rompimientos, rupturas, ia, monitoreo):
        """Consolida todos los análisis en un reporte unificado"""
        
        # Calcular score de oportunidad del mercado
        score_mercado = 0
        factores = []
        
        # Factor 1: Actividad de rompimientos
        if isinstance(rompimientos, dict) and 'total_analisis' in rompimientos:
            if rompimientos['total_analisis'] > 20:
                score_mercado += 20
                factores.append("Alta actividad de análisis")
            
            if rompimientos.get('rupturas_alcistas', 0) > rompimientos.get('rupturas_bajistas', 0):
                score_mercado += 15
                factores.append("Tendencia alcista en rompimientos")
            
            if rompimientos.get('confianza_promedio', 0) > 50:
                score_mercado += 15
                factores.append("Alta confianza en señales")
        
        # Factor 2: Detecciones de rupturas de velas
        if isinstance(rupturas, dict) and 'total_detecciones' in rupturas:
            if rupturas['total_detecciones'] > 5:
                score_mercado += 10
                factores.append("Rupturas de velas detectadas")
        
        # Factor 3: Actividad de IA
        if isinstance(ia, dict):
            if ia.get('anomalias_detectadas', 0) > 0:
                score_mercado += 10
                factores.append("Anomalías detectadas por IA")
            
            if ia.get('patrones_detectados', 0) > 0:
                score_mercado += 10
                factores.append("Patrones detectados por IA")
        
        # Factor 4: RSI del mercado
        if isinstance(rompimientos, dict) and 'rsi_promedio' in rompimientos:
            rsi = rompimientos['rsi_promedio']
            if 30 <= rsi <= 70:  # RSI neutral es bueno para trading
                score_mercado += 10
                factores.append("RSI en rango neutral")
        
        # Factor 5: Volumen
        if isinstance(rompimientos, dict) and 'volumen_ratio_promedio' in rompimientos:
            vol_ratio = rompimientos['volumen_ratio_promedio']
            if vol_ratio > 1.2:  # Volumen alto
                score_mercado += 10
                factores.append("Volumen alto")
        
        # Determinar estado del mercado
        if score_mercado >= 70:
            estado_mercado = "🟢 EXCELENTE"
        elif score_mercado >= 50:
            estado_mercado = "🟡 BUENO"
        elif score_mercado >= 30:
            estado_mercado = "🟠 MODERADO"
        else:
            estado_mercado = "🔴 BAJO"
        
        return {
            'timestamp': datetime.now().isoformat(),
            'score_mercado': score_mercado,
            'estado_mercado': estado_mercado,
            'factores_positivos': factores,
            'analisis_detallado': {
                'rompimientos': rompimientos,
                'rupturas_velas': rupturas,
                'ia_continua': ia,
                'monitoreo_proactivo': monitoreo
            }
        }
    
    def evaluar_paper_trading_actual(self):
        """Evalúa el estado actual del paper trading"""
        print("\n" + "="*80)
        print("💼 EVALUACIÓN DEL SISTEMA DE PAPER TRADING")
        print("="*80)
        
        # Leer configuración actual
        session_file = 'data/paper_trading_session.json'
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            print(f"📊 Estado de la sesión:")
            print(f"   • Capital inicial: ${session_data.get('capital', 0):,.2f}")
            print(f"   • Posiciones activas: {session_data.get('positions', 0)}")
            print(f"   • Total de trades: {session_data.get('total_trades', 0)}")
            print(f"   • Auto trading: {'✅ ACTIVO' if session_data.get('auto_trading', False) else '❌ INACTIVO'}")
            print(f"   • Última actualización: {session_data.get('timestamp', 'N/A')}")
        else:
            print("❌ No se encontró archivo de sesión de paper trading")
        
        # Evaluar configuración del motor
        portfolio = self.paper_engine.get_portfolio_summary()
        print(f"\n📈 Estado del motor de paper trading:")
        print(f"   • Capital actual: ${portfolio['current_capital']:,.2f}")
        print(f"   • Valor total del portfolio: ${portfolio['total_portfolio_value']:,.2f}")
        print(f"   • Posiciones abiertas: {portfolio['open_positions']}")
        print(f"   • Órdenes pendientes: {portfolio['pending_orders']}")
        print(f"   • Total de trades: {portfolio['total_trades']}")
        print(f"   • Tasa de acierto: {portfolio['win_rate']*100:.1f}%")
        print(f"   • PnL total: ${portfolio['total_pnl']:,.2f}")
        print(f"   • Retorno total: {portfolio['total_return_pct']:.2f}%")
        
        return {
            'session_data': session_data if os.path.exists(session_file) else {},
            'portfolio_summary': portfolio,
            'engine_status': 'activo' if self.paper_engine else 'inactivo'
        }
    
    def proponer_mejoras_paper_trading(self, analisis_mercado):
        """Propone mejoras para el sistema de paper trading basado en el análisis"""
        print("\n" + "="*80)
        print("🚀 PROPUESTAS DE MEJORA PARA PAPER TRADING")
        print("="*80)
        
        propuestas = []
        
        # Análisis del score de mercado
        score = analisis_mercado['score_mercado']
        estado = analisis_mercado['estado_mercado']
        
        print(f"📊 Score actual del mercado: {score}/100 - {estado}")
        
        if score >= 70:
            propuestas.extend([
                "🎯 ACTIVAR TRADING AGRESIVO: El mercado muestra excelentes condiciones",
                "💰 AUMENTAR TAMAÑO DE POSICIONES: Aprovechar las buenas condiciones",
                "⚡ REDUCIR TIMEOUTS: Ejecutar trades más rápidamente",
                "📈 ACTIVAR MÚLTIPLES SÍMBOLOS: Diversificar en varios pares"
            ])
        elif score >= 50:
            propuestas.extend([
                "⚖️ MANTENER TRADING MODERADO: Condiciones buenas pero no excepcionales",
                "🎯 ENFOCARSE EN SEÑALES DE ALTA CONFIANZA: Filtrar mejor las oportunidades",
                "📊 MONITOREAR RSI Y VOLUMEN: Usar indicadores adicionales"
            ])
        elif score >= 30:
            propuestas.extend([
                "🛡️ TRADING CONSERVADOR: Reducir riesgos en condiciones moderadas",
                "⏰ AUMENTAR TIMEOUTS: Esperar mejores confirmaciones",
                "🔍 ENFOCARSE EN 1-2 SÍMBOLOS: Concentrar esfuerzos"
            ])
        else:
            propuestas.extend([
                "⏸️ PAUSAR TRADING AUTOMÁTICO: Condiciones desfavorables",
                "👀 MODO OBSERVACIÓN: Solo monitorear sin ejecutar",
                "📚 ANALIZAR PATRONES: Estudiar el mercado actual"
            ])
        
        # Propuestas específicas basadas en datos
        rompimientos = analisis_mercado['analisis_detallado']['rompimientos']
        
        if isinstance(rompimientos, dict):
            if rompimientos.get('confianza_promedio', 0) < 30:
                propuestas.append("🔧 AJUSTAR FILTROS DE CONFIANZA: Señales muy débiles")
            
            if rompimientos.get('volumen_ratio_promedio', 0) < 0.8:
                propuestas.append("📉 ESPERAR MAYOR VOLUMEN: Mercado poco activo")
            
            # Análisis de recomendaciones
            recomendaciones = rompimientos.get('recomendaciones', {})
            if 'MANTENER' in recomendaciones and recomendaciones['MANTENER'] > 20:
                propuestas.append("⏳ MERCADO LATERAL: Considerar estrategias de rango")
        
        # Propuestas técnicas
        propuestas.extend([
            "🤖 INTEGRAR IA CONTINUA: Usar detecciones de anomalías para filtrar trades",
            "📊 DASHBOARD EN TIEMPO REAL: Crear interfaz de monitoreo avanzada",
            "🔄 BACKTESTING AUTOMÁTICO: Validar estrategias continuamente",
            "📱 SISTEMA DE ALERTAS: Notificaciones para oportunidades importantes"
        ])
        
        # Mostrar propuestas
        for i, propuesta in enumerate(propuestas, 1):
            print(f"{i:2d}. {propuesta}")
        
        return propuestas
    
    def generar_reporte_completo(self):
        """Genera un reporte completo del análisis"""
        print("\n" + "🔥"*50)
        print("📊 REPORTE INTEGRAL - MERCADO Y PAPER TRADING")
        print("🔥"*50)
        
        # 1. Análisis del mercado
        analisis_mercado = self.analizar_estado_mercado_actual()
        
        # 2. Evaluación del paper trading
        evaluacion_paper = self.evaluar_paper_trading_actual()
        
        # 3. Propuestas de mejora
        propuestas = self.proponer_mejoras_paper_trading(analisis_mercado)
        
        # 4. Recomendaciones inmediatas
        print(f"\n⚡ RECOMENDACIONES INMEDIATAS:")
        print("-"*50)
        
        score = analisis_mercado['score_mercado']
        if score >= 70:
            print("🟢 ACCIÓN RECOMENDADA: ACTIVAR TRADING AUTOMÁTICO")
            print("   • Configurar stop loss al 2%")
            print("   • Take profit al 4-6%")
            print("   • Máximo 3-5 posiciones simultáneas")
            print("   • Enfocarse en BTCUSDT, ETHUSDT, ADAUSDT")
        elif score >= 50:
            print("🟡 ACCIÓN RECOMENDADA: TRADING SELECTIVO")
            print("   • Solo señales con confianza >60%")
            print("   • Máximo 2-3 posiciones")
            print("   • Stop loss más conservador (1.5%)")
        else:
            print("🔴 ACCIÓN RECOMENDADA: MODO OBSERVACIÓN")
            print("   • Pausar trading automático")
            print("   • Monitorear condiciones del mercado")
            print("   • Preparar para próximas oportunidades")
        
        # 5. Guardar reporte
        reporte_completo = {
            'timestamp': datetime.now().isoformat(),
            'analisis_mercado': analisis_mercado,
            'evaluacion_paper_trading': evaluacion_paper,
            'propuestas_mejora': propuestas,
            'score_mercado': score,
            'recomendacion_inmediata': 'activar' if score >= 70 else 'selectivo' if score >= 50 else 'observar'
        }
        
        with open('reporte_integral_mercado_paper.json', 'w', encoding='utf-8') as f:
            json.dump(reporte_completo, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Reporte completo guardado en: reporte_integral_mercado_paper.json")
        
        return reporte_completo

def main():
    """Función principal"""
    analizador = AnalisisIntegralMercadoPaper()
    reporte = analizador.generar_reporte_completo()
    
    print(f"\n✅ Análisis completado exitosamente")
    print(f"📊 Score del mercado: {reporte['score_mercado']}/100")
    print(f"🎯 Recomendación: {reporte['recomendacion_inmediata'].upper()}")

if __name__ == "__main__":
    main()