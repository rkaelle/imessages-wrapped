import { useState, type CSSProperties } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { useResource } from './api';
import type { Habits, OnThisDay as OnThisDayData, Summary } from './types';
import { Avatar, Bubble, PersonLink, compact, date, number, shortDate } from './components';
import { BarList } from './charts';

type Archetype = { emoji: string; title: string; detail: string; score: number };

function seconds(s: number) {
  return s < 60 ? `${s} seconds` : s < 3600 ? `${Math.round(s / 60)} minutes` : `${(s / 3600).toFixed(1)} hours`;
}

/** Turns raw habit numbers into up to three texting-personality cards, strongest signal first. */
export function archetypes(h: Habits | null): Archetype[] {
  if (!h || !h.sent) return [];
  const found: Archetype[] = [];
  if (h.late_night >= 8) found.push({ emoji: '🦉', title: 'Night Owl', detail: `${h.late_night}% of your messages land between midnight and 4 AM.`, score: h.late_night / 8 });
  if (h.early_morning >= 12) found.push({ emoji: '🌅', title: 'Early Bird', detail: `${h.early_morning}% of your messages go out between 5 and 9 AM.`, score: h.early_morning / 12 });
  if (h.double_text >= 30) found.push({ emoji: '💬', title: 'Double Texter', detail: `${h.double_text}% of your texts follow your own within two minutes.`, score: h.double_text / 30 });
  if (h.avg_length !== null && h.avg_length >= 60) found.push({ emoji: '📜', title: 'The Essayist', detail: `Your texts average ${Math.round(h.avg_length)} characters.`, score: h.avg_length / 60 });
  if (h.avg_length !== null && h.avg_length <= 30) found.push({ emoji: '⚡️', title: 'Short & Sweet', detail: `Your texts average just ${Math.round(h.avg_length)} characters.`, score: 30 / Math.max(1, h.avg_length) });
  if (h.tapbacks_per_100 >= 6) found.push({ emoji: '👑', title: 'Tapback Royalty', detail: `${h.tapbacks_per_100} Tapbacks for every 100 messages you send.`, score: h.tapbacks_per_100 / 6 });
  if (h.starts_share !== null && h.starts_share >= 55) found.push({ emoji: '📣', title: 'The Instigator', detail: `You start ${h.starts_share}% of your conversations.`, score: h.starts_share / 55 });
  if (h.starts_share !== null && h.starts_share <= 42) found.push({ emoji: '🧲', title: 'In Demand', detail: `Friends start ${Math.round(100 - h.starts_share)}% of your conversations.`, score: (100 - h.starts_share) / 58 });
  if (h.reply_median !== null && h.reply_median <= 60) found.push({ emoji: '🏎️', title: 'Lightning Fingers', detail: `Your typical reply lands in ${seconds(h.reply_median)}.`, score: 60 / Math.max(5, h.reply_median) });
  if (h.reply_median !== null && h.reply_median >= 1800) found.push({ emoji: '🐢', title: 'Thoughtful Replier', detail: `Your typical reply takes ${seconds(h.reply_median)}.`, score: h.reply_median / 1800 });
  found.sort((a, b) => b.score - a.score);
  return found.length ? found.slice(0, 3) : [{ emoji: '🙂', title: 'Steady Texter', detail: 'No extremes here: you keep the conversation flowing.', score: 1 }];
}

export function Personality({ habits }: { habits: Habits | null }) {
  const cards = archetypes(habits);
  if (!cards.length) return null;
  return <section className="personality">
    <div className="section-title"><div><h2>Your texting personality.</h2><p>Based on how, when, and how much you text.</p></div></div>
    <div className="persona-row">
      {cards.map((c, i) => <div key={c.title} className="persona" style={{ '--i': i } as CSSProperties}>
        <span className="persona-emoji" aria-hidden="true">{c.emoji}</span>
        <strong>{c.title}</strong>
        <p>{c.detail}</p>
      </div>)}
    </div>
  </section>;
}

function readReveal() {
  try { return localStorage.getItem('wrapped:reveal-snippets') === '1'; } catch { return false; }
}

export function OnThisDay({ revision, onPerson }: { revision: number; onPerson: (id: string) => void }) {
  const state = useResource<OnThisDayData>('/onthisday', revision);
  const [reveal, setReveal] = useState(readReveal);
  const toggle = () => setReveal(v => { try { localStorage.setItem('wrapped:reveal-snippets', v ? '0' : '1'); } catch { /* storage unavailable */ } return !v; });
  const years = state.data?.years ?? [];
  if (!years.length) return null;
  const today = new Date(state.data!.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'long', day: 'numeric' });
  return <section className="panel on-this-day">
    <div className="section-title">
      <div><h2>On this day.</h2><p>What {today} looked like in years past.</p></div>
      <button className="secondary small" onClick={toggle} aria-pressed={reveal}>{reveal ? <><EyeOff size={14} /> Hide messages</> : <><Eye size={14} /> Show messages</>}</button>
    </div>
    <div className="otd-row">
      {years.map((y, i) => <article key={y.year} className="otd-card" style={{ '--i': i } as CSSProperties}>
        <header><span className="otd-ago">{y.years_ago === 1 ? '1 year ago' : `${y.years_ago} years ago`}</span><strong>{y.year}</strong><small>{number(y.total)} messages</small></header>
        {y.people[0] && <div className="otd-person"><Avatar name={y.people[0].name} size="small" /><PersonLink name={y.people[0].name} onClick={() => onPerson(y.people[0].id)} /></div>}
        {y.snippets.length > 0 && <div className={`thread otd-thread ${reveal ? '' : 'veiled'}`} aria-hidden={!reveal}>
          {y.snippets.map((s, k) => <Bubble key={k} from={s.sent ? 'me' : 'them'} tail={k === y.snippets.length - 1 || y.snippets[k + 1].sent !== s.sent} index={k}>{s.text}</Bubble>)}
        </div>}
        {y.people.length > 1 && <small className="otd-also">Also: {y.people.slice(1).map(p => p.name).join(', ')}</small>}
      </article>)}
    </div>
  </section>;
}

export function StreakBoard({ streaks, onPerson }: { streaks: Summary['streaks']; onPerson: (id: string) => void }) {
  if (!streaks.longest.length && !streaks.current.length) return null;
  return <section className="panel">
    <div className="section-title"><h2>Streak hall of fame.</h2></div>
    <p className="muted">Most consecutive days messaging one person.</p>
    {streaks.longest.length > 0 && <BarList onSelect={onPerson} format={n => `${number(n)}d`}
      items={streaks.longest.map(s => ({ key: s.id, label: s.name, note: `${shortDate(s.start)} – ${date(s.end)}`, value: s.days }))} />}
    {streaks.current.length > 0 && <>
      <h3 className="spaced">Going right now 🔥</h3>
      <div className="streak-chips">{streaks.current.map(s => <button key={s.id} className="streak-chip" onClick={() => onPerson(s.id)}>
        <Avatar name={s.name} size="small" /><span>{s.name}</span><b>{number(s.days)}</b>
      </button>)}</div>
    </>}
  </section>;
}

export function MediaMix({ media }: { media: Record<string, number> | null }) {
  if (!media) return null;
  const items: [string, string, number][] = [['📷', 'Photos', media.photos], ['🎬', 'Videos', media.videos], ['🎙️', 'Voice', media.voice], ['🔗', 'Links', media.links], ['📎', 'Files', media.files]];
  return <div className="media-mix">{items.map(([icon, label, n]) => <div key={label}><span aria-hidden="true">{icon}</span><strong>{compact(n)}</strong><small>{label}</small></div>)}</div>;
}

export function WordChips({ words }: { words: { word: string; count: number; ratio: number }[] }) {
  const max = Math.max(1, ...words.map(w => Math.log(w.ratio + 1)));
  return <div className="word-chips">{words.map((w, i) => <span key={w.word} className="word-chip" title={`${number(w.count)} times · ${w.ratio}× your usual rate`}
    style={{ '--i': i, fontSize: `${13 + 9 * Math.log(w.ratio + 1) / max}px` } as CSSProperties}>{w.word}<small>{w.ratio}×</small></span>)}</div>;
}
