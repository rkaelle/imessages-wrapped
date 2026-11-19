"""Pure helpers for text- and habit-based insights. Message text never leaves this process."""
import math
import re
import statistics
from collections import Counter
from datetime import date, timedelta

WORD = re.compile(r"[a-z][a-z']{2,}")
STOP = set('''
about after again all also always am an and any are aren't around as at back be because been before being but by can can't come could
did didn't do does doesn't doing don't done down even ever for from get getting go going gonna got had has have haven't having he her
here him his how i'd i'll i'm i've if in into is isn't it it's its just know like make me more most much my need never no not now of
off oh ok okay on one only or other our out over really right said say see she should so some still sure take than that that's the
their them then there there's these they they're thing think this those though time to too up us very want was wasn't way we we're
well were what what's when where which while who why will with won't would yeah yes yet you you're your yours also cause lol haha
lmao hahaha omg tho idk gonna wanna yea yeah yep nah ill im ive dont cant didnt doesnt isnt wasnt thats whats youre theyre
'''.split())

LAUGHS = [
    ('lol', re.compile(r'\blo+l+\b', re.I)),
    ('haha', re.compile(r'\b(?:ha){2,}h?\b', re.I)),
    ('lmao', re.compile(r'\blmf?ao+\b', re.I)),
    ('😂', re.compile('😂')),
]

REPLY_BINS = [(60, '<1m'), (300, '1–5m'), (900, '5–15m'), (3600, '15m–1h'), (10800, '1–3h'), (43200, '3–12h'), (86400, '12–24h')]


def tokens(text):
    return [w for w in WORD.findall(text.lower()) if w not in STOP and not w.startswith("'")]


def distinctive(person_counts, background, background_total, limit=12):
    """Words used unusually often with one person compared with all conversations."""
    total = sum(person_counts.values())
    if not total:
        return []
    floor = max(4, total // 4000)
    scored = []
    for word, n in person_counts.items():
        if n < floor:
            continue
        ratio = (n / total) / ((background.get(word, n) + 0.5) / background_total)
        scored.append((math.log(ratio) * math.log1p(n), word, n, ratio))
    scored.sort(reverse=True)
    return [{'word': w, 'count': n, 'ratio': round(r, 1)} for _, w, n, r in scored[:limit]]


def laugh_evolution(rows, texts):
    """Share of your sent messages per year that contain each laugh."""
    totals, counts = Counter(), {label: Counter() for label, _ in LAUGHS}
    for r in rows:
        if not r['sent']:
            continue
        text = texts.get(r['id'])
        if not text:
            continue
        year = r['dt'].year
        totals[year] += 1
        for label, pattern in LAUGHS:
            if pattern.search(text):
                counts[label][year] += 1
    # Years with only a handful of sent texts swing wildly, so leave them out.
    years = sorted(y for y in totals if totals[y] >= 200)
    return {'years': years, 'series': [{'label': label, 'values': [round(counts[label][y] / totals[y] * 100, 2) for y in years],
                                        'counts': [counts[label][y] for y in years]} for label, _ in LAUGHS]}


def reply_histogram(rows):
    you, them = [0] * len(REPLY_BINS), [0] * len(REPLY_BINS)
    previous = None
    for r in rows:
        if previous and previous['sent'] != r['sent']:
            seconds = (r['dt'] - previous['dt']).total_seconds()
            if 0 < seconds <= 86400:
                index = next(i for i, (edge, _) in enumerate(REPLY_BINS) if seconds <= edge)
                (you if r['sent'] else them)[index] += 1
        previous = r
    return {'bins': [label for _, label in REPLY_BINS], 'you': you, 'them': them}


def current_streak(days, today=None):
    today = today or date.today()
    day = today if today in days else today - timedelta(days=1)
    length = 0
    while day in days:
        length += 1
        day -= timedelta(days=1)
    return length


def habits(msgs, texts, by_person, reactions_given, initiations, response_times):
    """Raw numbers behind the 'texting personality' cards; the UI decides what they mean."""
    sent = [r for r in msgs if r['sent']]
    double = 0
    last = {}
    for r in msgs:
        previous = last.get(r['chat_id'])
        if r['sent'] and previous and previous['sent'] and (r['dt'] - previous['dt']).total_seconds() <= 120:
            double += 1
        last[r['chat_id']] = r
    lengths = [len(texts[r['id']]) for r in sent if texts.get(r['id'])]
    starts = them = 0
    reply = []
    for rows in by_person.values():
        i = initiations(rows)
        starts += i['you']
        them += i['them']
        reply.extend(response_times(rows))
    hours = Counter(r['dt'].hour for r in msgs)
    total = len(msgs) or 1
    return {
        'sent': len(sent),
        'late_night': round(sum(hours[h] for h in range(0, 4)) / total * 100, 1),
        'early_morning': round(sum(hours[h] for h in range(5, 9)) / total * 100, 1),
        'double_text': round(double / len(sent) * 100, 1) if sent else 0,
        'avg_length': round(statistics.mean(lengths), 1) if lengths else None,
        'tapbacks_per_100': round(reactions_given / len(sent) * 100, 1) if sent else 0,
        'starts_share': round(starts / (starts + them) * 100, 1) if starts + them else None,
        'reply_median': round(statistics.median(reply)) if reply else None,
    }
