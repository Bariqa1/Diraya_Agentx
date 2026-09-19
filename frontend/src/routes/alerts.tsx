import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, CheckCircle2, Clock3, MapPin, Radio, Siren } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { cn } from "@/lib/utils";
import { localeSearch, type Locale } from "@/lib/locale";

const BACKEND_URL = (import.meta.env["VITE_ENVIRONMENT_AGENT_URL"] as string | undefined)?.replace(/\/$/, "") || "http://localhost:8000";

type AlertSeverity = "critical" | "warning";

type AlertRecordItem = {
  id: string;
  time: { ar: string; en: string };
  zone: { ar: string; en: string };
  type: { ar: string; en: string };
  severity: AlertSeverity;
  status: { ar: string; en: string };
  action: { ar: string; en: string };
  isLive?: boolean;
};

const alertRecords: AlertRecordItem[] = [
  { id: "ALT-024", time: { ar: "قبل دقيقة", en: "1 min ago" }, zone: { ar: "المنطقة C", en: "Zone C" }, type: { ar: "عدم ارتداء الخوذة", en: "No Helmet" }, severity: "critical", status: { ar: "نشط", en: "Active" }, action: { ar: "تم إشعار مشرف المنطقة", en: "Zone supervisor notified" } },
  { id: "ALT-023", time: { ar: "قبل 5 دقائق", en: "5 min ago" }, zone: { ar: "المنطقة C", en: "Zone C" }, type: { ar: "اشتباه دخان", en: "Possible Smoke" }, severity: "critical", status: { ar: "قيد الاستجابة", en: "Responding" }, action: { ar: "تم إرسال فريق الطوارئ", en: "Emergency team dispatched" } },
  { id: "ALT-022", time: { ar: "قبل 14 دقيقة", en: "14 min ago" }, zone: { ar: "المنطقة B", en: "Zone B" }, type: { ar: "دخول منطقة غير آمنة", en: "Unsafe Area Entry" }, severity: "warning", status: { ar: "نشط", en: "Active" }, action: { ar: "تم تعليق تصريح الدخول", en: "Access permit suspended" } },
  { id: "ALT-021", time: { ar: "قبل 18 دقيقة", en: "18 min ago" }, zone: { ar: "المنطقة A", en: "Zone A" }, type: { ar: "مخالفة معدات الوقاية", en: "PPE Violation" }, severity: "warning", status: { ar: "نشط", en: "Active" }, action: { ar: "تم تنبيه الموظف", en: "Employee notified" } },
  { id: "ALT-020", time: { ar: "قبل 42 دقيقة", en: "42 min ago" }, zone: { ar: "المنطقة D", en: "Zone D" }, type: { ar: "انسكاب على الممر", en: "Walkway Spill" }, severity: "warning", status: { ar: "تمت المعالجة", en: "Resolved" }, action: { ar: "تم عزل وتنظيف المنطقة", en: "Area isolated and cleaned" } },
  { id: "ALT-019", time: { ar: "قبل ساعة", en: "1 hr ago" }, zone: { ar: "المنطقة E", en: "Zone E" }, type: { ar: "اقتراب غير آمن من مركبة", en: "Unsafe Vehicle Proximity" }, severity: "warning", status: { ar: "تمت المعالجة", en: "Resolved" }, action: { ar: "تم تنبيه السائق", en: "Driver notified" } },
];

const copy = {
  ar: {
    title: "سجل التنبيهات",
    description: "جميع تنبيهات السلامة المرصودة من نماذج الذكاء الاصطناعي وكاميرات الموقع.",
    filters: { all: "الكل", critical: "حرج", warning: "تحذير" },
    columns: { time: "الوقت", zone: "المنطقة", type: "نوع التنبيه", severity: "مستوى الخطورة", status: "الحالة", action: "الإجراء" },
    severity: { critical: "حرج", warning: "تحذير" },
    empty: "لا توجد تنبيهات مطابقة.",
    liveBadge: "مباشر من الكاميرا",
  },
  en: {
    title: "Alert Log",
    description: "All detected safety alerts from computer vision models and site cameras.",
    filters: { all: "All", critical: "Critical", warning: "Warning" },
    columns: { time: "Time", zone: "Area", type: "Alert Type", severity: "Severity", status: "Status", action: "Action" },
    severity: { critical: "Critical", warning: "Warning" },
    empty: "No matching alerts.",
    liveBadge: "Live Detection",
  },
} as const;

const severityStyles: Record<AlertSeverity, string> = {
  critical: "border-risk-critical/30 bg-risk-critical-soft text-risk-critical",
  warning: "border-risk-high/30 bg-risk-high-soft text-risk-high-deep",
};

export const Route = createFileRoute("/alerts")({
  validateSearch: localeSearch,
  head: () => ({ meta: [{ title: "سجل التنبيهات | دِراية — DIRAYA" }, { name: "description", content: "جميع تنبيهات السلامة المرصودة وحالة الاستجابة لها." }, { property: "og:title", content: "Alert Log | DIRAYA" }, { property: "og:description", content: "All detected safety alerts and their response status." }, { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary" }] }),
  component: Page,
});

function Page() {
  const { lang } = Route.useSearch();
  return <DashboardShell locale={lang} currentPath="/alerts"><AlertLog locale={lang} /></DashboardShell>;
}

function AlertLog({ locale }: { locale: Locale }) {
  const [filter, setFilter] = useState<AlertSeverity | "all">("all");
  const [alerts, setAlerts] = useState<AlertRecordItem[]>(alertRecords);
  const text = copy[locale];
  const arabic = locale === "ar";

  useEffect(() => {
    let mounted = true;
    async function fetchLiveAlerts() {
      try {
        const res = await fetch(`${BACKEND_URL}/alerts?limit=25`);
        if (!res.ok) return;
        const data = await res.json();
        if (data && Array.isArray(data.alerts) && data.alerts.length > 0) {
          const liveItems: AlertRecordItem[] = data.alerts.map((item: any, idx: number) => {
            const isCrit = item.severity === "CRITICAL" || Boolean(item.fall_detected);
            const missing = Array.isArray(item.missing_ppe) && item.missing_ppe.length > 0
              ? item.missing_ppe.slice(0, 3).join(", ")
              : undefined;
            const alertTypeAr = item.fall_detected
              ? "رصد سقوط عامل"
              : missing
              ? `نقص معدات (${missing})`
              : item.zone_violation
              ? "اختراق منطقة محظورة"
              : "تنبيه سلامة تشغيلي";
            const alertTypeEn = item.fall_detected
              ? "Worker Fall Detected"
              : missing
              ? `Missing PPE (${missing})`
              : item.zone_violation
              ? "Restricted Zone Breach"
              : "Operational Safety Alert";

            const zoneName = item.zone || "Zone C";
            const zoneAr = zoneName === "Welding Area" ? "منطقة اللحام" : zoneName;

            return {
              id: item.incident_id || `LIVE-${idx + 1}`,
              time: { ar: "الآن (بث حي)", en: "Just now (Live)" },
              zone: { ar: zoneAr, en: zoneName },
              type: { ar: alertTypeAr, en: alertTypeEn },
              severity: isCrit ? ("critical" as const) : ("warning" as const),
              status: { ar: "نشط", en: "Active" },
              action: {
                ar: item.escalation === "safety_officer" ? "تم إشعار مسؤول السلامة فوراً" : "تم تنبيه المشرف الميداني",
                en: item.escalation === "safety_officer" ? "Safety officer alerted immediately" : "Field supervisor notified",
              },
              isLive: true,
            };
          });

          if (mounted) {
            // Merge live alerts first, followed by default base records
            setAlerts([...liveItems, ...alertRecords]);
          }
        }
      } catch {
        // Keeps pre-seeded fallback alertRecords if backend fails
      }
    }

    fetchLiveAlerts();
    return () => {
      mounted = false;
    };
  }, []);

  const visibleAlerts = filter === "all" ? alerts : alerts.filter((alert) => alert.severity === filter);

  return (
    <div className="mx-auto max-w-[1600px] space-y-4 p-4 sm:p-5 xl:px-7 xl:py-5">
      <div>
        <h1 className={cn("text-2xl font-bold text-foreground sm:text-3xl", !arabic && "font-display")}>{text.title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{text.description}</p>
      </div>

      <section className="overflow-hidden rounded-lg border border-border bg-card shadow-sm" aria-label={text.title}>
        <div className="flex flex-wrap items-center gap-2 border-b border-border p-3 sm:p-4">
          {(["all", "critical", "warning"] as const).map((option) => (
            <Button key={option} type="button" size="sm" variant={filter === option ? "default" : "outline"} onClick={() => setFilter(option)} aria-pressed={filter === option}>
              {option === "all" ? <Siren /> : <AlertTriangle />}
              {text.filters[option]}
            </Button>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[880px] text-start text-sm">
            <thead className="border-b border-border bg-muted/45 text-xs font-semibold text-muted-foreground">
              <tr>{Object.values(text.columns).map((label) => <th key={label} scope="col" className="px-4 py-3 text-start">{label}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-border">
              {visibleAlerts.map((alert) => (
                <tr key={alert.id} className="transition-colors hover:bg-muted/30">
                  <td className="whitespace-nowrap px-4 py-3.5 text-muted-foreground">
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-center">
                      <span className="inline-flex items-center gap-1.5"><Clock3 className="size-3.5" />{alert.time[locale]}</span>
                      {alert.isLive ? (
                        <span className="inline-flex w-fit items-center gap-1 rounded-full bg-risk-critical/15 px-1.5 py-0.5 text-[10px] font-bold text-risk-critical">
                          <Radio className="size-2.5 animate-pulse" />
                          {text.liveBadge}
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3.5 font-semibold text-foreground"><span className="inline-flex items-center gap-1.5"><MapPin className="size-3.5 text-primary" />{alert.zone[locale]}</span></td>
                  <td className="px-4 py-3.5 font-semibold text-foreground">{alert.type[locale]}</td>
                  <td className="px-4 py-3.5"><span className={cn("inline-flex rounded-md border px-2 py-0.5 text-xs font-bold", severityStyles[alert.severity])}>{text.severity[alert.severity]}</span></td>
                  <td className="whitespace-nowrap px-4 py-3.5 text-foreground"><span className="inline-flex items-center gap-1.5"><span className={cn("size-2 rounded-full", alert.status.en === "Resolved" ? "bg-positive" : alert.severity === "critical" ? "bg-risk-critical" : "bg-risk-high")} />{alert.status[locale]}</span></td>
                  <td className="px-4 py-3.5 text-muted-foreground"><span className="inline-flex items-center gap-1.5"><CheckCircle2 className="size-3.5 shrink-0 text-positive-deep" />{alert.action[locale]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {visibleAlerts.length === 0 ? <p className="p-8 text-center text-sm text-muted-foreground">{text.empty}</p> : null}
        </div>
      </section>
    </div>
  );
}
