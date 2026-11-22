"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Card } from "@/components/common/Card";

interface DeferredChartProps {
  children: ReactNode;
  minHeight?: number;
}

/** Mount expensive ECharts instances only when they approach the viewport. */
export function DeferredChart({ children, minHeight = 280 }: DeferredChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || visible) return;

    if (!("IntersectionObserver" in window)) {
      const timer = setTimeout(() => setVisible(true), 0);
      return () => clearTimeout(timer);
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry?.isIntersecting) return;
        setVisible(true);
        observer.disconnect();
      },
      { rootMargin: "500px 0px" },
    );
    observer.observe(host);
    return () => observer.disconnect();
  }, [visible]);

  return (
    <div ref={hostRef} style={{ minHeight }}>
      {visible ? (
        children
      ) : (
        <Card>
          <div
            aria-hidden="true"
            className="animate-pulse rounded bg-[var(--color-border)]"
            style={{ height: minHeight - 32 }}
          />
        </Card>
      )}
    </div>
  );
}
