import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  Bell,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  UserRound,
} from "lucide-react";

import { LanguageSwitcher } from "@/components/language-switcher";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { DirayaMark } from "@/components/diraya-brand";
import { cn } from "@/lib/utils";
import type { Locale } from "@/lib/locale";
import { dashboardNav, type DashboardPath } from "./dashboard-data";

const routeTitles: Record<DashboardPath, { ar: string; en: string }> = {
  "/overview": { ar: "نظرة عامة", en: "Overview" },
  "/alerts": { ar: "التنبيهات", en: "Alerts" },
  "/risk-map": { ar: "المخاطر وصلاحيات الدخول", en: "Risks & Access Permissions" },
  "/incidents": { ar: "سجل الحوادث", en: "Incident Log" },
  "/analytics": { ar: "التحليلات", en: "Analytics" },
  "/ai-assistant": { ar: "المساعد الذكي", en: "AI Assistant" },
  "/profile": { ar: "الملف الشخصي", en: "Profile" },
};

export function DashboardShell({
  locale,
  currentPath,
  children,
}: {
  locale: Locale;
  currentPath: DashboardPath;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  const arabic = locale === "ar";
  const [collapsed, setCollapsed] = useState(false);
  const date = new Intl.DateTimeFormat(arabic ? "ar-SA" : "en-US", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    calendar: "gregory",
    numberingSystem: arabic ? "arab" : "latn",
    timeZone: "Asia/Riyadh",
  }).format(new Date());

  function changeLanguage(next: Locale) {
    navigate({ to: currentPath, search: { lang: next }, replace: true });
  }

  function logout() {
    navigate({ to: "/login", search: { lang: locale }, replace: true });
  }

  return (
    <TooltipProvider delayDuration={200}>
      <div dir={arabic ? "rtl" : "ltr"} lang={locale} className={cn("min-h-screen bg-muted/40", arabic && "font-arabic")}>
        <div className="flex min-h-screen w-full">
          <aside className={cn("sticky top-0 hidden h-screen shrink-0 flex-col border-e border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 lg:flex", collapsed ? "w-[76px]" : "w-64")}>
            <div className={cn("flex h-20 items-center border-b border-sidebar-border px-4", collapsed ? "justify-center" : "justify-between")}>
              <Link to="/overview" search={{ lang: locale }} className="flex items-center">
                {collapsed ? <DashboardMark className="size-9" /> : <DashboardWordmark locale={locale} />}
              </Link>
              {!collapsed ? (
                <Button variant="ghost" size="icon" onClick={() => setCollapsed(true)} aria-label={arabic ? "طي القائمة" : "Collapse sidebar"} className="size-8 text-muted-foreground">
                  {arabic ? <PanelLeftOpen /> : <PanelLeftClose />}
                </Button>
              ) : null}
            </div>
            {collapsed ? (
              <div className="flex justify-center pt-3">
                <Button variant="ghost" size="icon" onClick={() => setCollapsed(false)} aria-label={arabic ? "فتح القائمة" : "Expand sidebar"} className="size-9 text-muted-foreground">
                  {arabic ? <PanelLeftClose /> : <PanelLeftOpen />}
                </Button>
              </div>
            ) : null}
            <SidebarNavigation locale={locale} currentPath={currentPath} collapsed={collapsed} />
            <div className="mt-auto border-t border-sidebar-border p-3">
              <SidebarFooter locale={locale} currentPath={currentPath} collapsed={collapsed} onLogout={logout} />
            </div>
          </aside>

          <div className="min-w-0 flex-1">
            <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur">
              <div className="flex h-16 items-center justify-between gap-3 px-4 sm:px-6 xl:px-8">
                <div className="flex min-w-0 items-center gap-3">
                  <Sheet>
                    <SheetTrigger asChild>
                      <Button variant="outline" size="icon" aria-label={arabic ? "فتح القائمة" : "Open menu"} className="lg:hidden">
                        <Menu />
                      </Button>
                    </SheetTrigger>
                    <SheetContent side={arabic ? "right" : "left"} className="w-[292px] border-sidebar-border bg-sidebar p-0 text-sidebar-foreground">
                      <SheetTitle className="sr-only">{arabic ? "التنقل الرئيسي" : "Main navigation"}</SheetTitle>
                      <div className="flex h-20 items-center border-b border-sidebar-border px-5">
                        <Link to="/overview" search={{ lang: locale }} className="flex items-center">
                          <DashboardWordmark locale={locale} />
                        </Link>
                      </div>
                      <SidebarNavigation locale={locale} currentPath={currentPath} mobile />
                      <div className="absolute inset-x-0 bottom-0 border-t border-sidebar-border p-3">
                        <SidebarFooter locale={locale} currentPath={currentPath} onLogout={logout} mobile />
                      </div>
                    </SheetContent>
                  </Sheet>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-foreground">{routeTitles[currentPath][locale]}</p>
                    <p className="hidden truncate text-xs text-muted-foreground sm:block">{date}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="hidden md:block"><LanguageSwitcher locale={locale} onChange={changeLanguage} /></div>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="outline" size="icon" asChild className="relative">
                        <Link to="/alerts" search={{ lang: locale }} aria-label={arabic ? "فتح سجل التنبيهات" : "Open alert log"}>
                          <Bell />
                          <span className="absolute end-1.5 top-1.5 size-2 rounded-full bg-destructive ring-2 ring-background" />
                        </Link>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>{arabic ? "إشعاران جديدان" : "2 new notifications"}</TooltipContent>
                  </Tooltip>
                  <Button variant="ghost" className="h-10 gap-2 px-1.5 sm:px-2" onClick={() => navigate({ to: "/profile", search: { lang: locale } })}>
                    <Avatar className="size-8 border border-border"><AvatarFallback className="bg-primary text-xs font-bold text-primary-foreground">SO</AvatarFallback></Avatar>
                    <span className="hidden text-start sm:block">
                      <span className="block text-xs font-semibold text-foreground">{arabic ? "ضابط السلامة" : "Safety Officer"}</span>
                      <span className="block text-[11px] text-muted-foreground">{arabic ? "مركز العمليات" : "Operations Center"}</span>
                    </span>
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-between border-t border-border px-4 py-2 md:hidden">
                <span className="text-[11px] text-muted-foreground">{date}</span>
                <LanguageSwitcher locale={locale} onChange={changeLanguage} />
              </div>
            </header>
            <main>{children}</main>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}

function DashboardMark({ className }: { className?: string }) {
  return (
    <DirayaMark variant="auto" className={cn("size-10", className)} />
  );
}

function DashboardWordmark({ locale }: { locale: Locale }) {
  return (
    <div className="flex items-center gap-3 text-foreground">
      <DashboardMark className="size-10" />
      <p className={cn("font-display text-xl font-bold", locale === "ar" && "font-arabic")}>{locale === "ar" ? "دِراية" : "DIRAYA"}</p>
    </div>
  );
}

function SidebarNavigation({ locale, currentPath, collapsed = false, mobile = false }: { locale: Locale; currentPath: DashboardPath; collapsed?: boolean; mobile?: boolean }) {
  return (
    <nav aria-label={locale === "ar" ? "التنقل الرئيسي" : "Main navigation"} className="space-y-1 p-3">
      {dashboardNav.map((item) => {
        const active = currentPath === item.path;
        const content = (
          <Link to={item.path} search={{ lang: locale }} className={cn("flex h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors", active ? "bg-sidebar-primary text-sidebar-primary-foreground" : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground", collapsed && "justify-center px-0")}>
            <item.icon className="size-[18px] shrink-0" />
            {!collapsed ? <span>{item[locale]}</span> : null}
          </Link>
        );
        if (mobile) return <SheetClose asChild key={item.path}>{content}</SheetClose>;
        if (collapsed) return <Tooltip key={item.path}><TooltipTrigger asChild>{content}</TooltipTrigger><TooltipContent side={locale === "ar" ? "left" : "right"}>{item[locale]}</TooltipContent></Tooltip>;
        return <div key={item.path}>{content}</div>;
      })}
    </nav>
  );
}

function SidebarFooter({ locale, currentPath, collapsed = false, mobile = false, onLogout }: { locale: Locale; currentPath: DashboardPath; collapsed?: boolean; mobile?: boolean; onLogout: () => void }) {
  const profile = (
    <Link to="/profile" search={{ lang: locale }} className={cn("flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors", currentPath === "/profile" ? "bg-sidebar-primary text-sidebar-primary-foreground" : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground", collapsed && "justify-center px-0")}>
      <UserRound className="size-[18px]" />{!collapsed ? <span>{locale === "ar" ? "الملف الشخصي" : "Profile"}</span> : null}
    </Link>
  );
  return (
    <div className="space-y-1">
      {mobile ? <SheetClose asChild>{profile}</SheetClose> : profile}
      <Button variant="ghost" onClick={onLogout} className={cn("h-10 w-full justify-start gap-3 px-3 text-muted-foreground hover:bg-destructive/8 hover:text-destructive", collapsed && "justify-center px-0")}>
        <LogOut className="size-[18px]" />{!collapsed ? <span>{locale === "ar" ? "تسجيل الخروج" : "Logout"}</span> : null}
      </Button>
    </div>
  );
}

export function SectionLink({ locale, to, children, className }: { locale: Locale; to: DashboardPath; children: ReactNode; className?: string }) {
  const Arrow = locale === "ar" ? ChevronLeft : ChevronRight;
  return <Button variant="ghost" size="sm" asChild className={cn("gap-1.5 text-primary", className)}><Link to={to} search={{ lang: locale }}>{children}<Arrow className="size-4" /></Link></Button>;
}
