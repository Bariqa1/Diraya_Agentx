import type { ComponentType } from "react";
import { Construction } from "lucide-react";

import type { Locale } from "@/lib/locale";

export function PlaceholderPage({ locale, title, description, icon: Icon = Construction }: { locale: Locale; title: string; description: string; icon?: ComponentType<{ className?: string }> }) {
  return <div className="mx-auto max-w-[1600px] p-4 sm:p-6 xl:p-8"><section className="flex min-h-[calc(100vh-10rem)] items-center justify-center rounded-lg border border-border bg-card p-8 text-center shadow-sm"><div className="max-w-lg"><span className="mx-auto flex size-12 items-center justify-center rounded-md bg-primary/8 text-primary"><Icon className="size-6" /></span><h1 className="mt-5 text-2xl font-bold text-foreground">{title}</h1><p className="mt-2 text-sm leading-7 text-muted-foreground">{description}</p><p className="mt-5 text-xs font-semibold uppercase text-muted-foreground/70">{locale === "ar" ? "صفحة تجريبية — التنقل يعمل بنجاح" : "Placeholder page — navigation is working"}</p></div></section></div>;
}
