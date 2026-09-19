import { createFileRoute } from "@tanstack/react-router";
import { BriefcaseBusiness, Building2, Mail, MapPin, UserRound } from "lucide-react";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { cn } from "@/lib/utils";
import { localeSearch } from "@/lib/locale";

const profile = {
  name: { ar: "أحمد العتيبي", en: "Ahmed Alotaibi" },
  email: "demo@diraya.ai",
  role: { ar: "مسؤول السلامة", en: "Safety Officer" },
  facility: { ar: "المنشأة الصناعية الرئيسية", en: "Main Industrial Facility" },
  location: { ar: "الرياض، المملكة العربية السعودية", en: "Riyadh, Saudi Arabia" },
};

const copy = {
  ar: { title: "الملف الشخصي", description: "معلومات حساب المستخدم وموقع العمل.", name: "الاسم", email: "البريد الإلكتروني", role: "الدور", facility: "المنشأة / الموقع" },
  en: { title: "Profile", description: "User account and workplace information.", name: "Name", email: "Email Address", role: "Role", facility: "Facility / Location" },
} as const;

export const Route = createFileRoute("/profile")({
  validateSearch: localeSearch,
  head: () => ({ meta: [{ title: "الملف الشخصي | دِراية — DIRAYA" }, { name: "description", content: "معلومات حساب المستخدم وموقع العمل في دِراية." }, { property: "og:title", content: "Profile | DIRAYA" }, { property: "og:description", content: "DIRAYA user account and workplace information." }, { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary" }] }),
  component: Page,
});

function Page() {
  const { lang } = Route.useSearch();
  const text = copy[lang];
  const arabic = lang === "ar";
  const details = [
    { label: text.name, value: profile.name[lang], icon: UserRound },
    { label: text.email, value: profile.email, icon: Mail, ltr: true },
    { label: text.role, value: profile.role[lang], icon: BriefcaseBusiness },
    { label: text.facility, value: `${profile.facility[lang]} · ${profile.location[lang]}`, icon: Building2 },
  ];

  return (
    <DashboardShell locale={lang} currentPath="/profile">
      <div className="mx-auto max-w-[1600px] space-y-4 p-4 sm:p-5 xl:px-7 xl:py-5">
        <div>
          <h1 className={cn("text-2xl font-bold text-foreground sm:text-3xl", !arabic && "font-display")}>{text.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{text.description}</p>
        </div>

        <section className="max-w-3xl overflow-hidden rounded-lg border border-border bg-card shadow-sm">
          <div className="flex items-center gap-4 border-b border-border p-5 sm:p-6">
            <span className="flex size-14 shrink-0 items-center justify-center rounded-lg bg-primary/8 text-primary"><UserRound className="size-7" /></span>
            <div className="min-w-0">
              <h2 className="truncate text-lg font-bold text-foreground">{profile.name[lang]}</h2>
              <p className="mt-0.5 text-sm font-medium text-muted-foreground">{profile.role[lang]}</p>
            </div>
          </div>
          <dl className="divide-y divide-border">
            {details.map((detail) => (
              <div key={detail.label} className="grid gap-2 px-5 py-4 sm:grid-cols-[180px_minmax(0,1fr)] sm:items-center sm:px-6">
                <dt className="flex items-center gap-2 text-xs font-semibold text-muted-foreground"><detail.icon className="size-4 text-primary" />{detail.label}</dt>
                <dd className="text-sm font-semibold text-foreground" dir={detail.ltr ? "ltr" : undefined}>{detail.value}</dd>
              </div>
            ))}
          </dl>
          <div className="flex items-center gap-2 border-t border-border bg-muted/30 px-5 py-3 text-xs text-muted-foreground sm:px-6"><MapPin className="size-3.5 text-primary" />{profile.location[lang]}</div>
        </section>
      </div>
    </DashboardShell>
  );
}
