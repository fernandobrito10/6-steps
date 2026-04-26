import { motion } from "framer-motion";
import type { Movie, Step } from "../types";
import { tmdbPoster, tmdbProfile } from "../api";
import { useLang, useT } from "../i18n";

function titleFor(movie: Pick<Movie, "title" | "title_pt">, lang: "en" | "pt"): string {
  if (lang === "pt" && movie.title_pt) return movie.title_pt;
  return movie.title;
}

interface Props {
  steps: Step[];
  hops: number;
  elapsed: number;
}

export default function PathView({ steps, hops, elapsed }: Props) {
  const t = useT();
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-6"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-[0.3em] text-zinc-500">{t.resultLabel}</div>
          <h2 className="font-display text-4xl text-gradient-gold">
            {hops} {t.hopsLabel(hops)}
          </h2>
        </div>
        <div className="text-right">
          <div className="text-xs uppercase tracking-widest text-zinc-500">{t.foundIn}</div>
          <div className="font-mono text-zinc-200">{elapsed.toFixed(1)}s</div>
        </div>
      </div>

      <ol className="relative flex flex-col items-center gap-3">
        {steps.map((step, idx) => (
          <motion.li
            key={`${step.actor.id}-${idx}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: idx * 0.18, ease: "easeOut" }}
            className="w-full max-w-md"
          >
            {step.via_movie && idx > 0 && (
              <MovieConnector movie={step.via_movie} delay={idx * 0.18 - 0.05} />
            )}
            <ActorCard step={step} isFirst={idx === 0} isLast={idx === steps.length - 1} />
          </motion.li>
        ))}
      </ol>
    </motion.div>
  );
}

function ActorCard({
  step,
  isFirst,
  isLast,
}: {
  step: Step;
  isFirst: boolean;
  isLast: boolean;
}) {
  const t = useT();
  const profile = tmdbProfile(step.actor.profile_path, "h632");
  const tag = isFirst ? t.tagStart : isLast ? t.tagEnd : t.tagBridge;
  return (
    <div className="glass-strong relative overflow-hidden rounded-2xl shadow-glow">
      <div className="flex items-center gap-4 p-4">
        <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-ink-700">
          {profile ? (
            <img src={profile} alt={step.actor.name} className="h-full w-full object-cover" loading="lazy" />
          ) : (
            <div className="flex h-full w-full items-center justify-center font-display text-3xl text-zinc-500">
              {step.actor.name.charAt(0)}
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-[0.25em] text-gold-400">{tag}</div>
          <div className="mt-1 truncate font-display text-2xl tracking-wide text-zinc-50">
            {step.actor.name}
          </div>
          <div className="text-xs text-zinc-500">
            {t.popularity} {step.actor.popularity.toFixed(1)} · {t.tmdbId} {step.actor.id}
          </div>
        </div>
      </div>
    </div>
  );
}

function MovieConnector({ movie, delay }: { movie: Movie; delay: number }) {
  const t = useT();
  const { lang } = useLang();
  const poster = tmdbPoster(movie.poster_path, "w342");
  const display = titleFor(movie, lang);
  return (
    <motion.div
      initial={{ opacity: 0, scaleY: 0.6 }}
      animate={{ opacity: 1, scaleY: 1 }}
      transition={{ duration: 0.4, delay }}
      className="relative my-3 flex items-center justify-center"
    >
      <div className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-gold-500/40 to-transparent" />
      <div className="glass relative z-10 flex items-center gap-3 rounded-lg px-3 py-2">
        <div className="relative h-12 w-9 shrink-0 overflow-hidden rounded bg-ink-700">
          {poster ? (
            <img src={poster} alt={display} className="h-full w-full object-cover" loading="lazy" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-[8px] text-zinc-500">
              {t.noArt}
            </div>
          )}
        </div>
        <div className="min-w-0">
          <div className="text-[9px] uppercase tracking-widest text-zinc-500">{t.via}</div>
          <div className="truncate text-sm font-medium text-zinc-100" title={display}>
            {display}
          </div>
          {movie.year && <div className="text-[10px] text-zinc-500">{movie.year}</div>}
        </div>
      </div>
    </motion.div>
  );
}
