"""
api.py – core wrapper for extracting calendar events from free‑form text.

Example
-------
>>> from api import API
>>> api = API(
...     gemini_api_key="YOUR_KEY",
...     location="Australia/Adelaide",
...     language="English",
... )
>>> reply = api.gemini_normal(raw_text)
>>> events_data = api.extract_and_parse_json(reply)
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from zoneinfo import ZoneInfo  # Python 3.9+
import tzlocal                 # pip install tzlocal
import google.generativeai as genai

# --------------------------------------------------------------------------- #
# Logging                                                                     #
# --------------------------------------------------------------------------- #
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

# --------------------------------------------------------------------------- #
# API wrapper                                                                 #
# --------------------------------------------------------------------------- #
class API:
    """
    Lightweight helper around Gemini models.

    Parameters
    ----------
    gemini_api_key : str
        Your Gemini API key (mandatory).
    location : str, default "Australia/Adelaide"
        Home time‑zone or user‑supplied description used in the prompt.
    language : str, default "English"
        Language for all JSON values (e.g. "English", "Chinese").
    default_model : str, default "gemini-2.5-flash"
        Gemini model name used by default.

    Attributes
    ----------
    api_key : str
        Stored API key.
    location : str
        Time‑zone / location string inserted in prompts.
    language : str
        Target language for JSON field values.
    default_model : str
        Default Gemini model.
    """

    def __init__(
        self,
        gemini_api_key: str,
        location: str = "Australia/Adelaide",
        language: str = "English",
        default_model: str = "gemini-2.5-flash",
    ) -> None:
        self.api_key: str = gemini_api_key.strip()
        if not self.api_key:
            raise ValueError("Gemini API key must not be empty.")

        genai.configure(api_key=self.api_key)

        self.location: str = location
        self.language: str = language
        self.default_model: str = default_model

        # Prompt header is generated dynamically in `generate_prompt()`
        # because it includes today's date.
    # --------------------------------------------------------------------- #
    # Public methods                                                        #
    # --------------------------------------------------------------------- #
    def generate_prompt(self) -> str:
        """Build the system prompt used for event extraction."""
        current_date = datetime.date.today().strftime("%Y-%m-%d")
        return f"""Extract every calendar event mentioned in the following text and return only a single JSON object like this:
{{
  "events": [
    {{
      "summary": "Team Meeting",
      "start_date": "2025-03-10",
      "end_date": "2025-03-10",
      "start_time": "10:00",
      "end_time":   "11:00",
      "timezone":   "Australia/Adelaide",
      "location":   "Room 101",
      "description":"Quarterly planning session \\n organiser: ACME Corp \\n source: ACME webpage",
      "tz_conversion": "Sydney 10:30‑11:30 → Adelaide 10:00‑11:00",
      "recurrence": {{
        "frequency": "daily",
        "interval":  1,
        "count":     5
      }}
    }}
  ]
}}

Rules
-----
1. If the same event is repeated in the text, merge the duplicates.
2. Convert every time to the correct time‑zone which is {self.location}.
3. Output MUST be valid JSON with no extra text. If a timezone conversion is
   needed, fill the “tz_conversion” field with the before‑and‑after information;
   otherwise, leave this field empty.
4. All field values must be written in {self.language}.
5. The description field should include (when available): event summary(should less than 5 setence),
   organiser, and the source from where the event was extracted (e.g. ACME webpage).
6. The times shown in event details are usually given in the event’s local time zone. If that differs from the user’s current time zone, they’ll need to convert the times accordingly.

(Current date: {current_date})

Here is the text:
"""

    def gemini_normal(self, message) -> str:
        """Send `message` to Gemini and return raw text reply."""
        history=[]
        model = genai.GenerativeModel(self.default_model)
        new_message = {"role": "user", "parts": [message]}
        history.append(new_message)
        response = model.generate_content(history)
        return response.text

    def gemini_calendar(self, message: str) -> str:
        """Build prompt + user text, then call Gemini for calendar extraction."""
        prompt = self.generate_prompt()
        full_message = f"{prompt}\n{message}"
        print(
            "Generate calendar event ....\n"
            f"timezone: {self.location},\n"
            f"language: {self.language},\n"
        )
        return self.gemini_normal(full_message)

    # --------------------------------------------------------------------- #
    # Static helpers                                                        #
    # --------------------------------------------------------------------- #
    def extract_and_parse_json(self, reply_text: str) -> Optional[Dict[str, Any]]:
        """
        Extract the first JSON object from `reply_text` and parse it.

        Returns
        -------
        dict | None
            Parsed JSON if successful, otherwise None.
        """
        json_pattern = r"\{.*\}"
        match = re.search(json_pattern, reply_text, re.DOTALL)
        if not match:
            logger.warning("No JSON object found in Gemini reply.")
            return None

        json_str = match.group(0)
        try:
            parsed = json.loads(json_str)
            logger.info(
                "JSON parsed successfully (%d event(s) found).",
                len(parsed.get("events", [])),
            )
            return parsed
        except json.JSONDecodeError as exc:
            logger.error("JSON decoding failed: %s", exc)
            return None

    def extract_event(self, message: str) -> Dict[str, Any] | None:
        """
        High‑level helper: ask Gemini to extract events, then parse JSON and
        optionally report any timezone conversions.
        """
        raw_json = self.gemini_calendar(message)
        data = self.extract_and_parse_json(raw_json)

        if data:
            for event in data.get("events", []):
                tz_info = event.get("tz_conversion", "")
                if tz_info:
                    print(
                        f'Timezone conversion triggered: "{tz_info}" '
                        f'in "{event.get("summary", "")}"'
                    )
        return data

