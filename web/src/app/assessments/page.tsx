"use client";

import { Briefcase, RotateCcw } from "lucide-react";
import { useState } from "react";
import { useStudyTimer } from "@/components/lesson-parts";
import { emptyAnswer, QuestionCard, type AnswerState } from "@/components/quiz";
import { Button, ButtonLink, Card, EmptyState, ErrorState, PageHeader, PageSkeleton, Tabs, pct } from "@/components/ui";
import { api, useApi } from "@/lib/api";
import type { QuizQuestion } from "@/lib/types";

type Mode = "revision" | "interview";

function Session({ questions, mode, onRestart }: { questions: QuizQuestion[]; mode: Mode; onRestart: () => void }) {
  const [answers, setAnswers] = useState<Record<string, AnswerState>>({});
  const [scores, setScores] = useState<Record<string, number>>({});
  const record = (q: QuizQuestion) => async (s: AnswerState) => {
    const r = await api<{ score: number }>(`/questions/${encodeURIComponent(q.id)}/attempt`, { method: "POST", json: { response: s.response, self_grade: s.selfGrade, mode } });
    setScores((x) => ({ ...x, [q.id]: r.score }));
  };
  const done = Object.keys(scores).length;
  const avg = done ? Object.values(scores).reduce((a, b) => a + b, 0) / done : null;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm text-fg-2">
        <span>{done}/{questions.length} answered{avg != null && ` · running score ${pct(avg)}`}</span>
        <Button size="sm" variant="ghost" onClick={onRestart}><RotateCcw className="size-3.5" /> New session</Button>
      </div>
      {questions.map((q, i) => (
        <QuestionCard key={q.id} q={q} index={i} state={answers[q.id] ?? emptyAnswer()} onChange={(s) => setAnswers((a) => ({ ...a, [q.id]: s }))} onRecord={record(q)} />
      ))}
      {done === questions.length && (
        <Card className="p-5">
          <p className="text-lg font-semibold">Session score: {pct(avg)}</p>
          <p className="mt-1 text-sm text-fg-2">{mode === "revision" ? "Low scores on a completed lesson flag it for revision automatically. Check your dashboard." : "Interview answers are scored like real interviews: depth, trade-offs and precision."}</p>
          <Button className="mt-3" onClick={onRestart}>Start another session</Button>
        </Card>
      )}
    </div>
  );
}

function Revision() {
  const [nonce, setNonce] = useState(0);
  const { data, error, loading, reload } = useApi<{ questions: QuizQuestion[]; reason: string | null }>(`/revision/session?n=10&_=${nonce}`);
  if (loading && !data) return <PageSkeleton />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data?.questions.length) return <EmptyState title="Revision mode is locked" action={<ButtonLink href="/curriculum" variant="primary">Go to curriculum</ButtonLink>}>{data?.reason}</EmptyState>;
  return <Session key={nonce} questions={data.questions} mode="revision" onRestart={() => setNonce(nonce + 1)} />;
}

function Interview() {
  const tracks = useApi<{ id: string; title: string; questions: number }[]>("/interview/tracks");
  const [track, setTrack] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const session = useApi<QuizQuestion[]>(track ? `/interview/${track}?n=6&_=${nonce}` : null);
  if (tracks.loading && !tracks.data) return <PageSkeleton />;
  if (tracks.error) return <ErrorState error={tracks.error} onRetry={tracks.reload} />;
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {tracks.data?.map((t) => (
          <button key={t.id} onClick={() => { setTrack(t.id); setNonce(nonce + 1); }} className={`rounded-xl border p-4 text-left transition-colors ${track === t.id ? "border-accent bg-accent-soft" : "border-border bg-surface hover:border-border-strong"}`}>
            <Briefcase className="size-4 text-fg-3" />
            <p className="mt-2 text-sm font-medium">{t.title}</p>
            <p className="text-xs text-fg-3">{t.questions} questions</p>
          </button>
        ))}
      </div>
      {track && session.loading && !session.data && <PageSkeleton />}
      {track && session.data && <Session key={`${track}-${nonce}`} questions={session.data} mode="interview" onRestart={() => setNonce(nonce + 1)} />}
    </div>
  );
}

export default function AssessmentsPage() {
  const [mode, setMode] = useState<Mode>("revision");
  useStudyTimer();
  return (
    <div className="fade-in">
      <PageHeader
        eyebrow="Assessments"
        title={mode === "revision" ? "Revision mode" : "Technical interview mode"}
        description={
          mode === "revision"
            ? "A cumulative session mixing questions from every lesson you've studied, weakest topics first. Answer before you see any explanation."
            : "Interview-style questions: Python, SQL, ML/DL, LLM architecture, RAG design, agents and AI system design."
        }
        actions={<Tabs value={mode} onChange={setMode} items={[{ value: "revision", label: "Revision" }, { value: "interview", label: "Interview" }]} />}
      />
      <div className="mx-auto max-w-3xl">{mode === "revision" ? <Revision /> : <Interview />}</div>
    </div>
  );
}
