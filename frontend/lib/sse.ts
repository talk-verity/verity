export type StreamEvent = { event: string; data: string };

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
