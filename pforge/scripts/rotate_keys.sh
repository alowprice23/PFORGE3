#!/usr/bin/env bash

# This script automates the generation of a new key pair and the
# replacement of the public key in the repository.

set -euo pipefail

# Ensure we are in the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/.."

SIGNING_DIR="pforge/policies/signing"
NEW_PRIVATE_KEY="private_key.new.pem"
NEW_PUBLIC_KEY="public.pem.new"
OLD_PUBLIC_KEY_BACKUP="public.pem.old"
CURRENT_PUBLIC_KEY="public.pem"

echo "🔑 Generating a new 2048-bit RSA private key..."
openssl genpkey -algorithm RSA -out "$NEW_PRIVATE_KEY" -pkeyopt rsa_keygen_bits:2048
if [ $? -ne 0 ]; then
    echo "❌ Failed to generate private key."
    exit 1
fi

echo "🔐 Extracting public key from the new private key..."
openssl rsa -pubout -in "$NEW_PRIVATE_KEY" -out "$NEW_PUBLIC_KEY"
if [ $? -ne 0 ]; then
    echo "❌ Failed to extract public key."
    exit 1
fi

echo "🔄 Rotating public keys..."

# Check if the current public key exists
if [ -f "$SIGNING_DIR/$CURRENT_PUBLIC_KEY" ]; then
    echo "  -> Backing up current public key to $SIGNING_DIR/$OLD_PUBLIC_KEY_BACKUP"
    mv "$SIGNING_DIR/$CURRENT_PUBLIC_KEY" "$SIGNING_DIR/$OLD_PUBLIC_KEY_BACKUP"
else
    echo "  -> No existing public key found. Skipping backup."
fi

echo "  -> Installing new public key to $SIGNING_DIR/$CURRENT_PUBLIC_KEY"
mv "$NEW_PUBLIC_KEY" "$SIGNING_DIR/$CURRENT_PUBLIC_KEY"

echo ""
echo "✅ Public key rotation complete."
echo ""
echo "========================= ⚠️ IMPORTANT ⚠️ ========================="
echo "A new private key has been generated: './$NEW_PRIVATE_KEY'"
echo "This file is highly sensitive and MUST be moved to a secure location"
echo "immediately (e.g., a secrets vault or HSM). It should NEVER be"
echo "committed to version control."
echo ""
echo "After deploying the new public key, you must update your signing"
echo "service to use this new private key."
echo "==================================================================="
echo ""
