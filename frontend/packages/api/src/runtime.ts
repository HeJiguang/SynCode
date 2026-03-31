import type { CodeLanguage, Difficulty } from "./contracts";

export const DEFAULT_BACKEND_BASE_URL = "http://localhost:19090";

export function resolveBackendBaseUrl(
  baseUrl = process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? process.env.SYNCODE_BACKEND_BASE_URL ?? DEFAULT_BACKEND_BASE_URL
) {
  return baseUrl.replace(/\/+$/, "");
}

export function resolveJudgeWebSocketUrl(baseUrl = resolveBackendBaseUrl()) {
  const wsBase = baseUrl.replace(/^http:\/\//, "ws://").replace(/^https:\/\//, "wss://");
  return `${wsBase}/friend/ws/judge/result`;
}

export function normalizeDifficulty(difficulty?: number | string | null): Difficulty {
  if (difficulty === 1 || difficulty === "1" || difficulty === "Easy") return "Easy";
  if (difficulty === 2 || difficulty === "2" || difficulty === "Medium") return "Medium";
  if (difficulty === 3 || difficulty === "3" || difficulty === "Hard") return "Hard";
  return "Medium";
}

export function isJudgeLanguageSupported(language: CodeLanguage) {
  return language === "java";
}

export function programTypeFromLanguage(language: CodeLanguage) {
  if (language === "java") return 0;
  if (language === "cpp") return 1;
  if (language === "go") return 2;
  throw new Error(`Unsupported judge language: ${language}`);
}
