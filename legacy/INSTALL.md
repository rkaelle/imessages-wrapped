# Installation Guide

## Quick Start

### Option 1: Using the Setup Script (Recommended)

```bash
chmod +x setup.sh
./setup.sh
```

Then run the app:
```bash
source venv/bin/activate
streamlit run web/app.py
```

### Option 2: Manual Setup

1. **Create a virtual environment:**
```bash
python3 -m venv venv
```

2. **Activate the virtual environment:**
```bash
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the app:**
```bash
streamlit run web/app.py
```

5. **When done, deactivate:**
```bash
deactivate
```

## Verifying Installation

After setup, verify everything works:

```bash
source venv/bin/activate
python test_basic.py
```

All tests should pass if installation was successful.

## System Requirements

- macOS (for iMessage database access)
- Python 3.8 or higher
- Full Disk Access for Terminal (System Preferences > Privacy & Security)

## Troubleshooting

### "No module named 'pandas'" or similar
- Make sure you activated the virtual environment: `source venv/bin/activate`
- You should see `(venv)` in your terminal prompt

### "Failed to connect to iMessage database"
- Grant Full Disk Access to Terminal in System Preferences > Privacy & Security
- Ensure Messages app has synced data to this Mac

### Streamlit won't start
- Make sure virtual environment is activated
- Try: `python -m streamlit run web/app.py`

### Homebrew pip warnings
- Using a virtual environment (recommended approach) avoids these warnings
- Virtual environments are isolated and won't affect system packages
