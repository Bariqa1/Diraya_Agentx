import { useMemo, useState } from "react";
import { Bot, CalendarDays, CheckCircle2, ClipboardCheck, MapPin, Search, ShieldAlert, User } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { Locale } from "@/lib/locale";
import {
  formatIncidentDate,
  incidentSummary,
  incidentZones,
  incidents,
  severityLabels,
  statusLabels,
  type IncidentRecord,
  type IncidentSeverity,
  type IncidentStatus,
} from "./incident-data";

const copy = {
  ar: {
    title: "سجل الحوادث",
    subtitle: "السجل الكامل للحوادث والمخالفات المسجلة",
    search: "البحث في سجل الحوادث...",
    severity: "مستوى الخطورة",
    status: "الحالة",
    location: "المنطقة",
    dateFrom: "من تاريخ",
    dateTo: "إلى تاريخ",
    all: "الكل",
    reset: "إعادة تعيين",
    results: (n: number) => `${n} حادث مطابق`,
    empty: "لا توجد حوادث مطابقة لعوامل التصفية.",
    columns: { id: "رقم الحادث", incident: "الحادث", person: "الموظف", severity: "مستوى الخطورة", location: "المنطقة", cause: "السبب", date: "التاريخ", time: "الوقت", handledBy: "تم التعامل بواسطة", resolution: "المعالجة", status: "الحالة" },
    details: "تفاصيل الحادث",
    basic: "المعلومات الأساسية",
    riskScore: "نسبة الخطر",
    person: "الموظف المرتبط بالحادث",
    employeeId: "الرقم الوظيفي",
    role: "الوظيفة",
    department: "القسم",
    locationAt: "الموقع وقت الحادث",
    cause: "سبب الحادث",
    detection: "تفاصيل الرصد الذكي",
    method: "طريقة الرصد",
    detected: "الاكتشاف",
    confidence: "نسبة الثقة",
    camera: "الكاميرا",
    detectionTime: "وقت الرصد",
    risk: "تقييم الخطر",
    riskLevel: "مستوى الخطر",
    assessment: "التقييم",
    action: "الإجراء المتخذ",
    handledBy: "تم التعامل مع الحادث بواسطة",
    resolution: "كيفية معالجة الحادث",
    timelineTitle: "المسار الزمني للحادث",
    openRow: "عرض تفاصيل الحادث",
  },
  en: {
    title: "Incident Log",
    subtitle: "Complete record of detected safety incidents and violations",
    search: "Search incident log...",
    severity: "Severity",
    status: "Status",
    location: "Location",
    dateFrom: "From date",
    dateTo: "To date",
    all: "All",
    reset: "Reset",
    results: (n: number) => `${n} matching incidents`,
    empty: "No incidents match the current filters.",
    columns: { id: "Incident ID", incident: "Incident", person: "Employee", severity: "Risk Level", location: "Location", cause: "Cause", date: "Date", time: "Time", handledBy: "Handled By", resolution: "Resolution", status: "Status" },
    details: "Incident Details",
    basic: "Basic Information",
    riskScore: "Risk Score",
    person: "Employee Involved",
    employeeId: "Employee ID",
    role: "Role",
    department: "Department",
    locationAt: "Location at time of incident",
    cause: "Incident Cause",
    detection: "AI Detection Details",
    method: "Detection method",
    detected: "Detection",
    confidence: "Confidence",
    camera: "Camera",
    detectionTime: "Detection time",
    risk: "Risk Assessment",
    riskLevel: "Risk Level",
    assessment: "Assessment",
    action: "Action Taken",
    handledBy: "Handled By",
    resolution: "Resolution",
    timelineTitle: "Incident Timeline",
    openRow: "View incident details",
  },
} as const;

const severityStyles: Record<IncidentSeverity, string> = {
  low: "bg-risk-low-soft text-positive-deep border-risk-low/25",
  medium: "bg-risk-moderate-soft text-risk-moderate-deep border-risk-moderate/30",
  high: "bg-risk-high-soft text-risk-high-deep border-risk-high/30",
  critical: "bg-risk-critical-soft text-risk-critical border-risk-critical/30",
};

const statusStyles: Record<IncidentStatus, string> = {
  open: "bg-risk-moderate-soft text-risk-moderate-deep border-risk-moderate/30",
  investigating: "bg-risk-high-soft text-risk-high-deep border-risk-high/30",
  resolved: "bg-positive-soft text-positive-deep border-positive/25",
};

const summaryStyles: Record<string, string> = {
  neutral: "text-foreground",
  critical: "text-risk-critical",
  warning: "text-risk-high-deep",
  positive: "text-positive-deep",
};

const severityOptions: Array<IncidentSeverity | "all"> = ["all", "low", "medium", "high", "critical"];
const statusOptions: Array<IncidentStatus | "all"> = ["all", "open", "investigating", "resolved"];

function Pill({ label, className }: { label: string; className: string }) {
  return <span className={cn("inline-flex items-center whitespace-nowrap rounded-md border px-2 py-0.5 text-[11px] font-bold", className)}>{label}</span>;
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={cn("mt-0.5 text-sm font-semibold text-foreground", mono && "font-mono")}>{value}</p>
    </div>
  );
}

function Panel({ icon: Icon, title, children }: { icon: typeof User; title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <h3 className="flex items-center gap-2 text-sm font-bold text-foreground"><Icon className="size-4 text-primary" />{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

const selectClass =
  "h-9 w-full rounded-md border border-input bg-background px-2.5 text-sm font-medium text-foreground shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/40";

export function IncidentLogContent({ locale }: { locale: Locale }) {
  const text = copy[locale];
  const arabic = locale === "ar";

  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState<IncidentSeverity | "all">("all");
  const [status, setStatus] = useState<IncidentStatus | "all">("all");
  const [zone, setZone] = useState<string>("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [selected, setSelected] = useState<IncidentRecord | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return incidents.filter((incident) => {
      if (severity !== "all" && incident.severity !== severity) return false;
      if (status !== "all" && incident.status !== status) return false;
      if (zone !== "all" && incident.zone !== zone) return false;
      if (from && incident.date < from) return false;
      if (to && incident.date > to) return false;
      if (!q) return true;
      const haystack = [
        incident.id,
        incident.zone,
        incident.type.ar,
        incident.type.en,
        incident.person.name.ar,
        incident.person.name.en,
        incident.cause.ar,
        incident.cause.en,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [query, severity, status, zone, from, to]);

  const resetFilters = () => {
    setQuery("");
    setSeverity("all");
    setStatus("all");
    setZone("all");
    setFrom("");
    setTo("");
  };

  return (
    <div className="mx-auto max-w-[1600px] space-y-4 p-4 sm:p-5 xl:px-7 xl:py-5">
      <div>
        <h1 className={cn("text-2xl font-bold text-foreground sm:text-3xl", !arabic && "font-display")}>{text.title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{text.subtitle}</p>
      </div>

      <section aria-label={text.title} className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {incidentSummary.map((item) => (
          <article key={item.label.en} className="rounded-lg border border-border bg-card px-3.5 py-3 shadow-sm">
            <p className="truncate text-xs font-semibold text-muted-foreground">{item.label[locale]}</p>
            <p className={cn("mt-1 font-display text-2xl font-bold tabular-nums sm:text-3xl", summaryStyles[item.tone])}>{item.value}</p>
          </article>
        ))}
      </section>

      <section className="rounded-lg border border-border bg-card p-3.5 shadow-sm sm:p-4">
        <div className="relative">
          <Search className="pointer-events-none absolute inset-y-0 start-3 my-auto size-4 text-muted-foreground" />
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={text.search} className="h-10 ps-9" aria-label={text.search} />
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <label className="min-w-0 text-xs font-semibold text-muted-foreground">
            {text.severity}
            <select className={cn(selectClass, "mt-1")} value={severity} onChange={(event) => setSeverity(event.target.value as IncidentSeverity | "all")}>
              {severityOptions.map((option) => (
                <option key={option} value={option}>{option === "all" ? text.all : severityLabels[option][locale]}</option>
              ))}
            </select>
          </label>
          <label className="min-w-0 text-xs font-semibold text-muted-foreground">
            {text.status}
            <select className={cn(selectClass, "mt-1")} value={status} onChange={(event) => setStatus(event.target.value as IncidentStatus | "all")}>
              {statusOptions.map((option) => (
                <option key={option} value={option}>{option === "all" ? text.all : statusLabels[option][locale]}</option>
              ))}
            </select>
          </label>
          <label className="min-w-0 text-xs font-semibold text-muted-foreground">
            {text.location}
            <select className={cn(selectClass, "mt-1")} value={zone} onChange={(event) => setZone(event.target.value)}>
              <option value="all">{text.all}</option>
              {incidentZones.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
          <label className="min-w-0 text-xs font-semibold text-muted-foreground">
            {text.dateFrom}
            <input type="date" className={cn(selectClass, "mt-1")} value={from} onChange={(event) => setFrom(event.target.value)} dir="ltr" />
          </label>
          <label className="min-w-0 text-xs font-semibold text-muted-foreground">
            {text.dateTo}
            <input type="date" className={cn(selectClass, "mt-1")} value={to} onChange={(event) => setTo(event.target.value)} dir="ltr" />
          </label>
        </div>
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs font-semibold text-muted-foreground">{text.results(filtered.length)}</p>
          <Button type="button" variant="outline" size="sm" onClick={resetFilters}>{text.reset}</Button>
        </div>
      </section>

      <section className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1080px] border-collapse text-start text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50 text-start text-[11px] uppercase tracking-wide text-muted-foreground">
                {[text.columns.id, text.columns.incident, text.columns.person, text.columns.severity, text.columns.location, text.columns.cause, text.columns.date, text.columns.time, text.columns.handledBy, text.columns.resolution, text.columns.status].map((label) => (
                  <th key={label} scope="col" className="whitespace-nowrap px-3 py-2.5 text-start font-bold">{label}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((incident) => (
                <tr
                  key={incident.id}
                  tabIndex={0}
                  role="button"
                  aria-label={`${text.openRow} ${incident.id}`}
                  onClick={() => setSelected(incident)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelected(incident);
                    }
                  }}
                  className="cursor-pointer transition-colors hover:bg-muted/60 focus-visible:bg-muted/60 focus-visible:outline-none"
                >
                  <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs font-bold text-primary">{incident.id}</td>
                  <td className="px-3 py-2.5 font-semibold text-foreground">{incident.type[locale]}</td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-foreground/80">{incident.person.name[locale]}</td>
                  <td className="px-3 py-2.5"><Pill label={severityLabels[incident.severity][locale]} className={severityStyles[incident.severity]} /></td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-foreground/80">{incident.zone}</td>
                  <td className="max-w-[220px] truncate px-3 py-2.5 text-muted-foreground">{incident.cause[locale]}</td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-foreground/80">{formatIncidentDate(incident.date, locale)}</td>
                  <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs text-foreground/80">{incident.time}</td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-foreground/80">{incident.handledBy.name[locale]}</td>
                  <td className="max-w-[220px] truncate px-3 py-2.5 text-muted-foreground">{incident.resolution[locale]}</td>
                  <td className="px-3 py-2.5"><Pill label={statusLabels[incident.status][locale]} className={statusStyles[incident.status]} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 ? <p className="px-4 py-8 text-center text-sm text-muted-foreground">{text.empty}</p> : null}
      </section>

      <Dialog open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-h-[88vh] max-w-3xl overflow-y-auto" dir={arabic ? "rtl" : "ltr"}>
          {selected ? (
            <>
              <DialogHeader className="text-start">
                <DialogTitle className="flex flex-wrap items-center gap-2 text-lg">
                  <span className="font-mono text-sm text-primary">{selected.id}</span>
                  <span>{selected.type[locale]}</span>
                  <Pill label={severityLabels[selected.severity][locale]} className={severityStyles[selected.severity]} />
                  <Pill label={statusLabels[selected.status][locale]} className={statusStyles[selected.status]} />
                </DialogTitle>
                <DialogDescription>{text.details}</DialogDescription>
              </DialogHeader>

              <div className="space-y-3">
                <Panel icon={ShieldAlert} title={text.basic}>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    <Field label={text.columns.id} value={selected.id} mono />
                    <Field label={text.columns.incident} value={selected.type[locale]} />
                    <Field label={text.severity} value={severityLabels[selected.severity][locale]} />
                    <Field label={text.riskScore} value={`${selected.riskScore}%`} />
                    <Field label={text.location} value={selected.zone} />
                    <Field label={text.columns.date} value={`${formatIncidentDate(selected.date, locale)} · ${selected.time}`} />
                  </div>
                </Panel>

                <Panel icon={User} title={text.person}>
                  <p className="text-base font-bold text-foreground">{selected.person.name[locale]}</p>
                  <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <Field label={text.employeeId} value={selected.person.employeeId} mono />
                    <Field label={text.role} value={selected.person.role[locale]} />
                    <Field label={text.department} value={selected.person.department[locale]} />
                    <Field label={text.locationAt} value={selected.zone} />
                  </div>
                </Panel>

                <Panel icon={MapPin} title={text.cause}>
                  <p className="text-sm leading-7 text-foreground/85">{selected.cause[locale]}</p>
                </Panel>

                <Panel icon={Bot} title={text.detection}>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                    <Field label={text.method} value={selected.detection.method} mono />
                    <Field label={text.detected} value={selected.detection.className[locale]} />
                    <Field label={text.confidence} value={`${selected.detection.confidence}%`} />
                    <Field label={text.camera} value={selected.detection.camera} />
                    <Field label={text.detectionTime} value={selected.detection.time} mono />
                  </div>
                </Panel>

                <Panel icon={ShieldAlert} title={text.risk}>
                  <div className="flex flex-wrap items-center gap-3">
                    <Pill label={`${text.riskLevel}: ${severityLabels[selected.severity][locale]}`} className={severityStyles[selected.severity]} />
                    <span className="font-display text-xl font-bold tabular-nums text-foreground">{selected.riskScore}%</span>
                  </div>
                  <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
                    <div className={cn("h-full rounded-full", selected.severity === "critical" ? "bg-risk-critical" : selected.severity === "high" ? "bg-risk-high" : selected.severity === "medium" ? "bg-risk-moderate" : "bg-risk-low")} style={{ width: `${selected.riskScore}%` }} />
                  </div>
                  <p className="mt-3 text-sm leading-7 text-foreground/85"><span className="font-semibold">{text.assessment}: </span>{selected.riskAssessment[locale]}</p>
                </Panel>

                <Panel icon={ClipboardCheck} title={text.action}>
                  <p className="text-sm leading-7 text-foreground/85">{selected.actionTaken[locale]}</p>
                  <div className="mt-3 rounded-md border border-border bg-muted/40 p-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{text.handledBy}</p>
                    <p className="mt-1 text-sm font-bold text-foreground">{selected.handledBy.name[locale]}</p>
                    <p className="text-xs text-muted-foreground">{selected.handledBy.role[locale]}</p>
                    <p className="mt-1 text-xs text-foreground/75">{selected.handledBy.responseNote[locale]}</p>
                  </div>
                </Panel>

                <Panel icon={CheckCircle2} title={text.resolution}>
                  <p className="text-sm leading-7 text-foreground/85">{selected.resolution[locale]}</p>
                  <div className="mt-2"><Pill label={statusLabels[selected.status][locale]} className={statusStyles[selected.status]} /></div>
                </Panel>

                <Panel icon={CalendarDays} title={text.timelineTitle}>
                  <ol className="space-y-0">
                    {selected.timeline.map((step, index) => (
                      <li key={`${step.time}-${index}`} className="grid grid-cols-[auto_auto_minmax(0,1fr)] items-start gap-3">
                        <span className="w-12 pt-0.5 font-mono text-xs font-bold text-foreground">{step.time}</span>
                        <span className="flex flex-col items-center self-stretch">
                          <span className="mt-1 size-2.5 shrink-0 rounded-full bg-primary" />
                          {index < selected.timeline.length - 1 ? <span className="w-px flex-1 bg-border" /> : null}
                        </span>
                        <span className="pb-4 text-sm text-foreground/85">{step.label[locale]}</span>
                      </li>
                    ))}
                  </ol>
                </Panel>
              </div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
