# Hermes UI — Design tokens

Windows 11–style hierarchy. **One page title per route** (`PageHeader`); chrome shows app name only (`Titlebar`). Subsections use `SectionTitle`.

## Typography

| Role | Class | Size | Weight | Color |
|------|-------|------|--------|-------|
| Chrome (titlebar) | `.ds-chrome-title` | 14px | 600 | `--text-primary` |
| Page title | `.ds-page-title` | 24px | 600 | `--text-primary` |
| Page description | `.ds-page-desc` | 15px | 400 | `--text-secondary` |
| Section title | `.ds-section-title__text` | 16px | 600 | `--text-primary` |
| Card title | `.ds-card-title` | 16px | 600 | `--text-primary` |
| Label | `.ds-label` | 14px | 500 | `--text-secondary` |
| Body | `.text-body` | 15px | 400 | `--text-secondary` |
| Caption | `.ds-caption` / `.text-caption` | 13px | 400 | `--text-tertiary` |
| Stat number | `.ds-stat-value` | 28px | 600 | `--text-primary` |
| Mono value | `.ds-value` | 15px | 500 | `--text-primary` |

## Color

| Token | Use |
|-------|-----|
| `--text-primary` | Headings, primary content |
| `--text-secondary` | Body, labels |
| `--text-tertiary` | Captions, hints |
| `--text-muted` | Disabled, placeholders |
| `--accent` | Links, icons, focus, progress, badges (`#6e7af8` blue-violet) |
| `--state-ready` | Online, success |
| `--state-warn` | Paused, warning |
| `--state-error` | Offline, errors |
| `--surface-0` … `--surface-inset` | Layered backgrounds |

## Layout

| Class | Use |
|-------|------|
| `.ds-page-header` | Top of each page (title + optional action) |
| `.ds-section` | Spacing between form sections |
| `.ds-section-title` | Section heading with optional icon |
| `.ds-stack` | Vertical gap between blocks |
| `.ds-card` + `.ds-card-padded` | Elevated cards |
| `.ds-panel` | Inset form panels |
| `.ds-badge` | Status chips (+ `--accent`, `--success`, etc.) |

## Components

- **PageHeader** — single `h1` per route; no eyebrow/caption by default.
- **SectionTitle** — `h2` inside settings/configure pages.
- **Titlebar** — app name + status pill only (not page title).

## Sidebar

| State | Width | Icon | Label |
|-------|-------|------|-------|
| Expanded | 240px | 20px | 16px (`1rem`) |
| Collapsed | 64px | 24px | hidden (icons only) |

Classes: `.sidebar`, `.sidebar--collapsed`, `.nav-item`, `.nav-item--collapsed`, `.nav-icon`.

Source of truth: `src/index.css` (`:root` variables + `.ds-*` classes).
