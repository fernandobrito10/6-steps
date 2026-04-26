import { motion } from "framer-motion";
import type { SSEEvent } from "../types";
import { useT } from "../i18n";

interface Props {
  events: SSEEvent[];
  elapsed: number;
}

export default function ProgressView({ events, elapsed }: Props) {
  const t = useT();
  const expansions = events.filter((e): e is Extract<SSEEvent, { type: "expand" }> => e.type === "expand");
  const lastExpand = expansions[expansions.length - 1];
  const totalActorsTouched = expansions.reduce((acc, e) => acc + e.frontier_size, 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass rounded-2xl p-6 sm:p-8"
    >
      <div className="flex items-center gap-3">
        <Spinner />
        <div className="flex-1">
          <div className="text-sm uppercase tracking-[0.25em] text-zinc-500">{t.progressLabel}</div>
          <div className="mt-1 font-display text-2xl tracking-wide text-zinc-100">
            {phaseLabel(events, t)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs uppercase tracking-widest text-zinc-500">{t.elapsedLabel}</div>
          <div className="font-mono text-zinc-200">{elapsed.toFixed(1)}s</div>
        </div>
      </div>

      {lastExpand && (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label={t.sideLabel} value={lastExpand.side} />
          <Stat label={t.depthLabel} value={lastExpand.next_depth.toString()} />
          <Stat label={t.frontierLabel} value={lastExpand.frontier_size.toString()} />
          <Stat label={t.touchedLabel} value={totalActorsTouched.toString()} />
        </div>
      )}

      <div className="mt-6 max-h-44 overflow-y-auto rounded-lg border border-white/5 bg-black/30 p-3">
        <ul className="space-y-1 font-mono text-xs text-zinc-400">
          {events.slice(-12).map((e, i) => (
            <li key={i} className="flex gap-3">
              <span className="text-zinc-600">▸</span>
              <span>{describeEvent(e, t)}</span>
            </li>
          ))}
        </ul>
      </div>
    </motion.div>
  );
}

function phaseLabel(events: SSEEvent[], t: ReturnType<typeof useT>): string {
  const last = events[events.length - 1];
  if (!last) return t.phaseConnecting;
  switch (last.type) {
    case "start":
      return t.phaseConnecting;
    case "resolving":
      return t.phaseResolving;
    case "resolved":
      return t.phaseResolved;
    case "expand":
      return t.phaseExpand(last.side, last.next_depth);
    case "no_path":
      return t.phaseNoPath;
    case "error":
      return t.phaseError;
    case "result":
      return t.phaseResult;
  }
}

function describeEvent(e: SSEEvent, t: ReturnType<typeof useT>): string {
  switch (e.type) {
    case "start":
      return t.logStreamOpen;
    case "resolving":
      return t.logResolving;
    case "resolved":
      return t.logResolved(e.actor_a.name, e.actor_b.name);
    case "expand":
      return t.logExpand(e.side, e.next_depth, e.frontier_size);
    case "no_path":
      return t.logNoPath(e.max_depth);
    case "error":
      return t.logError(e.message);
    case "result":
      return t.logResult(e.hops);
  }
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/[0.03] p-3">
      <div className="text-[10px] uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="mt-0.5 font-display text-2xl text-zinc-100">{value}</div>
    </div>
  );
}

function Spinner() {
  return (
    <div className="relative h-10 w-10">
      <div className="absolute inset-0 animate-ping rounded-full bg-gold-500/20" />
      <div className="absolute inset-1 rounded-full border-2 border-gold-500 border-t-transparent animate-spin" />
    </div>
  );
}
