import { motion } from "framer-motion";
import { useLang } from "../i18n";
import type { Lang } from "../i18n";

const OPTIONS: { value: Lang; label: string }[] = [
  { value: "en", label: "EN" },
  { value: "pt", label: "PT-BR" },
];

export default function LanguageToggle() {
  const { lang, setLang } = useLang();

  return (
    <div
      role="radiogroup"
      aria-label="Language"
      className="glass relative inline-flex items-center rounded-full p-1 text-xs font-medium"
    >
      {OPTIONS.map((opt) => {
        const active = lang === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => setLang(opt.value)}
            className={`relative z-10 px-3.5 py-1.5 transition-colors ${
              active ? "text-ink-950" : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {active && (
              <motion.span
                layoutId="lang-pill"
                className="absolute inset-0 -z-10 rounded-full bg-gradient-to-r from-gold-500 to-gold-400 shadow-glow"
                transition={{ type: "spring", stiffness: 380, damping: 32 }}
              />
            )}
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
