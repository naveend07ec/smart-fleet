import base64
import json
import pytest
from app.services.ibe_service import ibe_service

def test_ibe_status_and_trust_model(client):
    res = client.get("/api/security/ibe/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "Boneh-Franklin" in data["scheme"]
    assert "BN128" in data["curve"]
    assert "key escrow" in data["pkg_trust_model"].lower()
    # Confirm master secret is not exposed in status
    assert "master_secret" not in data
    assert "s" not in data

def test_ibe_identity_validation():
    # Valid identities
    assert ibe_service.validate_identity("traffic-control-hub-01") == "traffic-control-hub-01"
    assert ibe_service.validate_identity("dispatch.chennai@smartfleet.org") == "dispatch.chennai@smartfleet.org"

    # Invalid identities: empty, too short, invalid chars
    with pytest.raises(ValueError, match="non-empty"):
        ibe_service.validate_identity("")
    with pytest.raises(ValueError, match="between 3 and 100"):
        ibe_service.validate_identity("ab")
    with pytest.raises(ValueError, match="invalid characters"):
        ibe_service.validate_identity("hacker$name#forbidden!")

def test_ibe_encrypt_and_authorized_decryption(client):
    recipient = "traffic-hub-chennai-north"
    payload = json.dumps({
        "vehicle_id": "SIM-DEMO-001",
        "speed": 62.4,
        "lat": 13.0827,
        "lng": 80.2707,
        "battery": 88.5
    })

    # Encrypt
    enc_res = client.post("/api/security/ibe/encrypt", json={
        "recipient_identity": recipient,
        "payload": payload
    })
    assert enc_res.status_code == 200
    bundle = enc_res.json()
    assert bundle["recipient_identity"] == recipient
    assert "ciphertext_b64" in bundle
    assert "u_point" in bundle
    assert bundle["payload_size_bytes"] == len(payload.encode("utf-8"))

    # Authorized Decrypt
    dec_res = client.post("/api/security/ibe/decrypt", json={
        "recipient_identity": recipient,
        "ciphertext_bundle": bundle
    })
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["success"] is True
    assert dec_data["decrypted_payload"] == payload

def test_ibe_unauthorized_decryption_rejected(client):
    recipient = "logistics-hub-01"
    intruder = "unauthorized-eavesdropper-node"
    payload = "Confidential telemetry coordinates: 13.0500, 80.2500"

    # Encrypt for legitimate recipient
    enc_res = client.post("/api/security/ibe/encrypt", json={
        "recipient_identity": recipient,
        "payload": payload
    })
    bundle = enc_res.json()

    # Attempt decrypt with unauthorized identity
    dec_res = client.post("/api/security/ibe/decrypt", json={
        "recipient_identity": intruder,
        "ciphertext_bundle": bundle
    })
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["success"] is False
    assert dec_data["decrypted_payload"] is None
    assert "failed" in dec_data["error"].lower()

def test_ibe_ciphertext_tampering_rejected(client):
    recipient = "security-operations-center"
    payload = "Sensory payload tamper test"

    enc_res = client.post("/api/security/ibe/encrypt", json={
        "recipient_identity": recipient,
        "payload": payload
    })
    bundle = enc_res.json()

    # Tamper with the raw ciphertext
    raw_ct = bytearray(base64.b64decode(bundle["ciphertext_b64"]))
    raw_ct[0] ^= 0x5A  # flip bits
    bundle["ciphertext_b64"] = base64.b64encode(bytes(raw_ct)).decode("ascii")

    dec_res = client.post("/api/security/ibe/decrypt", json={
        "recipient_identity": recipient,
        "ciphertext_bundle": bundle
    })
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["success"] is False
    assert dec_data["decrypted_payload"] is None

def test_ibe_payload_sizes(client):
    recipient = "size-test-recipient"

    # 128 bytes, 512 bytes, 2 KB synthetic payloads
    for size_bytes in [128, 512, 2048]:
        raw_payload = "A" * size_bytes
        enc_res = client.post("/api/security/ibe/encrypt", json={
            "recipient_identity": recipient,
            "payload": raw_payload
        })
        assert enc_res.status_code == 200
        bundle = enc_res.json()
        assert bundle["payload_size_bytes"] == size_bytes

        dec_res = client.post("/api/security/ibe/decrypt", json={
            "recipient_identity": recipient,
            "ciphertext_bundle": bundle
        })
        assert dec_res.status_code == 200
        assert dec_res.json()["decrypted_payload"] == raw_payload

def test_ibe_empty_payload_fails(client):
    res = client.post("/api/security/ibe/encrypt", json={
        "recipient_identity": "valid-id",
        "payload": ""
    })
    assert res.status_code == 422 or res.status_code == 400

def test_ibe_experiment_lifecycle(client):
    exp_payload = {
        "recipient_identity": "emergency-dispatch-01",
        "unauthorized_identity": "rogue-vehicle-sensor",
        "payload": '{"emergency_alert": "Battery critical", "vehicle_id": "SIM-DEMO-010"}',
        "notes": "Automated regression verification trial"
    }

    create_res = client.post("/api/security/ibe/experiments", json=exp_payload)
    assert create_res.status_code == 201
    exp_data = create_res.json()
    assert exp_data["status"] == "success"
    assert exp_data["authorized_success"] is True
    assert exp_data["unauthorized_rejected"] is True
    assert exp_data["tamper_check_passed"] is True
    assert exp_data["encryption_duration_ms"] > 0
    assert exp_data["decryption_duration_ms"] > 0
    exp_id = exp_data["experiment_id"]

    # Retrieve experiment
    get_res = client.get(f"/api/security/ibe/experiments/{exp_id}")
    assert get_res.status_code == 200
    assert get_res.json()["experiment_id"] == exp_id

    # List experiments
    list_res = client.get("/api/security/ibe/experiments")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
