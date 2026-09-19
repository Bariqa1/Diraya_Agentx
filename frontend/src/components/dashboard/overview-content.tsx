import { ShieldAlert } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Locale } from "@/lib/locale";
import { kpis, localize, type StatusTone } from "./dashboard-data";
import { EnvironmentalConditions } from "./environmental-conditions";
import { LiveMonitoringContent } from "./live-monitoring-content";

const copy = {
  ar: {
    title: "نظرة عامة",
    subtitle: "مركز القيادة الموحد ومراقبة السلامة المهنية في الوقت الفعلي",
    currentStatus: "الحالة العامة للموقع",
    statusValue: "مستوى خطورة مرتفع — مخالفات حرجة نشطة",
    summary: "يرصد نظام الذكاء الاصطناعي حالياً مخالفات حرجة نشطة (اختراق مناطق الخطر ونقص معدات الوقاية الشخصية) تتطلب تدخلاً فورياً من المشرف.",
    criticalCams: "2 كاميرات حرجة",
    warningCams: "1 كاميرا تحذيرية",
    safeCams: "1 كاميرا آمنة",
  },
  en: {
    title: "Overview",
    subtitle: "Unified operations command and real-time safety monitoring",
    currentStatus: "Facility Overall Status",
    statusValue: "High Risk Level — Active Critical Violations",
    summary: "AI vision system currently detects active critical violations (restricted zone breach and missing mandatory PPE) requiring immediate supervisor action.",
    criticalCams: "2 Critical Cameras",
    warningCams: "1 Warning Camera",
    safeCams: "1 Safe Camera",
  },
} as const;

const toneStyles: Record<StatusTone, string> = {
  positive: "bg-positive-soft text-positive-deep border-positive/20",
  warning: "bg-risk-moderate-soft text-risk-moderate-deep border-risk-moderate/20",
  critical: "bg-risk-critical-soft text-risk-critical border-risk-critical/20",
  neutral: "bg-muted text-muted-foreground border-border",
};

export function OverviewContent({ locale }: { locale: Locale }) {
  const text = copy[locale];
  const arabic = locale === "ar";

  return (
    <div className="mx-auto max-w-[1680px] space-y-5 p-4 sm:p-5 xl:px-8 xl:py-6">
      {/* Page Title */}
      <div>
        <h1 className={cn("text-2xl font-bold text-foreground sm:text-3xl", !arabic && "font-display")}>
          {text.title}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">{text.subtitle}</p>
      </div>

      {/* 1. Key Safety Metrics (KPIs) */}
      <section aria-label={arabic ? "مؤشرات السلامة الرئيسية" : "Key safety metrics"} className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <article
            key={kpi.label.en}
            className="grid min-h-24 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-xl border border-border bg-card p-3.5 shadow-sm sm:p-4"
          >
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-muted-foreground sm:text-sm">
                {localize(locale, kpi.label)}
              </p>
              <div className="mt-1.5 flex items-baseline gap-2">
                <p className="font-display text-2xl font-bold tabular-nums text-foreground sm:text-3xl">
                  {kpi.value}
                </p>
                {kpi.detail ? (
                  <span className={cn("text-[11px] font-bold", kpi.tone === "positive" ? "text-positive-deep" : "text-risk-critical")}>
                    {localize(locale, kpi.detail)}
                  </span>
                ) : null}
              </div>
            </div>
            <span className={cn("flex size-10 shrink-0 items-center justify-center rounded-lg border", toneStyles[kpi.tone])}>
              <kpi.icon className="size-5" />
            </span>
          </article>
        ))}
      </section>

      {/* 2. Embedded Live Quad Camera Monitoring (Replaced old static mock camera) */}
      <section className="rounded-2xl border border-border bg-card p-4 shadow-sm sm:p-5">
        <LiveMonitoringContent locale={locale} embedded={true} />
      </section>

      {/* 3. Facility Overall Status Banner (Harmonized with Active Hazards & Red Logs) */}
      <section className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-4 rounded-xl border border-red-500/30 bg-red-500/5 px-5 py-4 shadow-sm dark:bg-red-950/20">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-red-500/30 bg-red-500/15 text-red-600 shadow-sm dark:text-red-400">
          <ShieldAlert className="size-6 animate-pulse" />
        </span>
        <div className="min-w-0 space-y-2 sm:flex sm:items-center sm:justify-between sm:space-y-0 sm:gap-6">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xs font-semibold text-muted-foreground">{text.currentStatus}:</h2>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-red-500/30 bg-red-500/15 px-2.5 py-0.5 text-xs font-bold text-red-600 dark:text-red-400">
                <span className="size-1.5 rounded-full bg-red-500 animate-ping" />
                {text.statusValue}
              </span>
            </div>
            <p className="text-xs leading-relaxed text-foreground/85">{text.summary}</p>
          </div>

          {/* Quick Camera Breakdown Indicators */}
          <div className="flex shrink-0 flex-wrap items-center gap-1.5 pt-1 sm:pt-0 font-mono text-[11px]">
            <span className="rounded-lg border border-red-500/30 bg-red-500/15 px-2.5 py-1 font-bold text-red-600 dark:text-red-400">
              🔴 {text.criticalCams}
            </span>
            <span className="rounded-lg border border-amber-500/30 bg-amber-500/15 px-2.5 py-1 font-bold text-amber-600 dark:text-amber-400">
              🟡 {text.warningCams}
            </span>
            <span className="rounded-lg border border-emerald-500/30 bg-emerald-500/15 px-2.5 py-1 font-bold text-emerald-600 dark:text-emerald-400">
              🟢 {text.safeCams}
            </span>
          </div>
        </div>
      </section>

      {/* 4. Environmental Conditions & Heat Stress (Same Place as Before!) */}
      <EnvironmentalConditions locale={locale} />
    </div>
  );
}
