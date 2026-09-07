# Data Classification Policy (Sample)

## Classification Levels
- **Public**: No restrictions on disclosure.
- **Internal**: For employee use only, not for external sharing.
- **Confidential**: Customer PII, financial data, and credentials. Must be encrypted at rest and in
  transit, access is role-restricted, and access logs are retained for 1 year.
- **Restricted**: Highest sensitivity (e.g. authentication secrets, encryption keys). Access requires
  security team approval and is logged and reviewed monthly.

## Handling Requirements
Confidential and Restricted data must never be stored in local downloads, personal email, or
unapproved third-party SaaS tools. All Confidential data at rest must use AES-256 or equivalent
encryption, managed via Azure Key Vault-backed keys.
