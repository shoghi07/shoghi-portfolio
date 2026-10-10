# To do

- **Homepage follow-ups** — the homepage now runs hero → practice → Selected work (Delicut, ConnectX, Eden AI as featured cards) → More work → Experience → Writing. Still to do:
  - Real cover images for the three featured cards (they show the graphic covers for now).
  - The sports-ecosystem case study is held back while the product is in progress: off the homepage, the Previous/Next chain, `llms.txt` and the sitemap (the page itself still exists). Add it back as "07 · More work" when it can be shown.
  - Retire the older anonymised `work/meal-subscription.html` (no longer linked from anywhere except its own pager).
  - The old "Also" section (business-travel planner and other unlinked items) stays off the homepage.
- **Fill in the Delicut case study** (`work/delicut.html`) — rebuilt on the "Option D2" layout. Still to do:
  - Real assets for the remaining `.ph` placeholders (each has a `data-asset` id): goal and calorie flows, Flexi plan, checkout steps, the subscription strip, app screens, the Pro tier and AI Coach concepts, and the hero composition.
  - Bracketed copy: `[ITERATION NAME]` in the subscription-flow strip, `[SCREEN NAME]` for the three v0.5 app screens, `[WHAT THE PROTOTYPE TESTED OR SET UP]` for v0.5.
  - Landing page images are all in: the evolution strip (Original, Iterations 1, 2, 3, 5, V1, V1.1; each opens full length in a viewer with previous/next and a note), the menu section (original beside V1), the V1 page in the browser frame (desktop + mobile) and the original/V1 compare. The landing page's live version is called V1.1 (the export folder calls it v2). Confirm the viewer notes for each version (`data-full-note` on each `.cs-evo-open`). The original comes from `EXPORTS/Landing page/Old Design/Old-Desktop.png`, where the page is only 293px wide (cut from a 32,768px canvas), so it looks soft when enlarged; a 4x export of just the page frame would sharpen the compare and viewer.
  - Add screenshots through `assets-src/delicut/` + `tools/optimize-images.py` (see README "Images" for names and capture sizes).
  - Photos from Delicut's social media are in `assets/work/delicut/` (six photos in the full-bleed strip after the hero (arrives, the week in the fridge, breakfast, the sauce pour, a smoothie, shared), which replaced the planned Dubai skyline; the boxes in "Adapt"; four customer photos in the closing band), credited "Photos: Delicut". Get an explicit OK from Delicut to use them.
  - Check the pinned-browser notes and the "section order" figure against the real V2 screenshot (currently based on the live delicut.ae page order).
  - Confirm the customer figure: delicut.ae shows both "Trusted by 15,000+ customers" (hero) and "125K+ happy customers" (footer); the case study uses 125K+.
  - Decide what happens to the older anonymised `work/meal-subscription.html`.
- **Re-link Resume in the footer** — removed from `index.html`, `about.html`, `404.html`, and all `work/*.html` pages pending an updated resume. Re-add the link (points to `assets/Shoghi-Bagul-Resume.pdf`) once the new PDF is in place.
- **Re-run `python3 tools/generate-text.py` after copy changes** — the text versions (`*.md`) and `llms.txt` are generated from the pages. When a case study returns to the homepage, add it to `INDEXED_WORK` in that script so `llms.txt` lists it too.
