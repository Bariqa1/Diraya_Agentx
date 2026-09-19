import type { Locale } from "@/lib/locale";

export type Bilingual = { ar: string; en: string };
export type RangeKey = "7d" | "30d" | "3m";
export type RiskLevel = "low" | "moderate" | "high" | "critical";
export type TrendDirection = "up" | "down" | "stable";

export type TrendPoint = { label: Bilingual; risks: number };

/** One point of the forecast chart. `actual` is history, `forecast` is prediction. */
export type ForecastPoint = {
  label: Bilingual;
  actual: number | null;
  forecast: number | null;
  /** Optional confidence band for forecast points (low/high risk counts). */
  band?: [number, number];
};

/** Shape a real prediction service can populate later — the UI reads only this. */
export type RiskForecast = {
  zone: string | null;
  category: Bilingual | null;
  period: Bilingual;
  confidence: number;
  points: ForecastPoint[];
  insight: Bilingual;
};

export type RiskPattern = { label: Bilingual; share: number; level: RiskLevel };
export type ZoneTrend = {
  zone: string;
  level: RiskLevel;
  change: number;
  direction: TrendDirection;
  spark: number[];
};
export type TimeBucket = { range: string; intensity: number };
export type PpeSeries = { label: Bilingual; values: number[]; change: number };
export type PredictedArea = { zone: string; level: RiskLevel; note: Bilingual };
export type AiInsight = { kind: Bilingual; title: Bilingual; body: Bilingual; level: RiskLevel };

export type AnalyticsRange = {
  key: RangeKey;
  label: Bilingual;
  trend: TrendPoint[];
  trendDirection: TrendDirection;
  trendInsight: Bilingual;
  forecast: RiskForecast;
};

// Mock aggregation layer. Replace these values with API/YOLO aggregates later —
// the UI reads only from the exported shapes below.

const forecastPeriod: Bilingual = { ar: "الأيام السبعة القادمة", en: "Next 7 days" };

function fc(label: Bilingual, actual: number | null, forecast: number | null, band?: [number, number]): ForecastPoint {
  return { label, actual, forecast, ...(band ? { band } : {}) };
}

const d = (ar: string, en: string): Bilingual => ({ ar, en });

export const analyticsRanges: AnalyticsRange[] = [
  {
    key: "7d",
    label: d("آخر 7 أيام", "Last 7 Days"),
    trendDirection: "down",
    trend: [
      { label: d("الأربعاء", "Wed"), risks: 17 },
      { label: d("الخميس", "Thu"), risks: 14 },
      { label: d("الجمعة", "Fri"), risks: 11 },
      { label: d("السبت", "Sat"), risks: 9 },
      { label: d("الأحد", "Sun"), risks: 15 },
      { label: d("الاثنين", "Mon"), risks: 13 },
      { label: d("اليوم", "Today"), risks: 12 },
    ],
    trendInsight: d(
      "الاتجاه الحالي يشير إلى انخفاض تدريجي في مستوى المخاطر.",
      "The current trend indicates a gradual decrease in overall risk.",
    ),
    forecast: {
      zone: "Zone C",
      category: d("مخالفات معدات الوقاية", "PPE violations"),
      period: forecastPeriod,
      confidence: 72,
      points: [
        fc(d("الأحد", "Sun"), 15, null),
        fc(d("الاثنين", "Mon"), 13, null),
        fc(d("اليوم", "Today"), 12, 12, [12, 12]),
        fc(d("+1 يوم", "+1d"), null, 14, [11, 17]),
        fc(d("+2 يوم", "+2d"), null, 16, [12, 20]),
        fc(d("+3 يوم", "+3d"), null, 17, [12, 22]),
        fc(d("+5 يوم", "+5d"), null, 19, [13, 25]),
        fc(d("+7 يوم", "+7d"), null, 21, [14, 28]),
      ],
      insight: d(
        "تتوقع دِراية ارتفاع مستوى المخاطر في المنطقة C خلال الأيام القادمة.",
        "DIRAYA predicts an increase in risk levels in Zone C over the coming days.",
      ),
    },
  },
  {
    key: "30d",
    label: d("آخر 30 يومًا", "Last 30 Days"),
    trendDirection: "down",
    trend: [
      { label: d("الأسبوع 1", "Week 1"), risks: 46 },
      { label: d("الأسبوع 2", "Week 2"), risks: 41 },
      { label: d("الأسبوع 3", "Week 3"), risks: 34 },
      { label: d("الأسبوع 4", "Week 4"), risks: 30 },
      { label: d("الأسبوع 5", "Week 5"), risks: 27 },
    ],
    trendInsight: d(
      "الاتجاه الحالي يشير إلى انخفاض تدريجي في مستوى المخاطر.",
      "The current trend indicates a gradual decrease in overall risk.",
    ),
    forecast: {
      zone: "Zone C",
      category: d("مخالفات معدات الوقاية", "PPE violations"),
      period: forecastPeriod,
      confidence: 68,
      points: [
        fc(d("الأسبوع 2", "Week 2"), 41, null),
        fc(d("الأسبوع 3", "Week 3"), 34, null),
        fc(d("الأسبوع 4", "Week 4"), 30, null),
        fc(d("الأسبوع 5", "Week 5"), 27, 27, [27, 27]),
        fc(d("+2 يوم", "+2d"), null, 29, [24, 34]),
        fc(d("+4 يوم", "+4d"), null, 31, [25, 38]),
        fc(d("+7 يوم", "+7d"), null, 34, [26, 43]),
      ],
      insight: d(
        "تتوقع دِراية ارتفاع مستوى المخاطر في المنطقة C خلال الأيام القادمة.",
        "DIRAYA predicts an increase in risk levels in Zone C over the coming days.",
      ),
    },
  },
  {
    key: "3m",
    label: d("آخر 3 أشهر", "Last 3 Months"),
    trendDirection: "down",
    trend: [
      { label: d("يوليو", "Jul"), risks: 168 },
      { label: d("أغسطس", "Aug"), risks: 149 },
      { label: d("سبتمبر", "Sep"), risks: 131 },
    ],
    trendInsight: d(
      "الاتجاه العام خلال الأشهر الثلاثة الماضية يشير إلى تحسن مستمر في مستوى السلامة.",
      "The three-month trend indicates a continued improvement in overall safety.",
    ),
    forecast: {
      zone: "Zone C",
      category: d("مخالفات معدات الوقاية", "PPE violations"),
      period: forecastPeriod,
      confidence: 61,
      points: [
        fc(d("يوليو", "Jul"), 168, null),
        fc(d("أغسطس", "Aug"), 149, null),
        fc(d("سبتمبر", "Sep"), 131, 131, [131, 131]),
        fc(d("+3 يوم", "+3d"), null, 136, [120, 152]),
        fc(d("+7 يوم", "+7d"), null, 142, [122, 164]),
      ],
      insight: d(
        "تتوقع دِراية ارتفاع مستوى المخاطر في المنطقة C خلال الأيام القادمة.",
        "DIRAYA predicts an increase in risk levels in Zone C over the coming days.",
      ),
    },
  },
];

export const defaultRange: RangeKey = "30d";

export const riskPatterns: RiskPattern[] = [
  { label: d("مخالفات معدات الوقاية", "PPE violations"), share: 62, level: "critical" },
  { label: d("دخول منطقة محظورة", "Restricted area entry"), share: 18, level: "high" },
  { label: d("سلوك غير آمن", "Unsafe behaviour"), share: 12, level: "moderate" },
  { label: d("رصد دخان أو حريق", "Smoke / fire detection"), share: 5, level: "critical" },
  { label: d("مخاطر أخرى", "Other safety risks"), share: 3, level: "low" },
];

export const zoneTrends: ZoneTrend[] = [
  { zone: "Zone A", level: "low", change: -14, direction: "down", spark: [16, 14, 12, 11, 9] },
  { zone: "Zone B", level: "moderate", change: -4, direction: "stable", spark: [24, 25, 23, 24, 23] },
  { zone: "Zone C", level: "critical", change: 27, direction: "up", spark: [26, 30, 34, 38, 42] },
  { zone: "Zone D", level: "low", change: -21, direction: "down", spark: [14, 12, 11, 10, 9] },
  { zone: "Zone E", level: "high", change: 11, direction: "up", spark: [24, 26, 27, 29, 31] },
];

export const timeBuckets: TimeBucket[] = [
  { range: "00:00–06:00", intensity: 8 },
  { range: "06:00–09:00", intensity: 19 },
  { range: "09:00–12:00", intensity: 27 },
  { range: "12:00–15:00", intensity: 41 },
  { range: "15:00–18:00", intensity: 24 },
  { range: "18:00–00:00", intensity: 11 },
];

export const timeInsight: Bilingual = d(
  "تظهر أعلى كثافة للمخاطر خلال فترة الظهيرة.",
  "The highest concentration of risks occurs during the afternoon period.",
);

export const ppeTrendLabels: Bilingual[] = [
  d("الأسبوع 1", "Week 1"),
  d("الأسبوع 2", "Week 2"),
  d("الأسبوع 3", "Week 3"),
  d("الأسبوع 4", "Week 4"),
  d("الأسبوع 5", "Week 5"),
];

export const ppeTrends: PpeSeries[] = [
  { label: d("الخوذة", "Helmet"), values: [88, 90, 92, 94, 96], change: 8 },
  { label: d("سترة السلامة", "Safety Vest"), values: [86, 87, 89, 90, 91], change: 5 },
  { label: d("أحذية السلامة", "Safety Shoes"), values: [97, 96, 97, 98, 98], change: 1 },
];

export const ppeInsight: Bilingual = d(
  "تحسن الالتزام بالخوذات بشكل مستمر خلال الفترة الأخيرة.",
  "Helmet compliance has shown a consistent improvement recently.",
);

export const predictedAreas: PredictedArea[] = [
  {
    zone: "Zone C",
    level: "critical",
    note: d(
      "استنادًا إلى أنماط المخاطر الحديثة، قد تحتاج هذه المنطقة إلى مراقبة مكثفة.",
      "Based on recent risk patterns, this area may require increased monitoring.",
    ),
  },
  {
    zone: "Zone E",
    level: "high",
    note: d(
      "ارتفاع تدريجي في المخالفات المرصودة يستدعي متابعة إضافية.",
      "A gradual rise in detected violations suggests additional follow-up.",
    ),
  },
  {
    zone: "Zone B",
    level: "moderate",
    note: d(
      "مستوى المخاطر مستقر مع تقلبات محدودة خلال فترات الظهيرة.",
      "Risk level is stable with limited fluctuation during afternoon hours.",
    ),
  },
];

export const aiInsights: AiInsight[] = [
  {
    kind: d("خطر ناشئ", "Emerging risk"),
    title: d("ارتفاع متوقع في مخاطر المنطقة C", "Increasing risk expected in Zone C"),
    body: d(
      "تشير أنماط الرصد الحديثة إلى احتمال ارتفاع مخالفات السلامة.",
      "Recent detection patterns indicate a potential increase in safety violations.",
    ),
    level: "critical",
  },
  {
    kind: d("نمط سلوكي", "Behavioural pattern"),
    title: d("مخالفات معدات الوقاية هي النمط الأكثر تكرارًا", "PPE violations are the most recurring pattern"),
    body: d(
      "تمثل مخالفات معدات الوقاية النسبة الأكبر من الأنماط المرصودة.",
      "PPE violations represent the largest share of all detected patterns.",
    ),
    level: "high",
  },
  {
    kind: d("نمط زمني", "Time pattern"),
    title: d("ترتفع كثافة المخاطر خلال فترة الظهيرة", "Risk concentration increases during the afternoon"),
    body: d(
      "تتكرر معظم الاكتشافات بين الساعة 12:00 و15:00.",
      "Most detections recur between 12:00 and 15:00.",
    ),
    level: "moderate",
  },
];

export const riskLevelLabels: Record<RiskLevel, Bilingual> = {
  low: d("منخفض", "Low"),
  moderate: d("متوسط", "Medium"),
  high: d("عالٍ", "High"),
  critical: d("حرج", "Critical"),
};

export const trendDirectionLabels: Record<TrendDirection, Bilingual> = {
  up: d("تصاعدي", "Increasing"),
  down: d("تنازلي", "Decreasing"),
  stable: d("مستقر", "Stable"),
};

export function pick(locale: Locale, value: Bilingual) {
  return value[locale];
}
