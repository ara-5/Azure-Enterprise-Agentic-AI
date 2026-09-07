import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export function DemoBanner() {
  const [demoMode, setDemoMode] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((r) => r.json())
      .then((body) => setDemoMode(Boolean(body.demo_mode)))
      .catch(() => setDemoMode(null));
  }, []);

  if (!demoMode) return null;

  return (
    <div className="demo-banner">
      <strong>Demo mode:</strong> answers come from local keyword retrieval over sample docs, not a live Azure
      OpenAI call. Set <code>DEMO_MODE=false</code> with real Azure credentials to see the full pipeline.
    </div>
  );
}
