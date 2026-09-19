import type { ComponentType } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  Gauge,
  LayoutDashboard,
  Map,
  ShieldAlert,
  Siren,
  TrendingUp,
} from "lucide-react";

import type { Locale } from "@/lib/locale";

export type DashboardPath =
  | "/overview"
  | "/alerts"
  | "/risk-map"
  | "/incidents"
  | "/analytics"
  | "/ai-assistant"
  | "/profile";

export type Severity = "low" | "moderate" | "high" | "critical";
export type StatusTone = "positive" | "warning" | "critical" | "neutral";

export const dashboardNav: Array<{
  path: DashboardPath;
  icon: ComponentType<{ className?: string }>;
  ar: string;
  en: string;
}> = [
  { path: "/overview", icon: LayoutDashboard, ar: "نظرة عامة", en: "Overview" },
  { path: "/alerts", icon: Siren, ar: "التنبيهات", en: "Alerts" },
  { path: "/risk-map", icon: ShieldAlert, ar: "المخاطر وصلاحيات الدخول", en: "Risks & Access Permissions" },
  { path: "/incidents", icon: Activity, ar: "سجل الحوادث", en: "Incident Log" },
  { path: "/analytics", icon: TrendingUp, ar: "التحليلات", en: "Analytics" },
  { path: "/ai-assistant", icon: Bot, ar: "المساعد الذكي", en: "AI Assistant" },
];

export interface KpiItem {
  icon: ComponentType<{ className?: string }>;
  value: string;
  label: { ar: string; en: string };
  detail: { ar: string; en: string } | null;
  tone: StatusTone;
}

export const kpis: KpiItem[] = [
  { icon: AlertTriangle, value: "12", label: { ar: "الحوادث اليوم", en: "Incidents Today" }, detail: null, tone: "neutral" },
  { icon: Siren, value: "4", label: { ar: "التنبيهات النشطة", en: "Active Alerts" }, detail: { ar: "2 حرجة", en: "2 Critical" }, tone: "critical" },
  { icon: AlertTriangle, value: "2", label: { ar: "مخاطر حرجة", en: "Critical Risks" }, detail: null, tone: "warning" },
  { icon: Gauge, value: "64%", label: { ar: "مؤشر السلامة", en: "Safety Score" }, detail: { ar: "متراجع (مخالفات)", en: "Low (Violations)" }, tone: "warning" },
];

export const alerts = [
  { type: { ar: "خطر حريق / دخان", en: "Fire / Smoke Risk" }, zone: "Zone C", time: { ar: "رُصد قبل 5 دقائق", en: "Detected 5 minutes ago" }, confidence: "91%", status: { ar: "قيد التحقيق", en: "Investigating" }, severity: "critical" as const },
  { type: { ar: "مخالفة معدات الوقاية", en: "PPE Violation" }, zone: "Zone A", time: { ar: "رُصد قبل 8 دقائق", en: "Detected 8 minutes ago" }, confidence: "96%", status: { ar: "نشط", en: "Active" }, severity: "critical" as const },
  { type: { ar: "دخول منطقة غير آمنة", en: "Unsafe Area Entry" }, zone: "Zone B", time: { ar: "رُصد قبل 14 دقيقة", en: "Detected 14 minutes ago" }, confidence: "88%", status: { ar: "مفتوح", en: "Open" }, severity: "high" as const },
];

export const zones = [
  { zone: "A", risk: { ar: "منخفض", en: "Low Risk" }, severity: "low" as const },
  { zone: "B", risk: { ar: "متوسط", en: "Moderate Risk" }, severity: "moderate" as const },
  { zone: "C", risk: { ar: "حرج", en: "Critical" }, severity: "critical" as const },
  { zone: "D", risk: { ar: "منخفض", en: "Low Risk" }, severity: "low" as const },
  { zone: "E", risk: { ar: "عالٍ", en: "High Risk" }, severity: "high" as const },
];

export const incidentTrend = [
  { day: { ar: "الأربعاء", en: "Wed" }, incidents: 17 },
  { day: { ar: "الخميس", en: "Thu" }, incidents: 14 },
  { day: { ar: "الجمعة", en: "Fri" }, incidents: 11 },
  { day: { ar: "السبت", en: "Sat" }, incidents: 9 },
  { day: { ar: "الأحد", en: "Sun" }, incidents: 15 },
  { day: { ar: "الاثنين", en: "Mon" }, incidents: 13 },
  { day: { ar: "اليوم", en: "Today" }, incidents: 12 },
];

export const recentIncidents = [
  { incident: { ar: "مخالفة معدات الوقاية", en: "PPE Violation" }, location: "Zone A", severity: "high" as const, time: { ar: "قبل 10 دقائق", en: "10 min ago" }, status: { ar: "تمت المعالجة", en: "Resolved" }, statusTone: "positive" as const },
  { incident: { ar: "دخول منطقة غير آمنة", en: "Unsafe Area Entry" }, location: "Zone B", severity: "moderate" as const, time: { ar: "قبل 25 دقيقة", en: "25 min ago" }, status: { ar: "مفتوح", en: "Open" }, statusTone: "warning" as const },
  { incident: { ar: "رصد دخان", en: "Smoke Detection" }, location: "Zone C", severity: "critical" as const, time: { ar: "قبل 32 دقيقة", en: "32 min ago" }, status: { ar: "قيد التحقيق", en: "Investigating" }, statusTone: "critical" as const },
];

export function localize(locale: Locale, value: { ar: string; en: string }) {
  return value[locale];
}
