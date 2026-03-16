// Global footer with concise company positioning and navigation anchors.
import Link from "next/link";
import { BrandLogo } from "@/components/BrandLogo";

export function SiteFooter() {
  return (
    <footer className="border-t border-solarBlue-100 bg-white/90">
      <div className="mx-auto grid w-full max-w-7xl gap-6 px-5 py-12 md:grid-cols-3">
        <div>
          <BrandLogo full />
          <p className="mt-2 text-sm text-solarBlue-900/70">
            Utility-integrated clean energy access for households, developers, and climate-forward operators.
          </p>
        </div>

        <div>
          <h4 className="text-sm font-bold uppercase tracking-[0.16em] text-solarBlue-900/70">Platform</h4>
          <div className="mt-3 grid gap-2 text-sm text-solarBlue-900/80">
            <Link href="/product">Product</Link>
            <Link href="/technology">Technology</Link>
            <Link href="/pricing">Pricing</Link>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-bold uppercase tracking-[0.16em] text-solarBlue-900/70">Contact</h4>
          <div className="mt-3 grid gap-2 text-sm text-solarBlue-900/80">
            <a href="mailto:hello@solarshare.dev">hello@solarshare.dev</a>
            <a href="mailto:invest@solarshare.dev">invest@solarshare.dev</a>
            <span>© {new Date().getFullYear()} SolarShare</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
