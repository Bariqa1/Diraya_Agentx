import { useState, type FormEvent } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { AlertCircle, ArrowLeft, ArrowRight, Check, Eye, EyeOff, Loader2, Lock, Mail } from "lucide-react";

import industrialImage from "@/assets/diraya-industrial.jpg";
import { DirayaWordmark } from "@/components/diraya-brand";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Button } from "@/components/ui/button";
import { isArabic, localeSearch } from "@/lib/locale";

export const Route = createFileRoute("/login")({
  validateSearch: localeSearch,
  head: () => ({
    meta: [
      { title: "تسجيل الدخول | دِراية — DIRAYA" },
      { name: "description", content: "سجّل الدخول إلى منصة دِراية لمراقبة السلامة وإدارة المخاطر استباقيًا." },
      { property: "og:title", content: "تسجيل الدخول | دِراية — DIRAYA" },
      { property: "og:description", content: "الدخول إلى منصة ذكاء السلامة دِراية." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: LoginPage,
});

const translations = {
  ar: {
    title: "مرحبًا بعودتك",
    subtitle: "سجّل الدخول إلى دِراية",
    email: "البريد الإلكتروني",
    emailPlaceholder: "أدخل بريدك الإلكتروني",
    password: "كلمة المرور",
    passwordPlaceholder: "أدخل كلمة المرور",
    remember: "تذكرني",
    forgot: "هل نسيت كلمة المرور؟",
    submit: "تسجيل الدخول",
    submitting: "جارٍ تسجيل الدخول…",
    noAccount: "ليس لديك حساب؟",
    createAccount: "إنشاء حساب",
    invalidEmail: "أدخل بريدًا إلكترونيًا صحيحًا.",
    requiredEmail: "البريد الإلكتروني مطلوب.",
    requiredPassword: "كلمة المرور مطلوبة.",
    invalidCredentials: "البريد الإلكتروني أو كلمة المرور غير صحيحة.",
    visualTitle: "دِراية بالخطر، حماية لهم",
    visualBody: "لأن خلف كل خوذة عائلة تنتظر، نسخر التقنية لتحمي الحياة أولاً",
    back: "العودة",
    show: "إظهار كلمة المرور",
    hide: "إخفاء كلمة المرور",
  },
  en: {
    title: "Welcome back",
    subtitle: "Sign in to your DIRAYA account",
    email: "Email",
    emailPlaceholder: "Enter your email",
    password: "Password",
    passwordPlaceholder: "Enter your password",
    remember: "Remember me",
    forgot: "Forgot password?",
    submit: "Sign In",
    submitting: "Signing in…",
    noAccount: "Don’t have an account?",
    createAccount: "Create Account",
    invalidEmail: "Enter a valid email address.",
    requiredEmail: "Email is required.",
    requiredPassword: "Password is required.",
    invalidCredentials: "Incorrect email or password.",
    visualTitle: "Where safety reaches further.",
    visualBody: "Operational awareness that turns detected risks into actionable, preventive decisions.",
    back: "Back",
    show: "Show password",
    hide: "Hide password",
  },
} as const;

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const inputClass = "h-12 w-full rounded-md border border-input bg-card ps-11 pe-11 text-sm text-foreground outline-none transition-[border-color,box-shadow] placeholder:text-muted-foreground/70 focus:border-safety-deep focus:ring-[3px] focus:ring-safety/20";

function LoginPage() {
  const { lang } = Route.useSearch();
  const navigate = useNavigate();
  const arabic = isArabic(lang);
  const copy = translations[lang];
  const [email, setEmail] = useState("demo@diraya.ai");
  const [password, setPassword] = useState("Demo123!");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [authError, setAuthError] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const BackArrow = arabic ? ArrowRight : ArrowLeft;

  function changeLanguage(next: "ar" | "en") {
    navigate({ to: "/login", search: { lang: next }, replace: true });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");
    const nextErrors: typeof errors = {};
    if (!email.trim()) nextErrors.email = copy.requiredEmail;
    else if (!emailPattern.test(email)) nextErrors.email = copy.invalidEmail;
    if (!password) nextErrors.password = copy.requiredPassword;
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    window.setTimeout(() => {
      if (email.trim().toLowerCase() === "demo@diraya.ai" && password === "Demo123!") {
        navigate({ to: "/overview", search: { lang } });
        return;
      }
      setSubmitting(false);
      setAuthError(copy.invalidCredentials);
    }, 700);
  }

  return (
    <main dir={arabic ? "rtl" : "ltr"} lang={lang} className="min-h-screen bg-background lg:grid lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden min-h-screen overflow-hidden bg-navy-deep text-navy-foreground lg:flex lg:flex-col lg:justify-between lg:p-12 xl:p-16">
        <img src={industrialImage} alt="" width={1600} height={1000} className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,color-mix(in_oklch,var(--navy-deep)_72%,transparent),color-mix(in_oklch,var(--navy-deep)_86%,transparent))]" />
        <DirayaWordmark locale={lang} variant="white" className="relative text-navy-foreground" />
        <div className="relative max-w-lg animate-fade-up">
          <div className="mb-5 h-px w-16 bg-safety" />
          <h1 className={arabic ? "font-arabic text-4xl font-bold leading-tight" : "font-display text-4xl font-bold leading-tight"}>{copy.visualTitle}</h1>
          <p className="mt-4 max-w-md text-base leading-8 text-navy-foreground/68">{copy.visualBody}</p>
        </div>
        <div className="relative flex items-center gap-3 text-xs text-navy-foreground/55">
          <span className="size-2 rounded-full bg-positive" />
          <span>{arabic ? "نظام مراقبة ذكي" : "Intelligent safety monitoring"}</span>
        </div>
      </aside>

      <section className="flex min-h-screen flex-col px-5 py-6 sm:px-8 lg:px-12">
        <div className="flex items-center justify-between gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/", search: { lang } })} className="gap-2 text-muted-foreground">
            <BackArrow className="size-4" />
            {copy.back}
          </Button>
          <LanguageSwitcher locale={lang} onChange={changeLanguage} />
        </div>

        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-12">
          <DirayaWordmark locale={lang} variant="navy" compact className="mb-10 text-foreground lg:hidden" />
          <div className="animate-fade-up">
            <h2 className={arabic ? "font-arabic text-3xl font-bold text-foreground" : "font-display text-3xl font-bold text-foreground"}>{copy.title}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{copy.subtitle}</p>

            {/* Quick Demo Credentials Info for Judges */}
            <div className="mt-4 flex items-center justify-between rounded-lg border border-primary/20 bg-primary/5 px-3.5 py-2.5 text-xs text-foreground">
              <span className="font-semibold text-primary">
                {arabic ? "💡 حساب تجريبي للتحكيم (معبأ تلقائياً)" : "💡 Demo Credentials (Pre-filled)"}
              </span>
              <span className="font-mono text-[11px] text-muted-foreground">
                demo@diraya.ai / Demo123!
              </span>
            </div>

            <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-5">
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-semibold text-foreground">{copy.email}</label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute start-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <input id="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder={copy.emailPlaceholder} aria-invalid={Boolean(errors.email)} className={`${inputClass} ${errors.email ? "border-destructive focus:border-destructive focus:ring-destructive/15" : ""}`} />
                </div>
                {errors.email ? <p className="mt-1.5 flex items-center gap-1.5 text-xs text-destructive"><AlertCircle className="size-3.5" />{errors.email}</p> : null}
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-semibold text-foreground">{copy.password}</label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute start-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <input id="password" type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder={copy.passwordPlaceholder} aria-invalid={Boolean(errors.password)} className={`${inputClass} ${errors.password ? "border-destructive focus:border-destructive focus:ring-destructive/15" : ""}`} />
                  <Button type="button" variant="ghost" size="icon" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? copy.hide : copy.show} className="absolute end-1.5 top-1/2 -translate-y-1/2 text-muted-foreground">
                    {showPassword ? <EyeOff /> : <Eye />}
                  </Button>
                </div>
                {errors.password ? <p className="mt-1.5 flex items-center gap-1.5 text-xs text-destructive"><AlertCircle className="size-3.5" />{errors.password}</p> : null}
              </div>

              <div className="flex items-center justify-between gap-4">
                <Button type="button" variant="ghost" role="checkbox" aria-checked={remember} onClick={() => setRemember((value) => !value)} className="h-auto gap-2 p-0 text-sm font-medium hover:bg-transparent">
                  <span className={`flex size-[18px] items-center justify-center rounded border ${remember ? "border-primary bg-primary text-primary-foreground" : "border-input bg-card"}`}>{remember ? <Check className="size-3" strokeWidth={3} /> : null}</span>
                  {copy.remember}
                </Button>
                <Button type="button" variant="link" className="h-auto p-0 text-sm text-primary">{copy.forgot}</Button>
              </div>

              {authError ? <div role="alert" className="flex items-center gap-2 rounded-md border border-destructive/25 bg-destructive/8 px-3.5 py-3 text-sm text-destructive"><AlertCircle className="size-4 shrink-0" />{authError}</div> : null}

              <Button type="submit" disabled={submitting} className="h-12 w-full rounded-md text-sm font-bold shadow-lg shadow-primary/15">
                {submitting ? <><Loader2 className="animate-spin" />{copy.submitting}</> : copy.submit}
              </Button>
            </form>

            <p className="mt-8 text-center text-sm text-muted-foreground">
              {copy.noAccount} <Link to="/signup" search={{ lang }} className="font-semibold text-primary hover:underline">{copy.createAccount}</Link>
            </p>
          </div>
        </div>
        <p className="text-center text-xs text-muted-foreground/65">DIRAYA · {arabic ? "نظام ذكي للسلامة الصناعية" : "Smart system for industrial safety"}</p>
      </section>
    </main>
  );
}