import { useEffect, useState } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  HardHat,
  Info,
  MapPin,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Locale } from "@/lib/locale";

const BACKEND_URL =
  ((import.meta.env["VITE_ENVIRONMENT_AGENT_URL"] || import.meta.env["VITE_API_URL"]) as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

type ZoneItem = {
  id: string;
  name: { ar: string; en: string };
  code: string;
  level: "critical" | "warning" | "safe";
  riskScore: number;
  authorizedHelmet: { ar: string; en: string; colorClass: string };
  requiredPpe: { ar: string[]; en: string[] };
  activeHazards: { ar: string; en: string };
  description: { ar: string; en: string };
};

const preseededZones: ZoneItem[] = [
  {
    id: "ZONE_SUBSTATION",
    code: "ZONE-A",
    name: { ar: "محطة الجهد العالي والكهرباء", en: "Electrical Substation" },
    level: "critical",
    riskScore: 88,
    authorizedHelmet: {
      ar: "خوذة زرقاء (فني كهرباء معتمد)",
      en: "Blue Helmet (Certified Electrician)",
      colorClass: "bg-blue-600 text-white",
    },
    requiredPpe: {
      ar: ["خوذة غير موصلة (Class E)", "قفازات عازلة 1000V", "حذاء عازل للكهرباء"],
      en: ["Class E Hard Hat", "Dielectric Gloves 1000V", "Electrical Hazard Boots"],
    },
    activeHazards: {
      ar: "صعق كهربائي، قوس وميضي (Arc Flash)، حقول كهرومغناطيسية",
      en: "High Voltage Shock, Arc Flash, High EMF",
    },
    description: {
      ar: "منطقة حظر صارمة؛ يُمنع دخول أي شخص بدون تصريح عزل كهربائي ساري.",
      en: "Strictly restricted; entry without valid LOTO lock permit is prohibited.",
    },
  },
  {
    id: "ZONE_NO_GO_CRANE",
    code: "ZONE-C",
    name: { ar: "نطاق عمل الرافعة الثقيلة", en: "Heavy Crane Swing Area" },
    level: "critical",
    riskScore: 92,
    authorizedHelmet: {
      ar: "خوذة خضراء (ضابط سلامة) / ريجر",
      en: "Green Helmet (Safety Officer) / Rigger",
      colorClass: "bg-emerald-600 text-white",
    },
    requiredPpe: {
      ar: ["خوذة سلامة مع حزام ذقن", "سترة عاكسة فئة 3", "أحذية أمان مقواة"],
      en: ["Hard Hat with Chin Strap", "Class 3 High-Vis Vest", "Steel-toe Boots"],
    },
    activeHazards: {
      ar: "سقوط أحمال، مسار تأرجح ذراع الرافعة، حركة آليات ثقيلة",
      en: "Suspended Load Drop, Boom Swing Radius, Heavy Machinery",
    },
    description: {
      ar: "منطقة خطرة للغاية؛ يمنع التواجد تحت مسار الحمل المعلق إطلاقاً.",
      en: "Critical hazard zone; staying beneath suspended loads is prohibited.",
    },
  },
  {
    id: "ZONE_WELDING",
    code: "ZONE-B",
    name: { ar: "ورشة اللحام والقص الحراري", en: "Welding & Thermal Fabrication" },
    level: "warning",
    riskScore: 65,
    authorizedHelmet: {
      ar: "خوذة برتقالية / صفراء (لحّام معتمد)",
      en: "Orange / Yellow Helmet (Certified Welder)",
      colorClass: "bg-amber-600 text-white",
    },
    requiredPpe: {
      ar: ["درع وجه لحام", "قفازات جلدية حرارية", "بدلة مقاومة للهب", "حذاء سلامة"],
      en: ["Welding Face Shield", "Heat-resistant Gloves", "Flame-retardant Coverall", "Safety Shoes"],
    },
    activeHazards: {
      ar: "تطاير الشرر، درجات حرارة مرتفعة، أشعة فوق بنفسجية، أدخنة لحام",
      en: "Hot Sparks, UV Radiation, Fume Inhalation, Burn Hazards",
    },
    description: {
      ar: "يلزم تشغيل شفاط الأدخنة وتجهيز طفاية حريق بودرة جافة على بُعد أقل من 5 أمتار.",
      en: "Fume exhaust must run continuously and fire extinguisher within 5m.",
    },
  },
  {
    id: "ZONE_CHEMICAL",
    code: "ZONE-D",
    name: { ar: "مستودع الكيماويات والطلاء", en: "Chemical & Solvent Storage" },
    level: "warning",
    riskScore: 58,
    authorizedHelmet: {
      ar: "خوذة صفراء (فني مواد خطرة)",
      en: "Yellow Helmet (Hazmat Handler)",
      colorClass: "bg-yellow-500 text-black",
    },
    requiredPpe: {
      ar: ["قناع تنفس فلتر كيميائي", "نظارات حماية محكمة", "مريلة قفازات كيميائية"],
      en: ["Chemical Vapor Respirator", "Sealed Splash Goggles", "Nitrile Gloves & Apron"],
    },
    activeHazards: {
      ar: "أبخرة عضوية قابلة للاشتعال، انسكابات مواد حارقة",
      en: "Flammable Solvent Vapors, Corrosive Liquid Splash",
    },
    description: {
      ar: "محظور التدخين أو استخدام أي أدوات تصدر شرراً في محيط 15 متراً.",
      en: "No open flames or sparking tools within 15 meters perimeter.",
    },
  },
  {
    id: "ZONE_ASSEMBLY",
    code: "ZONE-E",
    name: { ar: "مسار التجميع والخدمات اللوجستية", en: "Assembly & Logistics Corridor" },
    level: "safe",
    riskScore: 22,
    authorizedHelmet: {
      ar: "عام (كافة الكوادر المصرح لها)",
      en: "General (All Authorized Personnel)",
      colorClass: "bg-slate-600 text-white",
    },
    requiredPpe: {
      ar: ["خوذة أمان قياسية", "سترة عاكسة", "حذاء أمان"],
      en: ["Standard Hard Hat", "High-Vis Vest", "Safety Shoes"],
    },
    activeHazards: {
      ar: "حركة رافعات شوكية خفيفة، ممرات سير المشاة",
      en: "Light Forklift Traffic, Pedestrian Crossing",
    },
    description: {
      ar: "منطقة تشغيلية آمنة نسبياً مع الالتزام بمسارات المشاة المحددة باللون الأصفر.",
      en: "Safe operational zone. Walk strictly inside yellow designated walkways.",
    },
  },
];

const copy = {
  ar: {
    title: "المخاطر وصلاحيات الدخول",
    subtitle: "تصاريح المناطق وألوان الخوذ ومحيط لوحات الخطر بالذكاء الاصطناعي",
    summaryTotal: "إجمالي المناطق",
    summaryCritical: "مناطق حرجة جداً",
    summaryWarnings: "مناطق تحذيرية",
    summarySafe: "مناطق آمنة",
    zonesTitle: "مناطق المنشأة ومستويات الخطر",
    authorizedRole: "الخوذة المصرح لها:",
    mandatoryPpe: "معدات الوقاية الإلزامية:",
    hazards: "المخاطر المرصودة:",
    riskScore: "مؤشر الخطورة:",
    filterAll: "الكل",
    filterCritical: "حرجة",
    filterWarning: "تحذيرية",
    filterSafe: "آمنة",
    simulatorTitle: "أداة الفحص التفاعلي لصلاحيات الدخول الميدانية",
    simulatorSubtitle: "اختر دور العامل والمنطقة للتحقق الحي عبر وكيل السلامة وصلاحيات الدخول",
    selectRole: "دور العامل ولون الخوذة:",
    selectZone: "المنطقة المستهدفة:",
    checkBtn: "فحص الصلاحية الآن",
    checking: "جارٍ فحص القواعد وصلاحيات الدخول...",
    resultAuthorized: "مصرح بالدخول ✅",
    resultDenied: "محظور الدخول ⛔",
  },
  en: {
    title: "Risks & Access Permissions",
    subtitle: "Physical RBAC, helmet roles, and AI signboard safety hazard perimeters",
    summaryTotal: "Total Zones",
    summaryCritical: "Critical Risk",
    summaryWarnings: "Warning Zones",
    summarySafe: "Safe Zones",
    zonesTitle: "Facility Zones & Risk Levels",
    authorizedRole: "Authorized Helmet:",
    mandatoryPpe: "Required PPE:",
    hazards: "Identified Hazards:",
    riskScore: "Risk Index:",
    filterAll: "All",
    filterCritical: "Critical",
    filterWarning: "Warning",
    filterSafe: "Safe",
    simulatorTitle: "Interactive Live Zone Access Inspector",
    simulatorSubtitle: "Select worker helmet role and target zone to evaluate access permissions via Safety Agent",
    selectRole: "Worker Role & Helmet:",
    selectZone: "Target Zone:",
    checkBtn: "Evaluate Access Now",
    checking: "Evaluating rules & permissions...",
    resultAuthorized: "Access Authorized ✅",
    resultDenied: "Access Denied ⛔",
  },
} as const;

export function RiskMapContent({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const arabic = locale === "ar";
  const [filter, setFilter] = useState<"all" | "critical" | "warning" | "safe">("all");
  const [selectedZone, setSelectedZone] = useState<string>("ZONE_SUBSTATION");
  const [selectedRole, setSelectedRole] = useState<string>("electrician");
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [evalResult, setEvalResult] = useState<any>(null);

  const zones = filter === "all" ? preseededZones : preseededZones.filter((z) => z.level === filter);

  async function handleEvaluate() {
    setEvaluating(true);
    setEvalResult(null);
    try {
      const res = await fetch(`${BACKEND_URL}/zones/evaluate-access`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          worker_role: selectedRole,
          zone_id: selectedZone,
          carried_tools: ["insulated_toolkit"],
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setEvalResult(data);
      } else {
        throw new Error("Backend error");
      }
    } catch {
      // Local fallback logic
      const isElectrician = selectedRole === "electrician" || selectedRole === "Blue";
      const isSubstation = selectedZone === "ZONE_SUBSTATION";
      const isCrane = selectedZone === "ZONE_NO_GO_CRANE";

      if (isSubstation && !isElectrician) {
        setEvalResult({
          authorized: false,
          risk_score: 95,
          decision: "DENIED",
          reason: arabic
            ? "غير مصرح: محطة الكهرباء تتطلب خوذة زرقاء (فني كهربائي مؤهل) وقفازات عازلة."
            : "Denied: Substation requires Blue Helmet (Certified Electrician) and dielectric gloves.",
        });
      } else if (isCrane && selectedRole === "laborer") {
        setEvalResult({
          authorized: false,
          risk_score: 90,
          decision: "DENIED",
          reason: arabic
            ? "غير مصرح: يمنع تواجد العمالة العادية تحت دائرة الرافعة الثقيلة أثناء الرفع."
            : "Denied: General laborers are prohibited inside crane lift perimeter.",
        });
      } else {
        setEvalResult({
          authorized: true,
          risk_score: 25,
          decision: "AUTHORIZED",
          reason: arabic
            ? "مصرح: تطابق متطلبات الدور ومعدات الوقاية مع معايير المنطقة."
            : "Authorized: Worker role and PPE match zone safety criteria.",
        });
      }
    } finally {
      setEvaluating(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-4 sm:p-5 xl:px-7 xl:py-6" dir={arabic ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className={cn("text-2xl font-bold text-foreground sm:text-3xl", !arabic && "font-display")}>
            {t.title}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{t.subtitle}</p>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:gap-4">
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <p className="text-xs text-muted-foreground">{t.summaryTotal}</p>
          <p className="mt-1 text-2xl font-bold text-foreground">5</p>
        </div>
        <div className="rounded-xl border border-risk-critical/30 bg-risk-critical-soft p-4 shadow-sm">
          <p className="text-xs font-medium text-risk-critical">{t.summaryCritical}</p>
          <p className="mt-1 text-2xl font-bold text-risk-critical">2</p>
        </div>
        <div className="rounded-xl border border-risk-high/30 bg-risk-high-soft p-4 shadow-sm">
          <p className="text-xs font-medium text-risk-high-deep">{t.summaryWarnings}</p>
          <p className="mt-1 text-2xl font-bold text-risk-high-deep">2</p>
        </div>
        <div className="rounded-xl border border-positive/30 bg-positive-soft p-4 shadow-sm">
          <p className="text-xs font-medium text-positive-deep">{t.summarySafe}</p>
          <p className="mt-1 text-2xl font-bold text-positive-deep">1</p>
        </div>
      </div>

      {/* Interactive Access Evaluation Simulator */}
      <div className="rounded-xl border border-primary/20 bg-primary/5 p-5 shadow-sm sm:p-6">
        <div className="flex items-center gap-2 text-primary font-bold text-base sm:text-lg">
          <ShieldAlert className="size-5" />
          <h2>{t.simulatorTitle}</h2>
        </div>
        <p className="mt-1 text-xs sm:text-sm text-muted-foreground">{t.simulatorSubtitle}</p>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-foreground">{t.selectRole}</label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="electrician">{arabic ? "فني كهربائي (خوذة زرقاء)" : "Electrician (Blue Helmet)"}</option>
              <option value="welder">{arabic ? "لحّام معتمد (خوذة برتقالية)" : "Certified Welder (Orange Helmet)"}</option>
              <option value="safety_officer">{arabic ? "ضابط سلامة (خوذة خضراء)" : "Safety Officer (Green Helmet)"}</option>
              <option value="laborer">{arabic ? "عامل عام (خوذة صفراء)" : "General Laborer (Yellow Helmet)"}</option>
              <option value="visitor">{arabic ? "زائر / متدرب (خوذة بيضاء)" : "Visitor / Trainee (White Helmet)"}</option>
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-semibold text-foreground">{t.selectZone}</label>
            <select
              value={selectedZone}
              onChange={(e) => setSelectedZone(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {preseededZones.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.code} — {z.name[locale]}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <Button
              onClick={handleEvaluate}
              disabled={evaluating}
              className="w-full h-10 font-bold bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {evaluating ? t.checking : t.checkBtn}
            </Button>
          </div>
        </div>

        {evalResult && (
          <div
            className={cn(
              "mt-4 flex flex-col gap-2 rounded-lg border p-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in",
              evalResult.authorized
                ? "border-positive/30 bg-positive-soft text-positive-deep"
                : "border-risk-critical/30 bg-risk-critical-soft text-risk-critical"
            )}
          >
            <div className="flex items-start gap-3">
              {evalResult.authorized ? (
                <ShieldCheck className="size-6 shrink-0 text-positive" />
              ) : (
                <AlertOctagon className="size-6 shrink-0 text-risk-critical" />
              )}
              <div>
                <p className="font-bold text-sm">
                  {evalResult.authorized ? t.resultAuthorized : t.resultDenied}
                </p>
                <p className="mt-0.5 text-xs opacity-90">{evalResult.reason}</p>
              </div>
            </div>
            {evalResult.risk_score !== undefined && (
              <div className="shrink-0 font-mono text-xs font-bold px-2.5 py-1 rounded bg-black/10 dark:bg-white/10">
                {t.riskScore} {evalResult.risk_score}%
              </div>
            )}
          </div>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant={filter === "all" ? "default" : "outline"}
          onClick={() => setFilter("all")}
        >
          {t.filterAll}
        </Button>
        <Button
          size="sm"
          variant={filter === "critical" ? "default" : "outline"}
          onClick={() => setFilter("critical")}
          className={filter === "critical" ? "bg-risk-critical text-white" : ""}
        >
          {t.filterCritical}
        </Button>
        <Button
          size="sm"
          variant={filter === "warning" ? "default" : "outline"}
          onClick={() => setFilter("warning")}
          className={filter === "warning" ? "bg-amber-600 text-white" : ""}
        >
          {t.filterWarning}
        </Button>
        <Button
          size="sm"
          variant={filter === "safe" ? "default" : "outline"}
          onClick={() => setFilter("safe")}
          className={filter === "safe" ? "bg-emerald-600 text-white" : ""}
        >
          {t.filterSafe}
        </Button>
      </div>

      {/* Zones Grid */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {zones.map((zone) => {
          const isCrit = zone.level === "critical";
          const isWarn = zone.level === "warning";
          return (
            <div
              key={zone.id}
              className={cn(
                "flex flex-col justify-between rounded-xl border bg-card p-5 shadow-sm transition-all hover:shadow-md",
                isCrit && "border-risk-critical/30",
                isWarn && "border-risk-high/30",
                zone.level === "safe" && "border-positive/30"
              )}
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs font-bold text-muted-foreground">{zone.code}</span>
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-0.5 text-xs font-bold",
                      isCrit && "bg-risk-critical-soft text-risk-critical",
                      isWarn && "bg-risk-high-soft text-risk-high-deep",
                      zone.level === "safe" && "bg-positive-soft text-positive-deep"
                    )}
                  >
                    {isCrit ? t.filterCritical : isWarn ? t.filterWarning : t.filterSafe} ({zone.riskScore}%)
                  </span>
                </div>

                <h3 className="mt-2 text-lg font-bold text-foreground">{zone.name[locale]}</h3>
                <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                  {zone.description[locale]}
                </p>

                <div className="mt-4 space-y-2.5 text-xs border-t border-border pt-3">
                  <div>
                    <span className="font-semibold text-foreground flex items-center gap-1.5">
                      <HardHat className="size-3.5 text-primary" />
                      {t.authorizedRole}
                    </span>
                    <span className={cn("mt-1 inline-block rounded px-2 py-0.5 font-medium text-[11px]", zone.authorizedHelmet.colorClass)}>
                      {zone.authorizedHelmet[locale]}
                    </span>
                  </div>

                  <div>
                    <span className="font-semibold text-foreground flex items-center gap-1.5">
                      <Shield className="size-3.5 text-primary" />
                      {t.mandatoryPpe}
                    </span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {zone.requiredPpe[locale].map((ppe) => (
                        <span key={ppe} className="rounded bg-muted px-2 py-0.5 text-[11px] text-foreground">
                          {ppe}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="font-semibold text-foreground flex items-center gap-1.5">
                      <AlertTriangle className="size-3.5 text-amber-500" />
                      {t.hazards}
                    </span>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">{zone.activeHazards[locale]}</p>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
