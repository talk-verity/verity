export type StreamEvent = { event: string; data: string };

type MicQuality = {
  score: number;
  quality: string;
  recognized: boolean;
  rms_db: number | null;
};

export type VoiceStreamEvent =
  | { event: "error"; message: string }
  | { event: "warning" | "transcription" | "ai_response"; data: string }
  | { event: "mic_quality"; data: MicQuality }
  | { event: "audio"; data: string }
  | { event: "done" }
  | { event: "unknown" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isText(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

const BASE64_PATTERN = /^[A-Za-z0-9+/]*={0,2}$/;

/** Reject malformed voice-stream payloads before they reach React state or audio decoding. */
export function parseVoiceEvent({ event, data }: StreamEvent): VoiceStreamEvent {
  let payload: unknown;
  try {
    payload = JSON.parse(data);
  } catch {
    return { event: "unknown" };
  }
  if (!isRecord(payload)) return { event: "unknown" };

  switch (event) {
    case "error":
      return isText(payload.message)
        ? { event: "error", message: payload.message }
        : { event: "unknown" };
    case "warning":
    case "transcription":
    case "ai_response":
      return isText(payload.data)
        ? { event, data: payload.data }
        : { event: "unknown" };
    case "mic_quality": {
      const quality = payload.data;
      if (
        !isRecord(quality) ||
        typeof quality.score !== "number" ||
        !Number.isFinite(quality.score) ||
        !isText(quality.quality) ||
        typeof quality.recognized !== "boolean" ||
        !(quality.rms_db === null || (typeof quality.rms_db === "number" && Number.isFinite(quality.rms_db)))
      ) {
        return { event: "unknown" };
      }
      return {
        event,
        data: {
          score: quality.score,
          quality: quality.quality,
          recognized: quality.recognized,
          rms_db: quality.rms_db,
        },
      };
    }
    case "audio":
      return isText(payload.data) && BASE64_PATTERN.test(payload.data)
        ? { event: "audio", data: payload.data }
        : { event: "unknown" };
    case "done":
      return { event: "done" };
    default:
      return { event: "unknown" };
  }
}

/** Retains the full unfinished frame across arbitrary network chunk boundaries. */
export class SSEParser {
  private buffer = "";
  push(chunk: string): StreamEvent[] {
    this.buffer += chunk;
    const result: StreamEvent[] = [];
    let match: RegExpExecArray | null;
    while ((match = /\r?\n\r?\n/.exec(this.buffer))) {
      const frame = this.buffer.slice(0, match.index);
      this.buffer = this.buffer.slice(match.index + match[0].length);
      let event = "message";
      const data: string[] = [];
      for (const line of frame.split(/\r?\n/)) {
        if (line.startsWith("event:")) event = line.slice(6).replace(/^ /, "");
        if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
      }
      if (data.length) result.push({ event, data: data.join("\n") });
    }
    if (this.buffer.length > 32 * 1024 * 1024) throw new Error("Voice response too large");
    return result;
  }
}
