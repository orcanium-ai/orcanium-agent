import React, { useState, useCallback, useEffect } from "react";
import { CheckCircle2, XCircle, X } from "lucide-react";

interface ToastMessage {
  id: number;
  text: string;
  type: "success" | "error";
}

let toastId = 0;
let addToastFn: ((text: string, type: "success" | "error") => void) | null =
  null;

export const toast = {
  success: (text: string) => addToastFn?.(text, "success"),
  error: (text: string) => addToastFn?.(text, "error"),
};

export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((text: string, type: "success" | "error") => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, text, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  useEffect(() => {
    addToastFn = addToast;
    return () => {
      addToastFn = null;
    };
  }, [addToast]);

  const remove = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[300] flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-start gap-2.5 p-3 rounded-xl border shadow-lg animate-fadeIn ${
            t.type === "success"
              ? "bg-emerald-100 dark:bg-emerald-900/80 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200"
              : "bg-rose-100 dark:bg-rose-900/80 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200"
          }`}
        >
          {t.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-500 dark:text-emerald-400" />
          ) : (
            <XCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500 dark:text-rose-400" />
          )}
          <p className="text-xs font-medium flex-1">{t.text}</p>
          <button
            onClick={() => remove(t.id)}
            className="p-0.5 opacity-60 hover:opacity-100 transition-opacity"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}
    </div>
  );
};
