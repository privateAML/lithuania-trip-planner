"""Shared desktop theme."""
from tkinter import ttk

def apply_desktop_theme(root):
    root.configure(background="#e8eff0")
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=("Segoe UI", 10), foreground="#142e37")
    style.configure("TFrame", background="#f2f7f6")
    style.configure("TLabel", background="#f2f7f6")
    style.configure("TEntry", padding=5, fieldbackground="white")
    style.configure("TCombobox", padding=4, fieldbackground="white")
    style.configure("TButton", padding=(10, 6), background="#e0ecea")
    style.configure("Search.TButton", padding=(15, 8), foreground="white", background="#075e59")
    style.map("Search.TButton", background=[("disabled", "#607a97"), ("active", "#064944")])
    style.configure("Treeview", rowheight=29, background="white", fieldbackground="white")
    style.configure("Treeview.Heading", background="#dbeae7", font=("Segoe UI", 10, "bold"), padding=6)
    style.map("Treeview", background=[("selected", "#075e59")], foreground=[("selected", "white")])
    style.configure("Masthead.TFrame", background="#142e37")
    style.configure("Masthead.TLabel", background="#142e37", foreground="#ffffff", font=("Segoe UI", 23, "bold"))
    style.configure("MastheadSub.TLabel", background="#142e37", foreground="#c5dedb")
