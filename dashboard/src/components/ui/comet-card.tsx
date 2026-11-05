/**
 * Comet Card, ported from Aceternity UI (ui.aceternity.com/components/comet-card).
 * Copied as-is: the spring-driven tilt (rotateX/Y from pointer position), the counter-translate,
 * the hover lift (scale 1.05, z 50, 0.2 s), the layered shadow, and the overlay glare.
 * Changed: `cn` import path; with prefers-reduced-motion the tilt, translate and lift are off
 * (the source declares none, so this follows the site-wide rule), the glare still tracks.
 * Added `glare` prop: "always" is the source behaviour (default); "hover" fades the glare in only
 * while hovered, for grids of dark cards where a resting glare washes every card gray.
 */
import React, { useRef } from "react";
import { motion, useMotionTemplate, useMotionValue, useReducedMotion, useSpring, useTransform } from "motion/react";
import { cn } from "../../lib/utils";

export const CometCard = ({ rotateDepth = 17.5, translateDepth = 20, className, children, glare = "always", glareOpacity = 0.6 }: {
  rotateDepth?: number; translateDepth?: number; className?: string; children: React.ReactNode;
  glare?: "always" | "hover"; glareOpacity?: number;
}) => {
  const [hovered, setHovered] = React.useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const rd = reduce ? 0 : rotateDepth, td = reduce ? 0 : translateDepth;

  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const mouseXSpring = useSpring(x);
  const mouseYSpring = useSpring(y);

  const rotateX = useTransform(mouseYSpring, [-0.5, 0.5], [`-${rd}deg`, `${rd}deg`]);
  const rotateY = useTransform(mouseXSpring, [-0.5, 0.5], [`${rd}deg`, `-${rd}deg`]);
  const translateX = useTransform(mouseXSpring, [-0.5, 0.5], [`-${td}px`, `${td}px`]);
  const translateY = useTransform(mouseYSpring, [-0.5, 0.5], [`${td}px`, `-${td}px`]);

  const glareX = useTransform(mouseXSpring, [-0.5, 0.5], [0, 100]);
  const glareY = useTransform(mouseYSpring, [-0.5, 0.5], [0, 100]);
  const glareBackground = useMotionTemplate`radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255, 255, 255, 0.9) 10%, rgba(255, 255, 255, 0.75) 20%, rgba(255, 255, 255, 0) 80%)`;

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    x.set((e.clientX - rect.left) / rect.width - 0.5);
    y.set((e.clientY - rect.top) / rect.height - 0.5);
  };
  const handleMouseLeave = () => { x.set(0); y.set(0); setHovered(false); };

  return (
    <div className={cn("perspective-distant transform-3d", className)}>
      <motion.div
        ref={ref}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={handleMouseLeave}
        style={{
          rotateX, rotateY, translateX, translateY,
          boxShadow: "rgba(0, 0, 0, 0.01) 0px 520px 146px 0px, rgba(0, 0, 0, 0.04) 0px 333px 133px 0px, rgba(0, 0, 0, 0.26) 0px 83px 83px 0px, rgba(0, 0, 0, 0.29) 0px 21px 46px 0px",
        }}
        initial={{ scale: 1, z: 0 }}
        whileHover={reduce ? undefined : { scale: 1.05, z: 50, transition: { duration: 0.2 } }}
        className="relative rounded-2xl">
        {children}
        <motion.div
          className="pointer-events-none absolute inset-0 z-50 h-full w-full rounded-[16px] mix-blend-overlay"
          style={{ background: glareBackground }}
          animate={{ opacity: glare === "always" || hovered ? glareOpacity : 0 }}
          transition={{ duration: 0.2 }} />
      </motion.div>
    </div>
  );
};
