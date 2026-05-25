from __future__ import annotations

from tkinter import ttk

PALETTE = {
    "app_bg": "#0B1020",
    "surface_bg": "#111827",
    "sidebar_bg": "#0F172A",
    "muted_fg": "#94A3B8",
    "body_fg": "#E5E7EB",
    "title_fg": "#FFFFFF",
    "sidebar_fg": "#E5E7EB",
    "sidebar_title_fg": "#CBD5E1",
    "nav_hover": "#172033",
    "accent": "#2563EB",
    "pill_idle": "#1F2937",
    "pill_active": "#3B82F6",
    "log_bg": "#0F172A",
    "danger": "#DC2626",
}


def apply_desktop_theme(root) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    root.option_add("*Font", "{Segoe UI} 10")
    root.option_add("*TCombobox*Listbox.font", "{Segoe UI} 10")

    style.configure("App.TFrame", background=PALETTE["app_bg"])
    style.configure("Surface.TFrame", background=PALETTE["surface_bg"])
    style.configure("Card.TFrame", background=PALETTE["surface_bg"])
    style.configure("Sidebar.TFrame", background=PALETTE["sidebar_bg"])
    style.configure("Title.TLabel", background=PALETTE["app_bg"], foreground=PALETTE["title_fg"], font=("Segoe UI", 22, "bold"))
    style.configure("Hero.TLabel", background=PALETTE["app_bg"], foreground=PALETTE["muted_fg"], font=("Segoe UI", 11))
    style.configure("Section.TLabel", background=PALETTE["surface_bg"], foreground=PALETTE["title_fg"], font=("Segoe UI", 12, "bold"))
    style.configure("Body.TLabel", background=PALETTE["surface_bg"], foreground=PALETTE["body_fg"], font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=PALETTE["surface_bg"], foreground=PALETTE["muted_fg"], font=("Segoe UI", 10))
    style.configure("SidebarTitle.TLabel", background=PALETTE["sidebar_bg"], foreground=PALETTE["sidebar_title_fg"], font=("Segoe UI", 10, "bold"))
    style.configure("Sidebar.TButton", background=PALETTE["sidebar_bg"], foreground=PALETTE["sidebar_fg"], relief="flat", padding=(12, 10))
    style.map("Sidebar.TButton", background=[("active", PALETTE["nav_hover"])])
    style.configure("Primary.TButton", padding=(12, 8))
    style.configure("Secondary.TButton", padding=(10, 8))
    style.configure("TEntry", padding=6)
    style.configure("TCheckbutton", background=PALETTE["surface_bg"], foreground=PALETTE["body_fg"])
    style.map("TCheckbutton", background=[("active", PALETTE["surface_bg"])])
