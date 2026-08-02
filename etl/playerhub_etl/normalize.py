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

TRANSFER_TYPE_CODES = {
    "Transfer": "TRANSFER",
    "Loan": "LOAN",
    "Return from loan": "LOAN_RETURN",
    "Draft": "DRAFT",
}

CAREER_STATE_CODES = {
    "Without Club": "WITHOUT_CLUB",
    "Retired": "RETIRED",
    "Career break": "CAREER_BREAK",
    "Unknown": "UNKNOWN",
    "---": "UNKNOWN",
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


def season_values(label: str) -> tuple[str, int, int, str]:
    cleaned = label.strip()
    split_match = re.fullmatch(r"(\d{2})/(\d{2})", cleaned)
    if split_match:
        start_short, end_short = (int(value) for value in split_match.groups())
        start_year = 1900 + start_short if start_short >= 50 else 2000 + start_short
        end_year = 1900 + end_short if end_short >= 50 else 2000 + end_short
        if end_year < start_year:
            end_year += 100
        if end_year != start_year + 1:
            raise ValueError(f"Invalid split season: {label}")
        return cleaned, start_year, end_year, "SPLIT_YEAR"

    if re.fullmatch(r"\d{4}", cleaned):
        year = int(cleaned)
        return cleaned, year, year, "CALENDAR_YEAR"

    raise ValueError(f"Unsupported season label: {label}")


def transfer_type(value: str | None) -> str:
    cleaned = optional_text(value)
    if cleaned not in TRANSFER_TYPE_CODES:
        raise ValueError(f"Unsupported transfer type: {value}")
    return TRANSFER_TYPE_CODES[cleaned]


def career_state(value: str | None) -> str | None:
    return CAREER_STATE_CODES.get((value or "").strip())


def fingerprint(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
