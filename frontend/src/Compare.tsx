import { useState } from 'react';
import type { Comparison } from './types';
import { useResource } from './api';
import { CountUp, Empty, Loading, PersonLink, compact, date, number, percent } from './components';
import { SlopeChart, YearLines } from './charts';

export function Compare({ years, revision, onPerson }: { years: number[]; revision: number; onPerson: (id: string) => void }) {
  const [before, setBefore] = useState(String(years[1] ?? years[0] ?? new Date().getFullYear() - 1));
  const [after, setAfter] = useState(String(years[0] ?? new Date().getFullYear()));
  const result = useResource<Comparison>(years.length ? `/compare?before=${before}&after=${after}` : null, revision);
  if (!years.length) return <Empty title="No years to compare yet" body="Message history needs to be available on this Mac." />;
  const r = result.data;
  return <div className="content comparison view-enter">
    <div className="section-title page-title">
      <div><h1>A different year.<br />A different conversation.</h1><p>See what changed, and who stayed close.</p></div>
      <div className="compare-selectors">
        <label>Earlier year<select value={before} onChange={e => setBefore(e.target.value)}>{years.map(y => <option key={y}>{y}</option>)}</select></label>
        <span>vs.</span>
        <label>Later year<select value={after} onChange={e => setAfter(e.target.value)}>{years.map(y => <option key={y}>{y}</option>)}</select></label>
      </div>
    </div>
    {result.loading ? <Loading /> : result.error ? <div className="error" role="alert">{result.error}</div> : r ? <>
      <div className="compare-hero">
        <div><span>{before}</span><strong><CountUp value={r.before.total} format={compact} /></strong><small>messages</small></div>
        <span className={`comparison-change ${r.change !== null && r.change < 0 ? 'down' : ''}`}>{percent(r.change)}</span>
        <div><span>{after}</span><strong className="after"><CountUp value={r.after.total} format={compact} /></strong><small>messages</small></div>
      </div>
      <p className="method">{r.note}</p>

      <section className="panel">
        <div className="section-title"><div><h2>Month by month.</h2><p>Both years on one scale.</p></div></div>
        <YearLines before={r.before.timeline} after={r.after.timeline} beforeLabel={before} afterLabel={after} />
        <div className="year-facts-row">
          {[r.before, r.after].map(y => <div key={y.year} className="year-facts">
            <strong>{y.year}</strong>
            <span>{number(y.people)} people</span><span>{number(y.active_days)} active days</span><span>{number(y.groups)} groups</span>
            <small>{date(y.coverage.first)} – {date(y.coverage.last)}</small>
          </div>)}
        </div>
      </section>

      <section className="panel">
        <div className="section-title"><div><h2>Who rose, who faded.</h2><p>The biggest changes in direct messages. Changes describe activity, not the quality of a relationship.</p></div></div>
        {r.people.length ? <SlopeChart rows={r.people} beforeLabel={before} afterLabel={after} onSelect={onPerson} /> : <p className="muted">No direct conversations in either year.</p>}
        <details className="chart-table"><summary>View all {r.people.length} changes</summary>
          <div className="table-scroll"><table><thead><tr><th>Person</th><th>{before}</th><th>{after}</th><th>Change</th></tr></thead>
            <tbody>{r.people.map(p => <tr key={p.id}><td><PersonLink name={p.name} onClick={() => onPerson(p.id)} /></td><td>{number(p.before)}</td><td>{number(p.after)}</td>
              <td className={p.difference > 0 ? 'positive' : p.difference < 0 ? 'negative' : ''}>{p.difference > 0 ? '+' : ''}{number(p.difference)}</td></tr>)}</tbody></table></div>
        </details>
      </section>
    </> : null}
  </div>;
}
