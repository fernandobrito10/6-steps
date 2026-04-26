import { createContext, useContext, useEffect, useState } from "react";

export type Lang = "en" | "pt";

const en = {
  tagline: "Six degrees · via TMDB",
  title1: "Connect",
  title2: "the Stars",
  description:
    "Pick any two actors. We'll trace the shortest movie-connection path between them using a bidirectional breadth-first search across the TMDB filmography graph.",

  from: "From",
  to: "To",
  placeholderA: "e.g. Tom Hanks",
  placeholderB: "e.g. Lupita Nyong'o",
  swap: "Swap",
  maxDepth: "Max depth",
  reset: "Reset",
  findConnection: "Find the connection",
  pickDifferent: "Pick two different actors.",

  errorTitle: "Error",
  noPathTitle: "No connection found",
  noPathBody: (depth: number, elapsed: number) =>
    `Tried up to depth ${depth} in ${elapsed.toFixed(1)}s. Try raising the max depth, or pick more popular actors.`,

  footer: "Powered by TMDB · bidirectional BFS · local cache",

  // Autocomplete
  searchingDots: "Searching…",
  popularity: "Popularity",
  tmdbId: "TMDB id",
  clear: "Clear",

  // Progress
  progressLabel: "Searching",
  elapsedLabel: "Elapsed",
  sideLabel: "Side",
  depthLabel: "Depth",
  frontierLabel: "Frontier",
  touchedLabel: "Total touched",

  phaseConnecting: "Connecting…",
  phaseResolving: "Looking up the actors…",
  phaseResolved: "Mapping the constellation…",
  phaseExpand: (side: string, depth: number) => `Exploring ${side}-side at depth ${depth}`,
  phaseNoPath: "No connection found.",
  phaseError: "Something went wrong.",
  phaseResult: "Found a path!",

  logStreamOpen: "stream open",
  logResolving: "resolving actors by id",
  logResolved: (a: string, b: string) => `resolved ${a} ↔ ${b}`,
  logExpand: (side: string, depth: number, n: number) =>
    `expand side ${side} → depth ${depth} (${n} actor${n === 1 ? "" : "s"})`,
  logNoPath: (depth: number) => `no path within depth ${depth}`,
  logError: (msg: string) => `error: ${msg}`,
  logResult: (hops: number) => `path of ${hops} hop${hops === 1 ? "" : "s"}`,

  // Result
  resultLabel: "Result",
  hopsLabel: (hops: number): string => (hops === 1 ? "Hop" : "Hops"),
  foundIn: "Found in",
  tagStart: "Start",
  tagEnd: "End",
  tagBridge: "Bridge",
  via: "via",
  noArt: "no art",
};

type Dict = typeof en;

const pt: Dict = {
  tagline: "Seis graus · via TMDB",
  title1: "Connect",
  title2: "the Stars",
  description:
    "Escolha dois atores quaisquer. Traçamos o menor caminho de conexão entre eles via filmes em comum, usando busca em largura bidirecional no grafo da TMDB.",

  from: "De",
  to: "Para",
  placeholderA: "ex: Wagner Moura",
  placeholderB: "ex: Fernanda Montenegro",
  swap: "Inverter",
  maxDepth: "Profundidade máx.",
  reset: "Resetar",
  findConnection: "Encontrar conexão",
  pickDifferent: "Escolha dois atores diferentes.",

  errorTitle: "Erro",
  noPathTitle: "Nenhuma conexão encontrada",
  noPathBody: (depth: number, elapsed: number) =>
    `Buscamos até profundidade ${depth} em ${elapsed.toFixed(1)}s. Tente aumentar a profundidade máxima, ou escolha atores mais populares.`,

  footer: "Powered by TMDB · BFS bidirecional · cache local",

  searchingDots: "Buscando…",
  popularity: "Popularidade",
  tmdbId: "TMDB id",
  clear: "Limpar",

  progressLabel: "Buscando",
  elapsedLabel: "Tempo",
  sideLabel: "Lado",
  depthLabel: "Profundidade",
  frontierLabel: "Fronteira",
  touchedLabel: "Total visitado",

  phaseConnecting: "Conectando…",
  phaseResolving: "Localizando os atores…",
  phaseResolved: "Mapeando a constelação…",
  phaseExpand: (side: string, depth: number) => `Explorando lado ${side} na profundidade ${depth}`,
  phaseNoPath: "Nenhuma conexão encontrada.",
  phaseError: "Algo deu errado.",
  phaseResult: "Caminho encontrado!",

  logStreamOpen: "stream aberto",
  logResolving: "resolvendo atores por id",
  logResolved: (a: string, b: string) => `resolvido ${a} ↔ ${b}`,
  logExpand: (side: string, depth: number, n: number) =>
    `expandir lado ${side} → profundidade ${depth} (${n} ator${n === 1 ? "" : "es"})`,
  logNoPath: (depth: number) => `sem caminho até a profundidade ${depth}`,
  logError: (msg: string) => `erro: ${msg}`,
  logResult: (hops: number) => `caminho de ${hops} salto${hops === 1 ? "" : "s"}`,

  resultLabel: "Resultado",
  hopsLabel: (hops: number) => (hops === 1 ? "Salto" : "Saltos"),
  foundIn: "Encontrado em",
  tagStart: "Início",
  tagEnd: "Fim",
  tagBridge: "Ponte",
  via: "via",
  noArt: "sem arte",
};

const translations: Record<Lang, Dict> = { en, pt };

const STORAGE_KEY = "cts_lang";

function detectLang(): Lang {
  if (typeof window === "undefined") return "en";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "en" || stored === "pt") return stored;
  if (typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("pt")) {
    return "pt";
  }
  return "en";
}

interface LangContextValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: Dict;
}

export const LangContext = createContext<LangContextValue | null>(null);

export function useLangState(): LangContextValue {
  const [lang, setLangState] = useState<Lang>(() => detectLang());

  useEffect(() => {
    document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";
    window.localStorage.setItem(STORAGE_KEY, lang);
  }, [lang]);

  return {
    lang,
    setLang: setLangState,
    t: translations[lang],
  };
}

export function useT(): Dict {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useT must be used inside <LangContext.Provider>");
  return ctx.t;
}

export function useLang(): { lang: Lang; setLang: (l: Lang) => void } {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used inside <LangContext.Provider>");
  return { lang: ctx.lang, setLang: ctx.setLang };
}
