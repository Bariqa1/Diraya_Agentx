import { Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Locale } from "@/lib/locale";
import { cn } from "@/lib/utils";

export function LanguageSwitcher({
  locale,
  onChange,
  inverse = false,
}: {
  locale: Locale;
  onChange: (locale: Locale) => void;
  inverse?: boolean;
}) {
  return (
    <div
      className={cn(
        "inline-flex h-10 items-center gap-1 rounded-lg border p-1",
        inverse ? "border-navy-foreground/20 bg-navy-deep/45" : "border-border bg-card",
      )}
      aria-label={locale === "ar" ? "اختيار اللغة" : "Language selection"}
    >
      <Languages className={cn("mx-1 size-4", inverse ? "text-navy-foreground/60" : "text-muted-foreground")} />
      {(["ar", "en"] as const).map((option) => (
        <Button
          key={option}
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onChange(option)}
          aria-pressed={locale === option}
          className={cn(
            "h-7 min-w-14 rounded-md px-2.5 shadow-none",
            locale === option
              ? inverse
                ? "bg-navy-foreground text-navy-deep hover:bg-navy-foreground/90 hover:text-navy-deep"
                : "bg-primary text-primary-foreground hover:bg-primary/90 hover:text-primary-foreground"
              : inverse
                ? "text-navy-foreground/70 hover:bg-navy-foreground/10 hover:text-navy-foreground"
                : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option === "ar" ? "العربية" : "English"}
        </Button>
      ))}
    </div>
  );
}