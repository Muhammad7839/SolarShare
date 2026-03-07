// src/App.jsx
import { useEffect, useMemo, useState } from "react";
import {
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import {
  checkEligibility,
  enroll,
  estimate,
  getEnrollment,
  getProjects,
} from "./api";
import {
  CheckCircle2,
  Download,
  ExternalLink,
  FileCheck,
  MapPin,
  Sun,
  Zap,
} from "lucide-react";
import "./App.css";

const BRAND = {
  name: "SolarShare",
  territory: "PSEG Long Island",
};

const TRUST_MESSAGE =
  "No roof change. No wires change. You stay with PSEG. You receive solar credits on your PSEG bill.";

const NO_SUBSCRIPTION_MESSAGE =
  "No subscription required. Savings are built into your community solar credit discount. You stay with PSEG Long Island — only your bill changes via credits. Cancel enrollment anytime.";

// Demo fallback data (used only if backend projects fail)
const DEMO_PROJECTS = [
  {
    id: "northport-sun-01",
    name: "Northport Community Solar",
    town: "Northport, NY",
    creditRate: 0.16,
    payPct: 0.9,
    savingsLow: 12,
    savingsHigh: 35,
    status: "Open",
    description:
      "A local community solar farm that applies credits to your PSEG bill. No panels. No wiring. No roof work.",
  },
  {
    id: "huntington-green-02",
    name: "Huntington Green Credits",
    town: "Huntington, NY",
    creditRate: 0.17,
    payPct: 0.9,
    savingsLow: 15,
    savingsHigh: 42,
    status: "Limited",
    description:
      "Limited spots available. Enroll digitally and start seeing credits within 1 to 2 billing cycles.",
  },
  {
    id: "babylon-solar-03",
    name: "Babylon Solar Collective",
    town: "Babylon, NY",
    creditRate: 0.155,
    payPct: 0.9,
    savingsLow: 10,
    savingsHigh: 30,
    status: "Open",
    description:
      "Simple enrollment. Cancel enrollment anytime. Your utility service stays the same.",
  },
];

const STORAGE = {
  zip: "solarshare_zip",
  territoryId: "solarshare_territory_id",
  projectId: "solarshare_project_id",
  enrollmentId: "solarshare_enrollment_id",
};

function saveStr(key, value) {
  try {
    if (value == null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, String(value));
  } catch {
    // ignore
  }
}
function readStr(key) {
  try {
    return sessionStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function money(n) {
  const num = Number(n);
  if (!Number.isFinite(num)) return "$0";
  return num.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function pct(n) {
  const num = Number(n);
  if (!Number.isFinite(num)) return "0%";
  return `${Math.round(num * 100)}%`;
}

function perKwh(n) {
  const num = Number(n);
  if (!Number.isFinite(num)) return "$0.000/kWh";
  return `$${num.toFixed(3)}/kWh`;
}

/* side effect: scroll to top when route changes */
function useHashlessScrollTopOnRouteChange() {
  const loc = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [loc.pathname, loc.search]);
}

function PrimaryButton({ children, className = "", ...props }) {
  return (
    <button className={`btn btnPrimary ${className}`} {...props}>
      {children}
    </button>
  );
}

function SecondaryButton({ children, className = "", ...props }) {
  return (
    <button className={`btn btnSecondary ${className}`} {...props}>
      {children}
    </button>
  );
}

function Pill({ icon, children }) {
  return (
    <div className="trustPill">
      <span className="pillIcon" aria-hidden="true">
        {icon}
      </span>
      <span className="pillText">{children}</span>
    </div>
  );
}

function Badge({ children, tone = "neutral" }) {
  const cls =
    tone === "good"
      ? "badge badgeGood"
      : tone === "warn"
      ? "badge badgeWarn"
      : "badge badgeNeutral";
  return <span className={cls}>{children}</span>;
}

function Card({ children, className = "" }) {
  return <div className={`card ${className}`}>{children}</div>;
}

function Section({ title, subtitle, children }) {
  return (
    <section className="section">
      <div className="sectionHead">
        <h2 className="sectionTitle">{title}</h2>
        {subtitle ? <p className="sectionSubtitle">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}

function Layout({ children }) {
  useHashlessScrollTopOnRouteChange();
  const navigate = useNavigate();

  function goHome() {
    navigate("/");
  }

  function onBrandKeyDown(e) {
    if (e.key === "Enter" || e.key === " ") goHome();
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbarInner">
          <div
            className="brandLockup"
            role="banner"
            onClick={goHome}
            onKeyDown={onBrandKeyDown}
            tabIndex={0}
          >
            <img
              className="brandLogo"
              src="/logo.png"
              alt={`${BRAND.name} logo`}
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
            <div className="brandMarkFallback" aria-hidden="true" />
            <div className="brandText">{BRAND.name}</div>
          </div>

          <nav className="nav" aria-label="Primary">
            <NavLink
              to="/"
              className={({ isActive }) =>
                isActive ? "navLink navLinkActive" : "navLink"
              }
            >
              Home
            </NavLink>
            <NavLink
              to="/how-it-works"
              className={({ isActive }) =>
                isActive ? "navLink navLinkActive" : "navLink"
              }
            >
              How it works
            </NavLink>
            <NavLink
              to="/projects"
              className={({ isActive }) =>
                isActive ? "navLink navLinkActive" : "navLink"
              }
            >
              Projects
            </NavLink>
            <NavLink
              to="/faq"
              className={({ isActive }) =>
                isActive ? "navLink navLinkActive" : "navLink"
              }
            >
              FAQ
            </NavLink>
            <NavLink
              to="/pricing"
              className={({ isActive }) =>
                isActive ? "navLink navLinkActive" : "navLink"
              }
            >
              Cost and savings
            </NavLink>
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                isActive ? "navLink navLinkActive" : "navLink"
              }
            >
              Dashboard
            </NavLink>
          </nav>

          <div className="topbarCta">
            <PrimaryButton onClick={() => navigate("/eligibility")}>
              Check eligibility
            </PrimaryButton>
          </div>
        </div>
      </header>

      <main className="container">{children}</main>

      <SiteFooter />
    </div>
  );
}

function SiteFooter() {
  const year = new Date().getFullYear();
  const repoUrl = "https://github.com/your-username/solarshare";

  return (
    <footer className="footer">
      <div className="footerInner">
        <div className="footerLeft">
          <div className="footerBrand">{BRAND.name}</div>
          <div className="footerMeta">{TRUST_MESSAGE}</div>
          <div className="footerMeta">{NO_SUBSCRIPTION_MESSAGE}</div>
          <div className="footerMeta">
            Prototype simulates enrollment and credit allocation. No real utility
            integration in demo.
          </div>
          <div className="footerMeta">© {year} Educational project</div>
        </div>

        <div className="footerRight">
          <a
            className="footerLink"
            href={repoUrl}
            target="_blank"
            rel="noreferrer"
          >
            GitHub repo
          </a>
          <span className="footerMeta">Estimates may vary by provider terms</span>
        </div>
      </div>
    </footer>
  );
}

function Home() {
  const navigate = useNavigate();

  return (
    <>
      <div className="hero heroPro">
        <div className="heroPhoto" aria-hidden="true" />
        <div className="heroBg" aria-hidden="true" />

        <div className="heroInner heroGrid">
          <div className="heroLeft">
            <div className="heroKicker">Community solar for Long Island</div>

            <h1 className="heroTitle">Get solar savings without installing panels</h1>

            <p className="heroSubtitle">
              Enroll in community solar and receive credits on your PSEG Long Island
              bill. No equipment. No roof work. Cancel enrollment anytime. No
              subscription required.
            </p>

            <div className="heroActions">
              <PrimaryButton onClick={() => navigate("/eligibility")}>
                Check eligibility
              </PrimaryButton>
              <SecondaryButton onClick={() => navigate("/how-it-works")}>
                See how it works
              </SecondaryButton>
            </div>

            <div className="trustRow" aria-label="Trust">
              <Pill icon={<Sun size={16} />}>No equipment</Pill>
              <Pill icon={<CheckCircle2 size={16} />}>No roof changes</Pill>
              <Pill icon={<FileCheck size={16} />}>Cancel enrollment anytime</Pill>
              <Pill icon={<Zap size={16} />}>Utility compliant</Pill>
            </div>

            <div className="proofRow">
              <div className="proofItem">
                <div className="proofBig">1–2</div>
                <div className="proofSmall">billing cycles to see credits</div>
              </div>
              <div className="proofItem">
                <div className="proofBig">10–40%</div>
                <div className="proofSmall">typical estimated savings range</div>
              </div>
              <div className="proofItem">
                <div className="proofBig">0</div>
                <div className="proofSmall">equipment installs</div>
              </div>
            </div>

            <div className="downloadRow" aria-label="Downloads">
              <a className="dlLink" href="/SolarShare-Guide.pdf">
                <Download size={18} />
                Download guide
              </a>
              <a className="dlLink" href="/CommunitySolar-FAQ.pdf">
                <Download size={18} />
                Download FAQ
              </a>
            </div>
          </div>

          <div className="heroRight" aria-label="SolarShare preview">
            <div className="deviceCard">
              <div className="deviceTop">
                <div className="dot" />
                <div className="dot" />
                <div className="dot" />
                <div className="deviceTitle">SolarShare Credits Preview</div>
              </div>

              <div className="deviceBody">
                <div className="billRow">
                  <div className="billLabel">PSEG Bill</div>
                  <div className="billValue">$182.40</div>
                </div>

                <div className="billRow">
                  <div className="billLabel">Solar credits</div>
                  <div className="billValue billGreen">- $26.10</div>
                </div>

                <div className="divider" />

                <div className="billRow">
                  <div className="billLabel">You pay</div>
                  <div className="billValue billStrong">$156.30</div>
                </div>

                <div className="miniNote">
                  You stay with PSEG Long Island. Only the bill changes via credits.
                  No subscription required.
                </div>

                <div className="miniCTA">
                  <button
                    className="miniBtn"
                    type="button"
                    onClick={() => navigate("/projects")}
                  >
                    View projects
                  </button>
                  <button
                    className="miniBtnOutline"
                    type="button"
                    onClick={() => navigate("/credit-explanation")}
                  >
                    Learn credits
                  </button>
                </div>
              </div>
            </div>

            <div className="floatingBadge">
              <Sun size={16} />
              Built for {BRAND.territory}
            </div>
          </div>
        </div>
      </div>

      <Card className="wideCard">
        <div className="featureStrip">
          <div className="featureItem">
            <span className="featureIcon" aria-hidden="true">
              <CheckCircle2 size={18} />
            </span>
            <div>
              <div className="featureTitle">Utility stays the same</div>
              <div className="featureText">PSEG still delivers power and bills you.</div>
            </div>
          </div>

          <div className="featureItem">
            <span className="featureIcon" aria-hidden="true">
              <Sun size={18} />
            </span>
            <div>
              <div className="featureTitle">Credits reduce your bill</div>
              <div className="featureText">Solar credits appear automatically.</div>
            </div>
          </div>

          <div className="featureItem">
            <span className="featureIcon" aria-hidden="true">
              <Zap size={18} />
            </span>
            <div>
              <div className="featureTitle">No subscription required</div>
              <div className="featureText">Savings are built into the credit discount.</div>
            </div>
          </div>
        </div>
      </Card>

      <Section
        title="How it works"
        subtitle="Four simple steps to start saving with community solar"
      >
        <div className="stepsGrid">
          <StepCard
            num="1"
            icon={<MapPin size={22} />}
            title="Check eligibility"
            text="Enter your ZIP code to confirm you are in PSEG Long Island territory."
          />
          <StepCard
            num="2"
            icon={<Sun size={22} />}
            title="Choose a solar project"
            text="Select from local community solar farms in your area."
          />
          <StepCard
            num="3"
            icon={<FileCheck size={22} />}
            title="Enroll digitally"
            text="Complete enrollment in minutes with no equipment installation."
          />
          <StepCard
            num="4"
            icon={<Zap size={22} />}
            title="Start saving"
            text="Receive solar credits on your PSEG bill within 1 to 2 billing cycles."
          />
        </div>

        <div className="centerRow">
          <SecondaryButton onClick={() => navigate("/credit-explanation")}>
            View bill credit breakdown
          </SecondaryButton>
        </div>
      </Section>

      <Section
        title="Frequently asked questions"
        subtitle="Everything you need to know about community solar"
      >
        <div className="faqPreviewGrid">
          <MiniFaq
            q="Do I switch utilities?"
            a="No. PSEG still delivers electricity and sends your bill."
          />
          <MiniFaq q="Do I install equipment?" a="No panels, no wiring, no roof work." />
          <MiniFaq
            q="Where do credits show up?"
            a="On your PSEG bill as a line item credit that reduces what you owe."
          />
          <MiniFaq q="Can I cancel?" a="Yes. Cancel enrollment anytime." />
        </div>

        <div className="centerRow">
          <SecondaryButton onClick={() => navigate("/faq")}>See all FAQs</SecondaryButton>
        </div>
      </Section>

      <CallToAction />
    </>
  );
}

function StepCard({ num, icon, title, text }) {
  return (
    <Card className="stepCard">
      <div className="stepNum">{num}</div>
      <div className="stepIcon" aria-hidden="true">
        {icon}
      </div>
      <div className="stepTitle">{title}</div>
      <div className="stepText">{text}</div>
    </Card>
  );
}

function MiniFaq({ q, a }) {
  return (
    <Card className="miniFaq">
      <div className="miniFaqQ">{q}</div>
      <div className="miniFaqA">{a}</div>
    </Card>
  );
}

function CallToAction() {
  const navigate = useNavigate();
  return (
    <section className="ctaBand">
      <div className="ctaInner">
        <div className="ctaTitle">Ready to start saving?</div>
        <div className="ctaText">
          Verify your territory and see available projects. Takes less than 30 seconds.
        </div>
        <div className="ctaActions">
          <button className="ctaBtn" onClick={() => navigate("/eligibility")}>
            Check eligibility now
          </button>
        </div>
      </div>
    </section>
  );
}

/* Eligibility page (backend wired) */
function Eligibility() {
  const navigate = useNavigate();

  const [zip, setZip] = useState("");
  const [whyOpen, setWhyOpen] = useState(false);
  const [error, setError] = useState("");

  const [loading, setLoading] = useState(false);
  const [notEligible, setNotEligible] = useState(false);
  const [waitlistEmail, setWaitlistEmail] = useState("");
  const [waitlistJoined, setWaitlistJoined] = useState(false);

  async function verify() {
    const z = zip.trim();

    setError("");
    setNotEligible(false);
    setWaitlistJoined(false);

    if (!/^\d{5}$/.test(z)) {
      setError("Please enter a 5 digit ZIP code.");
      return;
    }

    setLoading(true);
    try {
      const res = await checkEligibility({ zip: z });

      if (res?.eligible) {
        const territoryId = res.territory_id || "";
        saveStr(STORAGE.zip, z);
        saveStr(STORAGE.territoryId, territoryId);

        navigate(
          `/eligibility/result?zip=${encodeURIComponent(
            z
          )}&territory_id=${encodeURIComponent(territoryId)}`
        );
      } else {
        setNotEligible(true);
      }
    } catch (e) {
      setError(e?.message || "Could not verify eligibility.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="eligibilityWrap">
      <div className="eligibilityHero">
        <div className="eligibilityHeroInner">
          <h1 className="eligibilityTitle">Check eligibility in seconds</h1>
          <p className="eligibilitySubtitle">
            Verify you are in {BRAND.territory} so credits apply correctly.
          </p>

          <div className="eligibilityCard">
            {error ? (
              <div className="errorCard">
                <div className="errorTitle">Action needed</div>
                <div className="errorBody">{error}</div>
              </div>
            ) : null}

            {notEligible ? (
              <>
                <div className="resultRow" style={{ marginBottom: 12 }}>
                  <div className="resultIconNeutral" aria-hidden="true" />
                  <div>
                    <div className="resultTitle">Not supported yet</div>
                    <div className="resultBody">
                      Join the waitlist and we will notify you when your area is available.
                    </div>
                  </div>
                </div>

                <div className="waitlistRow">
                  <input
                    className="input"
                    value={waitlistEmail}
                    onChange={(e) => setWaitlistEmail(e.target.value)}
                    placeholder="Email address"
                  />
                  <PrimaryButton
                    onClick={() => {
                      if (!waitlistEmail.trim()) return;
                      setWaitlistJoined(true);
                    }}
                  >
                    Join waitlist
                  </PrimaryButton>
                </div>

                {waitlistJoined ? (
                  <div className="helperBox">You are on the list. Thank you.</div>
                ) : null}

                <div className="eligibilityHelper">{NO_SUBSCRIPTION_MESSAGE}</div>
              </>
            ) : (
              <div className="zipBlock">
                <label className="label" htmlFor="zip">
                  ZIP code
                </label>

                <div className="zipRow">
                  <input
                    id="zip"
                    className="input zipInput"
                    inputMode="numeric"
                    autoComplete="postal-code"
                    value={zip}
                    onChange={(e) => {
                      const next = e.target.value.replace(/[^\d]/g, "").slice(0, 5);
                      setZip(next);
                      if (error) setError("");
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !loading) verify();
                    }}
                    placeholder="e.g. 11743"
                    disabled={loading}
                  />

                  <PrimaryButton onClick={verify} className="zipBtn" disabled={loading}>
                    <ExternalLink size={18} style={{ marginRight: 8 }} />
                    {loading ? "Verifying..." : "Verify PSEG territory"}
                  </PrimaryButton>
                </div>

                <button
                  className="whyLink"
                  type="button"
                  onClick={() => setWhyOpen((v) => !v)}
                  aria-expanded={whyOpen}
                >
                  Why do we ask for ZIP?
                </button>

                {whyOpen ? (
                  <div className="helperBox">
                    We use your ZIP code only to confirm you are in the {BRAND.territory} service
                    area, so we show options that apply credits correctly. No subscription required.
                  </div>
                ) : null}

                <div className="eligibilityHelper">{NO_SUBSCRIPTION_MESSAGE}</div>
              </div>
            )}
          </div>

          <div className="eligibilityTrustRow" aria-label="Trust">
            <Pill icon={<Sun size={16} />}>No equipment</Pill>
            <Pill icon={<CheckCircle2 size={16} />}>No roof changes</Pill>
            <Pill icon={<FileCheck size={16} />}>Cancel enrollment anytime</Pill>
            <Pill icon={<Zap size={16} />}>Utility compliant</Pill>
          </div>
        </div>
      </div>
    </div>
  );
}

function EligibilityResult() {
  const navigate = useNavigate();
  const loc = useLocation();
  const params = new URLSearchParams(loc.search);

  const zip = params.get("zip") || "";
  const territoryId = params.get("territory_id") || "";
  const eligible = Boolean(territoryId);

  useEffect(() => {
    if (zip) saveStr(STORAGE.zip, zip);
    if (territoryId) saveStr(STORAGE.territoryId, territoryId);
  }, [zip, territoryId]);

  const [email, setEmail] = useState("");
  const [joined, setJoined] = useState(false);

  return (
    <Section title="Eligibility result" subtitle={`ZIP checked: ${zip || "unknown"}`}>
      <Card>
        {eligible ? (
          <>
            <div className="resultRow">
              <div className="resultIconGood" aria-hidden="true" />
              <div>
                <div className="resultTitle">Verified territory: {BRAND.territory}</div>
                <div className="resultBody">
                  Credits apply correctly in this territory. No subscription required. Next, view
                  available community solar projects.
                </div>
              </div>
            </div>

            <div className="rowActions">
              <PrimaryButton onClick={() => navigate("/projects")}>
                View available projects
              </PrimaryButton>
              <SecondaryButton onClick={() => navigate("/credit-explanation")}>
                View bill credit breakdown
              </SecondaryButton>
            </div>
          </>
        ) : (
          <>
            <div className="resultRow">
              <div className="resultIconNeutral" aria-hidden="true" />
              <div>
                <div className="resultTitle">Not supported yet</div>
                <div className="resultBody">
                  Join the waitlist and we will notify you when your area is available.
                </div>
              </div>
            </div>

            <div className="waitlistRow">
              <input
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
              />
              <PrimaryButton
                onClick={() => {
                  if (!email.trim()) return;
                  setJoined(true);
                }}
              >
                Join waitlist
              </PrimaryButton>
            </div>

            {joined ? <div className="helperBox">You are on the list. Thank you.</div> : null}
          </>
        )}

        <div className="helperText">{NO_SUBSCRIPTION_MESSAGE}</div>
      </Card>
    </Section>
  );
}

function normalizeProject(p) {
  if (!p || typeof p !== "object") return null;

  const id = p.id ?? p.project_id ?? p.slug ?? "";
  const name = p.name ?? p.project_name ?? "Community Solar Project";
  const town = p.town ?? p.location ?? p.city ?? "";
  const creditRate = p.creditRate ?? p.credit_rate ?? p.credit_rate_per_kwh ?? p.rate ?? null;
  const payPct = p.payPct ?? p.pay_pct ?? p.subscriber_pay_pct ?? null;
  const savingsLow = p.savingsLow ?? p.savings_low ?? p.savings_min ?? null;
  const savingsHigh = p.savingsHigh ?? p.savings_high ?? p.savings_max ?? null;
  const status = p.status ?? p.availability ?? "Open";
  const description = p.description ?? p.summary ?? "";

  return {
    id: String(id),
    name: String(name),
    town: String(town),
    creditRate: creditRate == null ? 0 : Number(creditRate),
    payPct: payPct == null ? 0.9 : Number(payPct),
    savingsLow: savingsLow == null ? 0 : Number(savingsLow),
    savingsHigh: savingsHigh == null ? 0 : Number(savingsHigh),
    status: String(status),
    description: String(description),
    raw: p,
  };
}

function Projects() {
  const navigate = useNavigate();

  const [projects, setProjects] = useState(DEMO_PROJECTS);
  const [loading, setLoading] = useState(false);
  const [note, setNote] = useState("");

  useEffect(() => {
    const territoryId = readStr(STORAGE.territoryId);
    if (!territoryId) {
      setNote("Tip: run eligibility first to load territory-based projects.");
      setProjects(DEMO_PROJECTS);
      return;
    }

    let alive = true;
    setLoading(true);
    setNote("");

    getProjects({ territory_id: territoryId })
      .then((data) => {
        if (!alive) return;

        const arr = Array.isArray(data) ? data : data?.projects;
        if (Array.isArray(arr) && arr.length > 0) {
          const mapped = arr.map(normalizeProject).filter(Boolean);
          setProjects(mapped.length ? mapped : DEMO_PROJECTS);
          if (!mapped.length) setNote("Using demo projects (backend returned unknown shape).");
        } else {
          setProjects(DEMO_PROJECTS);
          setNote("Using demo projects (no backend projects found for this territory).");
        }
      })
      .catch(() => {
        if (!alive) return;
        setProjects(DEMO_PROJECTS);
        setNote("Using demo projects (backend projects request failed).");
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, []);

  return (
    <Section
      title="Available community solar projects"
      subtitle="Choose a project. Enroll digitally. Cancel enrollment anytime. No subscription required."
    >
      {note ? <div className="helperBox" style={{ marginBottom: 12 }}>{note}</div> : null}
      {loading ? <div className="helperText">Loading projects...</div> : null}

      <div className="projectsGrid">
        {projects.map((p) => {
          const tone = p.status === "Limited" ? "warn" : "good";
          return (
            <Card key={p.id} className="projectCard">
              <div className="projectTop">
                <div>
                  <div className="projectName">{p.name}</div>
                  <div className="projectTown">{p.town}</div>
                </div>
                <Badge tone={tone}>
                  {p.status === "Limited" ? "Limited spots" : "Open"}
                </Badge>
              </div>

              <div className="projectStats">
                <div className="stat">
                  <div className="statLabel">Credit rate</div>
                  <div className="statValue">{perKwh(p.creditRate)} credit</div>
                </div>
                <div className="stat">
                  <div className="statLabel">Subscriber pays</div>
                  <div className="statValue">Pay about {pct(p.payPct)} of credit value</div>
                </div>
                <div className="stat">
                  <div className="statLabel">Estimated monthly savings</div>
                  <div className="statValue">
                    {money(p.savingsLow)} to {money(p.savingsHigh)}
                  </div>
                </div>
              </div>

              <div className="rowActions">
                <SecondaryButton onClick={() => navigate(`/projects/${p.id}`)}>
                  View details
                </SecondaryButton>
                <PrimaryButton onClick={() => navigate(`/projects/${p.id}?select=1`)}>
                  Choose this project
                </PrimaryButton>
              </div>

              <div className="helperText">{TRUST_MESSAGE}</div>
            </Card>
          );
        })}
      </div>
    </Section>
  );
}

function ProjectDetail() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const loc = useLocation();
  const selected = new URLSearchParams(loc.search).get("select") === "1";

  const [projects, setProjects] = useState(DEMO_PROJECTS);
  const [usage, setUsage] = useState(650);
  const [bill, setBill] = useState("");
  const [apiEstimate, setApiEstimate] = useState(null);
  const [estLoading, setEstLoading] = useState(false);

  useEffect(() => {
    const territoryId = readStr(STORAGE.territoryId);
    if (!territoryId) return;

    let alive = true;
    getProjects({ territory_id: territoryId })
      .then((data) => {
        if (!alive) return;
        const arr = Array.isArray(data) ? data : data?.projects;
        if (Array.isArray(arr) && arr.length) {
          const mapped = arr.map(normalizeProject).filter(Boolean);
          if (mapped.length) setProjects(mapped);
        }
      })
      .catch(() => {})
      .finally(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const project = projects.find((p) => String(p.id) === String(projectId));

  useEffect(() => {
    if (!project) return;

    const zip = readStr(STORAGE.zip);
    if (!zip) return;

    let alive = true;
    setEstLoading(true);

    estimate({
      zip,
      monthly_usage_kwh: Number(usage) || 0,
      project_id: project.id,
    })
      .then((data) => {
        if (!alive) return;
        setApiEstimate(data);
      })
      .catch(() => {
        if (!alive) return;
        setApiEstimate(null);
      })
      .finally(() => {
        if (!alive) return;
        setEstLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [project?.id, usage]);

  const localEstimate = useMemo(() => {
    if (!project) return { month: 0, year: 0, percent: null };

    const kwh = Number(usage);
    const creditValue = kwh * project.creditRate;
    const subscriberPays = creditValue * project.payPct;
    const savings = Math.max(creditValue - subscriberPays, 0);

    const billNum = Number(bill);
    const percent =
      Number.isFinite(billNum) && billNum > 0
        ? Math.min(savings / billNum, 1)
        : null;

    return { month: savings, year: savings * 12, percent };
  }, [usage, bill, project]);

  const displayMonth =
    Number(apiEstimate?.monthly_savings ?? apiEstimate?.month ?? apiEstimate?.savings_month) ||
    localEstimate.month;

  const displayYear =
    Number(apiEstimate?.yearly_savings ?? apiEstimate?.year ?? apiEstimate?.savings_year) ||
    localEstimate.year;

  if (!project) {
    return (
      <Section title="Project not found" subtitle="Please go back to projects.">
        <Card>
          <SecondaryButton onClick={() => navigate("/projects")}>
            Back to projects
          </SecondaryButton>
        </Card>
      </Section>
    );
  }

  return (
    <Section title={project.name} subtitle={project.town}>
      <div className="rowActions" style={{ marginTop: 0, marginBottom: 12 }}>
        <SecondaryButton onClick={() => navigate("/projects")}>
          Back to projects
        </SecondaryButton>
        {selected ? (
          <div className="helperBox" style={{ marginTop: 0 }}>
            This project is selected. Next step is enrollment.
          </div>
        ) : null}
      </div>

      <Card>
        <div className="detailGrid">
          <div>
            <div className="detailLabel">Summary</div>
            <div className="detailText">{project.description}</div>

            <div className="detailBullets">
              <div className="bullet">You stay with PSEG. They still deliver power.</div>
              <div className="bullet">No panels. No wiring. No roof work.</div>
              <div className="bullet">
                No subscription required. Savings are built into the credit discount.
              </div>
              <div className="bullet">Credits typically show in 1 to 2 billing cycles.</div>
            </div>

            <div className="detailActions">
              <PrimaryButton
                onClick={() => {
                  saveStr(STORAGE.projectId, project.id);
                  navigate("/enrollment");
                }}
              >
                Enroll in 3 minutes
              </PrimaryButton>
              <SecondaryButton onClick={() => navigate("/credit-explanation")}>
                View bill credit breakdown
              </SecondaryButton>
            </div>

            <div className="helperText">{TRUST_MESSAGE}</div>
          </div>

          <div>
            <div className="calcCard">
              <div className="calcTitle">Savings estimate</div>

              <div className="formRow">
                <label className="label">Monthly usage (kWh)</label>
                <input
                  className="range"
                  type="range"
                  min="200"
                  max="1400"
                  step="25"
                  value={usage}
                  onChange={(e) => setUsage(Number(e.target.value))}
                />
                <div className="rangeMeta">{usage} kWh</div>
              </div>

              <div className="formRow">
                <label className="label">Bill amount (optional)</label>
                <input
                  className="input"
                  value={bill}
                  onChange={(e) => {
                    const next = e.target.value.replace(/[^\d.]/g, "");
                    setBill(next);
                  }}
                  placeholder="e.g. 180"
                  inputMode="decimal"
                />
                <div className="helperText">
                  Optional. If you enter a bill amount, we can show a rough percent saved.
                </div>
              </div>

              <div className="calcResult">
                <div className="calcBig">
                  Estimated savings: {money(displayMonth)} per month
                </div>
                <div className="calcSmall">{money(displayYear)} per year</div>
                {estLoading ? <div className="calcSmall">Updating estimate...</div> : null}
              </div>

              <div className="rowActions">
                <PrimaryButton
                  onClick={() => {
                    saveStr(STORAGE.projectId, project.id);
                    navigate("/enrollment");
                  }}
                >
                  Continue to enrollment
                </PrimaryButton>
              </div>

              <div className="helperText">{NO_SUBSCRIPTION_MESSAGE}</div>
            </div>
          </div>
        </div>
      </Card>
    </Section>
  );
}

function CreditExplanation() {
  const navigate = useNavigate();
  return (
    <Section
      title="How you save with solar credits"
      subtitle="A simple explanation of what changes and what stays the same."
    >
      <Card>
        <div className="diagram">
          <div className="node">Solar farm</div>
          <div className="arrow" aria-hidden="true" />
          <div className="node">Grid</div>
          <div className="arrow" aria-hidden="true" />
          <div className="node">PSEG measures</div>
          <div className="arrow" aria-hidden="true" />
          <div className="node">SolarShare allocates credits</div>
          <div className="arrow" aria-hidden="true" />
          <div className="node">Your PSEG bill is reduced</div>
        </div>

        <div className="callouts">
          <div className="callout">
            <div className="calloutTitle">You still receive electricity from PSEG</div>
            <div className="calloutBody">
              You do not switch utilities. Only the bill changes via credits.
            </div>
          </div>

          <div className="callout">
            <div className="calloutTitle">No subscription required</div>
            <div className="calloutBody">
              Savings are built into your community solar credit discount.
            </div>
          </div>

          <div className="callout">
            <div className="calloutTitle">Credits appear in 1 to 2 billing cycles</div>
            <div className="calloutBody">
              Timing varies slightly, but most customers see credits quickly.
            </div>
          </div>
        </div>

        <div className="rowActions">
          <PrimaryButton onClick={() => navigate("/eligibility")}>Continue</PrimaryButton>
          <SecondaryButton onClick={() => navigate("/projects")}>Browse projects</SecondaryButton>
        </div>

        <div className="helperText">{TRUST_MESSAGE}</div>
      </Card>
    </Section>
  );
}

function HowItWorksPage() {
  const navigate = useNavigate();
  return (
    <Section title="How it works" subtitle="Clear steps from ZIP check to monthly savings.">
      <Card>
        <div className="timeline">
          <TimelineItem
            title="Enter ZIP and confirm territory"
            text="We confirm you are in PSEG Long Island so credits apply correctly."
          />
          <TimelineItem
            title="Choose a local community solar project"
            text="Pick a project with open spots or limited spots."
          />
          <TimelineItem
            title="Enroll digitally in about 3 minutes"
            text="A lightweight form. No roof changes. No wiring. No utility switching."
          />
          <TimelineItem
            title="Solar produces and PSEG applies credits"
            text="SolarShare allocates credits and they appear on your PSEG bill."
          />
          <TimelineItem
            title="You see savings monthly"
            text="Savings are built into the credit discount. Cancel enrollment anytime."
          />
        </div>

        <div className="rowActions">
          <PrimaryButton onClick={() => navigate("/eligibility")}>
            Start eligibility check
          </PrimaryButton>
        </div>

        <div className="helperText">{NO_SUBSCRIPTION_MESSAGE}</div>
      </Card>
    </Section>
  );
}

function TimelineItem({ title, text }) {
  return (
    <div className="timelineItem">
      <div className="timelineDot" aria-hidden="true" />
      <div>
        <div className="timelineTitle">{title}</div>
        <div className="timelineText">{text}</div>
      </div>
    </div>
  );
}

function Enrollment() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [ack1, setAck1] = useState(false);
  const [ack2, setAck2] = useState(false);
  const [ack3, setAck3] = useState(false);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    const zip = readStr(STORAGE.zip);
    const territory_id = readStr(STORAGE.territoryId);
    const project_id = readStr(STORAGE.projectId);

    if (!zip || !territory_id) {
      setError("Please run eligibility first so we know your territory.");
      return;
    }
    if (!project_id) {
      setError("Please choose a project first.");
      return;
    }
    if (!name.trim() || !email.trim() || !address.trim()) {
      setError("Please fill out name, email, and address.");
      return;
    }
    if (!ack1 || !ack2 || !ack3) {
      setError("Please check all acknowledgements to continue.");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const res = await enroll({
        name,
        email,
        address,
        zip,
        territory_id,
        project_id,
      });

      const enrollmentId =
        res?.enrollment_id || res?.id || res?.enrollmentId || "";

      if (enrollmentId) saveStr(STORAGE.enrollmentId, enrollmentId);

      navigate(`/dashboard?status=submitted${enrollmentId ? `&enrollment_id=${encodeURIComponent(enrollmentId)}` : ""}`);
    } catch (e) {
      setError(e?.message || "Enrollment failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Section
      title="Enrollment"
      subtitle="Complete enrollment in minutes. No equipment installation. No subscription required."
    >
      <Card>
        {error ? (
          <div className="errorCard">
            <div className="errorTitle">Action needed</div>
            <div className="errorText">{error}</div>
          </div>
        ) : null}

        <div className="formGrid">
          <div className="formRow">
            <label className="label">Name</label>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name"
              disabled={loading}
            />
          </div>

          <div className="formRow">
            <label className="label">Email</label>
            <input
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@email.com"
              disabled={loading}
            />
          </div>

          <div className="formRow">
            <label className="label">Address</label>
            <input
              className="input"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Street, City, NY"
              disabled={loading}
            />
          </div>

          <div className="formRow">
            <label className="label">Utility</label>
            <input className="input" value={BRAND.territory} disabled />
          </div>
        </div>

        <div className="checks">
          <label className="checkRow">
            <input
              type="checkbox"
              checked={ack1}
              onChange={(e) => setAck1(e.target.checked)}
              disabled={loading}
            />
            <span>No roof changes</span>
          </label>
          <label className="checkRow">
            <input
              type="checkbox"
              checked={ack2}
              onChange={(e) => setAck2(e.target.checked)}
              disabled={loading}
            />
            <span>No utility switching</span>
          </label>
          <label className="checkRow">
            <input
              type="checkbox"
              checked={ack3}
              onChange={(e) => setAck3(e.target.checked)}
              disabled={loading}
            />
            <span>Cancel enrollment anytime</span>
          </label>
        </div>

        <div className="rowActions">
          <PrimaryButton onClick={submit} disabled={loading}>
            {loading ? "Submitting..." : "Complete enrollment"}
          </PrimaryButton>
          <SecondaryButton onClick={() => navigate("/projects")} disabled={loading}>
            Back to projects
          </SecondaryButton>
        </div>

        <div className="helperText">{NO_SUBSCRIPTION_MESSAGE}</div>
      </Card>
    </Section>
  );
}

function Dashboard() {
  const loc = useLocation();
  const params = new URLSearchParams(loc.search);

  const urlEnrollmentId = params.get("enrollment_id") || "";
  const storedEnrollmentId = readStr(STORAGE.enrollmentId);
  const enrollmentId = urlEnrollmentId || storedEnrollmentId;

  const [data, setData] = useState(null);
  const [loadErr, setLoadErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enrollmentId) return;

    let alive = true;
    setLoading(true);
    setLoadErr("");

    getEnrollment(enrollmentId)
      .then((res) => {
        if (!alive) return;
        setData(res);
      })
      .catch((e) => {
        if (!alive) return;
        setLoadErr(e?.message || "Could not load enrollment.");
        setData(null);
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [enrollmentId]);

  const status = String(data?.status || params.get("status") || "submitted");

  const steps = [
    { key: "submitted", label: "Submitted" },
    { key: "approved", label: "Approved" },
    { key: "credits_active", label: "Credits active" },
  ];
  const activeIndex = Math.max(0, steps.findIndex((s) => s.key === status));

  const projectName =
    data?.project_name || data?.project || "Northport Community Solar";

  const savingsMonth =
    Number(data?.estimated_monthly_savings ?? data?.monthly_savings) || 28;

  return (
    <Section title="Dashboard" subtitle="Your enrollment status and savings at a glance.">
      {loading ? <div className="helperText">Loading enrollment...</div> : null}
      {loadErr ? (
        <div className="helperBox" style={{ marginBottom: 12 }}>
          {loadErr}
        </div>
      ) : null}

      <div className="dashGrid">
        <Card>
          <div className="dashTitle">Current project</div>
          <div className="dashBig">{projectName}</div>
          <div className="dashMeta">Utility: {BRAND.territory}</div>
          <div className="dashMeta">{NO_SUBSCRIPTION_MESSAGE}</div>
        </Card>

        <Card>
          <div className="dashTitle">Estimated savings this month</div>
          <div className="dashBig">{money(savingsMonth)}</div>
          <div className="dashMeta">Estimate based on recent usage and credit rate</div>
        </Card>

        <Card>
          <div className="dashTitle">When credits typically begin</div>
          <div className="dashBig">1–2 billing cycles</div>
          <div className="dashMeta">Credits show up as a line item on your PSEG bill</div>
        </Card>

        <Card className="dashWide">
          <div className="dashTitle">Status tracker</div>
          <div className="tracker">
            {steps.map((s, idx) => {
              const done = idx <= activeIndex;
              return (
                <div
                  key={s.key}
                  className={done ? "trackStep trackStepDone" : "trackStep"}
                >
                  <div className="trackDot" aria-hidden="true" />
                  <div className="trackLabel">{s.label}</div>
                </div>
              );
            })}
          </div>

          <div className="rowActions">
            <SecondaryButton onClick={() => alert("Bill credit breakdown page can be added next.")}>
              View bill credit breakdown
            </SecondaryButton>
            <SecondaryButton onClick={() => alert("Manage enrollment page can be added next.")}>
              Manage enrollment
            </SecondaryButton>
            <button
              className="btn btnDanger"
              onClick={() => alert("Cancel flow can be added next.")}
              type="button"
            >
              Cancel enrollment
            </button>
          </div>
        </Card>
      </div>
    </Section>
  );
}

function FaqPage() {
  return (
    <Section title="FAQ" subtitle="Big, readable answers with clear next steps.">
      <Card>
        <div className="faqList">
          <FaqItem q="Do I switch utilities?" a="No. PSEG still delivers electricity and sends your bill." />
          <FaqItem q="Do I install equipment?" a="No panels, no wiring, no roof work." />
          <FaqItem q="Where do credits show up?" a="On your PSEG bill as a line item credit that reduces what you owe." />
          <FaqItem q="How long until credits start?" a="Typically 1 to 2 billing cycles." />
          <FaqItem q="Can I cancel?" a="Yes. Cancel enrollment anytime." />
          <FaqItem q="Is this peer-to-peer energy selling?" a="No. This is credit allocation through community solar, not direct energy selling." />
        </div>

        <div className="supportBox">
          <div className="supportTitle">Need help?</div>
          <div className="supportText">
            Contact support and we will help you understand credits, billing, and enrollment.
          </div>
          <div className="supportActions">
            <SecondaryButton onClick={() => alert("Support page can be added next.")}>
              Contact support
            </SecondaryButton>
          </div>
        </div>

        <div className="helperText">{NO_SUBSCRIPTION_MESSAGE}</div>
      </Card>
    </Section>
  );
}

function FaqItem({ q, a }) {
  return (
    <details className="faqItem">
      <summary className="faqQ">{q}</summary>
      <div className="faqA">{a}</div>
    </details>
  );
}

function Pricing() {
  return (
    <Section
      title="Cost and savings"
      subtitle="No subscription required. Savings are built into your credit discount."
    >
      <div className="pricingGrid">
        <Card>
          <div className="priceTitle">How savings work</div>
          <div className="priceBig">Discounted credit value</div>
          <div className="priceText">
            Your utility issues bill credits based on solar production. You pay a discounted portion
            of the credit value and keep the difference as savings.
          </div>
          <div className="priceFoot">{NO_SUBSCRIPTION_MESSAGE}</div>
        </Card>

        <Card>
          <div className="priceTitle">Cancel enrollment anytime</div>
          <div className="priceBig">Utility stays the same</div>
          <div className="priceText">
            If your needs change, you can cancel enrollment. PSEG still delivers power and bills you.
          </div>
          <div className="priceFoot">{TRUST_MESSAGE}</div>
        </Card>
      </div>
    </Section>
  );
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/eligibility" element={<Eligibility />} />
        <Route path="/eligibility/result" element={<EligibilityResult />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:projectId" element={<ProjectDetail />} />
        <Route path="/credit-explanation" element={<CreditExplanation />} />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route path="/enrollment" element={<Enrollment />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/faq" element={<FaqPage />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="*" element={<Home />} />
      </Routes>
    </Layout>
  );
}