import type { Locale } from "@/lib/locale";

/** Bilingual text pair. Replace with i18n-backed values from the API later. */
export type Bilingual = { ar: string; en: string };

export type IncidentSeverity = "low" | "medium" | "high" | "critical";
export type IncidentStatus = "open" | "investigating" | "resolved";

/**
 * Shape of one historical incident record.
 * Structured to be replaced later by records produced by the YOLO
 * detection pipeline + AI agents (detection block mirrors the stream payload).
 */
export type IncidentRecord = {
  id: string;
  type: Bilingual;
  person: { name: Bilingual; employeeId: string; role: Bilingual; department: Bilingual };
  severity: IncidentSeverity;
  riskScore: number;
  riskAssessment: Bilingual;
  zone: string;
  cause: Bilingual;
  /** ISO date (YYYY-MM-DD) so date filtering stays simple. */
  date: string;
  time: string;
  handledBy: { name: Bilingual; role: Bilingual; responseNote: Bilingual };
  actionTaken: Bilingual;
  resolution: Bilingual;
  status: IncidentStatus;
  detection: { method: "YOLO"; className: Bilingual; confidence: number; camera: string; time: string };
  timeline: Array<{ time: string; label: Bilingual }>;
};

export const severityLabels: Record<IncidentSeverity, Bilingual> = {
  low: { ar: "منخفض", en: "Low" },
  medium: { ar: "متوسط", en: "Medium" },
  high: { ar: "عالٍ", en: "High" },
  critical: { ar: "حرج", en: "Critical" },
};

export const statusLabels: Record<IncidentStatus, Bilingual> = {
  open: { ar: "مفتوح", en: "Open" },
  investigating: { ar: "قيد التحقيق", en: "Under Investigation" },
  resolved: { ar: "تمت المعالجة", en: "Resolved" },
};

export const incidentSummary = [
  { value: "124", label: { ar: "إجمالي الحوادث", en: "Total Incidents" }, tone: "neutral" as const },
  { value: "8", label: { ar: "حوادث حرجة", en: "Critical Incidents" }, tone: "critical" as const },
  { value: "6", label: { ar: "حوادث قيد المعالجة", en: "Under Investigation" }, tone: "warning" as const },
  { value: "110", label: { ar: "تمت المعالجة", en: "Resolved" }, tone: "positive" as const },
];

const officers = {
  khaled: {
    name: { ar: "خالد العتيبي", en: "Khaled Al-Otaibi" },
    role: { ar: "مسؤول السلامة", en: "Safety Officer" },
    responseNote: { ar: "تم اتخاذ الإجراء بعد 3 دقائق من اكتشاف الحادث.", en: "Action taken 3 minutes after detection." },
  },
  noura: {
    name: { ar: "نورة الحربي", en: "Noura Al-Harbi" },
    role: { ar: "مشرفة السلامة", en: "Safety Supervisor" },
    responseNote: { ar: "تم اتخاذ الإجراء بعد 4 دقائق من اكتشاف الحادث.", en: "Action taken 4 minutes after detection." },
  },
  faisal: {
    name: { ar: "فيصل الدوسري", en: "Faisal Al-Dosari" },
    role: { ar: "منسق السلامة الميداني", en: "Field Safety Coordinator" },
    responseNote: { ar: "تم اتخاذ الإجراء بعد 6 دقائق من اكتشاف الحادث.", en: "Action taken 6 minutes after detection." },
  },
  sara: {
    name: { ar: "سارة القحطاني", en: "Sara Al-Qahtani" },
    role: { ar: "مسؤولة السلامة", en: "Safety Officer" },
    responseNote: { ar: "تم اتخاذ الإجراء بعد دقيقتين من اكتشاف الحادث.", en: "Action taken 2 minutes after detection." },
  },
};

const timeline = (start: string, alert: string, notify: string, action: string, resolved: string | null) => {
  const steps = [
    { time: start, label: { ar: "تم اكتشاف المخالفة", en: "Violation detected" } },
    { time: alert, label: { ar: "تم إنشاء التنبيه", en: "Alert generated" } },
    { time: notify, label: { ar: "تم إشعار مسؤول السلامة", en: "Safety officer notified" } },
    { time: action, label: { ar: "تم اتخاذ الإجراء", en: "Action taken" } },
  ];
  if (resolved) steps.push({ time: resolved, label: { ar: "تمت معالجة الحادث", en: "Incident resolved" } });
  return steps;
};

export const incidents: IncidentRecord[] = [
  {
    id: "INC-00124",
    type: { ar: "عدم ارتداء الخوذة", en: "No Helmet" },
    person: { name: { ar: "أحمد محمد", en: "Ahmed Mohammed" }, employeeId: "EMP-2417", role: { ar: "مشغل معدات", en: "Equipment Operator" }, department: { ar: "قسم العمليات", en: "Operations" } },
    severity: "critical",
    riskScore: 92,
    riskAssessment: { ar: "احتمال مرتفع لوقوع إصابة نتيجة عدم الالتزام بمعدات الوقاية الإلزامية.", en: "High likelihood of injury due to missing mandatory PPE." },
    zone: "Zone C",
    cause: { ar: "عدم الالتزام بمعدات الوقاية الشخصية أثناء العمل في منطقة تتطلب ارتداء الخوذة.", en: "Failure to comply with mandatory PPE requirements in a designated helmet-required area." },
    date: "2026-09-15",
    time: "14:32",
    handledBy: officers.khaled,
    actionTaken: { ar: "تم إيقاف العمل مؤقتًا، وتنبيه العامل، والتأكد من ارتداء الخوذة قبل استئناف العمل.", en: "Work paused, worker alerted, and helmet compliance confirmed before resuming." },
    resolution: { ar: "تم تصحيح المخالفة، وإعادة توعية العامل بمتطلبات معدات الوقاية، والتأكد من الالتزام قبل استئناف العمل.", en: "Violation corrected, worker re-briefed on PPE requirements, and compliance verified before work resumed." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "عدم ارتداء الخوذة", en: "No Helmet" }, confidence: 96, camera: "Camera 01", time: "14:32" },
    timeline: timeline("14:32", "14:32", "14:34", "14:35", "14:40"),
  },
  {
    id: "INC-00123",
    type: { ar: "عدم ارتداء سترة السلامة", en: "No Safety Vest" },
    person: { name: { ar: "سلطان الشمري", en: "Sultan Al-Shammari" }, employeeId: "EMP-1188", role: { ar: "فني صيانة", en: "Maintenance Technician" }, department: { ar: "قسم الصيانة", en: "Maintenance" } },
    severity: "high",
    riskScore: 74,
    riskAssessment: { ar: "احتمال متوسط إلى مرتفع للاصطدام بسبب انخفاض الظهور في ممرات المعدات.", en: "Moderate to high collision risk due to low visibility in equipment lanes." },
    zone: "Zone A",
    cause: { ar: "خلع سترة السلامة أثناء أعمال الصيانة في ممر متحرك.", en: "Safety vest removed during maintenance work in an active traffic lane." },
    date: "2026-09-15",
    time: "11:05",
    handledBy: officers.noura,
    actionTaken: { ar: "تم إشعار المشرف وتزويد العامل بسترة بديلة فورًا.", en: "Supervisor notified and a replacement vest issued immediately." },
    resolution: { ar: "تمت إعادة الالتزام بمعدات الظهور وتسجيل ملاحظة في سجل الفريق.", en: "Visibility PPE compliance restored and a note logged for the crew." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "عدم ارتداء سترة السلامة", en: "No Safety Vest" }, confidence: 91, camera: "Camera 03", time: "11:05" },
    timeline: timeline("11:05", "11:05", "11:07", "11:09", "11:18"),
  },
  {
    id: "INC-00122",
    type: { ar: "رصد دخان", en: "Smoke Detected" },
    person: { name: { ar: "غير محدد", en: "Unassigned" }, employeeId: "—", role: { ar: "لا يوجد موظف مرتبط", en: "No employee linked" }, department: { ar: "قسم العمليات", en: "Operations" } },
    severity: "critical",
    riskScore: 95,
    riskAssessment: { ar: "خطورة عالية جدًا لاحتمال نشوب حريق قرب مواد قابلة للاشتعال.", en: "Very high fire risk near flammable material storage." },
    zone: "Zone C",
    cause: { ar: "ارتفاع حرارة وحدة ضغط قديمة أدى إلى انبعاث دخان.", en: "Overheating of an aging compressor unit produced visible smoke." },
    date: "2026-09-14",
    time: "16:48",
    handledBy: officers.khaled,
    actionTaken: { ar: "تم إخلاء المنطقة وإيقاف الوحدة وفحصها من قبل فريق الصيانة.", en: "Area evacuated, unit shut down, and inspected by the maintenance team." },
    resolution: { ar: "قيد التحقيق لتحديد السبب الجذري وإعداد خطة استبدال الوحدة.", en: "Under investigation to confirm root cause and plan unit replacement." },
    status: "investigating",
    detection: { method: "YOLO", className: { ar: "دخان", en: "Smoke" }, confidence: 94, camera: "Camera 01", time: "16:48" },
    timeline: timeline("16:48", "16:48", "16:49", "16:52", null),
  },
  {
    id: "INC-00121",
    type: { ar: "دخول منطقة محظورة", en: "Restricted Area Entry" },
    person: { name: { ar: "ماجد العسيري", en: "Majed Al-Asiri" }, employeeId: "EMP-3042", role: { ar: "عامل نقل", en: "Logistics Worker" }, department: { ar: "قسم اللوجستيات", en: "Logistics" } },
    severity: "high",
    riskScore: 78,
    riskAssessment: { ar: "احتمال مرتفع للتعرض لمعدات رفع تعمل دون إشراف.", en: "High exposure risk to unsupervised lifting equipment." },
    zone: "Zone B",
    cause: { ar: "استخدام مسار مختصر عبر منطقة رفع محظورة.", en: "Shortcut taken through a restricted lifting area." },
    date: "2026-09-14",
    time: "09:21",
    handledBy: officers.faisal,
    actionTaken: { ar: "تم إخراج العامل من المنطقة وتوضيح المسار الآمن البديل.", en: "Worker escorted out and shown the approved safe route." },
    resolution: { ar: "تمت إعادة تحديد المسارات بعلامات أرضية جديدة.", en: "Walkways re-marked with new floor signage." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "دخول منطقة محظورة", en: "Restricted Zone Entry" }, confidence: 89, camera: "Camera 02", time: "09:21" },
    timeline: timeline("09:21", "09:21", "09:23", "09:27", "09:45"),
  },
  {
    id: "INC-00120",
    type: { ar: "سلوك غير آمن", en: "Unsafe Behavior" },
    person: { name: { ar: "عبدالله الزهراني", en: "Abdullah Al-Zahrani" }, employeeId: "EMP-2765", role: { ar: "مشغل رافعة", en: "Crane Operator" }, department: { ar: "قسم العمليات", en: "Operations" } },
    severity: "medium",
    riskScore: 56,
    riskAssessment: { ar: "خطورة متوسطة نتيجة تجاوز إجراءات التشغيل الآمن.", en: "Medium risk from bypassing safe operating procedure." },
    zone: "Zone D",
    cause: { ar: "تشغيل المعدة دون إكمال قائمة الفحص قبل البدء.", en: "Equipment operated without completing the pre-start checklist." },
    date: "2026-09-13",
    time: "13:14",
    handledBy: officers.sara,
    actionTaken: { ar: "تم إيقاف التشغيل حتى إكمال قائمة الفحص.", en: "Operation halted until the checklist was completed." },
    resolution: { ar: "تمت إعادة التدريب على إجراءات ما قبل التشغيل.", en: "Pre-start procedure retraining completed." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "سلوك غير آمن", en: "Unsafe Behavior" }, confidence: 84, camera: "Camera 04", time: "13:14" },
    timeline: timeline("13:14", "13:14", "13:16", "13:19", "13:40"),
  },
  {
    id: "INC-00119",
    type: { ar: "الاقتراب من منطقة خطرة", en: "Proximity to Hazard Zone" },
    person: { name: { ar: "ريم السبيعي", en: "Reem Al-Subaie" }, employeeId: "EMP-1902", role: { ar: "مفتشة جودة", en: "Quality Inspector" }, department: { ar: "قسم الجودة", en: "Quality" } },
    severity: "medium",
    riskScore: 51,
    riskAssessment: { ar: "خطورة متوسطة نتيجة الاقتراب من حد السلامة المحدد.", en: "Medium risk from crossing the defined safety boundary." },
    zone: "Zone E",
    cause: { ar: "الاقتراب من خط المعدات الساخنة أثناء أخذ القياسات.", en: "Approached the hot equipment line while taking measurements." },
    date: "2026-09-13",
    time: "10:02",
    handledBy: officers.noura,
    actionTaken: { ar: "تم تنبيه المفتشة وتحديد نقطة قياس آمنة.", en: "Inspector alerted and a safe measurement point assigned." },
    resolution: { ar: "تم تحديث تعليمات الفحص لتشمل مسافة أمان واضحة.", en: "Inspection instructions updated with a clear stand-off distance." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "اقتراب من منطقة خطرة", en: "Hazard Proximity" }, confidence: 87, camera: "Camera 05", time: "10:02" },
    timeline: timeline("10:02", "10:02", "10:05", "10:08", "10:25"),
  },
  {
    id: "INC-00118",
    type: { ar: "مخالفة معدات الوقاية الشخصية", en: "PPE Violation" },
    person: { name: { ar: "يوسف الغامدي", en: "Yousef Al-Ghamdi" }, employeeId: "EMP-2210", role: { ar: "لحام", en: "Welder" }, department: { ar: "قسم التصنيع", en: "Fabrication" } },
    severity: "critical",
    riskScore: 90,
    riskAssessment: { ar: "احتمال مرتفع لإصابة العين نتيجة العمل دون واقي الوجه.", en: "High likelihood of eye injury from welding without a face shield." },
    zone: "Zone A",
    cause: { ar: "بدء أعمال اللحام دون واقي الوجه المخصص.", en: "Welding started without the required face shield." },
    date: "2026-09-12",
    time: "15:57",
    handledBy: officers.khaled,
    actionTaken: { ar: "تم إيقاف اللحام فورًا وتوفير واقي الوجه.", en: "Welding stopped immediately and a face shield provided." },
    resolution: { ar: "تم توثيق المخالفة وإصدار تنبيه رسمي للفريق.", en: "Violation documented and a formal team notice issued." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "غياب واقي الوجه", en: "Missing Face Shield" }, confidence: 93, camera: "Camera 03", time: "15:57" },
    timeline: timeline("15:57", "15:57", "15:58", "16:00", "16:15"),
  },
  {
    id: "INC-00117",
    type: { ar: "عدم ارتداء الخوذة", en: "No Helmet" },
    person: { name: { ar: "بندر المطيري", en: "Bandar Al-Mutairi" }, employeeId: "EMP-3311", role: { ar: "عامل بناء", en: "Construction Worker" }, department: { ar: "قسم المشاريع", en: "Projects" } },
    severity: "high",
    riskScore: 71,
    riskAssessment: { ar: "احتمال مرتفع لإصابة الرأس أسفل أعمال الرفع.", en: "High head-injury risk while working below lifting operations." },
    zone: "Zone B",
    cause: { ar: "خلع الخوذة بسبب الحرارة دون طلب بديل مناسب.", en: "Helmet removed due to heat without requesting an alternative." },
    date: "2026-09-11",
    time: "12:41",
    handledBy: officers.faisal,
    actionTaken: { ar: "تم إيقاف العمل وتوفير خوذة بتهوية أفضل.", en: "Work paused and a better-ventilated helmet provided." },
    resolution: { ar: "تمت إضافة فترات راحة للتبريد إلى خطة العمل.", en: "Cool-down breaks added to the work plan." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "عدم ارتداء الخوذة", en: "No Helmet" }, confidence: 95, camera: "Camera 02", time: "12:41" },
    timeline: timeline("12:41", "12:41", "12:43", "12:46", "13:05"),
  },
  {
    id: "INC-00116",
    type: { ar: "دخول منطقة محظورة", en: "Restricted Area Entry" },
    person: { name: { ar: "طلال الحميدي", en: "Talal Al-Humaidi" }, employeeId: "EMP-1450", role: { ar: "زائر مرافق", en: "Escorted Visitor" }, department: { ar: "قسم الزوار", en: "Visitors" } },
    severity: "medium",
    riskScore: 48,
    riskAssessment: { ar: "خطورة متوسطة نتيجة تجاوز حدود الجولة المصرح بها.", en: "Medium risk from stepping outside the authorized tour path." },
    zone: "Zone D",
    cause: { ar: "الانفصال عن المرافق أثناء جولة تعريفية.", en: "Separated from the escort during a site tour." },
    date: "2026-09-10",
    time: "10:36",
    handledBy: officers.sara,
    actionTaken: { ar: "تمت إعادة الزائر إلى مسار الجولة مباشرة.", en: "Visitor returned to the approved tour route." },
    resolution: { ar: "تم تحديث بروتوكول مرافقة الزوار.", en: "Visitor escort protocol updated." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "دخول منطقة محظورة", en: "Restricted Zone Entry" }, confidence: 86, camera: "Camera 04", time: "10:36" },
    timeline: timeline("10:36", "10:36", "10:38", "10:40", "10:52"),
  },
  {
    id: "INC-00115",
    type: { ar: "سلوك غير آمن", en: "Unsafe Behavior" },
    person: { name: { ar: "مشعل البقمي", en: "Mishal Al-Baqami" }, employeeId: "EMP-2088", role: { ar: "مشغل رافعة شوكية", en: "Forklift Operator" }, department: { ar: "قسم المستودعات", en: "Warehouse" } },
    severity: "high",
    riskScore: 76,
    riskAssessment: { ar: "احتمال مرتفع للتصادم نتيجة السرعة الزائدة داخل الممرات.", en: "High collision risk from excessive speed inside aisles." },
    zone: "Zone E",
    cause: { ar: "تجاوز السرعة المحددة داخل ممر المستودع.", en: "Exceeded the posted aisle speed limit." },
    date: "2026-09-09",
    time: "08:52",
    handledBy: officers.noura,
    actionTaken: { ar: "تم إيقاف الرافعة ومراجعة قواعد السرعة مع المشغل.", en: "Forklift stopped and speed rules reviewed with the operator." },
    resolution: { ar: "قيد التحقيق لمراجعة سجل بيانات الرافعة.", en: "Under investigation pending forklift telemetry review." },
    status: "investigating",
    detection: { method: "YOLO", className: { ar: "سرعة غير آمنة", en: "Unsafe Speed" }, confidence: 82, camera: "Camera 05", time: "08:52" },
    timeline: timeline("08:52", "08:52", "08:55", "08:58", null),
  },
  {
    id: "INC-00114",
    type: { ar: "عدم ارتداء سترة السلامة", en: "No Safety Vest" },
    person: { name: { ar: "هاني العمري", en: "Hani Al-Omari" }, employeeId: "EMP-2903", role: { ar: "مساعد ميداني", en: "Field Assistant" }, department: { ar: "قسم العمليات", en: "Operations" } },
    severity: "low",
    riskScore: 28,
    riskAssessment: { ar: "خطورة منخفضة لوجود العامل في منطقة قليلة الحركة.", en: "Low risk as the worker stood in a low-traffic area." },
    zone: "Zone A",
    cause: { ar: "تأخر استلام السترة من مخزن المعدات.", en: "Delay in collecting a vest from the equipment store." },
    date: "2026-09-08",
    time: "17:20",
    handledBy: officers.sara,
    actionTaken: { ar: "تم تسليم السترة والتحقق من الالتزام.", en: "Vest issued and compliance verified." },
    resolution: { ar: "تم تعديل توقيت توزيع معدات الوقاية في بداية الوردية.", en: "PPE distribution moved to the start of the shift." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "عدم ارتداء سترة السلامة", en: "No Safety Vest" }, confidence: 88, camera: "Camera 03", time: "17:20" },
    timeline: timeline("17:20", "17:20", "17:22", "17:24", "17:35"),
  },
  {
    id: "INC-00113",
    type: { ar: "رصد دخان", en: "Smoke Detected" },
    person: { name: { ar: "غير محدد", en: "Unassigned" }, employeeId: "—", role: { ar: "لا يوجد موظف مرتبط", en: "No employee linked" }, department: { ar: "قسم الصيانة", en: "Maintenance" } },
    severity: "high",
    riskScore: 68,
    riskAssessment: { ar: "خطورة مرتفعة بسبب دخان محدود قرب لوحة كهربائية.", en: "Elevated risk from localized smoke near an electrical panel." },
    zone: "Zone B",
    cause: { ar: "تراكم غبار داخل لوحة توزيع كهربائية.", en: "Dust accumulation inside an electrical distribution panel." },
    date: "2026-09-07",
    time: "19:11",
    handledBy: officers.khaled,
    actionTaken: { ar: "تم عزل اللوحة وتنظيفها من قبل الفريق الكهربائي.", en: "Panel isolated and cleaned by the electrical team." },
    resolution: { ar: "مفتوح بانتظار جدولة صيانة دورية للوحات.", en: "Open pending a scheduled preventive panel maintenance plan." },
    status: "open",
    detection: { method: "YOLO", className: { ar: "دخان", en: "Smoke" }, confidence: 90, camera: "Camera 02", time: "19:11" },
    timeline: timeline("19:11", "19:11", "19:13", "19:18", null),
  },
  {
    id: "INC-00112",
    type: { ar: "الاقتراب من منطقة خطرة", en: "Proximity to Hazard Zone" },
    person: { name: { ar: "فهد الرشيد", en: "Fahad Al-Rashid" }, employeeId: "EMP-1677", role: { ar: "فني كهرباء", en: "Electrical Technician" }, department: { ar: "قسم الصيانة", en: "Maintenance" } },
    severity: "low",
    riskScore: 32,
    riskAssessment: { ar: "خطورة منخفضة مع وجود إشراف مباشر أثناء العمل.", en: "Low risk with direct supervision present during the task." },
    zone: "Zone C",
    cause: { ar: "الوقوف قرب حد المنطقة الخطرة أثناء نقل الأدوات.", en: "Stood near the hazard boundary while moving tools." },
    date: "2026-09-06",
    time: "14:05",
    handledBy: officers.faisal,
    actionTaken: { ar: "تم تنبيه الفني وتحديد نقطة تجميع أدوات آمنة.", en: "Technician alerted and a safe tool staging point assigned." },
    resolution: { ar: "تم إضافة علامة أرضية لحد المنطقة الخطرة.", en: "Floor marking added at the hazard boundary." },
    status: "resolved",
    detection: { method: "YOLO", className: { ar: "اقتراب من منطقة خطرة", en: "Hazard Proximity" }, confidence: 85, camera: "Camera 01", time: "14:05" },
    timeline: timeline("14:05", "14:05", "14:07", "14:10", "14:22"),
  },
];

export const incidentZones = Array.from(new Set(incidents.map((incident) => incident.zone))).sort();

const arabicMonths = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
const englishMonths = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** Formats an ISO date without Intl so SSR and the browser always agree. */
export function formatIncidentDate(iso: string, locale: Locale) {
  const [year, month, day] = iso.split("-");
  const monthName = (locale === "ar" ? arabicMonths : englishMonths)[Number(month) - 1] ?? month;
  return locale === "ar" ? `${Number(day)} ${monthName} ${year}` : `${Number(day)} ${monthName} ${year}`;
}
