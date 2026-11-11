/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, ListChecks } from "lucide-react";
import { cn } from "@/lib/utils";

/* 21st.dev "pixel perfect hero", adapted: TESSERA copy, standards marquee instead of brand logos. */
const STANDARDS = ["OWASP Agentic Top 10", "Cedar policy", "AARM decisions", "RFC 8693 delegation", "SPIFFE identity", "OpenTelemetry GenAI", "Ed25519 receipts"];

type Pixel = {
  x: number; y: number; color: string; ctx: CanvasRenderingContext2D; speed: number; size: number; sizeStep: number; minSize: number;
  maxSizeInt: number; maxSize: number; delay: number; counter: number; counterStep: number; isIdle: boolean; isReverse: boolean; isShimmer: boolean;
  draw: () => void; appear: () => void; disappear: () => void; shimmer: () => void;
};

function createPixel(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, x: number, y: number, color: string, baseSpeed: number, delay: number): Pixel {
  const rand = (min: number, max: number) => Math.random() * (max - min) + min;
  const p: Pixel = {
    x, y, color, ctx, speed: rand(0.08, 0.4) * baseSpeed, size: 0, sizeStep: rand(0.12, 0.28), minSize: 0.5, maxSizeInt: 2, maxSize: rand(0.5, 2), delay, counter: 0,
    counterStep: rand(1.8, 3.2) + (canvas.width + canvas.height) * 0.008, isIdle: false, isReverse: false, isShimmer: false,
    draw() { const offset = p.maxSizeInt * 0.5 - p.size * 0.5; ctx.fillStyle = p.color; ctx.fillRect(p.x + offset, p.y + offset, p.size, p.size); },
    appear() {
      p.isIdle = false;
      if (p.counter <= p.delay) { p.counter += p.counterStep; return; }
      if (p.size >= p.maxSize) p.isShimmer = true;
      if (p.isShimmer) p.shimmer(); else p.size += p.sizeStep;
      p.draw();
    },
    disappear() { p.isShimmer = false; p.counter = 0; if (p.size <= 0) { p.isIdle = true; return; } p.size -= 0.1; p.draw(); },
    shimmer() {
      if (p.size >= p.maxSize) p.isReverse = true; else if (p.size <= p.minSize) p.isReverse = false;
      if (p.isReverse) p.size -= p.speed; else p.size += p.speed;
    },
  };
  return p;
}

export function PixelCanvas({ colors, gap = 5, speed = 30 }: { colors: string[]; gap?: number; speed?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const pixelsRef = useRef<Pixel[]>([]);
  const animationRef = useRef<number>(0);
  const lastFrameRef = useRef(0);
  const reducedMotionRef = useRef(false);

  const init = useCallback(() => {
    const canvas = canvasRef.current; const wrap = wrapRef.current;
    if (!canvas || !wrap || colors.length === 0) return;
    const ctx = canvas.getContext("2d"); if (!ctx) return;
    const { width, height } = wrap.getBoundingClientRect();
    const w = Math.floor(width); const h = Math.floor(height);
    canvas.width = w; canvas.height = h; canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;
    const effectiveSpeed = reducedMotionRef.current ? 0 : Math.min(speed, 100) * 0.001;
    const pixels: Pixel[] = [];
    for (let x = 0; x < w; x += gap) for (let y = 0; y < h; y += gap) {
      const color = colors[Math.floor(Math.random() * colors.length)];
      const dx = x - w / 2; const dy = y - h / 2;
      const delay = reducedMotionRef.current ? 0 : Math.sqrt(dx * dx + dy * dy) * 0.65;
      pixels.push(createPixel(ctx, canvas, x, y, color, effectiveSpeed, delay));
    }
    pixelsRef.current = pixels;
  }, [colors, gap, speed]);

  const animate = useCallback((mode: "appear" | "disappear") => {
    cancelAnimationFrame(animationRef.current);
    const frameInterval = 1000 / 60;
    const loop = () => {
      animationRef.current = requestAnimationFrame(loop);
      const now = performance.now(); const elapsed = now - lastFrameRef.current;
      if (elapsed < frameInterval) return;
      lastFrameRef.current = now - (elapsed % frameInterval);
      const canvas = canvasRef.current; const ctx = canvas?.getContext("2d");
      if (!canvas || !ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const pixels = pixelsRef.current;
      for (const pixel of pixels) pixel[mode]();
    };
    animationRef.current = requestAnimationFrame(loop);
  }, []);

  useEffect(() => {
    reducedMotionRef.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    lastFrameRef.current = performance.now();
    init();
    const ro = new ResizeObserver(() => init());
    if (wrapRef.current) ro.observe(wrapRef.current);
    animate("appear");
    return () => { ro.disconnect(); cancelAnimationFrame(animationRef.current); };
  }, [init, animate]);

  return (<div ref={wrapRef} className="absolute inset-0 overflow-hidden"><canvas ref={canvasRef} className="block h-full w-full" /></div>);
}

interface PixelHeroProps {
  word1?: string; word2?: string; description?: string; primaryCta?: string; secondaryCta?: string;
  onPrimaryClick?: () => void; onSecondaryClick?: () => void;
}

export function PixelHero({ word1 = "Silent", word2 = "Precision.", description = "", primaryCta = "Explore", secondaryCta = "Start here", onPrimaryClick, onSecondaryClick }: PixelHeroProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [themeColors, setThemeColors] = useState<string[]>([]);
  useEffect(() => {
    const div = document.createElement("div"); document.body.appendChild(div);
    div.className = "text-muted-foreground"; const muted = getComputedStyle(div).color;
    div.className = "text-primary"; const primary = getComputedStyle(div).color;
    document.body.removeChild(div);
    setThemeColors([muted, muted, muted, muted, primary]);
    const t = setTimeout(() => setIsLoaded(true), 50);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="relative isolate -mx-5 -mt-8 flex min-h-[calc(100dvh-48px)] w-[calc(100%+2.5rem)] select-none flex-col items-center justify-center gap-8 overflow-hidden bg-background px-4 md:-mx-10 md:w-[calc(100%+5rem)]">
      <style>{`
        @keyframes marquee { 0% { transform: translateX(0%); } 100% { transform: translateX(-50%); } }
        .animate-marquee { animation: marquee 32s linear infinite; }
        .tahoe-glass-text { color: transparent; background: linear-gradient(135deg, #fff 0%, rgba(255,255,255,.4) 25%, rgba(255,255,255,.1) 45%, rgba(255,255,255,.9) 55%, rgba(255,255,255,.2) 75%, #fff 100%); background-size: 200% auto; -webkit-background-clip: text; background-clip: text; -webkit-text-stroke: 1.5px rgba(255,255,255,.3); animation: shimmer 8s linear infinite; }
        @keyframes shimmer { 0% { background-position: 200% center; } 100% { background-position: 0% center; } }
        @media (prefers-reduced-motion: reduce) { .animate-marquee, .tahoe-glass-text { animation: none; } }
      `}</style>
      <div className="pointer-events-none absolute inset-0 z-0">
        {themeColors.length > 0 && <PixelCanvas colors={themeColors} gap={6} speed={30} />}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,var(--background)_100%)] opacity-90" />
      </div>
      <h1 className="tahoe-glass-text pointer-events-none flex w-full flex-wrap items-center justify-center gap-2 px-1 text-center text-[2.6rem] leading-none sm:gap-4 sm:text-6xl md:text-8xl">
        <span className="font-serif font-medium italic">{word1}</span>
        <span className="font-sans font-extrabold tracking-tighter">{word2}</span>
      </h1>
      <p className="pointer-events-none max-w-xl px-1 text-center text-base font-light leading-relaxed text-foreground/85 sm:text-lg">{description}</p>
      <div className={cn("flex items-center justify-center gap-3 transition-all duration-1000", isLoaded ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0")} style={{ transitionDelay: "400ms" }}>
        <button onClick={onPrimaryClick} className="btn btn-primary !h-11 !rounded-xl !px-6 text-[15px] font-semibold">{primaryCta}<ArrowRight size={16} /></button>
        <button onClick={onSecondaryClick} className="btn btn-ghost !h-11 !rounded-xl !px-6 text-[15px] font-semibold"><ListChecks size={16} />{secondaryCta}</button>
      </div>
      <div className={cn("absolute inset-x-0 bottom-8 z-10 flex flex-col items-center gap-3 transition-all duration-1000", isLoaded ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0")} style={{ transitionDelay: "600ms" }}>
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground/80">Built on open standards</span>
        <div className="relative w-full max-w-4xl overflow-hidden [mask-image:linear-gradient(to_right,transparent,white_15%,white_85%,transparent)]">
          <div className="animate-marquee flex w-max gap-12 py-2 text-sm text-muted-foreground">
            {[0, 1].map((k) => (<div key={k} className="flex items-center gap-12" aria-hidden={k === 1}>{STANDARDS.map((s) => <span key={s + k} className="whitespace-nowrap font-medium">{s}</span>)}</div>))}
          </div>
        </div>
      </div>
    </div>
  );
}
