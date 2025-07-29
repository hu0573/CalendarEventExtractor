# CalendarEventExtractor

Convert messy, free‑form text (emails, web pages, chats …) into a clean **`.ics`** calendar file in one step.

## What it does

1. **Extracts events with Google Gemini**  
   The model summarises the text and returns structured JSON for every date‑time it finds.

2. **Automatic time‑zone handling**  
   All start / end times are converted to your home zone (configurable).

3. **Duplicate detection**  
   Repeated descriptions of the same event are merged into a single entry.

4. **Exports RFC 5545**  
   The resulting list is written to an iCalendar file that you can import into Google Calendar, Outlook, Apple Calendar, etc.

## Quick start

```bash
# 1. Clone the repo
git clone https://github.com/<your‑user>/CalendarEventExtractor.git
cd CalendarEventExtractor

# 2. Install dependencies
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt                     # google‑generativeai, pytz, tzlocal, …

# 3. Set your Gemini API key
export GEMINI_API_KEY="sk‑xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 4. Run the notebook (or write your own script)
jupyter lab RunFromHere.ipynb
