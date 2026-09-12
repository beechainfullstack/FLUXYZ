import { useEffect, useRef, useState } from 'react'
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BookOpen, ChevronDown, ChevronRight, CircleHelp, Clock3, Database, Droplets, ExternalLink, Flame, Github, Hexagon, Layers3, LayoutDashboard, LoaderCircle, Orbit, Radio, RefreshCw, Sparkles, Telescope } from 'lucide-react'
import { MarketChart, Sparkline } from './Charts'
import { SignalDials } from './Signals'
import { Chat } from './Chat'
import type { Dashboard, WindowRange } from './types'
import { API, commodities, money, signed, stamp } from './types'

type View = 'overview' | 'signals' | 'methodology'
const nav = [
  { key: 'overview' as const, title: 'Observatory', short: 'Overview', icon: LayoutDashboard },
  { key: 'signals' as const, title: 'Signal research', short: 'Research', icon: Orbit },
  { key: 'methodology' as const, title: 'Data & methodology', short: 'Data', icon: BookOpen },
]
const sourceNames: Record<string, string> = {
  'twelve_data:GLD': 'Twelve Data · GLD', 'twelve_data:USO': 'Twelve Data · USO',
  'twelve_data:BTU': 'Twelve Data · BTU', noaa_kp: 'NOAA · planetary Kp',
  noaa_solar: 'NOAA · GOES solar', eia: 'EIA · official coal', astronomy: 'Astronomical calculation', gemini: 'Gemini Flash',
}

export default function App() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [range, setRange] = useState<WindowRange>('1w'), [view, setView] = useState<View>('overview')
  const [error, setError] = useState(''), [loading, setLoading] = useState(true)
  const [refreshKey, setRefreshKey] = useState(0), [chatQuestion, setChatQuestion] = useState<string | null>(null)
  const [metric, setMetric] = useState<'price_r' | 'return_r'>('price_r'), [feedExpanded, setFeedExpanded] = useState(false)
  const chatTrigger = useRef<HTMLButtonElement | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await fetch(`${API}/api/dashboard?range=${range}`, { signal: controller.signal })
        if (!response.ok) throw new Error('The observatory is connecting to its data store. Please retry shortly.')
        const result: Dashboard = await response.json()
        setData(result); setError('')
      } catch (e) {
        if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to refresh observations.')
      } finally { if (!controller.signal.aborted) setLoading(false) }
    }
    void load()
    const timer = window.setInterval(() => { void load() }, 30000)
    return () => { controller.abort(); window.clearInterval(timer) }
  }, [range, refreshKey])
  const prices = data?.prices ?? { gold: [], oil: [], coal_proxy: [] }
  const latest = Object.values(prices).flat().map(p => p.timestamp).sort().at(-1) ?? null
  const sourceErrors = data?.sources.filter(s => s.status === 'error') ?? []
  const stale = !!latest && !!data?.market_open && new Date(data.generated_at).getTime() - new Date(latest).getTime() > 30 * 60000
  const openChat = (question = '', trigger?: HTMLButtonElement) => { chatTrigger.current = trigger ?? null; setChatQuestion(question) }
  function switchRange(value: WindowRange) { if (value !== range) { setLoading(true); setRange(value) } }
  return <>
    <a className="skip-link" href="#main">Skip to content</a>
    <aside className="sidebar" aria-label="Primary navigation">
      <a className="brand-symbol" href="#main" aria-label="fluxyz home" onClick={() => setView('overview')}><Orbit size={28} strokeWidth={1.3}/></a>
      <div className="side-links">{nav.map(item => <button key={item.key} className={`side-link ${view === item.key ? 'active' : ''}`} title={item.title} aria-label={item.title}
        aria-current={view === item.key ? 'page' : undefined} onClick={() => setView(item.key)}><item.icon size={19} strokeWidth={1.5}/></button>)}
        <button className="side-link" title="Ask the agent" aria-label="Ask the agent" onClick={e => openChat('', e.currentTarget)}><Sparkles size={19} strokeWidth={1.5}/></button>
      </div>
      <div className="side-bottom"><a href="https://github.com/beechainfullstack/FLUXYZ" target="_blank" rel="noreferrer" aria-label="Source code on GitHub" className="side-link"><Github size={18}/></a><button className="side-link" aria-label="About the data" onClick={() => setView('methodology')}><CircleHelp size={18}/></button><div className="avatar" aria-label="Flux observatory">f.</div></div>
    </aside>
    <div className="app-shell">
      <header className="topbar"><a href="#main" className="wordmark" onClick={() => setView('overview')}>fluxyz<span>OBSERVATORY</span></a>
        <div className="topbar-right"><span className="system-status"><i className={error || sourceErrors.length ? 'status-dot warning' : 'status-dot'}/>{!data ? 'CONNECTING' : error ? 'CONNECTION ALERT' : sourceErrors.length ? 'SOURCE ALERT' : 'SYSTEM ONLINE'}</span><span className="top-divider"/><span className="edition">An open-ended inquiry <span>↗</span></span></div>
      </header>
      <main id="main">
        <section className="page-heading"><div><div className="eyebrow"><span className="tiny-star">✧</span> MARKETS, IN A WIDER ORBIT</div><h1>{view === 'overview' ? <>Everything moves.<span> Find the relationships.</span></> : view === 'signals' ? <>Beyond the market.<span> Within the evidence.</span></> : <>A clear view.<span> Of what we know.</span></>}</h1><p>Gold, coal, and oil. Three markets. A universe of possible connections.</p></div>
          <button className="ask-button" onClick={e => openChat('', e.currentTarget)}><Sparkles size={16}/>Ask the agent<ArrowUpRight size={16}/></button>
        </section>
        <div className="view-toolbar"><nav className="tabs" aria-label="Dashboard sections">{nav.map(item => <button key={item.key} aria-label={item.title} aria-current={view === item.key ? 'page' : undefined} className={view === item.key ? 'selected' : ''} onClick={() => setView(item.key)}><item.icon size={14}/><span className="tab-full">{item.title}</span><span className="tab-short">{item.short}</span></button>)}</nav>
          <div className="update-note"><Clock3 size={12}/><span>{data ? `Updated ${stamp(data.generated_at)}` : 'Connecting to live sources'}</span><button className="icon-button small" aria-label="Refresh observations" disabled={loading} onClick={() => { setLoading(true); setRefreshKey(k => k + 1) }}><RefreshCw size={13} className={loading ? 'spin' : ''}/></button></div>
        </div>
        {(error || sourceErrors.length > 0 || stale) && <div className="notice" role="status"><Radio size={16}/><p>{error || (stale ? 'Market bars are more than 30 minutes old. Last stored readings are shown.' : `${sourceErrors.map(s => sourceNames[s.source] ?? s.source).join(', ')} could not refresh. Last successful readings remain visible.`)}</p><button onClick={() => setView('methodology')}>Source details <ArrowRight size={14}/></button></div>}
        {view === 'overview' && <>
          <section className="price-grid" aria-label="Commodity market prices">{commodities.map((c, index) => {
            const rows = prices[c.key], last = rows.at(-1), change = last ? (last.price / rows[0].price - 1) * 100 : null
            const Icon = index === 0 ? Hexagon : index === 1 ? Droplets : Flame
            return <article className={`price-card ${c.key}`} key={c.key}>
              <div className="price-card-top"><div className="commodity-name"><div className="commodity-icon" style={{ color: c.color }}><Icon size={17} strokeWidth={1.5}/></div><h2>{c.name}</h2><span className="ticker">{c.ticker}</span></div><span className="proxy-tag">PROXY <ArrowUpRight size={10}/></span></div>
              <div className="price-numbers"><strong>{last ? money(last.price) : '—'}</strong><span className="currency">USD</span><span className={`price-change ${change !== null && change < 0 ? 'down' : ''}`}>{change === null ? 'Awaiting data' : <>{change >= 0 ? <ArrowUpRight size={14}/> : <ArrowDownRight size={14}/>} {signed(change)}%</>}</span></div>
              <Sparkline rows={rows} color={c.color}/><div className="price-card-foot"><span>{c.note}</span><span>{data?.range.toUpperCase() ?? range.toUpperCase()} change</span></div>
            </article>
          })}</section>
          <div className="main-grid">
            <section className="panel market-panel" aria-labelledby="market-title">
              <div className="panel-header"><div><div className="section-kicker">THE MARKET LENS</div><h2 id="market-title">Three paths. One perspective.</h2></div><div className="range-control" aria-label="Chart time range">{(['1d', '1w', '1m'] as const).map(r => <button key={r} aria-pressed={range === r} disabled={loading && range === r} className={range === r ? 'active' : ''} onClick={() => switchRange(r)}>{r.toUpperCase()}</button>)}</div></div>
              <div className="chart-legend">{commodities.map(c => <span key={c.key}><i style={{ background: c.color }} className={c.key === 'coal_proxy' ? 'dashed' : ''}/>{c.name} <b>{c.ticker}</b></span>)}<span className="chart-unit">{loading ? 'Updating…' : 'RELATIVE PERFORMANCE, %'}</span></div>
              <MarketChart prices={prices}/>
              <div className="chart-footer"><span><i className="status-dot muted"/>{!data ? 'Market status pending' : data.market_open ? 'US market open' : 'US market closed'}<span className="muted-separator">·</span>5-minute bars</span><span>Last bar {stamp(latest, true)}</span></div>
              <div className="coal-reference"><Database size={15}/><div><strong>Coal, in the physical world.</strong><span>EIA official reference · {data?.coal_reference?.period ?? 'awaiting reading'} · monthly</span></div><div className="reference-value">{data?.coal_reference ? money(data.coal_reference.price) : '—'}<span>/ short ton</span></div><button className="icon-button" aria-label="Understand the official coal reference" onClick={() => setView('methodology')}><ArrowUpRight size={17}/></button></div>
            </section>
            <section className={`panel log-panel ${feedExpanded ? 'expanded' : ''}`} aria-labelledby="log-title">
              <div className="panel-header"><div><div className="section-kicker">A CONTINUOUS INQUIRY</div><h2 id="log-title"><Sparkles size={16}/>Observatory log</h2></div><span className="log-badge"><i/>AGENT</span></div>
              <div className="log-status"><span className="status-dot"/><span>Gemini Flash <span className="muted-separator">/</span> measured, not assumed</span></div>
              <div className="log-entries" aria-label="Agent observations">{data?.observations.length ? data.observations.map((entry, i) => <article className="log-entry" key={entry.id}><div className="log-entry-meta"><span>{String(data.observations.length - i).padStart(2, '0')}</span><time dateTime={entry.timestamp}>{stamp(entry.timestamp, true)}</time>{i === 0 && <span className="new-tag">LATEST</span>}</div><p>{entry.text}</p><span className="log-source">[ StarRocks → {entry.model} ]</span></article>) : <div className="log-empty">Listening to the incoming observations.<br/>The first entry will appear after a collection cycle.</div>}</div>
              <button className="expand-feed" onClick={() => setFeedExpanded(v => !v)}>{feedExpanded ? 'Collapse log' : 'Expand observatory log'}<ChevronDown size={15}/></button>
              <button className="log-question" onClick={e => openChat('What stands out in the latest observations?', e.currentTarget)}><span>Follow the thread. Ask a question.</span><ArrowRight size={16}/></button>
            </section>
          </div>
          <div className="lower-grid">
            <section className="panel signals-panel"><div className="panel-header"><div><div className="section-kicker">BEYOND THE TICKER</div><h2>Universal signals</h2></div><button className="text-button" onClick={() => setView('signals')}>Explore <ArrowUpRight size={14}/></button></div><SignalDials signal={data?.signals ?? null}/></section>
            <section className="panel correlation-panel"><div className="panel-header"><div><div className="section-kicker">MOVING TOGETHER?</div><h2>Correlation matrix</h2></div><Layers3 size={17} className="muted"/></div>
              <div className="correlation-controls"><div className="mini-tabs"><button aria-pressed={metric === 'price_r'} className={metric === 'price_r' ? 'active' : ''} onClick={() => setMetric('price_r')}>Price levels</button><button aria-pressed={metric === 'return_r'} className={metric === 'return_r' ? 'active' : ''} onClick={() => setMetric('return_r')}>Returns</button></div><span>Pearson r · {data?.range.toUpperCase() ?? '1W'}</span></div>
              <table className="matrix"><caption className="sr-only">{metric === 'price_r' ? 'Price level' : 'Log return'} correlations. Negative: opposing directions. Positive: moving together.</caption><thead><tr><th scope="col"><span className="sr-only">Commodity</span></th>{commodities.map(c => <th scope="col" key={c.key}>{c.name}<span>{c.ticker}</span></th>)}</tr></thead><tbody>{commodities.map((left, i) => <tr key={left.key}><th scope="row"><i style={{ background: left.color }}/>{left.name}</th>{commodities.map((right, j) => {
                const pair = data?.correlations.find(p => (p.left === left.key && p.right === right.key) || (p.right === left.key && p.left === right.key))
                const value = i === j ? (prices[left.key].length >= 12 ? 1 : null) : pair?.[metric] ?? null
                return <td key={right.key} className={i === j ? 'diagonal' : ''} title={pair ? `${metric === 'price_r' ? pair.samples : pair.return_samples} aligned observations` : 'Self correlation'}><div style={i === j || value === null ? undefined : { background: value >= 0 ? `rgba(194,174,127,${.05 + Math.abs(value) * .17})` : `rgba(134,164,193,${.06 + Math.abs(value) * .16})` }}>{value === null ? '—' : signed(value)}{i !== j && <span>{value === null ? 'collecting' : value > .3 ? 'together' : value < -.3 ? 'opposing' : 'weak'}</span>}</div></td>
              })}</tr>)}</tbody></table>
              <div className="matrix-scale"><span>−1 opposing</span><div/><span>+1 together</span></div><div className="correlation-foot"><Activity size={13}/>{data?.correlations[0]?.[metric === 'price_r' ? 'samples' : 'return_samples'] ?? 0} aligned observations · association ≠ causation</div>
            </section>
          </div>
          <div className="research-banner"><Telescope size={21} strokeWidth={1.4}/><div><h3>Patterns take time. Evidence takes longer.</h3><p>{data?.first_day_note ?? 'Live collection is starting. We will show what the evidence supports.'}</p></div><button onClick={() => setView('signals')}>View research notes <ArrowUpRight size={15}/></button></div>
        </>}
        {view === 'signals' && <div className="research-view"><section className="panel"><div className="panel-header"><div><div className="section-kicker">THREE PHYSICAL CONTEXTS</div><h2>Universal signals</h2></div><span className="small-label">Observed {stamp(data?.signals?.timestamp ?? null, true)}</span></div><SignalDials signal={data?.signals ?? null}/></section>
          <section className="panel research-notes"><div className="section-kicker">OBSERVATION WINDOW · {data?.collection_hours.toFixed(1) ?? '0.0'} HOURS</div><h2>The evidence, so far.</h2><p>{data?.first_day_note ?? 'Awaiting first observations.'}</p><p className="muted">Event thresholds: within 7 days of a solstice/equinox, Kp ≥ 5, or solar X-ray class M/X. Compare mean absolute one-hour price correlations in separate event and baseline windows. Five windows of each type are needed. No statistical significance or causal effect is implied.</p>
            <div className="comparison-scroll"><table className="comparison-table"><thead><tr><th>Physical context</th><th>Pair</th><th>Event windows</th><th>Baseline windows</th><th>Δ mean |r|</th></tr></thead><tbody>{data?.signal_tests.map(test => <tr key={`${test.signal}-${test.pair}`}><th scope="row">{test.signal}</th><td>{test.pair.replaceAll('coal_proxy', 'coal').replace(':', ' / ')}</td><td>{test.event_windows}</td><td>{test.baseline_windows}</td><td>{test.delta === null ? <span className="pending-label">Collecting</span> : signed(test.delta, 3)}</td></tr>)}</tbody></table></div>
            <h3 className="rolling-heading">Rolling relationships · 12 consecutive bars</h3><div className="rolling-grid">{data?.correlations.map(pair => <div key={pair.pair}><span>{pair.left.replace('_proxy', '')} / {pair.right.replace('_proxy', '')}</span><strong>{pair.rolling.length ? signed(pair.rolling.at(-1)![1]) : '—'}</strong><svg viewBox="0 0 280 65" role="img" aria-label={`${pair.pair} rolling one-hour price correlation`}><line x1="0" y1="32" x2="280" y2="32" stroke="#4a414d" strokeDasharray="2 4"/><path d={pair.rolling.map((p, i) => `${i ? 'L' : 'M'}${i / Math.max(1, pair.rolling.length - 1) * 280},${32 - p[1] * 28}`).join(' ')} fill="none" stroke="#cab3db" strokeWidth="1.5"/></svg><small>Latest window · {pair.rolling.length ? stamp(pair.rolling.at(-1)![0], true) : 'collecting'}</small></div>)}</div>
            {data?.signals?.flare_peak_class && <p className="event-note"><Radio size={16}/>Latest NOAA flare event peak: <strong>{data.signals.flare_peak_class}</strong> at {stamp(data.signals.flare_peak_timestamp, true)}. Separate from the current X-ray class.</p>}
          </section></div>}
        {view === 'methodology' && <div className="methodology-grid"><section className="panel prose-panel"><div className="section-kicker">HOW WE OBSERVE</div><h2>Transparent by design.</h2><p>fluxyz places market movements alongside physical, measurable signals. It asks whether relationships change together, while keeping observation separate from explanation.</p><h3>The market instruments</h3><p><strong>GLD</strong> is a gold ETF. <strong>USO</strong> is an oil futures ETF. <strong>BTU</strong> is Peabody Energy stock, a coal mining equity proxy. None is a live physical spot price. Company news, ETF construction, and futures roll effects can influence these instruments.</p><h3>The official coal reference</h3><p>The EIA reading is the monthly US electric power sector average cost of coal fuel receipts, in dollars per short ton. It is a lagged official reference, with its period shown explicitly. It is not interchangeable with BTU's share price.</p><h3>Measurement, without mythology</h3><p>{data?.methodology ?? 'Waiting for the analysis methodology from the API.'}</p><p>The seasonal dial shows the nearest equinox or solstice, using the Meeus astronomical approximation. Modern event timestamps are approximate to minutes. “Days from nearest solstice” is separately reported. NOAA Kp is a three-hour planetary index. Solar activity uses the current GOES X-ray class; the latest event peak is a separate reading.</p><h3>Timing & limitations</h3><p>Market polling runs every 10 minutes during NYSE trading hours, respecting holidays and early closes. An initial fetch loads available historical 5-minute bars. NOAA polls every 10 minutes; EIA at most once daily. Charts rebase each series to its first available close and compress non-trading gaps; timestamps use UTC. No prices or signals are simulated.</p><p>Signal history starts when this installation begins collecting. Historical prices alone cannot establish historical space-weather coincidences. Failed providers are identified alongside last successful timestamps. This is a single-node research demo.</p><a className="source-link" href="https://github.com/beechainfullstack/FLUXYZ" target="_blank" rel="noreferrer">Read the source and deployment guide <ExternalLink size={14}/></a></section>
          <section className="panel source-panel"><div className="section-kicker">DIRECT FROM THE SOURCE</div><h2>Collection health</h2><p>Provider failures remain visible. Last successful readings retain their original timestamps.</p><div className="source-list">{data?.sources.length ? data.sources.map(source => <div className="source-row" key={source.source}><div><i className={`status-dot ${source.status === 'error' ? 'warning' : ''}`}/><strong>{sourceNames[source.source] ?? source.source}</strong><span className={source.status === 'ok' ? 'source-ok' : 'source-error'}>{source.status === 'ok' ? 'Connected' : source.status}</span></div><p>{source.message}</p><span>Last success {stamp(source.last_success, true)}</span></div>) : <p>No source statuses available yet.</p>}</div><div className="source-disclaimer"><Database size={18}/><p>Stored in open-source StarRocks.<br/>Provider keys stay on the backend.</p></div></section>
        </div>}
        <footer className="footer"><span className="footer-brand">fluxyz<span>Stay curious. Stay grounded.</span></span><span>Correlation is an observation. Causation is a different question.</span><button onClick={() => setView('methodology')}>Data & methodology <ChevronRight size={13}/></button></footer>
        {loading && !data && <div className="loading-status" role="status"><LoaderCircle size={15} className="spin"/>Opening the observatory…</div>}
      </main>
    </div>
    {chatQuestion !== null && <Chat range={range} initialQuestion={chatQuestion} close={() => { setChatQuestion(null); chatTrigger.current?.focus() }}/>}
  </>
}
