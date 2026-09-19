export type DetectionSeverity = "critical" | "warning" | "safe";

export type YoloDetection = {
  id: string;
  className: string;
  label: { ar: string; en: string };
  confidence: number;
  timestamp: string;
  relativeTime: { ar: string; en: string };
  zone: string;
  severity: DetectionSeverity;
  box: { x: number; y: number; width: number; height: number };
};

export type YoloStreamPayload = {
  streamUrl: string;
  cameraId: string;
  zone: string;
  fps: number;
  detections: YoloDetection[];
};

// Future integration point. Set this only when a real, secured stream is available.
export const YOLO_STREAM_URL: string | null = null;

export const mockDetections: YoloDetection[] = [
  { id: "det-01", className: "NO HELMET", label: { ar: "عدم ارتداء الخوذة", en: "No Helmet" }, confidence: 96, timestamp: "2026-09-15T15:54:55Z", relativeTime: { ar: "منذ 5 ثوانٍ", en: "5 seconds ago" }, zone: "Zone C", severity: "critical", box: { x: 31, y: 25, width: 15, height: 48 } },
  { id: "det-02", className: "NO SAFETY VEST", label: { ar: "عدم ارتداء سترة السلامة", en: "No Safety Vest" }, confidence: 91, timestamp: "2026-09-15T15:54:48Z", relativeTime: { ar: "منذ 12 ثانية", en: "12 seconds ago" }, zone: "Zone A", severity: "warning", box: { x: 50, y: 28, width: 12, height: 42 } },
  { id: "det-03", className: "PERSON", label: { ar: "خوذة مكتشفة", en: "Helmet Detected" }, confidence: 98, timestamp: "2026-09-15T15:54:45Z", relativeTime: { ar: "منذ 15 ثانية", en: "15 seconds ago" }, zone: "Zone C", severity: "safe", box: { x: 66, y: 38, width: 15, height: 38 } },
  { id: "det-04", className: "SMOKE", label: { ar: "دخان محتمل", en: "Possible Smoke" }, confidence: 94, timestamp: "2026-09-15T15:54:31Z", relativeTime: { ar: "منذ 29 ثانية", en: "29 seconds ago" }, zone: "Zone C", severity: "critical", box: { x: 87, y: 7, width: 10, height: 25 } },
];