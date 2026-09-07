import { useMsal } from "@azure/msal-react";

import { apiTokenRequest } from "../auth/msalConfig";

export function SignIn() {
  const { instance } = useMsal();

  const signIn = () => {
    instance.loginPopup(apiTokenRequest).then((result) => {
      instance.setActiveAccount(result.account);
    });
  };

  return (
    <div className="signin">
      <h1>Azure Enterprise Agentic AI</h1>
      <p>Sign in with your organizational account to continue.</p>
      <button onClick={signIn}>Sign in with Microsoft Entra ID</button>
    </div>
  );
}
