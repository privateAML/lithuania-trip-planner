"""Launch the flight planner desktop application."""
import tkinter as tk

from flight_planner.ui.app import PlannerApp


def launch_desktop_application():
    window = tk.Tk()
    application = PlannerApp(window)
    application.show_sign_in_or_registration()
    window.mainloop()


if __name__ == "__main__":
    launch_desktop_application()
