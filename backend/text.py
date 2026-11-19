"""Structured decoding only; no printable-byte heuristics or metadata fallback."""
import re
from collections import Counter

EMOJI = re.compile('[\U0001F1E6-\U0001F1FF]{2}|[\U0001F300-\U0001FAFF\u2600-\u27BF](?:\uFE0F|[\U0001F3FB-\U0001F3FF])?(?:\u200D[\U0001F300-\U0001FAFF\u2600-\u27BF](?:\uFE0F|[\U0001F3FB-\U0001F3FF])?)*')


def decode(text, blob):
    if isinstance(text,str) and text:
        return text
    if not blob:
        return None
    try:
        import typedstream
        from typedstream.types.foundation import NSString
        from typedstream.archiving import GenericArchivedObject
        obj = typedstream.unarchive_from_data(bytes(blob))
        if isinstance(obj, GenericArchivedObject):
            clazz = obj.clazz
            is_attributed = False
            while clazz:
                is_attributed |= clazz.name == b'NSAttributedString'
                clazz = clazz.superclass
            if is_attributed and obj.contents:
                field = obj.contents[0]
                if field.encodings == [b'@'] and len(field.values) == 1:
                    value = field.values[0]
                    if isinstance(value, NSString):
                        return value.value if isinstance(value.value, str) else None
    except Exception:
        return None
    return None


def emojis(rows):
    counts = Counter()
    decoded = unreadable = 0
    for row in rows:
        text = decode(row['text'],row['attributedBody'])
        if text is None:
            unreadable += 1
        else:
            decoded += 1
            counts.update(EMOJI.findall(text))
    return {'items':[{'emoji':k,'count':v} for k,v in counts.most_common(8)],'decoded':decoded,'unreadable':unreadable}
