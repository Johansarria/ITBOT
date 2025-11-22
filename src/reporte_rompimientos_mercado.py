# /src/reporte_rompimientos_mercado.py

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from binance_data_provider import BinanceDataProvider

class ReporteRompimientosMercado:
    def __init__(self):
        self.data_provider = BinanceDataProvider()
        self.db_path = 'analisis_rompimientos_tiempo_real.db'
        
    def obtener_datos_recientes(self, horas=24):
        """Obtiene datos de análisis de las últimas horas"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT * FROM rompimientos_analisis 
            WHERE timestamp >= datetime('now', '-{} hours')
            ORDER BY timestamp DESC
        '''.format(horas)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def generar_estadisticas_mercado(self, df):
        """Genera estadísticas del mercado"""
        if df.empty:
            return {}
            
        stats = {
            'total_analisis': len(df),
            'simbolos_unicos': df['simbolo'].nunique(),
            'rupturas_alcistas': len(df[df['tipo_rompimiento'].str.contains('ALCISTA', na=False)]),
            'rupturas_bajistas': len(df[df['tipo_rompimiento'].str.contains('BAJISTA', na=False)]),
            'neutrales': len(df[df['tipo_rompimiento'] == 'NEUTRAL']),
            'confianza_promedio': df['confianza'].mean(),
            'rsi_promedio': df['rsi'].mean(),
            'volumen_ratio_promedio': df['volumen_ratio'].mean(),
            'momentum_promedio': df['momentum_score'].mean()
        }
        
        # Top símbolos por actividad
        actividad_simbolos = df['simbolo'].value_counts().head(5)
        stats['top_simbolos_activos'] = actividad_simbolos.to_dict()
        
        # Distribución de recomendaciones
        recomendaciones = df['recomendacion'].value_counts()
        stats['distribucion_recomendaciones'] = recomendaciones.to_dict()
        
        # Patrones más frecuentes
        patrones = df['patron_velas'].value_counts().head(5)
        stats['patrones_frecuentes'] = patrones.to_dict()
        
        return stats
    
    def analizar_tendencias_temporales(self, df):
        """Analiza tendencias temporales en los rompimientos"""
        if df.empty:
            return {}
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hora'] = df['timestamp'].dt.hour
        
        # Distribución por horas
        distribucion_horas = df['hora'].value_counts().sort_index()
        
        # Rupturas por hora
        rupturas_por_hora = df[df['tipo_rompimiento'] != 'NEUTRAL'].groupby('hora').size()
        
        # Volatilidad por hora (basada en fuerza de rompimiento)
        volatilidad_hora = df.groupby('hora')['fuerza_rompimiento'].mean()
        
        return {
            'distribucion_horas': distribucion_horas.to_dict(),
            'rupturas_por_hora': rupturas_por_hora.to_dict(),
            'volatilidad_por_hora': volatilidad_hora.to_dict()
        }
    
    def identificar_oportunidades_actuales(self):
        """Identifica oportunidades actuales en el mercado"""
        # Obtener datos más recientes (última hora)
        df_reciente = self.obtener_datos_recientes(horas=1)
        
        if df_reciente.empty:
            return []
            
        # Filtrar oportunidades con alta confianza
        oportunidades = df_reciente[
            (df_reciente['confianza'] >= 60) & 
            (df_reciente['tipo_rompimiento'] != 'NEUTRAL')
        ].sort_values('confianza', ascending=False)
        
        return oportunidades.to_dict('records')
    
    def generar_reporte_completo(self):
        """Genera un reporte completo del análisis de mercado"""
        print("\n" + "="*100)
        print("📊 REPORTE COMPLETO DE ANÁLISIS DE ROMPIMIENTOS DE MERCADO")
        print("="*100)
        print(f"🕐 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Datos de las últimas 24 horas
        df_24h = self.obtener_datos_recientes(24)
        stats_24h = self.generar_estadisticas_mercado(df_24h)
        
        # Datos de la última hora
        df_1h = self.obtener_datos_recientes(1)
        stats_1h = self.generar_estadisticas_mercado(df_1h)
        
        print("\n📈 RESUMEN EJECUTIVO (Últimas 24 horas)")
        print("-"*50)
        if stats_24h:
            print(f"• Total de análisis realizados: {stats_24h['total_analisis']:,}")
            print(f"• Símbolos monitoreados: {stats_24h['simbolos_unicos']}")
            print(f"• Rupturas alcistas detectadas: {stats_24h['rupturas_alcistas']}")
            print(f"• Rupturas bajistas detectadas: {stats_24h['rupturas_bajistas']}")
            print(f"• Análisis neutrales: {stats_24h['neutrales']}")
            print(f"• Confianza promedio: {stats_24h['confianza_promedio']:.1f}%")
            print(f"• RSI promedio del mercado: {stats_24h['rsi_promedio']:.1f}")
            print(f"• Ratio de volumen promedio: {stats_24h['volumen_ratio_promedio']:.2f}x")
        else:
            print("• No hay datos disponibles para las últimas 24 horas")
        
        print("\n🔥 ACTIVIDAD RECIENTE (Última hora)")
        print("-"*50)
        if stats_1h:
            print(f"• Análisis en la última hora: {stats_1h['total_analisis']}")
            print(f"• Rupturas alcistas: {stats_1h['rupturas_alcistas']}")
            print(f"• Rupturas bajistas: {stats_1h['rupturas_bajistas']}")
            print(f"• Momentum promedio: {stats_1h['momentum_promedio']:.2f}")
        else:
            print("• No hay datos recientes disponibles")
        
        # Análisis temporal
        if not df_24h.empty:
            tendencias = self.analizar_tendencias_temporales(df_24h)
            
            print("\n⏰ ANÁLISIS TEMPORAL")
            print("-"*50)
            
            if tendencias['rupturas_por_hora']:
                hora_mas_activa = max(tendencias['rupturas_por_hora'], 
                                    key=tendencias['rupturas_por_hora'].get)
                rupturas_max = tendencias['rupturas_por_hora'][hora_mas_activa]
                print(f"• Hora más activa: {hora_mas_activa}:00 ({rupturas_max} rupturas)")
            
            if tendencias['volatilidad_por_hora']:
                hora_mas_volatil = max(tendencias['volatilidad_por_hora'], 
                                     key=tendencias['volatilidad_por_hora'].get)
                volatilidad_max = tendencias['volatilidad_por_hora'][hora_mas_volatil]
                print(f"• Hora más volátil: {hora_mas_volatil}:00 (fuerza promedio: {volatilidad_max:.1f})")
        
        # Top símbolos activos
        if stats_24h and 'top_simbolos_activos' in stats_24h:
            print("\n🏆 SÍMBOLOS MÁS ACTIVOS (24h)")
            print("-"*50)
            for simbolo, count in list(stats_24h['top_simbolos_activos'].items())[:5]:
                print(f"• {simbolo}: {count} análisis")
        
        # Patrones más frecuentes
        if stats_24h and 'patrones_frecuentes' in stats_24h:
            print("\n🕯️ PATRONES DE VELAS MÁS FRECUENTES")
            print("-"*50)
            for patron, count in list(stats_24h['patrones_frecuentes'].items())[:5]:
                if patron != 'NEUTRAL':
                    print(f"• {patron}: {count} ocurrencias")
        
        # Oportunidades actuales
        oportunidades = self.identificar_oportunidades_actuales()
        
        print("\n💡 OPORTUNIDADES ACTUALES DE ALTA CONFIANZA")
        print("-"*50)
        if oportunidades:
            for opp in oportunidades[:5]:  # Top 5 oportunidades
                emoji = "🟢" if "ALCISTA" in opp['tipo_rompimiento'] else "🔴"
                print(f"{emoji} {opp['simbolo']} - {opp['tipo_rompimiento']}")
                print(f"   Precio: ${opp['precio_actual']:.6f} | Confianza: {opp['confianza']:.1f}%")
                print(f"   RSI: {opp['rsi']:.1f} | Volumen: {opp['volumen_ratio']:.1f}x")
                print(f"   Recomendación: {opp['recomendacion']}")
                print()
        else:
            print("• No hay oportunidades de alta confianza en este momento")
        
        # Distribución de recomendaciones
        if stats_24h and 'distribucion_recomendaciones' in stats_24h:
            print("\n📋 DISTRIBUCIÓN DE RECOMENDACIONES (24h)")
            print("-"*50)
            for recomendacion, count in stats_24h['distribucion_recomendaciones'].items():
                emoji = {"COMPRAR": "🟢", "VENDER": "🔴", "OBSERVAR_COMPRA": "👀🟢", 
                        "OBSERVAR_VENTA": "👀🔴", "MANTENER": "⚪"}.get(recomendacion, "📊")
                print(f"{emoji} {recomendacion}: {count} ({count/stats_24h['total_analisis']*100:.1f}%)")
        
        print("\n🎯 CONCLUSIONES Y RECOMENDACIONES")
        print("-"*50)
        
        if stats_24h:
            # Análisis del sentimiento del mercado
            total_rupturas = stats_24h['rupturas_alcistas'] + stats_24h['rupturas_bajistas']
            if total_rupturas > 0:
                ratio_alcista = stats_24h['rupturas_alcistas'] / total_rupturas
                if ratio_alcista > 0.6:
                    sentimiento = "🟢 ALCISTA"
                elif ratio_alcista < 0.4:
                    sentimiento = "🔴 BAJISTA"
                else:
                    sentimiento = "⚪ NEUTRAL"
            else:
                sentimiento = "⚪ NEUTRAL (Sin rupturas significativas)"
            
            print(f"• Sentimiento general del mercado: {sentimiento}")
            
            # Recomendaciones basadas en datos
            if stats_24h['confianza_promedio'] > 70:
                print("• Alta confianza en las señales - Considerar operaciones activas")
            elif stats_24h['confianza_promedio'] > 50:
                print("• Confianza moderada - Operar con cautela")
            else:
                print("• Baja confianza en señales - Evitar operaciones arriesgadas")
            
            if stats_24h['volumen_ratio_promedio'] > 1.5:
                print("• Alto volumen de trading - Mercado activo")
            elif stats_24h['volumen_ratio_promedio'] < 0.8:
                print("• Bajo volumen de trading - Mercado tranquilo")
            
            if stats_24h['rsi_promedio'] > 70:
                print("• RSI promedio alto - Posible sobrecompra del mercado")
            elif stats_24h['rsi_promedio'] < 30:
                print("• RSI promedio bajo - Posible sobreventa del mercado")
        
        print("\n" + "="*100)
        print("📊 Fin del reporte - Sistema de análisis funcionando correctamente")
        print("="*100)
        
        return {
            'stats_24h': stats_24h,
            'stats_1h': stats_1h,
            'oportunidades': oportunidades,
            'timestamp': datetime.now().isoformat()
        }

def main():
    """Función principal para generar reporte"""
    reporte = ReporteRompimientosMercado()
    resultado = reporte.generar_reporte_completo()
    
    # Guardar reporte en archivo JSON
    with open('reporte_mercado_rompimientos.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 Reporte guardado en: reporte_mercado_rompimientos.json")

if __name__ == "__main__":
    main()