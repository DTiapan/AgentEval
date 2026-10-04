import React from "react";

interface LandingHeroMotionProps {
  children: React.ReactNode;
  className?: string;
}

/** Staggered entrance (--hf-delay index). Easing per animate skill: ease-out expo-ish. */
export const LandingReveal: React.FC<LandingHeroMotionProps & { delayIndex?: number }> = ({
  children,
  className = "",
  delayIndex = 0,
}) => (
  <div
    className={`hf-fade-rise ${className}`}
    style={{ "--hf-delay": delayIndex } as React.CSSProperties}
  >
    {children}
  </div>
);
