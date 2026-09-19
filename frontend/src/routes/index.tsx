import { useCallback } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  Activity,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Bot,
  Brain,
  Camera,
  CloudSun,
  Eye,
  Gauge,
  LineChart,
  MessageSquare,
  ScanEye,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";

import heroFactory from "@/assets/diraya-hero-factory.jpg";
import { DirayaMark } from "@/components/diraya-brand";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Button } from "@/components/ui/button";
import { isArabic, localeSearch, type Locale } from "@/lib/locale";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  validateSearch: localeSearch,
  head: () => ({
    meta: [
      { title: "دِراية | DIRAYA — نكتشف الخطر، ونمنع الحادث" },
      {
        name: "description",
        content:
          "منصة ذكية للسلامة المهنية تستخدم الذكاء الاصطناعي لرصد المخاطر وتحليلها والتنبؤ بها قبل أن تتحول إلى حوادث.",
      },
      { property: "og:title", content: "دِراية | DIRAYA — نكتشف الخطر، ونمنع الحادث" },
      {
        property: "og:description",
        content: "رصد لحظي، تحليل للأنماط، وتنبؤ بالمخاطر لدعم فرق السلامة بقرارات مبنية على البيانات.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LandingPage,
});

const copy = {
  ar: {
    nav: { vision: "رؤيتنا", goals: "الأهداف", how: "كيف تعمل", login: "تسجيل الدخول" },
    hero: {
      headline: "دِراية بالخطر، حماية لهم",
      body: "الأرواح ليست أرقامًا، وخلف كل عامل عائلة تنتظر عودته. بالدِراية، نفهم المخاطر ونستبقها، لنساهم في بيئة عمل أكثر أمانًا يعود منها الجميع سالمين",
      primary: "احمِ فريقك الآن",
      secondary: "اكتشف دِراية",
      flow: ["رصد", "فهم وتحليل", "تنبؤ", "وقاية"],
    },
    what: {
      title: "ما هي دِراية؟",
      body: "دِراية نظام ذكي للسلامة الصناعية يفهم ما يحدث في بيئة العمل ويربط سياق المهمة بمتطلبات السلامة للتحقق من الالتزام ورصد المخاطر لحظيًا، كما يحلل البيانات والأنماط للتنبؤ بمستويات الخطر ودعم الوقاية من الحوادث.",
      cards: [
        { title: "رصد", body: "اكتشاف المخاطر ومخالفات السلامة لحظيًا في بيئة العمل." },
        { title: "فهم وتحليل", body: "فهم سياق العمل، وتحليل الأنماط لتحديد المناطق والأوقات الأكثر خطورة." },
        { title: "تنبؤ", body: "التنبؤ بالمخاطر المحتملة لمساعدة فرق السلامة على التدخل مبكرًا." },
      ],
    },
    vision: {
      title: "رؤيتنا",
      statement: "من التعامل مع الحوادث بعد وقوعها، إلى الوقاية منها قبل حدوثها.",
      body: "تهدف دِراية إلى اكتشاف مؤشرات الخطر مبكرًا، وفهمها وتحليلها، للمساعدة على اتخاذ إجراءات وقائية قبل وقوع الحوادث.",
      reactiveLabel: "بدون دِراية",
      reactive: ["حادث", "تحقيق", "إجراء"],
      dirayaLabel: "دِراية",
      diraya: ["رصد", "فهم وتحليل", "تنبؤ", "وقاية"],
    },
    goals: {
      title: "أهدافنا",
      items: [
        "اكتشاف المخاطر مبكرًا",
        "تسريع الاستجابة للمخاطر",
        "التنبؤ بالمناطق والأوقات عالية الخطورة",
        "دعم مسؤولي السلامة بقرارات مبنية على البيانات",
      ],
    },
    how: {
      title: "كيف تعمل دِراية؟",
      subtitle: "عدة وكلاء ذكيين يعملون معًا لتحويل البيانات إلى قرارات.",
      
      source: "الكاميرا",
      decision: "قرار السلامة",
      agents: [
        {
          name: "وكيل الرؤية والسياق",
          en: "VISION & CONTEXT AGENT",
          role: "يرصد ما يحدث في بيئة العمل ويفهم سياق المهمة لتكوين صورة متكاملة عن حالة السلامة.",
          tags: ["نقص معدات الوقاية", "كشف السقوط", "سلوك غير آمن", "دخول منطقة محظورة"],
        },
        {
          name: "وكيل البيئة",
          en: "ENVIRONMENT AGENT",
          role: "يقرأ الظروف البيئية مثل درجة الحرارة والرطوبة والطقس لتحديد الظروف التي قد تزيد من مستوى الخطر.",
          tags: ["درجة الحرارة", "الرطوبة", "خطر الإجهاد الحراري", "الظروف البيئية"],
        },
        {
          name: "وكيل الامتثال",
          en: "COMPLIANCE AGENT",
          role: "يتحقق من متطلبات السلامة وفقًا لسياق العمل، ويحدد المخالفات ويقيّم مستوى الخطر والاستجابة المناسبة.",
          tags: ["متطلبات السلامة", "المخالفات", "تقييم الخطر", "الاستجابة"],
        },
        {
          name: "وكيل التنبؤ",
          en: "PREDICTION AGENT",
          role: "يحلل الأنماط التاريخية للتنبؤ بالمناطق والأوقات والمخاطر التي قد تحتاج إلى تدخل.",
          tags: ["أنماط تاريخية", "مناطق متوقعة", "أوقات حرجة"],
        },
        {
          name: "المساعد الذكي",
          en: "DIRAYA AI ASSISTANT",
          role: "يحوّل نتائج الوكلاء والبيانات إلى إجابات وتوصيات مفهومة لمسؤولي السلامة.",
          tags: ["إجابات مباشرة", "توصيات عملية"],
        },
      ],
      exampleLabel: "مثال توضيحي — ليست بيانات حقيقية",
      question: "وش أكثر منطقة تحتاج تدخل اليوم؟",
      answer: "المنطقة C تظهر أعلى مستوى خطر حاليًا بناءً على التنبيهات والأنماط المسجلة.",
    },
    cta: { title: "جاهز لتجربة دِراية؟", body: "لأن الوقاية تبدأ بدِراية.", action: "تسجيل الدخول" },
    footerNote: "نظام ذكي للسلامة الصناعية",
  },
  en: {
    nav: { vision: "Vision", goals: "Goals", how: "How It Works", login: "Login" },
    hero: {
      headline: "Aware of the Risk. Protecting Them.",
      body: "Lives are not numbers, and behind every worker is a family waiting for their return. With DIRAYA, we understand risks and act ahead of them, contributing to a safer workplace where everyone returns home unharmed.",
      primary: "Get Started",
      secondary: "Explore DIRAYA",
      flow: ["Detection", "Understanding & Analysis", "Prediction", "Prevention"],
    },
    what: {
      title: "What is DIRAYA?",
      body: "DIRAYA is a smart industrial safety system that understands what happens in the work environment, links task context to safety requirements to verify compliance and detect risks in real time, and analyzes data and patterns to predict risk levels and support incident prevention.",
      cards: [
        { title: "Detection", body: "Detecting hazards and safety violations in real time in the work environment." },
        { title: "Understanding & Analysis", body: "Understand work context and analyze patterns to identify the riskiest areas and times." },
        { title: "Prediction", body: "Predict emerging risks so safety teams can intervene early." },
      ],
    },
    vision: {
      title: "Our Vision",
      statement: "From reacting to incidents after they occur, to preventing them before they happen.",
      body: "DIRAYA aims to detect early warning signs, understand and analyze them, helping take preventive actions before incidents occur.",
      reactiveLabel: "Reactive safety",
      reactive: ["Incident", "Investigation", "Action"],
      dirayaLabel: "DIRAYA",
      diraya: ["Detection", "Understanding & Analysis", "Prediction", "Prevention"],
    },
    goals: {
      title: "Our Goals",
      items: [
        "Detect hazards early",
        "Accelerate response to risks",
        "Predict high-risk areas and periods",
        "Support safety teams with data-driven decisions",
      ],
    },
    how: {
      title: "How does DIRAYA work?",
      subtitle: "Multiple AI agents work together to turn safety data into actionable decisions.",
      
      source: "Camera",
      decision: "Safety Decision",
      agents: [
        {
          name: "Vision & Context Agent",
          en: "VISION & CONTEXT AGENT",
          role: "Monitors what happens in the work environment and understands task context to form a complete picture of the safety status.",
          tags: ["Missing PPE", "Fall detection", "Unsafe behavior", "Restricted area entry"],
        },
        {
          name: "Environment Agent",
          en: "ENVIRONMENT AGENT",
          role: "Reads environmental conditions such as temperature, humidity, and weather that can raise risk levels.",
          tags: ["Temperature", "Humidity", "Heat risk", "Environmental conditions"],
        },
        {
          name: "Compliance Agent",
          en: "COMPLIANCE AGENT",
          role: "Verifies safety requirements according to work context, identifies violations, and assesses the risk level and appropriate response.",
          tags: ["Safety requirements", "Violations", "Risk assessment", "Response"],
        },
        {
          name: "Prediction Agent",
          en: "PREDICTION AGENT",
          role: "Analyzes historical patterns to predict areas, periods, and risks that may need intervention.",
          tags: ["Historical patterns", "Predicted areas", "Critical periods"],
        },
        {
          name: "DIRAYA AI Assistant",
          en: "DIRAYA AI ASSISTANT",
          role: "Turns agent outputs and safety data into clear answers and recommendations for safety officers.",
          tags: ["Direct answers", "Practical recommendations"],
        },
      ],
      exampleLabel: "Illustrative example — not real live data",
      question: "Which area needs intervention most today?",
      answer: "Zone C currently shows the highest risk level based on recorded alerts and patterns.",
    },
    cta: { title: "Ready to experience DIRAYA?", body: "Because prevention starts with DIRAYA.", action: "Login" },
    footerNote: "Smart system for industrial safety",
  },
} as const;

const agentIcons = [ScanEye, CloudSun, Gauge, TrendingUp, Bot];
const whatIcons = [Eye, BarChart3, LineChart];
const goalIcons = [ShieldCheck, Activity, Target, Users];

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function LandingPage() {
  const { lang } = Route.useSearch();
  const navigate = useNavigate();
  const arabic = isArabic(lang);
  const t = copy[lang];
  const Arrow = arabic ? ArrowLeft : ArrowRight;

  const changeLanguage = useCallback(
    (next: Locale) => {
      navigate({ to: "/", search: { lang: next }, replace: true });
    },
    [navigate],
  );

  const goLogin = useCallback(() => {
    navigate({ to: "/login", search: { lang } });
  }, [navigate, lang]);

  const heading = "font-bold font-tajawal";

  return (
    <main
      dir={arabic ? "rtl" : "ltr"}
      lang={lang}
      className="min-h-screen scroll-smooth bg-background font-tajawal text-foreground"
    >
      <header className="sticky top-0 z-50 border-b border-border/70 bg-background/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 w-full max-w-[1280px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-10">
          <div className="flex items-center gap-2.5 text-navy">
            <DirayaMark variant="navy" className="size-11" />
            <span className={cn("font-display text-xl font-bold", arabic && "font-tajawal")}>{arabic ? "دِراية" : "DIRAYA"}</span>
          </div>
          <nav className="hidden items-center gap-1 md:flex">
            {[
              { label: t.nav.vision, id: "vision" },
              { label: t.nav.goals, id: "goals" },
              { label: t.nav.how, id: "how-it-works" },
            ].map((item) => (
              <Button
                key={item.id}
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => scrollToSection(item.id)}
                className="text-sm font-semibold text-muted-foreground hover:text-foreground"
              >
                {item.label}
              </Button>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <LanguageSwitcher locale={lang} onChange={changeLanguage} />
            <Button
              type="button"
              onClick={goLogin}
              className="h-10 rounded-md bg-navy px-4 text-sm font-bold text-navy-foreground hover:bg-navy-deep"
            >
              {t.nav.login}
            </Button>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="relative overflow-hidden bg-navy-deep text-navy-foreground">
        {/* Blended workplace background (mirrored so the dark side sits behind the text in RTL) */}
        <img
          src={heroFactory}
          alt=""
          aria-hidden="true"
          width={1920}
          height={1088}
          fetchPriority="high"
          style={arabic ? { transform: "scaleX(-1)" } : undefined}
          className="pointer-events-none absolute inset-0 size-full object-cover opacity-70"
        />
        <div className="pointer-events-none absolute inset-0 bg-navy-deep/25" />
        <div
          style={arabic ? { transform: "scaleX(-1)" } : undefined}
          className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,color-mix(in_oklch,var(--navy-deep)_90%,transparent),color-mix(in_oklch,var(--navy-deep)_35%,transparent)_55%,color-mix(in_oklch,var(--navy-deep)_65%,transparent))]"
        />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_75%_25%,color-mix(in_oklch,var(--safety)_22%,transparent),transparent_58%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,transparent,color-mix(in_oklch,var(--navy-deep)_85%,transparent))]" />
        <div className="relative mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-[1280px] flex-col justify-center gap-10 px-4 py-16 sm:px-6 lg:gap-12 lg:px-10 lg:py-20">
          <div className="animate-fade-up">
            <div className="inline-flex items-center gap-2 rounded-md border border-positive/30 bg-positive/10 px-3 py-1.5 text-xs font-semibold text-positive-soft">
              <Sparkles className="size-3.5" />
              {arabic ? "نظام ذكي للسلامة الصناعية" : "Smart system for industrial safety"}
            </div>
            <div className="mt-6 flex items-center gap-4">
              <DirayaMark variant="white" className="size-12" />
              <p className={cn(heading, "text-2xl")}>{arabic ? "دِراية | DIRAYA" : "DIRAYA | دِراية"}</p>
            </div>
            <h1 className={cn(heading, "mt-6 text-4xl leading-tight sm:text-6xl")}>{t.hero.headline}</h1>
            <p className="mt-5 max-w-xl text-base leading-8 text-navy-foreground/75 sm:text-lg">{t.hero.body}</p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Button
                size="lg"
                onClick={goLogin}
                className="h-12 min-w-44 rounded-md bg-safety px-7 text-base font-bold text-navy-deep hover:bg-safety/90 gap-2 shadow-lg shadow-safety/20"
              >
                {t.hero.primary}
                <Arrow className="size-4" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => scrollToSection("what-is-diraya")}
                className="h-12 min-w-36 rounded-md border-navy-foreground/20 bg-transparent px-5 text-base font-semibold text-navy-foreground/80 hover:bg-navy-foreground/10 hover:text-navy-foreground"
              >
                {t.hero.secondary}
                <ArrowDown className="size-4" />
              </Button>
            </div>
          </div>

          {/* Floating glass dock: Detect -> Understand -> Predict -> Prevent */}
          <div className="animate-fade-in mx-auto mb-8 w-full max-w-[700px]">
            <div className="grid grid-cols-2 items-center justify-center gap-x-1 gap-y-1 rounded-full border border-navy-foreground/10 bg-navy-deep/70 px-3 py-2.5 shadow-[0_24px_60px_-24px_color-mix(in_oklch,var(--navy-deep)_95%,transparent)] backdrop-blur-md sm:flex sm:flex-wrap sm:px-4">
              {[Camera, Brain, Gauge, ShieldCheck].map((Icon, index) => (
                <div key={index} className="contents">
                  <div className="flex items-center justify-center gap-2.5 justify-self-center rounded-full px-2.5 py-1.5 transition-colors hover:bg-navy-foreground/5">
                    <span
                      className={cn(
                        "flex size-9 shrink-0 items-center justify-center rounded-full bg-safety/15 text-safety ring-1 ring-inset ring-safety/30 shadow-[0_0_18px_-2px_color-mix(in_oklch,var(--safety)_65%,transparent)]",
                        index === 3 &&
                          "bg-positive/15 text-positive ring-positive/30 shadow-[0_0_18px_-2px_color-mix(in_oklch,var(--positive)_65%,transparent)]",
                      )}
                    >
                      <Icon className="size-4.5" />
                    </span>
                    <p className="text-[13px] font-bold leading-5 whitespace-nowrap">{t.hero.flow[index]}</p>
                  </div>
                  {index < 3 ? (
                    <Arrow className="hidden size-3.5 shrink-0 text-navy-foreground/40 sm:block" />
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* WHAT IS DIRAYA */}
      <section id="what-is-diraya" className="scroll-mt-20 border-b border-border bg-background py-20">
        <div className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-10">
          <h2 className={cn(heading, "text-3xl sm:text-4xl")}>{t.what.title}</h2>
          <p className="mt-4 max-w-3xl text-base leading-8 text-muted-foreground">{t.what.body}</p>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {t.what.cards.map((card, index) => {
              const Icon = whatIcons[index]!;
              return (
                <article
                  key={card.title}
                  className="rounded-xl border border-border bg-card p-6 shadow-sm transition-shadow hover:shadow-md"
                >
                  <span className="flex size-11 items-center justify-center rounded-lg bg-primary/8 text-primary">
                    <Icon className="size-5" />
                  </span>
                  <h3 className={cn(heading, "mt-5 text-xl")}>{card.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-muted-foreground">{card.body}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* VISION */}
      <section id="vision" className="scroll-mt-20 border-b border-border bg-secondary/40 py-20">
        <div className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-10">
          <h2 className={cn(heading, "text-3xl sm:text-4xl")}>{t.vision.title}</h2>
          <p className={cn(heading, "mt-4 text-xl text-safety-deep sm:text-2xl")}>{t.vision.statement}</p>
          <p className="mt-4 max-w-3xl text-base leading-8 text-muted-foreground">{t.vision.body}</p>

          <div className="mt-10 grid gap-5 lg:grid-cols-2">
            <div className="rounded-xl border border-border bg-card p-6">
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                {t.vision.reactiveLabel}
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {t.vision.reactive.map((step, index) => (
                  <div key={step} className="flex items-center gap-2">
                    <span className="rounded-md border border-border bg-muted px-3 py-2 text-sm font-semibold text-muted-foreground">
                      {step}
                    </span>
                    {index < t.vision.reactive.length - 1 ? <Arrow className="size-4 text-muted-foreground/60" /> : null}
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-primary/25 bg-primary/5 p-6">
              <p className="text-xs font-bold uppercase tracking-wide text-primary">{t.vision.dirayaLabel}</p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {t.vision.diraya.map((step, index) => (
                  <div key={step} className="flex items-center gap-2">
                    <span
                      className={cn(
                        "rounded-md px-3 py-2 text-sm font-bold",
                        index === t.vision.diraya.length - 1
                          ? "bg-positive/12 text-positive-deep"
                          : "bg-card text-foreground shadow-sm",
                      )}
                    >
                      {step}
                    </span>
                    {index < t.vision.diraya.length - 1 ? <Arrow className="size-4 text-safety" /> : null}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* GOALS */}
      <section id="goals" className="scroll-mt-20 border-b border-border bg-background py-20">
        <div className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-10">
          <h2 className={cn(heading, "text-3xl sm:text-4xl")}>{t.goals.title}</h2>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {t.goals.items.map((goal, index) => {
              const Icon = goalIcons[index]!;
              return (
                <article
                  key={goal}
                  className="rounded-xl border border-border bg-card p-6 shadow-sm transition-transform hover:-translate-y-0.5"
                >
                  <span className="flex size-10 items-center justify-center rounded-lg bg-safety/12 text-safety-deep">
                    <Icon className="size-5" />
                  </span>
                  <p className="mt-4 text-sm font-bold leading-7 text-foreground">{goal}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how-it-works" className="scroll-mt-20 bg-navy-deep py-20 text-navy-foreground">
        <div className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-10">
          <h2 className={cn(heading, "text-3xl sm:text-4xl")}>{t.how.title}</h2>
          <p className="mt-4 max-w-2xl text-base leading-8 text-navy-foreground/70">{t.how.subtitle}</p>
          

          <div className="mt-10 space-y-2">
            <div className="flex items-center gap-3 rounded-xl border border-navy-foreground/12 bg-navy/40 px-5 py-4">
              <Camera className="size-5 text-navy-foreground/70" />
              <p className="text-sm font-bold">{t.how.source}</p>
            </div>
            <FlowArrow />

            {t.how.agents.map((agent, index) => {
              const Icon = agentIcons[index]!;
              return (
                <div key={agent.en}>
                  <article className="rounded-xl border border-navy-foreground/14 bg-navy/45 p-5 sm:p-6">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="flex size-11 items-center justify-center rounded-lg bg-safety/15 text-safety">
                        <Icon className="size-5" />
                      </span>
                      <div>
                        <p className={cn(heading, "text-lg")}>{agent.name}</p>
                        <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.14em] text-navy-foreground/50">
                          {agent.en}
                        </p>
                      </div>
                    </div>
                    <p className="mt-4 text-sm leading-7 text-navy-foreground/72">{agent.role}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {agent.tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-md border border-navy-foreground/14 bg-navy-foreground/7 px-2.5 py-1 text-xs font-semibold text-navy-foreground/80"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </article>
                  <FlowArrow />
                </div>
              );
            })}

            <div className="flex items-center gap-3 rounded-xl border border-positive/30 bg-positive/10 px-5 py-4">
              <ShieldCheck className="size-5 text-positive" />
              <p className="text-sm font-bold text-positive-soft">{t.how.decision}</p>
            </div>
          </div>

          <div className="mt-10 rounded-xl border border-navy-foreground/14 bg-navy/40 p-5 sm:p-6">
            <p className="text-xs font-bold uppercase tracking-wide text-safety">{t.how.exampleLabel}</p>
            <div className="mt-4 space-y-3">
              <div className="flex items-start gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-navy-foreground/10">
                  <MessageSquare className="size-4" />
                </span>
                <p className="rounded-lg bg-navy-foreground/10 px-4 py-3 text-sm">{t.how.question}</p>
              </div>
              <div className="flex items-start gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-safety/15 text-safety">
                  <Bot className="size-4" />
                </span>
                <p className="rounded-lg bg-safety/10 px-4 py-3 text-sm leading-7 text-navy-foreground/85">
                  {t.how.answer}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* FINAL CTA */}
      <section className="bg-navy py-20 text-navy-foreground">
        <div className="mx-auto w-full max-w-[1280px] px-4 text-center sm:px-6 lg:px-10">
          <DirayaMark variant="white" className="mx-auto size-16" />
          <h2 className={cn(heading, "mt-6 text-3xl sm:text-4xl")}>{t.cta.title}</h2>
          <p className="mt-3 text-base text-navy-foreground/75">{t.cta.body}</p>
          <Button
            size="lg"
            onClick={goLogin}
            className="mt-8 h-12 min-w-44 rounded-md bg-safety px-8 text-base font-bold text-navy-deep hover:bg-safety/90"
          >
            {t.cta.action}
            <Arrow className="size-4" />
          </Button>
        </div>
      </section>

      <footer className="border-t border-border bg-background py-8">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-3 px-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-10">
          <p>{t.footerNote}</p>
          <p>DIRAYA © 2026</p>
        </div>
      </footer>
    </main>
  );
}

function FlowArrow() {
  return (
    <div className="flex justify-center py-1.5">
      <ArrowDown className="size-4 animate-pulse text-safety/60" />
    </div>
  );
}
