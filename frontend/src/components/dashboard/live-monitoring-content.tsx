import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  AlertOctagon,
  AlertTriangle,
  Camera,
  CheckCircle2,
  Clock,
  Cpu,
  Eye,
  Grid2X2,
  Maximize2,
  Play,
  Radio,
  RefreshCw,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Tv,
  Volume2,
  VolumeX,
  Wifi,
} from "lucide-react";

import telemetryData from "@/data/camera-telemetry.json";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Locale } from "@/lib/locale";

interface CameraConfig {
  id: string;
  name: { ar: string; en: string };
  zone: string;
  zoneTitle: { ar: string; en: string };
  videoSrc: string;
  fps: number;
  status: "online" | "warning" | "critical";
  activeDetections: number;
  riskSummary: { ar: string; en: string };
}

const CAMERAS: CameraConfig[] = [
  {
    id: "cam-01",
    name: { ar: "الكاميرا 01 — ورشة اللحام والقص", en: "Camera 01 — Welding & Cutting Bay" },
    zone: "ZONE_WELDING",
    zoneTitle: { ar: "منطقة اللحام", en: "Welding Bay" },
    videoSrc: "/videos/cam1.mp4",
    fps: 30.0,
    status: "critical",
    activeDetections: 3,
    riskSummary: { ar: "عدم ارتداء درع وجه وواقيات", en: "Missing Face Shield & Protectors" },
  },
  {
    id: "cam-02",
    name: { ar: "الكاميرا 02 — منطقة العمل والارتفاعات", en: "Camera 02 — Working at Height & Scaffold" },
    zone: "ZONE_HEIGHT",
    zoneTitle: { ar: "منطقة الارتفاعات", en: "Height Operations" },
    videoSrc: "/videos/cam2.mp4",
    fps: 30.0,
    status: "critical",
    activeDetections: 2,
    riskSummary: { ar: "نقص سترة الأمان وحزام التعليق", en: "Missing Safety Vest & Harness" },
  },
  {
    id: "cam-03",
    name: { ar: "الكاميرا 03 — مستودع التخزين ومحيط الخطر", en: "Camera 03 — Chemical Storage & Hazard Zone" },
    zone: "ZONE_STORAGE",
    zoneTitle: { ar: "مستودع الكيماويات", en: "Chemical Storage" },
    videoSrc: "/videos/cam3.mp4",
    fps: 25.0,
    status: "warning",
    activeDetections: 1,
    riskSummary: { ar: "اقتراب من محيط لوحة الخطر", en: "Proximity to Danger Signboard" },
  },
  {
    id: "cam-04",
    name: { ar: "الكاميرا 04 — محطة التشغيل والرافعات الثقيلة", en: "Camera 04 — Crane Operations & Heavy Bay" },
    zone: "ZONE_CRANE",
    zoneTitle: { ar: "نطاق عمل الرافعة", en: "Heavy Crane Bay" },
    videoSrc: "/videos/cam4.mp4",
    fps: 25.0,
    status: "online",
    activeDetections: 2,
    riskSummary: { ar: "رصد حركة وتشغيل آمن للرافعة", en: "Operational Crane Movement" },
  },
];

interface TelemetryEvent {
  id: string;
  cameraId: string;
  cameraName: { ar: string; en: string };
  zone: string;
  zoneTitle: { ar: string; en: string };
  timestamp: number;
  severity: "critical" | "warning" | "safe";
  missingPpe: string[];
  personDetected: boolean;
  fallDetected: boolean;
  zoneViolation: boolean;
  message: { ar: string; en: string };
  realTime?: string;
}

const copy = {
  ar: {
    title: "مركز المراقبة الحية وتحليل الكاميرات",
    subtitle: "بث حي متعدد للكاميرات الصناعية الأربعة مع كشف فوري لمعدات الوقاية ومراقبة محيط الخطر",
    liveBadge: "بث مباشر حي",
    activeStreams: "الكاميرات النشطة: 4/4",
    singleView: "عرض كاميرا مفردة",
    gridView: "شبكة 4 كاميرات (2×2)",
    detectedEvents: "شريط سجلات الذكاء الاصطناعي اللحظية",
    eventsSubtitle: "تدفق مباشر للأحداث المستخرجة من نماذج الرؤية الحاسوبية",
    filterAll: "الكل",
    filterCritical: "الحالات الحرجة",
    filterWarning: "التحذيرات",
    filterSafe: "الآمنة",
    resolution: "الدقة: 1080p FHD",
    latency: "الاستجابة: 14ms",
    clickToFocus: "انقر للتركيز على هذه الكاميرا",
    dispatchAlert: "إشعار مشرف السلامة الميداني",
    alertSent: "تم إرسال الإشعار اللحظي إلى المشرف بنجاح!",
    activeDetectionsLabel: "المخالفات النشطة",
    switchCameraLabel: "اختيار الكاميرا:",
    streamTelemetry: "بيانات تتبع البث",
    noEvents: "لا توجد أحداث مطابقة للفلتر المحدد.",
    onlineStatus: "متصل ويعمل",
  },
  en: {
    title: "Live Surveillance & Computer Vision Matrix",
    subtitle: "Real-time quad industrial CCTV monitoring with automated PPE compliance and hazard perimeter monitoring",
    liveBadge: "LIVE STREAM",
    activeStreams: "Active Streams: 4/4",
    singleView: "Single Focus View",
    gridView: "Quad 2×2 Grid View",
    detectedEvents: "Live AI Telemetry Stream",
    eventsSubtitle: "Real-time inference events extracted by active vision models",
    filterAll: "All",
    filterCritical: "Critical",
    filterWarning: "Warning",
    filterSafe: "Safe",
    resolution: "Resolution: 1080p FHD",
    latency: "Latency: 14ms",
    clickToFocus: "Click to focus on this camera",
    dispatchAlert: "Dispatch Alert to Safety Officer",
    alertSent: "Real-time alert dispatched to supervisor successfully!",
    activeDetectionsLabel: "Active Detections",
    switchCameraLabel: "Select Camera:",
    streamTelemetry: "Telemetry Stream",
    noEvents: "No events match the selected filter.",
    onlineStatus: "Online & Active",
  },
} as const;

export function LiveMonitoringContent({
  locale,
  embedded = false,
}: {
  locale: Locale;
  embedded?: boolean;
}) {
  const t = copy[locale];
  const arabic = locale === "ar";

  const [selectedCamId, setSelectedCamId] = useState<string>("cam-01");
  const [viewMode, setViewMode] = useState<"single" | "grid">("grid");
  const [filter, setFilter] = useState<"all" | "critical" | "warning" | "safe">("all");
  const [muted, setMuted] = useState<boolean>(true);
  const [alertDispatched, setAlertDispatched] = useState<boolean>(false);

  // Live rolling telemetry feed simulation
  const [streamEvents, setStreamEvents] = useState<TelemetryEvent[]>(() => {
    return (telemetryData as TelemetryEvent[]).slice(0, 8).map((ev) => ({
      ...ev,
      realTime: new Date().toLocaleTimeString(arabic ? "ar-SA" : "en-US", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
    }));
  });

  const eventIndexRef = useRef<number>(8);
  const logScrollRef = useRef<HTMLDivElement>(null);

  // Continuously stream new telemetry items from real dataset
  useEffect(() => {
    const rawList = telemetryData as TelemetryEvent[];
    if (!rawList.length) return;

    const interval = setInterval(() => {
      const nextItem = rawList[eventIndexRef.current % rawList.length]!;
      eventIndexRef.current += 1;

      const formattedItem: TelemetryEvent = {
        ...nextItem,
        id: `${nextItem.id}-${Date.now()}`,
        realTime: new Date().toLocaleTimeString(arabic ? "ar-SA" : "en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
      };

      setStreamEvents((prev) => [formattedItem, ...prev.slice(0, 40)]);
    }, 2200);

    return () => clearInterval(interval);
  }, [arabic]);

  const activeCam = CAMERAS.find((c) => c.id === selectedCamId) ?? CAMERAS[0]!;

  const filteredEvents = streamEvents.filter((ev) => {
    if (filter === "all") return true;
    return ev.severity === filter;
  });

  function handleDispatchAlert() {
    setAlertDispatched(true);
    setTimeout(() => setAlertDispatched(false), 3500);
  }

  return (
    <div className={cn(embedded ? "space-y-4" : "mx-auto max-w-[1680px] space-y-5 p-4 sm:p-5 xl:px-8 xl:py-6")} dir={arabic ? "rtl" : "ltr"}>
      {/* Header Bar */}
      <header className={cn("flex flex-col justify-between gap-4 border-b border-border/80 sm:flex-row sm:items-center", embedded ? "pb-3" : "pb-5")}>
        <div>
          <div className="flex items-center gap-2.5">
            {embedded ? (
              <h2 className={cn("text-xl font-bold text-foreground sm:text-2xl", !arabic && "font-display")}>
                {t.title}
              </h2>
            ) : (
              <h1 className={cn("text-2xl font-bold text-foreground sm:text-3xl", !arabic && "font-display")}>
                {t.title}
              </h1>
            )}
            <Badge variant="outline" className="gap-1 border-red-500/40 bg-red-500/10 text-red-500 text-[11px] font-bold">
              <span className="size-2 rounded-full bg-red-500 animate-ping" />
              {t.liveBadge}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{t.subtitle}</p>
        </div>

        {/* View Mode Switcher */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center rounded-lg border border-border bg-card p-1">
            <Button
              size="sm"
              variant={viewMode === "single" ? "default" : "ghost"}
              onClick={() => setViewMode("single")}
              className="gap-1.5 text-xs h-8"
            >
              <Tv className="size-3.5" />
              {t.singleView}
            </Button>
            <Button
              size="sm"
              variant={viewMode === "grid" ? "default" : "ghost"}
              onClick={() => setViewMode("grid")}
              className="gap-1.5 text-xs h-8"
            >
              <Grid2X2 className="size-3.5" />
              {t.gridView}
            </Button>
          </div>
        </div>
      </header>

      {/* Main Monitoring Section */}
      <div className="grid gap-5 xl:grid-cols-[1fr_390px]">
        {/* Left Column: Video Feeds */}
        <div className="space-y-4">
          {viewMode === "single" ? (
            /* Single Camera Primary View */
            <div className="space-y-3">
              {/* Camera Tabs */}
              <div className="flex flex-wrap items-center gap-2">
                {CAMERAS.map((cam) => {
                  const isSelected = cam.id === selectedCamId;
                  return (
                    <button
                      key={cam.id}
                      type="button"
                      onClick={() => setSelectedCamId(cam.id)}
                      className={cn(
                        "flex items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-medium transition-all",
                        isSelected
                          ? "border-primary bg-primary text-primary-foreground shadow-md shadow-primary/20"
                          : "border-border bg-card text-foreground hover:border-border/80 hover:bg-muted/50",
                      )}
                    >
                      <Camera className="size-3.5" />
                      <span>{cam.name[locale]}</span>
                      <span
                        className={cn(
                          "size-2 rounded-full",
                          cam.status === "critical"
                            ? "bg-red-500 animate-pulse"
                            : cam.status === "warning"
                            ? "bg-amber-400"
                            : "bg-emerald-400",
                        )}
                      />
                    </button>
                  );
                })}
              </div>

              {/* Main Player Viewport */}
              <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-border/90 bg-slate-950 shadow-2xl">
                {/* HUD Top Bar */}
                <div className="absolute inset-x-0 top-0 z-30 flex items-center justify-between bg-gradient-to-b from-black/85 via-black/40 to-transparent p-4 text-white">
                  <div className="flex items-center gap-2.5">
                    <span className="inline-flex items-center gap-1.5 rounded bg-red-600 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-white shadow">
                      <Radio className="size-3 animate-pulse" /> LIVE
                    </span>
                    <span className="font-semibold text-xs sm:text-sm drop-shadow">
                      {activeCam.name[locale]}
                    </span>
                    <span className="rounded bg-black/60 px-2 py-0.5 text-[11px] font-mono text-emerald-400 drop-shadow">
                      {activeCam.zone}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-xs font-mono drop-shadow">
                    <span className="rounded bg-black/60 px-2 py-1">1080p FHD</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => setMuted(!muted)}
                      className="size-7 rounded text-white hover:bg-white/20"
                    >
                      {muted ? <VolumeX className="size-3.5" /> : <Volume2 className="size-3.5" />}
                    </Button>
                  </div>
                </div>

                {/* Actual Hardware-Accelerated Video Stream */}
                <video
                  key={activeCam.id}
                  src={activeCam.videoSrc}
                  autoPlay
                  loop
                  muted={muted}
                  playsInline
                  className="size-full object-cover"
                />

                {/* HUD Bottom Bar */}
                <div className="absolute inset-x-0 bottom-0 z-30 flex items-center justify-between bg-gradient-to-t from-black/85 via-black/30 to-transparent p-3.5 text-xs text-white/90">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1 font-mono text-[11px] text-white/70">
                      <Clock className="size-3" />
                      {new Date().toLocaleTimeString(arabic ? "ar-SA" : "en-US")}
                    </span>
                    <span className="hidden sm:inline-flex items-center gap-1 rounded bg-black/50 px-2 py-0.5 text-[11px] text-amber-300">
                      <AlertTriangle className="size-3" />
                      {activeCam.riskSummary[locale]}
                    </span>
                  </div>
                  <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-400 border border-emerald-500/30">
                    {arabic ? "محرك الرؤية الحاسوبية نشط" : "Vision AI Engine Active"}
                  </span>
                </div>
              </div>

              {/* Mini Preview Strip */}
              <div className="grid grid-cols-4 gap-2.5 pt-1">
                {CAMERAS.map((cam) => (
                  <button
                    key={`strip-${cam.id}`}
                    type="button"
                    onClick={() => setSelectedCamId(cam.id)}
                    className={cn(
                      "group relative aspect-video overflow-hidden rounded-xl border transition-all text-start",
                      selectedCamId === cam.id
                        ? "border-primary ring-2 ring-primary/30"
                        : "border-border/80 opacity-75 hover:opacity-100",
                    )}
                  >
                    <video
                      src={cam.videoSrc}
                      autoPlay
                      loop
                      muted
                      playsInline
                      className="size-full object-cover pointer-events-none"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                    <span className="absolute bottom-1.5 start-2 text-[11px] font-bold text-white drop-shadow truncate max-w-[90%]">
                      {cam.id.toUpperCase()}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* 2x2 CCTV Quad Grid Mode */
            <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
              {CAMERAS.map((cam) => (
                <div
                  key={`grid-${cam.id}`}
                  onClick={() => {
                    setSelectedCamId(cam.id);
                    setViewMode("single");
                  }}
                  className="group relative aspect-video cursor-pointer overflow-hidden rounded-2xl border border-border/80 bg-slate-950 shadow-lg transition-all hover:border-primary hover:shadow-xl"
                >
                  {/* Tile Top HUD */}
                  <div className="absolute inset-x-0 top-0 z-20 flex items-center justify-between bg-gradient-to-b from-black/80 to-transparent p-2.5 text-white">
                    <div className="flex items-center gap-1.5">
                      <span className="inline-flex items-center gap-1 rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-bold">
                        <Radio className="size-2.5 animate-pulse" /> LIVE
                      </span>
                      <span className="text-xs font-semibold drop-shadow truncate max-w-[170px]">
                        {cam.name[locale]}
                      </span>
                    </div>
                    <span className="rounded bg-black/60 px-1.5 py-0.5 font-mono text-[10px] text-white/80">
                      1080p FHD
                    </span>
                  </div>

                  {/* Video */}
                  <video
                    src={cam.videoSrc}
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="size-full object-cover"
                  />

                  {/* Hover Overlay with click-to-focus prompt */}
                  <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
                    <span className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground shadow-lg">
                      <Maximize2 className="size-3.5" />
                      {t.clickToFocus}
                    </span>
                  </div>

                  {/* Tile Bottom Status */}
                  <div className="absolute inset-x-0 bottom-0 z-20 flex items-center justify-between bg-gradient-to-t from-black/80 to-transparent p-2 text-[11px] text-white/80">
                    <span className="truncate max-w-[70%]">{cam.riskSummary[locale]}</span>
                    <span
                      className={cn(
                        "size-2 rounded-full",
                        cam.status === "critical"
                          ? "bg-red-500 animate-pulse"
                          : cam.status === "warning"
                          ? "bg-amber-400"
                          : "bg-emerald-400",
                      )}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Live Telemetry Feed & Incident Dispatch */}
        <div className="flex flex-col gap-4 self-start">
          {/* Dispatch Supervisor Alert Card */}
          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="size-4 text-red-500" />
                <h3 className="text-sm font-bold text-foreground">{t.dispatchAlert}</h3>
              </div>
              <span className="size-2 rounded-full bg-emerald-500 animate-ping" />
            </div>

            {alertDispatched ? (
              <div className="mt-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-2.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 text-center animate-fade-in">
                {t.alertSent}
              </div>
            ) : (
              <Button
                onClick={handleDispatchAlert}
                variant="destructive"
                className="mt-3 w-full gap-2 text-xs font-bold shadow-md shadow-destructive/20 h-9"
              >
                <Send className="size-3.5" />
                {t.dispatchAlert}
              </Button>
            )}
          </div>

          {/* Real-time Telemetry Log Panel */}
          <div className="flex flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
            {/* Panel Header */}
            <div className="border-b border-border p-4 pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="size-4 text-primary" />
                  <h2 className="text-sm font-bold text-foreground">{t.detectedEvents}</h2>
                </div>
                <span className="rounded-full bg-primary/10 px-2 py-0.5 font-mono text-[11px] font-bold text-primary">
                  {filteredEvents.length}
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{t.eventsSubtitle}</p>

              {/* Filters */}
              <div className="mt-3 flex items-center gap-1.5">
                {(["all", "critical", "warning", "safe"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setFilter(mode)}
                    className={cn(
                      "rounded-lg px-2.5 py-1 text-[11px] font-medium transition-all",
                      filter === mode
                        ? "bg-primary text-primary-foreground font-bold shadow-sm"
                        : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    {mode === "all"
                      ? t.filterAll
                      : mode === "critical"
                      ? t.filterCritical
                      : mode === "warning"
                      ? t.filterWarning
                      : t.filterSafe}
                  </button>
                ))}
              </div>
            </div>

            {/* Scrolling Events Stream */}
            <div ref={logScrollRef} className="space-y-2 overflow-y-auto p-3 max-h-[250px]">
              {filteredEvents.length === 0 ? (
                <div className="py-6 text-center text-xs text-muted-foreground">{t.noEvents}</div>
              ) : (
                filteredEvents.map((ev) => {
                  const isCrit = ev.severity === "critical";
                  const isWarn = ev.severity === "warning";

                  return (
                    <div
                      key={ev.id}
                      className={cn(
                        "relative rounded-xl border p-2.5 text-xs transition-all animate-fade-in",
                        isCrit
                          ? "border-red-500/30 bg-red-500/5 dark:bg-red-950/20"
                          : isWarn
                          ? "border-amber-500/30 bg-amber-500/5 dark:bg-amber-950/20"
                          : "border-emerald-500/30 bg-emerald-500/5 dark:bg-emerald-950/20",
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={cn(
                              "rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
                              isCrit
                                ? "bg-red-500 text-white"
                                : isWarn
                                ? "bg-amber-500 text-black"
                                : "bg-emerald-500 text-white",
                            )}
                          >
                            {ev.severity.toUpperCase()}
                          </span>
                          <span className="font-semibold text-foreground">{ev.cameraName[locale]}</span>
                        </div>
                        <span className="font-mono text-[10px] text-muted-foreground">{ev.realTime}</span>
                      </div>

                      <p className="mt-1.5 text-xs text-foreground/90 leading-relaxed font-medium">
                        {ev.message[locale]}
                      </p>

                      {ev.missingPpe.length > 0 && (
                        <div className="mt-2 flex flex-wrap items-center gap-1">
                          {ev.missingPpe.map((item) => (
                            <span
                              key={item}
                              className="rounded bg-background/80 px-1.5 py-0.5 text-[10px] font-mono text-red-600 dark:text-red-400 border border-red-500/20"
                            >
                              - {item}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Live Indicator Footer */}
            <div className="border-t border-border bg-muted/30 p-2.5 px-4 text-center">
              <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
                <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {t.onlineStatus} — 4 {arabic ? "كاميرات متزامنة مع السيرفر" : "Cameras Synced with Diraya Pipeline"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
