import React from "react";
import Editor from "@monaco-editor/react";

interface CodeViewerProps {
  code: string;
  language?: string;
  height?: string;
  readOnly?: boolean;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({
  code,
  language = "typescript",
  height = "320px",
  readOnly = true,
}) => {
  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");
  return (
    <div className="w-full overflow-hidden rounded-md border border-border bg-card">
      <Editor
        height={height}
        language={language}
        value={code}
        theme={isDark ? "vs-dark" : "light"}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 12,
          fontFamily: "JetBrains Mono, monospace",
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          automaticLayout: true,
          padding: { top: 8, bottom: 8 },
          wordWrap: "on",
          renderLineHighlight: "all",
        }}
        loading={
          <div className="flex h-40 items-center justify-center font-mono text-xs text-muted-foreground">
            Loading code inspector...
          </div>
        }
      />
    </div>
  );
};
