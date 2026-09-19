import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, Clock3, HardHat, MapPin, Minus, Sparkles, TrendingDown, TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Locale } from "@/lib/locale";
import {
  aiInsights,
  analyticsRanges,
  defaultRange,
  pick,
  ppeInsight,
  ppeTrendLabels,
  ppeTrends,
  predictedAreas,
  riskLevelLabels,
  riskPatterns,
  timeBuckets,
  timeInsight,
  trendDirectionLabels,
  zoneTrends,
  type RangeKey,
  type RiskLevel,
  type TrendDirection,
} from "./analytics-data";

const copy = {
  ar: {
    title: "التحليلات",
    subtitle: "اكتشف الاتجاهات وتوقع المخاطر قبل وقوعها",
    range: "الفترة الزمنية",
    trend: "اتجاه المخاطر",
    trendNote: "إجمالي المخاطر المرصودة عبر الزمن",
    trendState: "حالة الاتجاه",
    forecast: "توقع مستوى المخاطر",
    forecastNote: "بيانات تاريخية مع توقع للأيام السبعة القادمة",
    forecastBadge: "توقع تجريبي بالذكاء الاصطناعي",
    historical: "بيانات تاريخية",
    predicted: "توقع",
    confidence: "مستوى الثقة",
    patterns: "أنماط المخاطر الأكثر تكرارًا",
    patternsNote: "تصنيفات مجمعة للمخاطر المرصودة",
    zones: "اتجاه المخاطر حسب المنطقة",
    zonesNote: "مقارنة اتجاه المخاطر بين المناطق",
    zoneInsight: "المنطقة C تظهر أعلى اتجاه تصاعدي في مستوى المخاطر.",
    time: "أنماط المخاطر حسب الوقت",
    timeNote: "كثافة المخاطر خلال فترات اليوم",
    ppe: "اتجاه الالتزام بمعدات الوقاية",
    ppeNote: "تطور نسبة الالتزام خلال الفترة",
    predictedAreas: "المناطق المتوقع ارتفاع مخاطرها",
    predictedAreasNote: "مناطق قد تحتاج إلى مراقبة إضافية",
    predictedLevel: "مستوى الخطر المتوقع",
    insights: "رؤى دِراية",
    insightBadge: "رؤية مولدة بالذكاء الاصطناعي",
    low: "منخفض",
    high: "مرتفع",
  },
  en: {
    title: "Analytics",
    subtitle: "Discover trends and predict risks before they happen",
    range: "Date range",
    trend: "Risk Trend",
    trendNote: "Aggregated detected safety risks over time",
    trendState: "Trend state",
    forecast: "Risk Forecast",
    forecastNote: "Historical data with a forecast for the next 7 days",
    forecastBadge: "AI-based prototype forecast",
    historical: "Historical",
    predicted: "Forecast",
    confidence: "Confidence",
    patterns: "Most Common Risk Patterns",
    patternsNote: "Aggregated categories of detected risks",
    zones: "Risk Trends by Area",
    zonesNote: "Comparing risk direction across areas",
    zoneInsight: "Zone C shows the strongest upward risk trend.",
    time: "Risk Patterns by Time",
    timeNote: "Risk intensity across periods of the day",
    ppe: "PPE Compliance Trend",
    ppeNote: "How compliance evolved across the period",
    predictedAreas: "Predicted High-Risk Areas",
    predictedAreasNote: "Areas that may require additional attention",
    predictedLevel: "Predicted risk level",
    insights: "DIRAYA Insights",
    insightBadge: "AI-generated insight",
    low: "Low",
    high: "High",
  },
} as const;

const levelBar: Record<RiskLevel, string> = {
  low: "bg-risk-low",
  moderate: "bg-risk-moderate",
  high: "bg-risk-high",
  critical: "bg-risk-critical",
};
const levelChip: Record<RiskLevel, string> = {
  low: "bg-risk-low-soft text-positive-deep",
  moderate: "bg-risk-moderate-soft text-risk-moderate-deep",
  high: "bg-risk-high-soft text-risk-high-deep",
  critical: "bg-risk-critical-soft text-risk-critical",
};
const levelDot: Record<RiskLevel, string> = {
  low: "bg-risk-low",
  moderate: "bg-risk-moderate",
  high: "bg-risk-high",
  critical: "bg-risk-critical",
};

const ppeStroke = ["var(--chart-incidents)", "var(--risk-high)", "var(--risk-low)"];

function DirectionIcon({ direction, className }: { direction: TrendDirection; className?: string }) {
  if (direction === "up") return <TrendingUp className={cn("size-4 text-risk-critical", className)} />;
  if (direction === "down") return <TrendingDown className={cn("size-4 text-positive-deep", className)} />;
  return <Minus className={cn("size-4 text-muted-foreground", className)} />;
}

function Sparkline({ values, level }: { values: number[]; level: RiskLevel }) {
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const points = values
    .map((value, index) => `${(index / (values.length - 1)) * 100},${28 - ((value - min) / span) * 24}`)
    .join(" ");
  const stroke =
    level === "critical" ? "var(--risk-critical)" : level === "high" ? "var(--risk-high)" : level === "moderate" ? "var(--risk-moderate)" : "var(--risk-low)";
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" className="h-8 w-24 shrink-0" aria-hidden="true">
      <polyline points={points} fill="none" stroke={stroke} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function AnalyticsContent({ locale }: { locale: Locale }) {
  const text = copy[locale];
  const arabic = locale === "ar";
  const [range, setRange] = useState<RangeKey>(defaultRange);
  const active = analyticsRanges.find((item) => item.key === range) ?? analyticsRanges[1]!;

  const trendData = active.trend.map((point) => ({ name: pick(locale, point.label), risks: point.risks }));
  const forecast = active.forecast;
  const forecastData = forecast.points.map((point) => ({
    name: pick(locale, point.label),
    actual: point.actual,
    forecast: point.forecast,
  }));
  const maxIntensity = Math.max(...timeBuckets.map((bucket) => bucket.intensity));
  const ppeData = ppeTrendLabels.map((label, index) => ({
    name: pick(locale, label),
    ...Object.fromEntries(ppeTrends.map((series) => [series.label.en, series.values[index]])),
  }));

  return (
    <div className="mx-auto max-w-[1600px] space-y-4 p-4 sm:p-5 xl:px-7 xl:py-5">
      <div className="gap-3 sm:flex sm:items-end sm:justify-between">
        <div>
          <h1 className={cn("text-2xl font-bold text-foreground sm:text-3xl", !arabic && "font-display")}>{text.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{text.subtitle}</p>
        </div>
        <div className="mt-3 inline-flex rounded-lg border border-border bg-card p-1 sm:mt-0" role="group" aria-label={text.range}>
          {analyticsRanges.map((item) => (
            <Button
              key={item.key}
              type="button"
              variant="ghost"
              size="sm"
              aria-pressed={range === item.key}
              onClick={() => setRange(item.key)}
              className={cn(
                "h-8 rounded-md px-3 text-xs font-semibold shadow-none",
                range === item.key
                  ? "bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {pick(locale, item.label)}
            </Button>
          ))}
        </div>
      </div>

      {/* Risk trend */}
      <section className="rounded-lg border border-border bg-card p-4 shadow-sm sm:p-5">
        <div className="gap-3 sm:flex sm:items-start sm:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-base font-bold text-foreground">
              <Activity className="size-4 text-primary" />
              {text.trend}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">{text.trendNote} · {pick(locale, active.label)}</p>
          </div>
          <span className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-[11px] font-bold text-foreground sm:mt-0">
            <DirectionIcon direction={active.trendDirection} className="size-3.5" />
            {text.trendState}: {pick(locale, trendDirectionLabels[active.trendDirection])}
          </span>
        </div>
        <div className="mt-4 h-64 w-full sm:h-72" dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trendData} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-incidents)" stopOpacity={0.28} />
                  <stop offset="100%" stopColor="var(--chart-incidents)" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} reversed={arabic} />
              <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} orientation={arabic ? "right" : "left"} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: "1px solid var(--border)", background: "var(--card)", fontSize: 12 }}
                labelStyle={{ color: "var(--muted-foreground)" }}
              />
              <Area type="monotone" dataKey="risks" name={text.trend} stroke="var(--chart-incidents)" strokeWidth={2.5} fill="url(#trendFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-3 flex items-center gap-2 rounded-md bg-positive-soft px-3 py-2 text-xs font-semibold text-positive-deep">
          <Sparkles className="size-4 shrink-0" />
          {pick(locale, active.trendInsight)}
        </p>
      </section>

      {/* Risk forecast */}
      <section className="rounded-lg border border-ai-border bg-ai-surface p-4 text-ai-foreground shadow-sm sm:p-5">
        <div className="gap-3 sm:flex sm:items-start sm:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-base font-bold">
              <Sparkles className="size-4 text-ai-accent" />
              {text.forecast}
            </h2>
            <p className="mt-1 text-xs text-ai-muted">{text.forecastNote}</p>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 sm:mt-0">
            <span className="inline-flex items-center gap-1.5 rounded bg-ai-panel px-2 py-1 text-[10px] font-bold text-ai-accent">
              <Sparkles className="size-3" />
              {text.forecastBadge}
            </span>
            <span className="inline-flex items-center rounded bg-ai-panel/70 px-2 py-1 text-[10px] font-bold text-ai-muted">
              {text.confidence}: {forecast.confidence}%
            </span>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] font-semibold text-ai-muted">
          <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 rounded bg-ai-accent" />{text.historical}</span>
          <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 rounded border-t-2 border-dashed border-risk-high" />{text.predicted} · {pick(locale, forecast.period)}</span>
          {forecast.zone ? <span dir="ltr" className="rounded bg-ai-panel px-2 py-0.5">{forecast.zone}</span> : null}
        </div>
        <div className="mt-3 h-64 w-full sm:h-72" dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={forecastData} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid stroke="var(--ai-border)" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--ai-muted)" }} axisLine={false} tickLine={false} reversed={arabic} />
              <YAxis tick={{ fontSize: 11, fill: "var(--ai-muted)" }} axisLine={false} tickLine={false} orientation={arabic ? "right" : "left"} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: "1px solid var(--ai-border)", background: "var(--ai-panel)", fontSize: 12, color: "var(--ai-foreground)" }}
                labelStyle={{ color: "var(--ai-muted)" }}
              />
              <Line type="monotone" dataKey="actual" name={text.historical} stroke="var(--ai-accent)" strokeWidth={2.5} dot={false} connectNulls />
              <Line
                type="monotone"
                dataKey="forecast"
                name={text.predicted}
                stroke="var(--risk-high)"
                strokeWidth={2.5}
                strokeDasharray="5 5"
                dot={{ r: 3, fill: "var(--risk-high)", strokeWidth: 0 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-3 flex items-start gap-2 rounded-md bg-ai-panel/70 px-3 py-2 text-xs font-semibold text-ai-foreground">
          <Sparkles className="mt-0.5 size-4 shrink-0 text-ai-accent" />
          {pick(locale, forecast.insight)}
        </p>
      </section>

      {/* Patterns + zones */}
      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg border border-border bg-card p-4 shadow-sm sm:p-5">
          <h2 className="text-base font-bold text-foreground">{text.patterns}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{text.patternsNote}</p>
          <ul className="mt-4 space-y-3.5">
            {riskPatterns.map((pattern) => (
              <li key={pattern.label.en}>
                <div className="flex items-baseline justify-between gap-3 text-xs">
                  <span className="truncate font-semibold text-foreground">{pick(locale, pattern.label)}</span>
                  <span className="shrink-0 font-display font-bold tabular-nums text-foreground">{pattern.share}%</span>
                </div>
                <div className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-muted">
                  <div className={cn("h-full rounded-full", levelBar[pattern.level])} style={{ width: `${pattern.share}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-lg border border-border bg-card p-4 shadow-sm sm:p-5">
          <h2 className="flex items-center gap-2 text-base font-bold text-foreground">
            <MapPin className="size-4 text-primary" />
            {text.zones}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">{text.zonesNote}</p>
          <ul className="mt-4 divide-y divide-border">
            {zoneTrends.map((zone) => (
              <li key={zone.zone} className="flex items-center justify-between gap-3 py-2.5">
                <span className="flex min-w-0 items-center gap-2 text-xs font-semibold text-foreground">
                  <span dir="ltr">{zone.zone}</span>
                  <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-bold", levelChip[zone.level])}>{pick(locale, riskLevelLabels[zone.level])}</span>
                </span>
                <span className="flex items-center gap-3">
                  <Sparkline values={zone.spark} level={zone.level} />
                  <span
                    className={cn(
                      "flex w-16 items-center justify-end gap-1 text-xs font-bold tabular-nums",
                      zone.direction === "up" ? "text-risk-critical" : zone.direction === "down" ? "text-positive-deep" : "text-muted-foreground",
                    )}
                  >
                    <DirectionIcon direction={zone.direction} className="size-3.5" />
                    <span dir="ltr">{zone.change > 0 ? `+${zone.change}` : zone.change}%</span>
                  </span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 flex items-center gap-2 rounded-md bg-risk-critical-soft px-3 py-2 text-xs font-semibold text-risk-critical">
            <Sparkles className="size-4 shrink-0" />
            {text.zoneInsight}
          </p>
        </section>
      </div>

      {/* Time heatmap + PPE trend */}
      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg border border-border bg-card p-4 shadow-sm sm:p-5">
          <h2 className="flex items-center gap-2 text-base font-bold text-foreground">
            <Clock3 className="size-4 text-primary" />
            {text.time}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">{text.timeNote}</p>
          <div className="mt-5 space-y-2" dir="ltr">
            {timeBuckets.map((bucket) => {
              const ratio = bucket.intensity / maxIntensity;
              return (
                <div key={bucket.range} className="flex items-center gap-3">
                  <span className="w-24 shrink-0 text-[10px] font-medium tabular-nums text-muted-foreground sm:text-[11px]">{bucket.range}</span>
                  <div className="h-7 flex-1 overflow-hidden rounded-md bg-muted">
                    <div
                      className={cn("h-full rounded-md", ratio > 0.85 ? "bg-risk-critical" : ratio > 0.6 ? "bg-risk-high" : ratio > 0.35 ? "bg-risk-moderate" : "bg-risk-low")}
                      style={{ width: `${Math.max(ratio * 100, 6)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex items-center gap-2 text-[10px] font-semibold text-muted-foreground" dir="ltr">
            <span>{text.low}</span>
            <span className="h-2 w-6 rounded bg-risk-low" />
            <span className="h-2 w-6 rounded bg-risk-moderate" />
            <span className="h-2 w-6 rounded bg-risk-high" />
            <span className="h-2 w-6 rounded bg-risk-critical" />
            <span>{text.high}</span>
          </div>
          <p className="mt-3 flex items-center gap-2 rounded-md bg-risk-high-soft px-3 py-2 text-xs font-semibold text-risk-high-deep">
            <Sparkles className="size-4 shrink-0" />
            {pick(locale, timeInsight)}
          </p>
        </section>

        <section className="rounded-lg border border-border bg-card p-4 shadow-sm sm:p-5">
          <h2 className="flex items-center gap-2 text-base font-bold text-foreground">
            <HardHat className="size-4 text-primary" />
            {text.ppe}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">{text.ppeNote}</p>
          <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] font-semibold text-muted-foreground">
            {ppeTrends.map((series, index) => (
              <span key={series.label.en} className="flex items-center gap-1.5">
                <span className="h-0.5 w-5 rounded" style={{ background: ppeStroke[index] }} />
                {pick(locale, series.label)}
                <span className="tabular-nums text-positive-deep" dir="ltr">+{series.change}%</span>
              </span>
            ))}
          </div>
          <div className="mt-3 h-52 w-full" dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={ppeData} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="var(--border)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} reversed={arabic} />
                <YAxis domain={[80, 100]} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} orientation={arabic ? "right" : "left"} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: "1px solid var(--border)", background: "var(--card)", fontSize: 12 }}
                  labelStyle={{ color: "var(--muted-foreground)" }}
                />
                {ppeTrends.map((series, index) => (
                  <Line
                    key={series.label.en}
                    type="monotone"
                    dataKey={series.label.en}
                    name={pick(locale, series.label)}
                    stroke={ppeStroke[index]}
                    strokeWidth={2.5}
                    dot={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 flex items-center gap-2 rounded-md bg-positive-soft px-3 py-2 text-xs font-semibold text-positive-deep">
            <Sparkles className="size-4 shrink-0" />
            {pick(locale, ppeInsight)}
          </p>
        </section>
      </div>

      {/* Predicted high-risk areas */}
      <section className="rounded-lg border border-border bg-card p-4 shadow-sm sm:p-5">
        <div className="gap-3 sm:flex sm:items-start sm:justify-between">
          <div>
            <h2 className="text-base font-bold text-foreground">{text.predictedAreas}</h2>
            <p className="mt-1 text-xs text-muted-foreground">{text.predictedAreasNote}</p>
          </div>
          <span className="mt-2 inline-flex items-center gap-1.5 rounded bg-muted px-2 py-1 text-[10px] font-bold text-muted-foreground sm:mt-0">
            <Sparkles className="size-3" />
            {text.forecastBadge}
          </span>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {predictedAreas.map((area) => (
            <article key={area.zone} className="rounded-md border border-border p-3.5">
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 text-sm font-bold text-foreground">
                  <span className={cn("size-2.5 rounded-full", levelDot[area.level])} />
                  <span dir="ltr">{area.zone}</span>
                </span>
                <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-bold", levelChip[area.level])}>{pick(locale, riskLevelLabels[area.level])}</span>
              </div>
              <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{text.predictedLevel}</p>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{pick(locale, area.note)}</p>
            </article>
          ))}
        </div>
      </section>

      {/* DIRAYA insights */}
      <section className="rounded-lg border border-ai-border bg-ai-surface p-4 text-ai-foreground shadow-sm sm:p-5">
        <div className="flex items-center gap-2">
          <span className="flex size-8 items-center justify-center rounded-md bg-ai-panel text-ai-accent"><Sparkles className="size-4" /></span>
          <h2 className="text-base font-bold">{text.insights}</h2>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {aiInsights.map((insight) => (
            <article key={insight.title.en} className="rounded-md border border-ai-border bg-ai-panel/60 p-3.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded bg-ai-panel px-2 py-1 text-[10px] font-bold text-ai-accent">
                  <Sparkles className="size-3" />
                  {text.insightBadge}
                </span>
                <span className="text-[10px] font-bold text-ai-muted">{pick(locale, insight.kind)}</span>
              </div>
              <h3 className="mt-2.5 flex items-start gap-2 text-sm font-bold">
                <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", levelDot[insight.level])} />
                {pick(locale, insight.title)}
              </h3>
              <p className="mt-1.5 text-xs leading-relaxed text-ai-muted">{pick(locale, insight.body)}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
