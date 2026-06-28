from __future__ import annotations

from tkinter import ttk

PALETTE = {
    "app_bg": "#09090b",
    "surface_bg": "#111111",
    "sidebar_bg": "#0a0a0a",
    "muted_fg": "#737373",
    "body_fg": "#a3a3a3",
    "title_fg": "#f5f5f5",
    "sidebar_fg": "#a3a3a3",
    "sidebar_title_fg": "#737373",
    "nav_hover": "#171717",
    "accent": "#3D2BFF",
    "pill_idle": "#171717",
    "pill_active": "#3D2BFF",
    "log_bg": "#09090b",
    "danger": "#ef4444",
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
