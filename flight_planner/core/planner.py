"""Normalize provider offers and rank them in SQLite."""
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

AIRPORTS = {"VNO": "Vilnius", "KUN": "Kaunas", "PLQ": "Palanga"}
CENTS_PER_UNIT = 100
BALANCED_SCORE_MAX = 100
COST_WEIGHT = 0.5
DURATION_WEIGHT = 1 - COST_WEIGHT
SCORE_DECIMAL_PLACES = 6
MAX_AMOUNT = 1_000_000
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
MAX_SEARCH_WORKERS = len(AIRPORTS)
RANKING_SQL = Path(__file__).resolve().parents[1] / "storage" / "ranking.sql"
OFFER_SCHEMA = """CREATE TABLE offers (
    airport TEXT, arrival TEXT, airline TEXT, currency TEXT, fare_cents INTEGER,
    stops INTEGER, flight_min INTEGER, ground_min INTEGER, ground_cents INTEGER,
    buffer_min INTEGER, transfer_min INTEGER, transfer_cents INTEGER,
    departure_day TEXT, arrival_at TEXT, departure_at TEXT
)"""
INSERT_OFFER = """INSERT INTO offers VALUES (
    :airport, :arrival, :airline, :currency, :fare_cents, :stops, :flight_min,
    :ground_min, :ground_cents, :buffer_min, :transfer_min, :transfer_cents,
    :departure_day, :arrival_at, :departure_at
)"""


@dataclass(frozen=True)
class SearchRequest:
    destination: str
    departure_day: str
    ground_by_airport: dict[str, tuple[int, int]]
    buffer_minutes: int
    arrival_transfer: tuple[int, int]
    currency: str
    flight_only: bool


def parse_amount_to_cents(value):
    amount = Decimal(value)
    if not amount.is_finite() or not 0 <= amount <= MAX_AMOUNT:
        raise ValueError(f"Enter an amount between 0 and {MAX_AMOUNT:,}.")
    cents = amount * CENTS_PER_UNIT
    if cents != cents.to_integral_value():
        raise ValueError("Use at most two decimal places for prices.")
    return int(cents)


def format_currency_amount(cents, currency):
    return f"{cents / CENTS_PER_UNIT:,.2f} {currency}"


def parse_iso_duration_minutes(value):
    match = re.fullmatch(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?", value or "")
    if not match:
        raise ValueError("Missing or unsupported flight duration.")
    days, hours, minutes = (int(part or 0) for part in match.groups())
    total = (days * HOURS_PER_DAY + hours) * MINUTES_PER_HOUR + minutes
    if not total:
        raise ValueError("Flight duration must be positive.")
    return total


def normalize_provider_offer(offer, airport, request):
    if offer["total_currency"] != request.currency:
        raise ValueError("The offer currency does not match the search currency.")
    itinerary, *_ = offer["slices"]
    segments = itinerary["segments"]
    *_, final_segment = segments
    ground_minutes, ground_cents = request.ground_by_airport[airport]
    transfer_minutes, transfer_cents = request.arrival_transfer
    return {
        "airport": airport,
        "arrival": final_segment["destination"]["iata_code"],
        "airline": offer["owner"]["name"],
        "currency": request.currency,
        "fare_cents": parse_amount_to_cents(offer["total_amount"]),
        "stops": len(segments) - 1,
        "flight_min": parse_iso_duration_minutes(itinerary["duration"]),
        "ground_min": ground_minutes,
        "ground_cents": ground_cents,
        "buffer_min": request.buffer_minutes,
        "transfer_min": transfer_minutes,
        "transfer_cents": transfer_cents,
        "departure_day": offer.get("departure_day", request.departure_day),
        "departure_at": offer.get("departure_at"),
        "arrival_at": offer.get("arrival_at"),
    }


def fetch_airport_offers(airport, request, fetch):
    try:
        response = fetch(request.currency, airport, request.destination, request.departure_day)
    except (OSError, ValueError, KeyError) as error:
        reason = getattr(error, "code", type(error).__name__)
        return [], f"{airport}: search failed ({reason})."

    offers = []
    skipped = 0
    for raw_offer in response.get("offers", []):
        try:
            offers.append(normalize_provider_offer(raw_offer, airport, request))
        except (ValueError, KeyError, TypeError, ArithmeticError):
            skipped += 1
    source = response.get("source", "live" if response.get("live_mode") else "unverified")
    note = f"{airport}: {len(offers)} usable ({source}), {skipped} skipped."
    if warnings := response.get("warnings"):
        note += " Source notes: " + " ".join(warnings)
    return offers, note


def rank_offers_by_cost_and_duration(offers):
    with closing(sqlite3.connect(":memory:")) as database:
        database.row_factory = sqlite3.Row
        database.execute(OFFER_SCHEMA)
        database.executemany(INSERT_OFFER, offers)
        return database.execute(RANKING_SQL.read_text(encoding="utf-8"), {
            "score_max": BALANCED_SCORE_MAX, "cost_weight": COST_WEIGHT,
            "duration_weight": DURATION_WEIGHT, "score_decimals": SCORE_DECIMAL_PLACES,
        }).fetchall()


def fetch_and_rank_flight_offers(request, fetch):
    with ThreadPoolExecutor(max_workers=MAX_SEARCH_WORKERS) as pool:
        results = list(pool.map(
            lambda airport: fetch_airport_offers(airport, request, fetch),
            request.ground_by_airport,
        ))
    offers = [offer for airport_offers, _ in results for offer in airport_offers]
    return rank_offers_by_cost_and_duration(offers), [note for _, note in results]
