import { useMsal } from "@azure/msal-react";
import { useEffect, useState } from "react";

import { api, type CostSummary } from "../services/api";

export function CostBadge() {
  const { instance } = useMsal();
  const [summary, setSummary] = useState<CostSummary | null>(null);

  useEffect(() => {
    const load = () => api.costSummary(instance).then(setSummary).catch(() => setSummary(null));
    load();
    const interval = setInterval(load, 30_000);
    return () => clearInterval(interval);
  }, [instance]);

  if (!summary) return null;

  const pct = Math.min(summary.percent_of_budget, 100);
  const level = pct > 90 ? "danger" : pct > 70 ? "warn" : "ok";

  return (
    <div className={`cost-badge cost-badge--${level}`} title="Month-to-date Azure OpenAI spend tracked by this platform">
      ${summary.month_to_date_usd.toFixed(2)} / ${summary.monthly_budget_usd.toFixed(0)} ({pct.toFixed(0)}%)
    </div>
  );
}
