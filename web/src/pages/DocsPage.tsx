import React, { useState, useCallback } from "react";
import { FileText, ExternalLink, WifiOff, Loader2 } from "lucide-react";
import { PageHeader } from "../components/PageHeader";

export const ORCANIUM_DOCS_URL = "https://orcanium.com/docs/";

export const DocumentationPage: React.FC = () => {
  const [state, setState] = useState<"loading" | "loaded" | "error">("loading");

  const handleRetry = useCallback(() => {
    setState("loading");
  }, []);

  return (
    <div className="p-6 flex min-w-0 max-w-full flex-col gap-6 h-full animate-fadeIn">
      <PageHeader
        icon={<FileText className="w-4 h-4 text-blue-400" />}
        title="Documentation"
        description="Orcanium system documentation and manual"
      >
        <a
          href={ORCANIUM_DOCS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold border border-zinc-200/60 dark:border-zinc-700/50 text-zinc-600 dark:text-neutral-300 hover:text-zinc-800 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700/50 transition-all"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Open documentation
        </a>
      </PageHeader>

      <div className="flex-1 flex flex-col min-h-0">
        {state === "error" ? (
          <div className="w-full flex-1 min-h-[500px] rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 bg-slate-600/80 flex flex-col items-center justify-center gap-3">
            <WifiOff className="w-8 h-8 text-neutral-300" />
            <p className="text-sm font-medium text-neutral-300">
              Documentation unavailable
            </p>
            <p className="text-xs text-neutral-300/70 max-w-md text-center">
              Could not reach {ORCANIUM_DOCS_URL}. The documentation site may be
              offline or your internet connection may be down.
            </p>
            <button
              onClick={handleRetry}
              className="mt-2 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 transition-all"
            >
              Try again
            </button>
          </div>
        ) : (
          <>
            {/* Loading overlay — shown until iframe fires onLoad */}
            {state === "loading" && (
              <div className="w-full flex-1 min-h-[500px] rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 bg-neutral-800/80 flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-6 h-6 text-neutral-300 animate-spin" />
                <p className="text-sm text-neutral-300">
                  Loading documentation...
                </p>
              </div>
            )}
            <iframe
              title="Documentation"
              src={ORCANIUM_DOCS_URL}
              className={`w-full flex-1 min-h-[500px] rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 [color-scheme:light] bg-white ${state === "loading" ? "hidden" : ""}`}
              sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
              referrerPolicy="no-referrer-when-downgrade"
              onLoad={() => setState("loaded")}
              onError={() => setState("error")}
            />
          </>
        )}
      </div>
    </div>
  );
};

export default DocumentationPage;
