import { useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import type { Point } from './types';
import { compact, hourLabel, number, date } from './components';

/* ---------- shared plumbing ---------- */

function useWidth<T extends HTMLElement>(fallback = 640) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.clientWidth || fallback);
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width || fallback));
    observer.observe(el);
    return () => observer.disconnect();
  }, [fallback]);
  return [ref, width] as const;
}

type Tip = { x: number; y: number; content: ReactNode } | null;

function useTip() {
  const [tip, setTip] = useState<Tip>(null);
  return {
    tip,
    show: (e: { clientX: number; clientY: number }, content: ReactNode) => setTip({ x: e.clientX, y: e.clientY, content }),
    hide: () => setTip(null),
  };
}

function ChartTip({ tip }: { tip: Tip }) {
  if (!tip) return null;
  const x = Math.min(Math.max(tip.x, 100), window.innerWidth - 100);
  return <div className="chart-tip" style={{ left: x, top: tip.y }} role="presentation">{tip.content}</div>;
}

function niceStep(max: number, count = 3) {
  const raw = Math.max(1, max) / count;
  const power = 10 ** Math.floor(Math.log10(raw));
  const unit = [1, 2, 2.5, 5, 10].find(u => u * power >= raw) ?? 10;
  return unit * power;
}

function roundedTop(x: number, y: number, w: number, h: number, r: number) {
  r = Math.min(r, w / 2, h);
  return `M${x} ${y + h}V${y + r}Q${x} ${y} ${x + r} ${y}H${x + w - r}Q${x + w} ${y} ${x + w} ${y + r}V${y + h}Z`;
}

const Swatch = ({ kind }: { kind: string }) => <i className={`swatch ${kind}`} />;

/** Spreads label positions apart so text never overlaps. */
function spread(ys: number[], gap: number, min: number, max: number) {
  const order = ys.map((y, i) => ({ y, i })).sort((a, b) => a.y - b.y);
  for (let k = 1; k < order.length; k++) order[k].y = Math.max(order[k].y, order[k - 1].y + gap);
  const overflow = order.length ? order[order.length - 1].y - max : 0;
  if (overflow > 0) for (const o of order) o.y -= overflow;
  for (let k = 0; k < order.length; k++) order[k].y = Math.max(order[k].y, k ? order[k - 1].y + gap : min);
  const out = [...ys];
  for (const o of order) out[o.i] = o.y;
  return out;
}

/* ---------- monthly sent/received bars ---------- */

type Bin = { key: string; label: string; tick: string | null; sent: number; received: number };

function toBins(points: Point[]): Bin[] {
  let pts = points;
  if (pts.length > 12) {
    let a = 0, b = pts.length - 1;
    while (a < b && !(pts[a].sent + pts[a].received)) a++;
    while (b > a && !(pts[b].sent + pts[b].received)) b--;
    pts = pts.slice(a, b + 1);
  }
  const monthName = (p: string, style: 'short' | 'narrow') => new Date(+p.slice(0, 4), +p.slice(5, 7) - 1, 1).toLocaleDateString(undefined, { month: style });
  if (pts.length > 36) {
    const quarters = new Map<string, Bin>();
    for (const p of pts) {
      const q = Math.floor((+p.period.slice(5, 7) - 1) / 3) + 1;
      const key = `${p.period.slice(0, 4)}-Q${q}`;
      const bin = quarters.get(key) ?? { key, label: `Q${q} ${p.period.slice(0, 4)}`, tick: q === 1 ? p.period.slice(0, 4) : null, sent: 0, received: 0 };
      bin.sent += p.sent;
      bin.received += p.received;
      quarters.set(key, bin);
    }
    return [...quarters.values()];
  }
  const multiYear = pts.length > 12;
  return pts.map(p => ({
    key: p.period,
    label: `${monthName(p.period, 'short')} ${p.period.slice(0, 4)}`,
    tick: multiYear ? (p.period.endsWith('-01') ? p.period.slice(0, 4) : null) : monthName(p.period, 'narrow'),
    sent: p.sent,
    received: p.received,
  }));
}

export function Timeline({ points, label = 'Message activity' }: { points: Point[]; label?: string }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const { tip, show, hide } = useTip();
  const [active, setActive] = useState<number | null>(null);
  const bins = useMemo(() => toBins(points), [points]);
  const height = 190, top = 10, bottom = 22, left = 38;
  const inner = { w: Math.max(10, width - left), h: height - top - bottom };
  const max = Math.max(1, ...bins.map(b => b.sent + b.received));
  const step = niceStep(max);
  const ceiling = Math.ceil(max / step) * step;
  const band = inner.w / Math.max(1, bins.length);
  const gap = band > 8 ? 2 : band > 4 ? 1 : 0;
  const barW = Math.max(1, band - gap);
  const y = (v: number) => inner.h * (v / ceiling);
  const ticks = bins.map((b, i) => ({ b, i })).filter(t => t.b.tick);
  const thin = ticks.length > 10 ? Math.ceil(ticks.length / 8) : 1;
  const quarterly = bins[0]?.key.includes('Q');

  return <div className="chart-block" ref={ref}>
    <div className="chart-legend" aria-hidden="true">
      <span><Swatch kind="sent" /> You sent</span>
      <span><Swatch kind="received" /> You received</span>
      {quarterly && <span className="legend-note">Quarterly totals</span>}
    </div>
    <svg className="chart" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${label}. ${bins.length} ${quarterly ? 'quarters' : 'months'}. Exact values in the table below.`} onMouseLeave={() => { hide(); setActive(null); }}>
      {[0, 1, 2, 3].map(k => k * step).filter(v => v <= ceiling).map(v => <g key={v} className="grid">
        <line x1={left} x2={width} y1={top + inner.h - y(v)} y2={top + inner.h - y(v)} />
        <text x={left - 8} y={top + inner.h - y(v)} dy="0.32em" textAnchor="end">{compact(v)}</text>
      </g>)}
      {bins.map((b, i) => {
        const x = left + i * band + gap / 2;
        const hs = y(b.sent), hr = y(b.received);
        const split = hs > 0 && hr > 0 && hs + hr > 6 ? 2 : 0;
        const base = top + inner.h;
        return <g key={b.key} className={`bar ${active !== null && active !== i ? 'dim' : ''}`} style={{ '--i': Math.min(i, 60) } as CSSProperties}>
          {hs > 0 && <path className="sent" d={hr > 0 ? `M${x} ${base}V${base - hs}H${x + barW}V${base}Z` : roundedTop(x, base - hs, barW, hs, 4)} />}
          {hr > 0 && <path className="received" d={roundedTop(x, base - hs - hr, barW, Math.max(0.5, hr - split), 4)} />}
          <rect className="hit" x={left + i * band} y={top} width={band} height={inner.h}
            onMouseMove={e => { setActive(i); show(e, <><strong>{b.label}</strong><span><Swatch kind="sent" />{number(b.sent)} sent</span><span><Swatch kind="received" />{number(b.received)} received</span></>); }} />
        </g>;
      })}
      <line className="baseline" x1={left} x2={width} y1={top + inner.h} y2={top + inner.h} />
      {ticks.filter((_, k) => k % thin === 0).map(({ b, i }) => <text key={b.key} className="tick" x={left + i * band + band / 2} y={height - 4} textAnchor={quarterly || bins.length > 12 ? 'start' : 'middle'}>{b.tick}</text>)}
    </svg>
    <ChartTip tip={tip} />
    <details className="chart-table"><summary>View {quarterly ? 'quarterly' : 'monthly'} numbers</summary>
      <div className="table-scroll"><table><thead><tr><th>{quarterly ? 'Quarter' : 'Month'}</th><th>Sent</th><th>Received</th></tr></thead>
        <tbody>{bins.map(b => <tr key={b.key}><td>{b.label}</td><td>{number(b.sent)}</td><td>{number(b.received)}</td></tr>)}</tbody></table></div>
    </details>
  </div>;
}

/* ---------- weekday × hour heatmap ---------- */

const weekdays = [1, 2, 3, 4, 5, 6, 0].map(d => new Date(2023, 0, d + 1).toLocaleDateString(undefined, { weekday: 'short' }));
const weekdaysLong = [1, 2, 3, 4, 5, 6, 0].map(d => new Date(2023, 0, d + 1).toLocaleDateString(undefined, { weekday: 'long' }));

function seq(v: number) {
  return v <= 0 ? 'var(--cell-empty)' : `color-mix(in oklab, var(--seq-hi) ${Math.round(15 + Math.sqrt(v) * 85)}%, var(--seq-lo))`;
}

export function rhythmPeak(grid: number[][]) {
  let best = { day: 0, hour: 0, count: -1 };
  grid.forEach((row, d) => row.forEach((count, hour) => { if (count > best.count) best = { day: d, hour, count }; }));
  return best.count > 0 ? { ...best, dayName: weekdaysLong[best.day] } : null;
}

export function Heatmap({ grid, compactMode = false }: { grid: number[][]; compactMode?: boolean }) {
  const { tip, show, hide } = useTip();
  const max = Math.max(1, ...grid.flat());
  const peak = rhythmPeak(grid);
  const totals = grid.map(row => row.reduce((a, b) => a + b, 0));
  return <div className={`heatmap-block ${compactMode ? 'compact' : ''}`}>
    <div className="heatmap" role="img" aria-label={peak ? `Messages by weekday and hour. Busiest: ${peak.dayName} at ${hourLabel(peak.hour)}.` : 'No messages in this period.'} onMouseLeave={hide}>
      {grid.map((row, d) => <div className="heat-row" key={d}>
        <span className="heat-day">{weekdays[d]}</span>
        {row.map((count, h) => <span key={h} className={`heat-cell ${peak && peak.day === d && peak.hour === h ? 'peak' : ''}`}
          style={{ background: seq(count / max), '--d': d + h } as CSSProperties}
          onMouseMove={e => show(e, <><strong>{weekdaysLong[d]}, {hourLabel(h)}</strong><span>{number(count)} messages</span></>)} />)}
      </div>)}
      <div className="heat-row hours" aria-hidden="true"><span className="heat-day" />
        {Array.from({ length: 24 }, (_, h) => <span key={h} className="heat-hour">{h % 6 === 0 ? hourLabel(h).replace(/\s?([AP])M/i, (_, x: string) => x.toLowerCase()) : ''}</span>)}
      </div>
    </div>
    <div className="heat-legend" aria-hidden="true"><span>Less</span>{[0, 0.15, 0.35, 0.6, 1].map(v => <i key={v} style={{ background: v ? seq(v) : 'var(--cell-empty)' }} />)}<span>More</span></div>
    <ChartTip tip={tip} />
    {!compactMode && <details className="chart-table"><summary>View by weekday</summary>
      <div className="table-scroll"><table><thead><tr><th>Day</th><th>Messages</th><th>Busiest hour</th></tr></thead>
        <tbody>{grid.map((row, d) => <tr key={d}><td>{weekdaysLong[d]}</td><td>{number(totals[d])}</td><td>{totals[d] ? hourLabel(row.indexOf(Math.max(...row))) : '—'}</td></tr>)}</tbody></table></div>
    </details>}
  </div>;
}

/* ---------- calendar year ---------- */

export function CalendarHeatmap({ year, days, highlight }: { year: number; days: Record<string, number>; highlight?: string | null }) {
  const { tip, show, hide } = useTip();
  const cell = 11, gap = 2, left = 26, top = 16;
  const jan1 = new Date(year, 0, 1);
  const offset = (jan1.getDay() + 6) % 7;
  const max = Math.max(1, ...Object.values(days));
  const cells: { key: string; x: number; y: number; count: number }[] = [];
  const months: { x: number; label: string }[] = [];
  for (let d = new Date(jan1); d.getFullYear() === year; d.setDate(d.getDate() + 1)) {
    const index = Math.round((d.getTime() - jan1.getTime()) / 86400000) + offset;
    const week = Math.floor(index / 7);
    const key = `${year}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    if (d.getDate() === 1) months.push({ x: left + week * (cell + gap), label: d.toLocaleDateString(undefined, { month: 'short' }) });
    cells.push({ key, x: left + week * (cell + gap), y: top + (index % 7) * (cell + gap), count: days[key] ?? 0 });
  }
  const width = left + 54 * (cell + gap), height = top + 7 * (cell + gap);
  return <div className="calendar-block">
    <svg className="chart calendar" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Daily messages in ${year}.`} onMouseLeave={hide}>
      {months.map(m => <text key={m.label} className="tick" x={m.x} y={10}>{m.label}</text>)}
      {[0, 2, 4].map(d => <text key={d} className="tick" x={0} y={top + d * (cell + gap) + cell - 2}>{weekdays[d].slice(0, 3)}</text>)}
      {cells.map((c, i) => <rect key={c.key} className={`cal-cell ${c.key === highlight ? 'peak' : ''}`} x={c.x} y={c.y} width={cell} height={cell} rx={2.5}
        style={{ fill: seq(c.count / max), '--d': Math.floor(i / 7) } as CSSProperties}
        onMouseMove={e => show(e, <><strong>{date(c.key)}</strong><span>{number(c.count)} messages</span></>)} />)}
    </svg>
    <ChartTip tip={tip} />
  </div>;
}

/* ---------- small pieces ---------- */

export function BalanceBar({ left, right, leftLabel, rightLabel }: { left: number; right: number; leftLabel: string; rightLabel: string }) {
  const total = left + right;
  const share = total ? Math.round(left / total * 100) : 50;
  return <div className="balance" role="img" aria-label={`${leftLabel} ${share}%, ${rightLabel} ${100 - share}%`}>
    <div className="balance-labels" aria-hidden="true">
      <span><Swatch kind="sent" />{leftLabel} <strong>{share}%</strong></span>
      <span><strong>{100 - share}%</strong> {rightLabel}<Swatch kind="received" /></span>
    </div>
    <div className="balance-track" aria-hidden="true">
      <i className="sent" style={{ width: `calc(${share}% - 1px)` }} />
      <i className="received" style={{ width: `calc(${100 - share}% - 1px)` }} />
      <b className="balance-mid" />
    </div>
  </div>;
}

export function Sparkline({ values }: { values: number[] }) {
  const w = 56, h = 18;
  const max = Math.max(1, ...values);
  const pts = values.map((v, i) => [i / Math.max(1, values.length - 1) * (w - 4) + 2, h - 2 - v / max * (h - 4)]);
  return <svg className="sparkline" width={w} height={h} aria-hidden="true">
    <polyline points={pts.map(p => p.join(',')).join(' ')} />
    {pts.length > 0 && <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r={2} />}
  </svg>;
}

export function BarList({ items, onSelect, format = number, variant }: { items: { key: string; label: ReactNode; value: number; note?: string }[]; onSelect?: (key: string) => void; format?: (n: number) => string; variant?: 'emoji' }) {
  const max = Math.max(1, ...items.map(i => i.value));
  return <ol className={`bar-list ${variant ?? ''}`}>
    {items.map((item, i) => {
      const body = <>
        <span className="bar-list-label">{item.label}{item.note && <small>{item.note}</small>}</span>
        <span className="bar-list-track"><i style={{ width: `${Math.max(1.5, item.value / max * 100)}%`, '--i': i } as CSSProperties} /></span>
        <span className="bar-list-value">{format(item.value)}</span>
      </>;
      return <li key={item.key}>{onSelect ? <button onClick={() => onSelect(item.key)}>{body}</button> : <div>{body}</div>}</li>;
    })}
  </ol>;
}

/* ---------- year-over-year lines on one axis ---------- */

export function YearLines({ before, after, beforeLabel, afterLabel }: { before: Point[]; after: Point[]; beforeLabel: string; afterLabel: string }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const { tip, show, hide } = useTip();
  const [active, setActive] = useState<number | null>(null);
  const height = 220, top = 14, bottom = 22, left = 38, right = 48;
  // Months that have not happened yet are left off rather than drawn as zero.
  const now = new Date();
  const months = (label: string) => Number(label) === now.getFullYear() ? now.getMonth() + 1 : 12;
  const totals = (pts: Point[], label: string) => Array.from({ length: months(label) }, (_, m) => (pts[m]?.sent ?? 0) + (pts[m]?.received ?? 0));
  const a = totals(before, beforeLabel), b = totals(after, afterLabel);
  const max = Math.max(1, ...a, ...b);
  const step = niceStep(max);
  const ceiling = Math.ceil(max / step) * step;
  const innerW = Math.max(10, width - left - right), innerH = height - top - bottom;
  const x = (m: number) => left + m / 11 * innerW;
  const y = (v: number) => top + innerH - v / ceiling * innerH;
  const line = (vals: number[]) => vals.map((v, m) => `${m ? 'L' : 'M'}${x(m)} ${y(v)}`).join('');
  const month = (m: number, style: 'short' | 'narrow' | 'long') => new Date(2001, m, 1).toLocaleDateString(undefined, { month: style });
  const [ya, yb] = spread([y(a.at(-1) ?? 0), y(b.at(-1) ?? 0)], 14, top, top + innerH);
  return <div className="chart-block" ref={ref}>
    <div className="chart-legend" aria-hidden="true">
      <span><i className="swatch line before" /> {beforeLabel}</span>
      <span><i className="swatch line after" /> {afterLabel}</span>
    </div>
    <svg className="chart" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Monthly messages, ${beforeLabel} compared with ${afterLabel}, on a shared scale.`} onMouseLeave={() => { hide(); setActive(null); }}>
      {[0, 1, 2, 3].map(k => k * step).filter(v => v <= ceiling).map(v => <g key={v} className="grid">
        <line x1={left} x2={left + innerW} y1={y(v)} y2={y(v)} />
        <text x={left - 8} y={y(v)} dy="0.32em" textAnchor="end">{compact(v)}</text>
      </g>)}
      {active !== null && <line className="crosshair" x1={x(active)} x2={x(active)} y1={top} y2={top + innerH} />}
      <path className="year-line before" d={line(a)} pathLength={1} />
      <path className="year-line after" d={line(b)} pathLength={1} />
      {active !== null && <>
        {active < a.length && <circle className="dot before" cx={x(active)} cy={y(a[active])} r={4.5} />}
        {active < b.length && <circle className="dot after" cx={x(active)} cy={y(b[active])} r={4.5} />}
      </>}
      <text className="direct-label" x={x(a.length - 1) + 8} y={ya} dy="0.32em">{beforeLabel}</text>
      <text className="direct-label strong" x={x(b.length - 1) + 8} y={yb} dy="0.32em">{afterLabel}</text>
      {Array.from({ length: 12 }, (_, m) => <text key={m} className="tick" x={x(m)} y={height - 4} textAnchor="middle">{width < 480 ? month(m, 'narrow') : month(m, 'short')}</text>)}
      {Array.from({ length: 12 }, (_, m) => <rect key={m} className="hit" x={x(m) - innerW / 22} y={top} width={innerW / 11} height={innerH}
        onMouseMove={e => { setActive(m); show(e, <><strong>{month(m, 'long')}</strong><span><i className="swatch line before" />{beforeLabel}: {m < a.length ? number(a[m]) : '—'}</span><span><i className="swatch line after" />{afterLabel}: {m < b.length ? number(b[m]) : '—'}</span></>); }} />)}
    </svg>
    <ChartTip tip={tip} />
  </div>;
}

/* ---------- slope chart for who rose / faded ---------- */

type Slope = { id: string; name: string; before: number; after: number; difference: number };

export function SlopeChart({ rows, beforeLabel, afterLabel, onSelect }: { rows: Slope[]; beforeLabel: string; afterLabel: string; onSelect: (id: string) => void }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<string | null>(null);
  const shown = rows.slice(0, 8);
  const height = Math.max(220, shown.length * 34 + 40), top = 30, bottom = 14;
  const labelW = Math.min(170, Math.max(96, width * 0.32));
  const x1 = labelW, x2 = width - labelW;
  const max = Math.max(1, ...shown.flatMap(r => [r.before, r.after]));
  const y = (v: number) => top + (height - top - bottom) * (1 - v / max);
  const ly1 = spread(shown.map(r => y(r.before)), 16, top, height - bottom);
  const ly2 = spread(shown.map(r => y(r.after)), 16, top, height - bottom);
  const short = (s: string) => s.length > 16 ? s.slice(0, 15) + '…' : s;
  useEffect(() => setHover(null), [rows]);
  return <div className="chart-block slope" ref={ref}>
    <div className="chart-legend" aria-hidden="true">
      <span><i className="swatch line up" /> Grew</span>
      <span><i className="swatch line down" /> Faded</span>
    </div>
    <svg className="chart" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Biggest changes in direct messages between ${beforeLabel} and ${afterLabel}. Exact values in the table below.`}>
      <text className="axis-head" x={x1} y={12} textAnchor="middle">{beforeLabel}</text>
      <text className="axis-head" x={x2} y={12} textAnchor="middle">{afterLabel}</text>
      <line className="slope-axis" x1={x1} x2={x1} y1={top - 6} y2={height - bottom} />
      <line className="slope-axis" x1={x2} x2={x2} y1={top - 6} y2={height - bottom} />
      {shown.map((r, i) => {
        const kind = r.difference >= 0 ? 'up' : 'down';
        const dim = hover && hover !== r.id ? 'dim' : '';
        return <g key={r.id} className={`slope-row ${kind} ${dim}`} style={{ '--i': i } as CSSProperties}
          onMouseEnter={() => setHover(r.id)} onMouseLeave={() => setHover(null)} onClick={() => onSelect(r.id)}>
          <path className="slope-line" d={`M${x1} ${y(r.before)}L${x2} ${y(r.after)}`} pathLength={1} />
          <path className="slope-hit" d={`M${x1} ${y(r.before)}L${x2} ${y(r.after)}`} />
          <circle cx={x1} cy={y(r.before)} r={4.5} />
          <circle cx={x2} cy={y(r.after)} r={4.5} />
          <text className="slope-label" x={x1 - 10} y={ly1[i]} dy="0.32em" textAnchor="end">{short(r.name)} <tspan className="num">{compact(r.before)}</tspan></text>
          <text className="slope-label" x={x2 + 10} y={ly2[i]} dy="0.32em"><tspan className="num">{compact(r.after)}</tspan> {short(r.name)}</text>
        </g>;
      })}
    </svg>
  </div>;
}

/* ---------- laugh evolution: up to four series on one axis ---------- */

export function MultiLine({ x, series, unit = '%', label }: { x: number[]; series: { label: string; values: number[]; counts?: number[] }[]; unit?: string; label: string }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const { tip, show, hide } = useTip();
  const [active, setActive] = useState<number | null>(null);
  const height = 220, top = 14, bottom = 22, left = 38, right = 56;
  const max = Math.max(0.1, ...series.flatMap(s => s.values));
  const step = niceStep(max);
  const ceiling = Math.ceil(max / step) * step;
  const innerW = Math.max(10, width - left - right), innerH = height - top - bottom;
  const px = (i: number) => left + (x.length > 1 ? i / (x.length - 1) : 0.5) * innerW;
  const py = (v: number) => top + innerH - v / ceiling * innerH;
  const ends = spread(series.map(s => py(s.values.at(-1) ?? 0)), 14, top, top + innerH);
  const fmt = (v: number) => `${v < 1 ? v.toFixed(1) : Math.round(v)}${unit}`;
  return <div className="chart-block" ref={ref}>
    <div className="chart-legend" aria-hidden="true">{series.map((s, i) => <span key={s.label}><i className={`swatch cat-${i + 1}`} /> {s.label}</span>)}</div>
    <svg className="chart" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${label}. Exact values in the table below.`} onMouseLeave={() => { hide(); setActive(null); }}>
      {[0, 1, 2, 3].map(k => k * step).filter(v => v <= ceiling + 1e-9).map(v => <g key={v} className="grid">
        <line x1={left} x2={left + innerW} y1={py(v)} y2={py(v)} />
        <text x={left - 8} y={py(v)} dy="0.32em" textAnchor="end">{fmt(v)}</text>
      </g>)}
      {active !== null && <line className="crosshair" x1={px(active)} x2={px(active)} y1={top} y2={top + innerH} />}
      {series.map((s, i) => <g key={s.label} className={`series cat-${i + 1}`}>
        <path className="multi-line" d={s.values.map((v, j) => `${j ? 'L' : 'M'}${px(j)} ${py(v)}`).join('')} pathLength={1} style={{ animationDelay: `${i * 120}ms` }} />
        {s.values.map((v, j) => <circle key={j} cx={px(j)} cy={py(v)} r={active === j ? 4.5 : 2.5} />)}
        <text className="direct-label" x={left + innerW + 8} y={ends[i]} dy="0.32em">{s.label}</text>
      </g>)}
      {x.map((year, j) => <text key={year} className="tick" x={px(j)} y={height - 4} textAnchor="middle">{year}</text>)}
      {x.map((year, j) => <rect key={year} className="hit" x={px(j) - innerW / Math.max(1, x.length - 1) / 2} y={top} width={innerW / Math.max(1, x.length - 1)} height={innerH}
        onMouseMove={e => { setActive(j); show(e, <><strong>{year}</strong>{series.map((s, i) => <span key={s.label}><i className={`swatch cat-${i + 1}`} />{s.label}: {fmt(s.values[j])}{s.counts ? ` (${number(s.counts[j])})` : ''}</span>)}</>); }} />)}
    </svg>
    <ChartTip tip={tip} />
    <details className="chart-table"><summary>View yearly numbers</summary>
      <div className="table-scroll"><table><thead><tr><th>Year</th>{series.map(s => <th key={s.label}>{s.label}</th>)}</tr></thead>
        <tbody>{x.map((year, j) => <tr key={year}><td>{year}</td>{series.map(s => <td key={s.label}>{fmt(s.values[j])}</td>)}</tr>)}</tbody></table></div>
    </details>
  </div>;
}

/* ---------- reply-time distribution, you vs. them ---------- */

export function ReplyHistogram({ bins, you, them, themLabel }: { bins: string[]; you: number[]; them: number[]; themLabel: string }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const { tip, show, hide } = useTip();
  const share = (xs: number[]) => { const t = xs.reduce((a, b) => a + b, 0) || 1; return xs.map(v => v / t * 100); };
  const a = share(you), b = share(them);
  const height = 190, top = 10, bottom = 22, left = 38;
  const innerW = Math.max(10, width - left), innerH = height - top - bottom;
  const max = Math.max(1, ...a, ...b);
  const step = niceStep(max);
  const ceiling = Math.ceil(max / step) * step;
  const band = innerW / bins.length, barW = Math.max(2, Math.min(28, band / 2 - 4));
  const y = (v: number) => innerH * v / ceiling;
  return <div className="chart-block" ref={ref}>
    <div className="chart-legend" aria-hidden="true"><span><Swatch kind="sent" /> You</span><span><Swatch kind="received" /> {themLabel}</span><span className="legend-note">Share of each side’s replies</span></div>
    <svg className="chart" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`How quickly each of you replies, as a share of replies per time bucket.`} onMouseLeave={hide}>
      {[0, 1, 2, 3].map(k => k * step).filter(v => v <= ceiling).map(v => <g key={v} className="grid">
        <line x1={left} x2={width} y1={top + innerH - y(v)} y2={top + innerH - y(v)} />
        <text x={left - 8} y={top + innerH - y(v)} dy="0.32em" textAnchor="end">{Math.round(v)}%</text>
      </g>)}
      {bins.map((bin, i) => {
        const cx = left + i * band + band / 2;
        return <g key={bin} className="bar" style={{ '--i': i * 3 } as CSSProperties}>
          {a[i] > 0 && <path className="sent" d={roundedTop(cx - barW - 1, top + innerH - y(a[i]), barW, y(a[i]), 4)} />}
          {b[i] > 0 && <path className="received" d={roundedTop(cx + 1, top + innerH - y(b[i]), barW, y(b[i]), 4)} />}
          <text className="tick" x={cx} y={height - 4} textAnchor="middle">{bin}</text>
          <rect className="hit" x={left + i * band} y={top} width={band} height={innerH}
            onMouseMove={e => show(e, <><strong>Replies within {bin}</strong><span><Swatch kind="sent" />You: {Math.round(a[i])}% ({number(you[i])})</span><span><Swatch kind="received" />{themLabel}: {Math.round(b[i])}% ({number(them[i])})</span></>)} />
        </g>;
      })}
      <line className="baseline" x1={left} x2={width} y1={top + innerH} y2={top + innerH} />
    </svg>
    <ChartTip tip={tip} />
  </div>;
}

/* ---------- a year as a ring of 365 spokes ---------- */

export function YearRing({ year, days }: { year: number; days: Record<string, number> }) {
  const { tip, show, hide } = useTip();
  const size = 340, c = size / 2, inner = 74, outer = 158;
  const start = new Date(year, 0, 1);
  const count = Math.round((new Date(year + 1, 0, 1).getTime() - start.getTime()) / 86400000);
  // Scale to the 97th percentile so one extraordinary day doesn't flatten the rest; outliers reach the rim.
  const sorted = Object.values(days).sort((a, b) => a - b);
  const max = Math.max(1, sorted[Math.floor(sorted.length * 0.97)] ?? 1);
  const total = sorted.reduce((a, b) => a + b, 0);
  const spokes = Array.from({ length: count }, (_, i) => {
    const d = new Date(year, 0, 1 + i);
    const key = `${year}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const v = days[key] ?? 0;
    const angle = i / count * Math.PI * 2 - Math.PI / 2;
    const r = inner + 3 + Math.min(1, v / max) * (outer - inner - 3);
    return { key, v, i, x1: c + Math.cos(angle) * inner, y1: c + Math.sin(angle) * inner, x2: c + Math.cos(angle) * r, y2: c + Math.sin(angle) * r };
  });
  const months = Array.from({ length: 12 }, (_, m) => {
    const i = Math.round((new Date(year, m, 1).getTime() - start.getTime()) / 86400000);
    const angle = (i + 15) / count * Math.PI * 2 - Math.PI / 2;
    return { m, x: c + Math.cos(angle) * (outer + 12), y: c + Math.sin(angle) * (outer + 12), label: new Date(year, m, 1).toLocaleDateString(undefined, { month: 'narrow' }) };
  });
  return <div className="ring-block">
    <svg className="chart ring" viewBox={`-14 -14 ${size + 28} ${size + 28}`} role="img" aria-label={`Messages on each day of ${year}, arranged as a ring.`} onMouseLeave={hide}>
      <circle className="ring-track" cx={c} cy={c} r={inner} />
      {spokes.map(s => <line key={s.key} className="spoke" x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} pathLength={1}
        style={{ stroke: s.v ? seq(Math.min(1, s.v / max)) : 'var(--cell-empty)', animationDelay: `${s.i * 2}ms` }}
        onMouseMove={e => show(e, <><strong>{date(s.key)}</strong><span>{number(s.v)} messages</span></>)} />)}
      {months.map(m => <text key={m.m} className="tick" x={m.x} y={m.y} textAnchor="middle" dy="0.32em">{m.label}</text>)}
      <text className="ring-year" x={c} y={c - 6} textAnchor="middle">{year}</text>
      <text className="ring-total" x={c} y={c + 16} textAnchor="middle">{compact(total)} messages</text>
    </svg>
    <ChartTip tip={tip} />
  </div>;
}

/* ---------- friend constellation: people linked through shared group chats ---------- */

type NodeIn = { id: string; kind: 'person' | 'group'; name: string; total: number };
type Placed = NodeIn & { x: number; y: number; r: number };

function layout(nodes: NodeIn[], links: { a: string; b: string; w: number }[], width: number, height: number): Placed[] {
  // Deterministic force layout: repulsion, weighted springs and gentle gravity.
  const index = new Map(nodes.map((n, i) => [n.id, i]));
  const max = { person: Math.max(1, ...nodes.filter(n => n.kind === 'person').map(n => n.total)), group: Math.max(1, ...nodes.filter(n => n.kind === 'group').map(n => n.total)) };
  const pts = nodes.map((n, i) => {
    const angle = i * 2.399963;
    const radius = 40 + 9 * Math.sqrt(i) * 6;
    return { ...n, x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, vx: 0, vy: 0, r: n.kind === 'group' ? 10 + 18 * Math.sqrt(n.total / max.group) : 4 + 7 * Math.sqrt(n.total / max.person) };
  });
  const springs = links.map(l => ({ a: index.get(l.a)!, b: index.get(l.b)!, w: Math.log1p(l.w) })).filter(l => l.a !== undefined && l.b !== undefined);
  const maxW = Math.max(1, ...springs.map(s => s.w));
  for (let t = 0; t < 320; t++) {
    const cool = 1 - t / 320;
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
      const p = pts[i], q = pts[j];
      let dx = q.x - p.x, dy = q.y - p.y;
      const d2 = Math.max(25, dx * dx + dy * dy), d = Math.sqrt(d2);
      // Big group nodes push harder so the busiest chats don't pile into the middle.
      const f = 1400 * (1 + (p.r + q.r) / 8) / d2;
      dx /= d; dy /= d;
      p.vx -= dx * f; p.vy -= dy * f; q.vx += dx * f; q.vy += dy * f;
      const overlap = p.r + q.r + 6 - d;
      if (overlap > 0) { p.vx -= dx * overlap * 0.5; p.vy -= dy * overlap * 0.5; q.vx += dx * overlap * 0.5; q.vy += dy * overlap * 0.5; }
    }
    for (const s of springs) {
      const p = pts[s.a], q = pts[s.b];
      const dx = q.x - p.x, dy = q.y - p.y, d = Math.max(1, Math.hypot(dx, dy));
      const f = (d - (70 + 1.5 * (p.r + q.r))) * 0.01 * (0.3 + s.w / maxW);
      p.vx += dx / d * f; p.vy += dy / d * f; q.vx -= dx / d * f; q.vy -= dy / d * f;
    }
    for (const p of pts) {
      p.vx -= p.x * 0.003 * (height / width); p.vy -= p.y * 0.004;
      p.x += p.vx * 0.5 * cool; p.y += p.vy * 0.5 * cool;
      p.vx *= 0.6; p.vy *= 0.6;
    }
  }
  const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
  const pad = 60;
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const scale = Math.min((width - pad * 2) / Math.max(1, x1 - x0), (height - pad * 2) / Math.max(1, y1 - y0), 1.6);
  return pts.map(p => ({ ...p, x: width / 2 + (p.x - (x0 + x1) / 2) * scale, y: height / 2 + (p.y - (y0 + y1) / 2) * scale }));
}

export function Constellation({ groups, people, links, onPerson }: { groups: { id: string; name: string; total: number }[]; people: { id: string; name: string; total: number }[]; links: { person: string; group: string; weight: number }[]; onPerson: (id: string) => void }) {
  const [ref, width] = useWidth<HTMLDivElement>(900);
  const { tip, show, hide } = useTip();
  const [hover, setHover] = useState<string | null>(null);
  const height = Math.max(460, Math.min(720, width * 0.7));
  const edges = useMemo(() => links.map(l => ({ a: l.person, b: 'g:' + l.group, w: l.weight })), [links]);
  const nodes = useMemo(() => layout([
    ...groups.map(g => ({ id: 'g:' + g.id, kind: 'group' as const, name: g.name, total: g.total })),
    ...people.map(p => ({ id: p.id, kind: 'person' as const, name: p.name, total: p.total })),
  ], edges, width, height), [groups, people, edges, width, height]);
  const at = new Map(nodes.map(n => [n.id, n]));
  const neighbors = useMemo(() => {
    const m = new Map<string, Set<string>>();
    for (const e of edges) {
      if (!m.has(e.a)) m.set(e.a, new Set());
      if (!m.has(e.b)) m.set(e.b, new Set());
      m.get(e.a)!.add(e.b); m.get(e.b)!.add(e.a);
    }
    return m;
  }, [edges]);
  const lit = (id: string) => !hover || hover === id || neighbors.get(hover)?.has(id);
  const maxW = Math.max(1, ...edges.map(e => e.w));
  const short = (s: string) => s.length > 20 ? s.slice(0, 19) + '…' : s;
  // Greedy label placement: biggest groups first, then the most active people; skip any label that would overlap.
  const labelled = useMemo(() => {
    const boxes: [number, number, number, number][] = [];
    const keep = new Set<string>();
    const order = [...nodes].sort((a, b) => (a.kind === b.kind ? b.r - a.r : a.kind === 'group' ? -1 : 1));
    for (const n of order.slice(0, groups.length + 14)) {
      const w = Math.min(20, n.name.length) * 6.4, y = n.kind === 'group' ? n.y + n.r + 4 : n.y - n.r - 16;
      const box: [number, number, number, number] = [n.x - w / 2, y, n.x + w / 2, y + 13];
      if (boxes.some(b => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1])) continue;
      boxes.push(box);
      keep.add(n.id);
    }
    return keep;
  }, [nodes, groups.length]);
  return <div className="constellation" ref={ref}>
    <svg className="chart" width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${people.length} people connected through ${groups.length} group chats.`} onMouseLeave={() => { hide(); setHover(null); }}>
      {edges.map((e, i) => {
        const a = at.get(e.a), b = at.get(e.b);
        if (!a || !b) return null;
        const on = hover && (hover === e.a || hover === e.b);
        return <line key={i} className={`edge ${on ? 'on' : ''} ${hover && !on ? 'dim' : ''}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} style={{ strokeWidth: 0.6 + 2.4 * e.w / maxW, animationDelay: `${Math.min(i, 200) * 3}ms` }} />;
      })}
      {nodes.map((n, i) => <g key={n.id} className={`node ${n.kind} ${lit(n.id) ? '' : 'dim'}`} transform={`translate(${n.x} ${n.y})`} style={{ '--i': Math.min(i, 80) } as CSSProperties}
        onMouseEnter={e => { setHover(n.id); show(e, <><strong>{n.name}</strong><span>{n.kind === 'group' ? `${number(n.total)} messages · ${neighbors.get(n.id)?.size ?? 0} people shown` : `${number(n.total)} group messages · ${neighbors.get(n.id)?.size ?? 0} shared groups`}</span></>); }}
        onMouseMove={e => show(e, <><strong>{n.name}</strong><span>{n.kind === 'group' ? `${number(n.total)} messages · ${neighbors.get(n.id)?.size ?? 0} people shown` : `${number(n.total)} group messages · ${neighbors.get(n.id)?.size ?? 0} shared groups`}</span></>)}
        onMouseLeave={() => { setHover(null); hide(); }}
        onClick={() => n.kind === 'person' && onPerson(n.id)}>
        <circle className="node-dot" r={n.r} />
        {n.kind === 'group' && (labelled.has(n.id) || hover === n.id) && <text className="node-label group-label" y={n.r + 13} textAnchor="middle">{short(n.name)}</text>}
        {n.kind === 'person' && (labelled.has(n.id) || hover === n.id || (hover && neighbors.get(hover)?.has(n.id))) && <text className="node-label" y={-n.r - 5} textAnchor="middle">{short(n.name)}</text>}
      </g>)}
    </svg>
    <ChartTip tip={tip} />
  </div>;
}
