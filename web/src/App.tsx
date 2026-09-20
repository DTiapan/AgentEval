import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Info,
  ShieldAlert,
  X,
} from "lucide-react";
import { AssuranceView } from "./components/AssuranceView";
import { Header } from "./components/Header";
import { Landing } from "./components/Landing";
import { Studio } from "./components/Studio";
import { ToastMessage, WorkspaceProvider, useWorkspace } from "./context/WorkspaceContext";
import { PRODUCT_DOMAIN } from "./lib/product";

const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useWorkspace();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast: ToastMessage) => {
        const isSuccess = toast.type === "success";
        const isError = toast.type === "error";
        const isWarning = toast.type === "warning";

        return (
          <div
            key={toast.id}
            className={`flex items-start gap-3 rounded-lg border p-3.5 shadow-sm transition-all ${
              isSuccess
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200"
                : isError
                ? "border-destructive/30 bg-destructive/10 text-destructive dark:text-destructive-foreground"
                : isWarning
                ? "border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200"
                : "border-border bg-card text-foreground"
            }`}
          >
            {isSuccess ? (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400 mt-0.5" />
            ) : isError ? (
              <ShieldAlert className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
            ) : isWarning ? (
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
            ) : (
              <Info className="h-4 w-4 shrink-0 text-muted-foreground mt-0.5" />
            )}

            <div className="flex-1 text-xs">
              <div className="font-semibold">{toast.title}</div>
              {toast.message && (
                <div className="mt-0.5 text-[11px] opacity-90 leading-relaxed">
                  {toast.message}
                </div>
              )}
            </div>

            <button
              onClick={() => removeToast(toast.id)}
              className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
};

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("AgentEval UI Error Boundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="mx-auto my-12 max-w-xl rounded-xl border border-destructive/40 bg-card p-6 text-center shadow-sm">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10 text-destructive border border-destructive/30">
            <AlertCircle className="h-5 w-5" />
          </div>
          <h2 className="text-sm font-semibold text-foreground">
            View Render Exception Caught
          </h2>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {this.state.error?.message || "An unexpected error occurred while rendering."}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            className="mt-4 rounded-md border border-border bg-secondary px-3.5 py-1.5 font-mono text-xs font-medium text-secondary-foreground hover:bg-secondary/80 transition-colors cursor-pointer"
          >
            Reload Interface
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const MainContent: React.FC<{ onBackToMarketing?: () => void }> = ({
  onBackToMarketing,
}) => {
  const [activeTab, setActiveTab] = useState<"studio" | "assurance">("studio");

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans transition-colors duration-200">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onBrandClick={onBackToMarketing}
      />

      <main className="flex-1 pb-10">
        <ErrorBoundary>
          {activeTab === "studio" ? (
            <Studio onSuiteCreated={() => setActiveTab("assurance")} />
          ) : (
            <AssuranceView />
          )}
        </ErrorBoundary>
      </main>

      {/* Clean Minimalist Engineering Footer */}
      <footer className="border-t border-border bg-card/60 py-4 text-center text-xs text-muted-foreground transition-colors duration-200">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2 font-mono text-[11px]">
            <span className="text-foreground font-semibold">AgentEval</span>
            <span>•</span>
            <span>Trajectory-First Assurance</span>
            <span>•</span>
            <span>Deterministic Evidence vs Self-Report</span>
          </div>
          <div className="text-[11px] text-muted-foreground font-mono">
            {PRODUCT_DOMAIN} · OpenTelemetry & OpenInference
          </div>
        </div>
      </footer>

      <ToastContainer />
    </div>
  );
};

type SiteRoute = "marketing" | "console";

function readRoute(): SiteRoute {
  const hash = window.location.hash.replace(/^#/, "");
  if (hash === "/console" || hash.startsWith("/console/")) return "console";
  return "marketing";
}

function navigateTo(route: SiteRoute) {
  window.location.hash = route === "console" ? "#/console" : "#/";
}

export const App: React.FC = () => {
  const [route, setRoute] = useState<SiteRoute>(() => readRoute());

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    window.addEventListener("hashchange", onHash);
    if (!window.location.hash) {
      window.location.hash = "#/";
    }
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const enterConsole = () => navigateTo("console");

  return (
    <WorkspaceProvider>
      {route === "marketing" ? (
        <Landing onStartFree={enterConsole} onOpenConsole={enterConsole} />
      ) : (
        <MainContent onBackToMarketing={() => navigateTo("marketing")} />
      )}
    </WorkspaceProvider>
  );
};

export default App;
