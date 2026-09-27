"""Pydantic request models used to validate every PocketSmart form."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HOME_ROOMS = ("Living Room", "Kitchen", "Bedroom", "Dining Area", "Study", "Kids Room")
HOME_STYLES = ("Modern", "Traditional", "Minimalist", "Luxury", "Rustic", "Contemporary")
HOME_COLOURS = ("Neutral", "Warm", "Cool", "Earthy", "Bold")

PARTY_TYPES = ("Birthday", "Wedding", "Corporate", "Anniversary", "Baby Shower", "Farewell")
PARTY_NEEDS = ("Catering", "Decoration", "Entertainment", "Venue", "Photography", "Contingency")

JEWELRY_OCCASIONS = ("Wedding", "Birthday", "Anniversary", "Engagement", "Party", "Daily Wear")
JEWELRY_STYLES = ("Classic", "Modern", "Traditional", "Minimalist", "Statement", "Vintage")
JEWELRY_METALS = ("Gold", "Silver", "Rose Gold", "Platinum", "Diamond")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def _normalise_choices(values: Any, allowed: tuple[str, ...]) -> list[str]:
    """Map each entry onto its canonical option, case-insensitively."""
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    out: list[str] = []
    for entry in values:
        text = _blank_to_empty(entry)
        for option in allowed:
            if option.lower() == text.lower():
                out.append(option)
                break
        else:
            out.append(text)
    return out


def _clean_list(values: Any, allowed: tuple[str, ...], field_name: str) -> list[str]:
    """Normalise a multi-select payload into an ordered, de-duplicated list.

    Accepts a repeated form field (what browsers send), a JSON array, or a
    single comma-separated string (what some HTTP clients and scripts send).
    """
    if values is None:
        return []
    if isinstance(values, str):
        raw: list[Any] = [values]
    elif isinstance(values, (list, tuple, set)):
        raw = list(values)
    else:
        raise ValueError(f"{field_name} must be a list of values")

    # Flatten any comma-separated entry so "A,B" and ["A", "B"] behave the same.
    candidates: list[Any] = []
    for entry in raw:
        if isinstance(entry, str):
            candidates.extend(part.strip() for part in entry.split(",") if part.strip())
        elif entry is not None:
            candidates.append(entry)

    cleaned: list[str] = []
    for candidate in candidates:
        if candidate is None:
            continue
        text = str(candidate).strip()
        if not text:
            continue
        if allowed and text not in allowed:
            raise ValueError(f"{text!r} is not a valid {field_name}")
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


def _blank_to_empty(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _match_choice(value: Any, allowed: tuple[str, ...], field_name: str) -> str:
    """Case-insensitively resolve a choice, so the JSON API is forgiving.

    ``"wedding"`` and ``"Wedding"`` both resolve to the canonical option. An
    unknown value is returned unchanged so pydantic raises its normal error.
    """
    text = _blank_to_empty(value)
    for option in allowed:
        if option.lower() == text.lower():
            return option
    return text


class RegisterPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    accept_terms: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Name must contain at least one letter")
        return value

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterPayload":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        has_letter = re.search(r"[A-Za-z]", self.password)
        has_digit = re.search(r"\d", self.password)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain at least one letter and one number")
        return self


class LoginPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    remember: bool = False

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class ContactPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    subject: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=10, max_length=2000)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value
class HomePlannerPayload(BaseModel):
    """Adaptive home interior planner form."""

    model_config = ConfigDict(str_strip_whitespace=True)

    total_budget: float = Field(gt=0, le=100_000_000)
    rooms: list[str] = Field(min_length=1, max_length=len(HOME_ROOMS))
    lights: int = Field(default=1, ge=0, le=200)
    ceiling_fans: int = Field(default=1, ge=0, le=200)
    dining_tables: int = Field(default=0, ge=0, le=50)
    sofas: int = Field(default=0, ge=0, le=50)
    storage_units: int = Field(default=0, ge=0, le=50)
    style: Literal["Modern", "Traditional", "Minimalist", "Luxury", "Rustic", "Contemporary"] = "Modern"
    colour_preference: Literal["Neutral", "Warm", "Cool", "Earthy", "Bold"] = "Neutral"
    notes: str = Field(default="", max_length=600)
    furniture: str = Field(default="", max_length=120)

    @field_validator("rooms", mode="before")
    @classmethod
    def validate_rooms(cls, value: Any) -> list[str]:
        rooms = _clean_list(_normalise_choices(value, HOME_ROOMS), HOME_ROOMS, "room")
        if not rooms:
            raise ValueError("Select at least one room")
        return rooms

    @field_validator("style", "colour_preference", mode="before")
    @classmethod
    def normalise_choices(cls, value: Any, info) -> str:
        allowed = HOME_STYLES if info.field_name == "style" else HOME_COLOURS
        return _match_choice(value, allowed, info.field_name)

    @field_validator("notes", "furniture", mode="before")
    @classmethod
    def normalise_text(cls, value: Any) -> str:
        return _blank_to_empty(value)

    @model_validator(mode="after")
    def quantities_sane(self) -> "HomePlannerPayload":
        if self.lights + self.ceiling_fans <= 0:
            raise ValueError("Add at least one light or ceiling fan")
        return self


class PartyPlannerPayload(BaseModel):
    """Party budget planner form."""

    model_config = ConfigDict(str_strip_whitespace=True)

    total_budget: float = Field(gt=0, le=100_000_000)
    party_type: Literal[
        "Birthday", "Wedding", "Corporate", "Anniversary", "Baby Shower", "Farewell"
    ] = "Birthday"
    guests: int = Field(ge=1, le=5000)
    venue_preference: str = Field(default="Any", max_length=80)
    needs: list[str] = Field(default_factory=list, max_length=len(PARTY_NEEDS))
    notes: str = Field(default="", max_length=600)

    @field_validator("needs", mode="before")
    @classmethod
    def validate_needs(cls, value: Any) -> list[str]:
        return _clean_list(_normalise_choices(value, PARTY_NEEDS), PARTY_NEEDS, "need")

    @field_validator("party_type", mode="before")
    @classmethod
    def normalise_party_type(cls, value: Any) -> str:
        return _match_choice(value, PARTY_TYPES, "party_type")

    @field_validator("notes", "venue_preference", mode="before")
    @classmethod
    def normalise_text(cls, value: Any) -> str:
        return _blank_to_empty(value)

    @model_validator(mode="after")
    def budget_per_guest(self) -> "PartyPlannerPayload":
        per_guest = self.total_budget / self.guests
        if per_guest < 150:
            raise ValueError(
                f"Budget per guest is just Rs {per_guest:,.0f}. Increase the budget or "
                "reduce the guest count (minimum Rs 150 per guest)."
            )
        if not self.needs:
            self.needs = ["Catering", "Decoration", "Entertainment"]
        return self


class JewelryPlannerPayload(BaseModel):
    """Jewelry planner form - text plus an optional outfit image."""

    model_config = ConfigDict(str_strip_whitespace=True)

    total_budget: float = Field(gt=0, le=100_000_000)
    occasion: Literal[
        "Wedding", "Birthday", "Anniversary", "Engagement", "Party", "Daily Wear"
    ] = "Wedding"
    style: Literal[
        "Classic", "Modern", "Traditional", "Minimalist", "Statement", "Vintage"
    ] = "Classic"
    metal: Literal["Gold", "Silver", "Rose Gold", "Platinum", "Diamond"] = "Gold"
    preferences: str = Field(default="", max_length=600)

    @field_validator("occasion", "style", "metal", mode="before")
    @classmethod
    def normalise_choices(cls, value: Any, info) -> str:
        allowed = {
            "occasion": JEWELRY_OCCASIONS,
            "style": JEWELRY_STYLES,
            "metal": JEWELRY_METALS,
        }[info.field_name]
        return _match_choice(value, allowed, info.field_name)

    @field_validator("preferences", mode="before")
    @classmethod
    def normalise_text(cls, value: Any) -> str:
        return _blank_to_empty(value)


class TransactionPayload(BaseModel):
    """Manual spend entry tracked on the dashboard or a plan page."""

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(min_length=2, max_length=180)
    amount: float = Field(gt=0, le=10_000_000)
    category: str = Field(default="General", max_length=40)
    spent_on: str = Field(default="", max_length=20)
    recommendation_id: int | None = None

    @field_validator("spent_on", mode="before")
    @classmethod
    def normalise_date(cls, value: Any) -> str:
        return _blank_to_empty(value)

    @field_validator("category", mode="before")
    @classmethod
    def normalise_category(cls, value: Any) -> str:
        return _blank_to_empty(value) or "General"


def error_message(exc: Exception) -> str:
    """Flatten a pydantic ``ValidationError`` into a single friendly line."""
    errors = getattr(exc, "errors", None)
    if not callable(errors):
        return str(exc)
    parts: list[str] = []
    for err in errors():
        location = ".".join(str(item) for item in err.get("loc", ()) if item != "__root__")
        message = err.get("msg", "Invalid value")
        message = re.sub(r"^Value error,\s*", "", message)
        parts.append(f"{location}: {message}" if location else message)
    return " | ".join(parts) or "Please check the form and try again."