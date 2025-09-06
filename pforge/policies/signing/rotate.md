# Key Rotation Procedure

This document outlines the detailed, step-by-step procedure for rotating the cryptographic keys used for signing AMP event proofs. Regular key rotation is a critical security practice to limit the impact of a potential key compromise.

## 1. Generate New Key Pair

The first step is to generate a new RSA private/public key pair. We will use `openssl` for this. The private key should be at least 2048 bits.

**Command:**
```bash
# Generate a new 2048-bit RSA private key
openssl genpkey -algorithm RSA -out private_key.pem -pkeyopt rsa_keygen_bits:2048

# Extract the public key from the private key
openssl rsa -pubout -in private_key.pem -out public.pem.new
```

**Security Warning:**
*   The `private_key.pem` file is highly sensitive. It should be stored in a secure location with strict access controls, such as a hardware security module (HSM) or a secure vault system (e.g., HashiCorp Vault, AWS KMS).
*   **DO NOT** commit the private key to version control.

## 2. Deploy the New Public Key

The new public key (`public.pem.new`) must be deployed to all systems that need to verify proof signatures. In the `pforge` system, this means replacing the existing `public.pem` file.

**Steps:**
1.  **Backup the old public key:**
    ```bash
    mv pforge/policies/signing/public.pem pforge/policies/signing/public.pem.old
    ```
2.  **Install the new public key:**
    ```bash
    mv public.pem.new pforge/policies/signing/public.pem
    ```
3.  **Commit and deploy the change:**
    ```bash
    git add pforge/policies/signing/public.pem
    git commit -m "feat(security): Rotate proof signing public key"
    # Follow your standard deployment process to roll this change out to all servers.
    ```

## 3. Transition Period (Zero-Downtime Rotation)

To ensure a smooth transition without service interruption, both the old and new keys should be considered valid for a period of time. The `pforge` system is designed to handle this by attempting to verify signatures with multiple keys.

The `proof.verifier` component should be configured to check signatures against both `public.pem` (the new key) and `public.pem.old` (the old key).

**Note:** This functionality is not yet implemented in the current version of the verifier. A future enhancement will allow specifying multiple public keys for verification. For now, the transition requires a brief maintenance window or careful coordination.

## 4. Activate the New Private Key

Once the new public key has been deployed to all verifier instances, you can begin signing new proofs with the new private key.

This step involves updating the configuration of the signing service or agent to point to the new `private_key.pem` file. The exact procedure depends on how the private key is managed in your environment.

## 5. Decommission the Old Key

After a suitable transition period (e.g., 24-48 hours) to ensure all in-flight events signed with the old key have been processed, you can decommission the old key.

**Steps:**
1.  **Remove the old public key:**
    ```bash
    rm pforge/policies/signing/public.pem.old
    ```
2.  **Commit and deploy this change:**
    ```bash
    git add pforge/policies/signing/public.pem.old
    git commit -m "chore(security): Decommission old proof signing key"
    # Deploy the change.
    ```
3.  **Securely delete the old private key:** Follow your organization's policy for the secure destruction of cryptographic material.

## Automated Script

A helper script to automate steps 1 and 2 can be found at `pforge/scripts/rotate_keys.sh`. This script will be created in a subsequent step.
