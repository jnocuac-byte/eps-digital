---
name: EPS Digital
description: Colombian EPS healthcare platform with AI-powered medical appointment booking
colors:
  primary: "#2B3E59"
  primary-deep: "#1e2d40"
  primary-light: "#3a527a"
  background: "#ffffff"
  foreground: "#1a1a1a"
  card: "#ffffff"
  card-foreground: "#1a1a1a"
  secondary: "#f0f1f5"
  secondary-foreground: "#1a1a1a"
  muted: "#ececf0"
  muted-foreground: "#717182"
  accent: "#e9ebef"
  accent-foreground: "#1a1a1a"
  destructive: "#d4183d"
  destructive-foreground: "#ffffff"
  border: "rgba(0, 0, 0, 0.1)"
  input-background: "#f3f3f5"
  ring: "#b3b3b3"
  chart-1: "#c26b5a"
  chart-2: "#5a9e93"
  chart-3: "#3d6480"
  chart-4: "#d4b060"
  chart-5: "#c49240"
  page-background: "#F5F5F5"
  success: "#16a34a"
  success-light: "#dcfce7"
  warning: "#d97706"
  warning-light: "#fef3c7"
typography:
  display:
    fontFamily: "Inter, sans-serif"
    fontSize: "clamp(2rem, 4vw, 3rem)"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Inter, sans-serif"
    fontSize: "clamp(1.5rem, 3vw, 2.25rem)"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Inter, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  body:
    fontFamily: "Roboto, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Roboto, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
  small:
    fontFamily: "Roboto, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  sm: "0.375rem"
  md: "0.5rem"
  lg: "0.625rem"
  xl: "1rem"
  full: "9999px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.background}"
    rounded: "{rounded.full}"
    padding: "12px 32px"
  button-primary-hover:
    backgroundColor: "{colors.primary-deep}"
    textColor: "{colors.background}"
    rounded: "{rounded.full}"
    padding: "12px 32px"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    rounded: "{rounded.full}"
    padding: "12px 32px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.card-foreground}"
    rounded: "{rounded.xl}"
    padding: "24px"
  input:
    backgroundColor: "{colors.input-background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  sidebar-nav:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.background}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
---

# Design System: EPS Digital

## Overview

**Creative North Star: "The Calm Clinical Corridor"**

EPS Digital's visual language is a study in restrained confidence. The system speaks with the authority of a trusted healthcare provider — calm, clear, and unwavering — while avoiding the cold sterility that plagues medical software. Every surface earns its place through utility, not decoration. The deep navy (#2B3E59) anchors the entire experience like the sturdy frame of a clinic door: always visible, never ornamental.

The palette is deliberately limited. A single strong primary carries the brand weight across navbars, buttons, and section headers, while a carefully graded neutral scale handles the rest. White backgrounds keep the airiness that patients need when navigating health concerns. Color appears with purpose — green for availability, red for errors, blue-200 for emphasis in hero text — never as filler.

Layout is generous and uncluttered. The 1440px max-width container, 24px padding, and 24px grid gaps create breathing room that respects the user's attention. Cards are the primary content vessel: rounded-xl, softly shadowed, always on white. The system favors full-width CTAs and hero sections that let the brand gradient speak.

**Key Characteristics:**
- Navy-anchored calm: the primary #2B3E59 appears on every key surface, creating instant recognition
- White-dominant backgrounds with soft #F5F5F5 page tint for depth contrast
- Generous whitespace: 24px internal padding, 16–24px gaps, max-width 1440px container
- Rounded-full CTAs as the signature interactive pattern (pill-shaped buttons)
- Inter headings for authority, Roboto body for readability
- Minimal shadow vocabulary: ambient lifts only, never structural blocks
- Healthcare-appropriate restraint: no gradients on text, no glass effects, no decorative flourishes

## Colors

The palette is a single-accent system: one strong navy primary against a clean neutral field. The navy is the brand anchor and appears on every major surface.

### Primary
- **Clinical Navy** (#2B3E59): The brand's signature. Used for navbar, sidebar panels, primary buttons, section headings, icon tints, and the CTA gradient base. This color must appear on every key interactive surface.
- **Navy Deep** (#1e2d40): Hover state for navy elements. Slightly darker for confidence on interaction.
- **Navy Light** (#3a527a): The lighter terminus of the navy gradient. Used in hero backgrounds, CTA banners, and the modal header gradient.

### Neutral
- **Pure White** (#ffffff): Card backgrounds, button fills on navy surfaces, content areas. The dominant canvas color.
- **Page Tint** (#F5F5F5): The subtle warm-gray background behind cards and sections. Provides depth contrast against white cards.
- **Input Canvas** (#f3f3f5): Input field backgrounds. Slightly cooler than page tint for subtle field distinction.
- **Soft Gray** (#ececf0): Muted backgrounds, disabled states, secondary containers.
- **Medium Gray** (#717182): Muted foreground text — captions, secondary labels, descriptions.
- **Near-Black** (#1a1a1a): Primary text, headings, body copy. Maximum contrast on white.

### Semantic
- **Success Green** (#16a34a): Available status indicators, positive confirmations.
- **Success Light** (#dcfce7): Background for success badges and status pills.
- **Destructive Red** (#d4183d): Error states, destructive actions, delete confirmations.
- **Warning Amber** (#d97706): Caution states, degraded service notices.
- **Warning Light** (#fef3c7): Background for warning banners.

### Named Rules
**The Navy Anchor Rule.** The primary navy (#2B3E59) appears on every key interactive surface — navbar, sidebar, primary buttons, section headings. Its omnipresence is the brand signature. Removing it from a major surface requires explicit approval.

**The White Space Doctrine.** Backgrounds are white or page-tint (#F5F5F5). No card, section, or content area uses a saturated or tinted background unless it is a branded gradient banner. The airiness is the point.

## Typography

**Display Font:** Inter (with system sans-serif fallback)
**Body Font:** Roboto (with system sans-serif fallback)

**Character:** The pairing is clinical without being cold. Inter's geometric precision gives headings authority; Roboto's friendly proportions keep body text inviting. Both are workhorses that read clearly at small sizes on mobile — critical for a healthcare audience that spans all age groups.

### Hierarchy
- **Display** (700, clamp(2rem, 4vw, 3rem), 1.2): Hero headlines on landing and dashboard pages. Bold and commanding, never decorative.
- **Headline** (700, clamp(1.5rem, 3vw, 2.25rem), 1.3): Section titles, page headers. The workhorse heading size.
- **Title** (600, 1.25rem, 1.4): Card titles, sidebar section labels, modal headers. Compact authority.
- **Body** (400, 1rem, 1.5): All running text, descriptions, form labels. Standard comfortable reading measure.
- **Label** (500, 0.875rem, 1.5): Form field labels, navigation items, button text. Slightly heavier than body for interactive clarity.
- **Small** (400, 0.75rem, 1.5): Captions, timestamps, secondary metadata, badges.

### Named Rules
**The Heading Weight Rule.** Headings use Inter at 600–700 weight. Body text and labels use Roboto at 400–500. Never mix — Inter at 400 reads weak, Roboto at 700 reads cluttered.

## Layout

The spatial model is a single-column centered container with generous padding. Content never stretches full-width; the 1440px max-width ensures comfortable reading on ultra-wide displays.

- **Container:** max-width 1440px, mx-auto, px-6 (24px horizontal padding)
- **Grid gaps:** 24px (gap-6) for card grids, 16px (gap-4) for tighter groupings
- **Section rhythm:** py-10 to py-12 (40–48px vertical padding) between major sections
- **Content max-width:** Forms and text-heavy sections cap at max-w-3xl (768px) or max-w-2xl (672px) for optimal reading measure
- **Sidebar layouts:** Fixed-width sidebars (w-56 to w-64) with navy backgrounds, flex-1 main content
- **Responsive:** Single-column stacks below lg breakpoint, two-column at lg, three-column at xl for card grids
- **Navbar:** Fixed top, h-16 (64px), full-width navy bar with 1440px inner container
- **Page content offset:** main content uses pt-16 to clear the fixed navbar

## Elevation & Depth

The system uses minimal shadow vocabulary — ambient lifts only, never structural blocks. Depth is communicated through background color contrast (white cards on #F5F5F5 page tint) more than through shadows.

### Shadow Vocabulary
- **Card ambient** (`shadow-sm`): Subtle lift for content cards at rest. White cards on page tint need only the faintest definition.
- **Card hover** (`shadow-md`): Slightly deeper lift on interactive card hover. Signals that the card is clickable.
- **Modal overlay** (`shadow-2xl`): Heavy lift for dialogs, modals, and floating panels. The only place where a prominent shadow appears.
- **Dropdown** (`shadow-xl`): Navigation dropdowns and popover menus. Higher than modals because they float above content layers.
- **Navbar** (`shadow-md`): Fixed navigation bar gets a permanent subtle shadow to separate from page content below.

### Named Rules
**The Flat-By-Default Rule.** Surfaces are flat at rest. Shadows appear only to signal interactivity (hover) or layering (modal, dropdown). No decorative shadows on static content.

## Shapes

The form language is consistently rounded, favoring the pill shape for interactive elements and the rounded-xl for content containers.

- **Card radius:** 1rem (rounded-xl). All content cards, panels, and containers use this radius. It is the dominant shape.
- **Button radius:** 9999px (rounded-full). The signature shape. Primary CTAs, secondary buttons, and tag-style interactive elements are always pills.
- **Input radius:** 0.5rem (rounded-md). Form fields use a tighter radius that feels structural, not decorative.
- **Badge radius:** 0.375rem (rounded-md). Status badges, tags, and small labels use compact rounding.
- **Avatar radius:** 9999px (rounded-full). Profile images, bot avatars, and user icons are always circles.
- **Sidebar radius:** 0.5rem (rounded-md). Navigation items in sidebars use the same radius as inputs for consistency.
- **Border:** 1px solid rgba(0,0,0,0.1) for cards, inputs, and dividers. The border is structural — it defines edges, not decorates them.

## Components

### Buttons
- **Shape:** Rounded-full (pill) for primary/secondary; rounded-md for ghost and icon buttons
- **Primary:** Navy background (#2B3E59), white text, 12px 32px padding. On hover: darken to #1e2d40. On disabled: opacity-50, cursor-not-allowed.
- **Outline:** Transparent background, navy border and text. On hover: navy background, white text. Used for secondary actions and nav items.
- **Ghost:** Transparent background, navy text, no border. On hover: light background tint. Used for inline actions and text links.
- **Icon button:** 36x36 (size-9), rounded-md, transparent background. Used for search, close, and utility actions.

### Cards / Containers
- **Corner Style:** Rounded-xl (1rem)
- **Background:** White (#ffffff) on page-tint (#F5F5F5) background
- **Shadow Strategy:** shadow-sm at rest, shadow-md on hover for interactive cards
- **Border:** 1px solid rgba(0,0,0,0.1)
- **Internal Padding:** 24px (p-6)
- **Signature pattern:** Cards contain a 24px gap between sections, with headings in Inter 600 and body in Roboto 400

### Navigation
- **Top Navbar:** Fixed, h-16, navy (#2B3E59) background, white text. Logo on left (white circle + navy icon + "EPS Digital" in Inter 600). Nav links centered, auth buttons right. Mobile: hamburger menu with slide-down panel on darker navy (#1e2d40).
- **Sidebar Nav:** Fixed-width (w-56 to w-64), navy background, white text. Items are rounded-md with bg-white/20 for active state, hover:bg-white/10 for inactive. Logo at top with "Panel Admin" / "Panel Médico" subtitle.
- **Mobile nav:** Full-width dropdown below navbar, darker navy background, stacked links with border-top separators.

### Inputs / Fields
- **Style:** bg-input-background (#f3f3f5), 1px border, rounded-md, h-9 (36px)
- **Focus:** 2px ring in navy/30 opacity, border shifts to navy. Ring-offset not used.
- **Error:** border-destructive, ring-destructive/20
- **Disabled:** bg-gray-100, text-gray-500, cursor-not-allowed
- **Select dropdown:** Same styling as input, with native browser dropdown

### Chat Interface (EPSIA)
- **Container:** White card, rounded-2xl, border-gray-100, shadow-sm
- **Header:** Navy gradient (135deg, #2B3E59 → #3a527a), rounded-t-2xl, white text
- **User messages:** Navy background, white text, rounded-2xl with rounded-br-sm tail
- **Assistant messages:** Gray-100 background, dark text, rounded-2xl with rounded-bl-sm tail
- **Input:** Full-width, rounded-full, bg-gray-100, navy send button (rounded-full, 40x40)
- **Avatar circles:** 28x28, navy bg for user, blue-100 bg for assistant, icon centered

### Modal / Dialog
- **Overlay:** bg-black/50, fixed inset-0, z-50
- **Content:** White background, rounded-lg (shadcn default), shadow-lg, max-w-lg, centered
- **Header gradient:** Navy gradient (135deg, #2B3E59 → #3a527a) for branded modals
- **Close button:** Top-right, X icon, opacity-70, hover:opacity-100

### Badges / Status Pills
- **Available:** bg-green-100 text-green-700, rounded-full, text-xs, px-3 py-1
- **Unavailable:** bg-red-100 text-red-600, same shape
- **Active status:** bg-green-400/20 text-green-300 on dark backgrounds
- **Default badge:** bg-primary text-primary-foreground, rounded-md

## Do's and Don'ts

### Do:
- **Do** use navy (#2B3E59) as the primary accent on every key interactive surface — navbar, sidebar, primary buttons, section headings.
- **Do** keep backgrounds white or page-tint (#F5F5F5). The airiness is the healthcare brand.
- **Do** use rounded-full (pill) shapes for primary and secondary CTA buttons — it is the signature interaction pattern.
- **Do** pair Inter for headings with Roboto for body. Never mix weights or families across these roles.
- **Do** use 24px internal padding and 24px grid gaps as the standard spacing rhythm.
- **Do** keep shadows minimal — ambient lifts for cards at rest, slightly deeper on hover, prominent only for modals.
- **Do** use the navy gradient (135deg, #2B3E59 → #3a527a) for hero sections, CTA banners, and branded modal headers.

### Don't:
- **Don't** use saturated or tinted backgrounds for content cards. White on #F5F5F5 is the depth strategy.
- **Don't** add gradient text, glass effects, or decorative blur. Emphasis comes from weight and size.
- **Don't** use hard-offset shadows (box-shadow: 4px 4px 0) or block shadows. The system is flat-by-default.
- **Don't** put section numbers (01 / 02 / 03) or eyebrow kickers above headings. The heading carries its own weight.
- **Don't** use rounded-xl on buttons or rounded-full on cards. Shapes have specific roles.
- **Don't** apply color to text labels or secondary copy for decoration. Color on text is functional — status, links, emphasis.
- **Don't** use modals for tasks that don't require interruption or protected focus. Prefer inline expansion or navigation.
