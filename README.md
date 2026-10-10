# Shoghi Bagul — Portfolio

Personal portfolio site: [shoghibagul.com](https://shoghibagul.com)

A static site — no framework, no build step. Plain HTML, CSS, and a small
amount of vanilla JS.

## Structure

```
index.html            Homepage — hero, practice, selected work (3 featured + more work), experience, writing
about.html             About page — bio, experience timeline, writing
404.html                Custom not-found page
work/                   One case-study page per selected project
css/styles.css          All styling (design tokens live in :root)
js/site.js              Footer clock, copyright year, scroll reveals
assets/                 Resume PDF, favicon, Open Graph share images
tools/                  One-off scripts (see below)
assets-src/             Full-size image originals, git-ignored (see Images)
*.md, work/*.md         Markdown versions of each page, for AI tools (generated)
read/                   Reader pages: the same text as a calm article (generated)
css/reader.css          Styles for the Reader pages
llms.txt                Index of the Markdown versions for AI tools (generated)
sitemap.xml, robots.txt SEO
vercel.json             cleanUrls: true — extension-less routes (/about, /work/connectx)
```

## Running locally

```bash
npx serve@14 .
```

(Also configured as the `portfolio` launch target in `.claude/launch.json`.)

## Editing a case study

Each page in `work/` is self-contained: hero facts, a `.cover--<slug>` art
treatment defined in `css/styles.css`, then three prose sections.
`work/delicut.html` is the exception: a nine-chapter long-form case study
with scroll-driven figures (pinned sections, a section indicator, reveal
animations). Its styles are the "Long-form case study" block in
`css/styles.css` and its behaviour is `js/delicut.js`. Visuals are labelled
placeholders (`.ph`, each with a stable `data-asset` id): put an `<img>` in a
`.ph-frame` and add `.has-img` to the figure to swap in the real asset. Adding a
new one means:

1. Copy an existing `work/*.html` as a template.
2. Add a matching `.cover--<slug>` rule in `css/styles.css`.
3. Add the project to `tools/generate-og.py` (`COVERS` + `CARDS`) and run it
   to generate its share-card image.
4. Link it from `index.html` (a featured card or a "More work" row), give
   it its place in the Previous/Next chain (homepage order) and its number
   in the kicker and share card, and add it to `sitemap.xml` and
   `INDEXED_WORK` in `tools/generate-text.py`.

### Client naming

Not every client can be named publicly, so the site is deliberately mixed.
Check this list before writing or renaming a case study — the split is a
decision, not an oversight:

| Named on the site | Anonymised (descriptive title + slug) |
| --- | --- |
| ConnectX | Curam Care → `caregiver-marketplace` |
| Delicut → `delicut` | PubAdmin → `rights-management` |
| Eden AI | Quixera → `sports-ecosystem` |
| Novus Insights | |

Delicut was previously anonymised as `meal-subscription`. That page still
exists (unlinked from the homepage) alongside the named, long-form
`work/delicut.html`.

The anonymised three keep the client name out of the slug, `<title>`, `<h1>`,
every meta tag, the OG card filename, and body copy. Note that the résumé
names all of them — that is intentional: the résumé is sent to a known
recipient, the site is public.

## Images

Originals never go in the repo. Drop them, full size, into
`assets-src/<project>/` (git-ignored), named the way the page will use them,
then run:

```bash
python3 tools/optimize-images.py delicut
```

Each original becomes two WebP files in `assets/work/<project>/`
(`<name>-<width>.webp`), and the script prints an `<img>` tag with `srcset`,
`width` and `height` to paste into the page; set `sizes` to how wide the image
shows. Keep `loading="lazy"` on everything below the first screen. The name's
prefix picks the widths:

| Prefix | For | Widths | Capture at |
| --- | --- | --- | --- |
| `full-` | Full-page screenshots: the pinned browser frame (`V1_FULL_PAGE`, `V1_MOBILE_FULL_PAGE`), the compare (`OLD_FULL_PAGE`, `V1_FULL_PAGE_COMPARE`) and the versions in the evolution viewer | 1200 / 2400 | Desktop 1440px wide; mobile at the phone's width at 3x. The compare pair at the same width. |
| `app-` | Phone screens (`APP_*`) | 400 / 800 | The phone's native resolution |
| anything else | Photos and crops: landing and subscription iterations, flows, checkout steps, concepts, `LANDING_MENU_SECTION` | 640 / 1280 | At least 1280px wide |

PNG or JPG originals both work. Re-running skips anything already converted.
It needs macOS (`sips`) and downloads `sharp-cli` through `npx` on first use.

## Text versions for AI tools (`llms.txt`)

Every page has two text versions, both generated from the page:

- **Markdown, for AI tools** (`index.md`, `about.md`, `work/<slug>.md`),
  linked from the page's `<head>` and indexed by `llms.txt`.
- **A Reader page, for people** (`read/index.html`, `read/about.html`,
  `read/work/<slug>.html`, served at `/read`, `/read/about`, …): a single
  light column styled by `css/reader.css`, with "← Back to the full …" links.
  The footer's "Read as text" link points here.

Case studies and the about page also carry a JSON-LD description.

All of this is generated from the HTML, so it can't drift — but it does need
re-running after any copy change:

```bash
python3 tools/generate-text.py
```

The script is safe to re-run. It leaves out navigation, buttons, decorative
elements and image placeholders. `llms.txt` lists only what the homepage
features (see `INDEXED_WORK` in the script); never add the anonymised
`meal-subscription` page there. `vercel.json` serves the `.md` files as
UTF-8 text with `X-Robots-Tag: noindex`; Reader pages are also `noindex`
with a canonical link to their full page, so search engines keep the full
pages as the canonical versions.

Placeholder labels on the Delicut page live in `data-ph` attributes and are
drawn by CSS, so they're visible to people but not part of the page text. Add
`data-text-skip` to anything that only makes sense visually (for example
"drag to compare") to keep it out of the text version.

## Regenerating Open Graph images

```bash
python3 tools/generate-og.py
```

Renders every card in `assets/og/` as SVG and rasterises it (macOS only —
uses `qlmanage` and `sips`). Needs network on first run to fetch and cache
the webfonts. Re-run after changing any cover art or card copy.

## Deployment

Hosted on Vercel (Hobby plan), deploying automatically from this repo's
`main` branch. Custom domain (`shoghibagul.com`, purchased via Namecheap)
is configured in the Vercel project's Domains settings.
