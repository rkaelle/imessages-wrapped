# iMessage Wrapped

A local React site inspired by Apple Messages: a conversation sidebar, blue and gray bubbles, and a personal story built from the message history on your Mac.

## Run

Requires macOS, Python 3.10+, and Node.js 20.19+ (or 22.12+).

```sh
./setup.sh
npm start
```

Open **http://127.0.0.1:8501**. The server listens only on loopback. For frontend development, run `npm run dev` and open the Vite URL; it proxies the local API on port 8501.

## Features

- Overview of message volume, people, group chats, and monthly activity.
- Five-chapter Wrapped story for all time or a calendar year.
- Searchable relationship pages: sent/received timeline, observed reply gaps, shared emojis, and reactions.
- Calendar-year comparisons with archive coverage and changes by person.
- Real Tapback addition/removal counts, including custom emoji reactions.
- Contacts connection status, explicit permission request, and retry. Multiple phone numbers/emails linked to one macOS contact become one person.

## Permissions

Messages lives at `~/Library/Messages/chat.db`. Enable Full Disk Access for the application launching the server (for example Ghostty or Terminal). macOS may require quitting and reopening that application before access works.

Contacts has a separate permission. In the sidebar, open **Contact names**, click **Allow Contacts…**, and approve the macOS dialog. If denied, enable Contacts access for the application named by macOS in System Settings → Privacy & Security → Contacts, then click **Retry name lookup**. Numbers without an accessible matching contact remain numbers; the app does not guess names.

## Data handling

The new runtime is `backend/` plus `frontend/`. It does not send messages, edit contacts, upload data, or expose a message-composer endpoint. No remote fonts, analytics, CDN scripts, or cloud APIs are used. All analysis and name mappings stay in memory. Message bodies are read only for selected-person emoji analysis; the API returns emoji counts, not message bodies.

The only Messages connection factory is `backend/database.py`: SQLite `mode=ro`, `PRAGMA query_only=ON`, and an authorizer that rejects all actions except reads, selections, and query functions. It never creates a missing Messages database. Contacts uses fetch requests only, never save requests. Do not run this app through a public tunnel or expose its port: local results contain personal information.

## What the numbers mean

- Messages are ordinary message rows, excluding system events, retracted messages, spam, and associated events such as Tapbacks. A canonical chat join avoids duplicate counting.
- Direct-chat outgoing messages are attributed using the chat participants, rather than the outgoing message's often-empty handle. Group chats are identified using style 43 or multiple participants.
- Calendar years and activity hours use the Mac's local timezone. Only history available on this Mac is included. Current and partially synced years are not normalized or extrapolated.
- Reply times are medians of consecutive direct-message sender switches, excluding gaps over 24 hours. They do not indicate read time, availability, or relationship quality.
- Tapback totals count addition events during the period. Removal events are separate. These totals do not claim to measure currently active reactions. Stickers and other associated events are excluded and counted separately.
- Emoji counts use text or a structured typedstream decoder. Unsupported/missing bodies are excluded with coverage shown. No binary printable-text guessing, sentiment scoring, or implausible longest-message records.

## Verify

```sh
npm test
npm run build
```

Tests use synthetic databases in temporary directories. Mutation-rejection tests never run against your Messages database.

The former Streamlit implementation is preserved in `legacy/` for reference. It is not imported or served by the React app; its extra dependencies are not needed.
