import React from "react";
import {
  ArrowRight,
  BookOpen,
  FileCheck2,
  GitBranch,
  PlayCircle,
  Shield,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  BREACH_AMOUNT_USD,
  PRODUCT_DOMAIN,
  REFUND_CEILING_USD,
  formatUsd,
} from "@/lib/product";

interface LandingProps {
  onStartFree: () => void;
  onOpenConsole: () => void;
}

const FEATURES = [
  {
    icon: FileCheck2,
    title: "Requirements → test pack",
    description:
      "Set-cover optimizer turns PRD capabilities into a minimal regression pack—no hand-written YAML harnesses.",
  },
  {
    icon: GitBranch,
    title: "Freeze & regress",
    description:
      "Baseline diff on every run. Ship only when frozen invariants still pass in CI.",
  },
  {
    icon: PlayCircle,
    title: "Replay & audit",
    description:
      "Jump-to-fail trajectories with sealed HTTP evidence and exportable HTML audit reports.",
  },
] as const;

export const Landing: React.FC<LandingProps> = ({ onStartFree, onOpenConsole }) => {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-30">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Shield className="h-4 w-4" />
            </div>
            <span className="text-sm font-semibold tracking-tight">
              Agent<span className="text-primary font-bold">Eval</span>
            </span>
            <Badge variant="outline" className="font-mono text-[10px] hidden sm:inline-flex">
              {PRODUCT_DOMAIN}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" className="text-xs" type="button">
              <BookOpen className="h-3.5 w-3.5 mr-1.5" />
              Docs
            </Button>
            <Button variant="outline" size="sm" className="text-xs" onClick={onOpenConsole}>
              Open console
            </Button>
            <Button size="sm" className="text-xs" onClick={onStartFree}>
              Start free
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-20">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-[2.65rem] lg:leading-tight text-balance">
                Test AI agents before production.
              </h1>
              <p className="mt-4 text-base text-muted-foreground leading-relaxed max-w-xl">
                Deterministic evidence, frozen regression suites, and release gating for
                tool-calling agents—no vibes, no prod APM.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button onClick={onStartFree} className="gap-2">
                  Start free
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <Button variant="outline" onClick={onOpenConsole}>
                  Live demo console
                </Button>
              </div>
              <p className="mt-6 text-[11px] text-muted-foreground">
                Bring your PRD and agent HTTP endpoint — evaluation packs and runs come from the
                engine, not preloaded demo data.
              </p>
            </div>
            <Card className="overflow-hidden border-border shadow-xs">
              <img
                src="/design/ref/landing.png"
                alt="AgentEval marketing landing reference"
                className="w-full h-auto object-cover object-top"
                loading="lazy"
              />
            </Card>
          </div>
        </section>

        <section className="border-y border-border bg-muted/30">
          <div className="mx-auto grid max-w-6xl gap-6 px-4 py-12 sm:px-6 md:grid-cols-3">
            {FEATURES.map((f) => (
              <Card key={f.title} className="border-border bg-card shadow-xs">
                <CardHeader className="pb-2">
                  <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-md border border-border bg-muted/50 text-primary">
                    <f.icon className="h-4 w-4" />
                  </div>
                  <CardTitle className="text-base">{f.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm leading-relaxed">
                    {f.description}
                  </CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
          <Card className="border-border bg-card font-mono text-xs shadow-xs">
            <CardContent className="flex flex-wrap items-center gap-3 p-4 sm:gap-4">
              <span className="text-muted-foreground">Invariant verdicts</span>
              <Separator orientation="vertical" className="hidden h-5 sm:block" />
              <Badge variant="pass" className="font-mono">PASS</Badge>
              <Badge variant="fail" className="font-mono">FAIL</Badge>
              <Badge variant="outline" className="font-mono text-amber-700 dark:text-amber-300 border-amber-500/40">
                UNVERIFIABLE
              </Badge>
              <span className="text-muted-foreground w-full sm:w-auto sm:ml-auto text-[11px]">
                test-ceiling-breach · {formatUsd(BREACH_AMOUNT_USD)} &gt; {formatUsd(REFUND_CEILING_USD)} cap
              </span>
            </CardContent>
          </Card>
        </section>

        <section className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
            Product screens (Stitch reference)
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              { src: "/design/ref/studio.png", label: "Studio & Planner" },
              { src: "/design/ref/assurance-runs.png", label: "Assurance Runs" },
            ].map((shot) => (
              <Card key={shot.label} className="overflow-hidden border-border">
                <img src={shot.src} alt={shot.label} className="w-full h-auto" loading="lazy" />
                <div className="border-t border-border px-3 py-2 text-xs font-medium text-muted-foreground">
                  {shot.label}
                </div>
              </Card>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-card/60 py-6 text-xs text-muted-foreground">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 sm:px-6">
          <span>
            © {new Date().getFullYear()} AgentEval · {PRODUCT_DOMAIN}
          </span>
          <div className="flex gap-4">
            <a href="#" className="hover:text-foreground transition-colors">Terms</a>
            <a href="#" className="hover:text-foreground transition-colors">Privacy</a>
            <a href="#" className="hover:text-foreground transition-colors">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
};
