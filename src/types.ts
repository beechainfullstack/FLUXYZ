export type Commodity = 'gold' | 'oil' | 'coal_proxy'
export type WindowRange = '1d' | '1w' | '1m'
export interface Price { commodity: Commodity; timestamp: string; price: number; volume: number | null; source: string }
export interface Pair {
  pair: string; left: Commodity; right: Commodity; price_r: number | null; return_r: number | null
  samples: number; return_samples: number; previous_price_r: number | null; rolling: [string, number][]
}
export interface Signal {
  timestamp: string; days_to_solstice: number; days_to_event: number; nearest_event: string; event_timestamp: string
  kp_index: number | null; kp_timestamp: string | null; solar_flare_class: string | null; solar_timestamp: string | null
  flare_peak_class: string | null; flare_peak_timestamp: string | null
}
export interface Source {
  source: string; status: 'pending' | 'ok' | 'error'; last_attempt: string | null; last_success: string | null; message: string
}
export interface Dashboard {
  generated_at: string; range: WindowRange; market_open: boolean
  prices: Record<Commodity, Price[]>; correlations: Pair[]
  signal_tests: { signal: string; pair: string; event_windows: number; baseline_windows: number; event_mean_abs_r: number | null; baseline_mean_abs_r: number | null; delta: number | null; status: string }[]
  signals: Signal | null
  coal_reference: { price: number; period: string; units: string; description: string; timestamp: string } | null
  observations: { id: string; timestamp: string; text: string; model: string; kind: string }[]
  sources: Source[]
  first_observation_at: string | null; collection_hours: number; first_day_note: string; methodology: string
}
export const commodities: { key: Commodity; name: string; ticker: string; color: string; note: string }[] = [
  { key: 'gold', name: 'Gold', ticker: 'GLD', color: '#d4ba79', note: 'Gold ETF proxy' },
  { key: 'oil', name: 'Oil', ticker: 'USO', color: '#94b8d4', note: 'Oil ETF proxy' },
  { key: 'coal_proxy', name: 'Coal', ticker: 'BTU', color: '#c3c5ce', note: 'Coal mining equity proxy' },
]
export const API = import.meta.env.VITE_API_URL?.replace(/\/$/, '') ?? ''
export const money = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
export const stamp = (value: string | null, date = false) => value
  ? new Date(value).toLocaleString('en-GB', {
    ...(date ? { month: 'short', day: '2-digit' } : {}),
    hour: '2-digit', minute: '2-digit', timeZone: 'UTC', hour12: false,
  }) + ' UTC' : 'Not available'
export const signed = (value: number, digits = 2) => `${value > 0 ? '+' : ''}${value.toFixed(digits)}`
