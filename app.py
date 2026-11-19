"""Screen navigation and local sign-in."""
import sqlite3
import tkinter as tk
from functools import partial
from tkinter import ttk

from accounts import MIN_PASSWORD_LENGTH, register_or_verify_local_account
from group_view import GroupView
from search_view import open_flight_search_view
from theme import apply_desktop_theme

ACCOUNT_WINDOW_SIZE = "500x410"
GROUP_WINDOW_SIZE = "1120x640"


class PlannerApp:
    def __init__(self, root):
        self.root = root
        root.title("Lithuania Flight Planner")
        apply_desktop_theme(root)

    def destroy_current_screen_widgets(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_account_screen_panel(self):
        self.destroy_current_screen_widgets()
        self.root.minsize(0, 0)
        self.root.geometry(ACCOUNT_WINDOW_SIZE)
        panel = ttk.Frame(self.root, padding=28)
        panel.pack(fill="both", expand=True)
        return panel

    def show_sign_in_or_registration(self, register=False):
        panel = self.create_account_screen_panel()
        title = "Create an account" if register else "Sign in"
        ttk.Label(panel, text=title, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 16))
        ttk.Label(panel, text="Username").pack(anchor="w")
        username = ttk.Entry(panel)
        username.pack(fill="x", pady=(0, 10))
        ttk.Label(panel, text=f"Password (at least {MIN_PASSWORD_LENGTH} characters)" if register else "Password").pack(anchor="w")
        password = ttk.Entry(panel, show="*")
        password.pack(fill="x", pady=(0, 12))
        status = tk.StringVar(master=panel)
        submit = partial(self.submit_account_credentials, username, password, register, status)
        ttk.Button(panel, text=title, command=submit, style="Search.TButton").pack(fill="x", pady=4)
        ttk.Button(panel, text="Back to sign in" if register else "Create an account",
                   command=partial(self.show_sign_in_or_registration, not register)).pack(fill="x", pady=4)
        ttk.Label(panel, textvariable=status, wraplength=420).pack(anchor="w", pady=8)
        password.bind("<Return>", submit)
        username.focus_set()

    def submit_account_credentials(self, username, password, register, status, _event=None):
        try:
            account = register_or_verify_local_account(username.get(), password.get(), register)
        except ValueError as error:
            status.set(str(error))
        except (OSError, sqlite3.Error):
            status.set("Could not open the local account database.")
        else:
            self.show_trip_type_selection(account)

    def show_trip_type_selection(self, username):
        panel = self.create_account_screen_panel()
        ttk.Label(panel, text=f"Welcome, {username}", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(panel, text="Who is traveling?").pack(anchor="w", pady=(8, 20))
        ttk.Button(panel, text="Solo", command=self.show_solo_search, style="Search.TButton").pack(fill="x", pady=4)
        ttk.Button(panel, text="Group", command=partial(self.show_group_itinerary, username)).pack(fill="x", pady=4)
        ttk.Button(panel, text="Sign out", command=self.show_sign_in_or_registration).pack(anchor="w")

    def show_solo_search(self):
        self.destroy_current_screen_widgets()
        open_flight_search_view(self.root)

    def show_group_itinerary(self, username):
        self.destroy_current_screen_widgets()
        self.root.geometry(GROUP_WINDOW_SIZE)
        GroupView(self.root, on_back=partial(self.show_trip_type_selection, username))
