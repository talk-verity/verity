// Line-art symbols exported from the Figma "Home" frame. Each symbol is a
// composition of the original vector layers, positioned with the frame's insets.

type Part = {
  src: string;
  top: string;
  right: string;
  bottom: string;
  left: string;
};

const SYMBOLS: Record<string, Part[]> = {
  networking: [
    { src: "/figma/15430193-a584-4f30-b4d8-6976d8a67d7c.svg", top: "22.92%", right: "35.42%", bottom: "33.33%", left: "18.75%" },
    { src: "/figma/0d42ac28-3951-4dff-8c89-f199cf0e9ff7.svg", top: "41.67%", right: "18.75%", bottom: "18.75%", left: "39.58%" },
    { src: "/figma/1fdcfebf-d3a0-4a63-85b4-9ab83e07c16e.svg", top: "38.02%", right: "31.77%", bottom: "54.69%", left: "60.94%" },
  ],
  coworker: [
    { src: "/figma/b7358d4a-702f-44a7-8624-f89abe83ee6f.svg", top: "18.75%", right: "37.5%", bottom: "58.33%", left: "37.5%" },
    { src: "/figma/64f43b11-67c5-40a4-b62f-e44804bd4677.svg", top: "33.33%", right: "55.21%", bottom: "19.79%", left: "14.58%" },
    { src: "/figma/a5b01929-afc4-405c-9f47-6e9d503adc91.svg", top: "33.33%", right: "14.58%", bottom: "19.79%", left: "55.21%" },
  ],
  standup: [
    { src: "/figma/0d524dff-3538-452d-9998-61bc15b692fd.svg", top: "14.58%", right: "30.21%", bottom: "63.54%", left: "30.21%" },
    { src: "/figma/a53ff025-403e-4182-9e02-9475b9a2a88d.svg", top: "45.83%", right: "30.21%", bottom: "17.71%", left: "30.21%" },
  ],
  feedback: [
    { src: "/figma/08951e03-3ff4-47a6-a28f-32888bf010af.svg", top: "35.42%", right: "18.75%", bottom: "17.71%", left: "39.58%" },
    { src: "/figma/b5434959-b2cd-4b83-b45f-1f88a2225f4d.svg", top: "19.79%", right: "28.13%", bottom: "25%", left: "18.75%" },
  ],
};

export function symbolForScenario(scenarioId: string): keyof typeof SYMBOLS {
  if (scenarioId === "networking_event") return "networking";
  if (scenarioId === "job_interview") return "coworker";
  if (scenarioId === "workplace_conflict") return "coworker";
  if (scenarioId === "promotion_discussion") return "feedback";
  if (scenarioId === "performance_review") return "feedback";
  return "standup";
}

export default function ScenarioSymbol({ kind }: { kind: keyof typeof SYMBOLS }) {
  return (
    <div aria-hidden="true" className="relative size-[72px] shrink-0">
      {SYMBOLS[kind].map((part, index) => (
        <div
          key={index}
          className="absolute bg-contain bg-center bg-no-repeat"
          style={{
            top: part.top,
            right: part.right,
            bottom: part.bottom,
            left: part.left,
            backgroundImage: `url(${part.src})`,
          }}
        />
      ))}
    </div>
  );
}
