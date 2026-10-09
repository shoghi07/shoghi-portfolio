/* ------------------------------------------------------------------
   Delicut case study (work/delicut.html).

   The page reads without this file: pinned sections and reveals fall
   back to plain stacked content (the sign-up and calendar figures stay in
   their "before" state). This adds the scroll behaviour on top:
   the section indicator, figures that animate in when they reach the
   viewport ([data-anim] → .is-on), the insight words brightening, three
   pinned sections driven by scroll progress, and the compare slider.

   Pinned sections need room, so on narrow or very tall screens and with
   reduced motion the page switches to .cs-static: no pinning, everything
   stacked and visible.
   ------------------------------------------------------------------ */
(() => {
	const root = document.documentElement;
	const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
	const clamp = (v) => Math.min(1, Math.max(0, v));
	let isStatic = false;

	const setStatic = () => {
		isStatic = reduce.matches || window.innerWidth < 760 || window.innerHeight > 2000;
		root.classList.toggle("cs-static", isStatic);
	};
	setStatic();

	/* --- figures that animate once they are on screen --- */
	const anims = [...document.querySelectorAll("[data-anim]")];
	if (isStatic || !("IntersectionObserver" in window)) {
		anims.forEach((el) => el.classList.add("is-on"));
	} else {
		const io = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					if (entry.isIntersecting) {
						entry.target.classList.add("is-on");
						io.unobserve(entry.target);
					}
				}
			},
			{ rootMargin: "0px 0px -20% 0px" }
		);
		anims.forEach((el) => io.observe(el));
	}

	/* --- reading time ---
	   Words in the case study at an average silent-reading pace (238 wpm),
	   plus time for each visual: 12s for the first, a second less for each
	   after it, never under 3s (the convention Medium popularised). Labels
	   inside placeholders are skipped, so the estimate holds as real images
	   replace them. */
	const readTime = document.querySelector("[data-read-time]");
	const main = document.querySelector("main");
	if (readTime && main) {
		const copy = main.cloneNode(true);
		copy.querySelectorAll(".ph-id, .ph-label, .cs-blocks, .sr-only, svg, [aria-hidden='true']").forEach((el) => el.remove());
		const words = (copy.textContent.match(/[A-Za-z0-9][A-Za-z0-9’'%+-]*/g) || []).length;
		const visuals = main.querySelectorAll(".ph, .cs-browser, .cs-phone").length;
		let seconds = (words / 238) * 60;
		for (let i = 0; i < visuals; i++) seconds += Math.max(3, 12 - i);
		readTime.textContent = `${Math.max(1, Math.round(seconds / 60))} min read`;
	}

	/* --- before / after: drag the handle (or use the arrow keys) --- */
	document.querySelectorAll("[data-compare]").forEach((fig) => {
		const box = fig.querySelector(".cs-compare");
		const handle = fig.querySelector("[data-compare-handle]");
		if (!box || !handle) return;
		let pos = 50;
		const set = (v) => {
			pos = Math.round(Math.min(100, Math.max(0, v)));
			box.style.setProperty("--pos", `${pos}%`);
			handle.setAttribute("aria-valuenow", String(pos));
			handle.setAttribute(
				"aria-valuetext",
				pos === 0 ? "All V2" : pos === 100 ? "All original" : `${pos}% original, ${100 - pos}% V2`
			);
		};
		const fromPointer = (e) => {
			const r = box.getBoundingClientRect();
			set(((e.clientX - r.left) / r.width) * 100);
		};
		handle.addEventListener("pointerdown", (e) => {
			e.preventDefault();
			handle.setPointerCapture(e.pointerId);
			handle.classList.add("is-dragging");
			box.classList.add("is-dragging");
			fromPointer(e);
		});
		handle.addEventListener("pointermove", (e) => {
			if (handle.hasPointerCapture(e.pointerId)) fromPointer(e);
		});
		const end = (e) => {
			if (handle.hasPointerCapture(e.pointerId)) handle.releasePointerCapture(e.pointerId);
			handle.classList.remove("is-dragging");
			box.classList.remove("is-dragging");
		};
		handle.addEventListener("pointerup", end);
		handle.addEventListener("pointercancel", end);
		handle.addEventListener("keydown", (e) => {
			const step = e.shiftKey ? 20 : 5;
			const keys = { ArrowLeft: pos - step, ArrowDown: pos - step, ArrowRight: pos + step, ArrowUp: pos + step, Home: 0, End: 100 };
			if (e.key in keys) {
				e.preventDefault();
				set(keys[e.key]);
			}
		});
		set(50);
	});

	/* --- section indicator: one bar per section --- */
	const ind = document.querySelector("[data-ind]");
	const indLinks = ind ? [...ind.querySelectorAll("a")] : [];
	const chapters = indLinks.map((a) => document.querySelector(a.getAttribute("href")));
	const endBand = document.querySelector(".cs-end");
	const darkBands = [...document.querySelectorAll(".cs-band")];

	/* --- scroll-driven pieces --- */
	const insight = document.querySelector("[data-insight]");
	const insightWords = insight ? insight.querySelector(".cs-insight") : null;

	const pins = [...document.querySelectorAll("[data-pin]")];
	/* 0 when the pin's top reaches the sticky line (just under the site
	   header), 1 when the stage is about to scroll away */
	const progressOf = (el) => {
		const stage = el.querySelector(".pin-stage");
		if (!stage) return 0;
		const r = el.getBoundingClientRect();
		const stick = parseFloat(getComputedStyle(stage).top) || 0;
		return clamp((stick - r.top) / Math.max(1, r.height - stage.offsetHeight));
	};

	const drawBrowser = (pin, p) => {
		const device = pin.querySelector("[data-device]");
		const view = device ? device.dataset.view : "desktop";
		const vp = pin.querySelector(`[data-vp="${view}"]`);
		const page = pin.querySelector(`[data-page="${view}"]`);
		if (vp && page) {
			const shift = isStatic ? 0 : p * Math.max(0, page.scrollHeight - vp.clientHeight);
			page.style.setProperty("--shift", shift.toFixed(1));
			vp.style.setProperty("--sp", (isStatic ? 0 : p).toFixed(3));
		}
		pin.querySelectorAll("[data-notes] > li").forEach((li) => {
			const [a, b] = (li.dataset.range || "0 0").split(" ").map(Number);
			li.classList.toggle("is-active", !isStatic && p >= a && p < b);
		});
	};

	/* desktop / mobile switch for the pinned page */
	document.querySelectorAll("[data-view-btn]").forEach((btn) => {
		btn.addEventListener("click", () => {
			const pin = btn.closest("[data-pin]");
			const device = pin && pin.querySelector("[data-device]");
			if (!device) return;
			device.dataset.view = btn.dataset.viewBtn;
			pin.querySelectorAll("[data-view-btn]").forEach((b) =>
				b.setAttribute("aria-pressed", String(b === btn))
			);
			onScroll();
		});
	});

	/* --- learnings carousel ---
	   While pinned, scroll progress picks the card and the track glides so
	   it sits centred; between steps the card holds still for reading. The
	   index and arrows jump to a card by scrolling to its spot. In
	   .cs-static the track scrolls sideways and the active card follows it. */
	const learnPin = document.querySelector('[data-pin="learn"]');
	const learnTrack = learnPin && learnPin.querySelector("[data-learn-track]");
	const learnCards = learnTrack ? [...learnTrack.children] : [];
	const learnTabs = learnPin ? [...learnPin.querySelectorAll("[data-learn-go]")] : [];
	const learnArrows = learnPin ? [...learnPin.querySelectorAll("[data-learn-step]")] : [];
	let learnIdx = -1;

	const setLearn = (i) => {
		if (!learnTrack) return;
		learnIdx = i;
		learnCards.forEach((c, k) => c.classList.toggle("is-active", k === i));
		learnTabs.forEach((t, k) => {
			if (k === i) t.setAttribute("aria-current", "true");
			else t.removeAttribute("aria-current");
		});
		learnArrows.forEach((b) => {
			const to = i + Number(b.dataset.learnStep);
			b.disabled = to < 0 || to >= learnCards.length;
		});
		if (!isStatic) {
			const stage = learnPin.querySelector(".pin-stage");
			const card = learnCards[i];
			const tx = stage.clientWidth / 2 - (card.offsetLeft + card.offsetWidth / 2);
			learnTrack.style.setProperty("--tx", tx.toFixed(1));
		} else {
			learnTrack.style.setProperty("--tx", "0");
		}
	};

	const goLearn = (i) => {
		if (!learnTrack) return;
		i = Math.max(0, Math.min(learnCards.length - 1, i));
		const behavior = reduce.matches ? "auto" : "smooth";
		if (isStatic) {
			const card = learnCards[i];
			const pad = parseFloat(getComputedStyle(learnTrack).scrollPaddingLeft) || 0;
			learnTrack.scrollTo({ left: card.offsetLeft - learnTrack.offsetLeft - pad, behavior });
			setLearn(i);
			return;
		}
		const stage = learnPin.querySelector(".pin-stage");
		const top = learnPin.getBoundingClientRect().top + window.scrollY;
		const travel = learnPin.offsetHeight - stage.offsetHeight;
		const target = top + (i / Math.max(1, learnCards.length - 1)) * travel;
		window.scrollTo({ top: Math.round(target) + 1, behavior });
	};

	learnTabs.forEach((t) => t.addEventListener("click", () => goLearn(Number(t.dataset.learnGo))));
	learnArrows.forEach((b) =>
		b.addEventListener("click", () => goLearn(Math.max(0, learnIdx) + Number(b.dataset.learnStep)))
	);
	if (learnPin) {
		learnPin.addEventListener("keydown", (e) => {
			if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
			if (!e.target.closest(".cs-learn-head")) return;
			e.preventDefault();
			goLearn(Math.max(0, learnIdx) + (e.key === "ArrowRight" ? 1 : -1));
		});
	}
	if (learnTrack) {
		learnTrack.addEventListener(
			"scroll",
			() => {
				if (!isStatic) return;
				const left = learnTrack.scrollLeft;
				let best = 0;
				learnCards.forEach((c, k) => {
					const off = c.offsetLeft - learnCards[0].offsetLeft;
					if (Math.abs(off - left) < Math.abs(learnCards[best].offsetLeft - learnCards[0].offsetLeft - left)) best = k;
				});
				if (best !== learnIdx) setLearn(best);
			},
			{ passive: true }
		);
	}

	const drawLearn = (pin, p) => {
		if (isStatic) {
			if (learnIdx < 0) setLearn(0);
			return;
		}
		const i = Math.min(learnCards.length - 1, Math.round(p * (learnCards.length - 1)));
		if (i !== learnIdx) setLearn(i);
	};

	const drawCheckout = (pin, p) => {
		const step = isStatic ? -1 : Math.min(2, Math.floor(p * 3));
		pin.querySelectorAll("[data-steps] > li:not(.cs-summary-note)").forEach((li, i) => {
			li.classList.toggle("is-active", i === step);
		});
		pin.querySelectorAll("[data-frames] > .ph").forEach((f, i) => {
			f.classList.toggle("is-active", i === step);
			f.classList.toggle("is-before", i < step);
		});
	};

	const drawPhones = (pin, p) => {
		const rail = pin.querySelector("[data-rail]");
		const label = pin.querySelector("[data-rail-label]");
		if (!rail) return;
		if (isStatic) {
			rail.style.setProperty("--tx", "0");
			if (label) label.textContent = "";
			return;
		}
		const travel = Math.max(0, rail.scrollWidth - window.innerWidth);
		rail.style.setProperty("--tx", (-p * travel).toFixed(1));
		if (label) {
			let group = "";
			for (const li of rail.children) {
				if (li.getBoundingClientRect().left < window.innerWidth * 0.5) group = li.dataset.group || group;
			}
			label.textContent = group ? `Now: ${group}` : "";
		}
	};

	const draw = () => {
		const vh = window.innerHeight;

		if (ind && chapters.every(Boolean)) {
			/* the reading line sits at 40% of the viewport */
			const line = vh * 0.4;
			let current = 0;
			chapters.forEach((el, i) => {
				if (el.getBoundingClientRect().top <= line) current = i;
			});
			const bands = darkBands.map((band) => band.getBoundingClientRect());
			indLinks.forEach((a, i) => {
				if (i === current) a.setAttribute("aria-current", "location");
				else a.removeAttribute("aria-current");
				/* light bars wherever a dark band is behind this one */
				const r = a.getBoundingClientRect();
				const y = r.top + r.height / 2;
				a.classList.toggle("is-dark", bands.some((b) => b.top <= y && b.bottom >= y));
			});
			/* only between the start of the journey and the closing band */
			const afterStart = chapters[0].getBoundingClientRect().top <= line;
			const beforeEnd = !endBand || endBand.getBoundingClientRect().top > line;
			ind.classList.toggle("is-shown", afterStart && beforeEnd);
		}

		if (insightWords) {
			const r = insight.getBoundingClientRect();
			const p = isStatic ? 1 : clamp((vh * 0.85 - r.top) / (vh * 0.7));
			insightWords.style.setProperty("--p", p.toFixed(3));
		}

		pins.forEach((pin) => {
			const p = isStatic ? 0 : progressOf(pin);
			if (pin.dataset.pin === "browser") drawBrowser(pin, p);
			else if (pin.dataset.pin === "checkout") drawCheckout(pin, p);
			else if (pin.dataset.pin === "phones") drawPhones(pin, p);
			else if (pin.dataset.pin === "learn") drawLearn(pin, p);
		});
	};

	let queued = false;
	const onScroll = () => {
		if (queued) return;
		queued = true;
		requestAnimationFrame(() => {
			queued = false;
			draw();
		});
	};
	window.addEventListener("scroll", onScroll, { passive: true });
	window.addEventListener("resize", () => {
		setStatic();
		if (learnIdx >= 0) setLearn(learnIdx);
		if (isStatic) anims.forEach((el) => el.classList.add("is-on"));
		onScroll();
	});
	reduce.addEventListener?.("change", () => {
		setStatic();
		if (isStatic) anims.forEach((el) => el.classList.add("is-on"));
		onScroll();
	});
	draw();
})();
