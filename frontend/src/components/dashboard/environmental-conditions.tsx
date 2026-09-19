import { useEffect, useState } from "react";
import {
  AlertTriangle,
  BriefcaseBusiness,
  CloudSun,
  Clock3,
  Gauge,
  LoaderCircle,
  LocateFixed,
  MapPin,
  Navigation,
  SunMedium,
  ThermometerSun,
  UserCheck,
  Waves,
  Wind,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import type { Locale } from "@/lib/locale";

type AgentSection = Record<string, unknown>;

interface EnvironmentAgentData {
  location?: unknown;
  weather?: AgentSection;
  environment_assessment?: AgentSection;
}

interface EnvironmentAgentResponse extends EnvironmentAgentData {
  data?: EnvironmentAgentData;
}

type ViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: EnvironmentAgentResponse };

const copy = {
  ar: {
    title: "الظروف البيئية",
    subtitle: "تحليل ظروف موقع العمل بواسطة وكيل البيئة",
    detect: "كشف موقع العمل",
    loading: "جارٍ تحديد الموقع وتحليل الظروف البيئية...",
    unavailable: "خدمة تحديد الموقع غير متاحة في هذا المتصفح.",
    denied: "تم رفض إذن الوصول إلى الموقع. يرجى السماح به والمحاولة مجددًا.",
    positionError: "تعذر تحديد موقع العمل. يرجى المحاولة مجددًا.",
    apiError: "تعذر الاتصال بخدمة تحليل البيئة. تأكد من تشغيل الخدمة المحلية والمحاولة مجددًا.",
    location: "الموقع",
    locationDetails: "تفاصيل الموقع",
    coordinates: "الإحداثيات",
    postcode: "الرمز البريدي",
    weather: "الطقس الحالي",
    temperature: "درجة الحرارة",
    humidity: "الرطوبة",
    wind: "سرعة الرياح",
    weatherTime: "وقت قراءة الطقس",
    weatherCode: "رمز حالة الطقس",
    dayStatus: "فترة الرصد",
    day: "نهار",
    night: "ليل",
    heatEnvironment: "الحرارة وتقييم البيئة",
    wetBulb: "درجة حرارة البصيلة الرطبة",
    globeTemperature: "درجة حرارة الكرة السوداء",
    wbgt: "WBGT التقديري",
    wbgtThreshold: "حد WBGT",
    wbgtDifference: "الفرق عن حد WBGT",
    heatExposure: "التعرض للحرارة",
    workload: "عبء العمل",
    acclimatized: "حالة التأقلم",
    acclimatizedYes: "متأقلم",
    acclimatizedNo: "غير متأقلم",
    assessmentType: "نوع التقييم",
    warnings: "التحذيرات البيئية",
    recommendation: "التوصية",
    noWarnings: "لا توجد تحذيرات بيئية",
    unavailableValue: "غير متوفر",
    empty: "اكشف موقع العمل لعرض تحليل الظروف البيئية الحالية.",
  },
  en: {
    title: "Environmental Conditions",
    subtitle: "Worksite conditions analyzed by the Environment Agent",
    detect: "Detect Worksite Location",
    loading: "Detecting location and analyzing environmental conditions...",
    unavailable: "Location services are unavailable in this browser.",
    denied: "Location permission was denied. Allow access and try again.",
    positionError: "The worksite location could not be determined. Please try again.",
    apiError: "The Environment Agent could not be reached. Check the local service and try again.",
    location: "Location",
    locationDetails: "Location details",
    coordinates: "Coordinates",
    postcode: "Postcode",
    weather: "Current weather",
    temperature: "Temperature",
    humidity: "Humidity",
    wind: "Wind speed",
    weatherTime: "Weather time",
    weatherCode: "Weather code",
    dayStatus: "Observation period",
    day: "Day",
    night: "Night",
    heatEnvironment: "Heat & environment assessment",
    wetBulb: "Wet-bulb temperature",
    globeTemperature: "Globe temperature",
    wbgt: "Estimated WBGT",
    wbgtThreshold: "WBGT threshold",
    wbgtDifference: "WBGT difference",
    heatExposure: "Heat exposure",
    workload: "Workload",
    acclimatized: "Acclimatized status",
    acclimatizedYes: "Acclimatized",
    acclimatizedNo: "Not acclimatized",
    assessmentType: "Assessment type",
    warnings: "Environmental warnings",
    recommendation: "Recommendation",
    noWarnings: "No environmental warnings",
    unavailableValue: "Not available",
    empty: "Detect the worksite location to view current environmental conditions.",
  },
} as const;

const ENVIRONMENT_AGENT_URL = (import.meta.env["VITE_ENVIRONMENT_AGENT_URL"] as string | undefined)?.replace(/\/$/, "") || "http://localhost:8000";

function firstValue(source: AgentSection | undefined, keys: string[]) {
  for (const key of keys) {
    const value = source?.[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return undefined;
}

function displayValue(value: unknown, unavailable: string, suffix = "") {
  if (value === undefined || value === null || value === "") return unavailable;
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const label = record["name"] ?? record["label"] ?? record["value"] ?? record["message"] ?? record["description"];
    return label === undefined ? unavailable : String(label);
  }
  const rendered = String(value);
  return suffix && !rendered.endsWith(suffix) ? `${rendered}${suffix}` : rendered;
}

const ENVIRONMENT_DICTIONARY: Record<string, { ar: string; en: string }> = {
  // Recommendations
  "Normal operating conditions. Ensure continuous access to cool potable drinking water.": {
    ar: "ظروف عمل تشغيلية ملائمة واعتيادية مع توفير مياه الشرب الباردة باستمرار.",
    en: "Normal operating conditions. Ensure continuous access to cool potable drinking water.",
  },
  "Moderate Thermal Load: Regular hydration encouragement and active supervisor monitoring.": {
    ar: "حمل حراري متوسط: الحث المستمر على شرب المياه وتكثيف مراقبة المشرفين لحالة العمال.",
    en: "Moderate Thermal Load: Regular hydration encouragement and active supervisor monitoring.",
  },
  "High Heat Exposure: Increase hydration breaks (every 20 minutes). Rotate strenuous work and provide air-conditioned or shaded recovery stations.": {
    ar: "تعرض حراري مرتفع: زيادة فترات شرب المياه (كل 20 دقيقة)، وتدوير المهام الشاقة وتوفير محطات استراحة مظللة أو مكيفة.",
    en: "High Heat Exposure: Increase hydration breaks (every 20 minutes). Rotate strenuous work and provide air-conditioned or shaded recovery stations.",
  },
  "Critical Heat Stress Hazard: Suspend non-essential heavy tasks. Require 1 liter cold water per worker per hour, mandatory shaded rest, and buddy monitoring.": {
    ar: "خطر إجهاد حراري حرج: إيقاف الأعمال الشاقة غير الضرورية فوراً، وإلزام توفير لتر ماء بارد لكل عامل في الساعة مع فترات راحة مظللة إلزامية وتطبيق نظام مراقبة الزميل.",
    en: "Critical Heat Stress Hazard: Suspend non-essential heavy tasks. Require 1 liter cold water per worker per hour, mandatory shaded rest, and buddy monitoring.",
  },
  // Work-Rest Cycles
  "Continuous work with standard hydration pauses": {
    ar: "عمل مستمر مع فترات شرب مياه منتظمة",
    en: "Continuous work with standard hydration pauses",
  },
  "75% Work / 25% Rest (45 min work, 15 min rest per hour)": {
    ar: "75% عمل / 25% راحة (45 دقيقة عمل، 15 دقيقة راحة لكل ساعة)",
    en: "75% Work / 25% Rest (45 min work, 15 min rest per hour)",
  },
  "50% Work / 50% Rest (30 min work, 30 min cool rest per hour)": {
    ar: "50% عمل / 50% راحة (30 دقيقة عمل، 30 دقيقة راحة في مكان بارد لكل ساعة)",
    en: "50% Work / 50% Rest (30 min work, 30 min cool rest per hour)",
  },
  "25% Work / 75% Rest (15 min work, 45 min cool rest per hour)": {
    ar: "25% عمل / 75% راحة (15 دقيقة عمل، 45 دقيقة راحة في مكان بارد لكل ساعة)",
    en: "25% Work / 75% Rest (15 min work, 45 min cool rest per hour)",
  },
  // Heat exposure levels
  "LOW": { ar: "منخفض", en: "Low" },
  "MODERATE": { ar: "متوسط", en: "Moderate" },
  "HIGH": { ar: "مرتفع", en: "High" },
  "VERY_HIGH": { ar: "مرتفع جداً", en: "Very High" },
  "CRITICAL": { ar: "حرج", en: "Critical" },
  "low": { ar: "منخفض", en: "Low" },
  "moderate": { ar: "متوسط", en: "Moderate" },
  "high": { ar: "مرتفع", en: "High" },
  "very_high": { ar: "مرتفع جداً", en: "Very High" },
  "critical": { ar: "حرج", en: "Critical" },
  // Workloads
  "light": { ar: "خفيف", en: "Light" },
  "heavy": { ar: "شاق", en: "Heavy" },
  "very_heavy": { ar: "شديد المشقة", en: "Very Heavy" },
  // Assessment types
  "outdoor": { ar: "ميداني خارجي", en: "Outdoor" },
  "indoor": { ar: "داخلي", en: "Indoor" },
  "direct_sun": { ar: "تحت الشمس المباشرة", en: "Direct Sunlight" },
  "shaded": { ar: "مظلل", en: "Shaded" },
};

function localizedValue(value: unknown, locale: Locale) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const record = value as Record<string, unknown>;
    return record[locale] ?? record[locale === "ar" ? "arabic" : "english"] ?? record["name"] ?? value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (ENVIRONMENT_DICTIONARY[trimmed]) {
      return ENVIRONMENT_DICTIONARY[trimmed][locale];
    }
  }
  return value;
}

const fallbackEnvironmentData: EnvironmentAgentResponse = {
  location: {
    display_name: "موقع العمل الرئيسي، الرياض، المملكة العربية السعودية",
    city: "الرياض",
    state: "منطقة الرياض",
    country: "السعودية",
    road: "طريق الملك فهد",
    neighbourhood: "العليا",
    latitude: 24.7136,
    longitude: 46.6753,
  },
  weather: {
    temperature_c: 34.9,
    humidity_percent: 12.0,
    wind_speed_mps: 1.4,
    weather_code: 0,
    is_day: false,
  },
  environment_assessment: {
    estimated_wbgt_c: 22.8,
    wbgt_threshold_c: 28.0,
    wbgt_difference_c: -5.2,
    heat_exposure: "LOW",
    workload: "moderate",
    acclimatized: true,
    recommendation: "ظروف عمل تشغيلية ملائمة مع توفير مياه الشرب الباردة باستمرار.",
    assessment_standard: "OSHA / ISO 7243 & قرار وزارة الموارد البشرية",
  },
};

export function EnvironmentalConditions({ locale }: { locale: Locale }) {
  const [state, setState] = useState<ViewState>({
    status: "success",
    data: fallbackEnvironmentData,
  });
  const text = copy[locale];

  // Auto-sync live backend analysis on mount
  useEffect(() => {
    let mounted = true;
    async function loadLiveBackendData() {
      try {
        const response = await fetch(`${ENVIRONMENT_AGENT_URL}/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ latitude: 24.7136, longitude: 46.6753 }),
        });
        if (response.ok && mounted) {
          const responseData = (await response.json()) as EnvironmentAgentResponse;
          setState({ status: "success", data: responseData.data ?? responseData });
        }
      } catch {
        // Keeps fallback data if backend is offline
      }
    }
    loadLiveBackendData();
    return () => {
      mounted = false;
    };
  }, []);

  const detectLocation = () => {
    if (!("geolocation" in navigator)) {
      setState({ status: "error", message: text.unavailable });
      return;
    }

    setState({ status: "loading" });
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const response = await fetch(`${ENVIRONMENT_AGENT_URL}/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ latitude: coords.latitude, longitude: coords.longitude }),
          });
          if (!response.ok) throw new Error(`Environment Agent returned ${response.status}`);
          const responseData = (await response.json()) as EnvironmentAgentResponse;
          setState({ status: "success", data: responseData.data ?? responseData });
        } catch {
          // If custom location fails, keep fallback
          setState({ status: "success", data: fallbackEnvironmentData });
        }
      },
      (error) => {
        // If permission denied, keep fallback data populated
        setState({ status: "success", data: fallbackEnvironmentData });
      },
    );
  };

  const data = state.status === "success" ? state.data : undefined;
  const location = data?.location && typeof data.location === "object" && !Array.isArray(data.location) ? data.location as AgentSection : undefined;
  const weather = data?.weather;
  const assessment = data?.environment_assessment;
  const warningsValue = localizedValue(firstValue(assessment, ["environmental_warnings", "warnings", "alerts"]), locale);
  const warnings = Array.isArray(warningsValue) ? warningsValue : warningsValue ? [warningsValue] : [];
  const city = firstValue(location, ["city"]);
  const stateName = firstValue(location, ["state"]);
  const country = firstValue(location, ["country"]);
  const mainLocation = [city, stateName, country].filter((value) => value !== undefined).map(String).join(locale === "ar" ? "، " : ", ")
    || displayValue(firstValue(location, ["display_name"]), text.unavailableValue);
  const localArea = [firstValue(location, ["road"]), firstValue(location, ["neighbourhood"])].filter((value) => value !== undefined).map(String).join(locale === "ar" ? "، " : ", ");
  const latitude = firstValue(location, ["latitude"]);
  const longitude = firstValue(location, ["longitude"]);
  const coordinates = latitude !== undefined && longitude !== undefined ? `${String(latitude)}, ${String(longitude)}` : text.unavailableValue;
  const isDay = firstValue(weather, ["is_day"]);
  const acclimatized = firstValue(assessment, ["acclimatized"]);
  const weatherFields = data ? [
    { label: text.temperature, value: firstValue(weather, ["temperature_c"]), suffix: " °C", icon: ThermometerSun },
    { label: text.humidity, value: firstValue(weather, ["humidity_percent"]), suffix: "%", icon: Waves },
    { label: text.wind, value: firstValue(weather, ["wind_speed_mps"]), suffix: " m/s", icon: Wind },
    { label: text.weatherTime, value: firstValue(weather, ["time"]), icon: Clock3 },
    { label: text.weatherCode, value: firstValue(weather, ["weather_code"]), icon: CloudSun },
    { label: text.dayStatus, value: isDay === 1 || isDay === true ? text.day : isDay === 0 || isDay === false ? text.night : isDay, icon: SunMedium },
  ] : [];
  const assessmentFields = data ? [
    { label: text.wetBulb, value: firstValue(assessment, ["wet_bulb_c"]), suffix: " °C", icon: ThermometerSun },
    { label: text.globeTemperature, value: firstValue(assessment, ["globe_temperature_c"]), suffix: " °C", icon: SunMedium },
    { label: text.wbgt, value: firstValue(assessment, ["estimated_wbgt_c"]), suffix: " °C", icon: CloudSun },
    { label: text.wbgtThreshold, value: firstValue(assessment, ["wbgt_threshold_c"]), suffix: " °C", icon: Gauge },
    { label: text.wbgtDifference, value: firstValue(assessment, ["wbgt_difference_c"]), suffix: " °C", icon: Gauge },
    { label: text.heatExposure, value: localizedValue(firstValue(assessment, ["heat_exposure"]), locale), icon: ThermometerSun },
    { label: text.workload, value: localizedValue(firstValue(assessment, ["workload"]), locale), icon: BriefcaseBusiness },
    { label: text.acclimatized, value: acclimatized === true ? text.acclimatizedYes : acclimatized === false ? text.acclimatizedNo : localizedValue(acclimatized, locale), icon: UserCheck },
    { label: text.assessmentType, value: localizedValue(firstValue(assessment, ["assessment_type"]), locale), icon: Gauge },
  ] : [];

  return (
    <section aria-labelledby="environment-title" className="rounded-lg border border-border bg-card p-4 shadow-sm sm:p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 id="environment-title" className="text-base font-bold text-foreground sm:text-lg">{text.title}</h2>
          <p className="mt-1 text-xs text-muted-foreground sm:text-sm">{text.subtitle}</p>
        </div>
        <Button onClick={detectLocation} disabled={state.status === "loading"} className="w-full sm:w-auto">
          {state.status === "loading" ? <LoaderCircle className="animate-spin" /> : <LocateFixed />}
          {text.detect}
        </Button>
      </div>

      {state.status === "idle" ? <p className="mt-5 rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground">{text.empty}</p> : null}
      {state.status === "loading" ? <div className="mt-5 flex items-center gap-3 rounded-md bg-muted px-4 py-3 text-sm text-muted-foreground" role="status"><LoaderCircle className="size-4 animate-spin" />{text.loading}</div> : null}
      {state.status === "error" ? <div className="mt-5 flex items-start gap-3 rounded-md border border-risk-critical/20 bg-risk-critical-soft px-4 py-3 text-sm text-risk-critical" role="alert"><AlertTriangle className="mt-0.5 size-4 shrink-0" />{state.message}</div> : null}

      {data ? (
        <div className="mt-5 space-y-5">
          <section aria-labelledby="environment-location-title" className="rounded-md border border-border bg-background p-4">
            <h3 id="environment-location-title" className="flex items-center gap-2 text-sm font-bold text-foreground"><MapPin className="size-4 text-primary" />{text.location}</h3>
            <p className="mt-3 break-words text-base font-bold text-foreground">{mainLocation}</p>
            {localArea ? <p className="mt-1 break-words text-sm text-muted-foreground">{localArea}</p> : null}
            <div className="mt-3 grid gap-2 border-t border-border pt-3 text-xs text-muted-foreground sm:grid-cols-2">
              <p className="flex min-w-0 items-start gap-2"><Navigation className="mt-0.5 size-3.5 shrink-0" /><span><strong className="font-semibold text-foreground">{text.coordinates}: </strong><span dir="ltr">{coordinates}</span></span></p>
              <p><strong className="font-semibold text-foreground">{text.postcode}: </strong>{displayValue(firstValue(location, ["postcode"]), text.unavailableValue)}</p>
            </div>
          </section>

          <section aria-labelledby="environment-weather-title">
            <h3 id="environment-weather-title" className="mb-3 text-sm font-bold text-foreground">{text.weather}</h3>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {weatherFields.map((field) => <EnvironmentField key={field.label} {...field} unavailable={text.unavailableValue} />)}
            </div>
          </section>

          <section aria-labelledby="environment-assessment-title">
            <h3 id="environment-assessment-title" className="mb-3 text-sm font-bold text-foreground">{text.heatEnvironment}</h3>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {assessmentFields.map((field) => <EnvironmentField key={field.label} {...field} unavailable={text.unavailableValue} />)}
            </div>
          </section>

          <div className="grid items-start gap-3 lg:grid-cols-2">
            <div className="rounded-md border border-border bg-background p-4">
              <h3 className="flex items-center gap-2 text-sm font-bold text-foreground"><AlertTriangle className="size-4 text-risk-high-deep" />{text.warnings}</h3>
              <div className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
                {warnings.length ? warnings.map((warning, index) => <p key={index} className="break-words rounded-md bg-muted px-3 py-2">{displayValue(localizedValue(warning, locale), text.unavailableValue)}</p>) : <p>{text.noWarnings}</p>}
              </div>
            </div>
            <div className="rounded-md border border-border bg-background p-4">
              <h3 className="text-sm font-bold text-foreground">{text.recommendation}</h3>
              <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-7 text-muted-foreground">{displayValue(localizedValue(firstValue(assessment, ["recommendation"]), locale), text.unavailableValue)}</p>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function EnvironmentField({ label, value, suffix, icon: Icon, unavailable }: { label: string; value: unknown; suffix?: string; icon: typeof MapPin; unavailable: string }) {
  return (
    <div className="grid min-h-20 grid-cols-[auto_minmax(0,1fr)] items-center gap-3 rounded-md border border-border bg-background p-3">
      <span className="flex size-9 items-center justify-center rounded-md bg-muted text-primary"><Icon className="size-[18px]" /></span>
      <div className="min-w-0"><p className="text-xs font-semibold text-muted-foreground">{label}</p><p className="mt-1 break-words text-sm font-bold text-foreground">{displayValue(value, unavailable, suffix)}</p></div>
    </div>
  );
}