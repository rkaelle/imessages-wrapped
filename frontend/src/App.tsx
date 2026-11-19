import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import { flushSync } from 'react-dom';
import { AlertTriangle, BarChart3, BookOpen, Download, Heart, Info, MessageCircle, Network, RefreshCw, Search, SquarePen, TextSearch, Users, X } from 'lucide-react';
import { request, useResource, withSummaryDefaults } from './api';
import type { Summary } from './types';
import { Avatar, Empty, Loading, Privacy, ReactionPanel, compact, number, shortDate } from './components';
import { Sparkline } from './charts';
import { Overview } from './Overview';
import { Story } from './Story';
import { People } from './People';
import { Compare } from './Compare';
import { Circles } from './Circles';
import { Search as SearchView } from './Search';

type View = 'overview' | 'story' | 'people' | 'circles' | 'compare' | 'reactions' | 'search';
const navigation = [
  { id: 'overview', label: 'Overview', icon: MessageCircle },
  { id: 'story', label: 'Your Wrapped', icon: BookOpen },
  { id: 'people', label: 'People', icon: Users },
  { id: 'circles', label: 'Circles', icon: Network },
  { id: 'compare', label: 'Through the years', icon: BarChart3 },
  { id: 'reactions', label: 'Reactions', icon: Heart },
  { id: 'search', label: 'Search messages', icon: TextSearch },
] as const;
const views = navigation.map(n => n.id) as readonly string[];

/** Reads `#/view[/id]?year=YYYY` so a page survives reloads and can be bookmarked. */
function readHash() {
  const [path, query] = location.hash.replace(/^#\/?/, '').split('?');
  const [view, id] = path.split('/');
  const year = new URLSearchParams(query).get('year');
  return {
    view: (views.includes(view) ? view : 'overview') as View,
    id: id ? decodeURIComponent(id) : null,
    year: year && /^\d{4}$/.test(year) ? year : 'all',
  };
}

/** Runs a state change inside a view transition when the browser supports it. */
function transition(update: () => void) {
  const doc = document as Document & { startViewTransition?: (cb: () => void) => unknown };
  if (doc.startViewTransition && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) doc.startViewTransition(() => flushSync(update));
  else update();
}

export default function App() {
  const initial = useMemo(readHash, []);
  const [view, setView] = useState<View>(initial.view);
  const [year, setYear] = useState(initial.year);
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<string | null>(initial.view === 'people' ? initial.id : null);
  const [searchPerson, setSearchPerson] = useState<string | null>(initial.view === 'search' ? initial.id : null);
  const [search, setSearch] = useState('');
  const [contactPanel, setContactPanel] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const state = useResource<Summary>(`/summary?year=${year}`, revision);
  const data = useMemo(() => state.data && withSummaryDefaults(state.data), [state.data]);

  useEffect(() => {
    const id = view === 'people' ? selected : view === 'search' ? searchPerson : null;
    const hash = `#/${view}${id ? '/' + encodeURIComponent(id) : ''}${year === 'all' ? '' : `?year=${year}`}`;
    if (location.hash !== hash) history.replaceState(null, '', hash);
  }, [view, selected, searchPerson, year]);

  useEffect(() => {
    const onHash = () => { const h = readHash(); setView(h.view); setYear(h.year); if (h.view === 'people') setSelected(h.id); if (h.view === 'search') setSearchPerson(h.id); };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(t);
  }, [toast]);

  function exportPdf() {
    const title = document.title;
    const subject = person?.name ?? navigation.find(n => n.id === view)?.label;
    document.title = `iMessage Wrapped – ${subject}${year === 'all' ? '' : ` (${year})`}`;
    window.addEventListener('afterprint', () => { document.title = title; }, { once: true });
    window.print();
  }
  const go = (v: View) => transition(() => { setView(v); window.scrollTo(0, 0); });
  function openPerson(id: string) { transition(() => { setSelected(id); setView('people'); window.scrollTo(0, 0); }); }
  function searchWith(id: string | null) { transition(() => { setSearchPerson(id); setView('search'); window.scrollTo(0, 0); }); }
  async function action(path: string) {
    setBusy(true); setActionError(null);
    try {
      await request(path, undefined, true);
      if (path.startsWith('/contacts/')) setSelected(null);
      setRevision(r => r + 1);
      setToast(path === '/refresh' ? 'Updated just now' : 'Contacts refreshed');
    } catch (e) { setActionError(e instanceof Error ? e.message : 'Could not refresh.'); }
    finally { setBusy(false); }
  }

  const nearby = data?.top_people.filter(p => p.name.toLowerCase().includes(search.toLowerCase())).slice(0, 8) || [];
  const namesReady = data?.contacts.state === 'authorized' || data?.contacts.state === 'limited';
  const person = view === 'people' && selected ? data?.top_people.find(p => p.id === selected) : undefined;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="traffic" aria-hidden="true"><i /><i /><i /></span>
        <button className="icon-button" aria-label="Open your Wrapped" title="Open your Wrapped" onClick={() => go('story')}><SquarePen size={17} /></button>
      </div>
      <div className="sidebar-title"><span className="app-icon"><MessageCircle size={18} fill="currentColor" /></span><div><strong>Messages</strong><span>Wrapped</span></div></div>
      <label className="search"><Search size={14} /><input aria-label="Search conversations" placeholder="Search" value={search} onChange={e => setSearch(e.target.value)} /></label>
      <nav aria-label="Main navigation">
        {navigation.map(item => <button key={item.id} className={view === item.id ? 'nav-item active' : 'nav-item'} onClick={() => go(item.id)} aria-current={view === item.id ? 'page' : undefined}>
          <item.icon size={17} /><span>{item.label}</span>
        </button>)}
      </nav>
      <div className="sidebar-section"><span>Conversations</span></div>
      <div className="sidebar-conversations">
        {nearby.map((p, i) => <button className={`conversation ${view === 'people' && selected === p.id ? 'selected' : ''}`} key={p.id} onClick={() => openPerson(p.id)} style={{ '--i': i } as CSSProperties}>
          <Avatar name={p.name} />
          <span className="conversation-copy">
            <span className="conversation-top"><strong>{p.name}</strong><time>{shortDate(p.last)}</time></span>
            <span className="conversation-bottom"><small>{compact(p.total)} messages together</small><Sparkline values={p.sparkline} /></span>
          </span>
        </button>)}
        {!nearby.length && !state.loading && <p className="list-note">{search ? 'No matching conversations.' : 'Your people will appear here.'}</p>}
      </div>
      <button className="contacts-status" onClick={() => setContactPanel(v => !v)}>
        <span className={`status-dot ${namesReady ? 'ready' : ''}`} />
        <span><strong>{namesReady ? 'Contacts connected' : 'Contact names'}</strong><small>{namesReady ? `${data?.contacts.matched ?? 0} conversations matched` : 'Check name resolution'}</small></span>
        <Info size={15} />
      </button>
      <Privacy />
    </aside>

    <main className="main">
      <header className="toolbar">
        {person
          ? <div className="toolbar-person"><Avatar name={person.name} size="small" /><strong>{person.name}</strong></div>
          : <div className="toolbar-title"><strong>{navigation.find(n => n.id === view)?.label}</strong><span>iMessage Wrapped</span></div>}
        <div className="toolbar-actions">
          <label className="year-select"><span>Period</span>
            <select value={year} onChange={e => setYear(e.target.value)} aria-label="Analysis period">
              <option value="all">All time</option>{data?.years.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </label>
          {view !== 'story' && view !== 'search' && data && (view !== 'people' || selected) && <button className="icon-button" aria-label="Export as PDF" title="Export as PDF" onClick={exportPdf}><Download size={17} /></button>}
          <button className="icon-button" aria-label="Refresh local message data" title="Refresh local message data" disabled={busy} onClick={() => action('/refresh')}><RefreshCw size={17} className={busy ? 'spin' : ''} /></button>
        </div>
      </header>

      <div className="print-header" aria-hidden="true">
        <strong>iMessage Wrapped</strong>
        <span>{person?.name ?? navigation.find(n => n.id === view)?.label} · {year === 'all' ? 'All time' : year} · Exported {new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
      </div>

      {contactPanel && <section className="contact-panel" aria-label="Contact resolution status">
        <div className="section-title"><h2>Names make it personal.</h2><button className="icon-button" aria-label="Close contact status" onClick={() => setContactPanel(false)}><X size={18} /></button></div>
        <p>{data?.contacts.detail || 'Contact status will appear after Messages loads.'}</p>
        {data && <p className="muted">{number(data.contacts.loaded)} named contacts loaded. {number(data.contacts.matched)} direct conversations matched; {number(data.contacts.unmatched)} unmatched. Unknown numbers remain visible. Phone numbers and email addresses belonging to one contact are combined.</p>}
        <div className="button-row">
          {data?.contacts.state === 'not_requested' && <button className="primary" disabled={busy} onClick={() => action('/contacts/authorize')}>Allow Contacts…</button>}
          <button className="secondary" disabled={busy} onClick={() => action('/contacts/refresh')}>Retry name lookup</button>
        </div>
        <small>Reads names, phone numbers, and email addresses locally. Never edits your address book.</small>
      </section>}

      {actionError && <div className="error" role="alert">{actionError}</div>}
      {data?.stale && <div className="stale-banner" role="status"><AlertTriangle size={16} /><span><strong>The local server is running an older version.</strong> Restart it (<code>npm start</code>) to load streaks, the hour-by-weekday chart, and group chats.</span></div>}

      {state.loading ? <Loading /> : state.error ? <div className="content">
        <Empty title="Your messages aren’t available yet." body={state.error} />
        <div className="center"><button className="primary" disabled={busy} onClick={() => action('/refresh')}>Retry read-only connection</button></div>
      </div> : data ? <>
        {view === 'overview' && <Overview data={data} year={year} namesReady={namesReady} revision={revision} onStory={() => go('story')} onPeople={() => go('people')} onPerson={openPerson} onContacts={() => setContactPanel(true)} onCircles={() => go('circles')} />}
        {view === 'circles' && <Circles year={year} revision={revision} onPerson={openPerson} />}
        {view === 'search' && <SearchView year={year} revision={revision} people={data.top_people} person={searchPerson} onPerson={openPerson} onClearPerson={() => setSearchPerson(null)} />}
        {view === 'story' && (data.total ? <Story key={year} data={data} onPerson={openPerson} /> : <Empty title="No story for this period yet" body="Choose a year with message history." />)}
        {view === 'people' && <People people={data.top_people} selected={selected} onSelect={id => transition(() => setSelected(id))} year={year} revision={revision} onSearch={searchWith} />}
        {view === 'compare' && <Compare years={data.years} revision={revision} onPerson={id => { setYear('all'); openPerson(id); }} />}
        {view === 'reactions' && <div className="content view-enter">
          <div className="page-heading"><h1>Sometimes, one tap<br />says everything.</h1><p>Love, laughter, and a few emphatic exclamation marks.</p></div>
          <section className="panel"><ReactionPanel data={data.reactions} /></section>
        </div>}
      </> : null}
    </main>

    {toast && <div className="toast" role="status"><span className="toast-bubble">{toast}</span></div>}
  </div>;
}
