import type { IPublicClientApplication } from "@azure/msal-browser";
import { InteractionRequiredAuthError } from "@azure/msal-browser";

import { apiTokenRequest, authDisabled } from "../auth/msalConfig";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export interface Citation {
  source?: string;
  document_id?: string;
  score: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  retrieval_score: number;
}

export interface AgentChatResponse {
  answer: string;
}

export interface CostSummary {
  month_to_date_usd: number;
  monthly_budget_usd: number;
  percent_of_budget: number;
}

async function getToken(msalInstance: IPublicClientApplication): Promise<string | null> {
  if (authDisabled) return null;

  const account = msalInstance.getActiveAccount();
  if (!account) throw new Error("No active account; user must sign in first.");

  try {
    const result = await msalInstance.acquireTokenSilent({ ...apiTokenRequest, account });
    return result.accessToken;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      const result = await msalInstance.acquireTokenPopup(apiTokenRequest);
      return result.accessToken;
    }
    throw error;
  }
}

async function apiFetch<T>(msalInstance: IPublicClientApplication, path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken(msalInstance);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API error ${response.status}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  chatCompletion: (msal: IPublicClientApplication, question: string) =>
    apiFetch<ChatResponse>(msal, "/api/chat/completions", {
      method: "POST",
      body: JSON.stringify({ question, top_k: 5 }),
    }),

  agentChat: (msal: IPublicClientApplication, question: string) =>
    apiFetch<AgentChatResponse>(msal, "/api/chat/agent", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  costSummary: (msal: IPublicClientApplication) => apiFetch<CostSummary>(msal, "/api/cost/summary"),
};
