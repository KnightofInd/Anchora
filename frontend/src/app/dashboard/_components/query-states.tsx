interface LoadingStateProps {
  label?: string;
}

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: string;
}

interface ErrorStateProps {
  title?: string;
  message: string;
  retryLabel?: string;
  onRetry?: () => void;
}

export function LoadingState({ label = "Loading..." }: LoadingStateProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500 text-sm shadow-sm">
      <div className="inline-flex items-center gap-2">
        <svg className="animate-spin h-4 w-4 text-[#1e3fae]" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        {label}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  icon = "inbox",
}: EmptyStateProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center shadow-sm">
      <span className="material-symbols-outlined text-3xl text-slate-300">{icon}</span>
      <p className="text-slate-700 text-sm font-semibold mt-2">{title}</p>
      <p className="text-slate-400 text-sm mt-1">{description}</p>
    </div>
  );
}

export function ErrorState({
  title = "Could not load data",
  message,
  retryLabel = "Try again",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="bg-white rounded-2xl border border-red-200 p-6 shadow-sm">
      <div className="flex items-start gap-3">
        <span className="material-symbols-outlined text-red-500">error</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-red-700">{title}</p>
          <p className="text-sm text-red-600 mt-1">{message}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 h-8 px-3 rounded-lg border border-red-300 text-red-700 hover:bg-red-50 text-xs font-semibold transition-colors"
            >
              {retryLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
