import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Server,
  Smartphone,
  Wifi,
  Bluetooth,
  Cpu,
  Waves,
  Mic,
  Thermometer,
  Activity,
  Radio,
  ArrowRight,
} from "lucide-react";
import architecture from "@/assets/architecture.jpg";
import sensors from "@/assets/sensors.jpg";

export const Route = createFileRoute("/how-it-works")({
  head: () => ({
    meta: [
      { title: "How it works — AuraSense" },
      {
        name: "description",
        content:
          "AuraSense system architecture: sensor nodes, the edge AI hub, the phone app, and hardware connectivity.",
      },
      { property: "og:title", content: "How it works — AuraSense" },
      {
        property: "og:description",
        content:
          "AuraSense system architecture: sensor nodes, the edge AI hub, the phone app, and hardware connectivity.",
      },
      { property: "og:image", content: architecture },
      { name: "twitter:image", content: architecture },
    ],
  }),
  component: HowItWorksPage,
});

const architectureSteps = [
  {
    icon: Radio,
    title: "Sensor nodes",
    description:
      "Battery or mains ESP32-S3 modules scattered around the home. Each carries one or two sensors and publishes compact feature vectors over a local MQTT bus — never raw streams.",
  },
  {
    icon: Server,
    title: "The hub",
    description:
      "A Raspberry Pi 5 (or Jetson Orin Nano for heavier vision) runs the message broker, time-series database, and all inference models. The brain stays offline-capable.",
  },
  {
    icon: Smartphone,
    title: "The phone",
    description:
      "A Flutter app is your control panel and conversational interface. It talks to the hub over the LAN, and to a thin cloud only for push notifications and encrypted backups.",
  },
  {
    icon: Wifi,
    title: "Interoperability",
    description:
      "The hub speaks Matter/Thread, so it can observe and control third-party smart devices. AuraSense becomes the intelligent layer on top of gear you already own.",
  },
];

const hardwareItems = [
  {
    icon: Activity,
    title: "Whole-home power",
    description:
      "Clamp-on CT sensor on the mains feed streams high-rate current and voltage — the raw material for appliance-level energy disaggregation.",
  },
  {
    icon: Waves,
    title: "Presence & falls",
    description:
      "60 GHz mmWave radar module (e.g., Infineon BGT60) gives privacy-preserving presence, breathing, and fall detection without a camera.",
  },
  {
    icon: Mic,
    title: "Acoustic events",
    description:
      'A MEMS microphone on each node runs a tiny on-device classifier. It emits only labels like "glass break" or "running water" — never audio.',
  },
  {
    icon: Thermometer,
    title: "Air & environment",
    description:
      "BME680 for temperature, humidity, pressure, and VOC gas — useful for mold risk, air quality, and appliance heat signatures.",
  },
  {
    icon: Bluetooth,
    title: "Links",
    description:
      "BLE and Wi-Fi for nodes; Thread/Matter for the smart-home mesh; the phone connects over the local network with a cloud relay fallback.",
  },
  {
    icon: Cpu,
    title: "Edge inference",
    description:
      "All models run on the hub. Feature vectors are small, privacy-preserving, and never enough to reconstruct raw audio or video.",
  },
];

function HowItWorksPage() {
  return (
    <div className="relative px-6">
      <div className="surface-glow absolute inset-0 -z-10" aria-hidden="true" />

      <section className="mx-auto max-w-7xl pb-20 pt-24 lg:pt-32">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
            System architecture
          </div>
          <h1 className="mt-6 font-display text-4xl font-bold leading-tight tracking-tight text-foreground md:text-5xl lg:text-6xl">
            How AuraSense <br />
            <span className="text-gradient">builds a model of normal</span>
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            The design is a classic edge-first IoT topology with an on-device intelligence layer.
            Data is processed locally, only labels and summaries leave the house, and the whole
            system stays offline-capable.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl py-12">
        <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-card shadow-xl">
          <img
            src={architecture}
            alt="AuraSense edge AI architecture diagram showing hub, sensor nodes, and phone connected by secure lines"
            className="h-auto w-full object-cover"
            width={1536}
            height={1024}
          />
        </div>
      </section>

      <section className="mx-auto max-w-7xl py-20">
        <div className="grid gap-6 md:grid-cols-2">
          {architectureSteps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div
                key={step.title}
                className="relative rounded-2xl border border-border bg-card p-6 transition-all hover:border-primary/30"
              >
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Icon className="h-6 w-6" />
                  </div>
                  <div>
                    <div className="font-display text-xs font-semibold uppercase tracking-wider text-primary">
                      Step 0{idx + 1}
                    </div>
                    <h3 className="mt-1 font-display text-lg font-semibold text-foreground">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {step.description}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="mx-auto max-w-7xl py-20">
        <div className="grid gap-12 lg:grid-cols-2">
          <div className="order-2 flex items-center lg:order-1">
            <div className="aspect-[4/3] w-full overflow-hidden rounded-2xl border border-border/60 bg-card shadow-xl">
              <img
                src={sensors}
                alt="AuraSense sensor nodes for power, radar, acoustic, and environmental sensing"
                className="h-full w-full object-cover"
                loading="lazy"
                width={1536}
                height={1024}
              />
            </div>
          </div>
          <div className="order-1 flex flex-col justify-center lg:order-2">
            <h2 className="font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
              Hardware & connectivity
            </h2>
            <p className="mt-4 text-muted-foreground">
              Every sensor is chosen to be cheap, privacy-preserving, and informative. The
              combination is what lets AuraSense learn the rhythm of a home without cameras or
              microphones sending data outside.
            </p>
            <div className="mt-8 grid gap-6">
              {hardwareItems.map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.title} className="flex gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-display text-sm font-semibold text-foreground">
                        {item.title}
                      </h4>
                      <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                        {item.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl py-20 lg:py-28">
        <div className="rounded-3xl border border-primary/20 bg-primary/10 p-8 text-center md:p-16 surface-glow">
          <h2 className="font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            Want the technical deep dive?
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            We're happy to share specs, SDK plans, and integration details with early users and
            partners.
          </p>
          <Link
            to="/contact"
            className="group mt-8 inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90"
          >
            Get in touch
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>
      </section>
    </div>
  );
}
