/**
 * Floating Dock, ported from Aceternity UI (ui.aceternity.com/components/floating-dock).
 * Kept from the source: the magnification maths (distance -> [40, 80, 40] px), the spring
 * (mass 0.1, stiffness 150, damping 12), the tooltip motion, and the mobile fan-out.
 * Changed for this project (see the report in the commit):
 *  - items may carry `onClick` and `active` (for Search/Theme and the current page dot);
 *  - colors use this site's tokens plus a glass border so it sits on the dark backdrop;
 *  - pointer position uses clientX (the dock is position: fixed, so viewport coordinates match);
 *  - reduced motion: magnification is disabled (icons stay at rest size), tooltips still appear.
 */
import { cn } from "../../lib/utils";
import { PanelBottomOpen } from "lucide-react";
import {
  AnimatePresence, motion, useMotionValue, useReducedMotion, useSpring, useTransform, type MotionValue,
} from "motion/react";
import { useRef, useState } from "react";

export type DockItem = { title: string; icon: React.ReactNode; href?: string; onClick?: () => void; active?: boolean };

export const FloatingDock = ({ items, desktopClassName, mobileClassName }: {
  items: DockItem[]; desktopClassName?: string; mobileClassName?: string;
}) => (
  <>
    <FloatingDockDesktop items={items} className={desktopClassName} />
    <FloatingDockMobile items={items} className={mobileClassName} />
  </>
);

function ItemLink({ item, className, children }: { item: DockItem; className?: string; children: React.ReactNode }) {
  if (item.onClick) return <button type="button" onClick={item.onClick} aria-label={item.title} className={className}>{children}</button>;
  return <a href={item.href} aria-label={item.title} aria-current={item.active ? "page" : undefined} className={className}>{children}</a>;
}

const FloatingDockMobile = ({ items, className }: { items: DockItem[]; className?: string }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className={cn("relative block md:hidden", className)}>
      <AnimatePresence>
        {open && (
          <motion.div layoutId="nav" className="absolute inset-x-0 bottom-full mb-2 flex flex-col gap-2">
            {items.map((item, idx) => (
              <motion.div key={item.title}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10, transition: { delay: idx * 0.05 } }}
                transition={{ delay: (items.length - 1 - idx) * 0.05 }}>
                <ItemLink item={item}
                  className={cn("flex h-10 w-10 items-center justify-center rounded-full border border-line bg-gray-50 shadow-lg dark:bg-neutral-900",
                    item.active && "border-line-strong")}>
                  <div className="h-4 w-4" onClick={() => setOpen(false)}>{item.icon}</div>
                </ItemLink>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
      <button onClick={() => setOpen(!open)} aria-label="Menu" aria-expanded={open}
        className="flex h-10 w-10 items-center justify-center rounded-full border border-line bg-gray-50 shadow-lg dark:bg-neutral-800">
        <PanelBottomOpen className="h-5 w-5 text-neutral-500 dark:text-neutral-400" />
      </button>
    </div>
  );
};

const FloatingDockDesktop = ({ items, className }: { items: DockItem[]; className?: string }) => {
  const mouseX = useMotionValue(Infinity);
  return (
    <motion.div
      onMouseMove={(e) => mouseX.set(e.clientX)}
      onMouseLeave={() => mouseX.set(Infinity)}
      className={cn(
        "mx-auto hidden h-16 items-end gap-4 rounded-2xl border border-line bg-gray-50/80 px-4 pb-3 shadow-2xl backdrop-blur-xl md:flex dark:bg-neutral-900/80",
        className,
      )}>
      {items.map((item) => <IconContainer mouseX={mouseX} key={item.title} item={item} />)}
    </motion.div>
  );
};

function IconContainer({ mouseX, item }: { mouseX: MotionValue; item: DockItem }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();

  const distance = useTransform(mouseX, (val) => {
    const bounds = ref.current?.getBoundingClientRect() ?? { x: 0, width: 0 };
    return val - bounds.x - bounds.width / 2;
  });

  const widthTransform = useTransform(distance, [-150, 0, 150], reduce ? [40, 40, 40] : [40, 80, 40]);
  const heightTransform = useTransform(distance, [-150, 0, 150], reduce ? [40, 40, 40] : [40, 80, 40]);
  const widthTransformIcon = useTransform(distance, [-150, 0, 150], reduce ? [20, 20, 20] : [20, 40, 20]);
  const heightTransformIcon = useTransform(distance, [-150, 0, 150], reduce ? [20, 20, 20] : [20, 40, 20]);

  const width = useSpring(widthTransform, { mass: 0.1, stiffness: 150, damping: 12 });
  const height = useSpring(heightTransform, { mass: 0.1, stiffness: 150, damping: 12 });
  const widthIcon = useSpring(widthTransformIcon, { mass: 0.1, stiffness: 150, damping: 12 });
  const heightIcon = useSpring(heightTransformIcon, { mass: 0.1, stiffness: 150, damping: 12 });

  const [hovered, setHovered] = useState(false);

  return (
    <ItemLink item={item} className="relative">
      <motion.div
        ref={ref}
        style={{ width, height }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className={cn("relative flex aspect-square items-center justify-center rounded-full bg-gray-200 dark:bg-neutral-800",
          item.active && "ring-1 ring-line-strong")}>
        <AnimatePresence>
          {hovered && (
            <motion.div
              initial={{ opacity: 0, y: 10, x: "-50%" }}
              animate={{ opacity: 1, y: 0, x: "-50%" }}
              exit={{ opacity: 0, y: 2, x: "-50%" }}
              className="absolute -top-8 left-1/2 w-fit rounded-md border border-gray-200 bg-gray-100 px-2 py-0.5 text-xs whitespace-pre text-neutral-700 dark:border-neutral-900 dark:bg-neutral-800 dark:text-white">
              {item.title}
            </motion.div>
          )}
        </AnimatePresence>
        <motion.div style={{ width: widthIcon, height: heightIcon }} className="flex items-center justify-center">
          {item.icon}
        </motion.div>
      </motion.div>
      {item.active && <span className="absolute -bottom-2 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-ink" />}
    </ItemLink>
  );
}
