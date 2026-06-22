"use client";

import { useEffect, useState } from "react";
import { HeroGeometric } from "@/components/ui/shape-landing-hero";

export function SplashScreen() {
  const [mounted, setMounted] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const splashed = sessionStorage.getItem("sandbench_splashed");
    if (splashed) return;

    const startTimer = setTimeout(() => {
      setMounted(true);
      setVisible(true);
    }, 0);

    const fadeTimer = setTimeout(() => {
      setVisible(false);
    }, 2200);

    const unmountTimer = setTimeout(() => {
      setMounted(false);
      sessionStorage.setItem("sandbench_splashed", "true");
    }, 2600);

    return () => {
      clearTimeout(startTimer);
      clearTimeout(fadeTimer);
      clearTimeout(unmountTimer);
    };
  }, []);

  if (!mounted) return null;

  return (
    <div
      className={`fixed inset-0 z-[999] transition-opacity duration-400 ease-in-out ${
        visible ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
    >
      <HeroGeometric
        badge="Hardened execution platform"
        title1="Sand"
        title2="Bench"
      />
    </div>
  );
}
