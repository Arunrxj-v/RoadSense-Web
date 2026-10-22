---
name: Civic Cartography
colors:
  surface: '#faf9f5'
  surface-dim: '#dbdad6'
  surface-bright: '#faf9f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f4f0'
  surface-container: '#efeeea'
  surface-container-high: '#e9e8e4'
  surface-container-highest: '#e3e2df'
  on-surface: '#1b1c1a'
  on-surface-variant: '#44474b'
  inverse-surface: '#30312e'
  inverse-on-surface: '#f2f1ed'
  outline: '#75777c'
  outline-variant: '#c5c6cc'
  surface-tint: '#575f6c'
  primary: '#09111b'
  on-primary: '#ffffff'
  primary-container: '#1e2631'
  on-primary-container: '#858d9b'
  inverse-primary: '#bfc7d6'
  secondary: '#545f6e'
  on-secondary: '#ffffff'
  secondary-container: '#d8e3f5'
  on-secondary-container: '#5a6574'
  tertiary: '#270500'
  on-tertiary: '#ffffff'
  tertiary-container: '#4b1100'
  on-tertiary-container: '#eb6232'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe3f2'
  primary-fixed-dim: '#bfc7d6'
  on-primary-fixed: '#141c27'
  on-primary-fixed-variant: '#3f4753'
  secondary-fixed: '#d8e3f5'
  secondary-fixed-dim: '#bcc7d9'
  on-secondary-fixed: '#111c29'
  on-secondary-fixed-variant: '#3d4856'
  tertiary-fixed: '#ffdbd0'
  tertiary-fixed-dim: '#ffb59d'
  on-tertiary-fixed: '#390b00'
  on-tertiary-fixed-variant: '#842500'
  background: '#faf9f5'
  on-background: '#1b1c1a'
  surface-variant: '#e3e2df'
typography:
  headline-xl:
    fontFamily: Public Sans
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
  headline-xl-mobile:
    fontFamily: Public Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-lg:
    fontFamily: Public Sans
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 34px
  headline-lg-mobile:
    fontFamily: Public Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  headline-sm:
    fontFamily: Public Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Public Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Public Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Public Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-tablet: 1.5rem
  gutter-desktop: 2rem
  margin: 1rem
  margin-tablet: 1.5rem
  margin-desktop: 2.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system establishes a civic-grade, public utility standard tailored for municipal road condition reporting, transit safety analysis, and roadway navigation. Its design philosophy centers on municipal reliability, cartographic discipline, and uncompromised utilitarian clarity. 

The aesthetic draws from Swiss public signage and contemporary European topographic publications. It completely eliminates speculative UI trends: no frosted glass, no neon gradients, no decorative micro-animations, and no simulated depth effects. The layout provides absolute confidence through precision borders, generous typographic hierarchy, and structural legibility in high-glare daytime environments.

The interface presents users with an unshakeable sense of institutional accountability, calm competence, and immediate legibility. Content is structured to make civic hazards and navigational statuses unmistakable at glance speeds.

## Colors

The palette operates on strict functional segregation. 

- **Neutral Canvas (`#F4F3EF` / `#FFFFFF`):** The primary canvas is Warm Stone (`#F4F3EF`), with active map overlays and sheet cards rendered in Crisp White (`#FFFFFF`). This establishes an organic, non-fatiguing baseline reminiscent of high-finish architectural stock rather than bleached digital white.
- **Primary Ink (`#1E2631`):** Deep Slate serves as the primary structural tone for all authoritative typography, active structural dividers, and dominant state icons.
- **Secondary Slate (`#5B6675`):** Reserved for technical metadata, coordinates, street class labels, and inactive border treatments.
- **Civic Alert Vermilion (`#E05A2B`):** A concentrated warm amber-vermilion reserved solely for live hazard indicators, pothole flags, critical road status changes, and dynamic telemetry points. It is strictly banned from decorative use, branding flourishes, or secondary button states.

Structural boundary lines leverage an explicit neutral border tint (`#E2DFD7`), guaranteeing accessible contrast while keeping vector maps readable underneath floating panels.

## Typography

Typography prioritizes rapid cartographic scanning and municipal authority. 

- **Public Sans** provides clean grotesque geometry with high vertical metrics and open counters, ensuring street names, incident descriptions, and regulatory notices remain razor-sharp at varying viewing angles and device sizes.
- **JetBrains Mono** is introduced for all telemetry readouts, geographic coordinates, station codes, timestamps, and road degradation measurements. Its monospaced cadence anchors technical data, preventing tabular shifts during live streaming updates.

All headline levels maintain tight tracking (-0.015em) to enforce structural density, while label tokens incorporate positive tracking (+0.04em) to maintain legibility when converted to all-caps for administrative badging.

## Layout & Spacing

The layout is built around a full-canvas cartographic viewport accompanied by disciplined floating or anchored panels. It uses a strict 8px structural grid.

- **Desktop & Workstation (1024px+):** The cartographic view occupies 100% of the canvas. Floating administrative sidebars, incident telemetry decks, and inspection queues occupy fixed columns (380px or 440px wide) inset by desktop margins (`space-xl`), allowing map data to breathe behind structured control surfaces.
- **Tablet (768px - 1023px):** Sidebars transition to anchored split-screens or collapsable side-trays with standard 24px margins.
- **Mobile (<768px):** The cartographic layer remains uninterrupted with an anchored bottom sheet system. Margins collapse to 16px. Touch targets enforce a minimum clearance of 48px, while content groupings within sheets rely on compact internal spacing tokens (`space-sm` and `space-md`) to maximize vertical data density without visual crowding.

## Elevation & Depth

Depth is established strictly through planar separation, tonal contrast, and low-contrast boundary rules. Diffuse, multi-layered shadows are prohibited.

- **Ground Level (Map Canvas):** Level 0. Base vector maps and satellite imagery.
- **Sheet Level (Floating Panels, Menus, Cards):** Level 1. Crisp White (`#FFFFFF`) surfaces framed by a crisp 1px solid stroke (`#E2DFD7`). A singular, hyper-subtle architectural resting shadow is permitted exclusively to separate white cards from light base maps: `0 1px 3px 0 rgba(30, 38, 49, 0.08)`.
- **Overlay Level (Modals, Priority Alerts, Dialogs):** Level 2. Solid `#FFFFFF` background with a direct 1px stroke of Deep Slate (`#1E2631`) and an offset edge line: `0 4px 12px 0 rgba(30, 38, 49, 0.12)`.

No backdrop filters or translucent blur planes are permitted under any condition; map features must either be cleanly occluded or fully visible.

## Shapes

The design system employs subtle corner softening (0.25rem / 4px base radius) to evoke calibrated drafting templates and technical instruments rather than consumer toy software.

- Input fields, data cells, modal dialogues, and control containers use the default 4px radius.
- System buttons and interactive tabs use 4px radius to ensure strict alignment with parent grid borders.
- Map markers and live pulse beacons are the only elements that bypass the angular standard, utilizing pure 50% circular geometry to preserve universal geographic symbology.

## Components

### Buttons
- **Primary Action:** Solid Deep Slate (`#1E2631`) fill, Crisp White label in `Public Sans` Medium, 4px border radius. No drop shadow. Hover state brightens tone to `#2C3746`. Active state compresses slightly.
- **Secondary / Utility Action:** Crisp White (`#FFFFFF`) fill, 1px solid `#E2DFD7` border, `#1E2631` text. On hover, background shifts to Warm Stone (`#F4F3EF`).
- **Hazard Action (Resolve / Flag Incident):** Crisp White fill with a 1px solid Vermilion (`#E05A2B`) border and text color. Hover triggers an opaque 8% tint of vermilion over the surface.

### Inputs & Search Bars
- Rectangular 40px height fields. Clean white background with a 1px border of `#CFCCC4`.
- Placeholder text in Secondary Slate (`#5B6675`).
- Active focus removes default OS halos and applies an uncompromising 1px `#1E2631` perimeter stroke.
- Geographic search boxes incorporate leading monospaced coordinates or highway icons.

### Cards & Map Info Panels
- White background with `#E2DFD7` edge borders.
- Internal headers split data between primary naming (`headline-sm`) and telemetry coordinates (`label-md` in monospaced font).
- Dividers within cards are hairline 1px solid strokes with zero vertical feathering.

### Pothole Markers & Status Chips
- **Map Pothole Node:** A solid 10px circular node in Vermilion (`#E05A2B`) with a 2px outer ring of `#FFFFFF`. Critical live alerts feature a non-blurred outward concentric hairline ring.
- **Status Chips:** High-density, 20px height capsules. Neutral status chips use `#F4F3EF` background with `#1E2631` monospaced text. Pothole / Hazard status chips use an ultra-light tint background (`#FDF1EC`), 1px solid border (`#E05A2B`), and vermilion lettering.

### Checkboxes & Segmented Controls
- Checkboxes use 4px squares with 1px slate borders. Selected state fills with `#1E2631` displaying a precise white check glyph.
- Segmented layer controls (e.g., Road Surface, Traffic Density, Pothole Frequency) sit inside a shallow `#F4F3EF` frame, with active segments elevated via white fill and fine border containment.