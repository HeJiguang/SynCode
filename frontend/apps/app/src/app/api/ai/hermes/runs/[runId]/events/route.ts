import {
  assertHermesResourceId,
  hermesHeaders,
  hermesProxyErrorResponse,
  hermesUrl,
  resolveHermesRequestContext
} from "../../../../../../../lib/hermes-server";
import {
  parseSseEvent,
  recordSkillTelemetry,
  splitSseFrames,
  toSkillTelemetryEvent,
  type SkillTelemetryEvent
} from "../../../../../../../lib/skill-telemetry";

type RouteContext = { params: Promise<{ runId: string }> };

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function observingStream(
  context: Awaited<ReturnType<typeof resolveHermesRequestContext>>,
  runId: string,
  upstream: ReadableStream<Uint8Array>
) {
  const reader = upstream.getReader();
  const decoder = new TextDecoder();
  const events: SkillTelemetryEvent[] = [];
  let buffer = "";
  let sequence = 0;

  const collect = (text: string) => {
    buffer += text;
    const split = splitSseFrames(buffer);
    buffer = split.rest;
    for (const frame of split.frames) {
      const parsed = parseSseEvent(frame);
      if (parsed && events.length < 100) {
        const event = toSkillTelemetryEvent(parsed, runId, sequence);
        if (event) events.push(event);
      }
      sequence += 1;
    }
  };

  return new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          controller.enqueue(value);
          collect(decoder.decode(value, { stream: true }));
        }
        collect(decoder.decode());
        if (buffer.trim()) {
          const parsed = parseSseEvent(buffer);
          if (parsed && events.length < 100) {
            const event = toSkillTelemetryEvent(parsed, runId, sequence);
            if (event) events.push(event);
          }
        }
        controller.close();
        void recordSkillTelemetry(context, events);
      } catch (error) {
        controller.error(error);
      }
    },
    async cancel(reason) {
      await reader.cancel(reason);
      void recordSkillTelemetry(context, events);
    }
  });
}

export async function GET(request: Request, { params }: RouteContext) {
  try {
    const { runId: rawRunId } = await params;
    const runId = assertHermesResourceId(rawRunId, "运行 ID");
    const context = await resolveHermesRequestContext();
    const upstream = await fetch(hermesUrl(context, `/v1/runs/${encodeURIComponent(runId)}/events`), {
      headers: hermesHeaders(context),
      cache: "no-store",
      signal: request.signal
    });
    if (!upstream.ok || !upstream.body) {
      return new Response(await upstream.text(), {
        status: upstream.status,
        headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" }
      });
    }
    return new Response(observingStream(context, runId, upstream.body), {
      status: upstream.status,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no"
      }
    });
  } catch (error) {
    return hermesProxyErrorResponse(error, "连接 Hermes 事件流失败。");
  }
}
