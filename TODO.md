# To do

- **Restore the rest of "Selected work" and the "Also" section on the homepage** — removed from `index.html` pending revised content for each case study. "Selected work" is back with Delicut only; add the others back once their new copy is ready to publish.
- **Fill in the Delicut case study** (`work/delicut.html`) — rebuilt on the "Option D2" layout. Still to do:
  - Real assets for every `.ph` placeholder (each has a `data-asset` id), including the Dubai skyline strip (needs a licensed photo + credit), the six dish photos and four closing photos (confirm permission from delicut.ae), one tall V2 landing screenshot for the pinned browser frame plus one tall mobile screenshot for its Mobile view, and the original/V2 pair for the compare (full-length or cropped to the top sections; same width so they line up).
  - Bracketed copy: `[ITERATION NAME]` in the subscription-flow strip, `[SCREEN NAME]` for the three v0.5 app screens, `[WHAT THE PROTOTYPE TESTED OR SET UP]` for v0.5, `[CREDIT / LICENCE]`, `[CONFIRM PERMISSION]`, `[PHOTO FROM CLIENT, IF ANY]`.
  - Check the pinned-browser notes and the "section order" figure against the real V2 screenshot (currently based on the live delicut.ae page order).
  - Confirm the customer figure: delicut.ae shows both "Trusted by 15,000+ customers" (hero) and "125K+ happy customers" (footer); the case study uses 125K+.
  - Decide what happens to the older anonymised `work/meal-subscription.html`.
- **Re-link Resume in the footer** — removed from `index.html`, `about.html`, `404.html`, and all `work/*.html` pages pending an updated resume. Re-add the link (points to `assets/Shoghi-Bagul-Resume.pdf`) once the new PDF is in place.
- **Re-run `python3 tools/generate-text.py` after copy changes** — the text versions (`*.md`) and `llms.txt` are generated from the pages. When a case study returns to the homepage, add it to `INDEXED_WORK` in that script so `llms.txt` lists it too.
