"""Read public Ryanair fare-finder quotes for the selected date."""
import json
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

REQUEST_TIMEOUT_SECONDS = 9
FLEXIBLE_DATE_DAYS = 7
MAX_DIRECT_FLIGHT_MINUTES = 12 * 60

ZONES = {
    "at": "Vienna", "be": "Brussels", "cz": "Prague", "de": "Berlin",
    "dk": "Copenhagen", "ee": "Tallinn", "es": "Madrid", "fi": "Helsinki",
    "fr": "Paris", "gb": "London", "gr": "Athens", "ie": "Dublin",
    "it": "Rome", "lt": "Vilnius", "lv": "Riga", "nl": "Amsterdam",
    "no": "Oslo", "pl": "Warsaw", "pt": "Lisbon", "se": "Stockholm",
    "ch": "Zurich", "hr": "Zagreb", "hu": "Budapest", "ro": "Bucharest",
    "bg": "Sofia", "sk": "Bratislava", "mt": "Malta", "lu": "Luxembourg",
}
EXCEPTIONS = {"TFS": "Atlantic/Canary", "TFN": "Atlantic/Canary",
              "LPA": "Atlantic/Canary", "ACE": "Atlantic/Canary",
              "FUE": "Atlantic/Canary", "PDL": "Atlantic/Azores", "TER": "Atlantic/Azores",
              "FNC": "Atlantic/Madeira", "PXO": "Atlantic/Madeira",
              "CY": "Asia/Nicosia", "TR": "Europe/Istanbul"}
METROS = {"LON": "STN,LTN,LGW", "PAR": "BVA,ORY,CDG", "MIL": "BGY,MXP,LIN",
          "ROM": "CIA,FCO", "STO": "ARN,NYO", "BRU": "BRU,CRL",
          "BCN": "BCN,GRO,REU", "OSL": "OSL,TRF"}
NEARBY = {"BER": "LEJ,DRS", "AMS": "EIN,RTM", "LIS": "OPO,FAO",
          "VIE": "BTS", "WAW": "WMI", "MAD": "VLL", "HEL": "TMP",
          "CPH": "MMX", "BCN": "GRO,REU"}
CALENDAR_COUNTRIES = {
    code: country for country, codes in {
        "es": "BCN GRO REU MAD VLL", "gb": "STN LTN LGW",
        "fr": "BVA ORY CDG", "it": "BGY MXP LIN FCO CIA",
        "de": "BER LEJ DRS", "nl": "AMS EIN RTM", "pt": "LIS OPO FAO",
        "be": "BRU CRL", "dk": "CPH", "se": "ARN NYO MMX",
        "no": "OSL TRF", "pl": "WAW WMI", "at": "VIE", "sk": "BTS",
        "gr": "ATH", "ie": "DUB", "fi": "HEL TMP", "cz": "PRG",
        "lv": "RIX", "ee": "TLL",
    }.items() for code in codes.split()
}


def fetch_json_response(url):
    with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def iter_ryanair_daily_fares(airport, arrival, day, last):
    months = {day[:7], last[:7]}
    country = CALENDAR_COUNTRIES[arrival]
    for month in sorted(months):
        query = urlencode({"outboundMonthOfDate": month + "-01", "currency": "EUR", "market": "en-gb"})
        url = f"https://services-api.ryanair.com/farfnd/v4/oneWayFares/{airport}/{arrival}/cheapestPerDay?{query}"
        for fare in fetch_json_response(url)["outbound"]["fares"]:
            if not fare.get("price") or not day <= fare["day"] <= last:
                continue
            yield {"outbound": {**fare, "arrivalAirport": {
                "iataCode": arrival, "city": {"countryCode": country}}}}


def calculate_ryanair_flight_duration_minutes(outbound):
    arrival = outbound["arrivalAirport"]
    country = arrival["city"]["countryCode"].lower()
    zone = EXCEPTIONS.get(arrival["iataCode"]) or EXCEPTIONS.get(country.upper())
    if zone is None:
        zone = "Europe/" + ZONES[country]
    start = datetime.fromisoformat(outbound["departureDate"]).replace(tzinfo=ZoneInfo("Europe/Vilnius"))
    end = datetime.fromisoformat(outbound["arrivalDate"]).replace(tzinfo=ZoneInfo(zone))
    minutes = int((end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds() // 60)
    if not 0 < minutes < MAX_DIRECT_FLIGHT_MINUTES:
        raise ValueError("Invalid direct flight duration.")
    return minutes


def fetch_ryanair_direct_offers(_unused, airport, destination, day, end=None):
    last = end or day
    args = {"departureAirportIataCode": airport, "arrivalAirportIataCode": destination,
            "outboundDepartureDateFrom": day,
            "outboundDepartureDateTo": str(date.fromisoformat(last) + timedelta(days=1)),
            "currency": "EUR", "market": "en-gb"}
    offers = []
    failures = []
    for arrival in METROS.get(destination, destination).split(","):
        if arrival == airport:
            continue
        args["arrivalAirportIataCode"] = arrival
        url = "https://services-api.ryanair.com/farfnd/v4/oneWayFares?" + urlencode(args)
        try:
            if arrival in CALENDAR_COUNTRIES:
                fares = list(iter_ryanair_daily_fares(airport, arrival, day, last))
            else:
                fares = fetch_json_response(url)["fares"]
        except (OSError, ValueError, KeyError) as error:
            detail = f"HTTP {error.code}" if isinstance(error, HTTPError) else type(error).__name__
            if isinstance(error, HTTPError) and error.code == 404 and arrival in CALENDAR_COUNTRIES:
                try:
                    fares = fetch_json_response(url)["fares"]
                except (OSError, ValueError, KeyError):
                    failures.append(f"{arrival}: {detail}")
                    continue
            else:
                failures.append(f"{arrival}: {detail}")
                continue
        for fare in fares:
            outbound = fare["outbound"]
            departure_day = outbound["departureDate"][:10]
            if not day <= departure_day <= last:
                continue
            try:
                minutes = calculate_ryanair_flight_duration_minutes(outbound)
            except (KeyError, ValueError, ZoneInfoNotFoundError):
                continue
            offers.append({"total_currency": outbound["price"]["currencyCode"],
                           "departure_day": departure_day,
                           "departure_at": outbound["departureDate"],
                           "arrival_at": outbound["arrivalDate"],
                           "total_amount": str(outbound["price"]["value"]),
                           "owner": {"name": "Ryanair"},
                           "slices": [{"duration": f"PT{minutes}M",
                                       "segments": [{"destination": {"iata_code": arrival}}]}]})
    return {"live_mode": True, "offers": offers, "warnings": failures}


def fetch_nearest_ryanair_offers(token, airport, destination, day, alternate_airports=False, exact_only=False):
    wanted = date.fromisoformat(day)
    start = wanted if exact_only else max(date.today(), wanted - timedelta(days=FLEXIBLE_DATE_DAYS))
    end = wanted if exact_only else wanted + timedelta(days=FLEXIBLE_DATE_DAYS)
    targets = NEARBY.get(destination, "").split(",") if alternate_airports else [destination]
    combined = {"live_mode": True, "offers": [], "warnings": []}
    for target in filter(None, targets):
        data = fetch_ryanair_direct_offers(token, airport, target, start.isoformat(), end.isoformat())
        combined["offers"].extend(data["offers"])
        combined["warnings"].extend(data["warnings"])
    def departure_date_distance_days(offer):
        return abs((date.fromisoformat(offer["departure_day"]) - wanted).days)
    if combined["offers"]:
        nearest = min(map(departure_date_distance_days, combined["offers"]))
        combined["offers"] = [offer for offer in combined["offers"] if departure_date_distance_days(offer) == nearest]
    return combined
