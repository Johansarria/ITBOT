#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# Configurar variables de entorno manualmente
os.environ['TELEGRAM_BOT_TOKEN'] = '7932329638:AAG0LNwit7o7R17ezd-3Fkgc1m_Hne5Qj0s'
os.environ['TELEGRAM_CHAT_ID'] = '5277296078'
os.environ['BINANCE_API_KEY'] = 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs'
os.environ['BINANCE_SECRET_KEY'] = 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'
os.environ['DB_USER'] = 'itbot_db_prueba'
os.environ['DB_PASSWORD'] = '14564430'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'itbot_db'
os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'
os.environ['MLFLOW_TRACKING_URI'] = 'http://localhost:5000'
os.environ['ADMIN_TELEGRAM_ID'] = '987654321'

print("=== PRUEBA DE CONEXIONES ITBOT ===")
print()

# 1. Verificar variables de entorno
print("1. VERIFICANDO VARIABLES DE ENTORNO:")
print(f"TELEGRAM_BOT_TOKEN: {'✓' if os.getenv('TELEGRAM_BOT_TOKEN') else '✗'}")
print(f"BINANCE_API_KEY: {'✓' if os.getenv('BINANCE_API_KEY') else '✗'}")
print(f"DB_HOST: {os.getenv('DB_HOST', 'No configurado')}")
print(f"REDIS_HOST: {os.getenv('REDIS_HOST', 'No configurado')}")
print()

# 2. Probar conexión a Binance
print("2. PROBANDO CONEXIÓN A BINANCE:")
try:
    from binance.client import Client
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if api_key and secret_key:
        client = Client(api_key, secret_key, testnet=False)
        # Probar conexión básica
        server_time = client.get_server_time()
        print("✓ Conexión a Binance exitosa")
        print(f"  Hora del servidor: {server_time['serverTime']}")
        
        # Probar información de cuenta
        try:
            account_info = client.get_account()
            print(f"  Estado de cuenta: {account_info.get('accountType', 'N/A')}")
            print(f"  Balances disponibles: {len([b for b in account_info.get('balances', []) if float(b['free']) > 0])}")
        except Exception as e:
            print(f"  Advertencia: No se pudo obtener info de cuenta: {str(e)}")
    else:
        print("✗ API keys de Binance no configuradas")
except ImportError:
    print("✗ Módulo python-binance no instalado")
    print("  Para instalar: pip install python-binance")
except Exception as e:
    print(f"✗ Error en conexión a Binance: {str(e)}")
print()

# 3. Probar conexión a PostgreSQL
print("3. PROBANDO CONEXIÓN A POSTGRESQL:")
try:
    import psycopg2
    from psycopg2 import sql
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'itbot_db'),
        'user': os.getenv('DB_USER', 'itbot_db_prueba'),
        'password': os.getenv('DB_PASSWORD', '14564430')
    }
    
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    print("✓ Conexión a PostgreSQL exitosa")
    print(f"  Versión: {version.split()[0]} {version.split()[1]}")
    
    cursor.execute('SELECT current_database();')
    db_name = cursor.fetchone()[0]
    print(f"  Base de datos: {db_name}")
    
    # Verificar si existen tablas del bot
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = cursor.fetchall()
    print(f"  Tablas encontradas: {len(tables)}")
    
    cursor.close()
    conn.close()
except ImportError:
    print("✗ Módulo psycopg2 no instalado")
    print("  Para instalar: pip install psycopg2-binary")
except Exception as e:
    print(f"✗ Error en conexión a PostgreSQL: {str(e)}")
    print("  Verifica que PostgreSQL esté ejecutándose y la base de datos exista")
print()

# 4. Probar conexión a Redis
print("4. PROBANDO CONEXIÓN A REDIS:")
try:
    import redis
    
    redis_config = {
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', '6379')),
        'decode_responses': True
    }
    
    r = redis.Redis(**redis_config)
    r.ping()
    print("✓ Conexión a Redis exitosa")
    
    info = r.info()
    print(f"  Versión: {info.get('redis_version', 'N/A')}")
    print(f"  Memoria usada: {info.get('used_memory_human', 'N/A')}")
    print(f"  Clientes conectados: {info.get('connected_clients', 'N/A')}")
except ImportError:
    print("✗ Módulo redis no instalado")
    print("  Para instalar: pip install redis")
except Exception as e:
    print(f"✗ Error en conexión a Redis: {str(e)}")
    print("  Verifica que Redis esté ejecutándose")
print()

# 5. Verificar MLflow
print("5. VERIFICANDO MLFLOW:")
try:
    import mlflow
    tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    mlflow.set_tracking_uri(tracking_uri)
    print(f"✓ MLflow configurado")
    print(f"  URI: {tracking_uri}")
    
    # Intentar listar experimentos
    try:
        experiments = mlflow.search_experiments()
        print(f"  Experimentos disponibles: {len(experiments)}")
    except Exception as e:
        print(f"  Advertencia: No se pudo conectar al servidor MLflow: {str(e)}")
except ImportError:
    print("✗ Módulo mlflow no instalado")
    print("  Para instalar: pip install mlflow")
except Exception as e:
    print(f"✗ Error en MLflow: {str(e)}")

print()
print("=== RESUMEN ===")
print("Para instalar todas las dependencias:")
print("pip install python-binance psycopg2-binary redis mlflow")
print()
print("=== FIN DE PRUEBAS ===")