import { useEffect, useState } from 'react';
import { BookOpen, ChevronRight, Info, ShieldCheck } from 'lucide-react';
import type { Summary } from './types';
import { Avatar, Bubble, Highlight, Metric, PersonLink, Typing, compact, date, hourLabel, number, reducedMotion, shortDate } from './components';
import { BarList, Heatmap, MultiLine, Sparkline, Timeline, YearRing, rhythmPeak } from './charts';
import { OnThisDay, Personality, StreakBoard } from './Insights';

function HeroThread({ total }: { total: number }) {
  const [typing, setTyping] = useState(() => !reducedMotion());
  useEffect(() => {
    if (!typing) return;
    const t = setTimeout(() => setTyping(false), 1400);
    return () => clearTimeout(t);
  }, [typing]);
  return <div className="thread hero-thread" aria-hidden="true">
    <Bubble from="them" tail={false} index={0}>so… how much did we text?</Bubble>
    <Bubble from="them" index={1}>be honest 👀</Bubble>
    {typing ? <div className="hero-typing"><Typing index={2} /></div> : <>
      <Bubble from="me" tail={false} index={0}>you had a lot to say.</Bubble>
      <Bubble from="me" index={1} status="Delivered">{compact(total)} messages, actually.</Bubble>
    </>}
  </div>;
}

export function Overview({ data, year, namesReady, revision, onStory, onPeople, onPerson, onContacts, onCircles }: {
  data: Summary; year: string; namesReady: boolean; revision: number;
  onStory: () => void; onPeople: () => void; onPerson: (id: string) => void; onContacts: () => void; onCircles: () => void;
}) {
  const peak = rhythmPeak(data.rhythm);
  return <div className="content overview view-enter">
    <section className="welcome">
      <div className="welcome-copy">
        <div className="date-line">{year === 'all' ? 'Your available message history' : `${year} on this Mac`}</div>
        <h1>There’s a story<br />in every conversation.</h1>
        <p>A look at the people, patterns, and little moments that kept you connected.</p>
        <button className="primary" onClick={onStory}><BookOpen size={17} /> Open your Wrapped <ChevronRight size={16} /></button>
      </div>
      <HeroThread key={data.total} total={data.total} />
    </section>

    <div className="metrics four">
      <Metric label="Messages" value={data.total} note={`${compact(data.sent)} sent · ${compact(data.received)} received`} />
      <Metric label="People" value={data.people} note="Direct conversations" />
      <Metric label="Group chats" value={data.groups} note="In this period" />
      <Metric label="Days connected" value={data.active_days} note="Days with message activity" />
    </div>

    <div className="highlights">
      {data.streak && <Highlight icon="🔥" label="Longest streak" value={`${number(data.streak.days)} days`} note={`${shortDate(data.streak.start)} – ${date(data.streak.end)}`} />}
      {data.busiest_day && <Highlight icon="📅" label="Busiest day" value={date(data.busiest_day.date)} note={`${number(data.busiest_day.count)} messages`} />}
      {peak && <Highlight icon="⏰" label="Prime time" value={`${peak.dayName}s, ${hourLabel(peak.hour)}`} note="Your busiest hour of the week" />}
      {data.late_night !== null && <Highlight icon="🌙" label="After midnight" value={`${data.late_night}%`} note="Of messages, 12–4 AM" />}
    </div>

    {!namesReady && <button className="contact-nudge" onClick={onContacts}><Info size={18} /><span>Seeing numbers instead of names? <strong>Connect your Contacts.</strong></span><ChevronRight size={16} /></button>}

    <Personality habits={data.habits} />

    <OnThisDay revision={revision} onPerson={onPerson} />

    <div className="overview-grid">
      <div className="overview-col">
      <section className="panel">
        <div className="section-title"><div><h2>The conversation keeps going.</h2><p>Your sent and received messages over time.</p></div></div>
        <Timeline points={data.timeline} />
      </section>
      <section className="panel">
        <div className="section-title"><div><h2>When you text.</h2><p>{peak ? `Things get chatty on ${peak.dayName}s around ${hourLabel(peak.hour)}.` : 'Weekday and hour of every message.'}</p></div></div>
        <Heatmap grid={data.rhythm} />
      </section>
      {data.laughs.years.length > 1 && <section className="panel">
        <div className="section-title"><div><h2>How you laugh.</h2><p>Share of your sent messages containing each laugh, by year.</p></div></div>
        <MultiLine x={data.laughs.years} series={data.laughs.series} label="How you laugh over the years" />
      </section>}
      {data.calendar && <section className="panel">
        <div className="section-title"><div><h2>{data.calendar.year}, day by day.</h2><p>{year === 'all' ? 'Your busiest year, as a ring.' : 'Every day of the year, as a ring.'}</p></div></div>
        <YearRing year={data.calendar.year} days={data.calendar.days} />
      </section>}
      </div>
      <div className="overview-col">
      <section className="panel top-people">
        <div className="section-title"><h2>Your inner circle.</h2><button className="text-button" onClick={onPeople}>View all</button></div>
        <p className="muted">Most active direct conversations, with the last 12 months of activity.</p>
        {data.top_people.slice(0, 5).map((p, i) => <div className="ranked-person" key={p.id}>
          <span className="rank">{i + 1}</span>
          <Avatar name={p.name} />
          <div className="ranked-copy"><PersonLink name={p.name} onClick={() => onPerson(p.id)} /><small>{number(p.total)} messages · {Math.round(p.sent / Math.max(1, p.total) * 100)}% from you</small></div>
          <Sparkline values={p.sparkline} />
        </div>)}
        {!data.top_people.length && <p className="muted">No direct conversations in this period.</p>}
      </section>
      <section className="panel">
        <div className="section-title"><h2>Group chats.</h2><span className="pill">{number(data.groups)}</span></div>
        <p className="muted">Your busiest groups in this period.</p>
        {data.top_groups.length ? <BarList items={data.top_groups.map(g => ({ key: g.id, label: g.name || 'Unnamed group', value: g.total }))} /> : <p className="muted">No group conversations in this period.</p>}
        {data.top_groups.length > 0 && <button className="text-button" onClick={onCircles}>See how your circles connect</button>}
      </section>
      <StreakBoard streaks={data.streaks} onPerson={onPerson} />
      </div>
    </div>

    <footer className="data-footer"><ShieldCheck size={14} /><span>Available history: {date(data.coverage.first)} – {date(data.coverage.last)}. Counts exclude Tapbacks and system events. Times use this Mac’s local timezone.</span></footer>
  </div>;
}
