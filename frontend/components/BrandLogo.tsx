// Brand logo component that applies the official SolarShare logo consistently across the website.
import Image from "next/image";
import Link from "next/link";

interface BrandLogoProps {
  href?: string;
  full?: boolean;
  className?: string;
}

export function BrandLogo({ href = "/", full = false, className = "" }: BrandLogoProps) {
  const src = full ? "/solarshare-logo-full.svg" : "/solarshare-logo-icon.svg";
  const width = full ? 190 : 44;
  const height = full ? 105 : 44;

  return (
    <Link href={href} className={`inline-flex items-center ${className}`}>
      <Image src={src} alt="SolarShare logo" width={width} height={height} priority={full} className="h-auto w-auto" />
    </Link>
  );
}
