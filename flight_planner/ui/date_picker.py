"""Departure calendar widget."""
import tkinter as tk
from calendar import Calendar, month_name
from datetime import date
from tkinter import ttk

def open_departure_date_picker(parent, entry):
    today = date.today()
    try:
        selected = max(today, date.fromisoformat(entry.get().strip()))
    except ValueError:
        selected = today
    year, month = selected.year, selected.month
    popup = tk.Toplevel(parent)
    popup.title("Choose departure date")
    popup.transient(parent)
    popup.resizable(False, False)
    popup.geometry(f"+{entry.winfo_rootx()}+{entry.winfo_rooty() + entry.winfo_height()}")
    panel = ttk.Frame(popup, padding=10)
    panel.pack()

    def set_departure_date_and_close(day):
        entry.delete(0, tk.END)
        entry.insert(0, date(year, month, day).isoformat())
        popup.destroy()

    def change_displayed_month(step):
        nonlocal year, month
        year, offset = divmod(year * 12 + month - 1 + step, 12)
        month = offset + 1
        render_month_grid()

    def render_month_grid():
        for widget in panel.winfo_children():
            widget.destroy()
        previous = "disabled" if (year, month) <= (today.year, today.month) else "normal"
        following = "disabled" if (year, month) == (date.max.year, date.max.month) else "normal"
        ttk.Button(panel, text="‹", width=4, state=previous, command=lambda: change_displayed_month(-1)).grid(row=0, column=0)
        ttk.Label(panel, text=f"{month_name[month]} {year}").grid(row=0, column=1, columnspan=5)
        ttk.Button(panel, text="›", width=4, state=following, command=lambda: change_displayed_month(1)).grid(row=0, column=6)
        for index, label in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            ttk.Label(panel, text=label).grid(row=1, column=index, pady=4)
        for row, week in enumerate(Calendar().monthdayscalendar(year, month), start=2):
            for column, day in enumerate(week):
                if day:
                    state = "disabled" if date(year, month, day) < today else "normal"
                    ttk.Button(panel, text=str(day), width=4, state=state,
                               command=lambda value=day: set_departure_date_and_close(value)).grid(row=row, column=column, padx=2, pady=2)

    render_month_grid()
    popup.bind("<Escape>", lambda event: popup.destroy())
    popup.grab_set()
    popup.focus_set()
