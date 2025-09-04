# ITBOT cTrader Live Overlay

Muestra en el gráfico el régimen de mercado, el precio actual y el PnL estimado de la posición abierta del bot.

## Requisitos
- cTrader Desktop
- Acceso HTTP desde cTrader al endpoint del panel web

## Uso
1. Importa `ItbotLiveOverlay.cAlgo.cs` en cTrader (Automate > Open cBot > New > pega el código y compila).
2. Arrastra el cBot al gráfico del símbolo correspondiente (por ej. BTCUSDT).
3. Configura parámetros:
   - API Base URL: `http://<host>:8080`
   - Token: (si tu API lo requiere; déjalo vacío si no)
   - Símbolo: `BTCUSDT`
   - Segundos de sondeo: 5–10
4. Inicia el cBot. Verás Régimen, Precio y PnL estimado.

## Endpoint
GET `/api/ctrader/snapshot?symbol=BTCUSDT&token=<opcional>`

Respuesta:
```
{
  "symbol": "BTCUSDT",
  "regime": "trending_bull|bear|sideways|...",
  "active_strategies_count": 0,
  "current_pairs": ["BTCUSDT", ...],
  "open_position": {
    "operation_id": 123,
    "timestamp": "2025-09-01T12:34:56Z",
    "side": "BUY|SELL",
    "price": 58200.0,
    "quantity": 0.01,
    "decision": "ENTER",
    "pnl_estimated": 12.34
  },
  "current_price": 58350.0,
  "recent_trades": [ ... ]
}
```

## Notas
- El PnL es estimado con precio spot y cantidad; comisiones no incluidas.
- Si no hay posición abierta, PnL no se muestra.
- Asegura que el puerto 8080 esté accesible desde la máquina con cTrader.
# ITBOT cTrader Overlay

Visual superligera para ver el estado de ITBOT directamente en cTrader (chart overlay).

## Qué hace
- Llama al endpoint del panel web `/api/ctrader/snapshot`.
- Muestra régimen actual, nº de estrategias activas, posición abierta del símbolo y últimas operaciones.
- Dibuja una línea horizontal en el precio de entrada si hay posición abierta.

## Requisitos
- Servicio web de ITBOT accesible (por defecto http://HOST:8080).
- Token válido: `GET /api/generate_token` (o desde el login del panel web).

## Instalar en cTrader
1. Abrir cTrader Desktop.
2. Ir a Automate > New cBot > importar el archivo `ItbotLiveOverlay.cAlgo.cs`.
3. Pegar el contenido del archivo y compilar.
4. Adjuntar el cBot al símbolo correspondiente (ej. BTCUSD o el que uses; el símbolo para ITBOT se pasa por parámetro como `BTCUSDT`).

## Parámetros
- ApiBaseUrl: URL del panel, ej. `http://127.0.0.1:8080`
- Token: el token generado por `/api/generate_token`.
- Symbol: símbolo ITBOT (ej. `BTCUSDT`).
- PollSeconds: frecuencia de refresco (5-10 recomendado).

## Probar rápido (opcional)
- Genera un token:
  - Visita `http://HOST:8080/api/generate_token` y copia el `token`.
- Prueba el snapshot en el navegador:
  - `http://HOST:8080/api/ctrader/snapshot?token=<TOKEN>&symbol=BTCUSDT`

## Notas
- El endpoint usa la DB para leer operaciones y el último régimen guardado por el Controlador V3.
- Si no hay posición, el overlay muestra "Sin posición".
- Si tu símbolo en cTrader no coincide con el de ITBOT, sólo afecta al overlay (la API usa el parámetro `Symbol`).
