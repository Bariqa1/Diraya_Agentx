import { cn } from "@/lib/utils";
import type { Locale } from "@/lib/locale";

export type LogoVariant = "navy" | "white" | "auto";

export function DirayaMark({
  className,
  variant = "navy",
  alt = "شعار دِراية",
}: {
  className?: string;
  variant?: LogoVariant;
  alt?: string;
}) {
  if (variant === "white") {
    return (
      <span
        aria-hidden="true"
        className={cn("flex size-10 shrink-0 items-center justify-center p-0.5", className)}
      >
        <img
          src="/diraya-logo-white.png"
          alt={alt}
          className="size-full object-contain drop-shadow-sm"
        />
      </span>
    );
  }

  if (variant === "navy") {
    return (
      <span
        aria-hidden="true"
        className={cn("flex size-10 shrink-0 items-center justify-center p-0.5", className)}
      >
        <img
          src="/diraya-logo-navy.png"
          alt={alt}
          className="size-full object-contain"
        />
      </span>
    );
  }

  // "auto": adapts to dark/light mode
  return (
    <span
      aria-hidden="true"
      className={cn("flex size-10 shrink-0 items-center justify-center p-0.5", className)}
    >
      <img
        src="/diraya-logo-navy.png"
        alt={alt}
        className="size-full object-contain dark:hidden"
      />
      <img
        src="/diraya-logo-white.png"
        alt={alt}
        className="hidden size-full object-contain dark:block drop-shadow-sm"
      />
    </span>
  );
}

export function DirayaWordmark({
  locale,
  compact = false,
  arabicFont = "font-arabic",
  variant = "navy",
  className,
}: {
  locale: Locale;
  compact?: boolean;
  arabicFont?: string;
  variant?: LogoVariant;
  className?: string;
}) {
  const arabic = locale === "ar";

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <DirayaMark variant={variant} className="size-11" />
      <div className="leading-none">
        <p className={cn("font-display text-xl font-bold tracking-tight", arabic && arabicFont)}>
          {arabic ? "دِراية" : "DIRAYA"}
        </p>
        {!compact ? (
          <p className={cn("mt-2 text-[11px] font-medium text-current/60", !arabic && "uppercase tracking-[0.16em]")}>
            {arabic ? "نظام ذكي للسلامة الصناعية" : "Intelligent safety awareness"}
          </p>
        ) : null}
      </div>
    </div>
  );
}