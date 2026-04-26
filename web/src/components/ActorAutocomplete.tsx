import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Actor } from "../types";
import { searchActors, tmdbProfile } from "../api";
import { useT } from "../i18n";

interface Props {
  label: string;
  placeholder: string;
  selected: Actor | null;
  onSelect: (actor: Actor | null) => void;
  accent: "left" | "right";
}

export default function ActorAutocomplete({ label, placeholder, selected, onSelect, accent }: Props) {
  const t = useT();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Actor[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (selected) return;
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const ctrl = new AbortController();
    const handle = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await searchActors(query, ctrl.signal);
        setResults(res);
        setHighlight(0);
      } catch {
        // aborted or network error; ignore
      } finally {
        setLoading(false);
      }
    }, 220);
    return () => {
      clearTimeout(handle);
      ctrl.abort();
    };
  }, [query, selected]);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function pick(actor: Actor) {
    onSelect(actor);
    setOpen(false);
    setQuery("");
  }

  function clear() {
    onSelect(null);
    setQuery("");
    setResults([]);
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[highlight]) pick(results[highlight]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const accentRing = accent === "left" ? "focus-within:ring-gold-500/40" : "focus-within:ring-purple-400/30";
  const accentDot = accent === "left" ? "bg-gold-500" : "bg-purple-400";

  return (
    <div className="relative" ref={containerRef}>
      <label className="flex items-center gap-2 mb-2 text-xs font-medium uppercase tracking-[0.2em] text-zinc-400">
        <span className={`inline-block h-1.5 w-1.5 rounded-full ${accentDot}`} />
        {label}
      </label>

      {selected ? (
        <SelectedChip actor={selected} onClear={clear} clearLabel={t.clear} />
      ) : (
        <div
          className={`glass rounded-xl px-4 py-3 transition focus-within:bg-ink-800/60 focus-within:ring-2 ${accentRing}`}
        >
          <input
            ref={inputRef}
            type="text"
            placeholder={placeholder}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={onKeyDown}
            className="w-full bg-transparent text-lg text-zinc-100 placeholder:text-zinc-500 outline-none"
            autoComplete="off"
            spellCheck={false}
          />
        </div>
      )}

      <AnimatePresence>
        {!selected && open && (results.length > 0 || loading) && (
          <motion.ul
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            className="glass-strong absolute z-20 mt-2 w-full overflow-hidden rounded-xl shadow-2xl"
          >
            {loading && results.length === 0 && (
              <li className="px-4 py-3 text-sm text-zinc-400">{t.searchingDots}</li>
            )}
            {results.map((actor, idx) => (
              <li
                key={actor.id}
                onMouseEnter={() => setHighlight(idx)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(actor);
                }}
                className={`flex cursor-pointer items-center gap-3 px-3 py-2 transition ${
                  idx === highlight ? "bg-white/[0.06]" : "hover:bg-white/[0.04]"
                }`}
              >
                <Avatar src={tmdbProfile(actor.profile_path, "w185")} name={actor.name} size={40} />
                <div className="flex-1 min-w-0">
                  <div className="truncate text-zinc-100">{actor.name}</div>
                  <div className="text-xs text-zinc-500">
                    {t.popularity} {actor.popularity.toFixed(1)}
                  </div>
                </div>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}

function SelectedChip({
  actor,
  onClear,
  clearLabel,
}: {
  actor: Actor;
  onClear: () => void;
  clearLabel: string;
}) {
  return (
    <div className="glass-strong flex items-center gap-3 rounded-xl px-3 py-3 shadow-glow">
      <Avatar src={tmdbProfile(actor.profile_path, "w185")} name={actor.name} size={48} />
      <div className="flex-1 min-w-0">
        <div className="truncate font-medium text-zinc-100">{actor.name}</div>
        <div className="text-xs text-zinc-500">TMDB id {actor.id}</div>
      </div>
      <button
        type="button"
        onClick={onClear}
        className="rounded-full p-2 text-zinc-400 transition hover:bg-white/5 hover:text-zinc-100"
        aria-label={clearLabel}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

function Avatar({ src, name, size }: { src: string | null; name: string; size: number }) {
  const initial = name.charAt(0).toUpperCase();
  return (
    <div
      className="flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-ink-700 text-zinc-300"
      style={{ width: size, height: size }}
    >
      {src ? (
        <img src={src} alt={name} className="h-full w-full object-cover" loading="lazy" />
      ) : (
        <span className="font-semibold">{initial}</span>
      )}
    </div>
  );
}
