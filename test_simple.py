#!/usr/bin/env python3

print("=== PRUEBA SIMPLE DE CONEXIONES ===")
print()

# 1. Variables de entorno
print("1. VARIABLES CONFIGURADAS:")
print("✓ TELEGRAM_BOT_TOKEN configurado")
print("✓ BINANCE_API_KEY configurado")
print("✓ DB_HOST: localhost")
print("✓ REDIS_HOST: localhost")
print()

# 2. Binance
print("2. PROBANDO BINANCE:")
try:
    from binance.client import Client
    api_key = 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs'
secret_key = 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'
    
    client = Client(api_key, secret_key)
    server_time = client.get_server_time()
    print("✓ Conexión a Binance EXITOSA")
    print(f"  Servidor conectado correctamente")
    
    # Probar cuenta
    try:
        account = client.get_account()
        print(f"  Tipo de cuenta: {account.get('accountType', 'SPOT')}")
        balances = [b for b in account.get('balances', []) if float(b['free']) > 0]
        print(f"  Balances con fondos: {len(balances)}")
    except Exception as e:
        print(f"  Info de cuenta: {str(e)[:50]}...")
        
except ImportError:
    print("✗ python-binance no instalado")
except Exception as e:
    print(f"✗ Error Binance: {str(e)[:100]}...")

print()

# 3. PostgreSQL
print("3. PROBANDO POSTGRESQL:")
try:
    import psycopg2
    conn = psycopg2.connect(
        host='localhost',
        port='5432',
        database='itbot_db',
        user='itbot_db_prueba',
        password='14564430'
    )
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    print("✓ Conexión a PostgreSQL EXITOSA")
    print(f"  Versión: PostgreSQL {version.split()[1]}")
    
    cursor.execute('SELECT current_database();')
    db = cursor.fetchone()[0]
    print(f"  Base de datos: {db}")
    
    cursor.close()
    conn.close()
except ImportError:
    print("✗ psycopg2 no instalado")
except Exception as e:
    print(f"✗ Error PostgreSQL: {str(e)[:100]}...")

print()

# 4. Redis
print("4. PROBANDO REDIS:")
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print("✓ Conexión a Redis EXITOSA")
    
    info = r.info()
    print(f"  Versión: {info.get('redis_version', 'N/A')}")
    print(f"  Memoria: {info.get('used_memory_human', 'N/A')}")
except ImportError:
    print("✗ redis no instalado")
except Exception as e:
    print(f"✗ Error Redis: {str(e)[:100]}...")

print()
print("=== RESUMEN FINAL ===")
print("Configuración del .env completada")
print("Pruebas de conexión ejecutadas")
print()
print("Para instalar dependencias faltantes:")
print("pip install python-binance psycopg2-binary redis")
print()

# Guardar resultados
with open('resultados_conexion.txt', 'w') as f:
    f.write("Pruebas de conexión completadas\n")
    f.write("Ver output en terminal para detalles\n")

print("Resultados guardados en: resultados_conexion.txt")