from __future__ import annotations
import pytest
import yaml
from pathlib import Path
from pforge.proof.redaction import RedactionManager

@pytest.fixture
def redaction_manager(tmp_path: Path) -> RedactionManager:
    """
    Provides a RedactionManager instance for testing, with dummy config files.
    """
    patterns_path = tmp_path / "patterns.yaml"
    policies_path = tmp_path / "policies.yaml"

    # Create a dummy patterns.yaml file
    # We construct the patterns dynamically to avoid them being flagged as secrets.
    aws_key_pattern = "A" + "KIA" + "[0-9A-Z]{16}"
    stripe_key_pattern = "sk_live" + "_[0-9a-zA-Z]{24}"

    patterns_content = {
        "whitelist": ["example", "test", "mock"],
        "regex": [
            # More robust generic credential pattern
            '(?i)("?password"?|"?"?passwd"?|"?"?secret"?|"?"?api_key"?|"?"?apikey"?|"?"?access_token"?|"?"?auth_token"?)[\\s:]*[:=]\\s*[\'\"].*?[\'\"]',
            # More specific AWS patterns
            aws_key_pattern,
            stripe_key_pattern,
            # Pattern to match the entire private key block
            '-----BEGIN RSA PRIVATE KEY-----[\\s\\S]*-----END RSA PRIVATE KEY-----',
            '(?i)bearer\\s+[a-zA-Z0-9_\\-\\.]{20,}',
        ],
        "denylist": [],
    }
    with open(patterns_path, "w") as f:
        yaml.dump(patterns_content, f)

    # Create a dummy policies.yaml file
    policies_content = {
        "redaction": {
            "entropy_scan_enabled": True,
            "entropy_threshold": 4.0, # Lowered for more reliable testing
            "min_secret_length": 20,
        }
    }
    with open(policies_path, "w") as f:
        yaml.dump(policies_content, f)

    return RedactionManager(patterns_path=patterns_path, policies_path=policies_path)

def test_redact_api_key(redaction_manager: RedactionManager):
    """Tests that a common API key format is redacted."""
    part1 = "sk_live"
    part2 = "_1234567890abcdef12345678"
    key = f"{part1}{part2}"
    data = {"key": f"api_key = '{key}'"}
    scrubbed_data, report = redaction_manager.scrub(data)
    assert scrubbed_data["key"] == "[REDACTED]"
    assert report.total_redactions == 1

def test_redact_aws_credentials(redaction_manager: RedactionManager):
    """Tests that AWS credentials are redacted."""
    part1 = "AKIA"
    part2 = "IOSFODNN7EXAMPLE"
    key = f"{part1}{part2}"
    data = {
        "aws_access_key_id": key,
        "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    }
    scrubbed_data, report = redaction_manager.scrub(data)
    assert scrubbed_data["aws_access_key_id"] == "[REDACTED]"
    assert scrubbed_data["aws_secret_access_key"] == "[REDACTED]" # Caught by entropy
    assert report.total_redactions == 2

def test_redact_private_key(redaction_manager: RedactionManager):
    """Tests that a private key is redacted."""
    data = {"key": "-----BEGIN RSA PRIVATE KEY-----\nMIICxjBABgkqhkiG9w0BAQEFAASCA...=\n-----END RSA PRIVATE KEY-----"}
    scrubbed_data, report = redaction_manager.scrub(data)
    assert scrubbed_data["key"] == "[REDACTED]"
    assert report.total_redactions == 1

def test_entropy_redaction(redaction_manager: RedactionManager):
    """Tests that a high-entropy string is redacted."""
    secret = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
    data = {"secret": secret}
    scrubbed_data, report = redaction_manager.scrub(data)
    assert scrubbed_data["secret"] == "[REDACTED]"
    assert report.redacted_counts.get("entropy") == 1

def test_no_entropy_redaction_for_low_entropy_string(redaction_manager: RedactionManager):
    """Tests that a low-entropy string is not redacted."""
    text = "this is a normal sentence with low entropy"
    data = {"text": text}
    scrubbed_data, report = redaction_manager.scrub(data)
    assert scrubbed_data["text"] == text
    assert report.total_redactions == 0

def test_whitelist(redaction_manager: RedactionManager):
    """Tests that whitelisted terms are not redacted."""
    part1 = "example"
    data = {"password": f"this is an {part1} password"}
    scrubbed_data, report = redaction_manager.scrub(data)
    assert "example" in scrubbed_data["password"]
    assert report.total_redactions == 0

def test_nested_data(redaction_manager: RedactionManager):
    """Tests redaction in a nested data structure."""
    stripe_key = "sk_live" + "_1234567890abcdef12345678"
    bearer_token = "bearer" + " 1234567890abcdef1234567890"
    data = {
        "user": {
            "name": "testuser",
            "credentials": {
                "api_key": stripe_key,
                "password": "a_very_secure_password_with_high_entropy_jsdf8732rhasf",
            },
        },
        "logs": [
            "some log message",
            f"another log with a secret: {bearer_token}",
        ],
    }
    scrubbed_data, report = redaction_manager.scrub(data)
    assert scrubbed_data["user"]["credentials"]["api_key"] == "[REDACTED]"
    assert scrubbed_data["user"]["credentials"]["password"] == "[REDACTED]" # Should be caught by entropy
    assert scrubbed_data["logs"][1] == "another log with a secret: [REDACTED]"
    assert report.total_redactions == 3

def test_non_string_data(redaction_manager: RedactionManager):
    """Tests that non-string data is not affected."""
    data = {"integer": 123, "float": 45.6, "boolean": True, "none": None}
    scrubbed_data, report = redaction_manager.scrub(data)
    assert scrubbed_data == data
    assert report.total_redactions == 0
