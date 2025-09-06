# HMAC Secret Rotation Procedure

This document outlines the procedure for rotating the HMAC shared secrets used for signing capability tokens. Regular secret rotation is a critical security practice to limit the impact of a potential secret compromise.

The `pforge` system supports zero-downtime secret rotation. The verification component can check a signature against multiple secrets, while the signing component always uses the newest secret.

## How it Works

The system retrieves a list of secrets from the `PFORGE_HMAC_SECRETS` environment variable.

*   The variable should contain a comma-separated list of secrets.
*   **The first secret in the list is the primary secret**, used for signing all new tokens.
*   All secrets in the list are used for verifying existing tokens.

This design allows you to introduce a new secret for signing while still being able to validate tokens that were signed with an older secret.

## Rotation Steps

### 1. Add the New Secret

Update the `PFORGE_HMAC_SECRETS` environment variable in your deployment environment (e.g., your `.env` file, Kubernetes secret, or CI/CD variable store).

**Add the new secret to the beginning of the comma-separated list.**

**Example:**

If your current variable is:
`PFORGE_HMAC_SECRETS="old-secret-key"`

Generate a new, strong, random secret. You can use a command like this:
```bash
openssl rand -hex 32
```

Update the variable to:
`PFORGE_HMAC_SECRETS="your-new-strong-secret,old-secret-key"`

### 2. Deploy the Change

Roll out this environment variable change to all running instances of the `pforge` application.

Once deployed:
*   All new capability tokens will be signed using `"your-new-strong-secret"`.
*   The system will still be able to verify tokens signed with `"old-secret-key"`.

This ensures a seamless transition with no downtime.

### 3. Decommission the Old Secret

After a suitable transition period (e.g., 24-48 hours, or the maximum lifetime of a capability token), you can safely remove the old secret.

**Update the environment variable again, removing the old secret from the list.**

**Example:**

`PFORGE_HMAC_SECRETS="your-new-strong-secret"`

Deploy this change. Now, the system will only recognize the new secret for both signing and verification. Any tokens signed with the old secret will no longer be valid.
