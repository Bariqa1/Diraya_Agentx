import { createFileRoute } from "@tanstack/react-router";
import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { IncidentLogContent } from "@/components/dashboard/incident-log";
import { localeSearch } from "@/lib/locale";

export const Route = createFileRoute("/incidents")({
  validateSearch: localeSearch,
  head: () => ({
    meta: [
      { title: "سجل الحوادث | دِراية — DIRAYA" },
      { name: "description", content: "السجل الكامل للحوادث والمخالفات المسجلة في منصة دِراية لمراقبة السلامة." },
      { property: "og:title", content: "Incident Log | DIRAYA" },
      { property: "og:description", content: "Complete record of detected workplace safety incidents and violations." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Page,
});

function Page() {
  const { lang } = Route.useSearch();
  return (
    <DashboardShell locale={lang} currentPath="/incidents">
      <IncidentLogContent locale={lang} />
    </DashboardShell>
  );
}
