#!/usr/bin/env python3
"""
Integración completa de PatchTST con SICAR
Ejecuta el pipeline completo: datos → entrenamiento → predicción → señales → visualización
"""

import os
import sys
import argparse
from typing import List, Optional
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Agregar directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module_patchtst_integration import PatchTSTIntegration
from patchtst_visualization import PatchTSTVisualizer
from crypto_data_loader import CryptoDataLoader
from module_xai import generate_cognitive_report, generate_multi_ai_comparison_report, save_cognitive_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_complete_pipeline(retrain_models: bool = True, symbols: Optional[List[str]] = None):
    """
    Ejecutar el pipeline completo de PatchTST-SICAR
    """
    print("🚀 Ejecutando Pipeline Completo PatchTST-SICAR")
    print("=" * 60)
    
    try:
        # 1. Configurar parámetros
        config = {
            'symbols': symbols or ['BTC-USD', 'ETH-USD', 'LINK-USD'],
            'timeframe': '1h',
            'prediction_horizon': 96,
            'retrain': retrain_models
        }
        
        # 2. Inicializar integración
        print("📊 Inicializando integración PatchTST...")
        patchtst_integrations = {s: PatchTSTIntegration(symbol=s) for s in config['symbols']}
        
        # 3. Entrenar o cargar modelo
        for sym, integ in patchtst_integrations.items():
            if config['retrain']:
                print(f"🧠 Entrenando modelo PatchTST ({sym})...")
                success = integ._train_model()
                if not success:
                    print(f"❌ Error en entrenamiento {sym}")
                    return False
        
        # 4. Generar predicciones
        print("🔮 Generando predicciones...")
        
        asset_results = {}
        for sym in config['symbols']:
            dl = CryptoDataLoader(sym, config['timeframe'])
            data = dl.get_binance_data(limit=200)
            if data.empty:
                print(f"❌ No se pudieron obtener datos para {sym}")
                return False
            price = data['close'].iloc[-1]
            print(f"💰 {sym} Precio actual: ${price:.2f}")
            res = patchtst_integrations[sym].generate_prediction_signal(data, price)
            if 'error' in res:
                print(f"❌ Error en predicción {sym}: {res['error']}")
                return False
            print(f"📈 Señal generada {sym}: {res}")
            asset_results[sym] = {'data': data, 'price': price, 'signal': res}
        
        # 5. Análisis de riesgo
        print("⚠️ Realizando análisis de riesgo...")
        asset_risks = {}
        for sym in config['symbols']:
            ra = patchtst_integrations[sym].analyze_risk(asset_results[sym]['data'], asset_results[sym]['price'])
            print(f"📊 {sym} Análisis de riesgo: {json.dumps(ra, indent=2, default=str)}")
            asset_risks[sym] = ra

        primary = config['symbols'][0]
        xai_factors = {
            'confidence': asset_results[primary]['signal'].get('confidence', 0.0),
            'signal_strength': asset_results[primary]['signal'].get('analysis', {}).get('strength', 0.0),
            'volatility': asset_risks[primary].get('price_volatility', 0.0),
            'momentum': asset_results[primary]['signal'].get('analysis', {}).get('strength', 0.0)
        }

        primary_causal_factors = [
            'tendencia',
            'volatilidad',
            'soporte_resistencia'
        ]

        market_regime = 'Lateral/Consolidación'
        if asset_results[primary]['signal'].get('signal') == 'BUY':
            market_regime = 'Tendencia Alcista'
        elif asset_results[primary]['signal'].get('signal') == 'SELL':
            market_regime = 'Tendencia Bajista'

        additional_context = {
            'price': asset_results[primary]['price'],
            'predicted_price_96h': asset_results[primary]['signal'].get('predicted_price_96h', 0.0),
            'price_change_pct': asset_results[primary]['signal'].get('price_change_pct', 0.0),
            'risk_level': asset_risks[primary].get('risk_metrics', {}).get('risk_level', 'UNKNOWN'),
            'support_distance_pct': asset_risks[primary].get('support_resistance', {}).get('support_distance_pct', 0.0),
            'resistance_distance_pct': asset_risks[primary].get('support_resistance', {}).get('resistance_distance_pct', 0.0)
        }

        print("🧠 Generando reporte XAI con LLMs...")
        xai_report = generate_cognitive_report(
            decision=asset_results[primary]['signal'].get('signal', 'HOLD'),
            strategy='momentum',
            market_regime=market_regime,
            xai_factors=xai_factors,
            primary_causal_factors=primary_causal_factors,
            additional_context=additional_context
        )

        report_path = save_cognitive_report(xai_report, 'reporte_dinamico_patchtst.txt')

        print("🤖 Generando comparación multi-IA...")
        comparison = generate_multi_ai_comparison_report(
            decision=asset_results[primary]['signal'].get('signal', 'HOLD'),
            strategy='momentum',
            market_regime=market_regime,
            xai_factors=xai_factors,
            primary_causal_factors=primary_causal_factors,
            additional_context=additional_context
        )

        consensus = comparison.get('consensus_analysis', {})
        individual_reports = comparison.get('individual_reports', {})
        comparison_text = (
            f"Recomendación de Consenso: {consensus.get('consensus_recommendation', 'N/A')}\n"
            f"Nivel de Confianza: {consensus.get('confidence_level', 'N/A')}\n"
            f"Score de Consenso: {consensus.get('consensus_score', 0):.2f}\n"
            f"Sentimiento Promedio: {consensus.get('average_sentiment', 0):.2f}\n"
        )
        comparison_path = save_cognitive_report(
            "=== CONSENSO MULTI-IA ===\n\n" + comparison_text + "\n" + json.dumps(individual_reports, indent=2, ensure_ascii=False),
            'comparacion_multi_ia_patchtst.txt'
        )
        
        # 6. Crear visualizaciones
        print("🎨 Creando visualizaciones...")
        visualizer = PatchTSTVisualizer()
        
        # Preparar datos para visualización
        recent_data_btc = asset_results.get('BTC-USD', {}).get('data', pd.DataFrame()).tail(100)
        recent_data_eth = asset_results.get('ETH-USD', {}).get('data', pd.DataFrame()).tail(100)
        
        # Crear predicciones para gráfico usando volatilidad como CI
        pred_hours = 24
        base_btc = asset_results.get('BTC-USD', {}).get('price', None)
        target_btc = asset_results.get('BTC-USD', {}).get('signal', {}).get('predicted_price_96h', base_btc)
        pred_btc_24 = np.linspace(base_btc, target_btc, pred_hours)
        q_btc = asset_results['BTC-USD']['signal'].get('quantiles', {})
        if q_btc:
            band_btc = abs(q_btc.get('p90', target_btc) - q_btc.get('p10', target_btc)) / 2
            conf_intervals = np.full(pred_hours, band_btc)
        else:
            recent_returns = recent_data_btc['close'].pct_change().dropna()
            vol = recent_returns.std()
            conf_intervals = np.full(pred_hours, vol * base_btc)

        base_eth = asset_results.get('ETH-USD', {}).get('price', None)
        target_eth = asset_results.get('ETH-USD', {}).get('signal', {}).get('predicted_price_96h', base_eth)
        pred_eth_24 = np.linspace(base_eth, target_eth, pred_hours)
        q_eth = asset_results['ETH-USD']['signal'].get('quantiles', {})
        band_eth = abs(q_eth.get('p90', target_eth) - q_eth.get('p10', target_eth)) / 2 if q_eth else (recent_data_eth['close'].pct_change().std() * base_eth)
        
        # Crear gráficos
        pred_fig = None
        if isinstance(recent_data_btc, pd.DataFrame) and not recent_data_btc.empty and base_btc is not None:
            pred_fig = visualizer.create_prediction_chart(
                recent_data_btc, pred_btc_24, conf_intervals,
                title=f"Predicción PatchTST - BTC-USD"
            )
        
        # Crear señales de ejemplo
        signals_btc = []
        signals_eth = []
        sr_btc = asset_results.get('BTC-USD', {}).get('signal', {})
        sr_eth = asset_results.get('ETH-USD', {}).get('signal', {})
        now_btc = recent_data_btc['timestamp'].iloc[-1] if isinstance(recent_data_btc, pd.DataFrame) and not recent_data_btc.empty else None
        now_eth = recent_data_eth['timestamp'].iloc[-1] if isinstance(recent_data_eth, pd.DataFrame) and not recent_data_eth.empty else None
        signals_btc.append({
            'timestamp': now_btc,
            'price': recent_data_btc['close'].iloc[-1],
            'signal': 'BUY' if sr_btc['signal'] == 'BUY' else 'SELL',
            'confidence': sr_btc['confidence']
        })
        signals_eth.append({
            'timestamp': now_eth,
            'price': recent_data_eth['close'].iloc[-1],
            'signal': 'BUY' if sr_eth['signal'] == 'BUY' else 'SELL',
            'confidence': sr_eth['confidence']
        })
        signals_fig = None
        if isinstance(recent_data_btc, pd.DataFrame) and not recent_data_btc.empty and isinstance(recent_data_eth, pd.DataFrame) and not recent_data_eth.empty:
            signals_fig = visualizer.create_multi_asset_realtime_chart(
                recent_data_btc, recent_data_eth, signals_btc, signals_eth,
                title="BTC vs ETH - Tiempo Real y Señales"
            )
        
        # Crear dashboard de riesgo
        risk_fig = visualizer.create_risk_analysis_dashboard(asset_risks[primary])
        
        # 7. Guardar resultados
        print("💾 Guardando resultados...")
        
        # Crear directorio de resultados
        os.makedirs('results', exist_ok=True)
        
        # Guardar predicciones multi-activo (timestamp basado en BTC-USD si existe)
        if isinstance(recent_data_btc, pd.DataFrame) and not recent_data_btc.empty:
            ts24 = pd.date_range(
                start=recent_data_btc['timestamp'].iloc[-1] + timedelta(hours=1),
                periods=pred_hours,
                freq='H'
            )
            ts96 = pd.date_range(
                start=recent_data_btc['timestamp'].iloc[-1] + timedelta(hours=1),
                periods=96,
                freq='H'
            )
            pred_df_24 = pd.DataFrame({ 'timestamp': ts24 })
            pred_df_96 = pd.DataFrame({ 'timestamp': ts96 })
            for sym in config['symbols']:
                base = asset_results[sym]['price']
                target = asset_results[sym]['signal'].get('predicted_price_96h', base)
                key = sym.split('-')[0]
                pred_df_24[f'{key}_pred_24h'] = np.linspace(base, target, pred_hours)
                pred_df_96[f'{key}_pred_96h'] = np.linspace(base, target, 96)
            preds_merged = pred_df_24.merge(pred_df_96, on='timestamp', how='outer')
            preds_merged.to_csv('results/predictions_24_96h.csv', index=False)
        # Guardar cuantiles y bandas para todos los símbolos
        quantiles = {}
        bands = {}
        for sym in config['symbols']:
            q = asset_results[sym]['signal'].get('quantiles', {})
            quantiles[sym] = q
            data = asset_results[sym]['data']
            base = asset_results[sym]['price']
            if q:
                band = abs(q.get('p90', base) - q.get('p10', base)) / 2
            else:
                ret = data['close'].pct_change().dropna()
                vol = ret.std() if not ret.empty else 0.0
                band = vol * base
            bands[sym] = float(band)
        quantiles['bands'] = bands
        with open('results/quantiles.json', 'w') as f:
            json.dump(quantiles, f, indent=2)
        
        # Guardar análisis de riesgo
        with open('results/risk_analysis.json', 'w') as f:
            json.dump(asset_risks[primary], f, indent=2, default=str)
        with open('results/risk_multi.json', 'w') as f:
            json.dump({ sym: asset_risks[sym] for sym in config['symbols'] }, f, indent=2, default=str)
        def _local_plan(sym):
            res = asset_results[sym]['signal']
            ra = asset_risks[sym]
            price = asset_results[sym]['price']
            rm = ra.get('risk_metrics', {})
            support = rm.get('support_level', price*0.98)
            resistance = rm.get('resistance_level', price*1.02)
            vol = max(0.005, ra.get('price_volatility', 0.02))
            entry = float(price)
            if res['signal']=='BUY':
                if resistance <= entry: resistance = entry*(1+vol)
                if support >= entry: support = entry*(1-vol)
                sl = min(support, entry*(1-vol))
                risk = max(1e-6, entry - sl)
                tp1 = max(entry + 1.0*risk, resistance)
                tp2 = entry + 1.5*risk
                tp3 = entry + 2.0*risk
                rr_tp1 = (tp1-entry)/risk; rr_tp2 = (tp2-entry)/risk; rr_tp3 = (tp3-entry)/risk
            else:
                if support >= entry: support = entry*(1-vol)
                if resistance <= entry: resistance = entry*(1+vol)
                sl = max(resistance, entry*(1+vol))
                risk = max(1e-6, sl - entry)
                tp1 = min(entry - 1.0*risk, support)
                tp2 = entry - 1.5*risk
                tp3 = entry - 2.0*risk
                rr_tp1 = (entry-tp1)/risk; rr_tp2 = (entry-tp2)/risk; rr_tp3 = (entry-tp3)/risk
            return {'entry':entry,'sl':float(sl),'tp1':float(tp1),'tp2':float(tp2),'tp3':float(tp3),'rr_tp1':float(rr_tp1),'rr_tp2':float(rr_tp2),'rr_tp3':float(rr_tp3)}
        def _gate(sym):
            sig = asset_results[sym]['signal']
            ra = asset_risks[sym]
            rm = ra.get('risk_metrics', {})
            rr_tp1 = _local_plan(sym).get('rr_tp1', 0)
            rr_ok = (sig.get('signal') in ['BUY','SELL']) and rr_tp1 >= 1.0
            var_ok = abs(rm.get('var_95',0)) <= 0.02
            conf_ok = sig.get('confidence',0) >= 0.6
            dist_ok = rm.get('support_distance_pct',0) >= 0.3 and rm.get('resistance_distance_pct',0) >= 0.3
            tech_ok = rr_ok and var_ok and conf_ok and dist_ok
            rec = str(consensus.get('consensus_recommendation','')).upper()
            fund_ok = (sig.get('signal')=='BUY' and 'BUY' in rec) or (sig.get('signal')=='SELL' and 'SELL' in rec)
            reasons = {
                'tech': [
                    f"RR TP1 {rr_tp1:.2f}R",
                    f"VaR 95% {rm.get('var_95',0):.2%}",
                    f"Confianza {sig.get('confidence',0):.0%}",
                    f"Distancia SR {rm.get('support_distance_pct',0):.2f}%/{rm.get('resistance_distance_pct',0):.2f}%"
                ],
                'fund': [
                    f"Consenso {consensus.get('consensus_recommendation','N/A')}",
                    f"Confianza {consensus.get('confidence_level','N/A')}"
                ]
            }
            return tech_ok and fund_ok, tech_ok, fund_ok, reasons
        trade_plan = { sym: _local_plan(sym) for sym in config['symbols'] }
        with open('results/trade_plan.json', 'w') as f:
            json.dump(trade_plan, f, indent=2)
        
        # Guardar gráficos
        figures = {
            'predicciones': pred_fig,
            'señales_multi_activos': signals_fig,
            'analisis_riesgo': risk_fig
        }
        
        # Plan de trade con entrada, SL y TPs por activo
        def _compute_trade_plan(sym: str):
            res = asset_results[sym]['signal']
            ra = asset_risks[sym]
            price = asset_results[sym]['price']
            rm = ra.get('risk_metrics', {})
            support = rm.get('support_level', price * 0.98)
            resistance = rm.get('resistance_level', price * 1.02)
            vol = max(0.005, ra.get('price_volatility', 0.02) / 2)
            if res['signal'] == 'BUY':
                entry = price
                sl = support * (1 - vol)
                risk = entry - sl
                tp1 = resistance
                tp2 = entry + 1.5 * risk
                tp3 = entry + 2.0 * risk
            else:
                entry = price
                sl = resistance * (1 + vol)
                risk = sl - entry
                tp1 = support
                tp2 = entry - 1.5 * risk
                tp3 = entry - 2.0 * risk
            return {
                'entry': float(entry),
                'sl': float(sl),
                'tp1': float(tp1),
                'tp2': float(tp2),
                'tp3': float(tp3)
            }

        extra_sections = {
            'reporte_xai': xai_report,
            'consenso_multi_ia': comparison_text,
            'plan_de_trade_primary': (
                f"Entrada: {trade_plan[primary]['entry']:.2f} | SL: {trade_plan[primary]['sl']:.2f} | "
                f"TP1: {trade_plan[primary]['tp1']:.2f} | TP2: {trade_plan[primary]['tp2']:.2f} | TP3: {trade_plan[primary]['tp3']:.2f}"
            )
        }
        
        visualizer.save_dashboard_html(figures, 'results/patchtst_dashboard.html', extra_sections)
        
        # 8. Resumen final
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE RESULTADOS PATCHTST-SICAR")
        print("=" * 60)
        print(f"🪙 Activos: {', '.join(config['symbols'])}")
        for sym in config['symbols']:
            sr = asset_results[sym]['signal']
            print(f"💰 {sym} Precio actual: ${asset_results[sym]['price']:.2f}")
            print(f"📈 {sym} Señal: {sr['signal']} | Confianza: {sr['confidence']:.2%}")
        rm = asset_risks[primary].get('risk_metrics', {})
        print(f"⚠️ VaR 95%: {rm.get('var_95', 0):.2%}")
        print(f"📊 Sharpe Ratio: {rm.get('sharpe_ratio', 0):.2f}")
        if now_btc is not None and isinstance(recent_data_btc, pd.DataFrame) and not recent_data_btc.empty and sr_btc:
            print(f"🔔 BTC {'Entrada' if sr_btc.get('signal')=='BUY' else 'Salida'} @ {now_btc} precio {recent_data_btc['close'].iloc[-1]:.2f}")
        if now_eth is not None and isinstance(recent_data_eth, pd.DataFrame) and not recent_data_eth.empty and sr_eth:
            print(f"🔔 ETH {'Entrada' if sr_eth.get('signal')=='BUY' else 'Salida'} @ {now_eth} precio {recent_data_eth['close'].iloc[-1]:.2f}")
        for sym in config['symbols']:
            tp = trade_plan[sym]
            print(f"📌 {sym} Entrada: {tp['entry']:.2f} | SL: {tp['sl']:.2f} | TP1: {tp['tp1']:.2f} ({tp['rr_tp1']:.2f}R) | TP2: {tp['tp2']:.2f} ({tp['rr_tp2']:.2f}R) | TP3: {tp['tp3']:.2f} ({tp['rr_tp3']:.2f}R)")
        print(f"📁 Archivos guardados:")
        print(f"   - Predicciones: results/predictions_24_96h.csv")
        print(f"   - Análisis riesgo: results/risk_analysis.json")
        print(f"   - Análisis riesgo multi: results/risk_multi.json")
        print(f"   - Dashboard: results/patchtst_dashboard.html")
        if report_path:
            print(f"   - Reporte XAI: {report_path}")
        if comparison_path:
            print(f"   - Consenso Multi-IA: {comparison_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
        sys.stderr.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    print("🎯 PatchTST-SICAR Integration System")
    print("=" * 60)
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='Ejecutar sin reentrenar (solo refresh de datos y señales)')
    parser.add_argument('--assets', type=str, help='Lista de activos separados por coma (ej: BTC-USD,ETH-USD,BNB-USD)')
    args = parser.parse_args()
    assets = None
    if args.assets:
        assets = [s.strip() for s in args.assets.split(',') if s.strip()]
    success = run_complete_pipeline(retrain_models=not args.quick, symbols=assets)
    
    if success:
        print("\n🎉 ¡Pipeline completado exitosamente!")
        print("🚀 El sistema PatchTST está listo para operar")
    else:
        print("\n❌ El pipeline falló. Revisa los logs para más detalles.")
        sys.exit(1)

if __name__ == '__main__':
    main()
