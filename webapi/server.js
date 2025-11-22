import express from 'express'
import cors from 'cors'
import fs from 'fs'
import path from 'path'
import Papa from 'papaparse'
import { spawn } from 'child_process'
import https from 'https'

const app = express()
app.use(cors())
app.use(express.json())

const ROOT = path.resolve(process.cwd(), '..', 'results')

const FUTURES = {
  NQ: { tick_size: 0.25, tick_value: 5.0, multiplier: 20.0, margin_initial: 17600, margin_day: 8000 },
  MNQ: { tick_size: 0.25, tick_value: 0.5, multiplier: 2.0, margin_initial: 1760, margin_day: 800 },
}
function roundToTick(price, ts, mode = 'nearest') {
  const q = price / ts
  if (mode === 'up') return Math.ceil(q) * ts
  if (mode === 'down') return Math.floor(q) * ts
  return Math.round(q) * ts
}
function estimateMargin(sym, contracts = 1, day = true) {
  const f = FUTURES[sym]
  const base = day ? f.margin_day : f.margin_initial
  return base * contracts
}

function readJson(file) {
  try {
    const p = path.join(ROOT, file)
    const data = fs.readFileSync(p, 'utf8')
    return JSON.parse(data)
  } catch (e) {
    return { error: e.message }
  }
}

function readCsv(file) {
  try {
    const p = path.join(ROOT, file)
    const data = fs.readFileSync(p, 'utf8')
    const parsed = Papa.parse(data, { header: true, dynamicTyping: true })
    return parsed.data
  } catch (e) {
    return { error: e.message }
  }
}

app.get('/api/risk', (req, res) => {
  res.set('Cache-Control', 'no-store')
  res.json(readJson('risk_analysis.json'))
})

app.get('/api/risk-multi', (req, res) => {
  res.set('Cache-Control', 'no-store')
  res.json(readJson('risk_multi.json'))
})

app.get('/api/predictions', (req, res) => {
  res.set('Cache-Control', 'no-store')
  res.json(readCsv('predictions_24_96h.csv'))
})

app.get('/api/trade-plan', (req, res) => {
  res.set('Cache-Control', 'no-store')
  res.json(readJson('trade_plan.json'))
})

app.get('/api/forex-plan', (req, res) => {
  res.set('Cache-Control', 'no-store')
  res.json(readJson('forex_indices_trade_plan.json'))
})

app.get('/api/quantiles', (req, res) => {
  res.set('Cache-Control', 'no-store')
  res.json(readJson('quantiles.json'))
})

app.get('/api/report-xai', (req, res) => {
  try {
    const symbol = req.query.symbol || 'BTC-USD'
    // Intentar encontrar un archivo específico para el símbolo
    const symbolSpecific = path.resolve(process.cwd(), '..', 'reports', `reporte_dinamico_${symbol.replace('-', '_')}.txt`)
    const defaultPath = path.resolve(process.cwd(), '..', 'reports', 'reporte_dinamico_patchtst.txt')
    
    let p = defaultPath
    if (fs.existsSync(symbolSpecific)) {
      p = symbolSpecific
      console.log(`📄 Usando reporte específico para ${symbol}: ${symbolSpecific}`)
    } else {
      console.log(`📄 Usando reporte por defecto para ${symbol}: ${defaultPath}`)
    }
    
    const txt = fs.readFileSync(p, 'utf8')
    res.set('Cache-Control', 'no-store')
    res.type('text/plain').send(txt)
  } catch (e) {
    res.status(404).json({ error: e.message })
  }
})

app.get('/api/consensus-xai', (req, res) => {
  try {
    const symbol = req.query.symbol || 'BTC-USD'
    // Intentar encontrar un archivo específico para el símbolo
    const symbolSpecific = path.resolve(process.cwd(), '..', 'reports', `comparacion_multi_ia_${symbol.replace('-', '_')}.txt`)
    const defaultPath = path.resolve(process.cwd(), '..', 'reports', 'comparacion_multi_ia_patchtst.txt')
    
    let p = defaultPath
    if (fs.existsSync(symbolSpecific)) {
      p = symbolSpecific
      console.log(`📄 Usando consenso específico para ${symbol}: ${symbolSpecific}`)
    } else {
      console.log(`📄 Usando consenso por defecto para ${symbol}: ${defaultPath}`)
    }
    
    const txt = fs.readFileSync(p, 'utf8')
    res.set('Cache-Control', 'no-store')
    res.type('text/plain').send(txt)
  } catch (e) {
    res.status(404).json({ error: e.message })
  }
})

app.get('/api/assets', (req, res) => {
  const plan = readJson('trade_plan.json')
  const quants = readJson('quantiles.json')
  res.json({ assets: ['BTC-USD', 'ETH-USD'], plan, quants })
})

function extractDecision(text) {
  const t = (text || '').toUpperCase()
  if (t.includes('SELL') || t.includes('VENTA')) return 'SELL'
  if (t.includes('BUY') || t.includes('COMPRA')) return 'BUY'
  return 'HOLD'
}

function extractConfidence(text) {
  const m = (text || '').match(/(\d{1,3}(?:\.\d+)?)[ ]?\%/)
  if (m) return parseFloat(m[1])
  const mc = (text || '').match(/CONFIANZA[: ]+(\d+(?:\.\d+)?)/i)
  if (mc) return parseFloat(mc[1])
  return null
}

app.get('/api/breakout-validation', (req, res) => {
  try {
    const symbol = req.query.symbol || 'BTC-USD'
    // Intentar encontrar un archivo específico para el símbolo
    const symbolSpecific = path.resolve(process.cwd(), '..', 'reports', `breakout_validation_${symbol.replace('-', '_')}.json`)
    const defaultPath = path.resolve(process.cwd(), '..', 'reports', 'breakout_validation.json')
    
    let p = defaultPath
    if (fs.existsSync(symbolSpecific)) {
      p = symbolSpecific
      console.log(`📊 Usando validación de ruptura específica para ${symbol}: ${symbolSpecific}`)
    } else {
      console.log(`📊 Usando validación de ruptura por defecto para ${symbol}: ${defaultPath}`)
    }
    
    const data = fs.readFileSync(p, 'utf8')
    const jsonData = JSON.parse(data)
    res.set('Cache-Control', 'no-store')
    res.json(jsonData)
  } catch (e) {
    console.log(`⚠️ Error leyendo validación de ruptura: ${e.message}`)
    // Enviar datos de ejemplo si no existe el archivo
    const fallbackData = {
      status: 'PENDING',
      confidence: 0.5,
      factors: {
        volume: 0,
        momentum: 0,
        timeframe: 0,
        proximity: 0,
        volatility: 0,
        sentiment: 0
      },
      warnings: ['Datos de validación no disponibles'],
      recommendation: 'ESPERAR: Validación pendente',
      breakout_factor: 1.0,
      symbol: symbol || 'BTC-USD',
      timestamp: new Date().toISOString(),
      level_tested: null,
      current_price: 0,
      breakout_type: 'NEUTRAL',
      total_score: 0,
      validation_threshold: 4,
      is_valid: false
    }
    res.set('Cache-Control', 'no-store')
    res.json(fallbackData)
  }
})

app.get('/api/report-xai-summary', (req, res) => {
  try {
    const symbol = req.query.symbol || 'BTC-USD'
    // Intentar encontrar un archivo específico para el símbolo
    const symbolSpecific = path.resolve(process.cwd(), '..', 'reports', `reporte_dinamico_${symbol.replace('-', '_')}.txt`)
    const defaultPath = path.resolve(process.cwd(), '..', 'reports', 'reporte_dinamico_patchtst.txt')
    
    let p = defaultPath
    if (fs.existsSync(symbolSpecific)) {
      p = symbolSpecific
      console.log(`📄 Usando resumen de reporte específico para ${symbol}: ${symbolSpecific}`)
    } else {
      console.log(`📄 Usando resumen de reporte por defecto para ${symbol}: ${defaultPath}`)
    }
    
    const txt = fs.readFileSync(p, 'utf8')
    const decision = extractDecision(txt)
    const confidence = extractConfidence(txt)
    const lines = txt.split(/\r?\n/).map(s => s.trim()).filter(Boolean)
    const bullets = []
    for (const s of lines) {
      if (bullets.length >= 5) break
      if (/volatilidad|momentum|soporte|resistencia|riesgo|cambio|precio/i.test(s)) bullets.push(s)
    }
    res.set('Cache-Control', 'no-store')
    res.json({ decision, confidence, bullets })
  } catch (e) {
    res.status(404).json({ error: e.message })
  }
})

app.get('/api/consensus-xai-summary', (req, res) => {
  try {
    const symbol = req.query.symbol || 'BTC-USD'
    // Intentar encontrar un archivo específico para el símbolo
    const symbolSpecific = path.resolve(process.cwd(), '..', 'reports', `comparacion_multi_ia_${symbol.replace('-', '_')}.txt`)
    const defaultPath = path.resolve(process.cwd(), '..', 'reports', 'comparacion_multi_ia_patchtst.txt')
    
    let p = defaultPath
    if (fs.existsSync(symbolSpecific)) {
      p = symbolSpecific
      console.log(`📄 Usando resumen de consenso específico para ${symbol}: ${symbolSpecific}`)
    } else {
      console.log(`📄 Usando resumen de consenso por defecto para ${symbol}: ${defaultPath}`)
    }
    
    const txt = fs.readFileSync(p, 'utf8')
    const decision = extractDecision(txt)
    const confLine = txt.match(/Nivel de Confianza[: ](.+)/i)
    const scoreLine = txt.match(/Score de Consenso[: ](.+)/i)
    const sentLine = txt.match(/Sentimiento Promedio[: ](.+)/i)
    res.set('Cache-Control', 'no-store')
    res.json({ decision, confidence_label: confLine ? confLine[1].trim() : null, consensus_score: scoreLine ? parseFloat((scoreLine[1]||'0').replace(',', '.')) : null, average_sentiment: sentLine ? parseFloat((sentLine[1]||'0').replace(',', '.')) : null })
  } catch (e) {
    res.status(404).json({ error: e.message })
  }
})

// Last updated timestamps
app.get('/api/last-updated', (req, res) => {
  const files = {
    predictions: path.join(ROOT, 'predictions_24_96h.csv'),
    trade_plan: path.join(ROOT, 'trade_plan.json'),
    risk: path.join(ROOT, 'risk_analysis.json'),
    risk_multi: path.join(ROOT, 'risk_multi.json'),
    quantiles: path.join(ROOT, 'quantiles.json'),
    report_xai: path.resolve(process.cwd(), '..', 'reports', 'reporte_dinamico_patchtst.txt'),
    consensus_xai: path.resolve(process.cwd(), '..', 'reports', 'comparacion_multi_ia_patchtst.txt')
  }
  const out = {}
  for (const [k, p] of Object.entries(files)) {
    try {
      const st = fs.statSync(p)
      out[k] = new Date(st.mtime).toISOString()
    } catch (e) {
      out[k] = null
    }
  }
  res.set('Cache-Control', 'no-store')
  res.json(out)
})

// Pipeline runner
let lastRun = { status: 'idle', startedAt: null, endedAt: null, exitCode: null, log: [] }

app.get('/api/run-status', (req, res) => {
  res.json(lastRun)
})

app.post('/api/run-pipeline', (req, res) => {
  if (lastRun.status === 'running') {
    return res.status(409).json({ message: 'Pipeline ya en ejecución' })
  }
  lastRun = { status: 'running', startedAt: new Date().toISOString(), endedAt: null, exitCode: null, log: [] }
  const cwd = path.resolve(process.cwd(), '..')
  const mode = (req.query.mode || '').toLowerCase()
  const args = ['src/patchtst_sicar_pipeline.py']
  if (mode === 'quick') args.push('--quick')
  const assets = Array.isArray(req.body?.assets) ? req.body.assets : null
  if (assets && assets.length) {
    args.push('--assets')
    args.push(assets.join(','))
  }
  const isWin = process.platform === 'win32'
  const cmd = isWin ? `py -3` : `python3`
  const full = `${cmd} ${args.join(' ')}`
  const child = spawn(full, { cwd, shell: true, env: { ...process.env, PYTHONIOENCODING: 'utf-8' } })
  child.stdout.on('data', d => {
    const s = d.toString()
    lastRun.log.push(...s.split(/\r?\n/).slice(-10))
  })
  child.stderr.on('data', d => {
    const s = d.toString()
    lastRun.log.push(...s.split(/\r?\n/).slice(-10))
  })
  child.on('close', code => {
    lastRun.status = 'done'
    lastRun.exitCode = code
    lastRun.endedAt = new Date().toISOString()
  })
  res.status(202).json({ message: 'Pipeline iniciado' })
})

// Futures plan
app.post('/api/futures-plan', (req, res) => {
  try {
    const { symbol = 'MNQ', direction = 'SELL', entry = 17500, vol = 0.01, support, resistance, rr_targets = [1.0, 1.5, 2.0], contracts = 1, day_margin = true } = req.body || {}
    const sym = String(symbol).toUpperCase()
    if (!FUTURES[sym]) return res.status(400).json({ error: 'Símbolo no soportado' })
    const f = FUTURES[sym]
    const ts = f.tick_size
    const m = f.multiplier
    const e = roundToTick(entry, ts, 'nearest')
    const v = Math.max(0.001, Number(vol))
    let sup = support, resi = resistance
    let sl, risk, tps = [], rr = []
    if (String(direction).toUpperCase() === 'BUY') {
      if (!resi || resi <= e) resi = e * (1 + v)
      if (!sup || sup >= e) sup = e * (1 - v)
      sl = Math.min(sup, e * (1 - v))
      sl = roundToTick(sl, ts, 'down')
      risk = Math.max(1e-6, e - sl)
      for (const r of rr_targets) {
        const tp = roundToTick(e + r * risk, ts, 'up')
        tps.push(tp)
        rr.push((tp - e) / risk)
      }
      tps[0] = Math.max(tps[0], resi)
    } else {
      if (!sup || sup >= e) sup = e * (1 - v)
      if (!resi || resi <= e) resi = e * (1 + v)
      sl = Math.max(resi, e * (1 + v))
      sl = roundToTick(sl, ts, 'up')
      risk = Math.max(1e-6, sl - e)
      for (const r of rr_targets) {
        const tp = roundToTick(e - r * risk, ts, 'down')
        tps.push(tp)
        rr.push((e - tp) / risk)
      }
      tps[0] = Math.min(tps[0], sup)
    }
    const margin = estimateMargin(sym, contracts, day_margin)
    const notional = e * m * contracts
    res.set('Cache-Control', 'no-store')
    return res.json({
      symbol: sym, direction, entry: e, sl, tp1: tps[0], tp2: tps[1], tp3: tps[2], rr_tp1: rr[0], rr_tp2: rr[1], rr_tp3: rr[2],
      tick_size: ts, tick_value: f.tick_value, multiplier: m, margin_required: margin, notional
    })
  } catch (e) {
    return res.status(500).json({ error: e.message })
  }
})

function mapSymbol(sym) {
  const s = String(sym).toUpperCase()
  if (s.endsWith('-USD')) return s.replace('-USD', 'USDT')
  return s.replace('-', '')
}

function fetchBinanceKlines(symbol, interval = '1h', limit = 100) {
  const qs = new URLSearchParams({ symbol, interval, limit: String(limit) })
  const url = `https://api.binance.com/api/v3/klines?${qs.toString()}`
  return new Promise((resolve, reject) => {
    const req = https.get(url, resp => {
      let data = ''
      resp.on('data', chunk => data += chunk)
      resp.on('end', () => {
        try {
          const arr = JSON.parse(data)
          const out = arr.map(k => ({ timestamp: new Date(k[0]).toISOString(), open: Number(k[1]), high: Number(k[2]), low: Number(k[3]), close: Number(k[4]), volume: Number(k[5]) }))
          resolve(out)
        } catch (e) { reject(e) }
      })
    })
    req.on('error', reject)
    req.setTimeout(8000, () => { req.destroy(new Error('timeout')) })
  })
}

function fetchBinanceTickers() {
  const url = `https://api.binance.com/api/v3/ticker/24hr`
  return new Promise((resolve, reject) => {
    const req = https.get(url, resp => {
      let data = ''
      resp.on('data', chunk => data += chunk)
      resp.on('end', () => {
        try {
          const arr = JSON.parse(data)
          resolve(arr)
        } catch (e) { reject(e) }
      })
    })
    req.on('error', reject)
    req.setTimeout(8000, () => { req.destroy(new Error('timeout')) })
  })
}

app.get('/api/history', async (req, res) => {
  try {
    const symbol = mapSymbol(req.query.symbol || 'BTC-USD')
    const interval = req.query.interval || '1h'
    const limit = parseInt(req.query.limit || '100')
    const data = await fetchBinanceKlines(symbol, interval, limit)
    res.set('Cache-Control', 'no-store')
    res.json({ symbol, interval, data })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

app.get('/api/top-crypto', async (req, res) => {
  try {
    const tickers = await fetchBinanceTickers()
    const limit = Math.max(1, parseInt(req.query.limit || '10'))
    const usdt = tickers.filter(t => /USDT$/.test(t.symbol))
    usdt.sort((a,b) => parseFloat(b.quoteVolume||'0') - parseFloat(a.quoteVolume||'0'))
    const top = usdt.slice(0, limit)
    console.log(`[top-crypto] tickers=${tickers.length} usdt=${usdt.length} limit=${limit}`)
    const rows = []
    for (const t of top) {
      const sym = t.symbol
      const hist = await fetchBinanceKlines(sym, '1h', 200)
      const closes = hist.map(h=>h.close)
      const ret = []
      for (let i=1;i<closes.length;i++) ret.push((closes[i]-closes[i-1])/closes[i-1])
      const mean = ret.length ? ret.reduce((a,b)=>a+b,0)/ret.length : 0
      const variance = ret.length ? ret.reduce((a,b)=>a+(b-mean)*(b-mean),0)/ret.length : 0
      const std = Math.sqrt(variance)
      const sharpe = std>0 ? (mean/std) : 0
      const sorted = [...ret].sort((a,b)=>a-b)
      const idx = Math.max(0, Math.floor(0.05*sorted.length) - 1)
      const var95 = sorted.length ? sorted[idx] : 0
      const curr = closes[closes.length-1] || 0
      const win = closes.slice(-50)
      const support = win.length ? Math.min(...win) : curr
      const resistance = win.length ? Math.max(...win) : curr
      const supportDist = curr>0 ? ((curr - support)/curr)*100 : 0
      const resistanceDist = curr>0 ? ((resistance - curr)/curr)*100 : 0
      const friendly = sym.replace(/USDT$/,'-USD')
      rows.push({
        sym: friendly,
        rm: {
          var_95: var95,
          sharpe_ratio: sharpe,
          support_level: support,
          resistance_level: resistance,
          support_distance_pct: supportDist,
          resistance_distance_pct: resistanceDist
        },
        pl: null
      })
    }
    res.set('Cache-Control','no-store')
    res.json({ rows })
  } catch (e) {
    console.error('[top-crypto] error', e)
    res.status(500).json({ error: e.message })
  }
})

function normalCdf(x) {
  // Abramowitz and Stegun approximation
  const a1=0.254829592,a2=-0.284496736,a3=1.421413741,a4=-1.453152027,a5=1.061405429,p=0.3275911
  const sign = x<0?-1:1
  const t = 1.0/(1.0+p*Math.abs(x))
  const y = 1.0 - ((((a5*t+a4)*t+a3)*t+a2)*t+a1)*t*Math.exp(-x*x)
  return 0.5*(1.0+sign*y)
}

app.get('/api/probability', async (req, res) => {
  try {
    const symbol = mapSymbol(req.query.symbol || 'BTC-USD')
    const interval = req.query.interval || '1h'
    const hours = parseInt(req.query.hours || '24')
    const threshold = parseFloat(req.query.threshold)
    const hist = await fetchBinanceKlines(symbol, interval, 200)
    if (!hist || !hist.length || !isFinite(threshold)) return res.status(400).json({ error: 'Datos insuficientes' })
    const closes = hist.map(h=>h.close)
    const ret = []
    for (let i=1;i<closes.length;i++) ret.push((closes[i]-closes[i-1])/closes[i-1])
    const mean = ret.reduce((a,b)=>a+b,0)/ret.length
    const variance = ret.reduce((a,b)=>a+(b-mean)*(b-mean),0)/ret.length
    const std = Math.sqrt(variance)
    const hStd = std*Math.sqrt(hours)
    const curr = closes[closes.length-1]
    const r = (threshold-curr)/curr
    const z = (r - mean*hours)/hStd
    const probUp = 1 - normalCdf(z)
    res.set('Cache-Control', 'no-store')
    res.json({ symbol, interval, hours, current: curr, threshold, prob: probUp })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

app.get('/api/breakout-validation', (req, res) => {
  try {
    const symbol = req.query.symbol || 'BTC-USD'
    // Intentar encontrar un archivo específico para el símbolo
    const symbolSpecific = path.resolve(process.cwd(), '..', 'reports', `breakout_validation_${symbol.replace('-', '_')}.json`)
    const defaultPath = path.resolve(process.cwd(), '..', 'reports', 'breakout_validation.json')
    
    let p = defaultPath
    if (fs.existsSync(symbolSpecific)) {
      p = symbolSpecific
      console.log(`🔍 Usando validación de ruptura específica para ${symbol}: ${symbolSpecific}`)
    } else {
      console.log(`🔍 Usando validación de ruptura por defecto para ${symbol}: ${defaultPath}`)
    }
    
    const data = fs.readFileSync(p, 'utf8')
    const json = JSON.parse(data)
    res.set('Cache-Control', 'no-store')
    res.json(json)
  } catch (e) {
    // Si no existe el archivo, devolver datos de ejemplo
    console.log(`⚠️ No se encontró validación de ruptura para ${symbol}, usando datos de ejemplo`)
    res.json({
      status: 'PENDING',
      confidence: 0.65,
      factors: {
        volume: 0.7,
        momentum: 0.8,
        time: 0.6,
        proximity: 0.9,
        volatility: 0.8,
        sentiment: 0.5
      },
      warnings: ['Esperando confirmación de volumen'],
      recommendations: ['Espere 1-2 velas de confirmación'],
      breakout_factor: 0.8,
      symbol: symbol,
      timestamp: new Date().toISOString()
    })
  }
})

app.get('/api/macro', (req, res) => {
  const now = Date.now()
  const events = [
    { name: 'FOMC Statement', time: new Date(now + 3*60*60*1000).toISOString(), impact: 'high' },
    { name: 'CPI Release', time: new Date(now + 24*60*60*1000).toISOString(), impact: 'high' }
  ]
  const risk_reduced = events.some(ev => new Date(ev.time).getTime() - now <= 6*60*60*1000)
  res.set('Cache-Control','no-store')
  res.json({ events, risk_reduced })
})

const PORT = process.env.PORT || 4000
app.listen(PORT, () => {
  console.log(`SICAR Web API escuchando en http://localhost:${PORT}`)
})
