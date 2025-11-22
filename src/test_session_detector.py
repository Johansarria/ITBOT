"""
Script temporal para probar el detector de sesiones
"""
from session_detector import SessionDetector
import datetime
import pytz

# Crear detector
detector = SessionDetector()

# Obtener tiempo actual
est = pytz.timezone('US/Eastern')
now = datetime.datetime.now(est)
print(f'Hora actual EST: {now.strftime("%H:%M:%S")}')

# Verificar sesión actual
current_session = detector.get_current_session()
print(f'Sesión actual: {current_session}')

# Simular hora de sesión europea (03:02)
test_time = '03:02'
print(f'\nPrueba con hora {test_time}:')
for session_name, config in detector.sessions_config.items():
    if detector._is_time_in_session(test_time, config):
        print(f'  ✅ {session_name}: DETECTADA')
    else:
        print(f'  ❌ {session_name}: NO detectada')

# Verificar configuración de sesión europea
print(f'\nConfiguración sesión europea:')
european_config = detector.sessions_config['european']
for key, value in european_config.items():
    print(f'  {key}: {value}')

# Probar conversión de tiempo
print(f'\nPrueba conversión de tiempo:')
print(f'03:00 = {detector._time_to_minutes("03:00")} minutos')
print(f'03:02 = {detector._time_to_minutes("03:02")} minutos')
print(f'03:05 = {detector._time_to_minutes("03:05")} minutos')