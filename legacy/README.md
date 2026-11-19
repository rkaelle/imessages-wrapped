# iMessage Wrapped

Ever wondered who actually texts you back? Or which group chat you're ignoring? This thing analyzes your iMessage history and turns it into shareable stats.

Basically Spotify Wrapped but for your texts.

## What it does

Digs through your iMessage database (yeah, Apple stores everything locally) and shows you:

- Who you text the most
- Who ghosts you the hardest
- Your most chaotic group chats
- What time you're most likely to be on your phone
- How many messages you've sent (prepare to be horrified)
- Your "texting personality" based on your habits

You can look at the past year or go full send and analyze everything since you got your first iPhone.

## Setup

You need Python 3.8 or newer. Install dependencies:

```bash
pip install -r requirements.txt
```

**Important:** On macOS, you'll need to give Terminal (or whatever you're running this from) Full Disk Access. Go to System Preferences > Privacy & Security > Full Disk Access and enable it. Otherwise this won't be able to read your messages.

## Running it

### Web version (easier)

```bash
streamlit run web/app.py
```

Opens in your browser. You can toggle between past year vs all time, click around, and export images to share. There's an option to anonymize names if you don't want people knowing who you text.

### Code version

If you just want the images without the web interface:

```python
from src.database import iMessageDatabase
from src.analyzer import MessageAnalyzer
from src.visualizations import VisualizationGenerator
from src.utils import get_time_period

db = iMessageDatabase()
start_date, end_date = get_time_period("past_year")
messages = db.get_messages(start_date, end_date)

analyzer = MessageAnalyzer(messages)
viz = VisualizationGenerator()
viz.generate_all_images(analyzer, "Past Year", anonymize=False)
```

Images get saved to `output/` as PNGs.

## What gets generated

- Summary (total messages, sent vs received)
- Top contacts
- Time heatmap (hour by hour, day by day)
- Ghosting analysis (who leaves you on read)
- Fast responders (who actually texts back)
- Group chat rankings
- Texting personality card

## Privacy stuff

Everything runs locally. No data leaves your computer. The app only reads from your iMessage database, it doesn't modify anything. No APIs, no cloud uploads, no tracking. Just your Mac and your messages.

## Troubleshooting

**"Failed to connect to iMessage database"**
You probably didn't enable Full Disk Access. Check System Preferences.

**"No data available"**
Try "All Time" instead of "Past Year" - you might not have much recent activity.

**It's slow**
If you have like 100,000+ messages this will take a minute. First run is slower, then it caches stuff.

## How it works

Apple stores all your iMessages in a SQLite database at `~/Library/Messages/chat.db`. This reads from that database (specifically the `message`, `handle`, `chat`, and join tables) and does some basic stats.

Dates are stored as nanoseconds since Jan 1, 2001 because Apple is quirky like that. The code handles the conversion.

Ghosting is calculated as "messages they sent you within 24h after you messaged them" divided by "total messages you sent them". Response time is the median gap between your message and their next one.

## License

MIT - do whatever you want with it

## Built with

- Python 3
- Streamlit for the web UI
- Pandas for data wrangling
- Matplotlib/Seaborn for charts
- Your questionable texting habits
