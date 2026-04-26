import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ActorAutocomplete from "./components/ActorAutocomplete";
import ProgressView from "./components/ProgressView";
import PathView from "./components/PathView";
import LanguageToggle from "./components/LanguageToggle";
import { streamConnect } from "./api";
import { useT } from "./i18n";
import type { Actor, SSEEvent, Step } from "./types";

type Phase =
  | { kind: "idle" }
  | { kind: "running"; events: SSEEvent[]; elapsed: number }
  | { kind: "done"; steps: Step[]; hops: number; elapsed: number }
  | { kind: "no_path"; maxDepth: number; elapsed: number }
  | { kind: "error"; message: string };

export default function App() {
  const t = useT();
  const [actorA, setActorA] = useState<Actor | null>(null);
  const [actorB, setActorB] = useState<Actor | null>(null);
  const [maxDepth, setMaxDepth] = useState(6);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  const cancelRef = useRef<(() => void) | null>(null);
  const startRef = useRef<number>(0);
  const tickRef = useRef<number | null>(null);

  useEffect(() => {
    if (phase.kind !== "running") {
      if (tickRef.current !== null) {
        window.clearInterval(tickRef.current);
        tickRef.current = null;
      }
      return;
    }
    if (tickRef.current !== null) return;
    tickRef.current = window.setInterval(() => {
      setPhase((p) => {
        if (p.kind !== "running") return p;
        return { ...p, elapsed: (performance.now() - startRef.current) / 1000 };
      });
    }, 100);
    return () => {
      if (tickRef.current !== null) {
        window.clearInterval(tickRef.current);
        tickRef.current = null;
      }
    };
  }, [phase.kind]);

  useEffect(() => () => cancelRef.current?.(), []);

  function start() {
    if (!actorA || !actorB) return;
    if (actorA.id === actorB.id) {
      setPhase({ kind: "error", message: t.pickDifferent });
      return;
    }
    cancelRef.current?.();
    startRef.current = performance.now();
    setPhase({ kind: "running", events: [], elapsed: 0 });

    cancelRef.current = streamConnect(actorA.id, actorB.id, maxDepth, {
      onEvent: (event) => {
        setPhase((current) => {
          const elapsed = (performance.now() - startRef.current) / 1000;
          if (event.type === "result") {
            return { kind: "done", steps: event.path, hops: event.hops, elapsed };
          }
          if (event.type === "no_path") {
            return { kind: "no_path", maxDepth: event.max_depth, elapsed };
          }
          if (event.type === "error") {
            return { kind: "error", message: event.message };
          }
          if (current.kind !== "running") return current;
          return { ...current, events: [...current.events, event], elapsed };
        });
      },
      onError: (err) => {
        setPhase((current) => {
          if (current.kind === "done" || current.kind === "no_path" || current.kind === "error") {
            return current;
          }
          return { kind: "error", message: err.message };
        });
      },
    });
  }

  function reset() {
    cancelRef.current?.();
    setPhase({ kind: "idle" });
  }

  function swap() {
    setActorA(actorB);
    setActorB(actorA);
  }

  const canSearch = actorA !== null && actorB !== null && phase.kind !== "running";

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col px-5 py-10 sm:px-8 sm:py-16">
      <div className="mb-6 flex justify-end">
        <LanguageToggle />
      </div>

      <Header />

      <section className="glass mt-10 rounded-3xl p-6 sm:p-10 shadow-glow">
        <div className="grid gap-5 sm:grid-cols-[1fr_auto_1fr] sm:items-end">
          <ActorAutocomplete
            label={t.from}
            placeholder={t.placeholderA}
            selected={actorA}
            onSelect={setActorA}
            accent="left"
          />
          <button
            type="button"
            onClick={swap}
            disabled={phase.kind === "running"}
            className="mx-auto mb-1 hidden h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-zinc-400 transition hover:bg-white/[0.08] hover:text-zinc-100 disabled:opacity-30 sm:flex"
            aria-label={t.swap}
            title={t.swap}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M7 16h12M7 16l4-4M7 16l4 4M17 8H5M17 8l-4-4M17 8l-4 4" />
            </svg>
          </button>
          <ActorAutocomplete
            label={t.to}
            placeholder={t.placeholderB}
            selected={actorB}
            onSelect={setActorB}
            accent="right"
          />
        </div>

        <div className="mt-7 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-sm text-zinc-400">
            <label htmlFor="depth" className="text-xs uppercase tracking-widest text-zinc-500">
              {t.maxDepth}
            </label>
            <input
              id="depth"
              type="range"
              min={1}
              max={8}
              value={maxDepth}
              onChange={(e) => setMaxDepth(parseInt(e.target.value, 10))}
              className="accent-gold-500"
              disabled={phase.kind === "running"}
            />
            <span className="font-mono text-zinc-300">{maxDepth}</span>
          </div>

          <div className="flex gap-2">
            {phase.kind !== "idle" && (
              <button
                type="button"
                onClick={reset}
                className="rounded-full border border-white/10 px-5 py-2.5 text-sm text-zinc-300 transition hover:bg-white/[0.06]"
              >
                {t.reset}
              </button>
            )}
            <button
              type="button"
              onClick={start}
              disabled={!canSearch}
              className="group relative overflow-hidden rounded-full bg-gradient-to-r from-gold-500 to-gold-400 px-6 py-2.5 font-semibold text-ink-950 shadow-glowStrong transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-30"
            >
              <span className="relative">{t.findConnection}</span>
            </button>
          </div>
        </div>
      </section>

      <section className="mt-10">
        <AnimatePresence mode="wait">
          {phase.kind === "running" && (
            <motion.div key="run" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <ProgressView events={phase.events} elapsed={phase.elapsed} />
            </motion.div>
          )}
          {phase.kind === "done" && (
            <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <PathView steps={phase.steps} hops={phase.hops} elapsed={phase.elapsed} />
            </motion.div>
          )}
          {phase.kind === "no_path" && (
            <motion.div
              key="nopath"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass rounded-2xl p-8 text-center"
            >
              <div className="font-display text-3xl text-zinc-200">{t.noPathTitle}</div>
              <p className="mt-2 text-zinc-500">{t.noPathBody(phase.maxDepth, phase.elapsed)}</p>
            </motion.div>
          )}
          {phase.kind === "error" && (
            <motion.div
              key="err"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl border border-red-500/30 bg-red-950/30 p-6 text-red-200"
            >
              <div className="font-medium">{t.errorTitle}</div>
              <p className="mt-1 text-sm text-red-300/80">{phase.message}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      <Footer />
    </div>
  );
}

function Header() {
  const t = useT();
  return (
    <header className="text-center sm:text-left">
      <div className="text-xs font-medium uppercase tracking-[0.4em] text-gold-400">
        {t.tagline}
      </div>
      <h1 className="mt-3 font-display text-6xl tracking-wider sm:text-7xl">
        <span className="text-gradient-gold">{t.title1}</span>{" "}
        <span className="text-zinc-100">{t.title2}</span>
      </h1>
      <p className="mt-3 max-w-xl text-zinc-400">{t.description}</p>
    </header>
  );
}

function Footer() {
  const t = useT();
  return (
    <footer className="mt-16 flex items-center justify-between text-xs text-zinc-600">
      <span>{t.footer}</span>
      <span className="font-mono">v0.1</span>
    </footer>
  );
}
