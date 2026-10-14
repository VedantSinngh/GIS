# Bugatti Demo

A premium static demo showcasing the Bugatti brand design system – pure black canvas, high‑contrast white typography, transparent pill‑shaped primary CTA, and full‑bleed photography.

## Project structure
```
bugatti-demo/
├─ index.html      # main page
├─ style.css       # design‑system CSS (tokens, components)
├─ script.js       # minimal interactivity (menu toggle)
└─ README.md       # this file
```

## Running the demo
1. Open `index.html` directly in a browser **or** serve the folder with any static server (e.g., `python -m http.server 8000`).
2. The hero image is generated from a placeholder and lives in the Gemini artifact directory; the HTML points to it via an absolute path, so it works out‑of‑the‑box.

## Customising
- Replace the placeholder hero image (`hero_placeholder_*.png`) with a real Bugatti photo – keep the same aspect ratio.
- Swap the font families in `:root` if you obtain the official Bugatti web‑fonts.
- Extend the component grid with more model cards – just copy the `<article class="model-card">…</article>` block.

## Design highlights
- **Colors**: pure black canvas (`#000000`), white primary (`#ffffff`), ice‑blue link (`#c3d9f3`).
- **Typography**: three‑family split – `Saira Condensed` (Display), `Cormorant Garamond` (Text), `JetBrains Mono` (Monospace). All weights 400, emphasis via size & tracking.
- **Buttons**: transparent pill with 1 px white outline, `height:44px`, `border‑radius:9999px`.
- **Spacing**: generous 120 px section rhythm, base 4 px unit.
- **No shadows / gradients** – depth comes from photography.

Enjoy the demo and feel free to expand it!
