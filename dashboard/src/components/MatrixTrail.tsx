import { useEffect, useRef } from "react";
import { useReducedMotion } from "motion/react";

const GLYPHS = "01アイウエオカキクケコサシスセソ<>/{}=+*#$%&ΣΔλ".split("");

/**
 * Matrix trail: a grid of glyphs that ignites under the pointer, drips short falling streams,
 * and fades. A few ambient streams keep it alive without a mouse. Canvas only, paused off-screen,
 * disabled under prefers-reduced-motion, and it reads the theme's accent colors live.
 */
export default function MatrixTrail({ className = "", cell = 18, ambient = 0.0008 }: { className?: string; cell?: number; ambient?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || reduce) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let w = 0, h = 0, cols = 0, rows = 0, dpr = 1;
    let heat = new Float32Array(0);
    let chars: string[] = [];
    type Drop = { c: number; r: number; speed: number; life: number };
    const drops: Drop[] = [];
    let raf = 0, visible = true, last = performance.now();
    const pointer = { x: -1, y: -1, px: -1, py: -1, active: false };
    let colors = { a: "#22d3ee", b: "#a78bfa", dim: "rgba(255,255,255,0.05)" };

    const readColors = () => {
      const cs = getComputedStyle(document.documentElement);
      const light = document.documentElement.dataset.theme === "light";
      colors = { a: cs.getPropertyValue("--accent").trim() || colors.a, b: cs.getPropertyValue("--accent-2").trim() || colors.b,
        dim: light ? "rgba(15,15,35,0.045)" : "rgba(255,255,255,0.04)" };
    };
    const resize = () => {
      const r = canvas.getBoundingClientRect();
      dpr = Math.min(2, window.devicePixelRatio || 1);
      w = r.width; h = r.height;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cols = Math.ceil(w / cell); rows = Math.ceil(h / cell);
      heat = new Float32Array(cols * rows);
      chars = Array.from({ length: cols * rows }, () => GLYPHS[(Math.random() * GLYPHS.length) | 0]);
    };
    const ignite = (c: number, r: number, v: number) => {
      if (c < 0 || r < 0 || c >= cols || r >= rows) return;
      const i = r * cols + c;
      if (v > heat[i]) { heat[i] = v; if (Math.random() < 0.35) chars[i] = GLYPHS[(Math.random() * GLYPHS.length) | 0]; }
    };
    const onMove = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect();
      pointer.px = pointer.x; pointer.py = pointer.y;
      pointer.x = e.clientX - r.left; pointer.y = e.clientY - r.top;
      pointer.active = pointer.x >= 0 && pointer.y >= 0 && pointer.x <= r.width && pointer.y <= r.height;
      if (!pointer.active) return;
      // stamp along the path so fast moves leave a continuous trail
      const steps = Math.max(1, Math.ceil(Math.hypot(pointer.x - pointer.px, pointer.y - pointer.py) / (cell * 0.6)));
      for (let s = 0; s <= steps; s++) {
        const t = s / steps;
        const x = pointer.px < 0 ? pointer.x : pointer.px + (pointer.x - pointer.px) * t;
        const y = pointer.py < 0 ? pointer.y : pointer.py + (pointer.y - pointer.py) * t;
        const c = Math.floor(x / cell), r0 = Math.floor(y / cell);
        for (let dc = -1; dc <= 1; dc++) for (let dr = -1; dr <= 1; dr++) ignite(c + dc, r0 + dr, dc === 0 && dr === 0 ? 1 : 0.55);
        if (Math.random() < 0.18 && drops.length < 140) drops.push({ c, r: r0, speed: 9 + Math.random() * 14, life: 6 + Math.random() * 10 });
      }
    };
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (!visible) { last = now; return; }
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      if (Math.random() < ambient * cols && drops.length < 140) drops.push({ c: (Math.random() * cols) | 0, r: 0, speed: 6 + Math.random() * 8, life: rows * 0.6 });
      for (let k = drops.length - 1; k >= 0; k--) {
        const d = drops[k];
        const before = Math.floor(d.r);
        d.r += d.speed * dt; d.life -= d.speed * dt;
        for (let rr = before; rr <= Math.floor(d.r); rr++) ignite(d.c, rr, 0.9);
        if (d.life <= 0 || d.r >= rows) drops.splice(k, 1);
      }
      ctx.clearRect(0, 0, w, h);
      ctx.font = `${Math.round(cell * 0.66)}px "JetBrains Mono Variable", ui-monospace, monospace`;
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      const decay = Math.pow(0.1, dt);
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const i = r * cols + c;
          const v = heat[i];
          const x = c * cell + cell / 2, y = r * cell + cell / 2;
          if (v < 0.02) {
            if ((c * 7 + r * 3) % 5 === 0) { ctx.fillStyle = colors.dim; ctx.fillText(chars[i], x, y); }
            continue;
          }
          ctx.globalAlpha = Math.min(0.8, v);
          ctx.fillStyle = v > 0.85 ? "#ffffff" : (c + r) % 2 ? colors.a : colors.b;
          ctx.fillText(chars[i], x, y);
          ctx.globalAlpha = 1;
          heat[i] = v * decay;
        }
      }
    };

    readColors(); resize();
    const ro = new ResizeObserver(resize); ro.observe(canvas);
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; }); io.observe(canvas);
    const mo = new MutationObserver(readColors); mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    window.addEventListener("pointermove", onMove, { passive: true });
    raf = requestAnimationFrame(frame);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); io.disconnect(); mo.disconnect(); window.removeEventListener("pointermove", onMove); };
  }, [reduce, cell, ambient]);

  return <canvas ref={ref} aria-hidden className={`pointer-events-none h-full w-full ${className}`} />;
}
