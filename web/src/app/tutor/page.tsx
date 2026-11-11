"use client";

import { Bot, CheckCircle2, Cpu, HelpCircle } from "lucide-react";
import Link from "next/link";
import { TutorChat } from "@/components/tutor-chat";
import { Badge, Card, ErrorState, PageHeader, PageSkeleton, cn } from "@/components/ui";
import { useApi } from "@/lib/api";

interface LockedStatus {
  revealed: false;
  assembled: number;
  total: number;
  parts: { order: number; assembled: boolean; lesson_id: string | null; lesson_title: string | null }[];
}
interface RevealedStatus {
  revealed: true;
  assembled: number;
  total: number;
  execution_allowed: boolean;
  provider: string;
  parts: { id: string; order: number; title: string; lesson_id: string; lesson_title: string; file: string; capability: string; passed: boolean }[];
}

function Locked({ s }: { s: LockedStatus }) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <div className="relative mx-auto mb-6 flex size-40 items-center justify-center">
        <svg viewBox="0 0 160 160" className="absolute inset-0" aria-hidden>
          {s.parts.map((p, i) => {
            const a0 = (i / s.total) * Math.PI * 2 - Math.PI / 2 + 0.06;
            const a1 = ((i + 1) / s.total) * Math.PI * 2 - Math.PI / 2 - 0.06;
            const r = 70;
            const d = `M ${80 + r * Math.cos(a0)} ${80 + r * Math.sin(a0)} A ${r} ${r} 0 0 1 ${80 + r * Math.cos(a1)} ${80 + r * Math.sin(a1)}`;
            return <path key={p.order} d={d} fill="none" strokeWidth={10} strokeLinecap="round" stroke={p.assembled ? "var(--accent)" : "var(--surface-2)"} />;
          })}
        </svg>
        <Cpu className={cn("size-12", s.assembled ? "text-accent" : "text-fg-3")} />
      </div>
      <p className="text-sm font-medium tabular-nums text-fg-2">{s.assembled} of {s.total} parts assembled</p>
      <h2 className="mt-2 text-xl font-semibold">Something is being built here</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-fg-2">
        It isn&apos;t ready yet, and it can&apos;t be installed. It gets assembled from the <strong>Workshop</strong> tasks inside your lessons. Each workshop you verify adds one part.
      </p>
      <p className="mx-auto mt-2 max-w-md text-sm text-fg-3">For now, the foundations are yours to learn without shortcuts.</p>
      <ol className="mx-auto mt-8 max-w-sm space-y-2 text-left">
        {s.parts.map((p) => (
          <li key={p.order} className="flex items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2 text-sm">
            {p.assembled ? <CheckCircle2 className="size-4 text-success" /> : <HelpCircle className="size-4 text-fg-3" />}
            <span className="text-fg-3">Part {p.order}</span>
            {p.assembled ? <Link href={`/lessons/${p.lesson_id}`} className="truncate hover:underline">{p.lesson_title}</Link> : <span className="text-fg-3">Not built yet</span>}
          </li>
        ))}
      </ol>
    </div>
  );
}

function Revealed({ s }: { s: RevealedStatus }) {
  return (
    <div className="grid gap-6 xl:grid-cols-3">
      <div className="space-y-4 xl:col-span-2">
        <Card className="border-accent/40 bg-accent-soft/40 p-5">
          <p className="text-sm font-semibold text-accent-text">You built this.</p>
          <p className="mt-1 text-sm text-fg-2">
            Every part of this tutor is code you wrote in the workshops: the tokenizer, chunker, vector maths, BM25, prompt builder, LLM client and RAG pipeline. It answers from the course material and cites its sources. If it gives a bad answer, you can debug it, because you know exactly how it works.
          </p>
        </Card>
        <Card className="p-5">
          {!s.execution_allowed ? (
            <p className="text-sm text-warning">The tutor runs your workspace code, so it only runs in local mode (AUTH_MODE=local).</p>
          ) : (
            <TutorChat />
          )}
        </Card>
      </div>
      <aside className="space-y-4">
        <Card className="p-5">
          <p className="text-sm font-semibold">Generation</p>
          {s.provider === "none" || !s.provider ? (
            <p className="mt-1 text-sm text-fg-2">
              No model is configured, so answers are <strong>extractive</strong>: the best-matching course passage. Set <code className="font-mono text-xs">TUTOR_PROVIDER</code> (openai, anthropic or ollama) and <code className="font-mono text-xs">TUTOR_MODEL</code> in <code className="font-mono text-xs">api/.env</code>, then restart the API to get generated answers.
            </p>
          ) : (
            <p className="mt-1 text-sm text-fg-2">Using <Badge tone="accent">{s.provider}</Badge> through your own <code className="font-mono text-xs">generate.py</code>.</p>
          )}
        </Card>
        <Card className="p-5">
          <p className="mb-2 text-sm font-semibold">Your components</p>
          <ul className="space-y-2.5">
            {s.parts.map((p) => (
              <li key={p.id} className="text-sm">
                <p className="flex items-center gap-1.5 font-medium">
                  <CheckCircle2 className="size-3.5 text-success" /> {p.title}
                </p>
                <p className="ml-5 text-xs text-fg-3">
                  <code className="font-mono">{p.file}</code> · <Link href={`/lessons/${p.lesson_id}`} className="hover:underline">{p.lesson_title}</Link>
                </p>
                <p className="ml-5 text-xs text-fg-2">{p.capability}</p>
              </li>
            ))}
          </ul>
        </Card>
      </aside>
    </div>
  );
}

export default function TutorPage() {
  const { data, error, loading, reload } = useApi<LockedStatus | RevealedStatus>("/tutor/status");
  if (loading && !data) return <PageSkeleton />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data) return null;
  return (
    <div className="fade-in">
      <PageHeader
        eyebrow={<span className="inline-flex items-center gap-1"><Bot className="size-3.5" /> AI Tutor</span>}
        title={data.revealed ? "Your AI tutor" : "AI Tutor"}
        description={data.revealed ? "Grounded in the course and built by you. You can also open it from the sidebar of every lesson." : undefined}
      />
      {data.revealed ? <Revealed s={data} /> : <Locked s={data} />}
    </div>
  );
}
