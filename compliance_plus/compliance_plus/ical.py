# Copyright (c) 2026, KlyONIX Tech Consulting Pvt Ltd and contributors
# For license information, please see license.txt

"""A small iCalendar (RFC 5545) writer: all-day and timed events, enough for a subscribed feed."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

LINE_LIMIT = 75  # octets per line before folding


def escape(text: str) -> str:
	return (
		(text or "")
		.replace("\\", "\\\\")
		.replace(";", "\\;")
		.replace(",", "\\,")
		.replace("\r\n", "\\n")
		.replace("\n", "\\n")
	)


def fold(line: str) -> str:
	"""Split a line longer than 75 octets, continuing each part with a space (RFC 5545 3.1)."""
	parts, current = [], b""
	for character in line:
		encoded = character.encode()
		if len(current) + len(encoded) > LINE_LIMIT - (1 if parts else 0):
			parts.append(current.decode())
			current = b""
		current += encoded
	parts.append(current.decode())
	return "\r\n ".join(parts)


def utc(moment: datetime, zone: str) -> str:
	return moment.replace(tzinfo=ZoneInfo(zone)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def event_lines(event: dict, stamp: str, zone: str) -> list[str]:
	lines = ["BEGIN:VEVENT", f"UID:{event['uid']}", f"DTSTAMP:{stamp}"]
	start = event["start"]
	if isinstance(start, datetime):
		end = event.get("end") or start + timedelta(hours=1)
		lines += [f"DTSTART:{utc(start, zone)}", f"DTEND:{utc(end, zone)}"]
	else:
		lines += [
			f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
			f"DTEND;VALUE=DATE:{start + timedelta(days=1):%Y%m%d}",
			"TRANSP:TRANSPARENT",  # a due date does not make anyone busy
		]
	lines.append(f"SUMMARY:{escape(event['summary'])}")
	if event.get("description"):
		lines.append(f"DESCRIPTION:{escape(event['description'])}")
	if event.get("url"):
		lines.append(f"URL:{event['url']}")
	lines.append("END:VEVENT")
	return lines


def calendar(name: str, events: list[dict], zone: str, now: datetime | None = None) -> str:
	"""The whole feed as text; `events` have uid, start (a date, or a datetime in `zone`),
	optional end, summary, description and url."""
	stamp = (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
	lines = [
		"BEGIN:VCALENDAR",
		"VERSION:2.0",
		"PRODID:-//Compliance Plus//Calendar Feed//EN",
		"CALSCALE:GREGORIAN",
		"METHOD:PUBLISH",
		f"X-WR-CALNAME:{escape(name)}",
		f"X-WR-TIMEZONE:{zone}",
		# Ask calendar apps to look again every few hours.
		"REFRESH-INTERVAL;VALUE=DURATION:PT6H",
		"X-PUBLISHED-TTL:PT6H",
	]
	for event in events:
		lines += event_lines(event, stamp, zone)
	lines.append("END:VCALENDAR")
	return "\r\n".join(fold(line) for line in lines) + "\r\n"
