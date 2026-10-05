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
import { PRODUCT_DOMAIN } from "@/lib/product";
import { LandingHeroTerminal } from "@/components/motion/LandingHeroTerminal";

interface LandingProps {
  onStartFree: () => void;
  onOpenConsole: () => void;
}

const FEATURES = [
  {
    icon: FileCheck2,
    title: "Requirements → test pack",
    description:
      "Set-cover optimizer turns PRD capabilities into a minimal regression pack, without hand-written YAML harnesses.",
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

const DOCS_URL = "https://github.com/DTiapan/AgentEval#documentation-index";
const REPO_URL = "https://github.com/DTiapan/AgentEval";
const LICENSE_URL = "https://github.com/DTiapan/AgentEval/blob/main/LICENSE";

export const Landing: React.FC<LandingProps> = ({ onStartFree, onOpenConsole }) => {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <a
        href="#landing-main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      >
        Skip to content
      </a>
      <header className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-30">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Shield className="h-4 w-4" aria-hidden />
            </div>
            <span className="text-sm font-semibold tracking-tight">
              Agent<span className="text-primary font-bold">Eval</span>
            </span>
            <Badge variant="outline" className="font-mono text-[10px] hidden sm:inline-flex">
              {PRODUCT_DOMAIN}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" className="text-xs" asChild>
              <a href={DOCS_URL} target="_blank" rel="noopener noreferrer">
                <BookOpen className="h-3.5 w-3.5 mr-1.5" aria-hidden />
                Docs
              </a>
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

      <main id="landing-main" tabIndex={-1} className="flex-1">
        <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-20">
          <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-[2.65rem] lg:leading-tight text-balance">
                Test AI agents before production.
              </h1>
              <p className="mt-4 text-base text-muted-foreground leading-relaxed max-w-xl">
                Deterministic evidence, frozen regression suites, and release gating for
                tool-calling agents. No vibes, no prod APM.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button onClick={onStartFree} className="gap-2">
                  Start free
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Button>
                <Button variant="outline" onClick={onOpenConsole}>
                  Live demo console
                </Button>
              </div>
              <p className="mt-6 text-[11px] text-muted-foreground">
                Bring your PRD and agent HTTP endpoint. Evaluation packs and runs come from the
                engine, not preloaded demo data.
              </p>
            </div>
            <LandingHeroTerminal />
          </div>
        </section>

        <section className="border-y border-border bg-muted/30">
          <div className="mx-auto grid max-w-6xl gap-6 px-4 py-12 sm:px-6 md:grid-cols-3">
            {FEATURES.map((f) => (
              <Card
                key={f.title}
                className="border-border bg-card shadow-xs"
              >
                <CardHeader className="pb-2">
                  <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-md border border-border bg-muted/50 text-primary">
                    <f.icon className="h-4 w-4" aria-hidden />
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

        <section className="mx-auto max-w-6xl px-4 py-12 pb-16 sm:px-6">
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
                Sealed HTTP evidence · no guessed passes
              </span>
            </CardContent>
          </Card>
        </section>
      </main>

      <footer className="border-t border-border bg-card/60 py-6 text-xs text-muted-foreground">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 sm:px-6">
          <span>
            © {new Date().getFullYear()} AgentEval · {PRODUCT_DOMAIN}
          </span>
          <div className="flex gap-4">
            <a
              href={LICENSE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              License
            </a>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
};
