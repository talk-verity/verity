"use client";

import Link from "next/link";
import type { ReportContent, TranscriptExample } from "@/lib/api";

export default function ReportView({ content }: { content: ReportContent }) {
  const metrics = content.metrics ?? {};
  const examples = content.transcript_examples ?? [];

  // A score is only meaningful when the assessment method is validated. The
  // current backend emits transcript observations with no overall score.
  const validatedScore =
    typeof content.overall_score === "number" &&
    content.assessment_method !== "legacy_heuristic" &&
    content.assessment_method !== "transcript_observations_v1"
      ? content.overall_score
      : null;

  const goalText = content.goal_completion || "Not assessed automatically";
  const duration = content.time_limit_seconds
    ? `${Math.round(content.time_limit_seconds / 60)} min session`
    : "Practice session";
  const fillerDetail = metrics.filler_words?.length
    ? `Cues found: ${metrics.filler_words.join(", ")}.`
    : "No filler sounds were detected in the transcript.";

  const cards: { title: string; value: string | number; summary: string; detail: string }[] = [
    {
      title: "Words spoken",
      value: metrics.total_user_words ?? 0,
      summary: "Transcript count",
      detail: "Total words in your recorded responses.",
    },
    {
      title: "Words per response",
      value: metrics.avg_response_length ?? 0,
      summary: "Transcript average",
      detail: "Average length of each of your turns.",
    },
    {
      title: "Filler sounds",
      value: metrics.filler_word_count ?? 0,
      summary: "Text cues found",
      detail: fillerDetail,
    },
    {
      title: "Turns",
      value: metrics.total_turns ?? 0,
      summary: "Your responses",
      detail: "Recorded turns in this conversation.",
    },
    {
      title: "Goal",
      value: content.timed_out ? "Time expired" : "Not assessed",
      summary: "Goal status",
      detail: goalText,
    },
  ];

  const strengthExample = examples.find(ex => ex.type === "strength");
  const practiceAgain = content.recommendations?.[0];

  return (
    <div className="flex flex-col gap-7">
      {content.timed_out && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-800">
          <p className="font-semibold">5-minute time limit reached</p>
          <p className="mt-1 text-xs leading-relaxed text-red-700">
            The objective was not completed in time. Review your transcript cues and pacing below.
          </p>
        </div>
      )}

      <header className="flex flex-col gap-2.5">
        <p className="whitespace-pre-wrap text-sm text-muted">
          {`Your feedback  /  ${content.scenario}  /  ${duration}`}
        </p>
        <h2 className="text-[36px] font-semibold leading-[46px] text-ink">
          {content.timed_out ? "Time ran out. Here’s what to try next." : "A snapshot of this practice."}
        </h2>
        <p className="text-[17px] leading-[26px] text-muted">
          One small thing to try next time.
        </p>
      </header>

      <section className="flex flex-col gap-6 rounded-[20px] bg-forest px-7 py-6 text-white lg:flex-row lg:items-center">
        <div className="w-full shrink-0 lg:w-[205px]">
          <p className="text-sm font-bold text-lime">Overall score</p>
          {validatedScore !== null ? (
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-[52px] font-semibold leading-none">{validatedScore}</span>
              <span className="text-[17px] text-[#d1e3d5]">/ 100</span>
            </div>
          ) : (
            <p className="mt-2 text-[26px] font-semibold leading-tight">Not assessed</p>
          )}
          <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-[#476b59]">
            {validatedScore !== null && (
              <div
                className="h-full rounded-full bg-lime"
                style={{ width: `${validatedScore}%` }}
              />
            )}
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <p className="text-lg font-bold text-lime">Goal status</p>
          <p className="mt-2 text-2xl font-medium leading-8">{goalText}</p>
          {content.summary && (
            <p className="mt-2 text-base leading-6 text-[#d1e3d5]">{content.summary}</p>
          )}
        </div>

        <div className="w-full shrink-0 text-sm lg:w-[180px]">
          <p className="text-[11px] font-bold uppercase text-[#d1e3d5]">{content.scenario}</p>
          <p className="mt-1 text-base font-medium">Practice session</p>
          <p className="mt-1 text-[13px] text-[#d1e3d5]">{content.persona}</p>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between gap-4">
          <h3 className="text-[26px] font-semibold leading-9 text-ink">How you came across</h3>
          <p className="shrink-0 text-sm text-muted">Transcript observations, not scores</p>
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          {cards.map(card => <MetricCard key={card.title} {...card} />)}
        </div>

        <div className="flex flex-col gap-1.5 pt-1">
          <div className="h-3 w-full overflow-hidden rounded-full bg-bar">
            {validatedScore !== null && (
              <div
                className="h-full rounded-full bg-forest"
                style={{ width: `${validatedScore}%` }}
              />
            )}
          </div>
          <div className="flex justify-between text-[11px] text-muted">
            <span>0</span>
            <span>{validatedScore === null ? "No validated score to plot" : "Validated assessment"}</span>
            <span>100</span>
          </div>
        </div>
      </section>

      {content.rubric_observations && content.rubric_observations.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">
            Practice prompts
          </h3>
          <ul className="grid gap-2 text-sm text-muted sm:grid-cols-2 lg:grid-cols-3">
            {content.rubric_observations.map(item => (
              <li key={item.criterion} className="rounded-xl border border-line bg-white px-4 py-3">
                <span className="font-medium text-ink">{item.criterion}</span>
                <span className="mt-1 block text-xs">
                  {item.observed ? "Text cue found — review its meaning in context" : "No text cue found — review your transcript"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="flex flex-col gap-3 rounded-2xl bg-[#edf2e9] p-6">
          <h3 className="text-xl font-bold leading-7 text-forest">Keep doing this</h3>
          <p className="text-[22px] font-semibold leading-[30px] text-ink">
            {content.strengths?.[0] || "Review the moments that kept the conversation moving."}
          </p>
          {strengthExample && (
            <p className="text-lg font-medium leading-[26px] text-forest">“{strengthExample.quote}”</p>
          )}
          <p className="text-base leading-6 text-muted">
            {content.assessment_note || "Text cues are review prompts, not quality scores."}
          </p>
        </section>

        <section className="flex flex-col gap-3 rounded-2xl border border-line bg-white p-6">
          <h3 className="text-xl font-bold leading-7 text-forest">One thing to try next</h3>
          <p className="text-[22px] font-semibold leading-[30px] text-ink">
            {practiceAgain || "Choose one concrete change for your next conversation."}
          </p>
          {content.suggested_responses?.[0] && (
            <p className="text-lg font-medium leading-[26px] text-forest">
              “{content.suggested_responses[0].response}”
            </p>
          )}
          <p className="text-base leading-6 text-muted">
            {content.weaknesses?.[0] || content.recommendations?.[1] || "Review your transcript and pick one skill to focus on."}
          </p>
        </section>
      </div>

      {examples.length > 0 && (
        <section>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted">
            Transcript references
          </h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {examples.map((ex: TranscriptExample, i) => (
              <div key={i} className="rounded-xl border border-line bg-white px-4 py-3">
                <span className={`inline-block rounded-full px-2 py-0.5 text-xs ${
                  ex.type === "strength"
                    ? "bg-mint text-forest"
                    : "bg-amber-50 text-amber-700"
                }`}>
                  {ex.label}
                </span>
                <p className="mt-1 text-sm italic leading-relaxed text-muted">“{ex.quote}”</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="flex flex-wrap items-center gap-4 border-t border-line pt-6">
        <Link
          href="/scenarios"
          className="flex h-[54px] items-center justify-center rounded-lg bg-forest px-6 text-base font-bold text-white"
        >
          Practice again
        </Link>
        <Link href="/scenarios" className="text-[15px] font-medium text-forest underline">
          Choose another scenario
        </Link>
        <p className="ml-auto text-[13px] text-muted">
          Progress comes from practice, not perfect scores.
        </p>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  summary,
  detail,
}: {
  title: string;
  value: string | number;
  summary: string;
  detail: string;
}) {
  return (
    <div className="flex min-h-[240px] flex-col gap-2 rounded-xl border border-line bg-white p-5">
      <p className="text-xl font-bold leading-7 text-ink">{title}</p>
      <p className={`font-semibold leading-11 text-forest ${
        typeof value === "number" ? "text-[34px]" : "text-xl"
      }`}>
        {value}
      </p>
      <p className="text-sm font-medium leading-5 text-forest">{summary}</p>
      <p className="text-sm leading-[21px] text-muted">{detail}</p>
    </div>
  );
}
