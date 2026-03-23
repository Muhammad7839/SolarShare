// Main site header with startup-style navigation and primary conversion CTA.
"use client";

import { Menu, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/product", label: "Product" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/how-it-works", label: "How It Works" },
  { href: "/technology", label: "Technology" },
  { href: "/pricing", label: "Pricing" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" }
];

export function SiteHeader() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [visualMode, setVisualMode] = useState<"light" | "cinematic">("light");
  const [headerVisible, setHeaderVisible] = useState(true);
  const [headerCompact, setHeaderCompact] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    const storageKey = "solarshare_visual_mode";
    const stored = window.localStorage.getItem(storageKey);
    const nextMode = stored === "cinematic" ? "cinematic" : "light";
    setVisualMode(nextMode);
  }, []);

  useEffect(() => {
    const storageKey = "solarshare_visual_mode";
    window.localStorage.setItem(storageKey, visualMode);
    document.documentElement.classList.toggle("theme-cinematic", visualMode === "cinematic");
    document.documentElement.classList.toggle("dark", visualMode === "cinematic");
  }, [visualMode]);

  useEffect(() => {
    let previousScroll = window.scrollY;
    const handleScroll = () => {
      const currentScroll = window.scrollY;
      const nearTop = currentScroll < 48;
      const scrollingUp = currentScroll < previousScroll - 6;
      const scrollingDown = currentScroll > previousScroll + 8;
      setHeaderCompact(currentScroll > 20);
      if (scrollingDown && currentScroll > 84 && !mobileOpen) {
        setHeaderVisible(false);
      } else if (nearTop || scrollingUp || mobileOpen) {
        setHeaderVisible(true);
      }
      previousScroll = currentScroll;
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [mobileOpen]);

  return (
    <header
      className={`site-header-shell sticky top-0 z-50 border-b border-solarBlue-100/80 bg-white/75 backdrop-blur-xl transition-transform duration-300 ${
        headerVisible ? "translate-y-0" : "-translate-y-full"
      }`}
    >
      <div
        className={`mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-5 transition-all duration-200 ${
          headerCompact ? "py-1.5" : "py-2.5"
        }`}
      >
        <Link href="/" className="inline-flex items-center gap-2">
          <Image
            src="/solarshare-logo-icon.svg"
            alt="SolarShare logo"
            width={40}
            height={40}
            priority
            className={`transition-all duration-200 ${headerCompact ? "size-8" : "size-10"}`}
          />
          <span className={`font-semibold tracking-tight text-solarBlue-900 transition-all duration-200 ${headerCompact ? "text-sm" : "text-base"}`}>
            SolarShare
          </span>
        </Link>

        <nav className="hidden items-center gap-5 lg:flex">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`text-sm font-semibold transition ${
                  active ? "text-solarBlue-700" : "text-solarBlue-900/70 hover:text-solarBlue-700"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          <button
            type="button"
            onClick={() => setVisualMode((prev) => (prev === "cinematic" ? "light" : "cinematic"))}
            className="rounded-full border border-solarBlue-200 bg-white px-4 py-2 text-sm font-semibold text-solarBlue-700 shadow-card transition hover:bg-solarBlue-50"
          >
            {visualMode === "cinematic" ? "Light Mode" : "Cinematic Mode"}
          </button>
          <Link
            href="/product"
            className="rounded-full bg-solarBlue-700 px-4 py-2 text-sm font-semibold text-white shadow-card transition hover:bg-solarBlue-900"
          >
            Start Comparison
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen((previous) => !previous)}
          className="inline-flex items-center justify-center rounded-xl border border-solarBlue-200 bg-white p-2 text-solarBlue-700 lg:hidden"
          aria-expanded={mobileOpen}
          aria-controls="mobile-site-nav"
          aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
        >
          {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      <div
        id="mobile-site-nav"
        className={`mx-auto w-full max-w-7xl px-5 pb-4 transition-all duration-300 lg:hidden ${
          mobileOpen ? "pointer-events-auto max-h-[420px] opacity-100" : "pointer-events-none max-h-0 opacity-0"
        }`}
      >
        <nav className="grid gap-2 rounded-2xl border border-solarBlue-100 bg-white/95 p-3 shadow-card">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
                  active ? "bg-solarBlue-50 text-solarBlue-700" : "text-solarBlue-900/75 hover:bg-solarBlue-50 hover:text-solarBlue-700"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
          <Link
            href="/product"
            className="mt-1 inline-flex justify-center rounded-xl bg-solarBlue-700 px-4 py-2 text-sm font-semibold text-white shadow-card transition hover:bg-solarBlue-900"
          >
            Start Comparison
          </Link>
          <button
            type="button"
            onClick={() => setVisualMode((prev) => (prev === "cinematic" ? "light" : "cinematic"))}
            className="inline-flex justify-center rounded-xl border border-solarBlue-200 bg-white px-4 py-2 text-sm font-semibold text-solarBlue-700 shadow-card transition hover:bg-solarBlue-50"
          >
            {visualMode === "cinematic" ? "Light Mode" : "Cinematic Mode"}
          </button>
        </nav>
      </div>
    </header>
  );
}
