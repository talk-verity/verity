"use client";

import type { ReportContent, TranscriptExample } from "@/lib/api";

export default function ReportView({ content }: { content: ReportContent }) {
  const metrics = content.metrics ?? {};
  const examples = content.transcript_examples ?? [];

  return (
    <div className="space-y-6">
      {content.timed_out && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-200">
          <div className="flex items-center gap-2 font-semibold text-red-800 dark:text-red-400">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
            </svg>
            Time Expired (5-Minute Limit)
          </div>
          <p className="mt-1 text-xs sm:text-sm text-red-700 dark:text-red-300">
            The 5-minute time limit expired before the conversation objective was completed. Review your transcript cues and recommendations on pacing below.
          </p>
        </div>
      )}
      <p className="text-sm text-neutral-600">
        {content.assessment_note || "This legacy report used unvalidated heuristics. Numerical scores are hidden."}
      </p>
      {content.rubric_observations && (
        <Section label="Practice prompts">
          <ul className="space-y-2 text-sm">
            {content.rubric_observations.map(item => <li key={item.criterion}>
              {item.criterion}: {item.observed ? "text cue found — review its meaning in context" : "no text cue found — review your transcript"}
            </li>)}
          </ul>
        </Section>
      )}

      {content.assessment_method === "transcript_observations_v1" && content.summary && (
        <p className="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
          {content.summary}
        </p>
      )}

      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Words" value={metrics.total_user_words ?? 0} />
        <MetricCard label="Words per response" value={metrics.avg_response_length ?? 0} />
        <MetricCard label="Filler sounds in transcript" value={metrics.filler_word_count ?? 0} />
        <MetricCard label="Turns" value={metrics.total_turns ?? 0} />
      </div>

      {(metrics.filler_words?.length ?? 0) > 0 && (
        <div>
          <div className="text-xs text-neutral-400 uppercase tracking-wide mb-2">
            Filler words detected
          </div>
          <div className="flex flex-wrap gap-1.5">
            {metrics.filler_words!.map((w, i) => (
              <span
                key={i}
                className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
              >
                {w}
              </span>
            ))}
          </div>
        </div>
      )}

      {content.goal_completion && (
        <Section label="Goal completion">
          <p className={`text-sm ${content.timed_out ? "text-red-700 dark:text-red-400 font-medium" : "text-neutral-700 dark:text-neutral-300 capitalize"}`}>
            {content.goal_completion}
          </p>
        </Section>
      )}

      {content.strengths?.length > 0 && (
        <Section label="Strengths">
          <ul className="space-y-1">
            {content.strengths.map((s, i) => (
              <li key={i} className="text-sm text-neutral-700 flex gap-2 dark:text-neutral-300">
                <span className="text-emerald-600 shrink-0">+</span>
                {s}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {content.weaknesses?.length > 0 && (
        <Section label="Areas to improve">
          <ul className="space-y-1">
            {content.weaknesses.map((w, i) => (
              <li key={i} className="text-sm text-neutral-700 flex gap-2 dark:text-neutral-300">
                <span className="text-amber-600 shrink-0">→</span>
                {w}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {examples.length > 0 && (
        <Section label="Transcript references">
          <div className="space-y-2">
            {examples.map((ex: TranscriptExample, i) => (
              <div key={i} className="rounded-xl bg-neutral-50 dark:bg-neutral-900 px-4 py-3">
                <span
                  className={`inline-block text-xs px-2 py-0.5 rounded-full mb-1 ${
                    ex.type === "strength"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {ex.label}
                </span>
                <p className="text-sm text-neutral-700 italic dark:text-neutral-300">
                  “{ex.quote}”
                </p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {content.recommendations?.length > 0 && (
        <Section label="Recommended next steps">
          <ul className="space-y-2">
            {content.recommendations.map((r, i) => (
              <li key={i} className="text-sm text-neutral-700 flex gap-2 dark:text-neutral-300">
                <span className="text-indigo-600 shrink-0">↗</span>
                {r}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {(content.suggested_responses?.length ?? 0) > 0 && (
        <Section label="Practice suggestions">
          <div className="space-y-2">
            {content.suggested_responses!.map((s, i) => (
              <div key={i} className="rounded-xl bg-neutral-50 dark:bg-neutral-900 px-4 py-3">
                {s.weakness && (
                  <span className="inline-block text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300 mb-1">
                    For: {s.weakness}
                  </span>
                )}
                <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">{s.response}</p>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-neutral-50 dark:bg-neutral-900 px-4 py-3">
      <div className="text-xs text-neutral-400 uppercase tracking-wide">{label}</div>
      <div className="text-lg font-medium mt-1">{value}</div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-neutral-400 uppercase tracking-wide mb-2">{label}</div>
      {children}
    </div>
  );
}
