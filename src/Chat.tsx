import { ArrowUp, CornerDownLeft, LoaderCircle, Sparkles, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { WindowRange } from './types'
import { API, stamp } from './types'

interface Message { id: number; role: 'user' | 'agent'; text: string; timestamp?: string }
export function Chat({ close, range, initialQuestion }: { close: () => void; range: WindowRange; initialQuestion: string }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState(initialQuestion)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const ref = useRef<HTMLDialogElement>(null), bottom = useRef<HTMLDivElement>(null), inputRef = useRef<HTMLTextAreaElement>(null)
  useEffect(() => { ref.current?.showModal(); inputRef.current?.focus() }, [])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy, error])
  async function send() {
    const question = input.trim()
    if (question.length < 3 || busy) return
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', text: question }])
    setInput(''); setBusy(true); setError('')
    try {
      const response = await fetch(`${API}/api/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, range }), signal: AbortSignal.timeout(90000),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'The agent could not answer. Please retry.')
      setMessages(prev => [...prev, { id: Date.now(), role: 'agent', text: result.answer, timestamp: result.grounded_at }])
    } catch (e) { setError(e instanceof Error ? e.message : 'The connection failed. Please retry.'); setInput(question) }
    finally { setBusy(false) }
  }
  return <dialog ref={ref} className="chat-dialog" onCancel={e => { e.preventDefault(); close() }}
    onClick={e => { if (e.target === e.currentTarget) close() }} aria-labelledby="chat-title">
    <div className="chat-shell"><header className="chat-header"><div className="agent-icon"><Sparkles size={20}/></div><div><h2 id="chat-title">Ask the observatory</h2><p>Gemini Flash · grounded in StarRocks</p></div><button className="icon-button" onClick={close} aria-label="Close chat"><X size={19}/></button></header>
      <div className="chat-messages" aria-live="polite" aria-relevant="additions">
        {!messages.length && <div className="chat-intro"><div className="orbit-mark">✧</div><h3>A question is a good place to begin.</h3><p>Explore the relationships in the data. I can compare markets, examine measured signals, and tell you where the evidence ends.</p>
          {['How correlated are gold and coal this week?', 'Was there a solar flare during the largest oil move?', 'What can we conclude from the data so far?'].map(q => <button key={q} className="suggestion" onClick={() => { setInput(q); inputRef.current?.focus() }}>{q}<CornerDownLeft size={14}/></button>)}</div>}
        {messages.map(m => <article className={`chat-message ${m.role}`} key={m.id}><div className="message-label">{m.role === 'user' ? 'YOU' : 'FLUXYZ AGENT'}{m.timestamp && <span>{stamp(m.timestamp, true)}</span>}</div><p>{m.text}</p></article>)}
        {busy && <div className="thinking"><LoaderCircle size={15} className="spin"/>Reading the stored observations…</div>}
        {error && <p className="chat-error" role="alert">{error}</p>}<div ref={bottom}/>
      </div>
      <form className="chat-form" onSubmit={e => { e.preventDefault(); void send() }}>
        <label className="sr-only" htmlFor="chat-question">Ask a question about the data</label>
        <textarea ref={inputRef} id="chat-question" placeholder="What would you like to explore?" value={input} maxLength={1200} rows={2} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send() } }}/>
        <button className="send-button" type="submit" disabled={busy || input.trim().length < 3} aria-label="Send question"><ArrowUp size={20}/></button>
      </form><div className="chat-disclaimer">Selected window: {range.toUpperCase()} · Observations, not causation or financial advice.</div>
    </div>
  </dialog>
}
