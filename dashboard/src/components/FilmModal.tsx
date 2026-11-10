import { useEffect } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { X } from "lucide-react";

const SRC = `${import.meta.env.BASE_URL}media/evolvra-demo.mp4`;
export const FILM_POSTER = `${import.meta.env.BASE_URL}media/evolvra-demo-poster.jpg`;

/** The 42-second film in a lightbox. The file is only fetched when the player opens (preload="none"). */
export default function FilmModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const reduce = useReducedMotion();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKey); };
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[95] grid place-items-center bg-black/80 p-3 backdrop-blur-sm md:p-8"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: reduce ? 0 : 0.2 }}
          onClick={onClose}>
          <motion.div role="dialog" aria-modal="true" aria-label="Evolvra film" onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-5xl overflow-hidden rounded-2xl border border-line-strong bg-black shadow-2xl"
            initial={reduce ? false : { scale: 0.96, y: 12 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.97, opacity: 0 }}
            transition={{ type: "spring", stiffness: 380, damping: 32 }}>
            <video src={SRC} poster={FILM_POSTER} controls autoPlay playsInline preload="none" className="block aspect-video w-full" />
            <button onClick={onClose} aria-label="Close film"
              className="absolute right-3 top-3 grid h-10 w-10 place-items-center rounded-full border border-white/20 bg-black/60 text-white transition-colors hover:bg-black/80">
              <X size={18} />
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
