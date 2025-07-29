"""
calendar_utils.py – utility for converting a list / dict of event dictionaries
into an RFC 5545‑compliant *.ics* calendar file.

If a full JSON dict (with a top‑level "events" key) is passed, the function
will automatically extract that list, so you can call it directly with the
output of ``API.extract_and_parse_json()``.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List

import pytz
from tzlocal import get_localzone

__all__ = ["generate_ics"]


def generate_ics(events: Any, filename: str = "calendar.ics") -> None:
    """
    Convert *events* into an ICS file and save it.

    Parameters
    ----------
    events : list[dict] | dict
        Either a list of event dictionaries **or** a dict containing an
        ``"events"`` field (the raw output from ``API.extract_and_parse_json``).
    filename : str, default "calendar.ics"
        Destination file name (overwritten if it exists).
    """
    # Accept both list and dict formats ----------------------------------
    if isinstance(events, dict) and "events" in events:
        events = events["events"]

    if not isinstance(events, list):
        raise TypeError("`events` must be a list or a dict with an 'events' key")

    # --------------------------------------------------------------------
    ics_content: str = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//Custom Calendar//NONSGML v1.0//EN\n"
        "CALSCALE:GREGORIAN\n"
    )

    local_timezone = get_localzone()

    for event in events:
        # -------- basic extraction -------------------------------------
        summary: str = event.get("summary", "Unnamed Event")

        start_date: str = event.get("start_date", "none")  # YYYY‑MM‑DD
        end_date: str = (event.get("end_date") or start_date).strip()

        start_time: str = (event.get("start_time") or "").strip()  # HH:MM or ""
        end_time: str = (event.get("end_time") or "").strip()      # HH:MM or ""

        timezone: str = event.get("timezone", "none")
        location: str = event.get("location", "")
        description: str = event.get("description", "")
        recurrence: Dict | None = event.get("recurrence")

        # -------- validation -------------------------------------------
        if str(start_date).lower() == "none":
            print(f"Skipping event '{summary}' due to missing start date.")
            continue

        # Default to local zone if none specified -----------------------
        if str(timezone).lower() == "none":
            timezone = local_timezone.key

        tz = pytz.timezone(timezone)

        # -------- build datetime objects -------------------------------
        try:
            if start_time == "":
                # All‑day event – DTSTART inclusive, DTEND exclusive -----
                start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date_obj = (
                    datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
                    + datetime.timedelta(days=1)
                )
                is_all_day = True
            else:
                # Timed event
                if not end_time:
                    end_time = start_time  # default: same time

                start_dt = tz.localize(
                    datetime.datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
                )
                end_dt = tz.localize(
                    datetime.datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
                )
                is_all_day = False
        except ValueError as exc:
            print(f"Skipping event '{summary}' due to invalid date format: {exc}")
            continue

        # -------- compose VEVENT block ---------------------------------
        if is_all_day:
            ics_event = (
                "BEGIN:VEVENT\n"
                f"SUMMARY:{summary}\n"
                f"DTSTART;VALUE=DATE:{start_date_obj.strftime('%Y%m%d')}\n"
                f"DTEND;VALUE=DATE:{end_date_obj.strftime('%Y%m%d')}\n"
                f"LOCATION:{location}\n"
                f"DESCRIPTION:{description}\n"
            )
        else:
            ics_event = (
                "BEGIN:VEVENT\n"
                f"SUMMARY:{summary}\n"
                f"DTSTART;TZID={timezone}:{start_dt.strftime('%Y%m%dT%H%M%S')}\n"
                f"DTEND;TZID={timezone}:{end_dt.strftime('%Y%m%dT%H%M%S')}\n"
                f"LOCATION:{location}\n"
                f"DESCRIPTION:{description}\n"
            )

        # -------- recurrence (optional) --------------------------------
        if recurrence:
            freq = str(recurrence.get("frequency", "none")).upper()
            interval = recurrence.get("interval", 1)
            count = recurrence.get("count")

            if freq in {"DAILY", "WEEKLY", "MONTHLY"}:
                rrule = f"RRULE:FREQ={freq};INTERVAL={interval}"
                if count:
                    rrule += f";COUNT={count}"
                ics_event += rrule + "\n"

        ics_event += "END:VEVENT\n"
        ics_content += ics_event

    # --------------------------------------------------------------------
    ics_content += "END:VCALENDAR"

    with open(filename, "w", encoding="utf-8") as file:
        file.write(ics_content)

    print(f"ICS file saved as {filename}")
