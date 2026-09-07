import { AuthenticatedTemplate, UnauthenticatedTemplate, useMsal } from "@azure/msal-react";

import { authDisabled } from "./auth/msalConfig";
import { ChatWindow } from "./components/ChatWindow";
import { CostBadge } from "./components/CostBadge";
import { DemoBanner } from "./components/DemoBanner";
import { SignIn } from "./components/SignIn";

function Header() {
  const { instance } = useMsal();
  const account = instance.getActiveAccount();

  return (
    <header className="app-header">
      <h1>Enterprise Agentic AI</h1>
      <div className="app-header__right">
        <CostBadge />
        {account && (
          <span className="user-chip">
            {account.name ?? account.username}
            <button className="link-button" onClick={() => instance.logoutPopup()}>
              Sign out
            </button>
          </span>
        )}
      </div>
    </header>
  );
}

export default function App() {
  if (authDisabled) {
    return (
      <div className="app">
        <Header />
        <DemoBanner />
        <ChatWindow />
      </div>
    );
  }

  return (
    <div className="app">
      <AuthenticatedTemplate>
        <Header />
        <DemoBanner />
        <ChatWindow />
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <SignIn />
      </UnauthenticatedTemplate>
    </div>
  );
}
