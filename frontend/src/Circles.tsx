import { useResource } from './api';
import type { Network } from './types';
import { Empty, Loading, number } from './components';
import { Constellation } from './charts';

export function Circles({ year, revision, onPerson }: { year: string; revision: number; onPerson: (id: string) => void }) {
  const state = useResource<Network>(`/network?year=${year}`, revision);
  const d = state.data;
  return <div className="content circles view-enter">
    <div className="page-heading"><h1>Your circles.</h1><p>People linked through the group chats you share. Bigger dots talk more; hover to see a group’s people.</p></div>
    {state.loading ? <Loading text="Mapping your group chats…" /> : state.error ? <div className="error" role="alert">{state.error}</div>
      : !d || !d.groups.length ? <Empty title="No busy group chats in this period" body="Circles appear once a group has a few dozen messages." />
        : <section className="panel">
          <div className="section-title">
            <div><h2>{number(d.groups.length)} groups, {number(d.people.length)} people.</h2><p>Click anyone to open your direct conversation.</p></div>
            <div className="chart-legend" aria-hidden="true"><span><i className="swatch group-dot" /> Group chat</span><span><i className="swatch person-dot" /> Person</span></div>
          </div>
          <Constellation groups={d.groups} people={d.people} links={d.links} onPerson={onPerson} />
          <p className="method">The busiest {d.groups.length} group chats in this period and their most active members. Lines are weighted by how much each person posts in that group. Your own messages are not shown as a dot.</p>
        </section>}
  </div>;
}
