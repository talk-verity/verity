import type { ScenarioDetail } from "@/lib/api";
import { CheckIcon, SparklesIcon } from "@/components/Icons";

export default function ContextPanel({ scenario }: { scenario: ScenarioDetail }) {
  const persona = scenario.persona ?? {};
  const initial = persona.name?.charAt(0) ?? "?";
  const role = [persona.role, persona.company].filter(Boolean).join(" at ");

  return (
    <aside className="flex w-full flex-col gap-7">
      <section className="flex flex-col gap-5">
        <h2 className="text-[12px] font-bold tracking-[1.2px] text-muted">
          MEET YOUR PARTNER
        </h2>

        <div className="flex items-center gap-[14px]">
          <div className="flex size-[62px] shrink-0 items-center justify-center rounded-full bg-line text-[34px] font-semibold leading-none text-ink">
            {initial}
          </div>
          <div className="min-w-0">
            <p className="text-[18px] font-medium leading-6 text-ink">{persona.name}</p>
            <p className="mt-1 text-[11px] leading-5 text-muted">{role}</p>
          </div>
        </div>

        {scenario.context && (
          <p className="text-[14px] leading-[1.8] text-muted">{scenario.context}</p>
        )}
      </section>

      <section className="flex flex-col gap-3 rounded-xl border border-line bg-mint p-6">
        <SparklesIcon size={24} className="text-forest" />
        <h2 className="text-[18px] font-bold leading-6 text-ink">
          Your conversation goal
        </h2>
        <p className="text-[18px] font-medium leading-[26px] text-ink">
          {scenario.goal}
        </p>
      </section>

      {(scenario.tips?.length ?? 0) > 0 && (
        <section>
          <h2 className="text-[17px] font-medium leading-6 text-ink">
            A few gentle pointers
          </h2>
          <ul className="mt-2 flex flex-col gap-2">
            {scenario.tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-[14px]">
                <CheckIcon size={18} className="mt-0.5 shrink-0 text-forest" />
                <span className="text-[12px] leading-[1.8] text-muted">{tip}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </aside>
  );
}
