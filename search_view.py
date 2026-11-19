"""Search form and flight results window."""
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

from date_picker import open_departure_date_picker
from planner import AIRPORTS, BALANCED_SCORE_MAX, MINUTES_PER_HOUR, format_currency_amount
from search_tasks import start_flight_search_in_background
from trip_form import ORIGINS, DESTINATIONS, build_validated_trip_request, find_city_prefix_matches, normalize_city_name

DEFAULT_PREFLIGHT_MINUTES = 120
FIRST_PLACE = 1
SORT_COLUMNS = {"Balanced": "overall_rank", "Cheapest first": "cost_rank", "Fastest first": "time_rank"}

def format_ranked_flight_row(row, rank_column):
    labels = []
    if row["cost_rank"] == FIRST_PLACE:
        labels.append("Cheapest")
    if row["time_rank"] == FIRST_PLACE:
        labels.append("Fastest")
    hours, minutes = divmod(row["total_min"], MINUTES_PER_HOUR)
    currency = row["currency"]
    departure = format_local_departure(row["departure_at"], date_format="%Y-%m-%d %H:%M")
    if departure == "unavailable":
        departure = f"{row['departure_day']} · time unavailable"
    return (row[rank_column], departure, row["airport"], row["arrival"],
            row["airline"], format_currency_amount(row["fare_cents"], currency), row["stops"],
            f"{hours}h {minutes:02d}m", format_currency_amount(row["total_cents"], currency),
            " / ".join(labels))


def format_local_departure(departure_at, date_format="%d %b, %H:%M"):
    if departure_at:
        try:
            return datetime.fromisoformat(departure_at).strftime(date_format)
        except ValueError:
            pass
    return "unavailable"


def format_flight_cost_and_time_breakdown(row):
    currency = row["currency"]
    return (
        f"Departure (local): {format_local_departure(row['departure_at'])} from {row['airport']}\n"
        f"{row['airport']} → {row['arrival']} | "
        f"Flight: {format_currency_amount(row['fare_cents'], currency)}, {row['flight_min']} min. "
        f"Ground: {format_currency_amount(row['ground_cents'], currency)}, {row['ground_min']} min. "
        f"Airport buffer: {row['buffer_min']} min. "
        f"Arrival: {format_currency_amount(row['transfer_cents'], currency)}, {row['transfer_min']} min. "
        f"Balanced score: {row['penalty']:.1f}/{BALANCED_SCORE_MAX} (lower is better)."
    )

def format_search_summary(results, trip, sort_order):
    if not results:
        return "No priced flights found. Try another date or destination."
    request = trip.request
    best = min(results, key=lambda offer: offer[SORT_COLUMNS[sort_order]])
    airport = AIRPORTS[best["airport"]]
    heading = {"Balanced": "Best value found", "Cheapest first": "Cheapest found",
               "Fastest first": "Fastest found"}[sort_order]
    messages = []
    if not any(offer["departure_day"] == request.departure_day for offer in results):
        messages.append("No offers found on the selected date.")
    elif any(normalize_city_name(city) == normalize_city_name(trip.starting_city)
             for city in AIRPORTS.values()) and not any(
                 normalize_city_name(AIRPORTS[offer["airport"]]) == normalize_city_name(trip.starting_city)
                 for offer in results):
        messages.append(f"No offer found from {trip.starting_city} on the selected date.")
    travel_date = date.fromisoformat(best["departure_day"]).strftime("%d %b").lstrip("0")
    price = format_currency_amount(best["total_cents"], best["currency"])
    messages.append(f"{heading}: {airport} ({best['airport']}), {travel_date}, {price}.")
    return " ".join(messages)

def open_flight_search_view(root, add_to_cart=None, traveler=None, initial_trip=None):
    root.title(f"Find a flight for {traveler}" if traveler else "Lithuania Flight Planner")
    root.geometry("1140x790")
    root.minsize(900, 690)
    frame = ttk.Frame(root, padding=(24, 18))
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)
    header = ttk.Frame(frame, padding=(22, 15), style="Masthead.TFrame")
    header.grid(row=0, columnspan=3, sticky="ew", pady=(0, 12))
    ttk.Label(header, text="Departures from Lithuania", style="Masthead.TLabel").pack(anchor="w")
    ttk.Label(header, text="Compare one-way fares from Vilnius, Kaunas and Palanga", style="MastheadSub.TLabel").pack(anchor="w")

    def create_search_input_field(row, label, default="", choices=()):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
        entry = ttk.Combobox(frame, values=choices) if choices else ttk.Entry(frame)
        if choices:
            entry.bind("<KeyRelease>", lambda event: entry.configure(values=find_city_prefix_matches(entry.get(), choices)))
        entry.insert(0, default)
        entry.grid(row=row, column=1, sticky="ew", padx=8)
        return entry

    origin = create_search_input_field(1, "Starting city", choices=ORIGINS)
    destination = create_search_input_field(2, "Destination city or airport code", choices=tuple(DESTINATIONS))
    day = create_search_input_field(3, "Departure date (YYYY-MM-DD)")
    if initial_trip:
        for field_widget, value in zip((origin, destination, day), initial_trip):
            field_widget.insert(0, value)
    ttk.Button(frame, text="Choose date", command=lambda: open_departure_date_picker(root, day)).grid(row=3, column=2, sticky="w", padx=4)
    for entry in (origin, destination):
        hint = ttk.Label(frame, foreground="#24645b")
        hint.grid(row=1 if entry is origin else 2, column=2, sticky="w", padx=4)
        def update_city_suggestions(event, box=entry, label=hint):
            choices = ORIGINS if box is origin else tuple(DESTINATIONS)
            matches = find_city_prefix_matches(box.get(), choices)
            label.configure(text=" / ".join(matches[:3]) if box.get().strip() else "")
            if event.keysym == "Right" and matches and box.get().strip():
                box.set(matches[0])
                label.configure(text="")
        entry.bind("<KeyRelease>", update_city_suggestions, add="+")
    ttk.Label(frame, text="Type a city. Use the dropdown or Right Arrow to accept a suggestion.").grid(row=4, columnspan=3, sticky="w")
    currency = create_search_input_field(5, "Offer and transfer currency", "EUR")
    ttk.Label(frame, text="Google Flights · Ryanair fallback").grid(row=5, column=2, sticky="w", padx=4)
    ground = {code: create_search_input_field(i, f"From your city to {name} ({code}): minutes, cost")
              for i, (code, name) in enumerate(AIRPORTS.items(), start=6)}
    transfer = create_search_input_field(9, "Arrival transfer (optional): minutes, cost")
    buffer = create_search_input_field(10, "Preflight buffer (minutes)", str(DEFAULT_PREFLIGHT_MINUTES))
    ttk.Label(frame, text="Use 45, 12.50 for 45 minutes and 12.50 in the selected currency. Leave all ground fields blank to compare flights only.").grid(row=11, columnspan=3, sticky="w")
    ttk.Label(frame, text="Arrival estimate applies to every displayed arrival airport. Use a specific airport code if transfer costs differ.").grid(row=12, columnspan=3, sticky="w")
    advanced_widgets = [widget for widget in frame.grid_slaves()
                        if 5 <= int(widget.grid_info()["row"]) <= 12]
    advanced_visible = tk.BooleanVar(value=False)

    def toggle_ground_travel_fields():
        for widget in advanced_widgets:
            if advanced_visible.get():
                widget.grid()
            else:
                widget.grid_remove()

    ttk.Checkbutton(frame, text="Ground travel options", variable=advanced_visible,
                    command=toggle_ground_travel_fields).grid(row=4, column=2, sticky="w", padx=4)
    toggle_ground_travel_fields()
    status = tk.StringVar(value="Choose your cities and travel date to compare flights.")
    ttk.Label(frame, textvariable=status, wraplength=900).grid(row=14, columnspan=3, sticky="w", pady=5)
    columns = ("Rank", "Departure (local)", "From", "To", "Airline", "Flight fare", "Stops", "Trip time", "Trip cost", "Result")
    table = ttk.Treeview(frame, columns=columns, show="headings", height=10, selectmode="browse")
    for name, width in zip(columns, (48, 180, 55, 55, 120, 95, 55, 95, 95, 140)):
        table.heading(name, text=name)
        table.column(name, width=width)
    table.grid(row=15, columnspan=2, sticky="nsew")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
    scroll.grid(row=15, column=2, sticky="nsw")
    table.configure(yscrollcommand=scroll.set)
    table.tag_configure("alternate", background="#eaf4f1")
    frame.rowconfigure(15, weight=1)
    ttk.Label(frame, text="Balanced rank weights price and time equally relative to this search. Optional baggage and booking fees are excluded.").grid(row=16, columnspan=3, sticky="w")
    sort_order = ttk.Combobox(frame, values=("Balanced", "Cheapest first", "Fastest first"), state="readonly", width=20)
    sort_order.set("Balanced")
    sort_order.grid(row=13, column=1, sticky="w")
    detail = tk.StringVar(value="Select a result for the cost and time breakdown.")
    ttk.Label(frame, textvariable=detail, wraplength=1020).grid(row=17, columnspan=3, sticky="w", pady=6)
    displayed = {}
    current_rows = []

    def render_ranked_flight_table():
        table.delete(*table.get_children())
        displayed.clear()
        detail.set("Select a result for the cost and time breakdown.")
        rank_column = SORT_COLUMNS[sort_order.get()]
        for position, offer in enumerate(sorted(current_rows, key=lambda row: row[rank_column])):
            item = table.insert("", "end", values=format_ranked_flight_row(offer, rank_column),
                                tags=("alternate",) if position % 2 else ())
            displayed[item] = offer

    def show_selected_flight_breakdown(_event):
        selected = table.selection()
        if selected and selected[0] in displayed:
            detail.set(format_flight_cost_and_time_breakdown(displayed[selected[0]]))

    table.bind("<<TreeviewSelect>>", show_selected_flight_breakdown)
    def update_result_order(_event):
        render_ranked_flight_table()
        if current_rows and active_trip is not None:
            status.set(format_search_summary(current_rows, active_trip, sort_order.get()))

    sort_order.bind("<<ComboboxSelected>>", update_result_order)

    def submit_flight_search():
        nonlocal active_trip
        try:
            trip = build_validated_trip_request(
                origin.get(), destination.get(), day.get(), currency.get(),
                {airport: entry.get() for airport, entry in ground.items()},
                buffer.get(), transfer.get(),
            )
        except (ValueError, ArithmeticError) as error:
            messagebox.showerror("Check your input", str(error))
            return
        current_rows.clear()
        active_trip = trip
        render_ranked_flight_table()
        button.configure(state="disabled")
        airports = ", ".join(trip.request.ground_by_airport)
        status.set(f"Searching from {trip.starting_city} via {airports}…")
        search_context[:] = [trip.starting_city, trip.destination_label]
        start_flight_search_in_background(root, trip.request, display_completed_search_results)

    def display_completed_search_results(results, notes, _request):
        current_rows.extend(results)
        render_ranked_flight_table()
        if not results and any("search failed" in note or "Source notes:" in note for note in notes):
            status.set("No priced flights found. Some sources did not return usable offers.")
        else:
            status.set(format_search_summary(results, active_trip, sort_order.get()))
        button.configure(state="normal")

    button = ttk.Button(frame, text="Search and compare", command=submit_flight_search, style="Search.TButton")
    search_context = []
    active_trip = None
    if add_to_cart:
        def save_selected_flight_to_cart():
            selected = table.selection()
            if not selected or selected[0] not in displayed:
                messagebox.showinfo("Select a flight", "Choose a flight in the results first.", parent=root)
                return
            add_to_cart(*search_context, displayed[selected[0]])
            root.destroy()

        actions = ttk.Frame(frame)
        actions.grid(row=13, column=1, sticky="ew", padx=(8, 0))
        sort_order.grid_configure(in_=actions, row=0, column=0, sticky="w")
        ttk.Button(actions, text="Save flight", command=save_selected_flight_to_cart,
                   style="Search.TButton").grid(row=0, column=1, padx=12)
        table.bind("<Double-1>", lambda event: save_selected_flight_to_cart() if table.identify_row(event.y) else None)
    button.grid(row=13, column=0, sticky="w", pady=8)

