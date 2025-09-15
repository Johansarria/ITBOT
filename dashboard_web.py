#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Web para Simulaciones de Trading
Servidor web que muestra el estado en tiempo real de las 6 simulaciones
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from urllib.parse import urlparse, parse_qs

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class DashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, dashboard_data=None, **kwargs):
        self.dashboard_data = dashboard_data
        super().__init__(*args, **kwargs)
        
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_dashboard()
        elif parsed_path.path == '/api/data':
            self.serve_api_data()
        elif parsed_path.path == '/favicon.ico':
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            
    def serve_dashboard(self):
        html_content = self.get_dashboard_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html_content.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
        
    def serve_api_data(self):
        data = self.dashboard_data.get_current_stats() if self.dashboard_data else {}
        json_data = json.dumps(data, ensure_ascii=False)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(json_data.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
        
    def get_dashboard_html(self):
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Trading Algorítmico</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .last-update {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background: rgba(255, 255, 255, 0.15);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .summary-card h3 {
            font-size: 1.2em;
            margin-bottom: 10px;
            opacity: 0.9;
        }
        
        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #4CAF50;
        }
        
        .symbols-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }
        
        .symbol-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        
        .symbol-card:hover {
            transform: translateY(-5px);
        }
        
        .symbol-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .symbol-name {
            font-size: 1.5em;
            font-weight: bold;
        }
        
        .status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .status.running {
            background: #4CAF50;
            color: white;
        }
        
        .status.stopped {
            background: #f44336;
            color: white;
        }
        
        .status.warning {
            background: #ff9800;
            color: white;
        }
        
        .metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .metric {
            text-align: center;
        }
        
        .metric-label {
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 5px;
        }
        
        .metric-value {
            font-size: 1.3em;
            font-weight: bold;
        }
        
        .positive {
            color: #4CAF50;
        }
        
        .negative {
            color: #f44336;
        }
        
        .neutral {
            color: #fff;
        }
        
        .loading {
            text-align: center;
            font-size: 1.2em;
            margin: 50px 0;
        }
        
        .error {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid #f44336;
            color: #f44336;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin: 20px 0;
        }
        
        @media (max-width: 768px) {
            .symbols-grid {
                grid-template-columns: 1fr;
            }
            
            .summary {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Dashboard Trading Algorítmico</h1>
            <div class="last-update" id="lastUpdate">Cargando...</div>
        </div>
        
        <div class="summary" id="summary">
            <!-- Resumen se carga dinámicamente -->
        </div>
        
        <div class="symbols-grid" id="symbolsGrid">
            <!-- Símbolos se cargan dinámicamente -->
        </div>
        
        <div class="loading" id="loading">Cargando datos...</div>
    </div>
    
    <script>
        let updateInterval;
        
        function formatNumber(num, decimals = 2) {
            if (typeof num !== 'number') return '0.00';
            return num.toFixed(decimals);
        }
        
        function getStatusClass(status) {
            if (status === 'Ejecutándose') return 'running';
            if (status === 'Detenido') return 'stopped';
            return 'warning';
        }
        
        function getValueClass(value) {
            if (value > 0) return 'positive';
            if (value < 0) return 'negative';
            return 'neutral';
        }
        
        function updateSummary(data) {
            const symbols = Object.keys(data.symbols || {});
            const totalTrades = symbols.reduce((sum, symbol) => {
                return sum + (data.symbols[symbol].total_trades || 0);
            }, 0);
            
            const totalReturn = symbols.reduce((sum, symbol) => {
                return sum + (data.symbols[symbol].total_return || 0);
            }, 0);
            
            const activeSims = symbols.filter(symbol => {
                return data.symbols[symbol].process_status === 'Ejecutándose';
            }).length;
            
            const summaryHtml = `
                <div class="summary-card">
                    <h3>Simulaciones Activas</h3>
                    <div class="value">${activeSims}/6</div>
                </div>
                <div class="summary-card">
                    <h3>Total Trades</h3>
                    <div class="value">${totalTrades}</div>
                </div>
                <div class="summary-card">
                    <h3>Retorno Total</h3>
                    <div class="value ${getValueClass(totalReturn)}">${formatNumber(totalReturn, 4)}%</div>
                </div>
                <div class="summary-card">
                    <h3>Promedio por Símbolo</h3>
                    <div class="value ${getValueClass(totalReturn/6)}">${formatNumber(totalReturn/6, 4)}%</div>
                </div>
            `;
            
            document.getElementById('summary').innerHTML = summaryHtml;
        }
        
        function updateSymbols(data) {
            const symbols = data.symbols || {};
            const symbolsHtml = Object.keys(symbols).map(symbol => {
                const stats = symbols[symbol];
                return `
                    <div class="symbol-card">
                        <div class="symbol-header">
                            <div class="symbol-name">${symbol}</div>
                            <div class="status ${getStatusClass(stats.process_status)}">
                                ${stats.process_status || 'Desconocido'}
                            </div>
                        </div>
                        <div class="metrics">
                            <div class="metric">
                                <div class="metric-label">Trades</div>
                                <div class="metric-value">${stats.total_trades || 0}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Retorno Total</div>
                                <div class="metric-value ${getValueClass(stats.total_return)}">
                                    ${formatNumber(stats.total_return || 0, 4)}%
                                </div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Win Rate</div>
                                <div class="metric-value">${formatNumber(stats.win_rate || 0, 1)}%</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Tiempo Activo</div>
                                <div class="metric-value">${stats.uptime || 'N/A'}</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
            document.getElementById('symbolsGrid').innerHTML = symbolsHtml;
        }
        
        function updateDashboard() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('lastUpdate').textContent = 
                        `Última actualización: ${new Date().toLocaleString()}`;
                    
                    updateSummary(data);
                    updateSymbols(data);
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('loading').innerHTML = 
                        '<div class="error">Error al cargar los datos. Reintentando...</div>';
                });
        }
        
        // Inicializar dashboard
        updateDashboard();
        
        // Actualizar cada 30 segundos
        updateInterval = setInterval(updateDashboard, 30000);
        
        // Limpiar intervalo al cerrar la página
        window.addEventListener('beforeunload', () => {
            if (updateInterval) {
                clearInterval(updateInterval);
            }
        });
    </script>
</body>
</html>
        """
        
class DashboardData:
    def __init__(self):
        self.symbols = {
            'NAS100': {'file': 'simulacion_real_nas100_4.py', 'log': 'simulacion_btcusdt_4.jsonl', 'terminal': 4},
            'AUDCAD': {'file': 'simulacion_real_audcad_5.py', 'log': 'simulacion_audusdt_5.jsonl', 'terminal': 5},
            'XAUUSD': {'file': 'simulacion_real_xauusd_6.py', 'log': 'simulacion_btcusdt_6.jsonl', 'terminal': 6},
            'BNBUSDT': {'file': 'simulacion_real_bnbusdt_1.py', 'log': 'simulacion_bnbusdt_1.jsonl', 'terminal': 1},
            'ADAUSDT': {'file': 'simulacion_real_adausdt_2.py', 'log': 'simulacion_adausdt_2.jsonl', 'terminal': 2},
            'SOLUSDT': {'file': 'simulacion_real_solusdt_3.py', 'log': 'simulacion_solusdt_3.jsonl', 'terminal': 3}
        }
        
    def read_log_file(self, log_file: str) -> List[Dict]:
        """Lee el archivo de log JSONL"""
        try:
            if not os.path.exists(log_file):
                return []
                
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            recent_lines = lines[-50:] if len(lines) > 50 else lines
            
            entries = []
            for line in recent_lines:
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
                    
            return entries
        except Exception:
            return []
            
    def calculate_stats(self, symbol: str, entries: List[Dict]) -> Dict:
        """Calcula estadísticas para un símbolo"""
        if not entries:
            return {
                'status': 'Sin datos',
                'total_trades': 0,
                'total_return': 0.0,
                'win_rate': 0.0,
                'last_trade': 'N/A',
                'uptime': 'N/A',
                'avg_return_per_trade': 0.0,
                'process_status': 'Detenido'
            }
            
        trade_entries = [e for e in entries if e.get('tipo') == 'trade']
        
        if not trade_entries:
            return {
                'status': 'Activo - Sin trades',
                'total_trades': 0,
                'total_return': 0.0,
                'win_rate': 0.0,
                'last_trade': 'N/A',
                'uptime': self.calculate_uptime(entries),
                'avg_return_per_trade': 0.0,
                'process_status': self.check_process_status(symbol)
            }
            
        total_trades = len(trade_entries)
        total_return = sum(float(e.get('retorno_total', 0)) for e in trade_entries)
        
        winning_trades = sum(1 for e in trade_entries if float(e.get('retorno_total', 0)) > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        last_trade = trade_entries[-1] if trade_entries else None
        last_trade_time = last_trade.get('timestamp', 'N/A') if last_trade else 'N/A'
        
        avg_return = total_return / total_trades if total_trades > 0 else 0
        
        return {
            'status': 'Activo',
            'total_trades': total_trades,
            'total_return': total_return,
            'win_rate': win_rate,
            'last_trade': last_trade_time,
            'uptime': self.calculate_uptime(entries),
            'avg_return_per_trade': avg_return,
            'process_status': self.check_process_status(symbol)
        }
        
    def calculate_uptime(self, entries: List[Dict]) -> str:
        """Calcula el tiempo de actividad"""
        if not entries:
            return 'N/A'
            
        try:
            first_entry = entries[0]
            last_entry = entries[-1]
            
            first_time = datetime.fromisoformat(first_entry.get('timestamp', '').replace('Z', '+00:00'))
            last_time = datetime.fromisoformat(last_entry.get('timestamp', '').replace('Z', '+00:00'))
            
            uptime = last_time - first_time
            
            hours = int(uptime.total_seconds() // 3600)
            minutes = int((uptime.total_seconds() % 3600) // 60)
            
            return f"{hours}h {minutes}m"
        except:
            return 'N/A'
            
    def check_process_status(self, symbol: str) -> str:
        """Verifica si el proceso está ejecutándose"""
        try:
            log_file = self.symbols[symbol]['log']
            if not os.path.exists(log_file):
                return 'Detenido'
                
            last_modified = os.path.getmtime(log_file)
            current_time = time.time()
            
            if current_time - last_modified > 600:  # 10 minutos
                return 'Posiblemente detenido'
            else:
                return 'Ejecutándose'
                
        except Exception:
            return 'Estado desconocido'
            
    def get_current_stats(self) -> Dict:
        """Obtiene las estadísticas actuales"""
        stats = {}
        for symbol in self.symbols:
            log_file = self.symbols[symbol]['log']
            entries = self.read_log_file(log_file)
            stats[symbol] = self.calculate_stats(symbol, entries)
            
        return {
            'symbols': stats,
            'timestamp': datetime.now().isoformat(),
            'total_symbols': len(self.symbols)
        }
        
def create_handler(dashboard_data):
    def handler(*args, **kwargs):
        return DashboardHandler(*args, dashboard_data=dashboard_data, **kwargs)
    return handler
    
def run_server():
    dashboard_data = DashboardData()
    handler = create_handler(dashboard_data)
    
    server = HTTPServer(('localhost', 8080), handler)
    print("Dashboard web iniciado en: http://localhost:8080")
    print("Presiona Ctrl+C para detener el servidor")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando servidor...")
        server.shutdown()
        
if __name__ == "__main__":
    run_server()
