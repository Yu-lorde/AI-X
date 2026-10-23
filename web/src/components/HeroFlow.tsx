import { useEffect, useRef } from "react";

/** Artwork stays separate from accessible, selectable HTML and live controls. */
export function HeroFlow() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const layer = ref.current;
    const shell = layer?.closest<HTMLElement>(".hero-shell");
    if (!layer || !shell) return;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    const move = (event: PointerEvent) => {
      if (motion.matches || event.pointerType === "touch") return;
      const box = shell.getBoundingClientRect();
      const x = (event.clientX - box.left) / box.width;
      const y = (event.clientY - box.top) / box.height;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        layer.style.setProperty("--flow-x", `${(x - .5) * 12}px`);
        layer.style.setProperty("--flow-y", `${(y - .5) * 8}px`);
        layer.style.setProperty("--pointer-x", `${x * 100}%`);
        layer.style.setProperty("--pointer-y", `${y * 100}%`);
        layer.classList.add("is-interacting");
      });
    };
    const reset = () => {
      cancelAnimationFrame(frame);
      layer.style.setProperty("--flow-x", "0px");
      layer.style.setProperty("--flow-y", "0px");
      layer.classList.remove("is-interacting");
    };
    shell.addEventListener("pointermove", move);
    shell.addEventListener("pointerleave", reset);
    motion.addEventListener("change", reset);
    return () => {
      cancelAnimationFrame(frame);
      shell.removeEventListener("pointermove", move);
      shell.removeEventListener("pointerleave", reset);
      motion.removeEventListener("change", reset);
    };
  }, []);
  return <div ref={ref} className="hero-art" aria-hidden="true">
    <div className="hero-art-image" />
    <div className="hero-pointer-light" />
  </div>;
}
