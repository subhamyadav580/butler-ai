document.documentElement.classList.remove("no-js");

// Theme toggle: follows the system until the visitor picks one (remembered per browser)
(function () {
  const root = document.documentElement;
  try {
    const saved = localStorage.getItem("theme");
    if (saved) root.dataset.theme = saved;
  } catch (_) { /* storage blocked: follow the system */ }

  document.getElementById("theme-toggle").addEventListener("click", () => {
    const dark = root.dataset.theme
      ? root.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (_) {}
  });
})();

// Hero: type out example requests, one after another
(function () {
  const el = document.getElementById("typed");
  const prompts = [
    "How many unread mails do I have in Primary?",
    "Order milk and bread, wherever it's cheaper",
    "What's on my calendar tomorrow?",
    "Reply to Ankit: Friday at 8 works",
    "Book a table for 2 tonight in Indiranagar",
    "Remind me to pay rent on Friday",
  ];
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    el.textContent = prompts[0];
    return;
  }
  let i = 0, chars = 0, deleting = false;
  function tick() {
    const text = prompts[i];
    chars += deleting ? -1 : 1;
    el.textContent = text.slice(0, chars);
    let delay = deleting ? 22 : 45;
    if (!deleting && chars === text.length) { deleting = true; delay = 1800; }
    else if (deleting && chars === 0) { deleting = false; i = (i + 1) % prompts.length; delay = 350; }
    setTimeout(tick, delay);
  }
  tick();
})();

// Reveal sections as they scroll into view
(function () {
  const items = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window)) {
    items.forEach((el) => el.classList.add("visible"));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  items.forEach((el) => observer.observe(el));
})();

// Copy button on the install commands
document.querySelectorAll(".copy").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(button.dataset.copy);
      button.textContent = "Copied";
    } catch (_) {
      button.textContent = "Select and copy";
    }
    setTimeout(() => (button.textContent = "Copy"), 1600);
  });
});
