import { useState, type ReactNode } from 'react';
import { Search } from 'lucide-react';
import { useResource, withDetailDefaults } from './api';
import type { Detail, Person } from './types';
import { Avatar, Bubble, Empty, Loading, Metric, ReactionPanel, Stamp, compact, date, hourLabel, number, percent, shortDate } from './components';
import { BalanceBar, BarList, Heatmap, ReplyHistogram, Sparkline, Timeline, rhythmPeak } from './charts';
import { MediaMix, WordChips } from './Insights';

function duration(seconds: number | null) {
  if (seconds === null) return 'Not enough data';
  if (seconds < 60) return '<1 min';
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  return `${(seconds / 3600).toFixed(1)} hr`;
}

/** A question bubble from "them", answered by a card. */
function Exchange({ prompt, children, index = 0 }: { prompt: string; children: ReactNode; index?: number }) {
  return <div className="exchange">
    <div className="thread"><Bubble from="them" index={index}>{prompt}</Bubble></div>
    <section className="panel thread-card">{children}</section>
  </div>;
}

function Conversation({ d, year, onSearch }: { d: Detail; year: string; onSearch: () => void }) {
  const first = d.name.split(/\s+/)[0];
  const peak = rhythmPeak(d.rhythm);
  const starts = d.initiations.you + d.initiations.them;
  return <div className="conversation-view view-enter">
    <header className="person-heading">
      <Avatar name={d.name} size="xl" />
      <h2>{d.name}</h2>
      <p>{d.addresses > 1 ? `${d.addresses} addresses linked through Contacts` : 'Your direct conversation'} · {date(d.first)} – {date(d.last)}</p>
    </header>

    {d.first && <Stamp><strong>{year === 'all' ? 'First message' : `${year} begins`}</strong> {date(d.first)}</Stamp>}
    <div className="thread">
      <Bubble from="them" index={0}>so how much do we actually talk?</Bubble>
      <Bubble from="me" tail={false} index={1}>{number(d.total)} messages together.</Bubble>
      <Bubble from="me" index={2} status={year !== 'all' && d.change !== null ? `${percent(d.change)} vs. ${Number(year) - 1}` : 'Read'}>{number(d.sent)} from me, {number(d.received)} from you.</Bubble>
    </div>

    <section className="panel thread-card">
      <h3>Who does the talking.</h3>
      <BalanceBar left={d.sent} right={d.received} leftLabel="You" rightLabel={first} />
      {starts > 0 && <>
        <h3 className="spaced">Who starts the conversation.</h3>
        <BalanceBar left={d.initiations.you} right={d.initiations.them} leftLabel="You" rightLabel={first} />
        <p className="method">{number(starts)} conversations, counted as the first message after at least {d.initiations.gap_hours} quiet hours.</p>
      </>}
    </section>

    <Exchange prompt="when did we talk the most?" index={0}>
      <Timeline points={d.timeline} label={`Messages with ${d.name}`} />
    </Exchange>

    <Exchange prompt="are we morning people or night owls? 🌙">
      <p className="muted">{peak ? `You two peak on ${peak.dayName}s around ${hourLabel(peak.hour)}.` : 'Not enough messages yet.'}{d.late_night ? ` ${d.late_night}% of messages land after midnight.` : ''}</p>
      <Heatmap grid={d.rhythm} />
    </Exchange>

    <Exchange prompt="how fast do we reply?">
      <div className="metrics three">
        <Metric label="Your median reply" value={duration(d.responses.you)} note={`${number(d.responses.you_samples)} observed replies`} />
        <Metric label="Their median reply" value={duration(d.responses.them)} note={`${number(d.responses.their_samples)} observed replies`} />
        <Metric label="Longest streak" value={d.streak ? `${d.streak.days} days` : '—'} note={d.streak ? `${shortDate(d.streak.start)} – ${date(d.streak.end)}` : 'No streak yet'} />
      </div>
      {d.reply_histogram.bins.length > 0 && <ReplyHistogram bins={d.reply_histogram.bins} you={d.reply_histogram.you} them={d.reply_histogram.them} themLabel={first} />}
      <p className="method">Time between consecutive messages when the sender changes, using gaps up to 24 hours. These are observed gaps, not read receipts or a measure of attention.</p>
    </Exchange>

    {d.words.length > 0 && <Exchange prompt="what do we always talk about? 🤔">
      <WordChips words={d.words} />
      <p className="method">Words you two use far more often than in the rest of your messages. Larger means more distinctive; hover for counts.</p>
    </Exchange>}

    {d.media && <Exchange prompt="what do we send each other? 📸">
      <MediaMix media={d.media} />
      <button className="text-button" onClick={onSearch}>Search your messages with {first}</button>
    </Exchange>}

    <Exchange prompt="what's our emoji? 😂">
      {d.emojis.items.length
        ? <BarList items={d.emojis.items.map(e => ({ key: e.emoji, label: <span className="emoji-label">{e.emoji}</span>, value: e.count }))} variant="emoji" />
        : <p className="muted">No decoded emojis in this period.</p>}
      <p className="method">From {number(d.emojis.decoded)} readable message bodies. {number(d.emojis.unreadable)} media-only or undecodable bodies excluded. Text stays on this Mac.</p>
    </Exchange>

    <section className="panel thread-card"><ReactionPanel data={d.reactions} /></section>
  </div>;
}

export function People({ people, selected, onSelect, year, revision, onSearch }: { people: Person[]; selected: string | null; onSelect: (id: string) => void; year: string; revision: number; onSearch: (id: string) => void }) {
  const [search, setSearch] = useState('');
  const detail = useResource<Detail>(selected ? `/people/${selected}?year=${year}` : null, revision);
  const list = people.filter(p => p.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  return <div className="people-layout">
    <aside className="people-list">
      <label className="search"><Search size={15} /><input placeholder="Search" aria-label="Find a person" value={search} onChange={e => setSearch(e.target.value)} /></label>
      <p className="list-note">Direct conversations only</p>
      <div className="people-results" onKeyDown={e => {
        if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
        e.preventDefault();
        const at = list.findIndex(p => p.id === selected);
        const next = list[Math.max(0, Math.min(list.length - 1, at + (e.key === 'ArrowDown' ? 1 : -1)))];
        if (next) { onSelect(next.id); (e.currentTarget.querySelector(`[data-id="${next.id}"]`) as HTMLElement | null)?.focus(); }
      }}>
        {list.map(p => <button key={p.id} data-id={p.id} className={`conversation ${p.id === selected ? 'selected' : ''}`} onClick={() => onSelect(p.id)}>
          <Avatar name={p.name} />
          <span className="conversation-copy">
            <span className="conversation-top"><strong>{p.name}</strong><time>{shortDate(p.last)}</time></span>
            <span className="conversation-bottom"><small>{compact(p.total)} messages{p.resolved ? '' : ' · Not in Contacts'}</small><Sparkline values={p.sparkline} /></span>
          </span>
        </button>)}
        {!list.length && <p className="list-note">No matching conversations.</p>}
      </div>
    </aside>
    <div className="person-detail">
      {!selected ? <Empty title="Every connection has a story." body="Choose a person to explore your direct conversations together." />
        : detail.loading ? <Loading text="Putting this connection together…" />
          : detail.error ? <div className="error" role="alert">{detail.error}</div>
            : detail.data ? <Conversation key={detail.data.id} d={withDetailDefaults(detail.data)} year={year} onSearch={() => onSearch(detail.data!.id)} /> : null}
    </div>
  </div>;
}
