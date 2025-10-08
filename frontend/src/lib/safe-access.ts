/**
 * Utilitaires pour accéder aux propriétés d'objets de manière sécurisée
 * Évite les erreurs "Cannot read properties of null/undefined"
 */

/**
 * Accède à une propriété d'objet de manière sécurisée
 * @param obj - L'objet à interroger
 * @param path - Le chemin vers la propriété (ex: "company_name" ou "subsidiaries_details.length")
 * @param defaultValue - Valeur par défaut si la propriété n'existe pas
 * @returns La valeur de la propriété ou la valeur par défaut
 */
export function safeGet<
  T = unknown,
  O extends Record<string, unknown> = Record<string, unknown>
>(
  obj: O | null | undefined,
  path: string,
  defaultValue: T | null = null
): T | null {
  if (!obj || typeof obj !== "object") {
    return defaultValue;
  }

  const keys = path.split(".");
  let current: unknown = obj;

  for (const key of keys) {
    if (
      current === null ||
      current === undefined ||
      typeof current !== "object" ||
      !(key in current)
    ) {
      return defaultValue;
    }
    current = (current as Record<string, unknown>)[key];
  }

  return current !== undefined ? (current as T) : defaultValue;
}

/**
 * Version type-safe de safeGet qui garantit que l'objet n'est pas null
 */
export function safeGetNonNull<
  T = unknown,
  O extends Record<string, unknown> = Record<string, unknown>
>(
  obj: O | null | undefined,
  path: string,
  defaultValue: T | null = null
): T | null {
  if (!obj || typeof obj !== "object") {
    return defaultValue;
  }

  const keys = path.split(".");
  let current: unknown = obj;

  for (const key of keys) {
    if (
      current === null ||
      current === undefined ||
      typeof current !== "object" ||
      !(key in current)
    ) {
      return defaultValue;
    }
    current = (current as Record<string, unknown>)[key];
  }

  return current !== undefined ? (current as T) : defaultValue;
}

/**
 * Vérifie si un objet a une propriété de manière sécurisée
 * @param obj - L'objet à vérifier
 * @param path - Le chemin vers la propriété
 * @returns true si la propriété existe et n'est pas null/undefined
 */
export function safeHas<O extends Record<string, unknown>>(
  obj: O | null | undefined,
  path: string
): boolean {
  return safeGet(obj, path) !== null;
}

/**
 * Retourne un objet companyData sécurisé avec des valeurs par défaut
 * @param companyData - Les données d'entreprise
 * @returns Un objet avec des valeurs par défaut sécurisées
 */
export function safeCompanyData(
  companyData: Record<string, unknown> | null | undefined
) {
  if (!companyData || typeof companyData !== "object") {
    return {
      company_name: "",
      subsidiaries_details: [],
      headquarters_address: "",
      headquarters_city: "",
      headquarters_country: "",
      parent_company: "",
      sector: "",
      activities: [],
      revenue_recent: "",
      employees: "",
      founded_year: null,
      sources: [],
      methodology_notes: [],
      extraction_metadata: null,
      extraction_date: "",
    };
  }

  return {
    company_name: safeGet<string>(companyData, "company_name", "") ?? "",
    subsidiaries_details:
      safeGet<unknown[]>(companyData, "subsidiaries_details", []) ?? [],
    headquarters_address:
      safeGet<string>(companyData, "headquarters_address", "") ?? "",
    headquarters_city:
      safeGet<string | null>(companyData, "headquarters_city", "") ?? "",
    headquarters_country:
      safeGet<string | null>(companyData, "headquarters_country", "") ?? "",
    parent_company:
      safeGet<string | null>(companyData, "parent_company", "") ?? "",
    sector: safeGet<string>(companyData, "sector", "") ?? "",
    activities: safeGet<string[]>(companyData, "activities", []) ?? [],
    revenue_recent:
      safeGet<string | null>(companyData, "revenue_recent", "") ?? "",
    employees:
      safeGet<string | null>(companyData, "employees", "") ?? "",
    founded_year:
      safeGet<number | null>(companyData, "founded_year", null) ?? null,
    sources: safeGet<unknown[]>(companyData, "sources", []) ?? [],
    methodology_notes:
      safeGet<string[] | null>(companyData, "methodology_notes", []) ?? [],
    extraction_metadata:
      safeGet<unknown | null>(companyData, "extraction_metadata", null) ?? null,
    extraction_date: safeGet<string | null>(companyData, "extraction_date", "") ?? "",
  };
}
