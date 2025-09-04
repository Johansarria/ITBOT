using cAlgo;
using cAlgo.API;
using System;
using System.Net.Http;
using System.Threading.Tasks;
using System.Text.Json;

namespace cAlgo
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.Internet)]
    public class ItbotLiveOverlay : Robot
    {
        [Parameter("API Base URL", DefaultValue = "http://localhost:8080")] public string ApiBaseUrl { get; set; }
        [Parameter("Token", DefaultValue = "")] public string Token { get; set; }
        [Parameter("Símbolo", DefaultValue = "BTCUSDT")] public string SymbolParam { get; set; }
        [Parameter("Segundos de sondeo", DefaultValue = 5)] public int PollSeconds { get; set; }

        private HttpClient _http;
        private ChartText _regimeText, _pnlText, _priceText;
        private ChartHorizontalLine _entryLine;

        protected override void OnStart()
        {
            _http = new HttpClient();
            Chart.DrawStaticText("hdr", "ITBOT V3 Dinámico", VerticalAlignment.Top, HorizontalAlignment.Left, Color.Orange);
            _regimeText = Chart.DrawText("regime", "Regimen: -", Chart.BarsLastVisibleTime, Chart.HighestVisiblePrice, Color.Aqua);
            _pnlText = Chart.DrawText("pnl", "PnL: -", Chart.BarsLastVisibleTime, Chart.HighestVisiblePrice * 0.98, Color.Lime);
            _priceText = Chart.DrawText("price", "Precio: -", Chart.BarsLastVisibleTime, Chart.HighestVisiblePrice * 0.96, Color.Yellow);
            Timer.Start(TimeSpan.FromSeconds(Math.Max(2, PollSeconds)));
        }

        protected override void OnTimer()
        {
            _ = RefreshAsync();
            _ = PushSnapshotAsync();
        }

        private async Task RefreshAsync()
        {
            try
            {
                var url = $"{ApiBaseUrl}/api/ctrader/snapshot?symbol={SymbolParam}&token={Token}";
                var res = await _http.GetAsync(url);
                var json = await res.Content.ReadAsStringAsync();
                using var doc = JsonDocument.Parse(json);
                var root = doc.RootElement;
                var regime = root.GetProperty("regime").GetString();
                var currentPrice = root.TryGetProperty("current_price", out var cp) && cp.ValueKind != JsonValueKind.Null ? cp.GetDouble() : (double?)null;
                string pnlStr = "-";
                if (root.TryGetProperty("open_position", out var op) && op.ValueKind == JsonValueKind.Object)
                {
                    if (op.TryGetProperty("price", out var ep) && op.TryGetProperty("quantity", out var q))
                    {
                        var entry = ep.GetDouble();
                        var qty = q.GetDouble();
                        var side = op.GetProperty("side").GetString()?.ToUpperInvariant();
                        if (currentPrice.HasValue)
                        {
                            double pnl = side == "BUY" ? (currentPrice.Value - entry) * qty : (entry - currentPrice.Value) * qty;
                            pnlStr = pnl.ToString("0.####");
                        }
                        DrawEntryLine(entry);
                    }
                }

                _regimeText.Text = $"Régimen: {regime}";
                _priceText.Text = currentPrice.HasValue ? $"Precio: {currentPrice.Value:0.####}" : "Precio: -";
                _pnlText.Text = $"PnL: {pnlStr}";
            }
            catch (Exception ex)
            {
                Print($"Overlay error: {ex.Message}");
            }
        }

        private void DrawEntryLine(double entry)
        {
            if (_entryLine == null)
            {
                _entryLine = Chart.DrawHorizontalLine("entry", entry, Color.Gray, 1, LineStyle.Dots);
                _entryLine.IsInteractive = false;
            }
            else
            {
                _entryLine.Price = entry;
            }
        }

        private async Task PushSnapshotAsync()
        {
            try
            {
                var url = $"{ApiBaseUrl}/api/ctrader/push?token={Token}";
                var acc = new
                {
                    balance = Account.Balance,
                    equity = Account.Equity,
                    margin = Account.Margin,
                    freeMargin = Account.FreeMargin,
                    currency = Account.Currency,
                };
                var positions = new System.Collections.Generic.List<object>();
                foreach (var p in Positions)
                {
                    positions.Add(new
                    {
                        symbol = p.SymbolName,
                        side = p.TradeType.ToString(),
                        volume = p.VolumeInUnits,
                        entry_price = p.EntryPrice,
                        current_price = p.Symbol.Bid,
                        gross_profit = p.GrossProfit,
                        net_profit = p.NetProfit,
                        swap = p.Swap,
                        commission = p.Commissions,
                        label = p.Label,
                        id = p.Id,
                        created = p.EntryTime.ToString("o")
                    });
                }
                var payload = new { account = acc, positions = positions };
                var json = System.Text.Json.JsonSerializer.Serialize(payload);
                var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
                await _http.PostAsync(url, content);
            }
            catch (Exception ex)
            {
                Print($"Push error: {ex.Message}");
            }
        }
    }
}
using System;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using cAlgo;

/*
 ITBOT cTrader Overlay - Visualización LIVE
 -----------------------------------------
 - Consulta /api/ctrader/snapshot del panel web y muestra:
   * Régimen de mercado y confianza
   * Pares actuales
   * Posición abierta del símbolo (si existe)
   * Últimas operaciones en texto

 Requisitos:
 - Panel ITBOT Web accesible (puerto 8080 por defecto)
 - Token válido generado en /api/generate_token

 Parámetros recomendados:
 - ApiBaseUrl: http://<HOST>:8080
 - Token: (pegar el token)
 - Symbol: BTCUSDT (o el que corresponda)
 - PollSeconds: 5-10
*/

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.Internet)]
    public class ItbotLiveOverlay : Robot
    {
        [Parameter("API Base URL", DefaultValue = "http://127.0.0.1:8080", Group = "ITBOT API")] 
        public string ApiBaseUrl { get; set; }

        [Parameter("Token", DefaultValue = "", Group = "ITBOT API")]
        public string Token { get; set; }

        [Parameter("Symbol (e.g., BTCUSDT)", DefaultValue = "BTCUSDT", Group = "ITBOT API")]
        public string ItbotSymbol { get; set; }

        [Parameter("Poll Seconds", DefaultValue = 5, MinValue = 2, MaxValue = 60, Group = "ITBOT API")]
        public int PollSeconds { get; set; }

        private HttpClient _http;
        private string _lastSummary = "";

        protected override void OnStart()
        {
            _http = new HttpClient();
            Timer.Start(TimeSpan.FromSeconds(PollSeconds));
            Print("ITBOT Overlay iniciado. API={0}", ApiBaseUrl);
        }

        protected override void OnTimer()
        {
            _ = UpdateOverlay();
        }

        private async Task UpdateOverlay()
        {
            try
            {
                if (string.IsNullOrWhiteSpace(ApiBaseUrl) || string.IsNullOrWhiteSpace(Token))
                {
                    DrawText("Falta configurar ApiBaseUrl/Token");
                    return;
                }
                var url = $"{ApiBaseUrl.TrimEnd('/')}/api/ctrader/snapshot?token={Uri.EscapeDataString(Token)}&symbol={Uri.EscapeDataString(ItbotSymbol)}&limit=10";
                using var req = new HttpRequestMessage(HttpMethod.Get, url);
                using var resp = await _http.SendAsync(req);
                var json = await resp.Content.ReadAsStringAsync();

                var doc = JsonDocument.Parse(json);
                var root = doc.RootElement;
                if (!(root.TryGetProperty("success", out var ok) && ok.GetBoolean()))
                {
                    DrawText("Snapshot no disponible");
                    return;
                }

                string symbol = root.GetProperty("symbol").GetString();
                var regime = root.GetProperty("regime");
                string regimeName = regime.GetProperty("name").ValueKind == JsonValueKind.Null ? "-" : regime.GetProperty("name").GetString();
                string regimeConf = regime.GetProperty("confidence").ValueKind == JsonValueKind.Null ? "-" : (regime.GetProperty("confidence").GetDouble() * 100.0).ToString("0.0") + "%";
                int activeStrats = root.GetProperty("active_strategies_count").GetInt32();

                // Posición abierta
                string posText = "Sin posición";
                double posPrice = double.NaN;
                var openPosEl = root.GetProperty("open_position");
                if (openPosEl.ValueKind != JsonValueKind.Null)
                {
                    string side = openPosEl.GetProperty("side").GetString();
                    double price = openPosEl.GetProperty("price").GetDouble();
                    double qty = openPosEl.GetProperty("quantity").GetDouble();
                    string opid = openPosEl.GetProperty("operation_id").GetString();
                    posText = $"{side} {qty} @ {price:0.#####} (#{opid.Substring(0, Math.Min(opid.Length, 6))})";
                    posPrice = price;
                }

                // Últimas operaciones
                string tradesSummary = "";
                if (root.TryGetProperty("recent_trades", out var trades) && trades.ValueKind == JsonValueKind.Array)
                {
                    int i = 0;
                    foreach (var t in trades.EnumerateArray())
                    {
                        var side = t.GetProperty("side").GetString();
                        var price = t.GetProperty("price").GetDouble();
                        var status = t.GetProperty("status").GetString();
                        tradesSummary += $"{side}@{price:0.#####} {status}  ";
                        if (++i >= 5) break;
                    }
                }

                // Dibujar
                var sb = new System.Text.StringBuilder();
                sb.AppendLine($"ITBOT [{symbol}]");
                sb.AppendLine($"Régimen: {regimeName} ({regimeConf}) | Estrategias: {activeStrats}");
                sb.AppendLine($"Posición: {posText}");
                if (!string.IsNullOrWhiteSpace(tradesSummary))
                    sb.AppendLine($"Últimas: {tradesSummary}");

                var summary = sb.ToString();
                if (!string.Equals(summary, _lastSummary))
                {
                    DrawText(summary);
                    _lastSummary = summary;
                }

                // Línea horizontal para precio de entrada
                if (!double.IsNaN(posPrice) && posPrice > 0)
                {
                    Chart.DrawHorizontalLine("itbot_open_price", posPrice, Color.Orange, 1, LineStyle.Solid);
                }
                else
                {
                    Chart.RemoveObject("itbot_open_price");
                }
            }
            catch (Exception ex)
            {
                DrawText("Error: " + ex.Message);
            }
        }

        private void DrawText(string text)
        {
            Chart.DrawStaticText("itbot_overlay", text, VerticalAlignment.Top, HorizontalAlignment.Left, Color.LightGreen);
        }

        protected override void OnStop()
        {
            try
            {
                _http?.Dispose();
                Chart.RemoveObject("itbot_overlay");
                Chart.RemoveObject("itbot_open_price");
            }
            catch { }
        }
    }
}
