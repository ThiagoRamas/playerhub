from datetime import date
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]


class ClubSummary(BaseModel):
    id: int
    name: str
    slug: str | None
    country: str | None
    logo_url: str | None
    is_complete: bool


class ClubDetail(ClubSummary):
    team_type: str
    data_as_of: date | None
    linked_players: int


class SquadMember(BaseModel):
    id: int
    display_name: str
    image_url: str | None
    date_of_birth: date | None
    position: str | None
    citizenships: list[str]
    latest_market_value: int | None
    membership_type: str
    squad_status: Literal["SQUAD", "ON_LOAN", "LOANED_OUT"]


class PlayerClub(BaseModel):
    id: int
    name: str
    membership_type: str
    is_current: bool


class PlayerSummary(BaseModel):
    id: int
    display_name: str
    image_url: str | None
    date_of_birth: date | None
    position: str | None
    citizenships: list[str]
    current_clubs: list[str]
    latest_market_value: int | None


class PlayerDetail(BaseModel):
    id: int
    display_name: str
    full_name: str | None
    slug: str | None
    image_url: str | None
    date_of_birth: date | None
    date_of_death: date | None
    place_of_birth: str | None
    country_of_birth: str | None
    height_cm: int | None
    preferred_foot: str
    career_status: str
    position: str | None
    citizenships: list[str]
    current_clubs: list[PlayerClub]
    latest_market_value: int | None
    data_as_of: date | None


class PerformanceItem(BaseModel):
    season: str
    club: str
    competition: str
    appearances: int | None
    goals: int | None
    assists: int | None
    minutes_played: int | None
    yellow_cards: int | None
    red_cards: int | None


class MarketValueItem(BaseModel):
    valued_on: date
    amount: int
    currency_code: str | None


class TransferItem(BaseModel):
    transfer_date: date | None
    season: str | None
    from_team: str
    to_team: str
    transfer_type: str
    market_value_amount: int | None
    fee_amount: int | None
    currency_code: str | None


class InjuryItem(BaseModel):
    season: str | None
    reason: str
    started_on: date | None
    ended_on: date | None
    days_missed: int | None
    games_missed: int | None
