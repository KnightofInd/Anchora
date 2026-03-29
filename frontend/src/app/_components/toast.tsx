"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

type ToastVariant = "success" | "error" | "info";

interface ToastItem {
  id: string;
  title: string;
  message?: string;
  variant: ToastVariant;
}

interface ToastInput {
  title: string;
  message?: string;
  variant?: ToastVariant;
}

interface ToastContextValue {
  showToast: (toast: ToastInput) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TOAST_STYLES: Record<
  ToastVariant,
  {
    wrapper: string;
    icon: string;
    iconColor: string;
  }
> = {
  success: {
    wrapper: "border-green-200 bg-green-50 text-green-800",
    icon: "check_circle",
    iconColor: "text-green-600",
  },
  error: {
    wrapper: "border-red-200 bg-red-50 text-red-800",
    icon: "error",
    iconColor: "text-red-600",
  },
  info: {
    wrapper: "border-blue-200 bg-blue-50 text-blue-800",
    icon: "info",
    iconColor: "text-blue-600",
  },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((toast: ToastInput) => {
    const id = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
    const next: ToastItem = {
      id,
      title: toast.title,
      message: toast.message,
      variant: toast.variant ?? "info",
    };

    setToasts((prev) => [...prev, next]);

    setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
    }, 4000);
  }, []);

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed right-4 top-4 z-[100] flex w-[min(92vw,360px)] flex-col gap-2">
        {toasts.map((toast) => {
          const style = TOAST_STYLES[toast.variant];
          return (
            <div
              key={toast.id}
              className={`rounded-xl border px-3 py-2 shadow-lg backdrop-blur ${style.wrapper}`}
            >
              <div className="flex items-start gap-2">
                <span className={`material-symbols-outlined text-[18px] ${style.iconColor}`}>
                  {style.icon}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold leading-tight">{toast.title}</p>
                  {toast.message && <p className="mt-0.5 text-xs opacity-90">{toast.message}</p>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const value = useContext(ToastContext);
  if (!value) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return value;
}
