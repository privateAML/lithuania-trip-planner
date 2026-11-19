"""Group itinerary and editing of saved flights."""
import tkinter as tk
from dataclasses import dataclass
from functools import partial
from tkinter import messagebox, ttk

from flight_planner.core.planner import AIRPORTS, format_currency_amount
from flight_planner.ui.search_view import open_flight_search_view
from flight_planner.ui.trip_form import normalize_city_name

COLUMNS = {
    "Traveler": 115, "Travel to airport": 250, "Destination": 115,
    "Flight": 95, "Departure date": 115, "Arrival (local)": 155, "Flight fare": 95,
}


@dataclass(frozen=True)
class TravelerBooking:
    traveler: str
    city: str
    destination: str
    offer: object

    def saved_trip_search_fields(self):
        return self.city, self.destination, self.offer["departure_day"]


def format_traveler_itinerary_row(booking):
    offer = booking.offer
    airport_city = AIRPORTS[offer["airport"]]
    ground_route = booking.city
    if normalize_city_name(booking.city) != normalize_city_name(airport_city):
        ground_route = f"{booking.city} → {airport_city} (self transfer)"
    arrival = offer["arrival_at"]
    return (
        booking.traveler, ground_route, booking.destination,
        f"{offer['airport']} → {offer['arrival']}", offer["departure_day"],
        arrival[:16].replace("T", " ") if arrival else "Unavailable",
        format_currency_amount(offer["fare_cents"], offer["currency"]),
    )


def format_group_totals_by_currency(bookings):
    totals = {}
    for booking in bookings:
        currency = booking.offer["currency"]
        totals[currency] = totals.get(currency, 0) + booking.offer["fare_cents"]
    amounts = " + ".join(format_currency_amount(cents, currency) for currency, cents in sorted(totals.items()))
    return f"Travelers: {len(bookings)} | Flight total: {amounts or '—'}"


class GroupView(ttk.Frame):
    def __init__(self, root, on_back):
        super().__init__(root, padding=24)
        self.root = root
        self.bookings = {}
        self.summary = tk.StringVar(master=self)
        self.pack(fill="both", expand=True)
        ttk.Label(self, text="Group itinerary", font=("Segoe UI", 23, "bold")).pack(anchor="w")
        ttk.Label(self, text="Find a flight for each traveler, select a row, then click Save flight.").pack(anchor="w", pady=(4, 12))
        self.build_group_actions_toolbar(on_back)
        self.build_traveler_itinerary_table()
        ttk.Label(self, textvariable=self.summary, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(12, 4))
        ttk.Label(self, text="Quoted flight fares only. Prices can change before booking.").pack(anchor="w")
        self.update_group_total_label()

    def build_group_actions_toolbar(self, on_back):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 12))
        ttk.Label(toolbar, text="Traveler name").pack(side="left")
        self.traveler_name = ttk.Entry(toolbar, width=26)
        self.traveler_name.pack(side="left", padx=8)
        ttk.Button(toolbar, text="Find flight", command=self.start_new_traveler_search, style="Search.TButton").pack(side="left")
        self.edit_button = ttk.Button(toolbar, text="Edit flight", command=self.edit_selected_traveler_flight, state="disabled")
        self.edit_button.pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Remove selected", command=self.remove_selected_traveler).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Back to trip type", command=on_back).pack(side="right")

    def build_traveler_itinerary_table(self):
        holder = ttk.Frame(self)
        holder.pack(fill="both", expand=True)
        self.table = ttk.Treeview(holder, columns=list(COLUMNS), show="headings", selectmode="browse", height=10)
        for title, width in COLUMNS.items():
            self.table.heading(title, text=title)
            self.table.column(title, width=width)
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=self.table.yview)
        scrollbar.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<<TreeviewSelect>>", self.update_edit_button_state)
        self.table.bind("<Double-1>", self.edit_double_clicked_traveler)

    def update_group_total_label(self):
        self.summary.set(format_group_totals_by_currency(list(self.bookings.values())))

    def get_selected_traveler_row_id(self):
        return next(iter(self.table.selection()), None)

    def update_edit_button_state(self, _event):
        self.edit_button.configure(state="normal" if self.get_selected_traveler_row_id() else "disabled")

    def edit_double_clicked_traveler(self, event):
        if item := self.table.identify_row(event.y):
            self.table.selection_set(item)
            self.edit_selected_traveler_flight()

    def start_new_traveler_search(self):
        traveler = self.traveler_name.get().strip()
        if not traveler:
            messagebox.showinfo("Traveler name required", "Enter a name or identifier for this traveler.", parent=self.root)
            return
        if any(booking.traveler.casefold() == traveler.casefold() for booking in self.bookings.values()):
            messagebox.showinfo("Traveler already added", "Choose a distinct name or edit the existing flight.", parent=self.root)
            return
        self.open_traveler_flight_search(traveler)

    def open_traveler_flight_search(self, traveler, existing=None):
        popup = tk.Toplevel(self.root)
        popup.transient(self.root)
        popup.grab_set()
        initial_trip = self.bookings[existing].saved_trip_search_fields() if existing else None
        open_flight_search_view(popup, add_to_cart=partial(self.save_traveler_flight_to_cart, traveler, existing),
                     traveler=traveler, initial_trip=initial_trip)

    def save_traveler_flight_to_cart(self, traveler, existing, city, destination, offer):
        booking = TravelerBooking(traveler, city, destination, offer)
        values = format_traveler_itinerary_row(booking)
        if existing:
            self.table.item(existing, values=values)
            item = existing
        else:
            item = self.table.insert("", "end", values=values)
            self.traveler_name.delete(0, tk.END)
        self.bookings[item] = booking
        self.table.selection_set(item)
        self.table.see(item)
        self.update_group_total_label()

    def edit_selected_traveler_flight(self):
        if item := self.get_selected_traveler_row_id():
            self.open_traveler_flight_search(self.bookings[item].traveler, item)

    def remove_selected_traveler(self):
        if item := self.get_selected_traveler_row_id():
            del self.bookings[item]
            self.table.delete(item)
            self.update_group_total_label()
