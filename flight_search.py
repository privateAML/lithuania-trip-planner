"""Search providers in priority order before moving to other dates."""
from functools import partial

from google_flights import fetch_google_flight_offers
from planner import fetch_and_rank_flight_offers
from ryanair import FLEXIBLE_DATE_DAYS, NEARBY, fetch_nearest_ryanair_offers, fetch_ryanair_direct_offers


def fetch_offers_for_requested_date(currency, airport, destination, day):
    try:
        offers = fetch_google_flight_offers(airport, destination, day, currency)
        if offers:
            return {"live_mode": True, "offers": offers, "source": "Google Flights"}
        note = "Google Flights returned no priced offers."
    except (OSError, ValueError, KeyError, TypeError) as error:
        note = str(error) if type(error) is ValueError else "Google Flights response unavailable."
    response = fetch_ryanair_direct_offers(currency, airport, destination, day)
    response["warnings"].append(note)
    response["source"] = "Ryanair direct fallback"
    return response


def find_ranked_flights_with_fallbacks(request):
    steps = [(fetch_offers_for_requested_date, "")]
    can_use_alternate_airports = request.flight_only and request.destination in NEARBY
    if can_use_alternate_airports:
        steps.append((
            partial(fetch_nearest_ryanair_offers, alternate_airports=True, exact_only=True),
            "Checked nearby arrival airports on the requested date. Onward travel is separate.",
        ))
    steps.append((
        fetch_nearest_ryanair_offers,
        f"No exact-date offers. Checked dates within {FLEXIBLE_DATE_DAYS} days.",
    ))
    if can_use_alternate_airports:
        steps.append((
            partial(fetch_nearest_ryanair_offers, alternate_airports=True),
            "Checked nearby arrival airports. Onward travel is separate.",
        ))

    notes = []
    for fetch, explanation in steps:
        if explanation:
            notes.append(explanation)
        results, source_notes = fetch_and_rank_flight_offers(request, fetch)
        notes.extend(source_notes)
        if results:
            return results, notes
    return [], notes
