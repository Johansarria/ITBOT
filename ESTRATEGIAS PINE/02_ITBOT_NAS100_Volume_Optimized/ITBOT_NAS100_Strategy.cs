#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

//This namespace holds Strategies in this folder and is required. Do not change it. 
namespace NinjaTrader.NinjaScript.Strategies
{
	/// <summary>
	/// ITBOT NAS100 Strategy - Estrategia automatizada para índices
	/// Convertido desde Pine Script a NinjaScript Strategy
	/// </summary>
	public class ITBOT_NAS100_Strategy : Strategy
	{
		#region Variables
		private EMA fastEMA;
		private EMA slowEMA;
		private RSI rsi;
		private SMA volumeSMA;
		private ATR atr;
		private Momentum momentum;
		
		private bool previousTrendBullish = false;
		private bool previousTrendBearish = false;
		#endregion

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = @"ITBOT NAS100 Strategy - Estrategia automatizada para índices convertida desde Pine Script";
				Name = "ITBOT NAS100 Strategy";
				Calculate = Calculate.OnBarClose;
				EntriesPerDirection = 1;
				EntryHandling = EntryHandling.AllEntries;
				IsExitOnSessionCloseStrategy = true;
				ExitOnSessionCloseSeconds = 30;
				IsFillLimitOnTouch = false;
				MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
				OrderFillResolution = OrderFillResolution.Standard;
				Slippage = 0;
				StartBehavior = StartBehavior.WaitUntilFlat;
				TimeInForce = TimeInForce.Gtc;
				TraceOrders = false;
				RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
				StopTargetHandling = StopTargetHandling.PerEntryExecution;
				BarsRequiredToTrade = 20;
				IsInstantiatedOnEachOptimizationIteration = true;
				
				// === PARÁMETROS OPTIMIZADOS PARA ÍNDICES ===
				FastEMAPeriod = 5;
				SlowEMAPeriod = 20;
				RSIPeriod = 14;
				VolumePeriod = 20;
				ATRPeriod = 14;
				MomentumPeriod = 10;
				
				// === FILTROS CONSERVADORES PARA ÍNDICES ===
				RSIUpperThreshold = 75;
				RSILowerThreshold = 25;
				VolumeMultiplier = 1.8;
				MinMomentumThreshold = 0.5;
				MinSpreadFilter = 2.0;
				MinVolatilityATR = 0.3;
				
				// === GESTIÓN DE RIESGO ===
				StopLossATRMultiplier = 2.0;
				TakeProfitATRMultiplier = 3.0;
				RiskPercentage = 1.0;
				
				// === FILTROS DE SESIÓN ===
				EnableSessionFilter = true;
				SessionStartHour = 9;
				SessionStartMinute = 30;
				SessionEndHour = 16;
				SessionEndMinute = 0;
			}
			else if (State == State.DataLoaded)
			{
				fastEMA = EMA(FastEMAPeriod);
				slowEMA = EMA(SlowEMAPeriod);
				rsi = RSI(RSIPeriod, 3);
				volumeSMA = SMA(Volume, VolumePeriod);
				atr = ATR(ATRPeriod);
				momentum = Momentum(MomentumPeriod);
			}
		}

		protected override void OnBarUpdate()
		{
			if (BarsInProgress != 0 || CurrentBars[0] < Math.Max(SlowEMAPeriod, RSIPeriod))
				return;

			// === CÁLCULOS DE INDICADORES ===
			double fastEMAValue = fastEMA[0];
			double slowEMAValue = slowEMA[0];
			double rsiValue = rsi[0];
			double volumeAvg = volumeSMA[0];
			double atrValue = atr[0];
			double momentumValue = momentum[0];
			
			// === FILTROS DE SESIÓN ===
			bool inSession = true;
			if (EnableSessionFilter)
			{
				TimeSpan currentTime = Time[0].TimeOfDay;
				TimeSpan sessionStart = new TimeSpan(SessionStartHour, SessionStartMinute, 0);
				TimeSpan sessionEnd = new TimeSpan(SessionEndHour, SessionEndMinute, 0);
				inSession = currentTime >= sessionStart && currentTime <= sessionEnd;
			}
			
			// === CONDICIONES DE ENTRADA ===
			bool emaCrossUp = fastEMAValue > slowEMAValue && fastEMA[1] <= slowEMA[1];
			bool emaCrossDown = fastEMAValue < slowEMAValue && fastEMA[1] >= slowEMA[1];
			
			// === FILTROS AVANZADOS ===
			bool rsiFilter = rsiValue > RSILowerThreshold && rsiValue < RSIUpperThreshold;
			bool volumeFilter = Volume[0] > (volumeAvg * VolumeMultiplier);
			bool momentumFilter = Math.Abs(momentumValue) > MinMomentumThreshold;
			bool volatilityFilter = atrValue > MinVolatilityATR;
			bool spreadFilter = (High[0] - Low[0]) > (MinSpreadFilter * TickSize);
			
			// === SEÑALES DE COMPRA ===
			bool buySignal = emaCrossUp && 
							rsiFilter && 
							volumeFilter && 
							momentumFilter && 
							volatilityFilter && 
							spreadFilter && 
							inSession;
			
			// === SEÑALES DE VENTA ===
			bool sellSignal = emaCrossDown && 
							 rsiFilter && 
							 volumeFilter && 
							 momentumFilter && 
							 volatilityFilter && 
							 spreadFilter && 
							 inSession;
			
			// === EJECUCIÓN DE ÓRDENES ===
			if (buySignal && Position.MarketPosition == MarketPosition.Flat)
			{
				double stopLoss = Close[0] - (atrValue * StopLossATRMultiplier);
				double takeProfit = Close[0] + (atrValue * TakeProfitATRMultiplier);
				
				EnterLong("ITBOT_Long");
				SetStopLoss("ITBOT_Long", CalculationMode.Price, stopLoss, false);
				SetProfitTarget("ITBOT_Long", CalculationMode.Price, takeProfit);
			}
			
			if (sellSignal && Position.MarketPosition == MarketPosition.Flat)
			{
				double stopLoss = Close[0] + (atrValue * StopLossATRMultiplier);
				double takeProfit = Close[0] - (atrValue * TakeProfitATRMultiplier);
				
				EnterShort("ITBOT_Short");
				SetStopLoss("ITBOT_Short", CalculationMode.Price, stopLoss, false);
				SetProfitTarget("ITBOT_Short", CalculationMode.Price, takeProfit);
			}
		}

		#region Properties
		// === PARÁMETROS EMA ===
		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name="Fast EMA Period", Description="Período de la EMA rápida", Order=1, GroupName="01. EMA Settings")]
		public int FastEMAPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name="Slow EMA Period", Description="Período de la EMA lenta", Order=2, GroupName="01. EMA Settings")]
		public int SlowEMAPeriod { get; set; }

		// === PARÁMETROS RSI ===
		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name="RSI Period", Description="Período del RSI", Order=1, GroupName="02. RSI Settings")]
		public int RSIPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(50, 100)]
		[Display(Name="RSI Upper Threshold", Description="Umbral superior del RSI", Order=2, GroupName="02. RSI Settings")]
		public double RSIUpperThreshold { get; set; }

		[NinjaScriptProperty]
		[Range(0, 50)]
		[Display(Name="RSI Lower Threshold", Description="Umbral inferior del RSI", Order=3, GroupName="02. RSI Settings")]
		public double RSILowerThreshold { get; set; }

		// === PARÁMETROS DE VOLUMEN ===
		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name="Volume Period", Description="Período para promedio de volumen", Order=1, GroupName="03. Volume Settings")]
		public int VolumePeriod { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 5.0)]
		[Display(Name="Volume Multiplier", Description="Multiplicador de volumen", Order=2, GroupName="03. Volume Settings")]
		public double VolumeMultiplier { get; set; }

		// === PARÁMETROS ATR ===
		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name="ATR Period", Description="Período del ATR", Order=1, GroupName="04. ATR Settings")]
		public int ATRPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 1.0)]
		[Display(Name="Min Volatility ATR", Description="Volatilidad mínima ATR", Order=2, GroupName="04. ATR Settings")]
		public double MinVolatilityATR { get; set; }

		// === PARÁMETROS MOMENTUM ===
		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name="Momentum Period", Description="Período del Momentum", Order=1, GroupName="05. Momentum Settings")]
		public int MomentumPeriod { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 2.0)]
		[Display(Name="Min Momentum Threshold", Description="Umbral mínimo de momentum", Order=2, GroupName="05. Momentum Settings")]
		public double MinMomentumThreshold { get; set; }

		// === FILTROS ADICIONALES ===
		[NinjaScriptProperty]
		[Range(1.0, 10.0)]
		[Display(Name="Min Spread Filter", Description="Filtro mínimo de spread", Order=1, GroupName="06. Additional Filters")]
		public double MinSpreadFilter { get; set; }

		// === GESTIÓN DE RIESGO ===
		[NinjaScriptProperty]
		[Range(1.0, 5.0)]
		[Display(Name="Stop Loss ATR Multiplier", Description="Multiplicador ATR para Stop Loss", Order=1, GroupName="07. Risk Management")]
		public double StopLossATRMultiplier { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 10.0)]
		[Display(Name="Take Profit ATR Multiplier", Description="Multiplicador ATR para Take Profit", Order=2, GroupName="07. Risk Management")]
		public double TakeProfitATRMultiplier { get; set; }

		[NinjaScriptProperty]
		[Range(0.1, 5.0)]
		[Display(Name="Risk Percentage", Description="Porcentaje de riesgo por trade", Order=3, GroupName="07. Risk Management")]
		public double RiskPercentage { get; set; }

		// === FILTROS DE SESIÓN ===
		[NinjaScriptProperty]
		[Display(Name="Enable Session Filter", Description="Activar filtro de sesión", Order=1, GroupName="08. Session Filter")]
		public bool EnableSessionFilter { get; set; }

		[NinjaScriptProperty]
		[Range(0, 23)]
		[Display(Name="Session Start Hour", Description="Hora de inicio de sesión", Order=2, GroupName="08. Session Filter")]
		public int SessionStartHour { get; set; }

		[NinjaScriptProperty]
		[Range(0, 59)]
		[Display(Name="Session Start Minute", Description="Minuto de inicio de sesión", Order=3, GroupName="08. Session Filter")]
		public int SessionStartMinute { get; set; }

		[NinjaScriptProperty]
		[Range(0, 23)]
		[Display(Name="Session End Hour", Description="Hora de fin de sesión", Order=4, GroupName="08. Session Filter")]
		public int SessionEndHour { get; set; }

		[NinjaScriptProperty]
		[Range(0, 59)]
		[Display(Name="Session End Minute", Description="Minuto de fin de sesión", Order=5, GroupName="08. Session Filter")]
		public int SessionEndMinute { get; set; }
		#endregion
	}
}