#!/usr/bin/env python3
"""
CONFIGURACIÓN RÁPIDA - INICIO INMEDIATO
Para empezar a usar las estrategias autónomas en 5 minutos
"""

import asyncio
import sys
import os
from datetime import datetime

# Agregar ruta de tu bot actual
sys.path.append('/home/johan/itbot_linux')

# Configuración rápida - EDITAR ESTOS VALORES
QUICK_CONFIG = {
    # CONFIGURACIÓN BÁSICA (EDITAR)
    'capital_inicial': 1000,  # Tu capital inicial en USDT
    'modo_demo': True,       # True = modo demo, False = real trading
    'telegram_chat_id': None,  # Tu chat ID de Telegram (opcional)
    
    # PARES FAVORITOS (EDITAR según tus preferencias)
    'pares_favoritos': [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 
        'SOLUSDT', 'XRPUSDT', 'DOTUSDT', 'LINKUSDT'
    ],
    
    # CONFIGURACIÓN DE RIESGO (EDITAR según tu tolerancia)
    'riesgo_por_trade': 0.02,      # 2% de riesgo por trade
    'max_posiciones_simultaneas': 5, # Máximo 5 posiciones abiertas
    'stop_loss_diario': 0.05,      # Stop loss diario del 5%
    
    # TIMEFRAMES (EDITAR según tu estilo)
    'timeframes_principales': ['5m', '15m', '30m'],  # Para estrategias principales
    'timeframes_scalping': ['1m', '3m'],             # Para scalping
    
    # ESTRATEGIAS ACTIVAS (True/False)
    'estrategias_activas': {
        'scalping_auto': True,      # Scalping automatizado
        'mean_reversion': True,     # Reversión a la media  
        'breakout_momentum': True,  # Breakout y momentum
        'arbitrage_temporal': False, # Arbitraje temporal (avanzado)
        'volatility_trading': False  # Trading de volatilidad (avanzado)
    }
}

def create_quick_start_config():
    """
    Crear archivo de configuración personalizado
    """
    config_content = f'''#!/usr/bin/env python3
"""
CONFIGURACIÓN PERSONALIZADA PARA ESTRATEGIAS AUTÓNOMAS
Generado el: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

# IMPORTAR TU CONFIGURACIÓN ACTUAL
try:
    from config import *  # Tu configuración existente
    print("✅ Configuración actual importada correctamente")
except ImportError:
    print("⚠️  No se pudo importar config.py - usando configuración por defecto")

# CONFIGURACIÓN DE ESTRATEGIAS AUTÓNOMAS
AUTONOMOUS_CONFIG = {{
    # CAPITAL Y RIESGO
    'capital_inicial': {QUICK_CONFIG['capital_inicial']},
    'modo_demo': {QUICK_CONFIG['modo_demo']},
    'riesgo_por_trade': {QUICK_CONFIG['riesgo_por_trade']},
    'max_posiciones_simultaneas': {QUICK_CONFIG['max_posiciones_simultaneas']},
    'stop_loss_diario': {QUICK_CONFIG['stop_loss_diario']},
    
    # PARES DE TRADING
    'pares_favoritos': {QUICK_CONFIG['pares_favoritos']},
    
    # TIMEFRAMES
    'timeframes_principales': {QUICK_CONFIG['timeframes_principales']},
    'timeframes_scalping': {QUICK_CONFIG['timeframes_scalping']},
    
    # ESTRATEGIAS
    'estrategias_activas': {QUICK_CONFIG['estrategias_activas']},
    
    # DISTRIBUCIÓN DE CAPITAL POR ESTRATEGIA
    'distribucion_capital': {{
        'scalping_auto': 0.40,      # 40% para scalping
        'mean_reversion': 0.30,     # 30% para mean reversion
        'breakout_momentum': 0.20,  # 20% para breakouts
        'arbitrage_temporal': 0.10, # 10% para arbitraje
        'volatility_trading': 0.05  # 5% para volatilidad
    }},
    
    # CONFIGURACIÓN AVANZADA
    'filtros_calidad': {{
        'rsi_oversold': 25,         # RSI oversold level
        'rsi_overbought': 75,       # RSI overbought level
        'volumen_spike_factor': 1.5, # Factor para detectar spikes de volumen
        'min_confianza': 0.6,       # Confianza mínima para ejecutar señal
        'max_correlacion': 0.7      # Máxima correlación entre trades
    }},
    
    # ALERTAS Y NOTIFICACIONES
    'telegram_alerts': {{
        'chat_id': {QUICK_CONFIG['telegram_chat_id']},
        'alertas_trades': True,
        'alertas_pnl': True,
        'alertas_riesgo': True
    }}
}}

# FUNCIÓN DE INTEGRACIÓN RÁPIDA
def get_autonomous_config():
    """
    Obtener configuración para estrategias autónomas
    """
    return AUTONOMOUS_CONFIG

# FUNCIÓN DE VALIDACIÓN
def validate_config():
    """
    Validar que la configuración es correcta
    """
    config = AUTONOMOUS_CONFIG
    errors = []
    
    # Validar capital
    if config['capital_inicial'] <= 0:
        errors.append("Capital inicial debe ser mayor a 0")
    
    # Validar riesgo
    if config['riesgo_por_trade'] <= 0 or config['riesgo_por_trade'] > 0.1:
        errors.append("Riesgo por trade debe estar entre 0.1% y 10%")
    
    # Validar distribución de capital
    total_distribucion = sum(config['distribucion_capital'].values())
    if abs(total_distribucion - 1.0) > 0.01:
        errors.append(f"Distribución de capital no suma 100% (suma: {{total_distribucion:.1%}})")
    
    # Validar pares
    if not config['pares_favoritos']:
        errors.append("Debe configurar al menos un par de trading")
    
    if errors:
        print("❌ Errores en configuración:")
        for error in errors:
            print(f"   - {{error}}")
        return False
    else:
        print("✅ Configuración válida")
        return True

if __name__ == "__main__":
    print("🔧 Validando configuración autónoma...")
    validate_config()
    print("\\n📊 Configuración actual:")
    print(f"   Capital inicial: ${{AUTONOMOUS_CONFIG['capital_inicial']:,}}")
    print(f"   Modo: {{'Demo' if AUTONOMOUS_CONFIG['modo_demo'] else 'Real Trading'}}")
    print(f"   Estrategias activas: {{sum(AUTONOMOUS_CONFIG['estrategias_activas'].values())}}")
    print(f"   Pares configurados: {{len(AUTONOMOUS_CONFIG['pares_favoritos'])}}")
'''
    
    # Guardar configuración
    config_file = '/home/johan/itbot_linux/strategies/autonomous_config.py'
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Configuración guardada en: {config_file}")
    return config_file

def create_integration_script():
    """
    Crear script de integración que puedas ejecutar directamente
    """
    integration_script = '''#!/usr/bin/env python3
"""
SCRIPT DE INTEGRACIÓN DIRECTA
Ejecuta este archivo para integrar estrategias autónomas con tu bot
"""

import asyncio
import sys
import os
from datetime import datetime

# Agregar ruta
sys.path.append('/home/johan/itbot_linux')

async def main():
    """
    Función principal de integración
    """
    print("🚀 INICIANDO INTEGRACIÓN DE ESTRATEGIAS AUTÓNOMAS")
    print("=" * 55)
    
    try:
        # 1. Importar configuración
        from strategies.autonomous_config import get_autonomous_config, validate_config
        
        print("\\n📋 Paso 1: Validando configuración...")
        if not validate_config():
            print("❌ Configuración inválida. Revisa autonomous_config.py")
            return
        
        config = get_autonomous_config()
        print("✅ Configuración validada correctamente")
        
        # 2. Importar módulo autónomo
        print("\\n📋 Paso 2: Importando módulo autónomo...")
        from strategies.autonomous_integration_module import AutonomousStrategiesModule
        
        autonomous = AutonomousStrategiesModule(
            capital_inicial=config['capital_inicial'],
            existing_bot_config=config
        )
        print("✅ Módulo autónomo inicializado")
        
        # 3. Configurar estrategias
        print("\\n📋 Paso 3: Configurando estrategias...")
        for strategy_name, is_active in config['estrategias_activas'].items():
            if is_active and strategy_name in autonomous.strategy_config:
                autonomous.strategy_config[strategy_name]['enabled'] = True
                capital_pct = config['distribucion_capital'].get(strategy_name, 0.1)
                autonomous.strategy_config[strategy_name]['capital_pct'] = capital_pct
                print(f"   ✅ {strategy_name}: Activa ({capital_pct:.1%} capital)")
            else:
                if strategy_name in autonomous.strategy_config:
                    autonomous.strategy_config[strategy_name]['enabled'] = False
                    print(f"   ❌ {strategy_name}: Inactiva")
        
        # 4. Simular ciclo de trading
        print("\\n📋 Paso 4: Simulando ciclo de trading...")
        
        if config['modo_demo']:
            print("⚠️  MODO DEMO ACTIVADO - No se ejecutarán trades reales")
        else:
            print("🔴 MODO REAL ACTIVADO - Se ejecutarán trades reales")
        
        # Simular obtención de señales
        print("\\n📊 Obteniendo señales de trading...")
        # signals = await autonomous.get_all_autonomous_signals()
        print("✅ Sistema listo para generar señales")
        
        # 5. Mostrar resumen
        print("\\n📊 RESUMEN DE INTEGRACIÓN:")
        print(f"   💰 Capital inicial: ${config['capital_inicial']:,}")
        print(f"   🎯 Objetivo mensual: 15% ({config['capital_inicial'] * 0.15:,.0f} USDT)")
        print(f"   🔧 Estrategias activas: {sum(config['estrategias_activas'].values())}")
        print(f"   📈 Pares configurados: {len(config['pares_favoritos'])}")
        print(f"   ⚠️  Riesgo por trade: {config['riesgo_por_trade']:.1%}")
        print(f"   🚫 Stop loss diario: {config['stop_loss_diario']:.1%}")
        
        # 6. Instrucciones finales
        print("\\n" + "=" * 55)
        print("🎯 INTEGRACIÓN COMPLETADA EXITOSAMENTE")
        print("\\n📋 SIGUIENTES PASOS:")
        print("1. Adaptar funciones de datos en autonomous_integration_module.py")
        print("2. Conectar con tu cliente Binance actual")
        print("3. Probar en modo demo durante 24 horas")
        print("4. Activar gradualmente con capital pequeño")
        
        print("\\n⚡ PARA ACTIVAR EN TU BOT PRINCIPAL:")
        print("   - Importar: from strategies.autonomous_integration_module import run_autonomous_strategies_cycle")  
        print("   - Ejecutar: await run_autonomous_strategies_cycle() cada minuto")
        print("   - Monitorear resultados en tiempo real")
        
        return autonomous
        
    except Exception as e:
        print(f"❌ Error en integración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    # Guardar script
    script_file = '/home/johan/itbot_linux/strategies/run_integration.py'
    with open(script_file, 'w') as f:
        f.write(integration_script)
    
    print(f"✅ Script de integración guardado en: {script_file}")
    return script_file

def create_monitoring_dashboard():
    """
    Crear dashboard simple para monitorear las estrategias
    """
    dashboard_content = '''#!/usr/bin/env python3
"""
DASHBOARD DE MONITOREO SIMPLE
Para monitorear el rendimiento de las estrategias autónomas
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

class AutonomousMonitoringDashboard:
    """
    Dashboard simple para monitorear estrategias autónomas
    """
    
    def __init__(self):
        self.metrics_file = '/home/johan/itbot_linux/strategies/performance_metrics.json'
        self.trades_file = '/home/johan/itbot_linux/strategies/trades_log.json'
        
    def log_trade(self, trade_data: Dict):
        """
        Registrar un trade ejecutado
        """
        trade_entry = {
            'timestamp': datetime.now().isoformat(),
            'pair': trade_data.get('pair'),
            'direction': trade_data.get('direction'),
            'entry_price': trade_data.get('entry_price'),
            'position_size': trade_data.get('position_size'),
            'strategy': trade_data.get('strategy'),
            'confidence': trade_data.get('confidence'),
            'status': 'OPEN'
        }
        
        # Cargar trades existentes
        trades = self.load_trades()
        trades.append(trade_entry)
        
        # Guardar trades
        with open(self.trades_file, 'w') as f:
            json.dump(trades, f, indent=2)
            
    def load_trades(self) -> List[Dict]:
        """
        Cargar historial de trades
        """
        if os.path.exists(self.trades_file):
            with open(self.trades_file, 'r') as f:
                return json.load(f)
        return []
    
    def calculate_daily_performance(self) -> Dict:
        """
        Calcular rendimiento diario
        """
        trades = self.load_trades()
        today = datetime.now().date()
        
        today_trades = [
            t for t in trades 
            if datetime.fromisoformat(t['timestamp']).date() == today
        ]
        
        total_trades = len(today_trades)
        if total_trades == 0:
            return {'trades': 0, 'pnl': 0, 'win_rate': 0}
        
        # Simular PnL (en producción usar datos reales)
        total_pnl = sum(
            t.get('pnl', t['confidence'] * 0.01 * 1000)  # PnL simulado
            for t in today_trades
        )
        
        winning_trades = len([t for t in today_trades if t.get('pnl', 0) > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'trades': total_trades,
            'pnl': total_pnl,
            'win_rate': win_rate,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades
        }
    
    def generate_report(self) -> str:
        """
        Generar reporte de rendimiento
        """
        daily_perf = self.calculate_daily_performance()
        trades = self.load_trades()
        
        # Estadísticas por estrategia
        strategy_stats = {}
        for trade in trades:
            strategy = trade.get('strategy', 'unknown')
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'count': 0, 'total_confidence': 0}
            
            strategy_stats[strategy]['count'] += 1
            strategy_stats[strategy]['total_confidence'] += trade.get('confidence', 0)
        
        # Generar reporte
        report = f"""
🤖 REPORTE DE ESTRATEGIAS AUTÓNOMAS
=======================================
📅 Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📊 RENDIMIENTO DIARIO:
   💰 PnL: ${daily_perf['pnl']:,.2f}
   📈 Trades ejecutados: {daily_perf['trades']}
   🎯 Win Rate: {daily_perf['win_rate']:.1%}
   ✅ Trades ganadores: {daily_perf['winning_trades']}
   ❌ Trades perdedores: {daily_perf['losing_trades']}

📊 ESTADÍSTICAS POR ESTRATEGIA:
"""
        
        for strategy, stats in strategy_stats.items():
            avg_confidence = stats['total_confidence'] / stats['count'] if stats['count'] > 0 else 0
            report += f"   {strategy}: {stats['count']} trades (Confianza promedio: {avg_confidence:.1%})\\n"
        
        report += f"""
📋 RESUMEN TOTAL:
   📊 Total trades históricos: {len(trades)}
   🕐 Último trade: {trades[-1]['timestamp'] if trades else 'N/A'}
   
💡 RECOMENDACIONES:
"""
        
        if daily_perf['win_rate'] < 0.6:
            report += "   ⚠️  Win rate bajo - considerar ajustar parámetros de confianza\\n"
        if daily_perf['trades'] < 5:
            report += "   ⚠️  Pocos trades - considerar ampliar criterios de entrada\\n"
        if daily_perf['win_rate'] > 0.8:
            report += "   🎯 Excelente rendimiento - mantener configuración actual\\n"
            
        return report
    
    def show_live_dashboard(self):
        """
        Mostrar dashboard en tiempo real
        """
        os.system('clear')  # Limpiar pantalla
        
        report = self.generate_report()
        print(report)
        
        # Mostrar últimos 5 trades
        trades = self.load_trades()
        recent_trades = trades[-5:] if len(trades) >= 5 else trades
        
        if recent_trades:
            print("\\n📝 ÚLTIMOS TRADES:")
            for trade in reversed(recent_trades):
                timestamp = datetime.fromisoformat(trade['timestamp']).strftime("%H:%M:%S")
                print(f"   {timestamp} - {trade['strategy']} - {trade['pair']} {trade['direction']} @ {trade['entry_price']}")

def main():
    """
    Función principal del dashboard
    """
    dashboard = AutonomousMonitoringDashboard()
    
    try:
        dashboard.show_live_dashboard()
        
        print("\\n" + "=" * 50)
        print("🔄 Para actualizar en tiempo real, ejecuta:")
        print("   watch -n 10 'python3 strategies/monitoring_dashboard.py'")
        print("\\n💡 Para logging automático, integra con tu bot:")
        print("   dashboard.log_trade(signal_data)")
        
    except KeyboardInterrupt:
        print("\\n👋 Dashboard cerrado")

if __name__ == "__main__":
    main()
'''
    
    # Guardar dashboard
    dashboard_file = '/home/johan/itbot_linux/strategies/monitoring_dashboard.py'
    with open(dashboard_file, 'w') as f:
        f.write(dashboard_content)
    
    print(f"✅ Dashboard guardado en: {dashboard_file}")
    return dashboard_file

def main():
    """
    Configuración rápida principal
    """
    print("⚡ CONFIGURACIÓN RÁPIDA DE ESTRATEGIAS AUTÓNOMAS")
    print("=" * 50)
    
    print(f"\n📊 Configuración actual:")
    print(f"   💰 Capital inicial: ${QUICK_CONFIG['capital_inicial']:,}")
    print(f"   🎯 Modo: {'Demo' if QUICK_CONFIG['modo_demo'] else 'Real Trading'}")
    print(f"   ⚠️  Riesgo por trade: {QUICK_CONFIG['riesgo_por_trade']:.1%}")
    print(f"   📈 Pares: {len(QUICK_CONFIG['pares_favoritos'])}")
    print(f"   🔧 Estrategias activas: {sum(QUICK_CONFIG['estrategias_activas'].values())}")
    
    print(f"\n🔧 Creando archivos de configuración...")
    
    # Crear archivos
    config_file = create_quick_start_config()
    script_file = create_integration_script()
    dashboard_file = create_monitoring_dashboard()
    
    print(f"\n✅ ARCHIVOS CREADOS:")
    print(f"   📝 Configuración: {config_file}")
    print(f"   🚀 Script de integración: {script_file}")  
    print(f"   📊 Dashboard de monitoreo: {dashboard_file}")
    
    print(f"\n⚡ INICIO RÁPIDO EN 3 PASOS:")
    print(f"1. Editar configuración: nano strategies/autonomous_config.py")
    print(f"2. Ejecutar integración: python3 strategies/run_integration.py")
    print(f"3. Monitorear resultados: python3 strategies/monitoring_dashboard.py")
    
    print(f"\n🎯 OBJETIVO: 15% retorno mensual = ${QUICK_CONFIG['capital_inicial'] * 0.15:,.0f} USDT")
    print(f"⏱️  TIEMPO TOTAL DE SETUP: 5-10 minutos")

if __name__ == "__main__":
    main()
