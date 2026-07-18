import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  Home,
  ShieldCheck,
  TrendingUp,
  ArrowRight,
  CheckCircle,
} from "lucide-react";
import privacyShield from "@/assets/privacy-shield.jpg";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About — AuraSense" },
      {
        name: "description",
        content:
          "Why AuraSense exists: the gap between dumb automation and privacy-invading cloud cameras, and the market for aging-in-place safety.",
      },
      { property: "og:title", content: "About — AuraSense" },
      {
        property: "og:description",
        content:
          "Why AuraSense exists: the gap between dumb automation and privacy-invading cloud cameras, and the market for aging-in-place safety.",
      },
      { property: "og:image", content: privacyShield },
      { name: "twitter:image", content: privacyShield },
    ],
  }),
  component: AboutPage,
});

const marketStats = [
  {
    label: "Water damage claims",
    value: "#2",
    description: "largest home-insurance claim category",
  },
  {
    label: "Aging-in-place market",
    value: "$88B+",
    description: "enormous and underserved by current tech",
  },
  {
    label: "Smart homes with cameras",
    value: "Most",
    description: "send raw video to cloud servers",
  },
];

const problemPoints = [
  {
    icon: AlertTriangle,
    title: "Reactive rules miss the real failures",
    description:
      '"If motion, turn on light" does nothing when a fridge compressor draws odd current at 2 a.m. or a pipe bursts behind a wall.',
  },
  {
    icon: Home,
    title: "No device understands the home",
    description:
      "Today's market is a pile of disconnected gadgets. Each one reacts to a single trigger, not the overall rhythm of the house.",
  },
  {
    icon: ShieldCheck,
    title: "The privacy trade-off is false",
    description:
      "Cloud cameras ask families to trade dignity for safety. AuraSense rejects that choice by running everything on the edge.",
  },
];

function AboutPage() {
  return (
    <div className="relative px-6">
      <div className="surface-glow absolute inset-0 -z-10" aria-hidden="true" />

      <section className="mx-auto max-w-7xl pb-20 pt-24 lg:pt-32">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
            About
          </div>
          <h1 className="mt-6 font-display text-4xl font-bold leading-tight tracking-tight text-foreground md:text-5xl lg:text-6xl">
            The problem, the market, and our answer
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            AuraSense targets the gap between dumb automation and privacy-invading cloud cameras. We
            believe the most expensive failures — burst pipes, electrical faults, elderly falls —
            are exactly the ones a reactive rule engine misses.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl py-12">
        <div className="grid gap-8 md:grid-cols-3">
          {marketStats.map((stat) => (
            <div key={stat.label} className="rounded-2xl border border-border bg-card p-6">
              <p className="font-display text-4xl font-bold text-primary">{stat.value}</p>
              <p className="mt-2 font-display text-sm font-semibold uppercase tracking-wide text-foreground">
                {stat.label}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">{stat.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl py-20">
        <div className="grid gap-12 lg:grid-cols-2">
          <div className="relative">
            <div className="aspect-[4/3] overflow-hidden rounded-2xl border border-border/60 bg-card shadow-xl">
              <img
                src={privacyShield}
                alt="A modern home protected by a translucent shield of indigo light"
                className="h-full w-full object-cover"
                width={1408}
                height={1008}
              />
            </div>
          </div>
          <div className="flex flex-col justify-center">
            <h2 className="font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
              Today's smart home is not smart enough
            </h2>
            <p className="mt-4 text-muted-foreground">
              The smart-home market is fragmented into devices that react to rules you write
              yourself. Almost none of them learn, reason, or understand context. Meanwhile, the
              failures that cost the most — water damage, electrical faults, falls — need exactly
              that kind of understanding.
            </p>
            <ul className="mt-8 space-y-4">
              {[
                "Reactive automation misses gradual, contextual problems",
                "Cloud cameras create privacy risks families should not have to accept",
                "Aging-in-place safety is a massive, underserved market",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-foreground">
                  <CheckCircle className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl py-20">
        <div className="grid gap-8 md:grid-cols-3">
          {problemPoints.map((point) => {
            const Icon = point.icon;
            return (
              <div
                key={point.title}
                className="rounded-2xl border border-border bg-card p-6 transition-all hover:border-primary/30"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="mt-5 font-display text-lg font-semibold text-foreground">
                  {point.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {point.description}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      <section className="mx-auto max-w-7xl py-20 lg:py-28">
        <div className="rounded-3xl border border-border bg-card p-8 lg:p-12">
          <div className="flex flex-col items-start justify-between gap-8 lg:flex-row lg:items-center">
            <div className="max-w-2xl">
              <div className="flex items-center gap-2 text-sm font-semibold text-primary">
                <TrendingUp className="h-4 w-4" />
                The opportunity
              </div>
              <h2 className="mt-3 font-display text-2xl font-bold tracking-tight text-foreground md:text-3xl">
                A single intelligent layer on top of gear people already own
              </h2>
              <p className="mt-3 text-muted-foreground">
                AuraSense does not try to replace every smart device. It observes, learns, and warns
                — integrating with Matter and Thread so it works with the home you already have.
              </p>
            </div>
            <Link
              to="/how-it-works"
              className="group inline-flex shrink-0 items-center gap-2 rounded-lg bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90"
            >
              Explore the system
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
