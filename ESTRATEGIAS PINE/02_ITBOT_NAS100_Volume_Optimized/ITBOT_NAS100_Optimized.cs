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

//This namespace holds Indicators in this folder and is required. Do not change it. 
namespace NinjaTrader.NinjaScript.Indicators
{
	/// <summary>
	/// ITBOT NAS100 & Indices Optimizer - Versión especializada para índices
	/// Convertido desde Pine Script a NinjaScript (C#)
	/// </summary>
	public class ITBOT_NAS100_Optimized : Indicator
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
				Description									= @"ITBOT NAS100 Optimizer - Indicador especializado para índices convertido desde Pine Script";
				Name										= "ITBOT NAS100 Optimized";
				Calculate									= Calculate.OnBarClose;
				IsOverlay									= true;
				DisplayInDataBox							= true;
				DrawOnPricePanel							= true;
				DrawHorizontalGridLines						= true;
				DrawVerticalGridLines						= true;
				PaintPriceMarkers							= true;
				ScaleJustification							= NinjaTrader.Gui.Chart.ScaleJustification.Right;
				//Disable this property if your indicator requires custom values that cumulate with each new market data event. 
				//See Help Guide for additional information.
				IsSuspendedWhileInactive					= true;
				
				// === PARÁMETROS OPTIMIZADOS PARA ÍNDICES ===
				FastLength									= 5;
				SlowLength									= 20;
				Threshold									= 0.08;
				VolumeSMALength								= 20;
				VolumeLookback								= 150;
				HeightFactor								= 0.15;
				ShowSignals									= true;
				ShowTrendBackground							= true;
				
				// === FILTROS OPTIMIZADOS PARA ÍNDICES ===
				RSILength									= 14;
				RSIOverbought								= 75.0;
				RSIOversold									= 25.0;
				VolumeMultiplier							= 1.8;
				MomentumLength								= 8;
				UseAdvancedFilters							= true;
				
				// === FILTROS ESPECÍFICOS PARA ÍNDICES ===
				SessionFilter								= true;
				SpreadFilter								= true;
				MaxSpreadPips								= 2.0;
				
				// Configuración de colores
				FastEMAColor								= Brushes.Blue;
				SlowEMAColor								= Brushes.Red;
				BuySignalColor								= Brushes.Lime;
				SellSignalColor								= Brushes.Red;
				TrendBullishColor							= Brushes.Green;
				TrendBearishColor							= Brushes.Red;
				TrendNeutralColor							= Brushes.Yellow;
			}
			else if (State == State.DataLoaded)
			{
				// Inicializar indicadores
				fastEMA = EMA(FastLength);
				slowEMA = EMA(SlowLength);
				rsi = RSI(RSILength, 1);
				volumeSMA = SMA(Volume, VolumeSMALength);
				atr = ATR(14);
				momentum = Momentum(MomentumLength);
			}
		}

		protected override void OnBarUpdate()
		{
			// Validación de datos mínimos
			if (CurrentBar < Math.Max(FastLength, SlowLength) || CurrentBar < RSILength)
				return;

			// === CÁLCULOS DE TENDENCIA ===
			double fastMA = fastEMA[0];
			double slowMA = slowEMA[0];
			
			// Validación de datos
			if (slowMA == 0 || double.IsNaN(fastMA) || double.IsNaN(slowMA))
				return;
				
			// Cálculo de diferencia porcentual
			double maDiffPercent = Math.Abs(slowMA) > 0 ? ((fastMA - slowMA) / slowMA) * 100 : 0;
			bool trendBullish = maDiffPercent > Threshold;
			bool trendBearish = maDiffPercent < -Threshold;
			bool trendNeutral = Math.Abs(maDiffPercent) <= Threshold;

			// === INDICADORES PARA FILTROS ===
			double currentRSI = rsi[0];
			double currentMomentum = momentum[0];
			double currentVolumeSMA = volumeSMA[0];
			double currentATR = atr[0];

			// === FILTROS ESPECÍFICOS PARA ÍNDICES ===
			bool isMarketSession = true; // Simplificado - en producción usar SessionIterator
			double currentSpread = High[0] - Low[0];
			bool spreadOk = !SpreadFilter || currentSpread <= MaxSpreadPips;

			// === FILTROS AVANZADOS ===
			bool volumeConfirmation = Volume[0] > (currentVolumeSMA * VolumeMultiplier);
			bool rsiBullishFilter = currentRSI < RSIOversold;
			bool rsiBearishFilter = currentRSI > RSIOverbought;
			bool momentumBullish = currentMomentum > 0;
			bool momentumBearish = currentMomentum < 0;
			bool priceConfirmationSell = Close[0] < Open[0];
			bool priceConfirmationBuy = Close[0] > Open[0];

			// Filtro de volatilidad mínima para índices
			bool minVolatility = CurrentBar >= 20 ? currentATR > (atr[20] * 0.8) : true;

			// === SEÑALES BASADAS EN CRUCES DE EMAs ===
			bool basicBuySignal = fastMA > slowMA && fastEMA[1] <= slowEMA[1]; // Crossover
			bool basicSellSignal = fastMA < slowMA && fastEMA[1] >= slowEMA[1]; // Crossunder

			// Señales finales - directas sin filtros complejos (como en Pine Script)
			bool buySignal = basicBuySignal;
			bool sellSignal = basicSellSignal;

			// === SEÑALES OPTIMIZADAS CON FILTROS (opcional) ===
			bool indicesBuySignal = UseAdvancedFilters ? 
				basicBuySignal && volumeConfirmation && rsiBullishFilter && 
				momentumBullish && priceConfirmationBuy && minVolatility && spreadOk :
				basicBuySignal;
				
			bool indicesSellSignal = UseAdvancedFilters ?
				basicSellSignal && volumeConfirmation && rsiBearishFilter && 
				momentumBearish && priceConfirmationSell && minVolatility && spreadOk :
				basicSellSignal;

			// === VISUALIZACIÓN ===
			// Background de tendencia
			if (ShowTrendBackground)
			{
				if (trendBullish)
					BackBrush = new SolidColorBrush(Color.FromArgb(20, Colors.Green.R, Colors.Green.G, Colors.Green.B));
				else if (trendBearish)
					BackBrush = new SolidColorBrush(Color.FromArgb(20, Colors.Red.R, Colors.Red.G, Colors.Red.B));
				else
					BackBrush = new SolidColorBrush(Color.FromArgb(15, Colors.Yellow.R, Colors.Yellow.G, Colors.Yellow.B));
			}

			// Señales de compra y venta
			if (ShowSignals)
			{
				if (buySignal)
				{
					Draw.TriangleUp(this, "BuySignal" + CurrentBar, false, 0, Low[0] - TickSize * 10, BuySignalColor);
					Draw.Text(this, "BuyText" + CurrentBar, "BUY", 0, Low[0] - TickSize * 20, BuySignalColor);
				}

				if (sellSignal)
				{
					Draw.TriangleDown(this, "SellSignal" + CurrentBar, false, 0, High[0] + TickSize * 10, SellSignalColor);
					Draw.Text(this, "SellText" + CurrentBar, "SELL", 0, High[0] + TickSize * 20, SellSignalColor);
				}

				// Señales básicas (más pequeñas)
				if (basicBuySignal && !buySignal)
				{
					Draw.Dot(this, "BasicBuy" + CurrentBar, false, 0, Low[0] - TickSize * 5, Brushes.Green);
				}

				if (basicSellSignal && !sellSignal)
				{
					Draw.Dot(this, "BasicSell" + CurrentBar, false, 0, High[0] + TickSize * 5, Brushes.Orange);
				}
			}

			// Actualizar variables anteriores
			previousTrendBullish = trendBullish;
			previousTrendBearish = trendBearish;
		}

		public override void OnRenderTargetChanged()
		{
			// Limpiar objetos de dibujo cuando cambie el target de renderizado
		}

		#region Properties
		// === PARÁMETROS OPTIMIZADOS PARA ÍNDICES ===
		[NinjaScriptProperty]
		[Range(1, 50)]
		[Display(Name="Fast MA Length", Description="Longitud de la EMA rápida", Order=1, GroupName="Parámetros")]
		public int FastLength { get; set; }

		[NinjaScriptProperty]
		[Range(1, 100)]
		[Display(Name="Slow MA Length", Description="Longitud de la EMA lenta", Order=2, GroupName="Parámetros")]
		public int SlowLength { get; set; }

		[NinjaScriptProperty]
		[Range(0.01, 1.0)]
		[Display(Name="Trend Threshold %", Description="Umbral de tendencia optimizado para índices", Order=3, GroupName="Parámetros")]
		public double Threshold { get; set; }

		[NinjaScriptProperty]
		[Range(5, 100)]
		[Display(Name="Volume SMA Length", Description="Longitud del SMA de volumen", Order=4, GroupName="Parámetros")]
		public int VolumeSMALength { get; set; }

		[NinjaScriptProperty]
		[Range(20, 2000)]
		[Display(Name="Volume Lookback", Description="Ventana de volumen", Order=5, GroupName="Parámetros")]
		public int VolumeLookback { get; set; }

		[NinjaScriptProperty]
		[Range(0.05, 0.3)]
		[Display(Name="Height Factor", Description="Factor de altura del volumen", Order=6, GroupName="Parámetros")]
		public double HeightFactor { get; set; }

		[NinjaScriptProperty]
		[Display(Name="Show Signals", Description="Mostrar señales de entrada", Order=7, GroupName="Visualización")]
		public bool ShowSignals { get; set; }

		[NinjaScriptProperty]
		[Display(Name="Show Trend Background", Description="Mostrar fondo de tendencia", Order=8, GroupName="Visualización")]
		public bool ShowTrendBackground { get; set; }

		// === FILTROS OPTIMIZADOS PARA ÍNDICES ===
		[NinjaScriptProperty]
		[Range(5, 50)]
		[Display(Name="RSI Length", Description="Longitud del RSI estándar para índices", Order=9, GroupName="Filtros")]
		public int RSILength { get; set; }

		[NinjaScriptProperty]
		[Range(60.0, 90.0)]
		[Display(Name="RSI Overbought", Description="RSI sobrecomprado (conservador)", Order=10, GroupName="Filtros")]
		public double RSIOverbought { get; set; }

		[NinjaScriptProperty]
		[Range(10.0, 40.0)]
		[Display(Name="RSI Oversold", Description="RSI sobrevendido (conservador)", Order=11, GroupName="Filtros")]
		public double RSIOversold { get; set; }

		[NinjaScriptProperty]
		[Range(1.0, 3.0)]
		[Display(Name="Volume Multiplier", Description="Confirmación de volumen (moderado)", Order=12, GroupName="Filtros")]
		public double VolumeMultiplier { get; set; }

		[NinjaScriptProperty]
		[Range(5, 20)]
		[Display(Name="Momentum Length", Description="Longitud del momentum (balanceado)", Order=13, GroupName="Filtros")]
		public int MomentumLength { get; set; }

		[NinjaScriptProperty]
		[Display(Name="Use Advanced Filters", Description="Usar filtros avanzados", Order=14, GroupName="Filtros")]
		public bool UseAdvancedFilters { get; set; }

		// === FILTROS ESPECÍFICOS PARA ÍNDICES ===
		[NinjaScriptProperty]
		[Display(Name="Session Filter", Description="Habilitar filtro de sesión (horarios de mercado)", Order=15, GroupName="Filtros Específicos")]
		public bool SessionFilter { get; set; }

		[NinjaScriptProperty]
		[Display(Name="Spread Filter", Description="Habilitar filtro de spread", Order=16, GroupName="Filtros Específicos")]
		public bool SpreadFilter { get; set; }

		[NinjaScriptProperty]
		[Range(0.5, 10.0)]
		[Display(Name="Max Spread Pips", Description="Spread máximo (puntos)", Order=17, GroupName="Filtros Específicos")]
		public double MaxSpreadPips { get; set; }

		// === COLORES ===
		[NinjaScriptProperty]
		[XmlIgnore]
		[Display(Name="Fast EMA Color", Description="Color de la EMA rápida", Order=18, GroupName="Colores")]
		public Brush FastEMAColor { get; set; }

		[NinjaScriptProperty]
		[XmlIgnore]
		[Display(Name="Slow EMA Color", Description="Color de la EMA lenta", Order=19, GroupName="Colores")]
		public Brush SlowEMAColor { get; set; }

		[NinjaScriptProperty]
		[XmlIgnore]
		[Display(Name="Buy Signal Color", Description="Color de señal de compra", Order=20, GroupName="Colores")]
		public Brush BuySignalColor { get; set; }

		[NinjaScriptProperty]
		[XmlIgnore]
		[Display(Name="Sell Signal Color", Description="Color de señal de venta", Order=21, GroupName="Colores")]
		public Brush SellSignalColor { get; set; }

		[NinjaScriptProperty]
		[XmlIgnore]
		[Display(Name="Trend Bullish Color", Description="Color de tendencia alcista", Order=22, GroupName="Colores")]
		public Brush TrendBullishColor { get; set; }

		[NinjaScriptProperty]
		[XmlIgnore]
		[Display(Name="Trend Bearish Color", Description="Color de tendencia bajista", Order=23, GroupName="Colores")]
		public Brush TrendBearishColor { get; set; }

		[NinjaScriptProperty]
		[XmlIgnore]
		[Display(Name="Trend Neutral Color", Description="Color de tendencia neutral", Order=24, GroupName="Colores")]
		public Brush TrendNeutralColor { get; set; }

		// Serialización para XML
		[Browsable(false)]
		public string FastEMAColorSerializable
		{
			get { return Serialize.BrushToString(FastEMAColor); }
			set { FastEMAColor = Serialize.StringToBrush(value); }
		}

		[Browsable(false)]
		public string SlowEMAColorSerializable
		{
			get { return Serialize.BrushToString(SlowEMAColor); }
			set { SlowEMAColor = Serialize.StringToBrush(value); }
		}

		[Browsable(false)]
		public string BuySignalColorSerializable
		{
			get { return Serialize.BrushToString(BuySignalColor); }
			set { BuySignalColor = Serialize.StringToBrush(value); }
		}

		[Browsable(false)]
		public string SellSignalColorSerializable
		{
			get { return Serialize.BrushToString(SellSignalColor); }
			set { SellSignalColor = Serialize.StringToBrush(value); }
		}

		[Browsable(false)]
		public string TrendBullishColorSerializable
		{
			get { return Serialize.BrushToString(TrendBullishColor); }
			set { TrendBullishColor = Serialize.StringToBrush(value); }
		}

		[Browsable(false)]
		public string TrendBearishColorSerializable
		{
			get { return Serialize.BrushToString(TrendBearishColor); }
			set { TrendBearishColor = Serialize.StringToBrush(value); }
		}

		[Browsable(false)]
		public string TrendNeutralColorSerializable
		{
			get { return Serialize.BrushToString(TrendNeutralColor); }
			set { TrendNeutralColor = Serialize.StringToBrush(value); }
		}
		#endregion
	}
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private ITBOT_NAS100_Optimized[] cacheITBOT_NAS100_Optimized;
		public ITBOT_NAS100_Optimized ITBOT_NAS100_Optimized(int fastLength, int slowLength, double threshold, int volumeSMALength, int volumeLookback, double heightFactor, bool showSignals, bool showTrendBackground, int rSILength, double rSIOverbought, double rSIOversold, double volumeMultiplier, int momentumLength, bool useAdvancedFilters, bool sessionFilter, bool spreadFilter, double maxSpreadPips)
		{
			return ITBOT_NAS100_Optimized(Input, fastLength, slowLength, threshold, volumeSMALength, volumeLookback, heightFactor, showSignals, showTrendBackground, rSILength, rSIOverbought, rSIOversold, volumeMultiplier, momentumLength, useAdvancedFilters, sessionFilter, spreadFilter, maxSpreadPips);
		}

		public ITBOT_NAS100_Optimized ITBOT_NAS100_Optimized(ISeries<double> input, int fastLength, int slowLength, double threshold, int volumeSMALength, int volumeLookback, double heightFactor, bool showSignals, bool showTrendBackground, int rSILength, double rSIOverbought, double rSIOversold, double volumeMultiplier, int momentumLength, bool useAdvancedFilters, bool sessionFilter, bool spreadFilter, double maxSpreadPips)
		{
			if (cacheITBOT_NAS100_Optimized != null)
				for (int idx = 0; idx < cacheITBOT_NAS100_Optimized.Length; idx++)
					if (cacheITBOT_NAS100_Optimized[idx] != null && cacheITBOT_NAS100_Optimized[idx].FastLength == fastLength && cacheITBOT_NAS100_Optimized[idx].SlowLength == slowLength && cacheITBOT_NAS100_Optimized[idx].Threshold == threshold && cacheITBOT_NAS100_Optimized[idx].VolumeSMALength == volumeSMALength && cacheITBOT_NAS100_Optimized[idx].VolumeLookback == volumeLookback && cacheITBOT_NAS100_Optimized[idx].HeightFactor == heightFactor && cacheITBOT_NAS100_Optimized[idx].ShowSignals == showSignals && cacheITBOT_NAS100_Optimized[idx].ShowTrendBackground == showTrendBackground && cacheITBOT_NAS100_Optimized[idx].RSILength == rSILength && cacheITBOT_NAS100_Optimized[idx].RSIOverbought == rSIOverbought && cacheITBOT_NAS100_Optimized[idx].RSIOversold == rSIOversold && cacheITBOT_NAS100_Optimized[idx].VolumeMultiplier == volumeMultiplier && cacheITBOT_NAS100_Optimized[idx].MomentumLength == momentumLength && cacheITBOT_NAS100_Optimized[idx].UseAdvancedFilters == useAdvancedFilters && cacheITBOT_NAS100_Optimized[idx].SessionFilter == sessionFilter && cacheITBOT_NAS100_Optimized[idx].SpreadFilter == spreadFilter && cacheITBOT_NAS100_Optimized[idx].MaxSpreadPips == maxSpreadPips && cacheITBOT_NAS100_Optimized[idx].EqualsInput(input))
						return cacheITBOT_NAS100_Optimized[idx];
			return CacheIndicator<ITBOT_NAS100_Optimized>(new ITBOT_NAS100_Optimized(){ FastLength = fastLength, SlowLength = slowLength, Threshold = threshold, VolumeSMALength = volumeSMALength, VolumeLookback = volumeLookback, HeightFactor = heightFactor, ShowSignals = showSignals, ShowTrendBackground = showTrendBackground, RSILength = rSILength, RSIOverbought = rSIOverbought, RSIOversold = rSIOversold, VolumeMultiplier = volumeMultiplier, MomentumLength = momentumLength, UseAdvancedFilters = useAdvancedFilters, SessionFilter = sessionFilter, SpreadFilter = spreadFilter, MaxSpreadPips = maxSpreadPips }, input, ref cacheITBOT_NAS100_Optimized);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.ITBOT_NAS100_Optimized ITBOT_NAS100_Optimized(int fastLength, int slowLength, double threshold, int volumeSMALength, int volumeLookback, double heightFactor, bool showSignals, bool showTrendBackground, int rSILength, double rSIOverbought, double rSIOversold, double volumeMultiplier, int momentumLength, bool useAdvancedFilters, bool sessionFilter, bool spreadFilter, double maxSpreadPips)
		{
			return indicator.ITBOT_NAS100_Optimized(Input, fastLength, slowLength, threshold, volumeSMALength, volumeLookback, heightFactor, showSignals, showTrendBackground, rSILength, rSIOverbought, rSIOversold, volumeMultiplier, momentumLength, useAdvancedFilters, sessionFilter, spreadFilter, maxSpreadPips);
		}

		public Indicators.ITBOT_NAS100_Optimized ITBOT_NAS100_Optimized(ISeries<double> input , int fastLength, int slowLength, double threshold, int volumeSMALength, int volumeLookback, double heightFactor, bool showSignals, bool showTrendBackground, int rSILength, double rSIOverbought, double rSIOversold, double volumeMultiplier, int momentumLength, bool useAdvancedFilters, bool sessionFilter, bool spreadFilter, double maxSpreadPips)
		{
			return indicator.ITBOT_NAS100_Optimized(input, fastLength, slowLength, threshold, volumeSMALength, volumeLookback, heightFactor, showSignals, showTrendBackground, rSILength, rSIOverbought, rSIOversold, volumeMultiplier, momentumLength, useAdvancedFilters, sessionFilter, spreadFilter, maxSpreadPips);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.ITBOT_NAS100_Optimized ITBOT_NAS100_Optimized(int fastLength, int slowLength, double threshold, int volumeSMALength, int volumeLookback, double heightFactor, bool showSignals, bool showTrendBackground, int rSILength, double rSIOverbought, double rSIOversold, double volumeMultiplier, int momentumLength, bool useAdvancedFilters, bool sessionFilter, bool spreadFilter, double maxSpreadPips)
		{
			return indicator.ITBOT_NAS100_Optimized(Input, fastLength, slowLength, threshold, volumeSMALength, volumeLookback, heightFactor, showSignals, showTrendBackground, rSILength, rSIOverbought, rSIOversold, volumeMultiplier, momentumLength, useAdvancedFilters, sessionFilter, spreadFilter, maxSpreadPips);
		}

		public Indicators.ITBOT_NAS100_Optimized ITBOT_NAS100_Optimized(ISeries<double> input , int fastLength, int slowLength, double threshold, int volumeSMALength, int volumeLookback, double heightFactor, bool showSignals, bool showTrendBackground, int rSILength, double rSIOverbought, double rSIOversold, double volumeMultiplier, int momentumLength, bool useAdvancedFilters, bool sessionFilter, bool spreadFilter, double maxSpreadPips)
		{
			return indicator.ITBOT_NAS100_Optimized(input, fastLength, slowLength, threshold, volumeSMALength, volumeLookback, heightFactor, showSignals, showTrendBackground, rSILength, rSIOverbought, rSIOversold, volumeMultiplier, momentumLength, useAdvancedFilters, sessionFilter, spreadFilter, maxSpreadPips);
		}
	}
}

#endregion