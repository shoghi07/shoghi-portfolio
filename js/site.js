(() => {
	document.documentElement.classList.add("js");

	document.querySelectorAll("[data-year]").forEach((el) => {
		el.textContent = String(new Date().getFullYear());
	});

	const tick = () => {
		const time = new Intl.DateTimeFormat("en-GB", {
			timeZone: "Asia/Kolkata",
			hour: "2-digit",
			minute: "2-digit",
			hour12: true,
		}).format(new Date());
		document.querySelectorAll("[data-clock]").forEach((el) => {
			el.textContent = `Ahmedabad · ${time}`;
		});
	};
	tick();
	setInterval(tick, 30000);

	if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		const reveal = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (entry.isIntersecting) {
						entry.target.classList.add("is-in");
						reveal.unobserve(entry.target);
					}
				}
			},
			{ threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
		);
		document.querySelectorAll("[data-reveal]").forEach((el) => reveal.observe(el));
	} else {
		document.querySelectorAll("[data-reveal]").forEach((el) => el.classList.add("is-in"));
	}

	const preview = document.querySelector("[data-preview]");
	const cover = document.querySelector("[data-preview-cover]");
	const rows = document.querySelectorAll("[data-cover]");
	if (preview && cover && rows.length && window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
		const place = (event) => {
			const x = Math.min(event.clientX + 28, window.innerWidth - 380);
			const y = Math.min(Math.max(event.clientY - 90, 16), window.innerHeight - 280);
			preview.style.transform = `translate(${x}px, ${y}px)`;
		};

		rows.forEach((row) => {
			row.addEventListener("mouseenter", (event) => {
				cover.className = `cover cover--${row.dataset.cover}`;
				cover.innerHTML = row.dataset.word
					? `<span class="cover-word">${row.dataset.word}</span>`
					: "";
				preview.hidden = false;
				place(event);
			});
			row.addEventListener("mousemove", place);
			row.addEventListener("mouseleave", () => {
				preview.hidden = true;
			});
		});
	}

	const nav = document.querySelector("[data-header]");
	if (nav) {
		/* the header hides while scrolling down and comes back on any scroll
		   up; it always shows near the top of the page */
		let lastY = window.scrollY;
		const onScroll = () => {
			const y = window.scrollY;
			nav.classList.toggle("is-scrolled", y > 12);
			if (y < nav.offsetHeight * 2) nav.classList.remove("is-hidden");
			else if (y > lastY + 4) nav.classList.add("is-hidden");
			else if (y < lastY - 4) nav.classList.remove("is-hidden");
			if (Math.abs(y - lastY) > 4) lastY = y;
		};
		onScroll();
		window.addEventListener("scroll", onScroll, { passive: true });
	}

	/* --- back to top: appears after ~1.5 screens of scrolling --- */
	const toTop = document.createElement("button");
	toTop.type = "button";
	toTop.className = "to-top";
	toTop.setAttribute("aria-label", "Back to top");
	toTop.innerHTML =
		'<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 13V3M3.5 7.5L8 3l4.5 4.5" /></svg><span class="to-top-tip" aria-hidden="true">Back to top</span>';
	document.body.appendChild(toTop);
	const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
	toTop.addEventListener("click", () => {
		window.scrollTo({ top: 0, behavior: reduceMotion.matches ? "auto" : "smooth" });
		const first = document.querySelector("[data-header] .logo");
		if (first) first.focus({ preventScroll: true });
	});
	const onTopScroll = () => {
		toTop.classList.toggle("is-shown", window.scrollY > window.innerHeight * 1.5);
	};
	onTopScroll();
	window.addEventListener("scroll", onTopScroll, { passive: true });

	/* ------------------------------------------------------------------
	   Career timeline.

	   Both the homepage years strip and the about-page spine are authored
	   in HTML with correct-at-publish numbers, then recomputed here from
	   data-start / data-end ("now" for the current role). Nothing that
	   depends on today's date is hardcoded, so the figures, the duration
	   bars and the "4 yrs 10 mos" labels stay right on their own.
	   ------------------------------------------------------------------ */

	/* months since year 0, so durations are plain subtraction */
	const toMonths = (value) => {
		if (!value || value === "now") {
			const d = new Date();
			return d.getFullYear() * 12 + d.getMonth();
		}
		const m = /^(\d{4})-(\d{2})$/.exec(value);
		return m ? Number(m[1]) * 12 + (Number(m[2]) - 1) : null;
	};

	/* an entry with no data-start (the "Earlier" row) has no span at all —
	   without this it would read as now→now and set a zero-width bar */
	const spanOf = (el) => {
		if (!el.dataset.start) return null;
		const start = toMonths(el.dataset.start);
		const end = toMonths(el.dataset.end);
		return start === null || end === null ? null : { start, end, months: end - start };
	};

	const formatDuration = (months) => {
		const y = Math.floor(months / 12);
		const m = months % 12;
		const parts = [];
		if (y) parts.push(`${y} yr${y > 1 ? "s" : ""}`);
		if (m) parts.push(`${m} mo${m > 1 ? "s" : ""}`);
		return parts.join(" ") || "—";
	};

	/* --- A · years strip: place every segment on a fixed 2020–2027 axis --- */
	document.querySelectorAll("[data-years]").forEach((fig) => {
		const t0 = toMonths(fig.dataset.years || "2020-01");
		const span = Number(fig.dataset.span || 7) * 12;
		const pct = (m) => ((m - t0) / span) * 100;

		fig.querySelectorAll("[data-seg]").forEach((seg) => {
			const s = spanOf(seg);
			if (!s) return;
			seg.style.setProperty("--s", pct(s.start).toFixed(2));
			seg.style.setProperty("--w", (pct(s.end) - pct(s.start)).toFixed(2));
		});

		const now = fig.querySelector("[data-now-mark]");
		if (now) now.style.setProperty("--s", pct(toMonths("now")).toFixed(2));
	});

	/* --- durations: every [data-dur] prints the span of its own dates --- */
	document.querySelectorAll("[data-dur]").forEach((el) => {
		const s = spanOf(el);
		if (s) el.textContent = formatDuration(s.months);
	});

	/* --- B · spine: bar widths, then fill and ticks driven by scroll --- */
	const spineBox = document.querySelector("[data-spine]");
	if (spineBox) {
		const roles = [...spineBox.querySelectorAll("[data-tick]")];
		const spans = roles.map(spanOf);
		const longest = Math.max(1, ...spans.map((s) => (s ? s.months : 0)));
		spineBox.style.setProperty("--mo-max", String(longest));
		roles.forEach((role, i) => {
			if (spans[i]) role.style.setProperty("--mo", String(spans[i].months));
		});

		const fill = spineBox.querySelector("[data-spine-fill]");
		if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
			roles.forEach((r) => r.classList.add("is-past"));
		} else {
			let queued = false;
			const draw = () => {
				const box = spineBox.getBoundingClientRect();
				const line = window.innerHeight * 0.62;
				if (fill) {
					const p = (line - box.top) / box.height;
					fill.style.setProperty("--p", String(Math.max(0, Math.min(1, p))));
				}
				roles.forEach((r) => {
					r.classList.toggle("is-past", r.getBoundingClientRect().top < line);
				});
			};
			const onTimelineScroll = () => {
				if (queued) return;
				queued = true;
				requestAnimationFrame(() => {
					queued = false;
					draw();
				});
			};
			window.addEventListener("scroll", onTimelineScroll, { passive: true });
			window.addEventListener("resize", onTimelineScroll, { passive: true });
			draw();
		}
	}
})();
