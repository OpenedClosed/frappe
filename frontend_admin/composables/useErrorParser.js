import { toValue } from "vue";

/**
 * Centralised helpers for extracting readable messages from
 * FastAPI / Django‐style error payloads.
 *
 * ▸ `pickError(raw) → string`
 * ▸ `parseAxiosError(err, target)`  – fills a reactive `target`
 */
export function useErrorParser({ fallbackLang = "en" } = {}) {
  const { currentLanguage } = useLanguageState();

  /**
   * Normalise a single backend error entry.
   *  • "message"                         → "message"
   *  • ["too short", "must be email"]    → "too short"
   *  • { en:"...", ru:"..." }            → by lang/fallback
   */
  function pickError(raw) {
    if (!raw) return "";

    if (typeof raw === "string") return raw;               // plain string
    if (Array.isArray(raw)) return raw.find(Boolean) || ""; // first non-empty
    if (typeof raw === "object")
      return (
        raw[toValue(currentLanguage)] ??
        raw[fallbackLang] ??
        Object.values(raw).find(Boolean) ??
        ""
      );

    return "";
  }

  /**
   * Copy messages from an axios error into a reactive target object
   * (keys in `target` define which fields you care about).
   *
   * @param {any}   axiosError – error object from axios
   * @param {object} target    – reactive form-error object, e.g.
   *                             { phone:"", email:"", general:"" }
   */
  function parseAxiosError(axiosError, target) {
    // clear previous state
    Object.keys(target).forEach((k) => (target[k] = ""));

    const data = axiosError?.response?.data || {};

    /* 1️⃣ Field-level validation errors */
    if (data.errors && typeof data.errors === "object") {
      Object.keys(target).forEach((field) => {
        if (field in data.errors) target[field] = pickError(data.errors[field]);
      });
    }

    /* 2️⃣ Non-field / general errors */
    if (data.detail) {
      // detail might be string OR { field: msg }
      if (typeof data.detail === "object") {
        Object.keys(target).forEach((field) => {
          if (!target[field] && field in data.detail)
            target[field] = pickError(data.detail[field]);
        });
      }

      // if nothing caught yet – drop into `general`
      if (!Object.values(target).some(Boolean) && "general" in target)
        target.general = pickError(data.detail);
    }
  }

  return { pickError, parseAxiosError };
}
