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
		const onScroll = () => nav.classList.toggle("is-scrolled", window.scrollY > 12);
		onScroll();
		window.addEventListener("scroll", onScroll, { passive: true });
	}
})();
