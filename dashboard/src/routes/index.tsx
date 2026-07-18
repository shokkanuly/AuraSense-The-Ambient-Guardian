import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Shield,
  Zap,
  Droplets,
  Activity,
  Wind,
  Radio,
  Smartphone,
  Lock,
  ArrowRight,
} from "lucide-react";
import heroHub from "@/assets/hero-hub.jpg";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AuraSense — The Ambient Guardian" },
      {
        name: "description",
        content:
          "A privacy-first edge-AI hub that learns your home's normal rhythm and warns you the moment something drifts.",
      },
      { property: "og:title", content: "AuraSense — The Ambient Guardian" },
      {
        property: "og:description",
        content:
          "A privacy-first edge-AI hub that learns your home's normal rhythm and warns you the moment something drifts.",
      },
      { property: "og:image", content: heroHub },
      { name: "twitter:image", content: heroHub },
    ],
  }),
  component: Index,
});

const capabilities = [
  {
    icon: Zap,
    title: "Whole-home power",
    description:
      "A clamp-on CT sensor reads the mains feed, detecting appliance-level anomalies before they become failures.",
  },
  {
    icon: Activity,
    title: "Presence & falls",
    description:
      "60 GHz mmWave radar senses presence, breathing, and falls without a single camera in your home.",
  },
  {
    icon: Droplets,
    title: "Acoustic events",
    description:
      'Tiny on-device classifiers emit only labels like "glass break" or "running water" — never raw audio.',
  },
  {
    icon: Wind,
    title: "Air & environment",
    description:
      "Temperature, humidity, pressure, and VOC data catch mold risk, air-quality shifts, and heat signatures.",
  },
];

const trustPillars = [
  {
    icon: Lock,
    title: "No cloud cameras",
    description:
      "Video and raw audio never leave the house. Inference happens on the edge, inside your own hub.",
  },
  {
    icon: Radio,
    title: "Local-first",
    description:
      "The hub runs its own broker, time-series database, and models. It stays offline-capable by default.",
  },
  {
    icon: Smartphone,
    title: "Plain-language alerts",
    description:
      "When reality deviates, you get a clear sentence on your phone — not a raw sensor graph.",
  },
  {
    icon: Shield,
    title: "Built on what you own",
    description:
      "Matter/Thread support lets AuraSense observe and control the smart devices you already have.",
  },
];

function Index() {
  return (
    <div className="relative">
      {/* Hero */}
      <section className="relative overflow-hidden px-6 pb-20 pt-24 lg:pb-32 lg:pt-36">
        <div className="surface-glow absolute inset-0" aria-hidden="true" />
        <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2">
          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
              <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
              Project 1 · Smart Home / IoT
            </div>
            <h1 className="mt-6 font-display text-5xl font-bold leading-[1.05] tracking-tight text-foreground md:text-6xl lg:text-7xl">
              AuraSense — <br />
              <span className="text-gradient">The Ambient Guardian</span>
            </h1>
            <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted-foreground">
              A privacy-first edge-AI hub that learns your home's normal rhythm and warns you the
              moment something drifts — a failing fridge, a hidden water leak, an intrusion, or an
              elderly parent's fall.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                to="/contact"
                className="group inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20"
              >
                Join the waitlist
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                to="/how-it-works"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-secondary/50 px-6 py-3.5 text-sm font-semibold text-foreground transition-colors hover:bg-secondary"
              >
                See how it works
              </Link>
            </div>
            <div className="mt-10 flex items-center gap-3 text-sm text-muted-foreground">
              <Shield className="h-4 w-4 text-primary" />
              <span>No cloud cameras. No audio leaving the house. Privacy-first by design.</span>
            </div>
          </div>

          <div className="relative">
            <div className="relative aspect-[16/10] overflow-hidden rounded-2xl border border-border/60 bg-card shadow-2xl glow-indigo">
              <img
                src={heroHub}
                alt="AuraSense hub glowing with a protective indigo aura on a modern shelf"
                className="h-full w-full object-cover"
                width={1536}
                height={1024}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-background/40 via-transparent to-transparent" />
            </div>
            <div className="absolute -bottom-6 -left-6 hidden rounded-xl border border-border bg-card p-4 shadow-xl lg:block">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Activity className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Detected</p>
                  <p className="font-display text-sm font-semibold text-foreground">
                    Unusual current draw
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Capabilities grid */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-2xl">
            <h2 className="font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
              It listens to your home's electricity, sound, motion, and air
            </h2>
            <p className="mt-4 text-muted-foreground">
              AuraSense builds a personal model of “normal” from four quiet sensor streams, so it
              can spot the problems that rule-based systems miss.
            </p>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {capabilities.map((cap) => {
              const Icon = cap.icon;
              return (
                <div
                  key={cap.title}
                  className="group rounded-2xl border border-border bg-card p-6 transition-all hover:border-primary/30 hover:bg-card/80"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary transition-transform group-hover:scale-105">
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="mt-5 font-display text-lg font-semibold text-foreground">
                    {cap.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {cap.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Trust / Privacy pitch */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-12 lg:grid-cols-2">
            <div className="rounded-2xl border border-border bg-card p-8 lg:p-12">
              <h2 className="font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
                Privacy is not a feature. It is the architecture.
              </h2>
              <p className="mt-4 text-muted-foreground">
                Most smart home devices ship your data to the cloud. AuraSense runs its AI on the
                edge, so the raw signals that describe your life stay inside your walls.
              </p>
              <div className="mt-8 grid gap-6 sm:grid-cols-2">
                {trustPillars.map((pillar) => {
                  const Icon = pillar.icon;
                  return (
                    <div key={pillar.title} className="flex gap-4">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h4 className="font-display text-sm font-semibold text-foreground">
                          {pillar.title}
                        </h4>
                        <p className="mt-1 text-sm text-muted-foreground">{pillar.description}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="relative flex items-center">
              <div className="relative aspect-[4/3] w-full overflow-hidden rounded-2xl border border-border/60 bg-card shadow-xl">
                <img
                  src={heroHub}
                  alt="AuraSense hub creating a protective aura around a home"
                  className="h-full w-full object-cover"
                  loading="lazy"
                  width={1536}
                  height={1024}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA band */}
      <section className="px-6 py-24">
        <div className="mx-auto max-w-5xl rounded-3xl border border-primary/20 bg-primary/10 p-10 text-center md:p-16 surface-glow">
          <h2 className="font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            Ready to make your home truly aware?
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            AuraSense is currently in development. Join the waitlist to be the first to know when
            early access opens.
          </p>
          <Link
            to="/contact"
            className="group mt-8 inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20"
          >
            Join the waitlist
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>
      </section>
    </div>
  );
}
