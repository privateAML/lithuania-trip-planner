"""City suggestions and validation of search inputs."""
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from flight_planner.core.planner import AIRPORTS, HOURS_PER_DAY, MINUTES_PER_HOUR, SearchRequest, parse_amount_to_cents

MAX_GROUND_MINUTES = 7 * HOURS_PER_DAY * MINUTES_PER_HOUR
NO_GROUND_TRAVEL = (0, 0)

def parse_ground_travel_minutes(value):
    minutes = int(value)
    if not 0 <= minutes <= MAX_GROUND_MINUTES:
        raise ValueError(f"Minutes must be between 0 and {MAX_GROUND_MINUTES}.")
    return minutes


def parse_ground_travel_estimate(value):
    minutes, fare = value.split(",")
    return parse_ground_travel_minutes(minutes), parse_amount_to_cents(fare.strip())

ORIGINS = ("Kaunas", "Klaipėda", "Vilnius", "Palanga", "Šiauliai", "Panevėžys",
           "Alytus", "Marijampolė", "Utena", "Tauragė", "Telšiai")
DESTINATIONS = {"Amsterdam": "AMS", "Athens": "ATH", "Barcelona": "BCN",
                "Berlin": "BER", "Brussels": "BRU", "Copenhagen": "CPH",
                "Dublin": "DUB", "Helsinki": "HEL", "Lisbon": "LIS", "London": "LON",
                "Madrid": "MAD", "Milan": "MIL", "Oslo": "OSL", "Paris": "PAR",
                "Porto": "OPO", "Prague": "PRG", "Riga": "RIX", "Rome": "ROM",
                "Stockholm": "STO", "Tallinn": "TLL", "Vienna": "VIE", "Warsaw": "WAW"}


def normalize_city_name(value):
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def find_city_prefix_matches(value, choices):
    prefix = normalize_city_name(value)
    return tuple(city for city in choices if normalize_city_name(city).startswith(prefix))


def validate_and_normalize_starting_city(value):
    key = normalize_city_name(value)
    for city in ORIGINS:
        if normalize_city_name(city) == key:
            return city
    raise ValueError("Choose a starting city from the list, for example Kaunas or Klaipėda.")


@dataclass(frozen=True)
class TripForm:
    starting_city: str
    destination_label: str
    request: SearchRequest


def resolve_destination_airport_code(value):
    destination = value.strip()
    for city, airport_code in DESTINATIONS.items():
        if normalize_city_name(city) == normalize_city_name(destination):
            return airport_code
    return destination.upper()


def build_validated_trip_request(origin, destination, departure, currency, ground_fields, buffer, transfer):
    starting_city = validate_and_normalize_starting_city(origin)
    departure_date = date.fromisoformat(departure.strip())
    if departure_date < date.today():
        raise ValueError("Use a current or future departure date.")
    destination_code = resolve_destination_airport_code(destination)
    currency_code = currency.strip().upper()
    if not all(re.fullmatch("[A-Z]{3}", code) for code in (destination_code, currency_code)):
        raise ValueError("Use three-letter destination and currency codes.")
    ground_estimates = {
        airport: parse_ground_travel_estimate(value)
        for airport, value in ground_fields.items() if value.strip()
    }
    flight_only = not ground_estimates and not transfer.strip()
    if not flight_only and (ground_estimates.keys() != AIRPORTS.keys() or not transfer.strip()):
        raise ValueError("For full-trip comparison, fill in all ground and arrival estimates.")
    request = SearchRequest(
        destination=destination_code,
        departure_day=departure_date.isoformat(),
        ground_by_airport=dict.fromkeys(AIRPORTS, NO_GROUND_TRAVEL) if flight_only else ground_estimates,
        buffer_minutes=0 if flight_only else parse_ground_travel_minutes(buffer),
        arrival_transfer=NO_GROUND_TRAVEL if flight_only else parse_ground_travel_estimate(transfer),
        currency=currency_code,
        flight_only=flight_only,
    )
    return TripForm(starting_city, destination.strip(), request)
