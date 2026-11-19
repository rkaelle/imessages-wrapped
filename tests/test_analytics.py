"""All write attempts below target synthetic databases in temporary directories only."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from backend.database import connect, read_rows
from backend.analytics import Analytics, EPOCH, response_times, rhythm, streak, initiations, late_night
from backend import insights
from datetime import date
from backend.contacts import normalize
from backend.text import decode, EMOJI


class FakeContacts:
    def __init__(self): self.enabled=False
    def resolve(self,value):
        return {'key':'same-person','name':'Alex Example'} if self.enabled and value in ('+15555550100','alex@example.test') else None
    def status(self): return {'state':'authorized','detail':'Synthetic contacts','loaded':1}


class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'synthetic.db'
        c=sqlite3.connect(self.path)
        c.executescript('''
          CREATE TABLE message (guid TEXT,date INTEGER,is_from_me INTEGER,handle_id INTEGER,associated_message_type INTEGER,associated_message_guid TEXT,associated_message_emoji TEXT,cache_has_attachments INTEGER,is_system_message INTEGER,item_type INTEGER,date_retracted INTEGER,is_spam INTEGER,text TEXT,attributedBody BLOB);
          CREATE TABLE chat (style INTEGER,display_name TEXT);
          CREATE TABLE handle (id TEXT);
          CREATE TABLE chat_message_join (chat_id INTEGER,message_id INTEGER);
          CREATE TABLE chat_handle_join (chat_id INTEGER,handle_id INTEGER);
          INSERT INTO handle VALUES ('+15555550100'),('alex@example.test'),('+15555550101');
          INSERT INTO chat VALUES (45,NULL),(43,'Synthetic group'),(45,NULL);
          INSERT INTO chat_handle_join VALUES (1,1),(2,1),(2,3),(3,2);
        ''')
        entries=[(1,0,0,1,2024,1),(2,60,1,0,2024,1),(3,120,0,1,2024,1),(4,180,0,1,2024,2),(5,240,1,0,2024,3),(6,300,1,0,2025,1)]
        for ident,offset,sent,handle,year,chat in entries:
            stamp=int(((datetime(year,6,1,12,tzinfo=timezone.utc)-EPOCH).total_seconds()+offset)*1e9)
            c.execute('INSERT INTO message VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(str(ident),stamp,sent,handle,0,None,None,0,0,0,0,0,'hello 😊',None))
            c.execute('INSERT INTO chat_message_join VALUES (?,?)',(chat,ident))
        # Duplicate join must not duplicate a message.
        c.execute('INSERT INTO chat_message_join VALUES (1,1)')
        for code in [2000,2001,3000,2006,2007,4000]:
            c.execute('INSERT INTO message VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(f'r{code}',stamp+code*int(1e9),0,1,code,'p:0/6','🦊' if code==2006 else None,0,0,0,0,0,None,None))
            c.execute('INSERT INTO chat_message_join VALUES (1,last_insert_rowid())')
        c.commit();c.close()
        self.contacts=FakeContacts();self.a=Analytics(self.contacts,self.path);self.a.load()

    def tearDown(self): self.temp.cleanup()

    def test_read_only_connection_rejects_mutations(self):
        c=connect(self.path)
        for sql in ['DELETE FROM message','UPDATE message SET text=NULL',"INSERT INTO handle VALUES ('bad')",'DROP TABLE message','PRAGMA query_only=OFF',"ATTACH DATABASE ':memory:' AS other"]:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.DatabaseError): c.execute(sql)
        c.close()
        self.assertEqual(len(read_rows(self.path)),12)

    def test_no_database_creation_when_missing(self):
        p=Path(self.temp.name)/'missing.db'
        with self.assertRaises(sqlite3.OperationalError): connect(p)
        self.assertFalse(p.exists())

    def test_deduplicates_and_excludes_reaction_events(self):
        s=self.a.summary('all')
        self.assertEqual(s['total'],6)
        self.assertEqual(s['sent'],3)
        self.assertEqual(s['groups'],1)
        self.assertEqual(s['people'],2)

    def test_outgoing_messages_attributed_to_chat_partner(self):
        p=max(self.a.summary('all')['top_people'],key=lambda p:p['total'])
        self.assertEqual((p['sent'],p['received']),(2,2))

    def test_contacts_merge_phone_and_email(self):
        self.contacts.enabled=True;self.a.reindex()
        s=self.a.summary('all')
        self.assertEqual(s['people'],1)
        self.assertEqual(s['top_people'][0]['total'],5)
        self.assertEqual(s['contacts']['matched'],1)

    def test_tapbacks_count_additions_separately(self):
        r=self.a.summary('all')['reactions']
        self.assertEqual(r['total'],3)
        self.assertEqual(r['removed'],1)
        self.assertEqual(r['other_events'],2)
        self.assertIn('🦊',[x['emoji'] for x in r['items']])

    def test_calendar_year_and_zero_baseline(self):
        self.assertEqual(self.a.summary('2024')['total'],5)
        c=self.a.compare('2024','2025')
        self.assertEqual(c['change'],-80)
        self.assertIsNone(self.a.compare('2023','2024')['change'])
        self.assertEqual(len(c['before']['timeline']),12)

    def test_empty_period_and_missing_person(self):
        s=self.a.summary('2020')
        self.assertEqual(s['total'],0)
        self.assertIsNone(s['busiest_day'])
        with self.assertRaises(KeyError):self.a.person('missing','all')

    def test_person_emoji_and_responses(self):
        p=max(self.a.summary('2024')['top_people'],key=lambda p:p['total'])
        d=self.a.person(p['id'],'2024')
        self.assertEqual(d['responses']['you'],60)
        self.assertEqual(d['responses']['them'],60)
        self.assertEqual(d['emojis']['items'][0],{'emoji':'😊','count':3})

    def test_invalid_blob_is_never_treated_as_message_text(self):
        self.assertIsNone(decode(None,b'NSString metadata verylongfakebody'))
        self.assertEqual(decode('hello',b'bad'),'hello')
        self.assertEqual(EMOJI.findall('photo \ufffc hello 👩‍💻 ❤️'),['👩‍💻','❤️'])

    def test_normalizes_phone_and_email(self):
        self.assertEqual(normalize('+1 (555) 555-0100'),normalize('5555550100'))
        self.assertEqual(normalize(' ALEX@EXAMPLE.TEST '),'alex@example.test')

    def test_response_gaps_over_24_hours_excluded(self):
        t=datetime.now(timezone.utc)
        r=response_times([{'dt':t,'sent':0},{'dt':t+timedelta(days=2),'sent':1}])
        self.assertIsNone(r['you'])

    def test_rhythm_grid_counts_weekday_and_hour(self):
        t=datetime(2024,6,3,9,tzinfo=timezone.utc)  # a Monday
        g=rhythm([{'dt':t},{'dt':t+timedelta(minutes=5)},{'dt':t+timedelta(days=1,hours=1)}])
        self.assertEqual((len(g),len(g[0])),(7,24))
        self.assertEqual(g[0][9],2)
        self.assertEqual(g[1][10],1)
        self.assertEqual(sum(map(sum,g)),3)

    def test_longest_streak_of_consecutive_days(self):
        t=datetime(2024,1,1,12,tzinfo=timezone.utc)
        days=[0,1,2,5,6,6,7,8,20]
        s=streak([{'dt':t+timedelta(days=d)} for d in days])
        self.assertEqual(s,{'days':4,'start':'2024-01-06','end':'2024-01-09'})
        self.assertIsNone(streak([]))

    def test_initiations_after_quiet_gap(self):
        t=datetime(2024,1,1,tzinfo=timezone.utc)
        rows=[{'dt':t,'sent':1},{'dt':t+timedelta(minutes=1),'sent':0},{'dt':t+timedelta(hours=8),'sent':0},{'dt':t+timedelta(hours=20),'sent':1}]
        self.assertEqual(initiations(rows),{'you':2,'them':1,'gap_hours':6})

    def test_late_night_share_and_summary_fields(self):
        t=datetime(2024,1,1,tzinfo=timezone.utc)
        self.assertEqual(late_night([{'dt':t.replace(hour=1)},{'dt':t.replace(hour=13)}]),50.0)
        self.assertIsNone(late_night([]))
        s=self.a.summary('2024')
        self.assertEqual(sum(map(sum,s['rhythm'])),5)
        self.assertEqual(s['top_groups'][0]['name'],'Synthetic group')
        self.assertEqual(s['calendar']['year'],2024)
        self.assertEqual(len(s['top_people'][0]['sparkline']),12)
        self.assertEqual(sum(s['top_people'][0]['sparkline']),s['top_people'][0]['total'])

    def test_search_finds_text_case_insensitively_and_scopes_to_person(self):
        r=self.a.search('HELLO')
        self.assertEqual(r['total'],6)
        self.assertTrue(all('hello' in x['text'] for x in r['results']))
        self.assertEqual(r['results'][0]['id'],6)  # newest first
        pid=max(self.a.summary('all')['top_people'],key=lambda p:p['total'])['id']
        self.assertEqual(self.a.search('hello',person=pid)['total'],4)
        self.assertEqual(self.a.search('h')['total'],0)

    def test_on_this_day_groups_earlier_years(self):
        r=self.a.on_this_day(date(2026,6,1))
        self.assertEqual([y['year'] for y in r['years']],[2025,2024])
        self.assertEqual(r['years'][1]['total'],5)
        self.assertEqual(r['years'][1]['years_ago'],2)
        self.assertTrue(r['years'][1]['snippets'])
        self.assertEqual(self.a.on_this_day(date(2026,1,1))['years'],[])

    def test_network_links_group_senders(self):
        n=self.a.network('all',max_people=5)
        self.assertEqual(n['groups'],[])  # the synthetic group is below the activity floor
        self.assertEqual(self.a.summary('2024')['top_groups'][0]['total'],1)

    def test_person_words_media_and_reply_histogram(self):
        p=max(self.a.summary('2024')['top_people'],key=lambda p:p['total'])
        d=self.a.person(p['id'],'2024')
        self.assertEqual((d['reply_histogram']['you'][0],d['reply_histogram']['them'][0]),(1,1))  # one 60s reply each way
        self.assertEqual(d['media'],{'photos':0,'videos':0,'voice':0,'links':0,'files':0})
        self.assertEqual(d['words'],[])  # 'hello' appears too rarely to be distinctive

    def test_distinctive_words_prefer_unusual_vocabulary(self):
        background={'pizza':10,'hello':1000,'tahoe':12}
        person={'pizza':5,'hello':40,'tahoe':12}
        words=[w['word'] for w in insights.distinctive(person,background,10000)]
        self.assertEqual(words[0],'tahoe')
        self.assertNotIn('the',insights.tokens('The THE the tahoe'))
        self.assertEqual(insights.tokens("we're at Tahoe"),['tahoe'])

    def test_current_streak_allows_today_to_be_quiet(self):
        today=date(2026,3,10)
        days={date(2026,3,9),date(2026,3,8),date(2026,3,7),date(2026,3,1)}
        self.assertEqual(insights.current_streak(days,today),3)
        self.assertEqual(insights.current_streak(days|{today},today),4)
        self.assertEqual(insights.current_streak({date(2026,3,1)},today),0)

    def test_laughs_and_habits_in_summary(self):
        s=self.a.summary('all')
        self.assertEqual(s['laughs']['years'],[])  # too few sent texts per year to chart
        t=datetime(2024,1,1,tzinfo=timezone.utc)
        rows=[{'id':i,'sent':1,'dt':t} for i in range(200)]+[{'id':999,'sent':1,'dt':t.replace(year=2025)}]
        texts={i:('lol ok' if i<50 else 'hahaha') for i in range(200)}
        laughs=insights.laugh_evolution(rows,texts)
        self.assertEqual(laughs['years'],[2024])
        self.assertEqual({x['label']:x['values'][0] for x in laughs['series']}['lol'],25.0)
        self.assertEqual(set(s['habits']),{'sent','late_night','early_morning','double_text','avg_length','tapbacks_per_100','starts_share','reply_median'})
        self.assertIs(self.a.summary('all'),s)  # cached until reload
        self.a.reindex()
        self.assertIsNot(self.a.summary('all'),s)
        self.assertEqual(insights.reply_histogram([]),{'bins':[b for _,b in insights.REPLY_BINS],'you':[0]*7,'them':[0]*7})


if __name__=='__main__':unittest.main()

class StructuredTextTests(unittest.TestCase):
    def test_decodes_attributed_string_without_metadata(self):
        try:
            from Foundation import NSAttributedString, NSArchiver
        except ImportError:
            self.skipTest('macOS Foundation bridge required')
        body=NSAttributedString.alloc().initWithString_('Synthetic hello 👩‍💻 ❤️')
        blob=bytes(NSArchiver.archivedDataWithRootObject_(body))
        self.assertEqual(decode(None,blob),'Synthetic hello 👩‍💻 ❤️')
