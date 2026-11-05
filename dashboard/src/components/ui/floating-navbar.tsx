/**
 * Floating Navbar after Aceternity UI (ui.aceternity.com/components/floating-navbar).
 * Kept: the pill layout, hide-on-scroll-down / show-on-scroll-up behaviour, the y:-100 slide with a
 * 0.2 s transition, icons-only on small screens, and the gradient hairline under the action button.
 * Changed: scroll is measured in pixels (scrollY > 120) rather than page progress (< 5%), so it
 * behaves the same on short and very long pages; colors use this site's tokens; links use the shared gliding
 * hover pill (nav-links.tsx) and mark the current page; the action button opens search instead of a login.
 */
import { AnimatePresence, motion, useMotionValueEvent, useReducedMotion, useScroll } from "motion/react";
import { useState, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import { NavLinks, type NavLink } from "./nav-links";

export type NavItem = NavLink;

export const FloatingNav = ({ navItems, brand, action, className }: {
  navItems: NavItem[]; brand?: ReactNode; action?: ReactNode; className?: string;
}) => {
  const { scrollY } = useScroll();
  const reduce = useReducedMotion();
  const [visible, setVisible] = useState(false);

  useMotionValueEvent(scrollY, "change", (current) => {
    const previous = scrollY.getPrevious() ?? 0;
    if (current < 120) setVisible(false);
    else setVisible(current - previous < 0);
  });

  return (
    <AnimatePresence mode="wait">
      <motion.div
        initial={{ opacity: 1, y: -100 }}
        animate={{ y: visible ? 0 : -100, opacity: visible ? 1 : 0 }}
        transition={{ duration: reduce ? 0 : 0.2 }}
        className={cn(
          "fixed inset-x-0 top-6 z-[60] mx-auto max-w-fit items-center justify-center gap-1 rounded-full border border-line bg-card-solid/85 py-2 pl-4 pr-2 shadow-[0px_2px_3px_-1px_rgba(0,0,0,0.1),0px_1px_0px_0px_rgba(25,28,33,0.02),0px_0px_0px_1px_rgba(25,28,33,0.08)] backdrop-blur-xl",
          className ?? "flex",
        )}>
        {brand && <span className="mr-2 flex items-center">{brand}</span>}
        <NavLinks id="floating" items={navItems} compact />
        {action}
      </motion.div>
    </AnimatePresence>
  );
};

/** The source's bordered action button with the gradient hairline along its bottom edge. */
export function NavAction({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return (
    <button onClick={onClick} className="relative ml-1 rounded-full border border-line-strong px-4 py-2 text-sm font-medium text-ink transition-[background-color,box-shadow] duration-200 hover:bg-card-hover hover:shadow-[0_0_0_1px_var(--glow),0_6px_20px_-8px_var(--glow)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">
      <span className="inline-flex items-center gap-1.5">{children}</span>
      <span className="absolute inset-x-0 -bottom-px mx-auto h-px w-1/2 bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />
    </button>
  );
}
