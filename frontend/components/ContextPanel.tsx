import type { ScenarioDetail } from "@/lib/api";

export default function ContextPanel({ scenario }: { scenario: ScenarioDetail }) {
  const persona = scenario.persona ?? {};

  return (
    <aside className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900 p-4 text-sm space-y-4">
      <div>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-neutral-900 dark:text-neutral-100">
            {scenario.name}
          </h3>
          <span className="text-xs text-neutral-400 capitalize">{scenario.difficulty}</span>
        </div>
        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{scenario.description}</p>
      </div>

      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
          The situation
        </div>
        <p className="mt-1 leading-relaxed text-neutral-700 dark:text-neutral-200">
          {scenario.context}
        </p>
      </div>

      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
          Your goal
        </div>
        <p className="mt-1 leading-relaxed text-neutral-700 dark:text-neutral-200">
          {scenario.goal}
        </p>
      </div>

      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
          Who you&rsquo;re talking to
        </div>
        <p className="mt-1 leading-relaxed text-neutral-700 dark:text-neutral-200">
          {persona.name}, {persona.role} at {persona.company}
        </p>
        <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">
          {persona.personality}
        </p>
      </div>

      {(scenario.tips?.length ?? 0) > 0 && (
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
            Tips to succeed
          </div>
          <ul className="mt-1 space-y-1.5">
            {scenario.tips.map((tip, i) => (
              <li key={i} className="flex gap-2 text-neutral-600 dark:text-neutral-300 leading-relaxed">
                <span className="text-emerald-600 shrink-0">+</span>
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}
