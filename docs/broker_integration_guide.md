# SICAR - Guía de Integración con Brokers Tradicionales

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Instalación y Configuración](#instalación-y-configuración)
4. [Brokers Soportados](#brokers-soportados)
5. [Guía de Uso](#guía-de-uso)
6. [Sistema de Órdenes](#sistema-de-órdenes)
7. [Sincronización de Datos](#sincronización-de-datos)
8. [Monitoreo y Alertas](#monitoreo-y-alertas)
9. [Testing y Validación](#testing-y-validación)
10. [Mejores Prácticas](#mejores-prácticas)
11. [Solución de Problemas](#solución-de-problemas)
12. [API Reference](#api-reference)

## Introducción

La integración con brokers tradicionales de SICAR permite el trading automatizado de ETFs e índices a través de múltiples plataformas de corretaje. Este sistema proporciona:

- **Conectividad Multi-Broker**: Soporte para Interactive Brokers, TD Ameritrade y otros
- **Gestión Unificada de Órdenes**: Sistema centralizado para manejo de órdenes
- **Sincronización de Datos**: Datos en tiempo real de múltiples fuentes
- **Monitoreo Avanzado**: Dashboard web para supervisión del sistema
- **Testing Integral**: Suite completa de pruebas automatizadas

### Características Principales

- ✅ Soporte para múltiples brokers simultáneamente
- ✅ Gestión de riesgo integrada
- ✅ Recuperación automática ante fallos
- ✅ Monitoreo en tiempo real
- ✅ Backtesting y simulación
- ✅ Documentación completa

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    SICAR Core System                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Strategy      │  │   Risk          │  │   Market     │ │
│  │   Adapter       │  │   Management    │  │   Hours      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Order         │  │   Data Sync     │  │   Monitoring │ │
│  │   Management    │  │   System        │  │   Dashboard  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                 Broker Connectors Layer                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Interactive    │  │  TD Ameritrade  │  │    Future    │ │
│  │   Brokers       │  │   Connector     │  │  Connectors  │ │
│  │   Connector     │  └─────────────────┘  └──────────────┘ │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Principales

1. **Broker Connectors**: Interfaces específicas para cada broker
2. **Order Management System**: Gestión centralizada de órdenes
3. **Data Synchronization**: Sincronización de datos multi-fuente
4. **Monitoring Dashboard**: Interface web de monitoreo
5. **Testing Framework**: Sistema de pruebas automatizadas

## Instalación y Configuración

### Requisitos del Sistema

- Python 3.8+
- Windows 10/11 o Linux
- 8GB RAM mínimo (16GB recomendado)
- Conexión a internet estable
- Cuentas activas en brokers soportados

### Dependencias

```bash
# Instalar dependencias principales
pip install pandas numpy asyncio websockets flask
pip install ib-insync requests python-dotenv
pip install pytest pytest-asyncio psutil

# Para desarrollo
pip install black flake8 mypy
```

### Configuración Inicial

1. **Crear archivo de configuración**:

```python
# config/broker_config.py
BROKER_CONFIG = {
    "interactive_brokers": {
        "host": "localhost",
        "port": 7497,  # TWS Demo: 7497, TWS Live: 7496
        "client_id": 1,
        "timeout": 30,
        "max_retries": 3
    },
    "td_ameritrade": {
        "api_key": "YOUR_API_KEY",
        "redirect_uri": "http://localhost:8080",
        "token_file": "td_token.json",
        "sandbox": True  # False para producción
    },
    "risk_management": {
        "max_daily_loss": 0.02,  # 2%
        "max_position_size": 0.1,  # 10%
        "max_concurrent_orders": 50
    },
    "data_sync": {
        "update_interval": 1,  # segundos
        "cache_size": 10000,
        "quality_threshold": 0.95
    }
}
```

2. **Variables de entorno**:

```bash
# .env
IB_HOST=localhost
IB_PORT=7497
IB_CLIENT_ID=1

TDA_API_KEY=your_api_key_here
TDA_REDIRECT_URI=http://localhost:8080

SICAR_LOG_LEVEL=INFO
SICAR_DATA_DIR=./data
SICAR_CACHE_DIR=./cache
```

3. **Inicialización del sistema**:

```python
from src.brokers.interactive_brokers_connector import InteractiveBrokersConnector
from src.brokers.td_ameritrade_connector import TDAmeritradeConnector
from src.order_management.order_management_system import OrderManagementSystem

# Inicializar conectores
ib_connector = InteractiveBrokersConnector()
tda_connector = TDAmeritradeConnector()

# Inicializar sistema de órdenes
order_system = OrderManagementSystem()
order_system.register_broker("IB", ib_connector)
order_system.register_broker("TDA", tda_connector)
```

## Brokers Soportados

### Interactive Brokers

**Características**:
- Acceso a mercados globales
- Comisiones bajas
- API robusta (TWS API)
- Soporte para múltiples tipos de órdenes

**Configuración**:
```python
# Configurar TWS (Trader Workstation)
# 1. Instalar TWS o IB Gateway
# 2. Habilitar API en configuración
# 3. Configurar puerto (7497 demo, 7496 live)
# 4. Permitir conexiones desde localhost

ib_config = {
    "host": "localhost",
    "port": 7497,
    "client_id": 1,
    "account": "DU123456"  # Cuenta demo
}
```

**Tipos de órdenes soportadas**:
- Market Orders
- Limit Orders
- Stop Orders
- Stop-Limit Orders
- Trailing Stop Orders

### TD Ameritrade

**Características**:
- API REST moderna
- Datos de mercado en tiempo real
- Soporte para ETFs y opciones
- Integración con ThinkorSwim

**Configuración**:
```python
# Obtener API Key desde TD Ameritrade Developer
# 1. Crear cuenta en developer.tdameritrade.com
# 2. Crear aplicación
# 3. Obtener Consumer Key
# 4. Configurar OAuth

tda_config = {
    "api_key": "YOUR_CONSUMER_KEY@AMER.OAUTHAP",
    "redirect_uri": "http://localhost:8080",
    "account_id": "123456789"
}
```

**Autenticación OAuth**:
```python
# Proceso de autenticación inicial
async def authenticate_tda():
    connector = TDAmeritradeConnector()
    
    # Generar URL de autorización
    auth_url = connector.get_authorization_url()
    print(f"Visita: {auth_url}")
    
    # Obtener código de autorización
    auth_code = input("Ingresa el código: ")
    
    # Obtener tokens
    await connector.authenticate(auth_code)
```

## Guía de Uso

### Conexión Básica

```python
import asyncio
from src.brokers.interactive_brokers_connector import InteractiveBrokersConnector

async def basic_connection():
    # Crear conector
    connector = InteractiveBrokersConnector()
    
    try:
        # Conectar
        await connector.connect()
        print("Conectado exitosamente")
        
        # Verificar conexión
        if connector.is_connected():
            print("Estado: Conectado")
            
            # Obtener información de cuenta
            account_info = await connector.get_account_info()
            print(f"Cuenta: {account_info}")
        
    except Exception as e:
        print(f"Error de conexión: {e}")
    
    finally:
        # Desconectar
        await connector.disconnect()

# Ejecutar
asyncio.run(basic_connection())
```

### Colocación de Órdenes

```python
from src.order_management.order_management_system import OrderManagementSystem
from src.order_management.order_management_system import create_market_order

async def place_orders():
    # Inicializar sistema
    order_system = OrderManagementSystem()
    
    # Registrar brokers
    ib_connector = InteractiveBrokersConnector()
    await ib_connector.connect()
    order_system.register_broker("IB", ib_connector)
    
    # Crear orden de mercado
    order = create_market_order(
        symbol="SPY",
        quantity=100,
        side="BUY",
        broker_preference="IB"
    )
    
    # Colocar orden
    order_id = await order_system.place_order(order)
    print(f"Orden colocada: {order_id}")
    
    # Monitorear orden
    while True:
        status = await order_system.get_order_status(order_id)
        print(f"Estado: {status}")
        
        if status in ["FILLED", "CANCELLED", "REJECTED"]:
            break
        
        await asyncio.sleep(1)
```

### Obtención de Datos de Mercado

```python
async def get_market_data():
    connector = InteractiveBrokersConnector()
    await connector.connect()
    
    # Suscribirse a datos en tiempo real
    def on_market_data(data):
        print(f"Precio {data['symbol']}: {data['price']}")
    
    await connector.subscribe_market_data("SPY", on_market_data)
    
    # Obtener datos históricos
    historical_data = await connector.get_historical_data(
        symbol="SPY",
        duration="1 D",
        bar_size="1 min"
    )
    
    print(f"Datos históricos: {len(historical_data)} barras")
```

## Sistema de Órdenes

### Tipos de Órdenes

El sistema soporta múltiples tipos de órdenes:

```python
from src.order_management.order_management_system import (
    create_market_order,
    create_limit_order,
    create_stop_order
)

# Orden de mercado
market_order = create_market_order(
    symbol="SPY",
    quantity=100,
    side="BUY"
)

# Orden límite
limit_order = create_limit_order(
    symbol="QQQ",
    quantity=50,
    side="SELL",
    limit_price=380.50
)

# Orden stop
stop_order = create_stop_order(
    symbol="IWM",
    quantity=200,
    side="SELL",
    stop_price=195.00
)
```

### Gestión de Riesgo

```python
# Configurar límites de riesgo
risk_config = {
    "max_daily_loss": 0.02,  # 2% pérdida máxima diaria
    "max_position_size": 0.1,  # 10% del capital por posición
    "max_leverage": 2.0,  # Apalancamiento máximo 2:1
    "allowed_symbols": ["SPY", "QQQ", "IWM", "DIA"],
    "trading_hours_only": True
}

order_system.configure_risk_management(risk_config)
```

### Callbacks y Notificaciones

```python
# Configurar callbacks para eventos de órdenes
def on_order_filled(order_id, execution_details):
    print(f"Orden {order_id} ejecutada: {execution_details}")

def on_order_rejected(order_id, reason):
    print(f"Orden {order_id} rechazada: {reason}")

def on_position_update(symbol, position):
    print(f"Posición actualizada {symbol}: {position}")

# Registrar callbacks
order_system.add_order_callback(on_order_filled)
order_system.add_rejection_callback(on_order_rejected)
order_system.add_position_callback(on_position_update)
```

## Sincronización de Datos

### Configuración Multi-Fuente

```python
from src.data_sync.data_synchronization_system import DataSynchronizationSystem

# Inicializar sistema de sincronización
sync_system = DataSynchronizationSystem()

# Registrar fuentes de datos
sync_system.register_source("IB", ib_connector, priority=1)
sync_system.register_source("TDA", tda_connector, priority=2)

# Configurar resolución de conflictos
conflict_config = {
    "method": "priority",  # priority, quality, timestamp, average
    "quality_threshold": 0.95,
    "max_age_seconds": 5
}

sync_system.configure_conflict_resolution(conflict_config)

# Iniciar sincronización
await sync_system.start_sync()
```

### Callbacks de Datos

```python
# Callback para datos sincronizados
def on_synchronized_data(symbol, data):
    print(f"Datos sincronizados para {symbol}: {data}")

# Callback para conflictos
def on_data_conflict(symbol, sources, resolution):
    print(f"Conflicto resuelto para {symbol}: {resolution}")

sync_system.add_data_callback(on_synchronized_data)
sync_system.add_conflict_callback(on_data_conflict)
```

## Monitoreo y Alertas

### Dashboard Web

El sistema incluye un dashboard web para monitoreo en tiempo real:

```python
from src.monitoring.monitoring_dashboard import MonitoringDashboard

# Inicializar dashboard
dashboard = MonitoringDashboard()

# Registrar brokers para monitoreo
dashboard.register_broker("IB", ib_connector)
dashboard.register_broker("TDA", tda_connector)

# Configurar alertas
alert_config = {
    "connection_timeout": 30,  # segundos
    "order_rejection_threshold": 5,  # órdenes por minuto
    "latency_threshold": 1000,  # milisegundos
    "error_rate_threshold": 0.05  # 5%
}

dashboard.configure_alerts(alert_config)

# Iniciar dashboard (puerto 5000)
dashboard.run(host="localhost", port=5000, debug=False)
```

### Acceso al Dashboard

1. Abrir navegador en `http://localhost:5000`
2. Ver estado de conexiones en tiempo real
3. Monitorear órdenes activas
4. Revisar métricas de rendimiento
5. Configurar alertas personalizadas

### Alertas por Email/SMS

```python
# Configurar notificaciones
notification_config = {
    "email": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your_email@gmail.com",
        "password": "your_app_password",
        "recipients": ["trader@company.com"]
    },
    "webhook": {
        "url": "https://hooks.slack.com/services/...",
        "method": "POST"
    }
}

dashboard.configure_notifications(notification_config)
```

## Testing y Validación

### Ejecución de Pruebas

```bash
# Ejecutar todas las pruebas
python -m pytest src/testing/broker_integration_tests.py -v

# Ejecutar pruebas específicas
python -m pytest src/testing/broker_integration_tests.py::test_broker_connection -v

# Ejecutar con cobertura
python -m pytest src/testing/broker_integration_tests.py --cov=src --cov-report=html
```

### Pruebas Automatizadas

```python
from src.testing.broker_integration_tests import BrokerIntegrationTester

async def run_tests():
    tester = BrokerIntegrationTester()
    
    # Ejecutar suite completa
    results = await tester.run_all_tests()
    
    # Generar reporte
    report = tester.generate_test_report()
    print(report)
    
    # Exportar resultados
    df = tester.export_results_to_dataframe()
    df.to_csv("test_results.csv", index=False)

asyncio.run(run_tests())
```

### Simulación de Mercado

```python
# Configurar simulación
simulation_config = {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 100000,
    "symbols": ["SPY", "QQQ", "IWM"],
    "strategy": "momentum",
    "risk_level": "medium"
}

# Ejecutar simulación
from src.testing.market_simulator import MarketSimulator

simulator = MarketSimulator(simulation_config)
results = await simulator.run_simulation()

print(f"ROI: {results['roi']:.2f}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
```

## Mejores Prácticas

### Gestión de Conexiones

1. **Reconexión Automática**:
```python
async def robust_connection(connector, max_retries=3):
    for attempt in range(max_retries):
        try:
            await connector.connect()
            return True
        except Exception as e:
            print(f"Intento {attempt + 1} fallido: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial
    return False
```

2. **Monitoreo de Salud**:
```python
async def health_check(connector):
    try:
        # Verificar conexión
        if not connector.is_connected():
            await connector.reconnect()
        
        # Verificar latencia
        start_time = time.time()
        await connector.get_account_info()
        latency = (time.time() - start_time) * 1000
        
        if latency > 1000:  # 1 segundo
            print(f"Advertencia: Alta latencia {latency:.0f}ms")
        
        return True
    except Exception as e:
        print(f"Health check fallido: {e}")
        return False
```

### Gestión de Errores

1. **Manejo de Excepciones**:
```python
from src.brokers.exceptions import (
    BrokerConnectionError,
    OrderRejectionError,
    InsufficientFundsError
)

async def safe_order_placement(order_system, order):
    try:
        order_id = await order_system.place_order(order)
        return order_id
    except BrokerConnectionError:
        # Intentar reconectar
        await order_system.reconnect_all_brokers()
        return await order_system.place_order(order)
    except OrderRejectionError as e:
        # Log y notificar
        logger.error(f"Orden rechazada: {e}")
        return None
    except InsufficientFundsError:
        # Reducir tamaño de orden
        order.quantity = order.quantity // 2
        return await order_system.place_order(order)
```

2. **Logging Estructurado**:
```python
import logging
import json

# Configurar logger
logger = logging.getLogger("sicar.brokers")
handler = logging.FileHandler("broker_operations.log")
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Log estructurado
def log_order_event(event_type, order_id, details):
    log_data = {
        "event_type": event_type,
        "order_id": order_id,
        "timestamp": datetime.now().isoformat(),
        "details": details
    }
    logger.info(json.dumps(log_data))
```

### Optimización de Rendimiento

1. **Pool de Conexiones**:
```python
class BrokerConnectionPool:
    def __init__(self, broker_class, pool_size=5):
        self.broker_class = broker_class
        self.pool_size = pool_size
        self.connections = []
        self.available = asyncio.Queue()
    
    async def get_connection(self):
        if self.available.empty() and len(self.connections) < self.pool_size:
            conn = self.broker_class()
            await conn.connect()
            self.connections.append(conn)
            return conn
        
        return await self.available.get()
    
    async def return_connection(self, conn):
        await self.available.put(conn)
```

2. **Caché de Datos**:
```python
from functools import lru_cache
import time

class DataCache:
    def __init__(self, ttl=60):  # 60 segundos TTL
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())
```

### Seguridad

1. **Gestión de Credenciales**:
```python
import os
from cryptography.fernet import Fernet

class SecureCredentials:
    def __init__(self):
        self.key = os.environ.get('SICAR_ENCRYPTION_KEY')
        if not self.key:
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt_credential(self, credential):
        return self.cipher.encrypt(credential.encode()).decode()
    
    def decrypt_credential(self, encrypted_credential):
        return self.cipher.decrypt(encrypted_credential.encode()).decode()
```

2. **Validación de Entrada**:
```python
def validate_order(order):
    # Validar símbolo
    if not order.symbol or len(order.symbol) > 10:
        raise ValueError("Símbolo inválido")
    
    # Validar cantidad
    if order.quantity <= 0 or order.quantity > 10000:
        raise ValueError("Cantidad inválida")
    
    # Validar precio (si aplica)
    if order.price and (order.price <= 0 or order.price > 10000):
        raise ValueError("Precio inválido")
    
    return True
```

## Solución de Problemas

### Problemas Comunes

1. **Error de Conexión con Interactive Brokers**:
```
Error: Connection refused
Solución:
- Verificar que TWS/IB Gateway esté ejecutándose
- Confirmar puerto correcto (7497 demo, 7496 live)
- Habilitar API en configuración de TWS
- Verificar que el client_id no esté en uso
```

2. **Error de Autenticación TD Ameritrade**:
```
Error: Invalid token
Solución:
- Verificar API key correcta
- Renovar token de acceso
- Confirmar redirect_uri coincide
- Verificar permisos de cuenta
```

3. **Órdenes Rechazadas**:
```
Error: Order rejected
Solución:
- Verificar fondos suficientes
- Confirmar horarios de mercado
- Validar símbolo y tipo de orden
- Revisar límites de posición
```

### Diagnóstico

```python
async def diagnose_system():
    """Función de diagnóstico del sistema"""
    
    print("=== Diagnóstico del Sistema SICAR ===")
    
    # 1. Verificar conexiones
    print("\n1. Estado de Conexiones:")
    for broker_name, connector in brokers.items():
        try:
            status = "Conectado" if connector.is_connected() else "Desconectado"
            print(f"   {broker_name}: {status}")
        except Exception as e:
            print(f"   {broker_name}: Error - {e}")
    
    # 2. Verificar configuración
    print("\n2. Configuración:")
    config_items = [
        ("IB_HOST", os.getenv("IB_HOST")),
        ("IB_PORT", os.getenv("IB_PORT")),
        ("TDA_API_KEY", "***" if os.getenv("TDA_API_KEY") else None)
    ]
    
    for item, value in config_items:
        status = "✓" if value else "✗"
        print(f"   {status} {item}: {value}")
    
    # 3. Verificar permisos
    print("\n3. Permisos de Archivo:")
    directories = ["./data", "./logs", "./cache"]
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            test_file = os.path.join(directory, "test.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print(f"   ✓ {directory}: Escribible")
        except Exception as e:
            print(f"   ✗ {directory}: Error - {e}")
    
    # 4. Verificar dependencias
    print("\n4. Dependencias:")
    required_modules = ["pandas", "numpy", "asyncio", "ib_insync", "requests"]
    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✓ {module}: Instalado")
        except ImportError:
            print(f"   ✗ {module}: No encontrado")
```

### Logs y Debugging

```python
# Configurar logging detallado
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sicar_debug.log'),
        logging.StreamHandler()
    ]
)

# Logger específico para brokers
broker_logger = logging.getLogger('sicar.brokers')
broker_logger.setLevel(logging.DEBUG)

# Logger para órdenes
order_logger = logging.getLogger('sicar.orders')
order_logger.setLevel(logging.INFO)
```

## API Reference

### BrokerConnectorInterface

```python
class BrokerConnectorInterface(ABC):
    @abstractmethod
    async def connect(self) -> bool:
        """Conectar al broker"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Desconectar del broker"""
        pass
    
    @abstractmethod
    async def place_order(self, order: UnifiedOrder) -> str:
        """Colocar orden"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Obtener posiciones"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Obtener información de cuenta"""
        pass
```

### OrderManagementSystem

```python
class OrderManagementSystem:
    def __init__(self):
        """Inicializar sistema de órdenes"""
    
    def register_broker(self, broker_id: str, connector: BrokerConnectorInterface):
        """Registrar broker"""
    
    async def place_order(self, order: UnifiedOrder) -> str:
        """Colocar orden"""
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden"""
    
    def get_order_status(self, order_id: str) -> OrderStatus:
        """Obtener estado de orden"""
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas"""
```

### DataSynchronizationSystem

```python
class DataSynchronizationSystem:
    def __init__(self):
        """Inicializar sistema de sincronización"""
    
    def register_source(self, source_id: str, connector: Any, priority: int = 1):
        """Registrar fuente de datos"""
    
    async def start_sync(self):
        """Iniciar sincronización"""
    
    async def stop_sync(self):
        """Detener sincronización"""
    
    def get_latest_data(self, symbol: str) -> Optional[DataPoint]:
        """Obtener datos más recientes"""
```

---

## Contacto y Soporte

Para soporte técnico o consultas:

- **Email**: support@sicar-trading.com
- **Documentación**: https://docs.sicar-trading.com
- **GitHub**: https://github.com/sicar-trading/sicar
- **Discord**: https://discord.gg/sicar-trading

---

*Última actualización: Enero 2025*
*Versión: 1.0.0*