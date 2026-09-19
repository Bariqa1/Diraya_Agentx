import { useState, type FormEvent } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { AlertCircle, ArrowLeft, ArrowRight, Building2, BriefcaseBusiness, CheckCircle2, Eye, EyeOff, Loader2, Lock, Mail, UserRound } from "lucide-react";
import { z } from "zod";

import industrialImage from "@/assets/diraya-industrial.jpg";
import { DirayaWordmark } from "@/components/diraya-brand";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Button } from "@/components/ui/button";
import { isArabic, localeSearch } from "@/lib/locale";

export const Route = createFileRoute("/signup")({
  validateSearch: localeSearch,
  head: () => ({
    meta: [
      { title: "إنشاء حساب | دِراية — DIRAYA" },
      { name: "description", content: "أنشئ حسابًا جديدًا في منصة دِراية للسلامة الصناعية." },
      { property: "og:title", content: "إنشاء حساب | دِراية — DIRAYA" },
      { property: "og:description", content: "Create your DIRAYA industrial safety account." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: SignupPage,
});

const translations = {
  ar: {
    title: "إنشاء حساب",
    subtitle: "أنشئ حسابك للانضمام إلى دِراية",
    fullName: "الاسم الكامل",
    fullNamePlaceholder: "أدخل الاسم الكامل",
    email: "البريد الإلكتروني",
    emailPlaceholder: "أدخل بريدك الإلكتروني",
    password: "كلمة المرور",
    passwordPlaceholder: "أنشئ كلمة مرور قوية",
    confirmPassword: "تأكيد كلمة المرور",
    confirmPasswordPlaceholder: "أعد إدخال كلمة المرور",
    role: "الدور الوظيفي",
    rolePlaceholder: "اختر الدور الوظيفي",
    facility: "اسم المنشأة",
    facilityPlaceholder: "أدخل اسم المنشأة",
    roles: ["مسؤول السلامة", "مشرف الموقع", "مدير العمليات", "مهندس سلامة"],
    submit: "إنشاء الحساب",
    submitting: "جارٍ إنشاء الحساب…",
    success: "تم التحقق من بيانات الحساب بنجاح.",
    hasAccount: "لديك حساب بالفعل؟",
    signIn: "تسجيل الدخول",
    back: "العودة",
    show: "إظهار كلمة المرور",
    hide: "إخفاء كلمة المرور",
    required: "هذا الحقل مطلوب.",
    invalidEmail: "أدخل بريدًا إلكترونيًا صحيحًا.",
    shortName: "يجب ألا يقل الاسم عن حرفين.",
    longValue: "القيمة المدخلة طويلة جدًا.",
    weakPassword: "استخدم 8 أحرف على الأقل تتضمن حرفًا كبيرًا وصغيرًا ورقمًا.",
    mismatch: "كلمتا المرور غير متطابقتين.",
    visualTitle: "دِراية بالخطر، حماية لهم",
    visualBody: "لأن خلف كل خوذة عائلة تنتظر، نسخر التقنية لتحمي الحياة أولاً",
    monitor: "نظام مراقبة ذكي",
  },
  en: {
    title: "Create an account",
    subtitle: "Create your account to join DIRAYA",
    fullName: "Full name",
    fullNamePlaceholder: "Enter your full name",
    email: "Email",
    emailPlaceholder: "Enter your email",
    password: "Password",
    passwordPlaceholder: "Create a strong password",
    confirmPassword: "Confirm password",
    confirmPasswordPlaceholder: "Re-enter your password",
    role: "Job role",
    rolePlaceholder: "Select your job role",
    facility: "Facility name",
    facilityPlaceholder: "Enter your facility name",
    roles: ["Safety Officer", "Site Supervisor", "Operations Manager", "Safety Engineer"],
    submit: "Create Account",
    submitting: "Creating account…",
    success: "Your account details were validated successfully.",
    hasAccount: "Already have an account?",
    signIn: "Sign In",
    back: "Back",
    show: "Show password",
    hide: "Hide password",
    required: "This field is required.",
    invalidEmail: "Enter a valid email address.",
    shortName: "Name must contain at least 2 characters.",
    longValue: "This value is too long.",
    weakPassword: "Use at least 8 characters with uppercase, lowercase, and a number.",
    mismatch: "Passwords do not match.",
    visualTitle: "Where safety reaches further.",
    visualBody: "Operational awareness that turns detected risks into actionable, preventive decisions.",
    monitor: "Intelligent safety monitoring",
  },
} as const;

type FieldName = "fullName" | "email" | "password" | "confirmPassword" | "role" | "facility";
type FormValues = Record<FieldName, string>;

const initialValues: FormValues = { fullName: "", email: "", password: "", confirmPassword: "", role: "", facility: "" };
const inputClass = "h-12 w-full rounded-md border border-input bg-card ps-11 pe-11 text-sm text-foreground outline-none transition-[border-color,box-shadow] placeholder:text-muted-foreground/70 focus:border-safety-deep focus:ring-[3px] focus:ring-safety/20";

function SignupPage() {
  const { lang } = Route.useSearch();
  const navigate = useNavigate();
  const arabic = isArabic(lang);
  const copy = translations[lang];
  const [values, setValues] = useState<FormValues>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const BackArrow = arabic ? ArrowRight : ArrowLeft;

  function changeLanguage(next: "ar" | "en") {
    navigate({ to: "/signup", search: { lang: next }, replace: true });
  }

  function updateField(field: FieldName, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setSuccess(false);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const schema = z.object({
      fullName: z.string().trim().min(2, copy.shortName).max(100, copy.longValue),
      email: z.string().trim().min(1, copy.required).email(copy.invalidEmail).max(255, copy.longValue),
      password: z.string().min(1, copy.required).max(128, copy.longValue).regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/, copy.weakPassword),
      confirmPassword: z.string().min(1, copy.required).max(128, copy.longValue),
      role: z.string().trim().min(1, copy.required).max(80, copy.longValue),
      facility: z.string().trim().min(1, copy.required).max(120, copy.longValue),
    }).refine((data) => data.password === data.confirmPassword, { path: ["confirmPassword"], message: copy.mismatch });
    const result = schema.safeParse(values);

    if (!result.success) {
      const nextErrors: Partial<Record<FieldName, string>> = {};
      result.error.issues.forEach((issue) => {
        const field = issue.path[0];
        if (typeof field === "string" && !(field in nextErrors)) nextErrors[field as FieldName] = issue.message;
      });
      setErrors(nextErrors);
      setSuccess(false);
      return;
    }

    setSubmitting(true);
    window.setTimeout(() => {
      setSubmitting(false);
      setSuccess(true);
    }, 600);
  }

  const identityFields = [
    { name: "fullName" as const, label: copy.fullName, placeholder: copy.fullNamePlaceholder, icon: UserRound, type: "text", autoComplete: "name" },
    { name: "email" as const, label: copy.email, placeholder: copy.emailPlaceholder, icon: Mail, type: "email", autoComplete: "email" },
  ];

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
        <div className="relative flex items-center gap-3 text-xs text-navy-foreground/55"><span className="size-2 rounded-full bg-positive" /><span>{copy.monitor}</span></div>
      </aside>

      <section className="flex min-h-screen flex-col px-5 py-6 sm:px-8 lg:px-12">
        <div className="flex items-center justify-between gap-4">
          <Button variant="ghost" size="sm" asChild className="gap-2 text-muted-foreground"><Link to="/login" search={{ lang }}><BackArrow className="size-4" />{copy.back}</Link></Button>
          <LanguageSwitcher locale={lang} onChange={changeLanguage} />
        </div>

        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <DirayaWordmark locale={lang} variant="navy" compact className="mb-8 text-foreground lg:hidden" />
          <div className="animate-fade-up">
            <h2 className={arabic ? "font-arabic text-3xl font-bold text-foreground" : "font-display text-3xl font-bold text-foreground"}>{copy.title}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{copy.subtitle}</p>

            <form onSubmit={handleSubmit} noValidate className="mt-7 space-y-4">
              {identityFields.map((field) => <TextField key={field.name} {...field} value={values[field.name]} error={errors[field.name]} onChange={(value) => updateField(field.name, value)} />)}

              <div className="grid gap-4 sm:grid-cols-2">
                <PasswordField id="signup-password" label={copy.password} placeholder={copy.passwordPlaceholder} value={values.password} error={errors.password} visible={showPassword} toggle={() => setShowPassword((value) => !value)} showLabel={copy.show} hideLabel={copy.hide} autoComplete="new-password" onChange={(value) => updateField("password", value)} />
                <PasswordField id="signup-confirm-password" label={copy.confirmPassword} placeholder={copy.confirmPasswordPlaceholder} value={values.confirmPassword} error={errors.confirmPassword} visible={showConfirmPassword} toggle={() => setShowConfirmPassword((value) => !value)} showLabel={copy.show} hideLabel={copy.hide} autoComplete="new-password" onChange={(value) => updateField("confirmPassword", value)} />
              </div>

              <div>
                <label htmlFor="role" className="mb-2 block text-sm font-semibold text-foreground">{copy.role}</label>
                <div className="relative">
                  <BriefcaseBusiness className="pointer-events-none absolute start-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <select id="role" value={values.role} onChange={(event) => updateField("role", event.target.value)} aria-invalid={Boolean(errors.role)} className={`${inputClass} appearance-none ${errors.role ? "border-destructive focus:border-destructive focus:ring-destructive/15" : ""}`}>
                    <option value="">{copy.rolePlaceholder}</option>
                    {copy.roles.map((role) => <option key={role} value={role}>{role}</option>)}
                  </select>
                </div>
                <FieldError message={errors.role} />
              </div>

              <TextField name="facility" label={copy.facility} placeholder={copy.facilityPlaceholder} icon={Building2} type="text" autoComplete="organization" value={values.facility} error={errors.facility} onChange={(value) => updateField("facility", value)} />

              {success ? <div role="status" className="flex items-center gap-2 rounded-md border border-positive/30 bg-positive/10 px-3.5 py-3 text-sm font-medium text-positive-deep"><CheckCircle2 className="size-4 shrink-0" />{copy.success}</div> : null}

              <Button type="submit" disabled={submitting} className="h-12 w-full rounded-md text-sm font-bold shadow-lg shadow-primary/15">
                {submitting ? <><Loader2 className="animate-spin" />{copy.submitting}</> : copy.submit}
              </Button>
            </form>

            <p className="mt-7 text-center text-sm text-muted-foreground">{copy.hasAccount} <Link to="/login" search={{ lang }} className="font-semibold text-primary hover:underline">{copy.signIn}</Link></p>
          </div>
        </div>
        <p className="text-center text-xs text-muted-foreground/65">DIRAYA · {arabic ? "نظام ذكي للسلامة الصناعية" : "Smart system for industrial safety"}</p>
      </section>
    </main>
  );
}

function TextField({ name, label, placeholder, icon: Icon, type, autoComplete, value, error, onChange }: { name: FieldName; label: string; placeholder: string; icon: typeof UserRound; type: string; autoComplete: string; value: string; error: string | undefined; onChange: (value: string) => void }) {
  return <div><label htmlFor={name} className="mb-2 block text-sm font-semibold text-foreground">{label}</label><div className="relative"><Icon className="pointer-events-none absolute start-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" /><input id={name} type={type} autoComplete={autoComplete} maxLength={type === "email" ? 255 : 120} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} aria-invalid={Boolean(error)} className={`${inputClass} ${error ? "border-destructive focus:border-destructive focus:ring-destructive/15" : ""}`} /></div><FieldError message={error} /></div>;
}

function PasswordField({ id, label, placeholder, value, error, visible, toggle, showLabel, hideLabel, autoComplete, onChange }: { id: string; label: string; placeholder: string; value: string; error: string | undefined; visible: boolean; toggle: () => void; showLabel: string; hideLabel: string; autoComplete: string; onChange: (value: string) => void }) {
  return <div><label htmlFor={id} className="mb-2 block text-sm font-semibold text-foreground">{label}</label><div className="relative"><Lock className="pointer-events-none absolute start-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" /><input id={id} type={visible ? "text" : "password"} autoComplete={autoComplete} maxLength={128} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} aria-invalid={Boolean(error)} className={`${inputClass} ${error ? "border-destructive focus:border-destructive focus:ring-destructive/15" : ""}`} /><Button type="button" variant="ghost" size="icon" onClick={toggle} aria-label={visible ? hideLabel : showLabel} className="absolute end-1.5 top-1/2 -translate-y-1/2 text-muted-foreground">{visible ? <EyeOff /> : <Eye />}</Button></div><FieldError message={error} /></div>;
}

function FieldError({ message }: { message: string | undefined }) {
  return message ? <p className="mt-1.5 flex items-center gap-1.5 text-xs text-destructive"><AlertCircle className="size-3.5 shrink-0" />{message}</p> : null;
}