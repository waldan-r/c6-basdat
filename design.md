# TakTikTuk Design System (v1.1)

## 1. Typography
The typography system uses clean, system-safe fonts to ensure performance and readability across all platforms.
* **Font Family:** 'Segoe UI', Tahoma, sans-serif
* **Headings:**
  * H1 (Hero/Welcome): `text-4xl font-bold` (Tailwind) / 36pt
  * H2 (Page Title): `text-3xl font-extrabold` (Tailwind) / 30pt
  * H3 (Sub-section): `text-2xl font-semibold` / 24pt
  * H4 (Section Title): `text-xl font-bold` or `fw-bold` (Bootstrap) / 20pt
* **Body Text:**
  * Base: `text-gray-700` (#495057) - Primary readability
  * Muted/Secondary: `text-gray-500` / `text-muted` - For less important info
  * Small: `text-sm` / `small` - For form labels or table headers
  * Caption: `text-xs uppercase tracking-wider` - For metadata

## 2. Color Palette
The primary brand color is Blue, supported by a semantic system for status indicators.

### Primary Colors
* **Primary Base:** Blue-600 (`#2563eb`) / Bootstrap Primary (`#0d6efd`)
* **Primary Hover:** Blue-700 (`#1d4ed8`)
* **Primary Subtle:** Blue-50 (`#eff6ff`)

### Neutral/Grayscale Colors
* **Background:** Gray-50 (`#f9fafb`)
* **Card/Surface:** White (`#ffffff`)
* **Border:** Gray-200 (`#e5e7eb`)
* **Text Main:** Gray-800 (`#1f2937`)
* **Text Muted:** Gray-500 (`#6b7280`)

### Semantic / Status Colors
* **Success:** Text Green-700, Bg Green-50 (Used for: Completed, Paid)
* **Warning:** Text Orange-700, Bg Orange-50 (Used for: Pending, Due)
* **Danger:** Text Red-700, Bg Red-50 (Used for: Cancelled, Error)
* **Info:** Text Blue-600, Bg Blue-50 (Used for: Information)

## 3. UI Components

### Cards & Surfaces
* **Auth Card:** `bg-white rounded-xl shadow-lg border border-gray-100 p-8`
* **Dashboard Card:** `bg-white rounded-xl shadow-sm border border-gray-100 p-6`
* **Data Card:** `card border-0 rounded-12px shadow-sm`

### Buttons
* **Primary Button (Auth):** `bg-blue-600 text-white font-bold py-3 rounded-lg hover:bg-blue-700 transform hover:scale-[1.02] transition-all active:scale-95`
* **Pill Button:** `btn-primary rounded-pill px-4 fw-bold`
* **Outline Action:** `btn-outline-secondary border-0` or `btn-outline-danger border-0`

### Form Inputs
* **Label:** `block text-sm font-semibold text-gray-600 mb-1`
* **Input Field:** `w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all`

## 4. Spacing & Layout
Consistency in spacing ensures a rhythmic and balanced UI. We follow an **8px base grid system**.

* **Standard Padding:**
  * Page Container: `px-4 md:px-8 py-6`
  * Section Spacing: `mb-8`
  * Element Spacing (Inside Cards): `p-6`
* **Layout Management:**
  * **Grid:** Use `display: grid` for dashboard layouts (usually `grid-cols-1 md:grid-cols-3` for stats cards).
  * **Flexbox:** Use `display: flex` for navigation bars, button groups, and alignment.
  * **Gap:** Use standard gaps like `gap-4` (1rem) or `gap-6` (1.5rem) between repeating elements.

## 5. UI Feedback Guidelines
Provide visual cues for system actions to improve user experience.

* **Alerts:** Inline notifications for important status changes.
  * *Success Alert:* Green background with icon.
  * *Error Alert:* Red background for failed transactions/validation.
* **Toast Notifications:** Temporary pop-ups for background actions (e.g., "Promo Saved").
  * Position: Top-right on Desktop, Top-center on Mobile.
  * Duration: 3 - 5 seconds.
* **Skeleton Loading:** Used during data fetching.
  * Style: `bg-gray-200 animate-pulse rounded`.
  * Usage: Match the shape of the content being loaded (e.g., circular for avatars, rectangular for text lines).

## 6. Accessibility (a11y)
Designing for everyone ensures better usability and SEO.

* **Forms:**
  * Every input **must** have a linked `<label>`.
  * Use `placeholder` only for examples, not as a replacement for labels.
  * High-contrast focus rings (`focus:ring-2`) for keyboard navigation.
* **Buttons:**
  * Minimum touch target size: 44x44 pixels.
  * Use `aria-label` for icon-only buttons (e.g., a "trash" icon button should have `aria-label="Delete Order"`).
* **Contrast:** Ensure a minimum contrast ratio of 4.5:1 for body text against backgrounds (WCAG AA standard).