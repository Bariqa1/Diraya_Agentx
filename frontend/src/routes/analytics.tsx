import { createFileRoute } from "@tanstack/react-router";
import { AnalyticsContent } from "@/components/dashboard/analytics-content";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { localeSearch } from "@/lib/locale";
export const Route = createFileRoute("/analytics")({ validateSearch: localeSearch, head: () => ({ meta: [{ title: "التحليلات | دِراية — DIRAYA" }, { name: "description", content: "تحليلات أداء السلامة واتجاهات المخاطر." }, { property: "og:title", content: "Analytics | DIRAYA" }, { property: "og:description", content: "Safety performance analytics and risk trends." }, { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary" }] }), component: Page });
function Page() {
  const { lang } = Route.useSearch();
  return (
    <DashboardShell locale={lang} currentPath="/analytics">
      <AnalyticsContent locale={lang} />
    </DashboardShell>
  );
}
