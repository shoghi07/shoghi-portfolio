#!/usr/bin/env python3
"""Generate the site's text layer for AI tools and readers who prefer text.

For every page this writes:

  * a Markdown version next to the HTML (index.md, about.md, work/<slug>.md),
    for AI tools; /llms.txt indexes them
  * a Reader page under read/ (read/index.html, read/about.html,
    read/work/<slug>.html): the same text as a calm, single-column article
    for people, with a way back to the full page

and keeps three things in each HTML page up to date:

  * a <link rel="alternate" type="text/markdown"> pointing at its Markdown
  * a "Read as text" link in the footer, pointing at its Reader page
  * a JSON-LD block describing the page (case studies and the about page)

The Markdown is generated from the HTML, so it can never drift from the page:
re-run this after any copy change.

    python3 tools/generate-text.py

What the text version leaves out, on purpose: navigation, buttons, decorative
and aria-hidden elements, image placeholders (anything with data-ph or inside
.ph), and durations the page recomputes live (data-dur). Figures marked
role="img" are replaced by their aria-label.
"""

import html
import json
import os
import re
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://shoghibagul.com"
AUTHOR = {"@type": "Person", "name": "Shoghi Bagul", "url": SITE + "/"}

# (html file, public URL path, markdown file). The 404 page gets no text version.
PAGES = [
    ("index.html", "/", "index.md"),
    ("about.html", "/about", "about.md"),
    ("work/delicut.html", "/work/delicut", "work/delicut.md"),
    ("work/sports-ecosystem.html", "/work/sports-ecosystem", "work/sports-ecosystem.md"),
    ("work/connectx.html", "/work/connectx", "work/connectx.md"),
    ("work/rights-management.html", "/work/rights-management", "work/rights-management.md"),
    ("work/novus.html", "/work/novus", "work/novus.md"),
    ("work/eden.html", "/work/eden", "work/eden.md"),
    ("work/caregiver-marketplace.html", "/work/caregiver-marketplace", "work/caregiver-marketplace.md"),
    ("work/meal-subscription.html", "/work/meal-subscription", "work/meal-subscription.md"),
]

# llms.txt lists only what the homepage currently features, so it never
# promotes pages held back for revision (see TODO.md). Add a case study here
# when it returns to the homepage's "Selected work". The older anonymised
# meal-subscription page must stay out: listing it beside the named Delicut
# page would undo the anonymisation.
INDEXED_WORK = {
    "work/delicut.html",
    "work/connectx.html",
    "work/eden.html",
    "work/rights-management.html",
    "work/novus.html",
    "work/caregiver-marketplace.html",
    "work/sports-ecosystem.html",
}

# Clients that can be named (see README "Client naming"), for JSON-LD "about".
NAMED_CLIENTS = {
    "work/delicut.html": {"@type": "Organization", "name": "Delicut", "url": "https://delicut.ae/"},
    "work/connectx.html": {"@type": "Organization", "name": "ConnectX"},
    "work/eden.html": {"@type": "Organization", "name": "Eden AI"},
    "work/novus.html": {"@type": "Organization", "name": "Novus Insights"},
}

SKIP_TAGS = {"script", "style", "svg", "nav", "button", "noscript", "template", "input", "label", "select", "head"}
SKIP_CLASSES = {
    "ph", "ph-frame", "cs-blocks", "cs-ind", "preview", "cover", "cs-bleed", "cs-rail", "cs-rail-head",
    "cs-browser-tabs", "cs-browser-bar", "cs-phone-status", "cs-phone-bar", "years", "axis", "skip",
    "work-cover-mobile", "cs-compare", "cs-compare-labels", "before",
}
BLOCK = {"p", "h1", "h2", "h3", "h4", "li", "dt", "dd", "figcaption", "blockquote", "section", "article",
         "div", "figure", "ol", "ul", "dl", "main", "header", "q"}
VOID = {"br", "img", "hr", "meta", "link", "input", "source", "wbr"}
# elements that act as a label before following text ("**Hero** Plans…")
LABEL_TAGS = {"b", "strong", "time"}
# containers whose children are separate items written side by side
JOIN = {"meta-row": " · ", "chips": " · "}


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []

    def cls(self):
        return set((self.attrs.get("class") or "").split())


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {})
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def find(node, pred):
    if isinstance(node, str):
        return None
    if pred(node):
        return node
    for c in node.children:
        hit = find(c, pred)
        if hit:
            return hit
    return None


def skipped(n):
    if n.tag in SKIP_TAGS or n.attrs.get("aria-hidden") == "true":
        return True
    if "data-ph" in n.attrs or "data-dur" in n.attrs or "data-text-skip" in n.attrs:
        return True
    if n.tag == "a" and n.attrs.get("href", "").endswith(".md"):
        return True
    if n.cls() & SKIP_CLASSES:
        return True
    if "sr-only" in n.cls() and "new tab" in text_of(n):
        return True
    return False


def text_of(n):
    if isinstance(n, str):
        return n
    return "".join(text_of(c) for c in n.children)


def absolute(href):
    if href.startswith(("http://", "https://", "mailto:", "tel:")):
        return href
    if href.startswith("#"):
        return None
    href = re.sub(r"^(\.\./|\./)+", "", href)
    return SITE + "/" + href.lstrip("/")


def inline(n):
    """Render a node's children as one line of Markdown."""
    out = []
    prev_el = False
    for c in n.children:
        if isinstance(c, str):
            out.append(re.sub(r"\s+", " ", c))
            prev_el = False
            continue
        if skipped(c):
            continue
        if prev_el:
            out.append(" ")
        prev_el = c.tag in LABEL_TAGS
        if c.tag == "span" and "cs-carry" in n.cls() and not out:
            out.append(f"**{inline(c).strip()}:** ")
            prev_el = False
            continue
        if c.tag == "br":
            out.append(" ")
        elif c.tag == "a":
            label = inline(c).strip()
            href = absolute(c.attrs.get("href", ""))
            out.append(f"[{label}]({href})" if href and label else label)
        elif c.tag in ("strong", "b"):
            t = inline(c).replace("*", "").strip()
            out.append(f"**{t}**" if t else "")
        elif c.tag == "em":
            t = inline(c).strip()
            out.append(f"*{t}*" if t else "")
        elif c.tag == "q":
            out.append("“" + inline(c).strip() + "”")
        else:
            out.append(inline(c))
    return re.sub(r"\s+", " ", "".join(out))


def has_block_child(n):
    return any(not isinstance(c, str) and not skipped(c) and (c.tag in BLOCK or has_block_child(c)) for c in n.children)


def blocks(n, out, list_depth=0):
    for c in n.children:
        if isinstance(c, str):
            t = re.sub(r"\s+", " ", c).strip()
            if t:
                out.append(t)
            continue
        if skipped(c):
            continue
        if c.attrs.get("role") == "img" and c.attrs.get("aria-label"):
            out.append(f"*Figure: {c.attrs['aria-label']}*")
            continue
        tag = c.tag
        sep = next((JOIN[k] for k in c.cls() if k in JOIN), None)
        if sep:
            parts = [inline(x).strip() for x in c.children if not isinstance(x, str) and not skipped(x)]
            parts = [x for x in parts if x]
            if parts:
                out.append(sep.join(parts))
            continue
        if tag == "a" and has_block_child(c):
            blocks(c, out, list_depth)
            href = absolute(c.attrs.get("href", ""))
            if href:
                out.append(f"Link: {href}")
            continue
        if tag in ("h1", "h2", "h3", "h4"):
            level = {"h1": 1, "h2": 2, "h3": 3, "h4": 4}[tag]
            t = inline(c).replace("*", "").strip()
            if t:
                out.append("#" * level + " " + t)
        elif tag in ("ul", "ol"):
            items = []
            for i, li in enumerate([x for x in c.children if not isinstance(x, str) and x.tag == "li" and not skipped(x)], 1):
                if has_block_child(li):
                    sub = []
                    blocks(li, sub, list_depth + 1)
                    sub = [s for s in sub if s]
                    if not sub:
                        continue
                    head = sub[0].lstrip("# ")
                    rest = ["   " + s for s in sub[1:]]
                    items.append((f"{i}. " if tag == "ol" else "- ") + head + ("\n" + "\n".join(rest) if rest else ""))
                else:
                    t = inline(li).strip()
                    if t:
                        items.append((f"{i}. " if tag == "ol" else "- ") + t)
            if items:
                out.append("\n".join(items))
        elif tag == "dl":
            rows = []
            pairs = [x for x in c.children if not isinstance(x, str) and not skipped(x)]
            groups = [p.children for p in pairs if p.tag == "div"] or [pairs]
            for g in groups:
                dts = [inline(x).strip() for x in g if not isinstance(x, str) and x.tag == "dt" and not skipped(x)]
                dds = [inline(x).strip() for x in g if not isinstance(x, str) and x.tag == "dd" and not skipped(x)]
                dds = [d for d in dds if d]
                if dts and dds:
                    rows.append(f"- **{' / '.join(dts)}:** {' '.join(dds)}")
                elif dts:
                    rows.append(f"- **{' / '.join(dts)}**")
            if rows:
                out.append("\n".join(rows))
        elif tag in ("p", "figcaption", "dt", "dd", "li"):
            t = inline(c).strip()
            if t:
                out.append(t)
        elif tag == "blockquote":
            sub = []
            blocks(c, sub, list_depth)
            if sub:
                out.append("\n".join("> " + s for s in sub))
        elif tag in BLOCK or has_block_child(c):
            blocks(c, out, list_depth)
        else:
            wrapper = Node("span", {})
            wrapper.children = [c]
            t = inline(wrapper).strip()
            if t:
                out.append(t)


def page_meta(tree):
    head = find(tree.root, lambda n: n.tag == "head")
    title = find(head, lambda n: n.tag == "title")
    desc = find(head, lambda n: n.tag == "meta" and n.attrs.get("name") == "description")
    return (text_of(title).strip() if title else ""), (desc.attrs.get("content", "").strip() if desc else "")


def to_markdown(src, url_path):
    tree = Tree()
    tree.feed(src)
    title, desc = page_meta(tree)
    main = find(tree.root, lambda n: n.tag == "main")
    out = []
    blocks(main, out)
    # tidy: drop leftover separators and collapse duplicates next to each other
    cleaned = []
    for b in out:
        b = re.sub(r"·\s*,\s*", "· ", b).strip()
        if not b or b in ("·", "→", "↓"):
            continue
        if cleaned and cleaned[-1] == b:
            continue
        cleaned.append(b)
    h1 = next((b for b in cleaned if b.startswith("# ")), None)
    if h1:
        cleaned.remove(h1)
    body = "\n\n".join(cleaned)
    header = [
        h1 or f"# {title}",
        "",
        f"> Text version of {SITE}{url_path}, generated from the page. The visual page is the primary version; images are not included.",
    ]
    if desc:
        header += ["", desc]
    footer = [
        "",
        "---",
        "",
        "Shoghi Bagul · [shoghi07@gmail.com](mailto:shoghi07@gmail.com) · "
        "[LinkedIn](https://www.linkedin.com/in/shoghi07) · [Behance](https://www.behance.net/shoghi07) · "
        f"[Site]({SITE}/)",
        "",
    ]
    md = "\n".join(header) + "\n\n" + body + "\n" + "\n".join(footer)
    return md, title, desc, tree, (h1 or f"# {title}")[2:].strip(), body


def md_inline(t):
    """Escape, then **bold**, *italic* and [links](url) — the subset to_markdown emits."""
    t = html.escape(t, quote=False)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    return t


def is_label(block):
    """A short, single-line block that isn't a sentence: a section kicker."""
    return (
        "\n" not in block
        and len(block) <= 70
        and not re.match(r"^(#|>|-|\d+\.|\*|\[)", block)
        and not block.rstrip().endswith((".", "?", "!", ":"))
    )


def md_to_html(md):
    out = []
    blocks_ = [b for b in md.split("\n\n") if b.strip()]
    for i, block in enumerate(blocks_):
        # a label (or two) directly above a heading sits with that heading
        ahead = blocks_[i + 1 : i + 3]
        heading_next = next((k for k, b in enumerate(ahead) if b.startswith("## ")), None)
        if is_label(block) and heading_next is not None and all(is_label(b) for b in ahead[:heading_next]):
            out.append(f'<p class="rd-kicker">{md_inline(block)}</p>')
            continue
        lines = block.split("\n")
        first = lines[0]
        m = re.match(r"^(#{1,4}) (.*)", first)
        if m and len(lines) == 1:
            level = len(m.group(1))
            out.append(f"<h{level}>{md_inline(m.group(2))}</h{level}>")
        elif first.startswith("> "):
            paras = "".join(f"<p>{md_inline(l[2:])}</p>" for l in lines)
            out.append(f"<blockquote>{paras}</blockquote>")
        elif re.match(r"^(\d+\.|-) ", first):
            tag = "ol" if first[0].isdigit() else "ul"
            items, cur = [], None
            for l in lines:
                mm = re.match(r"^(\d+\.|-) (.*)", l)
                if mm:
                    cur = [mm.group(2)]
                    items.append(cur)
                elif cur is not None:
                    cur.append(l.strip())
            html_items = []
            for it in items:
                head, rest = it[0], it[1:]
                if rest:
                    parts = [f'<p class="rd-label">{md_inline(head)}</p>']
                    for r in rest:
                        hm = re.match(r"^(#{1,4}) (.*)", r)
                        parts.append(f"<h3>{md_inline(hm.group(2))}</h3>" if hm else f"<p>{md_inline(r)}</p>")
                    html_items.append("<li>" + "".join(parts) + "</li>")
                else:
                    html_items.append(f"<li>{md_inline(head)}</li>")
            out.append(f"<{tag}>" + "".join(html_items) + f"</{tag}>")
        elif first == "---":
            out.append("<hr />")
        elif re.match(r"^\*Figure: .*\*$", first):
            out.append(f'<p class="rd-figure">{md_inline(first[1:-1])}</p>')
        else:
            out.append("<p>" + md_inline(" ".join(lines)) + "</p>")
    return "\n".join(out)


def reader_path(url_path):
    """/ -> read/index.html (/read), /about -> read/about.html, /work/x -> read/work/x.html"""
    if url_path == "/":
        return "read/index.html", "/read"
    return "read" + url_path + ".html", "/read" + url_path


def reader_page(url_path, md_path, title, desc, h1, body):
    words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9’'%+-]*", body + " " + h1))
    minutes = max(1, round(words / 238))
    # if the page opens with a short "a · b · c" kicker, fold it into the meta
    # line (dropping its read time, which also counted images)
    meta = "Text version"
    parts = body.split("\n\n", 1)
    if "·" in parts[0] and is_label(parts[0]):
        kicker = re.sub(r"\s*·\s*\d+ min read", "", parts[0]).strip()
        meta += " · " + kicker
        body = parts[1] if len(parts) > 1 else ""
    meta += f" · {minutes} min read"
    back_label = (
        "Back to the full case study" if url_path.startswith("/work/")
        else "Back to the homepage" if url_path == "/"
        else "Back to the full page"
    )
    back = f'<a class="rd-back" href="{url_path}">← {back_label}</a>'
    e = lambda t: html.escape(t, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
	<head>
		<meta charset="utf-8" />
		<meta name="viewport" content="width=device-width, initial-scale=1" />
		<title>{e(h1)} · Text version · Shoghi Bagul</title>
		<meta name="description" content="{e(desc)}" />
		<meta name="robots" content="noindex" />
		<meta name="theme-color" content="#f2f1ee" />
		<link rel="canonical" href="{SITE}{url_path}" />
		<link rel="alternate" type="text/markdown" href="/{md_path}" title="Markdown" />
		<link rel="icon" href="/favicon.ico" sizes="32x32" />
		<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml" />
		<link rel="preconnect" href="https://fonts.googleapis.com" />
		<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
		<link
			href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;1,400&family=Figtree:wght@400;500&family=IBM+Plex+Mono:wght@400;500&display=swap"
			rel="stylesheet"
		/>
		<link rel="stylesheet" href="/css/reader.css" />
		<script>
			window.va = window.va || function () {{ (window.vaq = window.vaq || []).push(arguments); }};
		</script>
		<script defer src="/_vercel/insights/script.js"></script>
	</head>
	<body>
		<!-- Generated by tools/generate-text.py from {url_path}. Edit the page, then re-run the script. -->
		<header class="rd-bar">
			<div class="rd-col">
				<a class="rd-name" href="/">Shoghi Bagul</a>
				{back}
			</div>
		</header>
		<main id="main" class="rd-col rd">
			<article>
				<p class="rd-meta">{md_inline(meta)}</p>
				<h1>{md_inline(h1)}</h1>
{md_to_html(body)}
			</article>
		</main>
		<footer class="rd-col rd-foot">
			{back}
			<p>Shoghi Bagul · <a href="mailto:shoghi07@gmail.com">shoghi07@gmail.com</a> · <a href="https://www.linkedin.com/in/shoghi07">LinkedIn</a> · <a href="https://www.behance.net/shoghi07">Behance</a></p>
		</footer>
	</body>
</html>
"""


def json_ld(html_path, url_path, title, desc, tree):
    url = SITE + url_path
    if html_path == "about.html":
        return {
            "@context": "https://schema.org",
            "@type": "ProfilePage",
            "url": url,
            "name": title,
            "description": desc,
            "mainEntity": AUTHOR,
        }
    if not html_path.startswith("work/"):
        return None
    h1 = find(tree.root, lambda n: n.tag == "h1")
    data = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "genre": "Product design case study",
        "url": url,
        "name": text_of(h1).strip() if h1 else title,
        "headline": title,
        "description": desc,
        "inLanguage": "en",
        "author": AUTHOR,
        "creator": AUTHOR,
    }
    if html_path in NAMED_CLIENTS:
        data["about"] = NAMED_CLIENTS[html_path]
    return data


def update_html(src, html_path, md_path, ld, read_url):
    md_url = "/" + md_path
    # alternate link in <head>
    alt = f'<link rel="alternate" type="text/markdown" href="{md_url}" title="Text version" />'
    src = re.sub(r'\s*<link rel="alternate" type="text/markdown"[^>]*/>', "", src)
    src = src.replace('<link rel="canonical"', alt + '\n\t\t<link rel="canonical"', 1)
    # JSON-LD for this page
    src = re.sub(r'\s*<script type="application/ld\+json" id="ld-page">.*?</script>', "", src, flags=re.S)
    if ld:
        block = (
            '\t\t<script type="application/ld+json" id="ld-page">\n'
            + json.dumps(ld, ensure_ascii=False, indent="\t")
            + "\n\t\t</script>\n\t</head>"
        )
        src = src.replace("\t</head>", block, 1)
    # "Read as text" in the footer
    src = re.sub(r'\s*<a href="[^"]*" data-text-link>Read as text</a>', "", src)
    src = src.replace(
        '<div class="foot-links">',
        f'<div class="foot-links">\n\t\t\t\t\t<a href="{read_url}" data-text-link>Read as text</a>',
        1,
    )
    return src


def main():
    index = []
    for html_path, url_path, md_path in PAGES:
        full = os.path.join(ROOT, html_path)
        src = open(full, encoding="utf-8").read()
        md, title, desc, tree, h1, body = to_markdown(src, url_path)
        with open(os.path.join(ROOT, md_path), "w", encoding="utf-8") as fh:
            fh.write(md)
        read_file, read_url = reader_path(url_path)
        os.makedirs(os.path.dirname(os.path.join(ROOT, read_file)), exist_ok=True)
        with open(os.path.join(ROOT, read_file), "w", encoding="utf-8") as fh:
            fh.write(reader_page(url_path, md_path, title, desc, h1, body))
        ld = json_ld(html_path, url_path, title, desc, tree)
        new = update_html(src, html_path, md_path, ld, read_url)
        if new != src:
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(new)
        if not html_path.startswith("work/") or html_path in INDEXED_WORK:
            index.append((html_path, url_path, md_path, title, desc))
        print(f"  {md_path:32} {len(md.split()):5} words   + {read_file}")

    home = next(i for i in index if i[0] == "index.html")
    lines = [
        "# Shoghi Bagul",
        "",
        f"> {home[4]}",
        "",
        "Product designer and Design Lead at Tcules, Ahmedabad (M.Des, NID Ahmedabad). "
        "Every page below has a plain-text Markdown version, generated from the page itself.",
        "",
        "## Pages",
        "",
    ]
    for html_path, url_path, md_path, title, desc in index:
        if html_path.startswith("work/"):
            continue
        lines.append(f"- [{title}]({SITE}{url_path}): {desc} Text: {SITE}/{md_path}")
    lines += ["", "## Case studies", ""]
    for html_path, url_path, md_path, title, desc in index:
        if not html_path.startswith("work/"):
            continue
        lines.append(f"- [{title}]({SITE}{url_path}): {desc} Text: {SITE}/{md_path}")
    lines += [
        "",
        "## Contact",
        "",
        "- Email: shoghi07@gmail.com",
        "- LinkedIn: https://www.linkedin.com/in/shoghi07",
        "- Behance: https://www.behance.net/shoghi07",
        "",
    ]
    with open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"  llms.txt                             {len(index)} pages listed")


if __name__ == "__main__":
    main()
