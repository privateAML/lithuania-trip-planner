"""Read search results using the unofficial fli adapter."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


REQUEST_TIMEOUT_SECONDS = 40


def fetch_google_flight_offers(airport, destination, day, currency):
    executable = Path(sys.executable).parent / "Scripts" / "fli.exe"
    command = str(executable) if executable.is_file() else shutil.which("fli")
    if not command:
        raise ValueError("Google Flights adapter is missing. Run setup.bat.")
    environment = os.environ.copy()
    environment["FLI_SOCS_COOKIE"] = ""
    environment["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            [command, "flights", airport, destination, day,
             "--currency", currency, "--format", "json"],
            capture_output=True, encoding="utf-8", env=environment, timeout=REQUEST_TIMEOUT_SECONDS,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError("Google Flights timed out.") from error
    if result.returncode:
        raise ValueError("Google Flights request failed.")
    data = json.loads(result.stdout)
    if data.get("success") is not True:
        raise ValueError("Google Flights did not return a successful response.")
    offers = []
    for flight in data["flights"]:
        legs = flight.get("legs") or []
        if not legs or flight.get("price") is None or flight.get("currency") != currency:
            continue
        if legs[0]["departure_time"][:10] != day or legs[0]["departure_airport"]["code"] != airport:
            continue
        airline = " / ".join(dict.fromkeys(leg["airline"]["name"] for leg in legs))
        if flight.get("self_transfer"):
            airline += " (self-transfer)"
        offers.append({
            "total_currency": flight["currency"], "total_amount": str(flight["price"]),
            "owner": {"name": airline}, "departure_day": day,
            "departure_at": legs[0]["departure_time"],
            "arrival_at": legs[-1]["arrival_time"],
            "slices": [{"duration": f'PT{flight["duration"]}M',
                        "segments": [{"destination": {"iata_code": leg["arrival_airport"]["code"]}}
                                     for leg in legs]}],
        })
    return offers
