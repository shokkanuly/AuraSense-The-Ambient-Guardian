import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Mail, MapPin, Send, CheckCircle, Shield, ArrowLeft } from "lucide-react";

export const Route = createFileRoute("/contact")({
  head: () => ({
    meta: [
      { title: "Contact — AuraSense" },
      {
        name: "description",
        content: "Join the AuraSense waitlist or get in touch with the team.",
      },
      { property: "og:title", content: "Contact — AuraSense" },
      {
        property: "og:description",
        content: "Join the AuraSense waitlist or get in touch with the team.",
      },
    ],
  }),
  component: ContactPage,
});

function ContactPage() {
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", interest: "waitlist", message: "" });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="relative px-6">
      <div className="surface-glow absolute inset-0 -z-10" aria-hidden="true" />

      <section className="mx-auto max-w-7xl pb-20 pt-24 lg:pt-32">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
            Contact
          </div>
          <h1 className="mt-6 font-display text-4xl font-bold leading-tight tracking-tight text-foreground md:text-5xl lg:text-6xl">
            Join the waitlist
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            AuraSense is currently in development. Leave your details and we'll reach out when early
            access is available.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl pb-24 lg:pb-32">
        <div className="grid gap-12 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <div className="rounded-2xl border border-border bg-card p-6 shadow-lg md:p-8">
              {submitted ? (
                <div className="py-12 text-center">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <CheckCircle className="h-8 w-8" />
                  </div>
                  <h2 className="mt-6 font-display text-2xl font-bold text-foreground">
                    You're on the list
                  </h2>
                  <p className="mx-auto mt-2 max-w-md text-muted-foreground">
                    Thanks for your interest in AuraSense. We'll be in touch as soon as early access
                    opens.
                  </p>
                  <button
                    onClick={() => {
                      setSubmitted(false);
                      setForm({ name: "", email: "", interest: "waitlist", message: "" });
                    }}
                    className="mt-8 inline-flex items-center gap-2 rounded-lg border border-border bg-secondary px-5 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-secondary/80"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Submit another entry
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="grid gap-6 md:grid-cols-2">
                    <div className="space-y-2">
                      <label htmlFor="name" className="text-sm font-medium text-foreground">
                        Name
                      </label>
                      <input
                        id="name"
                        type="text"
                        required
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground outline-none ring-offset-background transition-colors focus-visible:ring-2 focus-visible:ring-ring"
                        placeholder="Jane Doe"
                      />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="email" className="text-sm font-medium text-foreground">
                        Email
                      </label>
                      <input
                        id="email"
                        type="email"
                        required
                        value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground outline-none ring-offset-background transition-colors focus-visible:ring-2 focus-visible:ring-ring"
                        placeholder="jane@example.com"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="interest" className="text-sm font-medium text-foreground">
                      I'm interested in
                    </label>
                    <select
                      id="interest"
                      value={form.interest}
                      onChange={(e) => setForm({ ...form, interest: e.target.value })}
                      className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground outline-none ring-offset-background transition-colors focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="waitlist">Early access / waitlist</option>
                      <option value="developer">Developer / SDK access</option>
                      <option value="partner">Partnership / distribution</option>
                      <option value="investor">Investor information</option>
                      <option value="press">Press inquiry</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="message" className="text-sm font-medium text-foreground">
                      Message (optional)
                    </label>
                    <textarea
                      id="message"
                      rows={4}
                      value={form.message}
                      onChange={(e) => setForm({ ...form, message: e.target.value })}
                      className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground outline-none ring-offset-background transition-colors focus-visible:ring-2 focus-visible:ring-ring"
                      placeholder="Tell us about your home, your project, or your questions..."
                    />
                  </div>

                  <button
                    type="submit"
                    className="group inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 hover:shadow-lg hover:shadow-primary/20 md:w-auto"
                  >
                    <Send className="h-4 w-4" />
                    Submit
                  </button>
                </form>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl border border-border bg-card p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Mail className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display text-sm font-semibold text-foreground">Email</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                <a href="mailto:hello@aurasense.io" className="hover:text-foreground">
                  hello@aurasense.io
                </a>
              </p>
            </div>

            <div className="rounded-2xl border border-border bg-card p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <MapPin className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display text-sm font-semibold text-foreground">Location</h3>
              <p className="mt-1 text-sm text-muted-foreground">Cambridge, MA</p>
            </div>

            <div className="rounded-2xl border border-border bg-card p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Shield className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display text-sm font-semibold text-foreground">
                Privacy note
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                We only use your email to contact you about AuraSense. No spam, no third-party
                sales.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
