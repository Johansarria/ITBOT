// Ejemplo mínimo de cBot cTrader para consumir pull/ack del bridge interno
// Nota: Este es un ejemplo didáctico. Ajusta manejo de errores, reconexión,
// y mapeo de símbolos a los de cTrader según tu cuenta.

using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using cAlgo;

namespace ItbotOrderBridgeSample
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.Internet)]
    public class ItbotOrderBridgeSample : Robot
    {
        [Parameter("Web API Base", DefaultValue = "http://localhost:8080")] public string WebApiBase { get; set; }
        [Parameter("Internal Secret", DefaultValue = "local-internal-secret")] public string InternalSecret { get; set; }
        [Parameter("Polling (ms)", DefaultValue = 1000)] public int PollingMs { get; set; }

        private HttpClient _http;

        protected override void OnStart()
        {
            _http = new HttpClient();
            Print("ITBOT cTrader Bridge iniciado: {0}", WebApiBase);

            Timer.Start(TimeSpan.FromMilliseconds(PollingMs));
        }

        protected override void OnTimer()
        {
            Task.Run(async () => await PollAndExecute());
        }

        private async Task PollAndExecute()
        {
            try
            {
                var req = new HttpRequestMessage(HttpMethod.Get, new Uri(new Uri(WebApiBase), "/api/ctrader/orders/pull"));
                req.Headers.Add("X-Internal-Secret", InternalSecret);
                var resp = await _http.SendAsync(req);
                var body = await resp.Content.ReadAsStringAsync();
                if (!resp.IsSuccessStatusCode)
                {
                    Print("[pull] HTTP {0}: {1}", resp.StatusCode, body);
                    return;
                }
                using var doc = JsonDocument.Parse(body);
                var root = doc.RootElement;
                if (!root.TryGetProperty("orders", out var orders) || orders.ValueKind != JsonValueKind.Array)
                    return;
                foreach (var order in orders.EnumerateArray())
                {
                    var oid = order.GetProperty("id").GetString();
                    var symbol = order.GetProperty("symbol").GetString();
                    var side = order.GetProperty("side").GetString();
                    var type = order.GetProperty("type").GetString();
                    var qty = order.GetProperty("quantity").GetDouble();

                    var sym = Symbols.GetSymbol(symbol);
                    if (sym == null)
                    {
                        await Ack(oid, "REJECTED", null, null, $"Símbolo no encontrado: {symbol}");
                        continue;
                    }

                    try
                    {
                        // Solo MARKET en ejemplo
                        if (type == "MARKET")
                        {
                            TradeResult res;
                            if (side == "BUY") res = ExecuteMarketOrder(TradeType.Buy, sym.Name, qty);
                            else if (side == "SELL") res = ExecuteMarketOrder(TradeType.Sell, sym.Name, qty);
                            else throw new Exception($"Side inválido: {side}");

                            if (res.IsSuccessful)
                            {
                                var px = res.Position != null ? (double?)res.Position.EntryPrice : null;
                                await Ack(oid, "FILLED", px, qty, null);
                            }
                            else
                            {
                                await Ack(oid, "REJECTED", null, null, res.Error);
                            }
                        }
                        else
                        {
                            await Ack(oid, "REJECTED", null, null, $"Tipo no soportado en ejemplo: {type}");
                        }
                    }
                    catch (Exception ex)
                    {
                        await Ack(oid, "ERROR", null, null, ex.Message);
                    }
                }
            }
            catch (Exception ex)
            {
                Print("[bridge] error: {0}", ex.Message);
            }
        }

        private async Task Ack(string oid, string status, double? executedPrice, double? executedQty, string error)
        {
            try
            {
                var payload = new
                {
                    id = oid,
                    status = status,
                    executed_price = executedPrice,
                    executed_qty = executedQty,
                    error = error,
                    ts = DateTime.UtcNow.ToString("o")
                };
                var json = JsonSerializer.Serialize(payload);
                var req = new HttpRequestMessage(HttpMethod.Post, new Uri(new Uri(WebApiBase), "/api/ctrader/orders/ack"));
                req.Headers.Add("X-Internal-Secret", InternalSecret);
                req.Content = new StringContent(json, Encoding.UTF8, "application/json");
                var resp = await _http.SendAsync(req);
                var body = await resp.Content.ReadAsStringAsync();
                if (!resp.IsSuccessStatusCode)
                {
                    Print("[ack] HTTP {0}: {1}", resp.StatusCode, body);
                }
            }
            catch (Exception ex)
            {
                Print("[ack] error: {0}", ex.Message);
            }
        }

        protected override void OnStop()
        {
            _http?.Dispose();
        }
    }
}
