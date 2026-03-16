// SolarShare global site script: transitions, navigation state, and contact form handling.
(function () {
  const PAGE_TRANSITION_MS = 220;
  const VISUAL_MODE_STORAGE_KEY = "solarshare_visual_mode";
  const SESSION_KEY = "solarshare_session_id_v1";
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const visualModeToggles = Array.from(document.querySelectorAll("[data-visual-mode-toggle]"));

  function getSessionId() {
    try {
      const existing = localStorage.getItem(SESSION_KEY);
      if (existing) {
        return existing;
      }
      const created = `sess_${Math.random().toString(36).slice(2, 12)}_${Date.now().toString(36)}`;
      localStorage.setItem(SESSION_KEY, created);
      return created;
    } catch (error) {
      return "anonymous";
    }
  }

  function trackEvent(eventName, metadata) {
    const payload = {
      event_name: eventName,
      page: window.location.pathname,
      session_id: getSessionId(),
      metadata: metadata || {},
    };
    fetch("/analytics/events", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-session-id": payload.session_id,
      },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {
      // Do not interrupt UX for analytics failures.
    });
  }

  function normalizePath(pathname) {
    if (!pathname || pathname === "/") {
      return "/";
    }
    return pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
  }

  function setActiveNavLink() {
    const currentPath = normalizePath(window.location.pathname);
    document.querySelectorAll("[data-route]").forEach((link) => {
      const route = normalizePath(link.getAttribute("data-route") || "");
      if (route === currentPath) {
        link.classList.add("active-nav");
      } else {
        link.classList.remove("active-nav");
      }
    });
  }

  function setCurrentYear() {
    const year = String(new Date().getFullYear());
    document.querySelectorAll("#current-year").forEach((element) => {
      element.textContent = year;
    });
  }

  function readVisualMode() {
    try {
      const raw = localStorage.getItem(VISUAL_MODE_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : "classic";
      return parsed === "cinematic" ? "cinematic" : "classic";
    } catch (error) {
      return "classic";
    }
  }

  function saveVisualMode(mode) {
    try {
      localStorage.setItem(VISUAL_MODE_STORAGE_KEY, JSON.stringify(mode));
    } catch (error) {
      // Ignore storage failures in private/incognito browsers.
    }
  }

  function applyVisualMode(mode, persist) {
    const isCinematic = mode === "cinematic";
    document.documentElement.classList.toggle("theme-cinematic", isCinematic);
    if (document.body) {
      document.body.classList.toggle("theme-cinematic", isCinematic);
    }
    visualModeToggles.forEach((toggle) => {
      toggle.textContent = isCinematic ? "Classic Mode" : "Cinematic Mode";
      toggle.setAttribute("aria-pressed", String(isCinematic));
    });
    if (persist) {
      saveVisualMode(isCinematic ? "cinematic" : "classic");
    }
  }

  function wireVisualModeToggle() {
    if (!visualModeToggles.length) {
      return;
    }
    visualModeToggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const nextMode = document.documentElement.classList.contains("theme-cinematic") ? "classic" : "cinematic";
        applyVisualMode(nextMode, true);
        trackEvent("theme_toggled", { mode: nextMode });
      });
    });
  }

  function isTransitionableLink(anchor, event) {
    if (!(anchor instanceof HTMLAnchorElement)) {
      return false;
    }
    if (anchor.target && anchor.target !== "_self") {
      return false;
    }
    if (anchor.hasAttribute("download")) {
      return false;
    }
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return false;
    }
    const href = anchor.getAttribute("href") || "";
    if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) {
      return false;
    }
    return true;
  }

  function wirePageTransitions() {
    if (prefersReducedMotion) {
      return;
    }

    document.body.classList.add("page-transition-in");
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        document.body.classList.remove("page-transition-in");
      });
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const anchor = target.closest("a[href]");
      if (!isTransitionableLink(anchor, event)) {
        return;
      }

      const destination = new URL(anchor.href, window.location.origin);
      if (destination.origin !== window.location.origin) {
        return;
      }

      const currentPath = normalizePath(window.location.pathname);
      const nextPath = normalizePath(destination.pathname);
      if (currentPath === nextPath && destination.hash) {
        return;
      }

      event.preventDefault();
      document.body.classList.add("page-transition-out");
      window.setTimeout(() => {
        window.location.href = `${destination.pathname}${destination.search}${destination.hash}`;
      }, PAGE_TRANSITION_MS);
    });
  }

  function wireSectionReveal() {
    const targets = Array.from(document.querySelectorAll(".panel, .metrics-strip"));
    if (!targets.length) {
      return;
    }
    targets.forEach((element) => {
      if (!element.classList.contains("reveal")) {
        element.classList.add("reveal");
      }
    });

    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      targets.forEach((element) => element.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14 }
    );
    targets.forEach((element) => observer.observe(element));
  }

  function wireMegaNav() {
    const megaNavs = Array.from(document.querySelectorAll(".mega-nav"));
    if (!megaNavs.length) {
      return;
    }
    document.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      megaNavs.forEach((megaNav) => {
        if (!megaNav.contains(target)) {
          megaNav.removeAttribute("open");
        }
      });
    });
  }

  function setContactStatus(message, isError) {
    const status = document.getElementById("contact-status");
    if (!status) {
      return;
    }
    status.textContent = message;
    status.classList.toggle("error-inline", Boolean(isError));
    status.classList.toggle("success-inline", !isError && Boolean(message));
  }

  async function submitContactInquiry(payload) {
    const response = await fetch("/contact-inquiries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let message = "Unable to submit inquiry right now.";
      try {
        const errorPayload = await response.json();
        if (typeof errorPayload.detail === "string") {
          message = errorPayload.detail;
        }
      } catch (error) {
        // Keep fallback message.
      }
      throw new Error(message);
    }
    return response.json();
  }

  function wireContactForm() {
    const form = document.getElementById("contact-form");
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      setContactStatus("", false);

      const submitButton = form.querySelector("button[type='submit']");
      if (submitButton instanceof HTMLButtonElement) {
        submitButton.disabled = true;
        submitButton.textContent = "Sending...";
      }

      const payload = {
        name: (document.getElementById("contact-name") || {}).value || "",
        email: (document.getElementById("contact-email") || {}).value || "",
        interest: (document.getElementById("contact-interest") || {}).value || "other",
        message: (document.getElementById("contact-message") || {}).value || "",
      };

      try {
        await submitContactInquiry(payload);
        form.reset();
        setContactStatus("Inquiry received. We will follow up shortly.", false);
        trackEvent("contact_submit", { interest: payload.interest });
      } catch (error) {
        setContactStatus(error.message || "Unable to submit inquiry.", true);
        trackEvent("contact_submit_error", {});
      } finally {
        if (submitButton instanceof HTMLButtonElement) {
          submitButton.disabled = false;
          submitButton.textContent = "Submit Inquiry";
        }
      }
    });
  }

  function chatbotResponse(message) {
    const normalized = message.toLowerCase();
    if (normalized.includes("compare") || normalized.includes("run")) {
      return "Start with 'Run Live Comparison'. Enter location or ZIP, monthly usage, and priority. Then review ranked options and savings.";
    }
    if (normalized.includes("cinematic") || normalized.includes("theme") || normalized.includes("light")) {
      return "Use the Cinematic Mode button in the top header. Your preference stays active as you move between pages.";
    }
    if (normalized.includes("zip") || normalized.includes("location") || normalized.includes("city")) {
      return "You can enter city/state, ZIP, or both. ZIP improves precision and the results panel shows resolved city, county, state, and postal details.";
    }
    if (normalized.includes("contact") || normalized.includes("support") || normalized.includes("help")) {
      return "Open the Contact page from the top navigation and send your message. The team receives it directly in the inquiry system.";
    }
    return "I can help with navigation, comparison flow, cinematic mode, and location/ZIP inputs. Ask me what you want to do next.";
  }

  async function requestAssistantReply(message) {
    const sessionId = getSessionId();
    try {
      const response = await fetch("/assistant-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-session-id": sessionId,
        },
        body: JSON.stringify({
          message,
          page: window.location.pathname,
          context: { session_id: sessionId },
        }),
      });
      if (!response.ok) {
        throw new Error("assistant_unavailable");
      }
      const payload = await response.json();
      if (payload && typeof payload.reply === "string" && payload.reply.trim()) {
        return payload.reply.trim();
      }
    } catch (error) {
      // Fallback below.
    }
    return chatbotResponse(message);
  }

  function createChatbotWidget() {
    const shell = document.createElement("aside");
    shell.className = "chatbot-shell";
    shell.innerHTML = `
      <button type="button" class="chatbot-toggle" aria-expanded="false" aria-controls="chatbot-panel">
        Help
      </button>
      <section id="chatbot-panel" class="chatbot-panel" aria-label="SolarShare assistant">
        <header class="chatbot-header">
          <h3>SolarShare Assistant</h3>
          <p>Quick help for navigation and comparison.</p>
        </header>
        <div class="chatbot-messages" id="chatbot-messages" aria-live="polite"></div>
        <div class="chatbot-suggestions">
          <button type="button" data-chatbot-prompt="How do I run a comparison?">Run comparison</button>
          <button type="button" data-chatbot-prompt="How should I enter ZIP and location?">ZIP help</button>
          <button type="button" data-chatbot-prompt="How do I use cinematic mode?">Cinematic mode</button>
          <button type="button" data-chatbot-prompt="How do I contact the team?">Contact team</button>
        </div>
        <form class="chatbot-form" id="chatbot-form">
          <input id="chatbot-input" type="text" maxlength="220" placeholder="Ask a question..." />
          <button type="submit">Send</button>
        </form>
      </section>
    `;
    document.body.appendChild(shell);

    const toggle = shell.querySelector(".chatbot-toggle");
    const panel = shell.querySelector(".chatbot-panel");
    const messages = shell.querySelector("#chatbot-messages");
    const form = shell.querySelector("#chatbot-form");
    const input = shell.querySelector("#chatbot-input");

    function addMessage(role, text) {
      const message = document.createElement("article");
      message.className = `chatbot-message ${role === "user" ? "from-user" : "from-bot"}`;
      message.textContent = text;
      messages.appendChild(message);
      messages.scrollTop = messages.scrollHeight;
    }

    function sendPrompt(prompt) {
      const text = String(prompt || "").trim();
      if (!text) {
        return;
      }
      addMessage("user", text);
      trackEvent("chatbot_message", { length: text.length });
      requestAssistantReply(text).then((reply) => {
        addMessage("bot", reply);
      });
    }

    addMessage("bot", "Hi, I can help you navigate SolarShare.");

    toggle.addEventListener("click", () => {
      const isOpen = panel.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(isOpen));
      if (isOpen) {
        trackEvent("chatbot_open", {});
      }
      if (isOpen && input instanceof HTMLElement) {
        input.focus();
      }
    });

    shell.querySelectorAll("[data-chatbot-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        sendPrompt(button.getAttribute("data-chatbot-prompt") || "");
      });
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      sendPrompt(input.value);
      input.value = "";
    });
  }

  setActiveNavLink();
  setCurrentYear();
  applyVisualMode(readVisualMode(), false);
  wireVisualModeToggle();
  trackEvent("page_view", {});
  wirePageTransitions();
  wireMegaNav();
  wireSectionReveal();
  wireContactForm();
  window.solarshareTrackEvent = trackEvent;
  createChatbotWidget();
})();
