# Key Rotation Procedure

This document outlines the procedure for rotating the cryptographic keys used for signing AMP events.

## Steps

1.  **Generate a new key pair.** Use a secure method to generate a new RSA key pair.
2.  **Distribute the new public key.** The new public key should be distributed to all systems that need to verify AMP event signatures.
3.  **Transition period.** For a period of time, both the old and new keys should be considered valid.
4.  **Decommission the old key.** Once all systems have been updated with the new public key, the old key should be decommissioned.
