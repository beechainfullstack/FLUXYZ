import { ArrowUpRight, Orbit, Radio, Sun } from 'lucide-react'
import type { Signal } from './types'
import { stamp } from './types'

export function SignalDials({ signal }: { signal: Signal | null }) {
  const kp = signal?.kp_index ?? null, angle = (-180 + ((kp ?? 0) / 9) * 180) * Math.PI / 180
  const eventPassed = signal ? new Date(signal.event_timestamp) < new Date(signal.timestamp) : false
  return <div className="signal-grid">
    <article className="signal-card">
      <div className="signal-label"><Orbit size={15}/><h3>Seasonal cycle</h3><span>01</span></div>
      <div className="dial"><svg viewBox="0 0 160 132" aria-hidden="true">
        <circle cx="80" cy="65" r="48" fill="none" stroke="#38353c"/><circle cx="80" cy="65" r="39" fill="none" stroke="#434049" strokeDasharray="1 5"/>
        <ellipse cx="80" cy="65" rx="64" ry="21" transform="rotate(-32 80 65)" fill="none" stroke="#6f6576"/>
        <path d="M80 12v10m0 86v10M27 65h10m86 0h10" stroke="#a2a1af"/><circle cx="126" cy="37" r="4" fill="#d0bf9c"/>
        <circle cx="80" cy="65" r="24" fill="#13141b"/><path d="M80 47v36M62 65h36M68 53l24 24m0-24L68 77" stroke="#baab8c"/>
        <circle cx="80" cy="65" r="8" fill="#d0bf9c"/>
      </svg></div>
      <div className="signal-value">{signal ? signal.days_to_event.toFixed(1) : '—'}<span>days</span></div>
      <p>{signal?.nearest_event ?? 'Nearest seasonal event'}{signal ? eventPassed ? ' · elapsed' : ' · approaching' : ''}</p>
      <div className="signal-foot">Solstice or equinox <ArrowUpRight size={12}/></div>
      <span className="signal-detail">{signal ? `${signal.days_to_solstice.toFixed(1)} days from nearest solstice` : 'Calculated locally'}</span>
    </article>
    <article className="signal-card">
      <div className="signal-label"><Radio size={15}/><h3>Geomagnetic field</h3><span>02</span></div>
      <div className="dial"><svg viewBox="0 0 150 132" aria-hidden="true">
        <path d="M20 80 A55 55 0 0 1 130 80" fill="none" stroke="#43404d" strokeWidth="7" strokeDasharray="1 6"/>
        <path d="M20 80 A55 55 0 0 1 84.6 25.8" fill="none" stroke="#8fa9bd" strokeWidth="7" strokeDasharray="1 6"/>
        {[0, 3, 6, 9].map(n => { const a = (-180 + n / 9 * 180) * Math.PI / 180
          return <text key={n} x={75 + 68 * Math.cos(a)} y={83 + 68 * Math.sin(a)} textAnchor="middle" className="dial-number">{n}</text> })}
        {kp !== null && <><line x1="75" y1="80" x2={75 + 44 * Math.cos(angle)} y2={80 + 44 * Math.sin(angle)} stroke="#c7d6e2" strokeWidth="2"/><circle cx="75" cy="80" r="5" fill="#c7d6e2"/></>}
        <text x="75" y="115" textAnchor="middle" className="dial-caption">PLANETARY Kp</text>
      </svg></div>
      <div className="signal-value">{kp === null ? '—' : kp.toFixed(2)}<span>/ 9</span></div>
      <p>{kp === null ? 'Reading unavailable' : kp >= 5 ? 'Elevated · storm threshold' : kp >= 4 ? 'Active geomagnetic field' : 'Quiet geomagnetic field'}</p>
      <div className="signal-foot">NOAA SWPC <span>3-hour index</span></div><span className="signal-detail">{stamp(signal?.kp_timestamp ?? null)}</span>
    </article>
    <article className="signal-card">
      <div className="signal-label"><Sun size={15}/><h3>Solar activity</h3><span>03</span></div>
      <div className="dial"><svg viewBox="0 0 160 132" aria-hidden="true">
        <circle cx="80" cy="65" r="51" fill="none" stroke="#45404b" strokeDasharray="1 6"/><circle cx="80" cy="65" r="40" fill="none" stroke="#48404f"/>
        {Array.from({ length: 24 }, (_, i) => { const a = i * Math.PI / 12
          return <line key={i} x1={80 + 28 * Math.cos(a)} y1={65 + 28 * Math.sin(a)} x2={80 + (i % 3 === 0 ? 36 : 32) * Math.cos(a)} y2={65 + (i % 3 === 0 ? 36 : 32) * Math.sin(a)} stroke="#acabb8"/> })}
        <circle cx="80" cy="65" r="21" fill="#27202d" stroke="#c4bac8"/><path d="M73 70l7-14-2 10h9L77 78l3-8z" fill="#d5c8d7"/>
      </svg></div>
      <div className="signal-value">{signal?.solar_flare_class ?? '—'}<span>class</span></div><p>Current solar X-ray level</p>
      <div className="signal-foot">NOAA GOES <span>0.1–0.8 nm</span></div><span className="signal-detail">{stamp(signal?.solar_timestamp ?? null)}</span>
    </article>
  </div>
}
