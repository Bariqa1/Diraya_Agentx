import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { RiskMapContent } from "@/components/dashboard/risk-map-content";
import { localeSearch } from "@/lib/locale";

export const Route = createFileRoute("/risk-map")({
  validateSearch: localeSearch,
  head: () => ({
    meta: [
      { title: "المخاطر وصلاحيات الدخول | دِراية — DIRAYA" },
      { name: "description", content: "مناطق المخاطر وصلاحيات الدخول وألوان الخوذ في بيئة العمل." },
      { property: "og:title", content: "Risks & Access Permissions | DIRAYA" },
      { property: "og:description", content: "Workplace zones, physical RBAC, and current risk levels." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Page,
});

function Page() {
  const { lang } = Route.useSearch();
  return (
    <DashboardShell locale={lang} currentPath="/risk-map">
      <RiskMapContent locale={lang} />
    </DashboardShell>
  );
}

