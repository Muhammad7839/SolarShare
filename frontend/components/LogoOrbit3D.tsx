// 3D-styled animated SolarShare emblem for hero-level visual identity.
import Image from "next/image";

export function LogoOrbit3D() {
  return (
    <div className="logo-orbit-shell">
      <div className="logo-orbit-ring ring-one" />
      <div className="logo-orbit-ring ring-two" />
      <div className="logo-orbit-ring ring-three" />
      <div className="logo-orbit-core">
        <Image src="/solarshare-logo-icon.svg" alt="SolarShare animated logo" width={110} height={110} />
      </div>
    </div>
  );
}
