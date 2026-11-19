import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { ArrowUpRight, MessageCircle, ShieldCheck } from 'lucide-react';
import type { Reactions } from './types';
import { BalanceBar } from './charts';

export const number = (n: number) => new Intl.NumberFormat().format(n);
export const compact = (n: number) => new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(n);
export const percent = (n: number | null) => n === null ? 'No prior baseline' : `${n > 0 ? '+' : ''}${n}%`;
export const date = (s: string | null) => s ? new Date(s + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'No history';
export const shortDate = (s: string) => new Date(s + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
export const hourLabel = (h: number) => new Date(2001, 0, 1, h).toLocaleTimeString(undefined, { hour: 'numeric' });

export function reducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/** Eases a number up from zero once per value change. */
export function useCountUp(value: number, duration = 900) {
  const [shown, setShown] = useState(() => reducedMotion() ? value : 0);
  const from = useRef(0);
  useEffect(() => {
    if (reducedMotion()) { setShown(value); return; }
    const start = performance.now();
    const origin = from.current;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
      const next = Math.round(origin + (value - origin) * eased);
      from.current = next;
      setShown(next);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);
  return shown;
}

export function CountUp({ value, format = number }: { value: number; format?: (n: number) => string }) {
  const shown = useCountUp(value);
  return <span className="count-up" aria-label={format(value)}><span aria-hidden="true">{format(shown)}</span></span>;
}

export function Avatar({ name, size = 'normal' }: { name: string; size?: 'small' | 'normal' | 'large' | 'xl' }) {
  const unknown = /^[+\d(]/.test(name) || name.includes('@');
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase();
  return <span className={`avatar ${size}`} aria-hidden="true">
    {unknown ? <svg viewBox="0 0 24 24" className="avatar-silhouette"><circle cx="12" cy="9" r="4.2" /><path d="M3.6 21.5c1.2-4.3 4.5-6.6 8.4-6.6s7.2 2.3 8.4 6.6" /></svg> : initials}
  </span>;
}

type BubbleProps = { from?: 'me' | 'them'; tail?: boolean; index?: number; status?: string; className?: string; children: ReactNode };

/** An iMessage bubble. Consecutive bubbles stack; only the last of a run gets a tail. */
export function Bubble({ from = 'them', tail = true, index = 0, status, className = '', children }: BubbleProps) {
  return <div className={`bubble-row ${from}`} style={{ '--i': index } as CSSProperties}>
    <div className={`bubble ${from} ${tail ? 'tailed' : ''} ${className}`}>
      {children}
      {tail && <svg className="tail" viewBox="-10 0 22 20" aria-hidden="true"><path d="M-10 0H0C0 8 3 15 12 20C6 20.6 1.5 19.3-1.5 17.5-4 19.5-7 20-10 20Z" /></svg>}
    </div>
    {status && <span className="bubble-status">{status}</span>}
  </div>;
}

export function Typing({ index = 0 }: { index?: number }) {
  return <div className="bubble-row them" style={{ '--i': index } as CSSProperties} aria-label="Typing">
    <div className="bubble them typing tailed"><i /><i /><i />
      <svg className="tail" viewBox="-10 0 22 20" aria-hidden="true"><path d="M-10 0H0C0 8 3 15 12 20C6 20.6 1.5 19.3-1.5 17.5-4 19.5-7 20-10 20Z" /></svg>
    </div>
  </div>;
}

export function Stamp({ children }: { children: ReactNode }) {
  return <div className="thread-stamp">{children}</div>;
}

export function Metric({ label, value, note, format }: { label: string; value: number | string; note?: string; format?: (n: number) => string }) {
  return <div className="metric">
    <span>{label}</span>
    <strong>{typeof value === 'number' ? <CountUp value={value} format={format} /> : value}</strong>
    {note && <small>{note}</small>}
  </div>;
}

export function Highlight({ icon, label, value, note }: { icon: string; label: string; value: ReactNode; note?: string }) {
  return <div className="highlight">
    <span className="highlight-icon" aria-hidden="true">{icon}</span>
    <div><small>{label}</small><strong>{value}</strong>{note && <span>{note}</span>}</div>
  </div>;
}

export function Empty({ title, body }: { title: string; body: string }) {
  return <div className="empty"><span className="empty-icon"><MessageCircle size={26} /></span><h3>{title}</h3><p>{body}</p></div>;
}

export function Loading({ text = 'Reading your local history…' }: { text?: string }) {
  return <div className="loading" role="status">
    <div className="thread loading-thread" aria-hidden="true">
      <div className="bubble-row them"><div className="bubble them skeleton" style={{ width: 180 }} /></div>
      <div className="bubble-row me"><div className="bubble me skeleton" style={{ width: 120 }} /></div>
      <Typing />
    </div>
    <span>{text}</span>
  </div>;
}

export function Privacy() {
  return <div className="privacy"><ShieldCheck size={14} /><span>On your Mac. Read-only. No uploads.</span></div>;
}

export function PersonLink({ name, onClick }: { name: string; onClick: () => void }) {
  return <button className="person-link" onClick={onClick}>{name}<ArrowUpRight size={14} /></button>;
}

export function ReactionPanel({ data }: { data: Reactions }) {
  const sent = data.items.reduce((a, r) => a + r.sent, 0);
  const received = data.total - sent;
  const tapbacks = data.items.filter(r => r.label !== 'Custom emoji');
  const custom = data.items.filter(r => r.label === 'Custom emoji');
  return <>
    <div className="section-title">
      <div><h2>A little reaction goes a long way.</h2><p>Actual Tapbacks from your message history.</p></div>
      <span className="pill">{compact(data.total)} added</span>
    </div>
    {data.items.length ? <>
      <BalanceBar left={sent} right={received} leftLabel="You gave" rightLabel="You got" />
      <div className="reaction-grid">
        {tapbacks.map((r, i) => <div className="reaction" key={r.emoji + r.label} style={{ '--i': i } as CSSProperties}>
          <div className="reaction-bubble">
            <span className="tapback-badge"><span>{r.emoji}</span></span>
            <span className="reaction-lines" aria-hidden="true"><i /><i /></span>
          </div>
          <strong><CountUp value={r.count} /></strong>
          <span>{r.label}</span>
          <div className="mini-split" title={`${number(r.sent)} from you · ${number(r.received)} to you`}>
            <i className="sent" style={{ flexGrow: r.sent || 0.0001 }} /><i className="received" style={{ flexGrow: r.received || 0.0001 }} />
          </div>
          <small>{number(r.sent)} from you · {number(r.received)} to you</small>
        </div>)}
      </div>
      {custom.length > 0 && <div className="custom-reactions">
        <h3>Custom emoji Tapbacks <span>{number(custom.reduce((a, r) => a + r.count, 0))}</span></h3>
        <div className="emoji-chips">{custom.map((r, i) => <span key={r.emoji} className="emoji-chip" style={{ '--i': i } as CSSProperties} title={`${number(r.sent)} from you · ${number(r.received)} to you`}><b>{r.emoji}</b>{number(r.count)}</span>)}</div>
      </div>}
    </> : <Empty title="No Tapbacks in this period" body="Choose another year to explore reactions." />}
    <p className="method">{data.method} {number(data.removed)} removal events; {number(data.other_events)} other associated events excluded.</p>
  </>;
}
