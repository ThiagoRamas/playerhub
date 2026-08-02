from datetime import date
import hashlib
import json
import re
from typing import Any


MISSING_TEXT = {"", "N/A", "---", "Unknown"}
NON_CLUB_NAMES = {"Retired", "Without Club", "Unknown", "---", "Career break"}

POSITION_CODES = {
    "Goalkeeper": "GOALKEEPER",
    "Defender - Centre-Back": "CENTRE_BACK",
    "Defender - Right-Back": "RIGHT_BACK",
    "Defender - Left-Back": "LEFT_BACK",
    "Midfield - Defensive Midfield": "DEFENSIVE_MIDFIELD",
    "Midfield - Central Midfield": "CENTRAL_MIDFIELD",
    "Midfield - Right Midfield": "RIGHT_MIDFIELD",
    "Midfield - Left Midfield": "LEFT_MIDFIELD",
    "Midfield - Attacking Midfield": "ATTACKING_MIDFIELD",
    "Attack - Second Striker": "SECOND_STRIKER",
    "Attack - Right Winger": "RIGHT_WINGER",
    "Attack - Left Winger": "LEFT_WINGER",
    "Attack - Centre-Forward": "CENTRE_FORWARD",
}

CAREER_STATUSES = {
    "Retired": "RETIRED",
    "Without Club": "WITHOUT_CLUB",
    "Career break": "CAREER_BREAK",
    "Unknown": "UNKNOWN",
    "---": "UNKNOWN",
}

FOOT_CODES = {
    "right": "RIGHT",
    "left": "LEFT",
    "both": "BOTH",
}


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return None if cleaned in MISSING_TEXT else cleaned


def clean_entity_name(value: str | None, external_id: int | str | None = None) -> str:
    cleaned = optional_text(value) or f"Unknown {external_id}"
    if external_id is not None:
        cleaned = re.sub(rf"\s*\({re.escape(str(external_id))}\)\s*$", "", cleaned)
    return cleaned.strip()


def optional_int(value: str | None, *, zero_is_null: bool = False) -> int | None:
    text = optional_text(value)
    if text is None:
        return None
    result = int(float(text))
    return None if zero_is_null and result == 0 else result


def optional_date(value: str | None) -> date | None:
    text = optional_text(value)
    return date.fromisoformat(text) if text else None


def preferred_foot(value: str | None) -> str:
    return FOOT_CODES.get((value or "").strip().lower(), "UNKNOWN")


def career_status(current_club_name: str | None) -> str:
    return CAREER_STATUSES.get((current_club_name or "").strip(), "ACTIVE")


def split_citizenships(value: str | None) -> list[str]:
    text = optional_text(value)
    if not text:
        return []
    return list(dict.fromkeys(part.strip() for part in re.split(r"\s{2,}", text) if part.strip()))


def position_code(value: str | None) -> str | None:
    return POSITION_CODES.get((value or "").strip())


def fingerprint(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
