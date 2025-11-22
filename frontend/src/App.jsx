import React, { useEffect, useState, useMemo } from 'react'
import Plot from 'react-plotly.js'

// Agregar estilos CSS para animaciones
const GlobalStyles = () => (
  <style>{`
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    .spinning {
      animation: spin 1s linear infinite;
      display: inline-block;
    }
    .status-valid {
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
      color: white;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
    }
    .status-fakeout {
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      color: white;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
    }
    .status-pending {
      background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
      color: #333;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
    }
    .status-insufficient_data {
      background: #666;
      color: white;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
    }
  `}</style>
)

const API = 'http://localhost:4000/api'

function useFetch(url) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    if (!url) {
      setLoading(false)
      return
    }
    let mounted = true
    setLoading(true)
    fetch(url)
      .then(r => r.json())
      .then(d => { if (mounted) { setData(d); setLoading(false) } })
      .catch(() => setLoading(false))
    return () => { mounted = false }
  }, [url])
  return { data, loading }
}

function useFetchText(url) {
  const [data, setData] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    if (!url) {
      setLoading(false)
      return
    }
    let mounted = true
    setLoading(true)
    fetch(url)
      .then(r => r.text())
      .then(d => { if (mounted) { setData(d); setLoading(false) } })
      .catch(() => setLoading(false))
    return () => { mounted = false }
  }, [url])
  return { data, loading }
}

export default function App() {
  const [tick, setTick] = useState(0)
  const [asset, setAsset] = useState('BTC-USD')
  const [selectedAssets, setSelectedAssets] = useState(['BTC-USD','ETH-USD'])
  const [isLoading, setIsLoading] = useState(false)
  
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 15000)
    return () => clearInterval(id)
  }, [])

  // Declarar hooks después de definir las variables de estado
  const { data: riskMulti } = useFetch(`${API}/risk-multi?ts=${tick}`)
  const { data: preds } = useFetch(`${API}/predictions?ts=${tick}`)
  const { data: updated } = useFetch(`${API}/last-updated?ts=${tick}`)
  const { data: plan } = useFetch(`${API}/trade-plan?ts=${tick}`)
  const { data: quants } = useFetch(`${API}/quantiles?ts=${tick}`)
  const { data: macro } = useFetch(`${API}/macro?ts=${tick}`)
  const { data: top } = useFetch(`${API}/top-crypto?ts=${tick}`)
  
  // Usar hooks condicionales solo cuando asset esté definido
  const { data: xai } = useFetchText(asset ? `${API}/report-xai?symbol=${asset}&ts=${tick}` : '')
  const { data: consensus } = useFetchText(asset ? `${API}/consensus-xai?symbol=${asset}&ts=${tick}` : '')
  const { data: xaiSummary } = useFetch(asset ? `${API}/report-xai-summary?symbol=${asset}&ts=${tick}` : '')
  const { data: consensusSummary } = useFetch(asset ? `${API}/consensus-xai-summary?symbol=${asset}&ts=${tick}` : '')
  const { data: breakoutValidation } = useFetch(asset ? `${API}/breakout-validation?symbol=${asset}&ts=${tick}` : '')
  
  useEffect(() => {
    if (Array.isArray(selectedAssets) && selectedAssets.length) {
      setAsset(selectedAssets[0])
    }
  }, [selectedAssets])
  
  useEffect(() => {
    let cancelled = false
    async function runQuickForAsset() {
      if (!asset) return
      
      setIsLoading(true)
      try {
        console.log(`🔄 Iniciando análisis para ${asset}...`)
        const url = `${API}/run-pipeline?mode=quick`
        const response = await fetch(url, { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify({ assets: [asset] }) 
        })
        
        if (!response.ok) {
          if (response.status === 409) {
            // El pipeline ya está en ejecución, esperar a que termine
            console.log(`⏳ Pipeline ocupado, esperando...`)
            for (let i = 0; i < 120; i++) { // Esperar hasta 60 segundos
              if (cancelled) {
                console.log('❌ Análisis cancelado mientras esperaba')
                return
              }
              const statusResponse = await fetch(`${API}/run-status`).then(res => res.json()).catch(() => ({ status: 'error' }))
              
              if (statusResponse.status === 'done' || statusResponse.status === 'idle') {
                console.log(`✅ Pipeline liberado, continuando...`)
                // Intentar nuevamente
                const retryResponse = await fetch(url, { 
                  method: 'POST', 
                  headers: { 'Content-Type': 'application/json' }, 
                  body: JSON.stringify({ assets: [asset] }) 
                })
                if (!retryResponse.ok) {
                  throw new Error(`Error ${retryResponse.status}: ${retryResponse.statusText}`)
                }
                break
              }
              if (statusResponse.status === 'error') {
                throw new Error('Error en el pipeline anterior')
              }
              await new Promise(res => setTimeout(res, 500))
            }
          } else {
            throw new Error(`Error ${response.status}: ${response.statusText}`)
          }
        }
        
        console.log(`⏳ Esperando resultados para ${asset}...`)
        for (let i = 0; i < 60; i++) { // Reducido de 120 a 60 para mayor velocidad
          if (cancelled) {
            console.log('❌ Análisis cancelado')
            return
          }
          const r = await fetch(`${API}/run-status`).then(res => res.json()).catch(() => ({ status: 'error' }))
          if (r.status === 'done') {
            console.log(`✅ Análisis completado para ${asset}`)
            break
          }
          if (r.status === 'error') {
            throw new Error('Error en el análisis')
          }
          await new Promise(res => setTimeout(res, 500)) // Reducido de 1000ms a 500ms
        }
        
        if (!cancelled) {
          console.log(`🔄 Actualizando datos para ${asset}`)
          setTick(t => t + 1)
        }
      } catch (e) {
        console.error(`❌ Error analizando ${asset}:`, e)
        let errorMessage = `Error al analizar ${asset}: ${e.message}`
        if (e.message.includes('409')) {
          errorMessage = `El análisis de ${asset} no pudo iniciarse porque hay otro análisis en curso. Por favor, espera un momento y vuelve a intentarlo.`
        }
        alert(errorMessage)
      } finally {
        setIsLoading(false)
      }
    }
    
    if (asset) {
      runQuickForAsset()
    }
    return () => { cancelled = true }
  }, [asset])
  const [tf, setTf] = useState('1h')
  const [activeTab, setActiveTab] = useState('overview')
  const levels = asset && plan ? plan[asset] : null
  const predsArr = Array.isArray(preds) ? preds : []
  const assetKey = (asset||'').split('-')[0]
  const predsClean = predsArr.filter(p => p && p.timestamp)
  const shapes = levels ? [
    { type: 'line', xref: 'x', yref: 'y', x0: predsClean[0]?.timestamp, x1: predsClean.slice(-1)[0]?.timestamp, y0: levels.entry, y1: levels.entry, line: { color: 'yellow', width: 1 } },
    { type: 'line', xref: 'x', yref: 'y', x0: predsClean[0]?.timestamp, x1: predsClean.slice(-1)[0]?.timestamp, y0: levels.sl, y1: levels.sl, line: { color: 'red', width: 1 } },
    { type: 'line', xref: 'x', yref: 'y', x0: predsClean[0]?.timestamp, x1: predsClean.slice(-1)[0]?.timestamp, y0: levels.tp1, y1: levels.tp1, line: { color: 'green', width: 1 } },
    { type: 'line', xref: 'x', yref: 'y', x0: predsClean[0]?.timestamp, x1: predsClean.slice(-1)[0]?.timestamp, y0: levels.tp2, y1: levels.tp2, line: { color: 'green', width: 1, dash: 'dot' } },
    { type: 'line', xref: 'x', yref: 'y', x0: predsClean[0]?.timestamp, x1: predsClean.slice(-1)[0]?.timestamp, y0: levels.tp3, y1: levels.tp3, line: { color: 'green', width: 1, dash: 'dash' } }
  ] : []

  const band = quants?.bands?.[asset] ?? null
  const qasset = quants?.[asset] ?? null
  const predTrace = predsClean.length ? [{
    x: predsClean.map(p => p.timestamp),
    y: predsClean.map(p => p[`${assetKey}_pred_24h`] ?? p[`${assetKey}_pred_96h`]),
    type: 'scatter',
    mode: 'lines',
    name: `${assetKey} Pred`
  }, ...(band ? [{
    x: predsClean.map(p => p.timestamp),
    y: predsClean.map(p => (p[`${assetKey}_pred_24h`] ?? p[`${assetKey}_pred_96h`]) + band),
    type: 'scatter',
    mode: 'lines',
    name: `${assetKey} Upper`,
    line: { width: 0 },
    showlegend: false
  },{
    x: predsClean.map(p => p.timestamp),
    y: predsClean.map(p => (p[`${assetKey}_pred_24h`] ?? p[`${assetKey}_pred_96h`]) - band),
    type: 'scatter',
    mode: 'lines',
    name: `${assetKey} Band`,
    fill: 'tonexty',
    fillcolor: 'rgba(255,255,255,0.12)',
    line: { width: 0 },
    showlegend: false
  }] : []), ...(qasset && isFinite(qasset.p10) ? [{
    x: predsClean.map(p => p.timestamp),
    y: predsClean.map(() => Number(qasset.p10)),
    type: 'scatter',
    mode: 'lines',
    name: 'P10',
    line: { color: '#ff4d4f', dash: 'dot' }
  }] : []), ...(qasset && isFinite(qasset.p50) ? [{
    x: predsClean.map(p => p.timestamp),
    y: predsClean.map(() => Number(qasset.p50)),
    type: 'scatter',
    mode: 'lines',
    name: 'P50',
    line: { color: '#ffd666' }
  }] : []), ...(qasset && isFinite(qasset.p90) ? [{
    x: predsClean.map(p => p.timestamp),
    y: predsClean.map(() => Number(qasset.p90)),
    type: 'scatter',
    mode: 'lines',
    name: 'P90',
    line: { color: '#52c41a', dash: 'dot' }
  }] : [])] : []

  function inferDecision(text) {
    if (!text) return 'HOLD'
    const t = text.toUpperCase()
    if (t.includes('SELL') || t.includes('VENTA')) return 'SELL'
    if (t.includes('BUY') || t.includes('COMPRA')) return 'BUY'
    return 'HOLD'
  }

  const decision = useMemo(() => inferDecision(consensus), [consensus])

  return (
    <React.Fragment>
      <GlobalStyles />
      <div style={{padding: 20, fontFamily: 'system-ui', background: '#0b0e11', color: '#e5e5e5', position: 'relative'}}>
        <h1>SICAR Dashboard (React)</h1>
      {isLoading && (
        <div style={{
          position: 'absolute',
          top: 20,
          right: 20,
          background: 'rgba(26, 29, 41, 0.9)',
          padding: '8px 16px',
          borderRadius: '6px',
          border: '1px solid #444',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          zIndex: 1000
        }}>
          <span style={{animation: 'spin 1s linear infinite', fontSize: '16px'}}>🔄</span>
          <span>Analizando {asset}...</span>
        </div>
      )}
      <div style={{marginBottom: 16, display:'flex', gap:12, alignItems:'center'}}>
        <div>
          <label>Activo: </label>
          {(()=>{
            const optsBase = ['BTC-USD','ETH-USD','BNB-USD','SOL-USD','XRP-USD','LINK-USD']
            const dyn = Array.isArray(top?.rows) ? top.rows.map(r=>r.sym) : []
            const opts = Array.from(new Set([...optsBase, ...dyn]))
            
            return (
              <select 
                value={asset} 
                onChange={e => {
                  const selected = e.target.value
                  console.log(`🎯 Usuario seleccionó: ${selected}`)
                  setAsset(selected)
                  setSelectedAssets([selected]) // Mantener compatibilidad con el resto del código
                }}
                style={{
                  marginLeft: '8px',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid #444',
                  backgroundColor: isLoading ? '#2a2d39' : '#1a1d29',
                  color: '#e5e5e5',
                  fontSize: '14px',
                  cursor: isLoading ? 'wait' : 'pointer',
                  opacity: isLoading ? 0.7 : 1
                }}
                disabled={isLoading}
              >
                {opts.map((s,i)=>(
                  <option key={i} value={s}>{s}</option>
                ))}
              </select>
            )
          })()}
        </div>
        <RunPipelineButton label={'Repetir análisis'} mode={'quick'} assets={selectedAssets} onComplete={() => setTick(t => t + 1)} />
        <RunPipelineButton label={'Reentrenar'} mode={'full'} assets={selectedAssets} onComplete={() => setTick(t => t + 1)} />
        {updated && (
          <span style={{marginLeft:12, opacity:0.8}}>Último análisis: {new Date(updated.report_xai || updated.predictions || Date.now()).toLocaleString()}</span>
        )}
        {macro?.risk_reduced && (
          <span className={'badge'} style={{marginLeft:12}}>Modo Riesgo Reducido</span>
        )}
        <div style={{marginLeft:'auto', display:'flex', gap:8}}>
          <label>TF:
            <select value={tf} onChange={e=>setTf(e.target.value)} className={'btn-tab'}>
              <option>15m</option>
              <option>1h</option>
              <option>4h</option>
            </select>
          </label>
          <button className={'btn-tab'} onClick={() => setActiveTab('overview')} disabled={activeTab==='overview'}>Overview</button>
          <button className={'btn-tab'} onClick={() => setActiveTab('futures')} disabled={activeTab==='futures'}>Futuros NQ/MNQ</button>
        </div>
      </div>
      {activeTab==='overview' && (
        <>
          <section>
            <h2>Idea de Trading {asset}</h2>
            <SignalCard 
              title={asset} 
              risk={riskMulti?.[asset]} 
              plan={plan?.[asset]} 
              color={'#52c41a'} 
              tf={tf}
              keyField={asset.split('-')[0]}
              quants={quants?.[asset]}
            />
            {/* Debug: Mostrar datos recibidos */}
            {console.log(`📊 Datos para ${asset}:`, {
              risk: riskMulti?.[asset],
              plan: plan?.[asset],
              quants: quants?.[asset],
              riskMulti: riskMulti,
              planFull: plan,
              quantsFull: quants,
              xaiSummary: xaiSummary,
              consensusSummary: consensusSummary,
              xai: xai?.substring(0, 100) + '...',
              consensus: consensus?.substring(0, 100) + '...'
            })}
            {/* Debug: Mostrar estructura completa del primer objeto con datos */}
            {riskMulti && Object.keys(riskMulti).length > 0 && console.log('🔍 Estructura riskMulti:', JSON.stringify(riskMulti, null, 2))}
            {plan && Object.keys(plan).length > 0 && console.log('🔍 Estructura plan:', JSON.stringify(plan, null, 2))}
            {quants && Object.keys(quants).length > 0 && console.log('🔍 Estructura quants:', JSON.stringify(quants, null, 2))}
            {/* Debug: Análisis de IA */}
            {console.log(`🤖 Análisis IA para ${asset}:`, {
              xaiSummary: xaiSummary,
              consensusSummary: consensusSummary,
              xaiLength: xai?.length,
              consensusLength: consensus?.length
            })}
          </section>
          
          <section>
            <h2>Resumen {asset}</h2>
            {(riskMulti && riskMulti[asset]) || (Array.isArray(top?.rows) && top.rows.some(r=>r.sym===asset)) ? (
              (()=>{
                const rm = riskMulti && riskMulti[asset] ? riskMulti[asset].risk_metrics : (top.rows.find(r=>r.sym===asset)||{}).rm
                return (
                  <ul>
                    <li>VaR 95%: {((rm?.var_95||0)*100).toFixed(2)}%</li>
                    <li>Sharpe: {(rm?.sharpe_ratio||0).toFixed(2)}</li>
                    <li>Soporte: {rm?.support_level}</li>
                    <li>Resistencia: {rm?.resistance_level}</li>
                  </ul>
                )
              })()
            ) : null}
          </section>
          <section>
            <h2>Predicciones {asset} (24/96h) + Niveles</h2>
            {(preds && predTrace.length) ? (
              <Plot data={predTrace} layout={{ title: `${asset} Proyección`, height: 460, shapes }} />
            ) : (
              <p>Predicciones no disponibles para {asset}. Usa la tarjeta para histórico y niveles.</p>
            )}
          </section>
          
          <section>
            <h2>Plan de Trade</h2>
            {plan ? (
              <div style={{display: 'flex', gap: 40}}>
                <div>
                  <h3>{asset}</h3>
                  <ul>
                    <li>Entrada: {plan[asset]?.entry?.toFixed(2)}</li>
                    <li>SL: {plan[asset]?.sl?.toFixed(2)}</li>
                    <li>TP1: {plan[asset]?.tp1?.toFixed(2)}</li>
                    <li>TP2: {plan[asset]?.tp2?.toFixed(2)}</li>
                    <li>TP3: {plan[asset]?.tp3?.toFixed(2)}</li>
                  </ul>
                </div>
              </div>
            ) : (
              <p>Cargando plan de trade...</p>
            )}
          </section>
          <section>
            <h2>Fundamental & Consenso IA</h2>
            <div className={'chat-panel'}>
              <AnalysisPanel 
                title={'Reporte XAI'} 
                summary={{
                  header:`Decisión: ${xaiSummary?.decision || '—'} | Confianza: ${xaiSummary?.confidence ? `${xaiSummary.confidence.toFixed(1)}%` : 'N/A'}`,
                  bullets:(xaiSummary?.bullets||[])
                }} 
                fullText={xai || ''} 
                variant={'system'}
              />
              <AnalysisPanel 
                title={'Consenso IA'} 
                summary={{
                  header:`Acción: ${consensusSummary?.decision || '—'} | Confianza: ${consensusSummary?.confidence_label || 'N/A'}`,
                  bullets:[`Score: ${consensusSummary?.consensus_score?.toFixed(2) ?? 'N/A'}`, `Sentimiento: ${consensusSummary?.average_sentiment?.toFixed(2) ?? 'N/A'}`]
                }} 
                fullText={consensus || ''} 
                variant={'consensus'}
              />
              {breakoutValidation && (
                <div className={'bubble system'}>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                    <strong>🔍 Validación de Rupturas</strong>
                    <span className={`status-${breakoutValidation.status?.toLowerCase() || 'pending'}`}>
                      {breakoutValidation.status || 'PENDIENTE'}
                    </span>
                  </div>
                  <div style={{marginTop: 8}}>
                    <div><strong>Score:</strong> {breakoutValidation.total_score || 0}/{breakoutValidation.validation_threshold || 4}</div>
                    <div><strong>Confianza:</strong> {((breakoutValidation.confidence || 0) * 100).toFixed(1)}%</div>
                    {breakoutValidation.factors && (
                      <div style={{marginTop: 8}}>
                        <strong>Factores:</strong>
                        <ul style={{margin: '4px 0', paddingLeft: 16}}>
                          <li style={{color: (breakoutValidation.factors.volume || 0) >= 1 ? '#4ecdc4' : '#ff6b6b'}}>
                            Volumen: {(breakoutValidation.factors.volume || 0) * 1}/1
                            {(breakoutValidation.factors.volume || 0) >= 1 ? ' ✅' : ' ❌'}
                          </li>
                          <li style={{color: (breakoutValidation.factors.momentum || 0) >= 1 ? '#4ecdc4' : '#ff6b6b'}}>
                            Momentum: {(breakoutValidation.factors.momentum || 0) * 1}/1
                            {(breakoutValidation.factors.momentum || 0) >= 1 ? ' ✅' : ' ❌'}
                          </li>
                          <li style={{color: (breakoutValidation.factors.timeframe || 0) >= 1 ? '#4ecdc4' : '#ff6b6b'}}>
                            Tiempo: {(breakoutValidation.factors.timeframe || 0) * 1}/1
                            {(breakoutValidation.factors.timeframe || 0) >= 1 ? ' ✅' : ' ❌'}
                          </li>
                          <li style={{color: (breakoutValidation.factors.proximity || 0) >= 1 ? '#4ecdc4' : '#ff6b6b'}}>
                            Proximidad: {(breakoutValidation.factors.proximity || 0) * 1}/1
                            {(breakoutValidation.factors.proximity || 0) >= 1 ? ' ✅' : ' ❌'}
                          </li>
                          <li style={{color: (breakoutValidation.factors.volatility || 0) >= 1 ? '#4ecdc4' : '#ff6b6b'}}>
                            Volatilidad: {(breakoutValidation.factors.volatility || 0) * 1}/1
                            {(breakoutValidation.factors.volatility || 0) >= 1 ? ' ✅' : ' ❌'}
                          </li>
                          <li style={{color: (breakoutValidation.factors.sentiment || 0) >= 1 ? '#4ecdc4' : '#ff6b6b'}}>
                            Sentimiento: {(breakoutValidation.factors.sentiment || 0) * 1}/1
                            {(breakoutValidation.factors.sentiment || 0) >= 1 ? ' ✅' : ' ❌'}
                          </li>
                        </ul>
                      </div>
                    )}
                    {breakoutValidation.warnings && breakoutValidation.warnings.length > 0 && (
                      <div style={{marginTop: 8}}>
                        <strong style={{color: '#ff6b6b'}}>⚠️ Advertencias:</strong>
                        <ul style={{margin: '4px 0', paddingLeft: 16, color: '#ff6b6b'}}>
                          {breakoutValidation.warnings.map((warning, i) => (
                            <li key={i}>{warning}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {breakoutValidation.recommendations && breakoutValidation.recommendations.length > 0 && (
                      <div style={{marginTop: 8}}>
                        <strong style={{color: '#4ecdc4'}}>💡 Recomendaciones:</strong>
                        <ul style={{margin: '4px 0', paddingLeft: 16, color: '#4ecdc4'}}>
                          {breakoutValidation.recommendations.map((rec, i) => (
                            <li key={i}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <div className={'card'}>
              <h3 style={{marginTop:0}}>Niveles actuales ({asset})</h3>
              <ul>
                <li>Entrada: {levels?.entry?.toFixed(2)}</li>
                <li>SL: {levels?.sl?.toFixed(2)}</li>
                <li>TP1: {levels?.tp1?.toFixed(2)}</li>
                <li>TP2: {levels?.tp2?.toFixed(2)}</li>
                <li>TP3: {levels?.tp3?.toFixed(2)}</li>
              </ul>
            </div>
          </section>

          
        </>
      )}
      {activeTab==='futures' && (
        <section>
          <h2>Futuros NQ/MNQ (Prototipo en React)</h2>
          <FuturesPanel />
        </section>
      )}
    </div>
    </React.Fragment>
  )
}

function RunPipelineButton({ label = 'Repetir análisis', mode = 'quick', assets = [], onComplete }) {
  const [status, setStatus] = useState('idle')
  const [log, setLog] = useState([])
  const trigger = async () => {
    setStatus('starting')
    const url = mode==='quick' ? `${API}/run-pipeline?mode=quick` : `${API}/run-pipeline?mode=full`
    await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ assets }) })
    setStatus('running')
    const interval = setInterval(async () => {
      const r = await fetch(`${API}/run-status`)
      const j = await r.json()
      setLog(j.log || [])
      if (j.status === 'done') {
        clearInterval(interval)
        setStatus('done')
        onComplete && onComplete()
      }
    }, 1500)
  }
  return (
    <div>
      <button onClick={trigger} disabled={status==='running'} style={{padding:'6px 12px'}}>{label}</button>
      <span style={{marginLeft:8}}>{status==='running' ? 'Ejecutando...' : status==='done' ? 'Completado' : ''}</span>
      {(status==='running' || status==='done') && (
        <details style={{marginTop:8}}>
          <summary>Ver log</summary>
          <pre style={{whiteSpace:'pre-wrap', maxHeight:200, overflow:'auto'}}>{(log||[]).join('\n')}</pre>
        </details>
      )}
    </div>
  )
}

function AnalysisPanel({ title, summary, fullText, variant }) {
  const [mode, setMode] = useState('resumen')
  return (
    <div className={`bubble ${variant}`}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <strong>{title}</strong>
        <select value={mode} onChange={e=>setMode(e.target.value)} className={'btn-tab'}>
          <option value={'resumen'}>Resumen</option>
          <option value={'completo'}>Completo</option>
        </select>
      </div>
      {mode==='resumen' ? (
        <>
          <div>{summary?.header}</div>
          <ul>
            {(summary?.bullets||[]).map((b,i)=>(<li key={i}>{b}</li>))}
          </ul>
        </>
      ) : (
        (()=>{
          const parseJsonBlock = txt => {
            try {
              const s = txt.slice(txt.indexOf('{'))
              const e = s.lastIndexOf('}')
              const j = JSON.parse(s.substring(0, e+1))
              return j
            } catch { return null }
          }
          const toHtml = t => {
            if (!t) return ''
            let x = t.replace(/\\n/g,'\n')
            x = x.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
            x = x.replace(/\(Palabras:[^\)]*\)/g,'=== FIN DEL REPORTE ===')
            x = x.split('\n\n').map(p=>`<p>${p.replace(/\n/g,'<br/>')}</p>`).join('')
            return x
          }
          const j = parseJsonBlock(fullText)
          if (j && typeof j==='object') {
            const entries = Object.entries(j).filter(([k])=>['openai','grok'].includes(String(k).toLowerCase()))
            return (
              <div className={'pre-readable'}>
                {entries.map(([k,v],i)=> (
                  <div key={i} style={{marginBottom:12}}>
                    <div style={{fontWeight:700, marginBottom:6}}>{k.toUpperCase()}</div>
                    <div dangerouslySetInnerHTML={{__html: toHtml(String(v))}} />
                  </div>
                ))}
              </div>
            )
          }
          return <div className={'pre-readable'} dangerouslySetInnerHTML={{__html: toHtml(fullText)}} />
        })()
      )}
    </div>
  )
}

function SignalCard({ title, risk, plan, tf='1h', keyField = 'BTC', color = '#52c41a', quants }) {
  // Debug: Verificar datos recibidos
  console.log(`📋 SignalCard recibiendo datos para ${title}:`, { risk, plan, quants })
  
  const rm = risk?.risk_metrics || {}
  const entry = plan?.entry
  const sl = plan?.sl
  const tp1 = plan?.tp1
  const tp2 = plan?.tp2
  const tp3 = plan?.tp3
  const rr = plan?.rr_tp1
  const direction = plan?.direction || 'HOLD'
  const isSell = direction==='SELL'
  const callout = isSell ? 'Sell Signal' : (direction==='BUY' ? 'Buy Signal' : 'Sin Señal')
  let profitPct = null
  if (entry!=null && tp1!=null && isFinite(entry) && isFinite(tp1) && entry!==0) {
    profitPct = ((tp1 - entry) / entry) * 100
  }
  const profit = profitPct!=null ? `${profitPct>=0?'+':''}${profitPct.toFixed(1)}%` : '—'
  const [hist, setHist] = useState(null)
  useEffect(() => {
    const sym = title
    fetch(`${API}/history?symbol=${encodeURIComponent(sym)}&interval=${encodeURIComponent(tf)}&limit=100`)
      .then(r => r.json())
      .then(j => setHist(j.data || []))
      .catch(() => setHist(null))
  }, [title, tf])
  const xs = (hist||[]).map(p => p.timestamp)
  const ys = (hist||[]).map(p => p.close)
  const vols = (hist||[]).map(p => p.volume)
  const maxv = Math.max(...vols, 1)
  const vbars = vols.map(v => v/maxv)
  const diffs = ys.map((y,i) => (i>0 && y!=null && ys[i-1]!=null) ? Math.abs(y - ys[i-1]) : 0)
  const maxd = Math.max(...diffs)
  const bars = diffs.map(d => maxd>0 ? d/maxd : 0)
  const shapes = entry ? [
    { type:'line', x0: xs[0], x1: xs.slice(-1)[0], y0: entry, y1: entry, line: { color: 'yellow', width: 1 }},
    { type:'line', x0: xs[0], x1: xs.slice(-1)[0], y0: sl, y1: sl, line: { color: 'red', width: 1 }},
    { type:'line', x0: xs[0], x1: xs.slice(-1)[0], y0: tp1, y1: tp1, line: { color: 'green', width: 1 }}
  ] : []
  const annotations = entry ? [{ x: xs[xs.length-1], y: tp1, text: callout, showarrow: true, arrowhead: 3, ax: -20, ay: -40, font: { color:'#fff' } }] : []
  // Sigma-retorno y etiqueta de riesgo
  let riskLabel = 'N/A'
  if (ys.length>10 && entry!=null && tp1!=null) {
    const ret = []
    for (let i=1;i<ys.length;i++) ret.push((ys[i]-ys[i-1])/ys[i-1])
    const mean = ret.reduce((a,b)=>a+b,0)/ret.length
    const variance = ret.reduce((a,b)=>a+(b-mean)*(b-mean),0)/ret.length
    const std = Math.sqrt(variance)
    const hours = tf==='4h'?24 : (tf==='15m'?24 : 24)
    const hStd = std*Math.sqrt(hours)
    const move = Math.abs((tp1 - entry)/entry)
    const sigma = move / (hStd||1e-6)
    if (sigma<=1.5) riskLabel = 'Bajo'
    else if (sigma<=3.0) riskLabel = 'Medio'
    else riskLabel = 'Alto'
  }
  // Gating 2-de-3 TF
  const [align, setAlign] = useState(null)
  useEffect(() => {
    const sym = title
    Promise.all([
      fetch(`${API}/history?symbol=${encodeURIComponent(sym)}&interval=15m&limit=60`).then(r=>r.json()).catch(()=>({data:[]})),
      fetch(`${API}/history?symbol=${encodeURIComponent(sym)}&interval=1h&limit=60`).then(r=>r.json()).catch(()=>({data:[]})),
      fetch(`${API}/history?symbol=${encodeURIComponent(sym)}&interval=4h&limit=60`).then(r=>r.json()).catch(()=>({data:[]}))
    ]).then(([m15,h1,h4])=>{
      const slope = d => {
        const arr = (d.data||[]).map(x=>x.close)
        if (arr.length<5) return 0
        const a = arr.slice(-5)
        return a[a.length-1]-a[0]
      }
      const s15 = slope(m15), s1 = slope(h1), s4 = slope(h4)
      const dir = (plan?.direction==='SELL') ? -1 : (plan?.direction==='BUY' ? 1 : 0)
      const count = [s15,s1,s4].filter(s=>dir!==0 && Math.sign(s)===dir).length
      setAlign(count)
    }).catch(()=>setAlign(null))
  }, [title, plan?.direction])
  const eligibleBase = !!plan?.eligible
  const eligible = eligibleBase && (align==null || align>=2)
  return (
    <div className={'card'}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h3 style={{margin:0}}>{title}</h3>
        <span className={'badge'} style={{background: eligible ? color : '#888'}}>{callout}</span>
        <span style={{marginLeft:8, opacity:0.8}}>Riesgo: {riskLabel}</span>
        {align!=null && (<span style={{marginLeft:8, opacity:0.8}}>{align}/3 TF alineados</span>)}
      </div>
      <div style={{marginTop:8, display:'grid', gridTemplateColumns:'1fr 1fr', gap:8}}>
        <div>
          <div>Entrada: {entry?.toFixed(2)}</div>
          <div>SL: {sl?.toFixed(2)}</div>
          <div>TP1: {tp1?.toFixed(2)} {rr ? `(${rr.toFixed(2)}R)` : ''}</div>
          {tp2 && <div>TP2: {tp2?.toFixed(2)}</div>}
          {tp3 && <div>TP3: {tp3?.toFixed(2)}</div>}
          {!eligible && (
            <ul>
              {(plan?.reasons?.tech||[]).map((b,i)=>(<li key={i}>{b}</li>))}
            </ul>
          )}
        </div>
        <div>
          <div>VaR 95%: {((rm.var_95||0)*100).toFixed(2)}%</div>
          <div>Sharpe: {(rm.sharpe_ratio||0).toFixed(4)}</div>
          <div>Soporte: {rm.support_level?.toFixed(2)} | Resistencia: {rm.resistance_level?.toFixed(2)}</div>
          {!eligible && (
            <ul>
              {(plan?.reasons?.fund||[]).map((b,i)=>(<li key={i}>{b}</li>))}
            </ul>
          )}
        </div>
      </div>
      {xs.length>0 && ys.every(y => y!=null) && (
        <div style={{marginTop:8}}>
          <Plot data={[
            { x: xs, y: ys, type:'scatter', mode:'lines', name: `${title} mini`, line:{color:'#7d89ff'} },
            { x: xs, y: vbars, type:'bar', name:'Vol', marker:{color:'#3a4ba3'}, yaxis:'y2' }
          ]} layout={{ height: 180, margin:{l:30,r:10,t:10,b:30}, template:'plotly_dark', shapes, annotations, yaxis2:{overlaying:'y', side:'right'} }} />
        </div>
      )}
      <div style={{marginTop:8, display:'flex', alignItems:'center', gap:8}}>
        <div className={'badge'} style={{background:(profitPct!=null && profitPct>0)?'#52c41a':'#ff4d4f'}}>Profit {profit}</div>
        {quants && (
          <span className={'badge'} style={{background:'#1a1f27'}}>P10: {Number(quants.p10||0).toFixed(2)} | P50: {Number(quants.p50||0).toFixed(2)} | P90: {Number(quants.p90||0).toFixed(2)}</span>
        )}
        <div style={{opacity:0.8}}>Distancia soporte: {((rm.support_distance_pct||0)).toFixed(2)}% | resistencia: {((rm.resistance_distance_pct||0)).toFixed(2)}%</div>
      </div>
    </div>
  )
}

function AltCard({ title, tf='1h', top }) {
  const rm = Array.isArray(top?.rows) ? (top.rows.find(r=>r.sym===title)||{}).rm : {}
  const [hist, setHist] = useState(null)
  useEffect(() => {
    fetch(`${API}/history?symbol=${encodeURIComponent(title)}&interval=${encodeURIComponent(tf)}&limit=120`)
      .then(r=>r.json()).then(j=>setHist(j.data||[])).catch(()=>setHist(null))
  }, [title, tf])
  const xs = (hist||[]).map(p=>p.timestamp)
  const ys = (hist||[]).map(p=>p.close)
  const sup = rm?.support_level
  const resi = rm?.resistance_level
  const shapes = (isFinite(sup) && isFinite(resi)) ? [
    { type:'line', x0: xs[0], x1: xs.slice(-1)[0], y0: sup, y1: sup, line:{ color:'orange', width:1 }},
    { type:'line', x0: xs[0], x1: xs.slice(-1)[0], y0: resi, y1: resi, line:{ color:'cyan', width:1 }}
  ] : []
  return (
    <div className={'card'}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h3 style={{margin:0}}>{title}</h3>
        <span style={{marginLeft:8, opacity:0.8}}>TF: {tf}</span>
      </div>
      <div style={{marginTop:8}}>
        {xs.length>0 && ys.every(y=>y!=null) ? (
          <Plot data={[{ x: xs, y: ys, type:'scatter', mode:'lines', name:title, line:{color:'#7d89ff'} }]} layout={{ height: 180, margin:{l:30,r:10,t:10,b:30}, template:'plotly_dark', shapes }} />
        ) : (
          <div>Cargando histórico...</div>
        )}
      </div>
      <div style={{marginTop:8}}>
        <div>VaR 95%: {((rm?.var_95||0)*100).toFixed(2)}%</div>
        <div>Sharpe: {(rm?.sharpe_ratio||0).toFixed(4)}</div>
        <div>Soporte: {sup?.toFixed?.(2)} | Resistencia: {resi?.toFixed?.(2)}</div>
        <div>Distancia soporte: {(rm?.support_distance_pct||0).toFixed(2)}% | resistencia: {(rm?.resistance_distance_pct||0).toFixed(2)}%</div>
      </div>
    </div>
  )
}

function HeatmapTable({ riskMulti, plan, symbols, onSelect }) {
  const [selected, setSelected] = useState('Todos')
  const [sortKey, setSortKey] = useState('rr')
  const [sortDir, setSortDir] = useState('desc')
  const [hoverIdx, setHoverIdx] = useState(null)
  const base = Array.isArray(symbols) && symbols.length>0 ? symbols : [
    { sym:'BTC-USD', rm:riskMulti?.['BTC-USD']?.risk_metrics, pl:plan?.['BTC-USD'] },
    { sym:'ETH-USD', rm:riskMulti?.['ETH-USD']?.risk_metrics, pl:plan?.['ETH-USD'] }
  ]
  const rows = base.filter(r => selected==='Todos' || r.sym===selected)
  const syms = Array.from(new Set(base.map(r=>r.sym)))
  const valOf = (r,k) => {
    if (k==='var') return Number(r.rm?.var_95||0)
    if (k==='sharpe') return Number(r.rm?.sharpe_ratio||0)
    if (k==='rr') return Number(r.pl?.rr_tp1||0)
    if (k==='support') return Number(r.rm?.support_distance_pct||0)
    if (k==='resistance') return Number(r.rm?.resistance_distance_pct||0)
    return 0
  }
  rows.sort((a,b)=>{
    const va = valOf(a,sortKey)
    const vb = valOf(b,sortKey)
    return sortDir==='asc' ? va-vb : vb-va
  })
  const cellStyle = (val, invert=false) => {
    const v = Number(val)
    if (!isFinite(v)) return { background:'#2b2f3a' }
    const score = invert ? -v : v
    if (score > 0.5) return { background:'#1f6f43' }
    if (score > 0.2) return { background:'#3b5b1e' }
    if (score < -0.5) return { background:'#6f1f1f' }
    if (score < -0.2) return { background:'#5b1e3b' }
    return { background:'#2b2f3a' }
  }
  const headBtn = (label,key) => (
    <button onClick={()=>{ setSortKey(key); setSortDir(d=> (sortKey===key && d==='asc') ? 'desc' : 'asc') }} className={'btn-tab'}>
      {label} {sortKey===key ? (sortDir==='asc' ? '↑' : '↓') : ''}
    </button>
  )
  return (
    <div>
      <div style={{display:'flex', gap:8, alignItems:'center', marginBottom:8}}>
        <label>Símbolos:
          <select value={selected} onChange={e=>{ const v=e.target.value; setSelected(v); if (onSelect && v!=='Todos') onSelect(v) }} className={'btn-tab'}>
            <option>Todos</option>
            {syms.map((s,i)=>(<option key={i}>{s}</option>))}
          </select>
        </label>
        <span style={{opacity:0.7}}>Ordenar por:</span>
        {headBtn('RR TP1','rr')}
        {headBtn('VaR 95%','var')}
        {headBtn('Sharpe','sharpe')}
        {headBtn('Dist. Soporte','support')}
        {headBtn('Dist. Resistencia','resistance')}
      </div>
      <div style={{overflowX:'auto'}}>
        <table style={{width:'100%', borderCollapse:'collapse'}}>
          <thead>
            <tr>
              <th style={{textAlign:'left', padding:8}}>Símbolo</th>
              <th style={{padding:8}}>VaR 95%</th>
              <th style={{padding:8}}>Sharpe</th>
              <th style={{padding:8}}>RR TP1</th>
              <th style={{padding:8}}>Dist. Soporte</th>
              <th style={{padding:8}}>Dist. Resistencia</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r,i) => (
              <tr key={i} onMouseEnter={()=>setHoverIdx(i)} onMouseLeave={()=>setHoverIdx(null)} onClick={()=>onSelect && onSelect(r.sym)} style={{cursor:'pointer', background: hoverIdx===i ? '#12161c' : 'transparent'}}>
                <td style={{padding:8}}>{r.sym}</td>
                <td style={{padding:8, ...cellStyle(r.rm?.var_95)}} title={'Pérdida esperada al 95% en un día'}>{((r.rm?.var_95||0)*100).toFixed(2)}%</td>
                <td style={{padding:8}} title={'Sharpe ratio (rendimiento ajustado por riesgo)'}>{(r.rm?.sharpe_ratio||0).toFixed(4)}</td>
                <td style={{padding:8, ...cellStyle(r.pl?.rr_tp1)}} title={'R múltiplos al primer objetivo'}>{(r.pl?.rr_tp1||0).toFixed(2)}R</td>
                <td style={{padding:8}} title={'Distancia porcentual al soporte'}>{(r.rm?.support_distance_pct||0).toFixed(2)}%</td>
                <td style={{padding:8}} title={'Distancia porcentual a la resistencia'}>{(r.rm?.resistance_distance_pct||0).toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function FuturesPanel() {
  const [symbol, setSymbol] = useState('MNQ')
  const [direction, setDirection] = useState('SELL')
  const [entry, setEntry] = useState(17500)
  const [vol, setVol] = useState(0.01)
  const [support, setSupport] = useState('')
  const [resistance, setResistance] = useState('')
  const [contracts, setContracts] = useState(1)
  const [dayMargin, setDayMargin] = useState(true)
  const [plan, setPlan] = useState(null)
  const submit = async () => {
    const payload = {
      symbol, direction,
      entry: Number(entry), vol: Number(vol),
      support: support ? Number(support) : undefined,
      resistance: resistance ? Number(resistance) : undefined,
      contracts, day_margin: dayMargin
    }
    const r = await fetch(`${API}/futures-plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const j = await r.json()
    setPlan(j)
  }
  return (
    <div>
      <div style={{display:'flex', gap:12, flexWrap:'wrap', alignItems:'center'}}>
        <label>Símbolo:
          <select value={symbol} onChange={e => setSymbol(e.target.value)}>
            <option>NQ</option>
            <option>MNQ</option>
          </select>
        </label>
        <label>Dirección:
          <select value={direction} onChange={e => setDirection(e.target.value)}>
            <option>SELL</option>
            <option>BUY</option>
          </select>
        </label>
        <label>Entrada:
          <input type="number" value={entry} onChange={e => setEntry(e.target.value)} step="0.25" />
        </label>
        <label>Volatilidad:
          <input type="number" value={vol} onChange={e => setVol(e.target.value)} step="0.001" />
        </label>
        <label>Soporte:
          <input type="number" value={support} onChange={e => setSupport(e.target.value)} step="0.25" />
        </label>
        <label>Resistencia:
          <input type="number" value={resistance} onChange={e => setResistance(e.target.value)} step="0.25" />
        </label>
        <label>Contratos:
          <input type="number" value={contracts} onChange={e => setContracts(parseInt(e.target.value||'1'))} />
        </label>
        <label>
          <input type="checkbox" checked={dayMargin} onChange={e => setDayMargin(e.target.checked)} /> Margen intradía
        </label>
        <button onClick={submit}>Calcular</button>
      </div>
      {plan && (
        <div style={{marginTop:12, background:'#12161c', padding:12, borderRadius:6}}>
          <div><strong>Entrada:</strong> {plan.entry?.toFixed(2)} | <strong>SL:</strong> {plan.sl?.toFixed(2)}</div>
          <div><strong>TP1:</strong> {plan.tp1?.toFixed(2)} ({plan.rr_tp1?.toFixed(2)}R) | <strong>TP2:</strong> {plan.tp2?.toFixed(2)} ({plan.rr_tp2?.toFixed(2)}R) | <strong>TP3:</strong> {plan.tp3?.toFixed(2)} ({plan.rr_tp3?.toFixed(2)}R)</div>
          <div><strong>Margen requerido:</strong> ${plan.margin_required?.toLocaleString()} | <strong>Notional:</strong> ${plan.notional?.toLocaleString()}</div>
        </div>
      )}
    </div>
  )
}
