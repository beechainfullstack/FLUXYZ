import { useEffect, useRef, useState } from 'react'
import type { Commodity, Price } from './types'
import { commodities, money, signed, stamp } from './types'

const H = 260, L = 50, R = 22, T = 20, B = 32

export function MarketChart({ prices }: { prices: Record<Commodity, Price[]> }) {
  const [cursor, setCursor] = useState<number | null>(null)
  const [width, setWidth] = useState(700)
  const wrapper = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!wrapper.current) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(wrapper.current)
    return () => observer.disconnect()
  }, [])
  const W = Math.max(200, width)
  const times = [...new Set(Object.values(prices).flat().map(p => p.timestamp))].sort()
  const indices = new Map(times.map((time, i) => [time, i]))
  const series = commodities.map(c => ({ ...c, points: prices[c.key].map(p => ({
    ...p, value: (p.price / prices[c.key][0].price - 1) * 100,
  })) }))
  const values = series.flatMap(s => s.points.map(p => p.value))
  const low = Math.min(-0.1, ...values), high = Math.max(0.1, ...values)
  const padding = (high - low) * 0.15, min = low - padding, max = high + padding
  const x = (i: number) => L + (i / Math.max(1, times.length - 1)) * (W - L - R)
  const y = (value: number) => T + ((max - value) / (max - min)) * (H - T - B)
  const active = cursor === null ? null : Math.min(cursor, times.length - 1)
  return <div ref={wrapper} className="chart-wrap" tabIndex={0} role="group"
    aria-label="Price performance chart. Use left and right arrow keys to inspect observations."
    onKeyDown={e => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault()
        setCursor(Math.max(0, Math.min(times.length - 1, (cursor ?? times.length - 1) + (e.key === 'ArrowLeft' ? -1 : 1))))
      }
      if (e.key === 'Escape') setCursor(null)
    }} onMouseLeave={() => setCursor(null)}>
    {!times.length ? <div className="chart-empty">Awaiting market observations. No simulated prices.</div> : <>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Gold, oil and coal proxy percentage change"
      onMouseMove={e => {
        const rect = e.currentTarget.getBoundingClientRect()
        setCursor(Math.max(0, Math.min(times.length - 1, Math.round((((e.clientX - rect.left) / rect.width) * W - L) / (W - L - R) * (times.length - 1)))))
      }}>
      {Array.from({ length: 5 }, (_, i) => {
        const v = min + (max - min) * i / 4
        return <g key={i}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#292b32" strokeDasharray="3 5"/>
          <text x={L - 12} y={y(v) + 4} textAnchor="end" className="axis">{signed(v, 1)}%</text></g>
      })}
      <line x1={L} x2={W - R} y1={y(0)} y2={y(0)} stroke="#555760" strokeDasharray="2 5"/>
      {series.map((s, i) => <path key={s.key} d={s.points.map((p, j) => `${j === 0 ? 'M' : 'L'}${x(indices.get(p.timestamp) ?? 0).toFixed(1)},${y(p.value).toFixed(1)}`).join(' ')}
        fill="none" stroke={s.color} strokeWidth={i === 0 ? 2.4 : 1.8} strokeLinejoin="round" strokeLinecap="round" strokeDasharray={i === 2 ? '5 3' : undefined}/>)}
      {(W < 420 ? [0, .5, 1] : [0, .25, .5, .75, 1]).map(f => {
        const i = Math.round(f * (times.length - 1))
        return <text key={f} x={x(i)} y={H - 5} textAnchor={f === 0 ? 'start' : f === 1 ? 'end' : 'middle'} className="axis">
          {new Date(times[i]).toLocaleDateString('en-GB', { month: 'short', day: 'numeric', timeZone: 'UTC' })}
        </text>
      })}
      {active !== null && <g><line x1={x(active)} x2={x(active)} y1={T} y2={H - B} stroke="#a7a9b2" strokeDasharray="3 4"/>
        {series.map(s => {
          const p = s.points.find(p => p.timestamp === times[active])
          return p ? <circle key={s.key} cx={x(active)} cy={y(p.value)} r="4" fill={s.color} stroke="#0b0c10" strokeWidth="2"/> : null
        })}</g>}
    </svg>
    {active !== null && <div className="chart-tooltip" aria-live="polite"><span>{stamp(times[active], true)}</span>
      {series.map(s => {
        const p = s.points.find(p => p.timestamp === times[active])
        return <span key={s.key}><i style={{ background: s.color }}/>{s.ticker} {p ? `${money(p.price)} (${signed(p.value)}%)` : 'No matching bar'}</span>
      })}
    </div>}</>}
  </div>
}

export function Sparkline({ rows, color }: { rows: Price[]; color: string }) {
  if (rows.length < 2) return <div className="spark-empty">Collecting history</div>
  const min = Math.min(...rows.map(p => p.price)), max = Math.max(...rows.map(p => p.price))
  const path = rows.map((p, i) => `${i === 0 ? 'M' : 'L'}${(i / (rows.length - 1) * 250).toFixed(1)},${(42 - ((p.price - min) / (max - min || 1)) * 34).toFixed(1)}`).join(' ')
  return <svg className="sparkline" viewBox="0 0 250 50" role="img" aria-label={`Price history from ${money(rows[0].price)} to ${money(rows[rows.length - 1].price)}`}>
    <path d={path} fill="none" stroke={color} strokeWidth="1.7" strokeLinejoin="round"/>
  </svg>
}
