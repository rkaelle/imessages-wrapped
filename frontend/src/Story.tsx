import { useCallback, useEffect, useState, type CSSProperties } from 'react';
import { ArrowLeft, ArrowRight, Pause, Play, RotateCcw } from 'lucide-react';
import type { Summary } from './types';
import { Avatar, Bubble, CountUp, compact, date, hourLabel, number, percent, reducedMotion } from './components';
import { BarList, CalendarHeatmap, Heatmap, rhythmPeak } from './charts';
import { archetypes } from './Insights';

const DURATION = 7000;
const hues = ['var(--story-1)', 'var(--story-2)', 'var(--story-3)', 'var(--story-4)', 'var(--story-2)', 'var(--story-5)', 'var(--story-6)', 'var(--story-1)'];

function timeOfDay(hour: number) {
  if (hour < 5) return 'a night owl';
  if (hour < 12) return 'a morning person';
  if (hour < 17) return 'an afternoon texter';
  if (hour < 21) return 'an evening chatter';
  return 'a late-night texter';
}

export function Story({ data, onPerson }: { data: Summary; onPerson: (id: string) => void }) {
  const [step, setStep] = useState(0);
  const [paused, setPaused] = useState(() => reducedMotion());
  const [hovering, setHovering] = useState(false);
  const top = data.top_people[0];
  const peak = rhythmPeak(data.rhythm);
  const tapback = data.reactions.items[0];
  const titles = ['Your history, wrapped.', 'Your number one.', 'The people in your corner.', 'A rhythm of your own.', 'Your texting personality.', 'Your biggest day.', 'Said without words.', 'That’s your story.'];
  const persona = archetypes(data.habits);
  const last = titles.length - 1;
  const go = useCallback((n: number) => setStep(Math.max(0, Math.min(last, n))), [last]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('input, select, textarea')) return;
      if (e.key === 'ArrowRight') go(step + 1);
      else if (e.key === 'ArrowLeft') go(step - 1);
      else if (e.key === ' ') { e.preventDefault(); setPaused(p => !p); }
      else return;
    };
    window.addEventListener('keydown', key);
    return () => window.removeEventListener('keydown', key);
  }, [step, go]);

  const running = !paused && !hovering && step !== last;

  return <section className="story view-enter" style={{ '--story-hue': hues[step] } as CSSProperties} aria-roledescription="story">
    <div className="story-progress" aria-label={`Chapter ${step + 1} of ${titles.length}`}>
      {titles.map((t, i) => <button key={t} className={i < step ? 'done' : i === step ? `current ${running ? 'running' : ''}` : ''}
        onClick={() => go(i)} aria-label={`Chapter ${i + 1}: ${t}`} aria-current={step === i ? 'step' : undefined}>
        <i style={{ animationDuration: `${DURATION}ms` }} onAnimationEnd={() => i === step && step < last && go(step + 1)} />
      </button>)}
    </div>

    <div className="story-stage" onMouseEnter={() => setHovering(true)} onMouseLeave={() => setHovering(false)}>
      <button className="story-zone prev" aria-label="Previous chapter" onClick={() => go(step - 1)} disabled={step === 0} />
      <button className="story-zone next" aria-label="Next chapter" onClick={() => go(step + 1)} disabled={step === last} />
      <div className="story-content" key={step}>
        <span className="story-chapter">Chapter {step + 1} of {titles.length}</span>
        <h2>{titles[step]}</h2>

        {step === 0 && <div className="thread story-thread">
          <Bubble from="me" index={0} className="huge"><strong><CountUp value={data.total} format={compact} /></strong><span>messages. A whole lot of life.</span></Bubble>
          <Bubble from="them" index={2}>{number(data.sent)} sent, {number(data.received)} received, between {date(data.coverage.first)} and {date(data.coverage.last)}.</Bubble>
        </div>}

        {step === 1 && (top ? <div className="thread story-thread">
          <div className="story-avatar"><Avatar name={top.name} size="xl" /><strong>{top.name}</strong></div>
          <Bubble from="them" index={1}>Your most active direct conversation.</Bubble>
          <Bubble from="me" index={2} status="Read" className="huge"><strong><CountUp value={top.total} /></strong><span>messages together</span></Bubble>
          <button className="story-link" onClick={() => onPerson(top.id)}>Explore this connection <ArrowRight size={14} /></button>
        </div> : <p className="story-note">No direct conversations in this period.</p>)}

        {step === 2 && <div className="story-card">
          <BarList items={data.top_people.slice(0, 5).map(p => ({ key: p.id, label: p.name, value: p.total }))} onSelect={onPerson} />
          <p className="story-note">{number(data.people)} people and {number(data.groups)} group chats appear in this period.</p>
        </div>}

        {step === 3 && <div className="story-card">
          {peak ? <>
            <div className="thread story-thread tight">
              <Bubble from="them" index={0}>So what kind of texter are you?</Bubble>
              <Bubble from="me" index={1}>{timeOfDay(peak.hour)} 🙃</Bubble>
            </div>
            <Heatmap grid={data.rhythm} compactMode />
            <p className="story-note">Peak: {peak.dayName}s at {hourLabel(peak.hour)}.{data.late_night ? ` ${data.late_night}% of your messages land between midnight and 4 AM.` : ''}</p>
          </> : <p className="story-note">No activity yet.</p>}
        </div>}

        {step === 4 && <div className="story-card persona-story">
          {persona.map((c, i) => <div key={c.title} className="persona" style={{ '--i': i } as CSSProperties}><span className="persona-emoji" aria-hidden="true">{c.emoji}</span><strong>{c.title}</strong><p>{c.detail}</p></div>)}
          {!persona.length && <p className="story-note">Not enough messages to read your style yet.</p>}
        </div>}

        {step === 5 && <div className="story-card">
          {data.busiest_day ? <>
            <div className="thread story-thread tight">
              <Bubble from="me" index={0} className="huge"><strong><CountUp value={data.busiest_day.count} /></strong><span>messages on {date(data.busiest_day.date)}</span></Bubble>
            </div>
            {data.calendar && <CalendarHeatmap year={data.calendar.year} days={data.calendar.days} highlight={data.busiest_day.date} />}
            <p className="story-note">{data.streak ? `Your longest streak: ${number(data.streak.days)} days in a row, ending ${date(data.streak.end)}.` : ''}</p>
          </> : <p className="story-note">No activity yet.</p>}
        </div>}

        {step === 6 && <div className="thread story-thread">
          {tapback ? <>
            <Bubble from="them" index={0} className="tapped">Your go-to Tapback
              <span className="tapback-badge story-badge"><span>{tapback.emoji}</span></span>
            </Bubble>
            <Bubble from="me" index={2} className="huge"><strong><CountUp value={tapback.count} /></strong><span>{tapback.label.toLowerCase()} reactions · {compact(data.reactions.total)} Tapbacks total</span></Bubble>
          </> : <Bubble from="them" index={0}>No Tapbacks this time. Words did the work.</Bubble>}
          {data.year !== 'all' && <Bubble from="them" index={3}>{data.change === null ? 'No earlier year to compare against.' : `${percent(data.change)} messages compared with ${Number(data.year) - 1}.`}</Bubble>}
        </div>}

        {step === 7 && <div className="thread story-thread">
          <Bubble from="them" tail={false} index={0}>{compact(data.total)} messages</Bubble>
          {top && <Bubble from="them" tail={false} index={1}>#1: {top.name}</Bubble>}
          {persona[0] && <Bubble from="them" tail={false} index={2}>{persona[0].emoji} {persona[0].title}</Bubble>}
          {data.streak && <Bubble from="them" index={3}>{data.streak.days}-day streak 🔥</Bubble>}
          <Bubble from="me" index={4} status="Delivered" className="huge"><strong className="story-name">Life happens<br />between the bubbles.</strong></Bubble>
          <span className="story-footnote">Generated from local message counts. This is an analysis, not a conversation.</span>
        </div>}
      </div>
    </div>

    <div className="story-controls">
      <button className="secondary" onClick={() => go(step - 1)} disabled={step === 0}><ArrowLeft size={16} /> Back</button>
      <span>
        {step !== last && <button className="icon-button" onClick={() => setPaused(p => !p)} aria-label={paused ? 'Play' : 'Pause'}>{paused ? <Play size={16} /> : <Pause size={16} />}</button>}
        {data.year === 'all' ? 'All time' : data.year} Wrapped
      </span>
      <button className="primary" onClick={() => step === last ? (setStep(0), setPaused(false)) : go(step + 1)}>{step === last ? <><RotateCcw size={16} /> Replay</> : <>Next <ArrowRight size={16} /></>}</button>
    </div>
  </section>;
}
