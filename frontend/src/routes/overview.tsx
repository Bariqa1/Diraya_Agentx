import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { OverviewContent } from "@/components/dashboard/overview-content";
import { localeSearch } from "@/lib/locale";

export const Route = createFileRoute("/overview")({
  validateSearch: localeSearch,
  head: () => ({ meta: [
    { title: "نظرة عامة | دِراية — DIRAYA" },
    { name: "description", content: "مركز دِراية لمتابعة حالة السلامة والمخاطر والتنبيهات الحالية." },
    { property: "og:title", content: "نظرة عامة | دِراية — DIRAYA" },
    { property: "og:description", content: "Safety status, active risks, and AI recommendations at a glance." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary" },
  ] }),
  component: OverviewPage,
});

function OverviewPage() { const { lang } = Route.useSearch(); return <DashboardShell locale={lang} currentPath="/overview"><OverviewContent locale={lang} /></DashboardShell>; }
