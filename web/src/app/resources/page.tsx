"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { ResourceCard, TYPE_META } from "@/components/resources";
import { EmptyState, ErrorState, PageHeader, PageSkeleton } from "@/components/ui";
import { useApi } from "@/lib/api";
import type { Resource } from "@/lib/types";

const selectCls = "h-8 rounded-lg border border-border bg-surface px-2 text-[13px] focus:border-accent focus:outline-none";

function ResourcesInner() {
  const params = useSearchParams();
  const focus = params.get("focus");
  const [type, setType] = useState(params.get("type") ?? "");
  const [level, setLevel] = useState("");
  const [cost, setCost] = useState("");
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);
  const qs = new URLSearchParams(Object.entries({ type, level, cost, q: debounced }).filter(([, v]) => v)).toString();
  const { data, error, loading, reload } = useApi<Resource[]>(`/resources${qs ? `?${qs}` : ""}`);
  useEffect(() => {
    if (focus && data) document.getElementById(`r-${focus}`)?.scrollIntoView({ block: "center" });
  }, [focus, data]);
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    (data ?? []).forEach((r) => (c[r.type] = (c[r.type] ?? 0) + 1));
    return c;
  }, [data]);

  return (
    <div className="fade-in">
      <PageHeader
        eyebrow="Resource library"
        title="Curated learning resources"
        description="Videos, books, official docs, courses, papers and interactive tools, each reviewed and linked to the lessons that use it. Free resources are preferred when quality is comparable. Paid and audit-only resources are labelled."
      />
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title, author, provider…" aria-label="Search resources" className={`${selectCls} w-64 max-w-full`} />
        <select value={type} onChange={(e) => setType(e.target.value)} aria-label="Type" className={selectCls}>
          <option value="">All types</option>
          {Object.entries(TYPE_META).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <select value={level} onChange={(e) => setLevel(e.target.value)} aria-label="Level" className={selectCls}>
          <option value="">All levels</option>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
        <select value={cost} onChange={(e) => setCost(e.target.value)} aria-label="Cost" className={selectCls}>
          <option value="">Any cost</option>
          <option value="free">Free</option>
          <option value="audit">Free to audit</option>
          <option value="freemium">Free tier</option>
          <option value="paid">Paid</option>
        </select>
        {data && (
          <span className="text-xs text-fg-3">
            {data.length} resources{type ? "" : ` · ${Object.entries(counts).map(([k, n]) => `${n} ${TYPE_META[k as Resource["type"]].label.toLowerCase()}`).join(", ")}`}
          </span>
        )}
      </div>
      {loading && !data ? (
        <PageSkeleton />
      ) : error ? (
        <ErrorState error={error} onRetry={reload} />
      ) : !data?.length ? (
        <EmptyState title="No resources match these filters" />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {data.map((r) => (
            <div key={r.id} id={`r-${r.id}`} className={focus === r.id ? "rounded-xl ring-2 ring-accent" : ""}>
              <ResourceCard r={r} />
              {r.lessons && r.lessons.length > 0 && (
                <p className="mt-1.5 px-1 text-xs text-fg-3">
                  Used in:{" "}
                  {r.lessons.slice(0, 4).map((l, i) => (
                    <span key={l.id}>
                      {i > 0 && " · "}
                      <Link href={`/lessons/${l.id}`} className="hover:text-accent-text hover:underline">{l.title}</Link>
                    </span>
                  ))}
                  {r.lessons.length > 4 && ` +${r.lessons.length - 4} more`}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ResourcesPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <ResourcesInner />
    </Suspense>
  );
}
