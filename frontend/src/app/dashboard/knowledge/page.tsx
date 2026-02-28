"use client";

import { useState, useRef, FormEvent, DragEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "@/lib/api";

interface Document {
  id: string;
  title: string;
  source: string;
  created_at: string;
  meta: { size_bytes?: number; content_type?: string; filename?: string };
}

interface SearchResult {
  id: string;
  filename: string;
  content_preview: string;
  similarity: number;
}

const FILE_ICONS: Record<string, { icon: string; bg: string; fg: string }> = {
  pdf:  { icon: "picture_as_pdf", bg: "bg-red-100",  fg: "text-red-600" },
  txt:  { icon: "article",        bg: "bg-slate-100", fg: "text-slate-600" },
  md:   { icon: "description",    bg: "bg-blue-100",  fg: "text-blue-600" },
  docx: { icon: "description",    bg: "bg-blue-100",  fg: "text-blue-600" },
};

function fileIconFor(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  return FILE_ICONS[ext] ?? { icon: "insert_drive_file", bg: "bg-slate-100", fg: "text-slate-600" };
}

export default function KnowledgePage() {
  const fileRef    = useRef<HTMLInputElement>(null);
  const qc         = useQueryClient();
  const [dragging, setDragging]     = useState(false);
  const [uploadMsg, setUploadMsg]   = useState("");
  const [query, setQuery]           = useState("");
  const [results, setResults]       = useState<SearchResult[]>([]);
  const [searched, setSearched]     = useState(false);
  const [searching, setSearching]   = useState(false);
  const [searchError, setSearchError] = useState("");

  const { data: docsData, isLoading: docsLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentsApi.list(),
  });
  const allDocs: Document[] = docsData?.data ?? [];

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return documentsApi.upload(form);
    },
    onSuccess: (res) => {
      setUploadMsg(`Uploaded: ${res.data?.filename ?? "document"}`);
      if (fileRef.current) fileRef.current.value = "";
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ?? "Upload failed.";
      setUploadMsg(`Error: ${msg}`);
    },
  });

  function triggerUpload(file?: File) {
    const f = file ?? fileRef.current?.files?.[0];
    if (!f) return;
    setUploadMsg("");
    uploadMutation.mutate(f);
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) triggerUpload(file);
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearchError("");
    setResults([]);
    setSearched(false);
    try {
      const res = await documentsApi.search(query);
      setResults(res.data ?? []);
      setSearched(true);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Search failed.";
      setSearchError(typeof msg === "string" ? msg : "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-slate-900">AI Knowledge Repository</h1>
          <p className="text-sm text-slate-500 mt-0.5">Upload documents and perform semantic search across the knowledge base.</p>
        </div>
        <button className="flex items-center gap-1.5 h-9 px-4 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 text-sm font-medium transition-colors shadow-sm">
          <span className="material-symbols-outlined text-base leading-none">tune</span>
          Filter
        </button>
        <button className="flex items-center gap-1.5 h-9 px-4 rounded-xl bg-[#1e3fae] hover:bg-[#162f85] text-white text-sm font-semibold shadow-sm shadow-[#1e3fae]/20 transition-colors">
          <span className="material-symbols-outlined text-base leading-none">add</span>
          New Framework
        </button>
      </div>

      {/* Upload zone */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <h2 className="text-[15px] font-semibold text-slate-800 mb-4">Upload Document</h2>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`relative rounded-2xl border-2 border-dashed transition-all duration-200 cursor-pointer flex flex-col items-center justify-center gap-3 py-12
            ${dragging
              ? "border-[#1e3fae]/50 bg-[#1e3fae]/10 scale-[1.02]"
              : "border-[#1e3fae]/30 bg-[#1e3fae]/5 hover:border-[#1e3fae]/50 hover:bg-[#1e3fae]/10"}`}
          onClick={() => fileRef.current?.click()}
        >
          <div className="p-4 rounded-full bg-white shadow-sm">
            <span className={`material-symbols-outlined text-4xl transition-all duration-200 ${dragging ? "text-[#1e3fae] scale-110" : "text-[#1e3fae]/60"}`}>
              cloud_upload
            </span>
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-700">Drag &amp; drop files here</p>
            <p className="text-xs text-slate-400 mt-0.5">PDF, TXT, MD, DOCX supported</p>
          </div>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); fileRef.current?.click(); }}
            className="h-9 px-5 rounded-xl bg-[#1e3fae] hover:bg-[#162f85] text-white text-xs font-semibold transition-colors shadow-sm"
          >
            Browse Files
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.txt,.md,.docx"
            className="hidden"
            onChange={() => triggerUpload()}
          />
        </div>

        {uploadMutation.isPending && (
          <div className="mt-3 flex items-center gap-2 text-sm text-[#1e3fae]">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            Uploading…
          </div>
        )}
        {uploadMsg && !uploadMutation.isPending && (
          <div className={`mt-3 flex items-center gap-2 text-sm ${uploadMsg.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>
            <span className="material-symbols-outlined text-base">{uploadMsg.startsWith("Error") ? "error" : "check_circle"}</span>
            {uploadMsg}
          </div>
        )}
      </div>

      {/* Document Library */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[15px] font-semibold text-slate-800">Document Library</h2>
          <span className="text-xs text-slate-400">{allDocs.length} document{allDocs.length !== 1 ? "s" : ""}</span>
        </div>
        {docsLoading ? (
          <div className="py-6 text-center text-sm text-slate-400">Loading…</div>
        ) : allDocs.length === 0 ? (
          <div className="py-8 text-center">
            <span className="material-symbols-outlined text-3xl text-slate-300">library_books</span>
            <p className="text-sm text-slate-400 mt-2">No documents uploaded yet.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {allDocs.map((doc) => {
              const fi = fileIconFor(doc.source || doc.title);
              const sizeKb = doc.meta?.size_bytes ? Math.round(doc.meta.size_bytes / 1024) : null;
              const date = new Date(doc.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
              return (
                <div key={doc.id} className="flex items-center gap-3 px-4 py-3 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50 transition-all group">
                  <div className={`p-2 rounded-lg shrink-0 ${fi.bg}`}>
                    <span className={`material-symbols-outlined text-base leading-none ${fi.fg}`}>{fi.icon}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-semibold text-slate-800 truncate">{doc.title}</p>
                    <p className="text-[11px] text-slate-400 mt-0.5 font-mono">{doc.id.slice(0, 8)}…</p>
                  </div>
                  <div className="text-right shrink-0">
                    {sizeKb && <p className="text-[11px] text-slate-400">{sizeKb} KB</p>}
                    <p className="text-[11px] text-slate-300">{date}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Search zone */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[15px] font-semibold text-slate-800">Search Knowledge Base</h2>
          <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-green-700 bg-green-100 px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            Index Active
          </span>
        </div>

        <form onSubmit={handleSearch} className="relative">
          <span className="material-symbols-outlined text-slate-400 text-lg absolute left-4 top-1/2 -translate-y-1/2">search</span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by meaning, topic, or keyword…"
            className="w-full h-14 pl-12 pr-24 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e3fae]/30 focus:border-[#1e3fae]/40 focus:bg-white transition-all"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-1 rounded-lg bg-white border border-slate-200 text-[10px] font-mono text-slate-400 shadow-sm">
              ⌘K
            </kbd>
            <button
              type="submit"
              disabled={searching}
              className="h-9 px-4 rounded-lg bg-[#1e3fae] hover:bg-[#162f85] text-white text-xs font-semibold transition-colors disabled:opacity-60"
            >
              {searching ? "…" : "Search"}
            </button>
          </div>
        </form>

        {searchError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-red-600">
            <span className="material-symbols-outlined text-base">error</span>
            {searchError}
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="mt-5 space-y-3">
            {results.map((r) => {
              const fi = fileIconFor(r.filename);
              const pct = Math.round(r.similarity * 100);
              const matchColor = pct >= 70 ? "bg-green-100 text-green-700" : pct >= 40 ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500";
              return (
                <div key={r.id} className="group rounded-xl border border-slate-100 hover:border-slate-200 bg-white hover:bg-slate-50 p-4 transition-all">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg shrink-0 ${fi.bg}`}>
                      <span className={`material-symbols-outlined text-lg leading-none ${fi.fg}`}>{fi.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <p className="text-[13px] font-semibold text-slate-800 truncate">{r.filename}</p>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${matchColor}`}>
                          {pct}% match
                        </span>
                      </div>
                      {/* Excerpt */}
                      <div className="mt-2 bg-slate-50 border-l-2 border-[#1e3fae]/40 pl-3 py-1.5 rounded-r-lg">
                        <p className="text-xs text-slate-500 italic leading-relaxed line-clamp-3">{r.content_preview}</p>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {searched && !searching && !searchError && results.length === 0 && (
          <div className="mt-6 text-center">
            <span className="material-symbols-outlined text-3xl text-slate-300">search_off</span>
            <p className="text-sm text-slate-400 mt-2">No results found for "{query}"</p>
          </div>
        )}
      </div>
    </div>
  );
}


