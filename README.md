# Lithuania Flight Planner

A Windows desktop app for comparing one-way flights from Vilnius (VNO), Kaunas (KUN) and Palanga (PLQ) to European destinations. Search for one traveler or build a group itinerary with separate routes, arrival times and fares for each person.

## Example search: Lithuania to London

Ryanair's fare calendar returned four direct offers for **12 December 2026** in a snapshot taken on **19 November 2026**. These are airfare-only observations from one source.

| Decision | Flight | Fare | Duration |
|---|---|---:|---:|
| Lowest fare | Kaunas → Luton | €21.99 | 2 h 50 min |
| Shortest flight | Palanga → Stansted | €26.99 | 2 h 25 min |

In this search, paying **€5 more** saved **25 minutes in the air**. The flights also land at different airports, so ground travel can change the preferred route.

![Bar chart of the four observed London airfares](docs/media/london-fares.png)

![Bar chart of the four observed London flight durations](docs/media/london-durations.png)

[View the data behind the charts](docs/media/london-snapshot.json). Prices and availability change.

## How it works

1. **Collect offers.** Python requests live results through the unofficial Google Flights adapter [fli](https://github.com/punitarani/fli). The Ryanair fare calendar provides a direct-flight fallback.
2. **Compare routes.** Python normalizes fares and durations. [SQL](flight_planner/storage/ranking.sql) ranks the offers in an in-memory SQLite database by cost, duration or a balanced score that weights both equally. The search tries the selected date across departure airports before checking nearby dates.
3. **Plan a group.** Choose a route and date for each traveler, save the selected flight and review the table of local arrival times and fares. You can replace individual flights and see the group total by currency.

Optional ground travel estimates can be entered manually. The charts contain flight time and airfare only. Baggage, booking fees and onward travel are outside those figures.

## Setup and launch

### macOS

1. Install [Python 3.11 for macOS](https://www.python.org/downloads/macos/) with Tkinter. Run `python3.11 -m tkinter` to check that a test window opens, then close it.
2. In Terminal, open the project folder and run:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flight_planner
```

For later launches, use the last command again.

### Windows

1. Install Python 3.11 with Tkinter.
2. Double-click `setup.bat` once to install the dependencies.
3. Double-click `launch.pyw`, or run `python -m flight_planner` from the project folder.

Create a local account and choose **Solo** or **Group**. Local accounts are stored in SQLite with salted password hashes. Search results are held in memory and the cart lasts for the current Group session.

## Project structure

| Path | Responsibility |
| --- | --- |
| `flight_planner/ui/` | Tkinter screens, calendar, input validation and background search callbacks |
| `flight_planner/core/` | Search order, offer normalization and ranking |
| `flight_planner/providers/` | Google Flights and Ryanair adapters |
| `flight_planner/storage/` | Local accounts in SQLite and the flight ranking SQL query |
| `docs/media/` | Charts and the fare snapshot used above |
