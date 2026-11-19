import { useEffect, useState, type ReactNode } from 'react';
import { Search as SearchIcon, X } from 'lucide-react';
import { useResource } from './api';
import type { Person, SearchResult } from './types';
import { Avatar, Bubble, Empty, Loading, PersonLink, Stamp, number } from './components';

function highlight(text: string, query: string): ReactNode {
  const q = query.trim();
  if (!q) return text;
  const parts: ReactNode[] = [];
  const lower = text.toLocaleLowerCase(), needle = q.toLocaleLowerCase();
  let at = 0, i;
  while ((i = lower.indexOf(needle, at)) !== -1) {
    parts.push(text.slice(at, i), <mark key={i}>{text.slice(i, i + q.length)}</mark>);
    at = i + q.length;
  }
  parts.push(text.slice(at));
  return parts;
}

export function Search({ year, revision, people, person, onPerson, onClearPerson }: {
  year: string; revision: number; people: Person[]; person: string | null; onPerson: (id: string) => void; onClearPerson: () => void;
}) {
  const [input, setInput] = useState('');
  const [query, setQuery] = useState('');
  useEffect(() => { const t = setTimeout(() => setQuery(input.trim()), 250); return () => clearTimeout(t); }, [input]);
  const path = query.length >= 2 ? `/search?q=${encodeURIComponent(query)}&year=${year}${person ? `&person=${person}` : ''}` : null;
  const state = useResource<SearchResult>(path, revision);
  const who = person ? people.find(p => p.id === person) : undefined;
  const results = state.data?.results ?? [];
  return <div className="content search-view view-enter">
    <div className="page-heading"><h1>Find that message.</h1><p>Search every text on this Mac. Nothing is uploaded, and the search runs locally.</p></div>
    <div className="search-bar">
      <label className="search big"><SearchIcon size={18} /><input autoFocus placeholder="Search messages" aria-label="Search messages" value={input} onChange={e => setInput(e.target.value)} /></label>
      {who && <span className="filter-chip"><Avatar name={who.name} size="small" />{who.name}<button className="icon-button" aria-label="Search everyone" onClick={onClearPerson}><X size={14} /></button></span>}
    </div>
    {!path ? <Empty title="Search your history" body="Type at least two characters. Try a place, a plan, or an inside joke." />
      : state.loading ? <Loading text="Searching…" />
        : state.error ? <div className="error" role="alert">{state.error}</div>
          : !results.length ? <Empty title="No messages found" body={`Nothing matches “${query}” in this period.`} />
            : <>
              <p className="muted">{number(state.data!.total)} {state.data!.total === 1 ? 'message' : 'messages'}{state.data!.total > results.length ? `, showing the newest ${results.length}` : ''}.</p>
              <div className="search-results">
                {results.map((r, i) => {
                  const prev = results[i - 1];
                  const newChat = !prev || prev.chat.id !== r.chat.id || prev.chat.kind !== r.chat.kind;
                  const day = new Date(r.at).toDateString();
                  const newDay = newChat || new Date(prev.at).toDateString() !== day;
                  return <div key={r.id} className={newChat ? 'result-group' : ''}>
                    {newChat && <div className="result-chat"><Avatar name={r.chat.name} size="small" />{r.chat.kind === 'person' ? <PersonLink name={r.chat.name} onClick={() => onPerson(r.chat.id)} /> : <strong>{r.chat.name}</strong>}</div>}
                    {newDay && <Stamp>{new Date(r.at).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })} {new Date(r.at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}</Stamp>}
                    <div className="thread">
                      {r.sender && <span className="sender-name">{r.sender}</span>}
                      <Bubble from={r.sent ? 'me' : 'them'}>{highlight(r.text, query)}</Bubble>
                    </div>
                  </div>;
                })}
              </div>
            </>}
  </div>;
}
