# StreamML — Design System: "Neon Midnight Ops"

> **Source:** Stitch Project — *Live Operations Command Center*
> **Project ID:** `7044849643172022974`
> **Design System Asset:** `assets/84c19325864342318c724c53ebf0c8ad`
> **Creative North Star:** _"The Kinetic Observer"_
> **Last Synced:** 2026-03-29

---

## 1. Overview & Creative Direction

The **Kinetic Observer** is the creative foundation for this design system. It represents a shift from passive data visualization to an active, high-velocity engine room. This system embraces a **Cyber-Ops** aesthetic — combining the raw authority of a command-line interface with sophisticated layering of high-end editorial design.

**Key Principles:**
- **Intentional Asymmetry** — Break the traditional rigid grid. Anchor major data streams with expansive typography; nest secondary controls within layered surfaces.
- **Digital Cockpit** — This isn't a flat website; it is a cockpit for real-time ML operations.
- **Density over White Space** — Professionals prefer information-dense interfaces. Use tight spacing (Spacing Scale `2` and `3`) for data grids.

---

## 2. Color Palette

### 2.1 Theme Configuration

| Property | Value |
|---|---|
| **Color Mode** | `DARK` |
| **Color Variant** | `VIBRANT` |
| **Corner Roundness** | `ROUND_FOUR` (0.25rem default) |
| **Spacing Scale** | `1` |

### 2.2 Override / Brand Colors

| Role | Hex | Preview |
|---|---|---|
| **Primary Override** | `#3B82F6` | 🔵 Vivid Blue |
| **Secondary Override** | `#10B981` | 🟢 Emerald Green |
| **Tertiary Override** | `#F43F5E` | 🔴 Rose Red |
| **Neutral Override** | `#0B0E14` | ⚫ Midnight |

### 2.3 Full Named Color Tokens

#### Primary Scale

| Token | Hex | Usage |
|---|---|---|
| `primary` | `#85ADFF` | Primary actions, links, active states |
| `primary-container` | `#6E9FFF` | Primary container backgrounds |
| `primary-dim` | `#699CFF` | Dimmed primary for subtle accents |
| `primary-fixed` | `#6E9FFF` | Fixed primary (non-adaptive) |
| `primary-fixed-dim` | `#5391FF` | Dimmed fixed primary |
| `on-primary` | `#002C66` | Text/icons on primary surfaces |
| `on-primary-container` | `#002150` | Text/icons on primary containers |
| `on-primary-fixed` | `#000000` | Text on fixed primary |
| `on-primary-fixed-variant` | `#002A62` | Text on fixed primary variant |
| `inverse-primary` | `#005BC4` | Primary color for inverse surfaces |

#### Secondary Scale

| Token | Hex | Usage |
|---|---|---|
| `secondary` | `#69F6B8` | Success states, positive metrics |
| `secondary-container` | `#006C49` | Secondary container backgrounds |
| `secondary-dim` | `#58E7AB` | Dimmed secondary |
| `secondary-fixed` | `#69F6B8` | Fixed secondary |
| `secondary-fixed-dim` | `#58E7AB` | Dimmed fixed secondary |
| `on-secondary` | `#005A3C` | Text/icons on secondary surfaces |
| `on-secondary-container` | `#E1FFEC` | Text on secondary containers |
| `on-secondary-fixed` | `#00452D` | Text on fixed secondary |
| `on-secondary-fixed-variant` | `#006544` | Text on fixed secondary variant |

#### Tertiary Scale

| Token | Hex | Usage |
|---|---|---|
| `tertiary` | `#FF6F7E` | Alerts, warnings, drift indicators |
| `tertiary-container` | `#FC4563` | Tertiary container backgrounds |
| `tertiary-dim` | `#FF6F7E` | Dimmed tertiary |
| `tertiary-fixed` | `#FF9099` | Fixed tertiary |
| `tertiary-fixed-dim` | `#FF7986` | Dimmed fixed tertiary |
| `on-tertiary` | `#490010` | Text/icons on tertiary surfaces |
| `on-tertiary-container` | `#100001` | Text on tertiary containers |
| `on-tertiary-fixed` | `#39000B` | Text on fixed tertiary |
| `on-tertiary-fixed-variant` | `#780021` | Text on fixed tertiary variant |

#### Surface Scale

| Token | Hex | Usage |
|---|---|---|
| `surface` | `#0B0E14` | **Base layer** — App background |
| `surface-dim` | `#0B0E14` | Dimmed surface |
| `surface-bright` | `#282C36` | **Floating modals/popovers** |
| `surface-container-lowest` | `#000000` | Terminal views only |
| `surface-container-low` | `#10131A` | **Primary sectioning** |
| `surface-container` | `#161A21` | **Interactive cards** |
| `surface-container-high` | `#1C2028` | Elevated cards |
| `surface-container-highest` | `#22262F` | Input tracks, top-layer cards |
| `surface-variant` | `#22262F` | Variant surface |
| `surface-tint` | `#85ADFF` | Surface tint overlay |

#### Foreground / Content

| Token | Hex | Usage |
|---|---|---|
| `on-background` | `#ECEDF6` | Text on background |
| `on-surface` | `#ECEDF6` | Primary text on surfaces |
| `on-surface-variant` | `#A9ABB3` | Secondary/muted text |
| `inverse-on-surface` | `#52555C` | Text on inverse surfaces |
| `inverse-surface` | `#F9F9FF` | Inverse (light) surface |

#### Outline

| Token | Hex | Usage |
|---|---|---|
| `outline` | `#73757D` | Standard outlines |
| `outline-variant` | `#45484F` | Ghost borders (use at 20% opacity) |

#### Error Scale

| Token | Hex | Usage |
|---|---|---|
| `error` | `#FF716C` | Error states |
| `error-container` | `#9F0519` | Error container backgrounds |
| `error-dim` | `#D7383B` | Dimmed error |
| `on-error` | `#490006` | Text on error surfaces |
| `on-error-container` | `#FFA8A3` | Text on error containers |

### 2.4 Surface Philosophy

#### The "No-Line" Rule
> **Standard borders are prohibited.** Boundaries must be defined through **Background Color Shifts** using the `surface-container` scale.

#### Surface Hierarchy (Tonal Layering)

```
┌─────────────────────────────────────────────────┐
│  surface-bright     (#282C36) — Floating/Modals │
│  ┌─────────────────────────────────────────────┐ │
│  │  surface-container-highest (#22262F) — Top  │ │
│  │  ┌─────────────────────────────────────────┐│ │
│  │  │  surface-container (#161A21) — Cards    ││ │
│  │  │  ┌─────────────────────────────────────┐││ │
│  │  │  │  surface-container-low (#10131A)    ││││
│  │  │  │  ┌─────────────────────────────────┐│││ │
│  │  │  │  │  surface (#0B0E14) — Base Layer ││││ │
│  │  │  │  └─────────────────────────────────┘│││ │
│  │  │  └─────────────────────────────────────┘││ │
│  │  └─────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

#### Glass & Gradient Rules
- **Glassmorphism:** Semi-transparent `surface-container-highest` + `backdrop-blur: 12px` for floating overlays
- **Signature Glows:** Primary CTAs use `primary` (`#85ADFF`) at 20% opacity as outer glow

---

## 3. Typography

### 3.1 Font Stack

| Role | Font Family | Usage |
|---|---|---|
| **Display & Headlines** | `Space Grotesk` | Hero metrics, page titles, critical status numbers |
| **UI & Navigation** | `Inter` | Body text, navigation, labels, buttons |
| **Data & Monospace** | `JetBrains Mono` | Model parameters, logs, code snippets, terminal output |

### 3.2 Google Fonts Import

```css
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');
```

### 3.3 Type Scale

| Token | Size | Font | Usage |
|---|---|---|---|
| `display-lg` | `3.5rem` (56px) | Space Grotesk | Critical status numbers (e.g., Live Accuracy %) |
| `display-md` | `2.5rem` (40px) | Space Grotesk | Major section headers |
| `display-sm` | `2rem` (32px) | Space Grotesk | Sub-section headers |
| `headline-lg` | `1.75rem` (28px) | Space Grotesk | Card titles |
| `headline-md` | `1.5rem` (24px) | Space Grotesk | Panel headers |
| `headline-sm` | `1.25rem` (20px) | Space Grotesk | Widget titles |
| `title-lg` | `1.125rem` (18px) | Inter | Navigation items |
| `title-md` | `1rem` (16px) | Inter | Button text, main labels |
| `title-sm` | `0.875rem` (14px) | Inter | Secondary labels |
| `body-lg` | `1rem` (16px) | Inter | Primary body text |
| `body-md` | `0.875rem` (14px) | Inter | Standard body text |
| `body-sm` | `0.75rem` (12px) | Inter | Captions, footnotes |
| `label-lg` | `0.875rem` (14px) | Inter | Button labels |
| `label-md` | `0.75rem` (12px) | Inter | Technical metadata, chip text |
| `label-sm` | `0.6875rem` (11px) | Inter | Micro labels |
| `mono-lg` | `0.875rem` (14px) | JetBrains Mono | Code blocks |
| `mono-md` | `0.75rem` (12px) | JetBrains Mono | Log output, parameters |
| `mono-sm` | `0.6875rem` (11px) | JetBrains Mono | Inline code |

---

## 4. Elevation & Depth

### 4.1 Tonal Layering (Primary Method)

Elevation is conveyed through **Tonal Layering**, not traditional box shadows.

| Level | Surface Token | Hex | Context |
|---|---|---|---|
| 0 | `surface` | `#0B0E14` | Page background |
| 1 | `surface-container-low` | `#10131A` | Section backgrounds |
| 2 | `surface-container` | `#161A21` | Card backgrounds |
| 3 | `surface-container-high` | `#1C2028` | Elevated cards |
| 4 | `surface-container-highest` | `#22262F` | Inputs, top-layer |
| 5 | `surface-bright` | `#282C36` | Modals, popovers |

### 4.2 Ambient Shadows (Floating Elements Only)

Use only for critical floating elements (e.g., alert modals):

```css
/* Ambient Shadow — Tinted, not black */
box-shadow: 0 0 40px rgba(236, 237, 246, 0.08);
```

- **Blur:** 40px
- **Opacity:** 8%
- **Color:** Tinted `on-surface` (`#ECEDF6`), never pure black

### 4.3 Ghost Border (Accessibility Fallback)

When a border is required for accessibility:

```css
border: 1px solid rgba(69, 72, 79, 0.2); /* outline-variant at 20% */
```

> **Constraint:** Never use 100% opaque, high-contrast borders for layout containers.

---

## 5. Component Specifications

### 5.1 Buttons

#### Primary Button
```css
.btn-primary {
  background-color: #85ADFF;           /* primary */
  color: #002C66;                       /* on-primary */
  font-family: 'Inter', sans-serif;
  font-size: 0.875rem;                  /* label-lg */
  font-weight: 500;
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 0.25rem;              /* ROUND_FOUR */
  box-shadow: 0 0 4px rgba(133, 173, 255, 0.2); /* Signature glow */
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-primary:hover {
  box-shadow: 0 0 8px rgba(133, 173, 255, 0.35);
}
```

#### Secondary Button (Ghost)
```css
.btn-secondary {
  background-color: transparent;
  color: #85ADFF;                       /* primary */
  font-family: 'Inter', sans-serif;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0.625rem 1.25rem;
  border: 1px solid rgba(69, 72, 79, 0.2); /* Ghost border */
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-secondary:hover {
  border-color: rgba(133, 173, 255, 0.4);
}
```

#### Tertiary Button
```css
.btn-tertiary {
  background-color: transparent;
  color: #A9ABB3;                       /* on-surface-variant */
  font-family: 'Inter', sans-serif;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-tertiary:hover {
  background-color: #282C36;            /* surface-bright */
}
```

### 5.2 Cards & Data Modules

```css
.card {
  background-color: #161A21;            /* surface-container */
  border-radius: 0.25rem;
  padding: 1.5rem;
  /* NO border. NO divider lines inside. */
  /* Use vertical whitespace to separate internal sections. */
}
.card-header-meta {
  font-family: 'Inter', sans-serif;
  font-size: 0.75rem;                   /* label-md */
  color: #A9ABB3;                       /* on-surface-variant */
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.card-value {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2rem;                      /* display-sm */
  font-weight: 700;
  color: #ECEDF6;                       /* on-surface */
}
```

### 5.3 Inputs & Terminal Fields

```css
.input-field {
  background-color: #22262F;            /* surface-container-highest */
  color: #ECEDF6;                       /* on-surface */
  font-family: 'Inter', sans-serif;
  font-size: 0.875rem;
  padding: 0.625rem 0.875rem;
  border: none;
  border-bottom: 1px solid transparent;
  border-radius: 0.25rem;
  transition: all 0.2s ease;
}
.input-field:focus {
  outline: none;
  border-bottom-color: #85ADFF;         /* primary */
  box-shadow: 0 2px 8px rgba(105, 156, 255, 0.15); /* primary-dim glow */
}

.terminal-field {
  background-color: #000000;            /* surface-container-lowest */
  color: #69F6B8;                       /* secondary (green terminal text) */
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  padding: 1rem;
  border-radius: 0.25rem;
}
```

### 5.4 Chips / Status Indicators

#### Success / Stable
```css
.chip-success {
  background-color: #006C49;            /* secondary-container */
  color: #69F6B8;                       /* secondary */
  font-family: 'Inter', sans-serif;
  font-size: 0.6875rem;                 /* label-sm */
  font-weight: 600;
  padding: 0.25rem 0.625rem;
  border-radius: 1rem;
  border: none;
}
```

#### Alert / Drift
```css
.chip-alert {
  background-color: #FC4563;            /* tertiary-container */
  color: #490010;                       /* on-tertiary */
  font-family: 'Inter', sans-serif;
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.25rem 0.625rem;
  border-radius: 1rem;
  border: none;
}
```

#### Error
```css
.chip-error {
  background-color: #9F0519;            /* error-container */
  color: #FFA8A3;                       /* on-error-container */
  font-family: 'Inter', sans-serif;
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.25rem 0.625rem;
  border-radius: 1rem;
  border: none;
}
```

### 5.5 Glassmorphism Overlay

```css
.glass-overlay {
  background: rgba(34, 38, 47, 0.7);   /* surface-container-highest at 70% */
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(69, 72, 79, 0.2);
  border-radius: 0.5rem;
}
```

---

## 6. Screens Inventory

| Screen | ID | Dimensions | Type |
|---|---|---|---|
| **Live Operations Command Center** | `fe9232c1af384e6b87195932b387782e` | 2560 × 2240 | Desktop |
| **Model Registry & Control** | `eee744a948b94f8f9a906c5326e2d318` | 2560 × 2048 | Desktop |
| **StreamML Operations Center** | `811f2e56943140ec99cb357293021951` | 1280 × 1024 | Desktop |
| **Drift & Pipeline Observability** | `0bb807df1f184ba7aaef6ba717330b6d` | 2560 × 2806 | Desktop |
| **Feature Intelligence Hub** | `c53a46de4a7f4a75a8d2cfe219c21b6e` | 2560 × 2178 | Desktop |
| **README.md** | `2037492003854883160` | — | Document |
| **image.png** | `13531989311971649695` | 1887 × 1017 | Reference |

---

## 7. CSS Custom Properties Reference

Copy this block into your root stylesheet to use the design tokens as CSS variables:

```css
:root {
  /* ── Primary ── */
  --color-primary: #85ADFF;
  --color-primary-container: #6E9FFF;
  --color-primary-dim: #699CFF;
  --color-primary-fixed: #6E9FFF;
  --color-primary-fixed-dim: #5391FF;
  --color-on-primary: #002C66;
  --color-on-primary-container: #002150;
  --color-inverse-primary: #005BC4;

  /* ── Secondary ── */
  --color-secondary: #69F6B8;
  --color-secondary-container: #006C49;
  --color-secondary-dim: #58E7AB;
  --color-on-secondary: #005A3C;
  --color-on-secondary-container: #E1FFEC;

  /* ── Tertiary ── */
  --color-tertiary: #FF6F7E;
  --color-tertiary-container: #FC4563;
  --color-tertiary-dim: #FF6F7E;
  --color-on-tertiary: #490010;
  --color-on-tertiary-container: #100001;

  /* ── Error ── */
  --color-error: #FF716C;
  --color-error-container: #9F0519;
  --color-error-dim: #D7383B;
  --color-on-error: #490006;
  --color-on-error-container: #FFA8A3;

  /* ── Surface ── */
  --color-surface: #0B0E14;
  --color-surface-dim: #0B0E14;
  --color-surface-bright: #282C36;
  --color-surface-container-lowest: #000000;
  --color-surface-container-low: #10131A;
  --color-surface-container: #161A21;
  --color-surface-container-high: #1C2028;
  --color-surface-container-highest: #22262F;
  --color-surface-variant: #22262F;
  --color-surface-tint: #85ADFF;

  /* ── Background & Foreground ── */
  --color-background: #0B0E14;
  --color-on-background: #ECEDF6;
  --color-on-surface: #ECEDF6;
  --color-on-surface-variant: #A9ABB3;
  --color-inverse-surface: #F9F9FF;
  --color-inverse-on-surface: #52555C;

  /* ── Outline ── */
  --color-outline: #73757D;
  --color-outline-variant: #45484F;

  /* ── Typography ── */
  --font-display: 'Space Grotesk', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* ── Border Radius ── */
  --radius-sm: 0.125rem;  /* 2px */
  --radius-default: 0.25rem;  /* 4px — ROUND_FOUR */
  --radius-md: 0.375rem;  /* 6px */
  --radius-lg: 0.5rem;    /* 8px */
  --radius-full: 9999px;  /* Pill shape for chips */

  /* ── Shadows ── */
  --shadow-ambient: 0 0 40px rgba(236, 237, 246, 0.08);
  --shadow-glow-primary: 0 0 4px rgba(133, 173, 255, 0.2);
  --shadow-glow-primary-hover: 0 0 8px rgba(133, 173, 255, 0.35);

  /* ── Ghost Border ── */
  --border-ghost: 1px solid rgba(69, 72, 79, 0.2);
}
```

---

## 8. Do's and Don'ts

### ✅ Do

| Rule | Detail |
|---|---|
| **Use Intentional Asymmetry** | Align high-level metrics left, granular controls right — create a visual "flow" of data |
| **Embrace Density** | Use Spacing Scale `2` and `3` for tight data grids |
| **Integrate the Bolt** | The StreamML bolt logo is a functional element — use as Home/Refresh trigger in top-left nav |
| **Use Tonal Layering** | Convey depth through `surface-container` tiers, not box shadows |
| **Apply Signature Glows** | All primary CTAs should glow with `primary` at 20% opacity |

### ❌ Don't

| Rule | Detail |
|---|---|
| **No Pure Black** | Never use `#000000` for backgrounds (except `surface-container-lowest` in terminal views). Use Midnight `#0B0E14`. |
| **No Rounded Corners for Everything** | Keep most technical containers at `DEFAULT` (0.25rem). Reserve `lg` (0.5rem) for special elements. |
| **No Default Shadows** | If it doesn't look like it's glowing or naturally layered, it doesn't belong. |
| **No 1px Gray Borders** | Use background color shifts instead. If a11y requires a border, use Ghost Border at 20% opacity. |
| **No Divider Lines in Cards** | Use vertical whitespace (Spacing Scale `8` or `10`) to separate internal card sections. |
