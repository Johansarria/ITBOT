import datetime
import pytz

# Obtener hora actual en EST
est = pytz.timezone('US/Eastern')
now_est = datetime.datetime.now(est)

print(f"Hora actual EST: {now_est.strftime('%H:%M:%S')}")
print(f"Sesión de prueba configurada: 14:08 - 14:13 EST")

# Calcular tiempo restante
session_start = now_est.replace(hour=14, minute=8, second=0, microsecond=0)
if now_est > session_start:
    print("¡La sesión de prueba ya debería estar activa!")
else:
    time_remaining = session_start - now_est
    print(f"Tiempo restante para la sesión: {time_remaining}")
    
print(f"Estado: {'ACTIVA' if now_est.hour == 14 and 8 <= now_est.minute <= 13 else 'INACTIVA'}")