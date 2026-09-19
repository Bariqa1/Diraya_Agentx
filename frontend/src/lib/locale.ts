export type Locale = "ar" | "en";

export function parseLocale(value: unknown): Locale {
  return value === "en" ? "en" : "ar";
}

export function localeSearch(search: Record<string, unknown>) {
  return { lang: parseLocale(search["lang"]) };
}

export function isArabic(locale: Locale) {
  return locale === "ar";
}