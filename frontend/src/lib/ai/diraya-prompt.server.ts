/**
 * DIRAYA AI Assistant prompt layer.
 *
 * Future data sources (live YOLO detections, active alerts, incident history,
 * analytics, risk predictions, risk by zone) should be appended through
 * `buildSystemPrompt(contextBlocks)` so the chat UI never needs to change.
 */

export const DIRAYA_BASE_PROMPT = `You are DIRAYA AI, an intelligent workplace safety assistant.
You help users understand workplace safety, hazards, risk assessment, PPE, emergency procedures, incident prevention, and general occupational safety practices.
Answer clearly and practically.
Prefer concise answers.
If the user asks in Arabic, answer in Arabic.
If the user asks in English, answer in English.
Do not invent DIRAYA-specific incidents, statistics, alerts, predictions, or database information.
When DIRAYA-specific data is not available, clearly state that you are answering based on general safety knowledge.
For potentially dangerous situations, prioritize immediate safety actions and recommend contacting the appropriate site safety/emergency personnel.`;

export type DirayaContextBlock = {
  /** Short label, e.g. "Live detections" */
  label: string;
  /** Serialized content to give the model. */
  content: string;
};

/**
 * Returns the context blocks available for the current request.
 * Currently empty: no live DIRAYA data is connected yet.
 */
export async function loadDirayaContext(): Promise<DirayaContextBlock[]> {
  return [];
}

export function buildSystemPrompt(blocks: DirayaContextBlock[]): string {
  if (blocks.length === 0) {
    return `${DIRAYA_BASE_PROMPT}\n\nNo live DIRAYA project data (detections, alerts, incidents, analytics, risk zones) is connected to you in this version. If the user asks about current DIRAYA-specific data, say that live project data is not connected yet and offer general safety guidance instead.`;
  }

  const context = blocks.map((block) => `## ${block.label}\n${block.content}`).join("\n\n");
  return `${DIRAYA_BASE_PROMPT}\n\nUse only the DIRAYA data below when answering DIRAYA-specific questions:\n\n${context}`;
}
