import hashlib
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from .database import read_rows, text_rows, corpus_rows, attachment_rows, DB_PATH
from .contacts import normalize
from .text import emojis, decode
from . import insights

EPOCH = datetime(2001,1,1,tzinfo=timezone.utc)
REACTIONS = {2000:('❤️','Love'),2001:('👍','Like'),2002:('👎','Dislike'),2003:('😂','Laugh'),2004:('‼️','Emphasis'),2005:('❓','Question'),2006:('✨','Custom emoji')}


def delta(current, previous):
    return round((current-previous)/previous*100,1) if previous else None


def timeline(rows, years):
    bins = {f'{y}-{m:02d}':{'period':f'{y}-{m:02d}','sent':0,'received':0} for y in years for m in range(1,13)}
    for r in rows:
        key=r['dt'].strftime('%Y-%m')
        if key in bins:
            bins[key]['sent' if r['sent'] else 'received']+=1
    return list(bins.values())


def rhythm(rows):
    grid=[[0]*24 for _ in range(7)]
    for r in rows:
        grid[r['dt'].weekday()][r['dt'].hour]+=1
    return grid


def streak(rows):
    days=sorted({r['dt'].date() for r in rows})
    best=None
    start=previous=None
    for d in days:
        if previous is None or d-previous!=timedelta(days=1):
            start=d
        if best is None or (d-start).days+1>best['days']:
            best={'days':(d-start).days+1,'start':start.isoformat(),'end':d.isoformat()}
        previous=d
    return best


def initiations(rows, gap=6*3600):
    you=them=0
    previous=None
    for r in rows:
        if previous is None or (r['dt']-previous['dt']).total_seconds()>=gap:
            if r['sent']:
                you+=1
            else:
                them+=1
        previous=r
    return {'you':you,'them':them,'gap_hours':gap//3600}


def late_night(rows):
    return round(sum(r['dt'].hour<4 for r in rows)/len(rows)*100,1) if rows else None


def calendar(rows, year):
    return {'year':year,'days':dict(Counter(r['dt'].date().isoformat() for r in rows if r['dt'].year==year))}


def reply_samples(rows):
    samples=[]
    previous=None
    for r in rows:
        if previous and r['sent'] and not previous['sent']:
            seconds=(r['dt']-previous['dt']).total_seconds()
            if 0<seconds<=86400:
                samples.append(seconds)
        previous=r
    return samples


def response_times(rows):
    sent, received = [], []
    previous = None
    for r in rows:
        if previous and previous['sent'] != r['sent']:
            seconds=(r['dt']-previous['dt']).total_seconds()
            if 0<seconds<=86400:
                (sent if r['sent'] else received).append(seconds)
        previous=r
    return {'you':round(statistics.median(sent)) if sent else None,'them':round(statistics.median(received)) if received else None,'you_samples':len(sent),'their_samples':len(received)}


class Analytics:
    def __init__(self, contacts, path=DB_PATH):
        self.contacts=contacts
        self.path=path
        self.rows=[]
        self.people={}
        self.emoji_cache={}
        self.loaded_at=None
        self._texts=None
        self._media=None
        self._background=None
        self.word_cache={}
        self.summary_cache={}

    def load(self):
        raw=read_rows(self.path)
        rows=[]
        for r in raw:
            try:
                r['dt']=(EPOCH+timedelta(seconds=r['date']/1e9)).astimezone()
            except (ValueError,OverflowError):
                continue
            if r['dt']>datetime.now().astimezone()+timedelta(days=1):
                continue
            rows.append(r)
        self.rows=rows
        self._texts=self._media=self._background=None
        self.word_cache={}
        self.summary_cache={}
        self.loaded_at=datetime.now().astimezone().isoformat()
        self.reindex()

    def identify(self, identifier):
        identity=normalize(identifier)
        resolved=self.contacts.resolve(identifier)
        key='contact:'+resolved['key'] if resolved else 'address:'+identity
        pid=hashlib.sha256(key.encode()).hexdigest()[:20]
        if pid not in self.people:
            self.people[pid]={'id':pid,'name':resolved['name'] if resolved else str(identifier),'resolved':bool(resolved),'identifiers':set()}
        self.people[pid]['identifiers'].add(str(identifier))
        return pid

    def reindex(self):
        self.people={}
        for r in self.rows:
            r['person_id']=r['sender_id']=None
            if not r['identifier']:
                continue
            if not r['is_group']:
                r['person_id']=self.identify(r['identifier'])
            elif not r['sent']:
                # In a group, a received message's identifier is its sender.
                r['sender_id']=self.identify(r['identifier'])
        self.emoji_cache={}
        self.word_cache={}
        self.summary_cache={}

    def texts(self):
        if self._texts is None:
            self._texts={}
            for row in corpus_rows(self.path):
                text=decode(row['text'],row['attributedBody'])
                if text:
                    self._texts[row['id']]=text.replace('\ufffc','').strip()
        return self._texts

    def media(self):
        if self._media is None:
            kinds={}
            for row in attachment_rows(self.path):
                mime=row['mime_type'] or ''
                kind='photos' if mime.startswith('image/') else 'videos' if mime.startswith('video/') else 'audio' if mime.startswith('audio/') else 'files'
                kinds.setdefault(row['message_id'],kind)
            self._media=kinds
        return self._media

    def background(self):
        if self._background is None:
            texts=self.texts()
            counts=Counter()
            for r in self.messages(self.rows):
                if r['id'] in texts:
                    counts.update(insights.tokens(texts[r['id']]))
            self._background=(counts,sum(counts.values()) or 1)
        return self._background

    def period(self, year):
        return [r for r in self.rows if year=='all' or r['dt'].year==int(year)]

    @staticmethod
    def messages(rows):
        return [r for r in rows if (r['reaction_type'] or 0)==0]

    def ranked(self, rows):
        groups=defaultdict(list)
        for r in self.messages(rows):
            if r['person_id']:
                groups[r['person_id']].append(r)
        result=[]
        for pid,msgs in groups.items():
            p=self.people[pid]
            sent=sum(bool(r['sent']) for r in msgs)
            # Twelve monthly totals ending at this person's last message in the period.
            end=msgs[-1]['dt']
            months=[((end.year*12+end.month-1-i)//12,(end.year*12+end.month-1-i)%12+1) for i in range(11,-1,-1)]
            monthly=Counter((r['dt'].year,r['dt'].month) for r in msgs)
            result.append({'id':pid,'name':p['name'],'resolved':p['resolved'],'total':len(msgs),'sent':sent,'received':len(msgs)-sent,'first':msgs[0]['dt'].date().isoformat(),'last':msgs[-1]['dt'].date().isoformat(),
                           'sparkline':[monthly[m] for m in months]})
        return sorted(result,key=lambda p:(-p['total'],p['name']))

    def summary(self, year):
        # Cached per period; load() and reindex() clear it.
        if year not in self.summary_cache:
            self.summary_cache[year]=self._summary(year)
        return self.summary_cache[year]

    def _summary(self, year):
        rows=self.period(year)
        msgs=self.messages(rows)
        years=sorted({r['dt'].year for r in self.messages(self.rows)},reverse=True)
        sent=sum(bool(r['sent']) for r in msgs)
        daily=Counter(r['dt'].date().isoformat() for r in msgs)
        hours=Counter(r['dt'].hour for r in msgs)
        ranked=self.ranked(rows)
        coverage={'first':msgs[0]['dt'].date().isoformat() if msgs else None,'last':msgs[-1]['dt'].date().isoformat() if msgs else None}
        matched=sum(p['resolved'] for p in ranked)
        previous=self.messages(self.period(str(int(year)-1))) if year!='all' else []
        group_counts=Counter(r['chat_id'] for r in msgs if r['is_group'])
        group_names={r['chat_id']:r['chat_name'] for r in msgs if r['is_group']}
        busiest=daily.most_common(1)[0][0] if daily else None
        return {'year':year,'years':years,'loaded_at':self.loaded_at,'total':len(msgs),'sent':sent,'received':len(msgs)-sent,
                'people':len(ranked),'groups':len({r['chat_id'] for r in msgs if r['is_group']}),'active_days':len(daily),
                'busiest_day':{'date':daily.most_common(1)[0][0],'count':daily.most_common(1)[0][1]} if daily else None,
                'peak_hour':hours.most_common(1)[0][0] if hours else None,'coverage':coverage,
                'previous_total':len(previous),'change':delta(len(msgs),len(previous)) if year!='all' else None,
                'top_people':ranked,'timeline':timeline(msgs,sorted(years) if year=='all' else [int(year)]),
                'contacts':{**self.contacts.status(),'matched':matched,'unmatched':len(ranked)-matched},
                'reactions':self.reactions(rows),'rhythm':rhythm(msgs),'streak':streak(msgs),'late_night':late_night(msgs),
                'calendar':calendar(msgs,int(year) if year!='all' else int(busiest[:4])) if busiest else None,
                'top_groups':[{'id':str(cid),'name':group_names[cid] or self.group_label(cid,msgs),'total':n} for cid,n in group_counts.most_common(5)],
                'streaks':self.streaks(msgs,year),'habits':self.habits(rows,msgs),'laughs':self.laughs()}

    def group_label(self, chat_id, msgs, limit=3):
        senders=Counter(r['sender_id'] for r in msgs if r['chat_id']==chat_id and r['sender_id'])
        names=[self.people[pid]['name'].split()[0] for pid,_ in senders.most_common(limit)]
        return ', '.join(names) if names else None

    def streaks(self, msgs, year):
        days=defaultdict(set)
        for r in msgs:
            if r['person_id']:
                days[r['person_id']].add(r['dt'].date())
        longest,current=[],[]
        live=year in ('all',str(datetime.now().year))
        for pid,d in days.items():
            best=streak([{'dt':datetime.combine(x,datetime.min.time())} for x in d])
            if best and best['days']>=2:
                longest.append({'id':pid,'name':self.people[pid]['name'],**best})
            if live:
                n=insights.current_streak(d)
                if n>=2:
                    current.append({'id':pid,'name':self.people[pid]['name'],'days':n})
        return {'longest':sorted(longest,key=lambda x:-x['days'])[:5],'current':sorted(current,key=lambda x:-x['days'])[:5]}

    def habits(self, rows, msgs):
        by_person=defaultdict(list)
        for r in msgs:
            if r['person_id']:
                by_person[r['person_id']].append(r)
        given=sum(1 for r in rows if r['sent'] and (r['reaction_type'] or 0) in REACTIONS)
        return insights.habits(msgs,self.texts(),by_person,given,initiations,reply_samples)

    def laughs(self):
        if 'laughs' not in self.word_cache:
            self.word_cache['laughs']=insights.laugh_evolution(self.messages(self.rows),self.texts())
        return self.word_cache['laughs']

    def words(self, pid, year, msgs):
        key=(pid,year)
        if key not in self.word_cache:
            texts=self.texts()
            counts=Counter()
            for r in msgs:
                if r['id'] in texts:
                    counts.update(insights.tokens(texts[r['id']]))
            background,total=self.background()
            self.word_cache[key]=insights.distinctive(counts,background,total)
        return self.word_cache[key]

    def media_mix(self, msgs):
        kinds=self.media()
        texts=self.texts()
        mix=Counter(kinds[r['id']] for r in msgs if r['id'] in kinds)
        mix['links']=sum(1 for r in msgs if 'http' in texts.get(r['id'],''))
        mix['voice']=mix.pop('audio',0)
        return {k:mix.get(k,0) for k in ['photos','videos','voice','links','files']}

    def on_this_day(self, today=None):
        today=today or datetime.now().astimezone().date()
        texts=self.texts()
        by_year=defaultdict(list)
        for r in self.messages(self.rows):
            d=r['dt'].date()
            if d.month==today.month and d.day==today.day and d.year<today.year:
                by_year[d.year].append(r)
        result=[]
        for year in sorted(by_year,reverse=True):
            msgs=by_year[year]
            people=Counter(r['person_id'] for r in msgs if r['person_id'])
            snippets=[]
            if people:
                top=people.most_common(1)[0][0]
                lines=[r for r in msgs if r['person_id']==top and 2<=len(texts.get(r['id'],''))<=180]
                start=max(0,len(lines)//2-2)
                snippets=[{'text':texts[r['id']],'sent':bool(r['sent']),'time':r['dt'].strftime('%H:%M')} for r in lines[start:start+4]]
            result.append({'year':year,'years_ago':today.year-year,'total':len(msgs),'date':msgs[0]['dt'].date().isoformat(),
                           'people':[{'id':pid,'name':self.people[pid]['name'],'count':n} for pid,n in people.most_common(3)],'snippets':snippets})
        return {'date':today.isoformat(),'years':result}

    def network(self, year, max_groups=18, max_people=60):
        msgs=[r for r in self.messages(self.period(year)) if r['is_group']]
        groups=Counter(r['chat_id'] for r in msgs)
        chosen=[cid for cid,n in groups.most_common(max_groups) if n>=30]
        names={r['chat_id']:r['chat_name'] for r in msgs}
        edges=Counter((r['sender_id'],r['chat_id']) for r in msgs if r['chat_id'] in chosen and r['sender_id'])
        weight=Counter()
        for (pid,_),n in edges.items():
            weight[pid]+=n
        people=[pid for pid,n in weight.most_common(max_people) if n>=10]
        keep=set(people)
        return {'groups':[{'id':str(cid),'name':names[cid] or self.group_label(cid,msgs) or 'Unnamed group','total':groups[cid],
                           'yours':sum(1 for r in msgs if r['chat_id']==cid and r['sent'])} for cid in chosen],
                'people':[{'id':pid,'name':self.people[pid]['name'],'total':weight[pid]} for pid in people],
                'links':[{'person':pid,'group':str(cid),'weight':n} for (pid,cid),n in edges.items() if pid in keep]}

    def search(self, query, year='all', person=None, limit=80):
        needle=query.casefold().strip()
        if len(needle)<2:
            return {'query':query,'total':0,'results':[]}
        texts=self.texts()
        hits=[]
        total=0
        for r in reversed(self.messages(self.period(year))):
            if person and r['person_id']!=person:
                continue
            text=texts.get(r['id'])
            if not text or needle not in text.casefold():
                continue
            total+=1
            if len(hits)<limit:
                if r['person_id']:
                    chat={'kind':'person','id':r['person_id'],'name':self.people[r['person_id']]['name']}
                else:
                    chat={'kind':'group','id':str(r['chat_id']),'name':r['chat_name'] or 'Group chat'}
                sender=None if r['sent'] or not r['sender_id'] else self.people[r['sender_id']]['name']
                hits.append({'id':r['id'],'text':text[:400],'sent':bool(r['sent']),'at':r['dt'].isoformat(),'chat':chat,'sender':sender})
        return {'query':query,'total':total,'results':hits}

    @staticmethod
    def reactions(rows):
        counts=Counter()
        sent=Counter()
        removed=unsupported=0
        for r in rows:
            code=r['reaction_type'] or 0
            if code in REACTIONS:
                emoji,label=REACTIONS[code]
                if code==2006:
                    emoji=r['reaction_emoji'] or '✨'
                    label='Custom emoji'
                counts[(emoji,label)]+=1
                sent[(emoji,label)]+=bool(r['sent'])
            elif 3000<=code<=3006:
                removed+=1
            elif code:
                unsupported+=1
        return {'items':[{'emoji':e,'label':l,'count':n,'sent':sent[(e,l)],'received':n-sent[(e,l)]} for (e,l),n in counts.most_common()],
                'total':sum(counts.values()),'removed':removed,'other_events':unsupported,
                'method':'Tapback addition events in this period. Removals are shown separately; additions are not the count of currently active reactions. Stickers and other associated events are excluded.'}

    def person(self, pid, year):
        if pid not in self.people:
            raise KeyError('Contact not found. Refresh the people list.')
        rows=[r for r in self.period(year) if r['person_id']==pid]
        msgs=self.messages(rows)
        p=self.people[pid]
        cache_key=(pid,year)
        if cache_key not in self.emoji_cache:
            self.emoji_cache[cache_key]=emojis(text_rows([r['id'] for r in msgs],self.path))
        years=sorted({r['dt'].year for r in msgs})
        sent=sum(bool(r['sent']) for r in msgs)
        monthly=timeline(msgs,years if year=='all' else [int(year)])
        change=None
        if year!='all':
            prior=[r for r in self.messages(self.period(str(int(year)-1))) if r['person_id']==pid]
            change=delta(len(msgs),len(prior))
        return {'id':pid,'name':p['name'],'resolved':p['resolved'],'addresses':len(p['identifiers']),'total':len(msgs),'sent':sent,'received':len(msgs)-sent,
                'first':msgs[0]['dt'].date().isoformat() if msgs else None,'last':msgs[-1]['dt'].date().isoformat() if msgs else None,
                'timeline':monthly,'responses':response_times(msgs),'emojis':self.emoji_cache[cache_key],
                'reactions':self.reactions(rows),'change':change,'rhythm':rhythm(msgs),'streak':streak(msgs),
                'initiations':initiations(msgs),'late_night':late_night(msgs),
                'reply_histogram':insights.reply_histogram(msgs),'words':self.words(pid,year,msgs),'media':self.media_mix(msgs)}

    def compare(self, left, right):
        a=self.summary(left)
        b=self.summary(right)
        ar={p['id']:p for p in a['top_people']}
        br={p['id']:p for p in b['top_people']}
        people=[]
        for pid in ar.keys()|br.keys():
            av=ar.get(pid,{}).get('total',0)
            bv=br.get(pid,{}).get('total',0)
            people.append({'id':pid,'name':self.people[pid]['name'],'before':av,'after':bv,'difference':bv-av,'change':delta(bv,av)})
        return {'before':{k:a[k] for k in ['year','total','sent','received','people','groups','active_days','coverage','timeline']},
                'after':{k:b[k] for k in ['year','total','sent','received','people','groups','active_days','coverage','timeline']},
                'change':delta(b['total'],a['total']),'people':sorted(people,key=lambda p:-abs(p['difference']))[:30],
                'note':'Calendar-year totals from messages available on this Mac. Missing history and incomplete years can affect comparisons.'}
