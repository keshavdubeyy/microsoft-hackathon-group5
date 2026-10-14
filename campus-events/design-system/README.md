# Design System — "Research lab notebook at noon"

Light, monochrome, editorial. Files:

- `tokens.css` — CSS custom properties (colors, type scale, spacing, radii, shadow)
- `components.css` — base styles + buttons, chips, input, cards, grid, nav, footer
- `index.html` — reference page; open it in a browser

## Rules
**Do**
- `--color-obsidian` is the only filled button color (`.btn--filled`), used sparingly.
- Borders are always `--color-hairline` (rgba(0,0,0,.12)), never gray hex.
- Buttons, tags, inputs: 9999px radius. Cards and images: 6px.
- Body 17px / 1.65 / -0.01em. Weight 500 for nav, labels, subheads; 600 only for 28px heading; 400 body.
- Separate sections with whitespace (32–64px), not rules or colored bands.

**Don't**
- No accent colors, gradients, or brand hues.
- No box-shadows on cards (`--shadow-sm` is for outlined-pill hover only).
- No weights above 600; no body text below 16px.
- No icons inside buttons or text links.
- Ash / Whisper surfaces only for hover and selected states.

Font: `OpenAI Sans` is proprietary; the stack falls back to Inter / system-ui. Add Inter via `<link>` if you want a consistent fallback.
