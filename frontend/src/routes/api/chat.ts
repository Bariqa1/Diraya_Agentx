import { createFileRoute } from "@tanstack/react-router";

import { buildSystemPrompt, loadDirayaContext } from "@/lib/ai/diraya-prompt.server";

type ChatMessage = { role: "user" | "assistant"; content: string };

type ChatBody = { messages?: unknown };

function isChatMessage(value: unknown): value is ChatMessage {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as { role?: unknown; content?: unknown };
  return (
    (candidate.role === "user" || candidate.role === "assistant") &&
    typeof candidate.content === "string" &&
    candidate.content.trim().length > 0
  );
}

export const Route = createFileRoute("/api/chat")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const body = (await request.json().catch(() => ({}))) as ChatBody;
        const messages = Array.isArray(body.messages) ? body.messages.filter(isChatMessage) : [];
        if (messages.length === 0) {
          return new Response("Messages are required", { status: 400 });
        }

        const apiKey = process.env["LOVABLE_API_KEY"];
        if (!apiKey) {
          // Required environment variable for the AI integration.
          return new Response("Missing LOVABLE_API_KEY", { status: 500 });
        }

        const systemPrompt = buildSystemPrompt(await loadDirayaContext());

        const upstream = await fetch("https://ai.gateway.lovable.dev/v1/responses", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Lovable-API-Key": apiKey,
            "X-Lovable-AIG-SDK": "fetch",
          },
          body: JSON.stringify({
            model: "openai/gpt-6-astra",
            stream: true,
            store: false,
            reasoning: { effort: "low" },
            input: [
              { role: "system", content: [{ type: "input_text", text: systemPrompt }] },
              ...messages.slice(-20).map((message) => ({
                role: message.role,
                content: [
                  {
                    type: message.role === "assistant" ? "output_text" : "input_text",
                    text: message.content,
                  },
                ],
              })),
            ],
          }),
        });

        if (!upstream.ok || !upstream.body) {
          const detail = await upstream.text().catch(() => "");
          return new Response(detail || "AI request failed", { status: upstream.status || 502 });
        }

        const decoder = new TextDecoder();
        const encoder = new TextEncoder();
        const reader = upstream.body.getReader();
        let buffer = "";

        const stream = new ReadableStream<Uint8Array>({
          async pull(controller) {
            while (true) {
              const { done, value } = await reader.read();
              if (done) {
                controller.close();
                return;
              }

              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split("\n");
              buffer = lines.pop() ?? "";
              let text = "";

              for (const line of lines) {
                if (!line.startsWith("data:")) continue;
                const payload = line.slice(5).trim();
                if (!payload || payload === "[DONE]") continue;
                try {
                  const event = JSON.parse(payload) as { type?: string; delta?: string };
                  if (event.type === "response.output_text.delta" && typeof event.delta === "string") {
                    text += event.delta;
                  }
                } catch {
                  // ignore partial/unparseable events
                }
              }

              if (text) {
                controller.enqueue(encoder.encode(text));
                return;
              }
            }
          },
          cancel(reason) {
            return reader.cancel(reason);
          },
        });

        return new Response(stream, {
          headers: {
            "Content-Type": "text/plain; charset=utf-8",
            "Cache-Control": "no-store",
          },
        });
      },
    },
  },
});
