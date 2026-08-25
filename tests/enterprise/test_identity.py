"""Wave A identity core: config fields, claims->principal, role matrix, contextvar."""

from mnemo_mcp.config import Settings


def test_enterprise_defaults_off(monkeypatch):
    for var in (
        "MNEMO_ENTERPRISE",
        "MNEMO_ENTERPRISE_ISSUERS",
        "MNEMO_ENTERPRISE_AUDIENCE",
        "MNEMO_ENTERPRISE_ROLE_CLAIM",
        "MNEMO_ENTERPRISE_ROLE_MAPPING",
        "MNEMO_ENTERPRISE_TENANT_CLAIM",
        "MNEMO_AUDIT_HASH_KEY",
        "MNEMO_AUDIT_KEY_ID",
        "MNEMO_AUDIT_RETENTION_DAYS",
    ):
        monkeypatch.delenv(var, raising=False)
    s = Settings()
    assert s.enterprise_enabled is False
    assert s.enterprise_issuers == ""
    assert s.enterprise_audience == ""
    assert s.enterprise_role_claim == "groups"
    assert s.enterprise_role_mapping == "{}"
    assert s.enterprise_tenant_claim == "tid"
    assert s.audit_hash_key == ""
    assert s.audit_key_id == "k1"
    assert s.audit_retention_days == 400


def test_enterprise_env_overrides(monkeypatch):
    monkeypatch.setenv("MNEMO_ENTERPRISE", "true")
    monkeypatch.setenv("MNEMO_ENTERPRISE_ISSUERS", "https://idp.example.com")
    monkeypatch.setenv("MNEMO_AUDIT_HASH_KEY", "sixteen-byte-key")
    s = Settings()
    assert s.enterprise_enabled is True
    assert s.enterprise_issuers == "https://idp.example.com"
    assert s.audit_hash_key == "sixteen-byte-key"
