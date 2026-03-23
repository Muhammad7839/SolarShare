// Root layout that applies global navigation and footer around all SolarShare pages.
import type { Metadata } from "next";
import "./globals.css";
import { AssistantWidget } from "@/components/AssistantWidget";
import { BackgroundStage } from "@/components/BackgroundStage";
import { PageTransition } from "@/components/PageTransition";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata: Metadata = {
  title: "SolarShare | Utility-Integrated Community Solar Platform",
  description:
    "SolarShare helps households access community solar credits through existing utility billing systems with transparent, source-backed comparisons.",
  icons: {
    icon: "/solarshare-logo-icon.svg"
  }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var mode=localStorage.getItem('solarshare_visual_mode');if(mode==='cinematic'){document.documentElement.classList.add('theme-cinematic');document.documentElement.classList.add('dark');}}catch(e){}})();"
          }}
        />
      </head>
      <body>
        <BackgroundStage />
        <SiteHeader />
        <PageTransition>{children}</PageTransition>
        <SiteFooter />
        <AssistantWidget />
      </body>
    </html>
  );
}
