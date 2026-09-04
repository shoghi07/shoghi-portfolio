# Shoghi Bagul — Portfolio

Personal portfolio site: [shoghibagul.com](https://shoghibagul.com)

A static site — no framework, no build step. Plain HTML, CSS, and a small
amount of vanilla JS.

## Structure

```
index.html            Homepage — hero, selected work, "also", writing
about.html             About page — bio, experience timeline, writing
404.html                Custom not-found page
work/                   One case-study page per selected project
css/styles.css          All styling (design tokens live in :root)
js/site.js              Footer clock, copyright year, scroll reveals
assets/                 Resume PDF, favicon, Open Graph share images
tools/                  One-off scripts (see below)
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
treatment defined in `css/styles.css`, then three prose sections. Adding a
new one means:

1. Copy an existing `work/*.html` as a template.
2. Add a matching `.cover--<slug>` rule in `css/styles.css`.
3. Add the project to `tools/generate-og.py` (`COVERS` + `CARDS`) and run it
   to generate its share-card image.
4. Link it from `index.html` (Selected work or Also) and add it to
   `sitemap.xml`.

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
