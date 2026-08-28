import React, { useEffect, useRef } from "react";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  loading = false,
  onConfirm,
  onCancel,
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    dialogRef.current
      ?.querySelector<HTMLButtonElement>("[data-confirm]")
      ?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
      prev?.focus?.();
    };
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div
        ref={dialogRef}
        className="bg-stone-100 dark:bg-zinc-800 border border-zinc-200/60 dark:border-zinc-700/50 w-full max-w-md rounded-2xl shadow-2xl"
      >
        <div className="flex items-start gap-3 p-4 border-b border-zinc-200/60 dark:border-zinc-700/50">
          {destructive && (
            <div className="mt-0.5 shrink-0 text-rose-500 dark:text-rose-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h2 className="text-sm font-bold text-zinc-800 dark:text-zinc-100">
              {title}
            </h2>
            {description && (
              <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                {description}
              </p>
            )}
          </div>
          <button
            onClick={onCancel}
            className="p-1 text-neutral-300 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center justify-end gap-2 p-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-3 py-2 rounded-xl border border-zinc-200/60 dark:border-zinc-700/50 text-xs font-medium text-zinc-500 dark:text-neutral-300 hover:text-zinc-700 dark:hover:text-zinc-300 transition-all"
          >
            {cancelLabel}
          </button>
          <button
            data-confirm
            onClick={onConfirm}
            disabled={loading}
            className={`px-3 py-2 rounded-xl text-xs font-semibold text-white transition-all shadow-lg ${
              destructive
                ? "bg-rose-600 hover:bg-rose-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300"
                : "bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 disabled:text-neutral-300"
            }`}
          >
            {loading ? "..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
