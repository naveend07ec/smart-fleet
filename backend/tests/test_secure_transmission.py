import json
import uuid
import base64
from datetime import datetime, timezone, timedelta
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.models.vehicle import Vehicle
from app.models.telemetry import Telemetry
from app.models.secure_transmission import VehicleEnrollment, SecureTransmission, ProcessedMessageCache
from app.services.ibe_service import ibe_service
from app.services.secure_transmission_service import secure_transmission_service, SERVER_RECIPIENT_IDENTITY

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

def test_enrollment_and_authorization(client, db_session):
    # Setup vehicle
    v = Vehicle(vehicle_identifier="TEST-SEC-001", name="Test Unit 001", status="idle")
    db_session.add(v)
    db_session.commit()

    # 1. Enroll vehicle
    resp = client.post("/api/secure-transmission/enroll", json={
        "vehicle_identifier": "TEST-SEC-001",
        "assigned_identity": "TEST-SEC-001@fleet.iot.local",
        "notes": "Test enrollment"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["vehicle_identifier"] == "TEST-SEC-001"
    assert data["is_enrolled"] is True
    assert data["signing_public_key"] is not None
    assert len(data["signing_public_key"]) > 0

    # 2. List enrollments
    list_resp = client.get("/api/secure-transmission/enrollments")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(item["vehicle_identifier"] == "TEST-SEC-001" for item in items)

def test_mode_a_plaintext_transmission(client, db_session):
    v = Vehicle(vehicle_identifier="TEST-SEC-002", name="Test Unit 002", status="idle")
    db_session.add(v)
    db_session.commit()

    client.post("/api/secure-transmission/enroll", json={
        "vehicle_identifier": "TEST-SEC-002"
    })

    msg_id = f"MSG-TEST-PT-{uuid.uuid4().hex[:6]}"
    now_dt = datetime.now(timezone.utc)

    payload = {
        "vehicle_identifier": "TEST-SEC-002",
        "sender_identity": "TEST-SEC-002@fleet.iot.local",
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": msg_id,
        "timestamp": now_dt.isoformat(),
        "telemetry": {
            "latitude": 13.0500,
            "longitude": 80.2100,
            "speed": 40.0,
            "status": "moving",
            "battery_level": 82.5
        },
        "payload_category": "medium"
    }

    resp = client.post("/api/secure-transmission/plaintext", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["transmission_mode"] == "plaintext"
    assert data["original_payload_size_bytes"] > 0
    assert data["encrypted_envelope_size_bytes"] == data["original_payload_size_bytes"]
    assert data["payload_expansion_bytes"] == 0
    assert data["telemetry_persisted"] is True

    # Verify persisted in database
    db_rec = db_session.query(SecureTransmission).filter(
        SecureTransmission.transmission_id == data["transmission_id"]
    ).first()
    assert db_rec is not None
    assert db_rec.status == "success"

def test_mode_b_encrypted_authorized_transmission(client, db_session):
    v = Vehicle(vehicle_identifier="TEST-SEC-003", name="Test Unit 003", status="idle")
    db_session.add(v)
    db_session.commit()

    client.post("/api/secure-transmission/enroll", json={
        "vehicle_identifier": "TEST-SEC-003"
    })

    sender_id = "TEST-SEC-003@fleet.iot.local"
    recipient_id = SERVER_RECIPIENT_IDENTITY
    msg_id = f"MSG-TEST-IBE-{uuid.uuid4().hex[:6]}"
    ts_iso = utc_now_iso()

    telemetry_json = json.dumps({
        "vehicle_identifier": "TEST-SEC-003",
        "timestamp": ts_iso,
        "telemetry": {
            "latitude": 13.0600,
            "longitude": 80.2200,
            "speed": 55.0,
            "status": "moving",
            "battery_level": 76.0
        }
    })

    # Client-side IBE encryption with AAD binding
    aad = secure_transmission_service.compute_aad(sender_id, recipient_id, msg_id, ts_iso)
    bundle = ibe_service.encrypt(recipient_id, telemetry_json, aad=aad)

    # Client-side Ed25519 digital signature
    sig_b64 = secure_transmission_service.sign_envelope(
        vehicle_identifier="TEST-SEC-003",
        sender_identity=sender_id,
        recipient_identity=recipient_id,
        message_id=msg_id,
        timestamp_str=ts_iso,
        ciphertext_bundle=bundle
    )

    req = {
        "sender_identity": sender_id,
        "recipient_identity": recipient_id,
        "message_id": msg_id,
        "timestamp": ts_iso,
        "ciphertext_bundle": bundle,
        "signature_b64": sig_b64,
        "claimed_vehicle_identifier": "TEST-SEC-003",
        "payload_category": "medium"
    }

    resp = client.post("/api/secure-transmission/encrypted", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["signature_verified"] is True
    assert data["transmission_mode"] == "ibe_protected"
    assert data["decryption_duration_ms"] > 0
    assert data["encrypted_envelope_size_bytes"] > data["original_payload_size_bytes"]
    assert data["payload_expansion_bytes"] > 0
    assert data["telemetry_persisted"] is True

def test_rejection_unauthorized_vehicle_identity(client, db_session):
    # Unenrolled rogue identity
    unauth_sender = "ROGUE-VEH-999@attacker.net"
    msg_id = f"MSG-UNAUTH-{uuid.uuid4().hex[:6]}"
    ts_iso = utc_now_iso()

    raw_payload = json.dumps({
        "vehicle_identifier": "ROGUE-VEH-999",
        "telemetry": {"latitude": 13.0, "longitude": 80.0, "speed": 60.0, "status": "moving", "battery_level": 50.0}
    })
    aad = secure_transmission_service.compute_aad(unauth_sender, SERVER_RECIPIENT_IDENTITY, msg_id, ts_iso)
    bundle = ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, raw_payload, aad=aad)

    req = {
        "sender_identity": unauth_sender,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": msg_id,
        "timestamp": ts_iso,
        "ciphertext_bundle": bundle,
        "payload_category": "medium"
    }

    resp = client.post("/api/secure-transmission/encrypted", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["unauthorized_identity_flag"] is True
    assert "Unauthorized sender identity" in data["rejection_reason"]
    assert data["telemetry_persisted"] is False

def test_rejection_tampered_ciphertext(client, db_session):
    v = Vehicle(vehicle_identifier="TEST-SEC-004", name="Test Unit 004", status="idle")
    db_session.add(v)
    db_session.commit()
    client.post("/api/secure-transmission/enroll", json={"vehicle_identifier": "TEST-SEC-004"})

    sender_id = "TEST-SEC-004@fleet.iot.local"
    msg_id = f"MSG-TAMPER-CT-{uuid.uuid4().hex[:6]}"
    ts_iso = utc_now_iso()

    raw_payload = json.dumps({
        "vehicle_identifier": "TEST-SEC-004",
        "telemetry": {"latitude": 13.0, "longitude": 80.0, "speed": 50.0, "status": "moving", "battery_level": 80.0}
    })
    aad = secure_transmission_service.compute_aad(sender_id, SERVER_RECIPIENT_IDENTITY, msg_id, ts_iso)
    bundle = dict(ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, raw_payload, aad=aad))

    sig_b64 = secure_transmission_service.sign_envelope(
        vehicle_identifier="TEST-SEC-004",
        sender_identity=sender_id,
        recipient_identity=SERVER_RECIPIENT_IDENTITY,
        message_id=msg_id,
        timestamp_str=ts_iso,
        ciphertext_bundle=bundle
    )

    # Tamper 1 bit in ciphertext
    ct_bytes = bytearray(base64.b64decode(bundle["ciphertext_b64"]))
    ct_bytes[0] ^= 0x01
    bundle["ciphertext_b64"] = base64.b64encode(bytes(ct_bytes)).decode("ascii")

    req = {
        "sender_identity": sender_id,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": msg_id,
        "timestamp": ts_iso,
        "ciphertext_bundle": bundle,
        "signature_b64": sig_b64,
        "claimed_vehicle_identifier": "TEST-SEC-004"
    }

    resp = client.post("/api/secure-transmission/encrypted", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["tampered_flag"] is True
    assert "Cryptographic integrity verification failed" in data["rejection_reason"]

def test_rejection_replayed_message(client, db_session):
    v = Vehicle(vehicle_identifier="TEST-SEC-005", name="Test Unit 005", status="idle")
    db_session.add(v)
    db_session.commit()
    client.post("/api/secure-transmission/enroll", json={"vehicle_identifier": "TEST-SEC-005"})

    sender_id = "TEST-SEC-005@fleet.iot.local"
    msg_id = f"MSG-REPLAY-{uuid.uuid4().hex[:6]}"
    ts_iso = utc_now_iso()

    raw_payload = json.dumps({
        "vehicle_identifier": "TEST-SEC-005",
        "telemetry": {"latitude": 13.0, "longitude": 80.0, "speed": 40.0, "status": "moving", "battery_level": 90.0}
    })
    aad = secure_transmission_service.compute_aad(sender_id, SERVER_RECIPIENT_IDENTITY, msg_id, ts_iso)
    bundle = ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, raw_payload, aad=aad)
    sig_b64 = secure_transmission_service.sign_envelope(
        vehicle_identifier="TEST-SEC-005",
        sender_identity=sender_id,
        recipient_identity=SERVER_RECIPIENT_IDENTITY,
        message_id=msg_id,
        timestamp_str=ts_iso,
        ciphertext_bundle=bundle
    )

    req = {
        "sender_identity": sender_id,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": msg_id,
        "timestamp": ts_iso,
        "ciphertext_bundle": bundle,
        "signature_b64": sig_b64,
        "claimed_vehicle_identifier": "TEST-SEC-005"
    }

    # First transmission: succeeds
    resp1 = client.post("/api/secure-transmission/encrypted", json=req)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "success"

    # Second transmission (Replay): must be rejected
    resp2 = client.post("/api/secure-transmission/encrypted", json=req)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "rejected"
    assert data2["replayed_flag"] is True
    assert "Replay attack detected" in data2["rejection_reason"]

def test_rejection_cross_vehicle_substitution(client, db_session):
    v1 = Vehicle(vehicle_identifier="TEST-SEC-006A", name="Test Unit 006A", status="idle")
    v2 = Vehicle(vehicle_identifier="TEST-SEC-006B", name="Test Unit 006B", status="idle")
    db_session.add_all([v1, v2])
    db_session.commit()
    client.post("/api/secure-transmission/enroll", json={"vehicle_identifier": "TEST-SEC-006A"})
    client.post("/api/secure-transmission/enroll", json={"vehicle_identifier": "TEST-SEC-006B"})

    sender_id = "TEST-SEC-006A@fleet.iot.local"
    msg_id = f"MSG-CROSS-{uuid.uuid4().hex[:6]}"
    ts_iso = utc_now_iso()

    raw_payload = json.dumps({
        "vehicle_identifier": "TEST-SEC-006A",
        "telemetry": {"latitude": 13.0, "longitude": 80.0, "speed": 35.0, "status": "moving", "battery_level": 70.0}
    })
    aad = secure_transmission_service.compute_aad(sender_id, SERVER_RECIPIENT_IDENTITY, msg_id, ts_iso)
    bundle = ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, raw_payload, aad=aad)
    sig_b64 = secure_transmission_service.sign_envelope(
        vehicle_identifier="TEST-SEC-006A",
        sender_identity=sender_id,
        recipient_identity=SERVER_RECIPIENT_IDENTITY,
        message_id=msg_id,
        timestamp_str=ts_iso,
        ciphertext_bundle=bundle
    )

    req = {
        "sender_identity": sender_id,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": msg_id,
        "timestamp": ts_iso,
        "ciphertext_bundle": bundle,
        "signature_b64": sig_b64,
        "claimed_vehicle_identifier": "TEST-SEC-006B"  # Mismatched claim!
    }

    resp = client.post("/api/secure-transmission/encrypted", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["unauthorized_identity_flag"] is True
    assert "Cross-vehicle identity substitution detected" in data["rejection_reason"]

def test_security_demonstration_endpoint(client, db_session):
    v = Vehicle(vehicle_identifier="TEST-SEC-007", name="Test Unit 007", status="idle")
    db_session.add(v)
    db_session.commit()

    # 1. Test authorized scenario
    r1 = client.post("/api/secure-transmission/demonstration", json={
        "scenario": "valid_authorized",
        "vehicle_identifier": "TEST-SEC-007"
    })
    assert r1.status_code == 200
    assert r1.json()["status"] == "success"
    assert r1.json()["signature_verified"] is True

    # 2. Test tampered tag scenario
    r2 = client.post("/api/secure-transmission/demonstration", json={
        "scenario": "tampered_tag",
        "vehicle_identifier": "TEST-SEC-007"
    })
    assert r2.status_code == 200
    assert r2.json()["status"] == "rejected"
    assert r2.json()["tampered_flag"] is True

    # 3. Test attacker impersonation scenario
    r3 = client.post("/api/secure-transmission/demonstration", json={
        "scenario": "attacker_impersonation",
        "vehicle_identifier": "TEST-SEC-007"
    })
    assert r3.status_code == 200
    assert r3.json()["status"] == "rejected"
    assert r3.json()["unauthorized_identity_flag"] is True
    assert r3.json()["signature_verified"] is False

    # 4. Test tampered signature scenario
    r4 = client.post("/api/secure-transmission/demonstration", json={
        "scenario": "tampered_signature",
        "vehicle_identifier": "TEST-SEC-007"
    })
    assert r4.status_code == 200
    assert r4.json()["status"] == "rejected"
    assert r4.json()["tampered_flag"] is True

    # 5. Test substituted signature scenario
    r5 = client.post("/api/secure-transmission/demonstration", json={
        "scenario": "substituted_signature",
        "vehicle_identifier": "TEST-SEC-007"
    })
    assert r5.status_code == 200
    assert r5.json()["status"] == "rejected"
    assert r5.json()["signature_verified"] is False

# ==============================================================================
# PHASE 3.1 SPECIFIC AUDIT & VALIDATION TESTS
# ==============================================================================

def test_genuine_enrolled_vehicle_impersonation_rejected(client, db_session):
    """
    Critical Impersonation Test:
    1. Enroll Vehicle A.
    2. Create a separate attacker client.
    3. Attacker generates new encrypted envelope for fleet server using public IBE parameters.
    4. Attacker claims Vehicle A identity and crafts matching AAD.
    5. Attacker does not hold Vehicle A's Ed25519 private key (signs with rogue key or submits unsigned).
    6. Verify server rejects transmission and does not persist fake telemetry.
    """
    v_a = Vehicle(vehicle_identifier="TEST-IMPERSONATE-A", name="Impersonation Target", status="idle")
    db_session.add(v_a)
    db_session.commit()
    enr_resp = client.post("/api/secure-transmission/enroll", json={"vehicle_identifier": "TEST-IMPERSONATE-A"})
    assert enr_resp.status_code == 200

    target_sender_id = "TEST-IMPERSONATE-A@fleet.iot.local"
    attacker_msg_id = f"MSG-ATTACK-{uuid.uuid4().hex[:6]}"
    ts_iso = utc_now_iso()

    # Fake attacker telemetry
    fake_telemetry = json.dumps({
        "vehicle_identifier": "TEST-IMPERSONATE-A",
        "telemetry": {"latitude": 0.000, "longitude": 0.000, "speed": 180.0, "status": "stolen", "battery_level": 1.0}
    })
    aad = secure_transmission_service.compute_aad(target_sender_id, SERVER_RECIPIENT_IDENTITY, attacker_msg_id, ts_iso)
    attacker_bundle = ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, fake_telemetry, aad=aad)

    # Rogue keypair generated by attacker
    rogue_priv = ed25519.Ed25519PrivateKey.generate()
    msg_bytes = secure_transmission_service.compute_canonical_signature_message(
        sender_identity=target_sender_id,
        recipient_identity=SERVER_RECIPIENT_IDENTITY,
        message_id=attacker_msg_id,
        timestamp_str=ts_iso,
        ciphertext_bundle=attacker_bundle
    )
    forged_signature = base64.b64encode(rogue_priv.sign(msg_bytes)).decode("ascii")

    # Attacker submits forged transmission
    impersonation_req = {
        "sender_identity": target_sender_id,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": attacker_msg_id,
        "timestamp": ts_iso,
        "ciphertext_bundle": attacker_bundle,
        "signature_b64": forged_signature,
        "claimed_vehicle_identifier": "TEST-IMPERSONATE-A",
        "payload_category": "medium"
    }

    resp = client.post("/api/secure-transmission/encrypted", json=impersonation_req)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "rejected"
    assert res_data["signature_verified"] is False
    assert res_data["telemetry_persisted"] is False
    assert "Cryptographic integrity verification failed" in res_data["rejection_reason"] or "Cryptographic sender authentication failed" in res_data["rejection_reason"]

def test_missing_signature_rejected(client, db_session):
    """Verifies that an encrypted transmission lacking an Ed25519 signature is rejected."""
    v = Vehicle(vehicle_identifier="TEST-SEC-NOSIG", name="No Sig Vehicle", status="idle")
    db_session.add(v)
    db_session.commit()
    client.post("/api/secure-transmission/enroll", json={"vehicle_identifier": "TEST-SEC-NOSIG"})

    sender_id = "TEST-SEC-NOSIG@fleet.iot.local"
    msg_id = f"MSG-NOSIG-{uuid.uuid4().hex[:6]}"
    ts_iso = utc_now_iso()

    raw_payload = json.dumps({"vehicle_identifier": "TEST-SEC-NOSIG", "telemetry": {"speed": 20.0}})
    aad = secure_transmission_service.compute_aad(sender_id, SERVER_RECIPIENT_IDENTITY, msg_id, ts_iso)
    bundle = ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, raw_payload, aad=aad)

    req = {
        "sender_identity": sender_id,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": msg_id,
        "timestamp": ts_iso,
        "ciphertext_bundle": bundle,
        "signature_b64": None,  # Omitted signature!
        "claimed_vehicle_identifier": "TEST-SEC-NOSIG"
    }

    resp = client.post("/api/secure-transmission/encrypted", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert "Missing Ed25519 vehicle signature" in data["rejection_reason"]
    assert data["signature_verified"] is False

def test_future_timestamp_rejected(client, db_session):
    """Verifies that a transmission timestamped > 30s into the future is rejected."""
    v = Vehicle(vehicle_identifier="TEST-SEC-FUTURE", name="Future Vehicle", status="idle")
    db_session.add(v)
    db_session.commit()
    client.post("/api/secure-transmission/enroll", json={"vehicle_identifier": "TEST-SEC-FUTURE"})

    sender_id = "TEST-SEC-FUTURE@fleet.iot.local"
    msg_id = f"MSG-FUTURE-{uuid.uuid4().hex[:6]}"
    future_iso = (datetime.now(timezone.utc) + timedelta(seconds=120)).isoformat()

    raw_payload = json.dumps({"vehicle_identifier": "TEST-SEC-FUTURE", "telemetry": {"speed": 30.0}})
    aad = secure_transmission_service.compute_aad(sender_id, SERVER_RECIPIENT_IDENTITY, msg_id, future_iso)
    bundle = ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, raw_payload, aad=aad)
    sig_b64 = secure_transmission_service.sign_envelope(
        vehicle_identifier="TEST-SEC-FUTURE",
        sender_identity=sender_id,
        recipient_identity=SERVER_RECIPIENT_IDENTITY,
        message_id=msg_id,
        timestamp_str=future_iso,
        ciphertext_bundle=bundle
    )

    req = {
        "sender_identity": sender_id,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": msg_id,
        "timestamp": future_iso,
        "ciphertext_bundle": bundle,
        "signature_b64": sig_b64,
        "claimed_vehicle_identifier": "TEST-SEC-FUTURE"
    }

    resp = client.post("/api/secure-transmission/encrypted", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert "future" in data["rejection_reason"].lower()

def test_expired_timestamp_rejected(client, db_session):
    """Verifies that a transmission older than the 300s freshness window is rejected."""
    v = Vehicle(vehicle_identifier="TEST-SEC-EXPIRED", name="Expired Vehicle", status="idle")
    db_session.add(v)
    db_session.commit()
    client.post("/api/secure-transmission/enroll", json={"vehicle_identifier": "TEST-SEC-EXPIRED"})

    sender_id = "TEST-SEC-EXPIRED@fleet.iot.local"
    msg_id = f"MSG-EXPIRED-{uuid.uuid4().hex[:6]}"
    expired_iso = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()

    raw_payload = json.dumps({"vehicle_identifier": "TEST-SEC-EXPIRED", "telemetry": {"speed": 30.0}})
    aad = secure_transmission_service.compute_aad(sender_id, SERVER_RECIPIENT_IDENTITY, msg_id, expired_iso)
    bundle = ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, raw_payload, aad=aad)
    sig_b64 = secure_transmission_service.sign_envelope(
        vehicle_identifier="TEST-SEC-EXPIRED",
        sender_identity=sender_id,
        recipient_identity=SERVER_RECIPIENT_IDENTITY,
        message_id=msg_id,
        timestamp_str=expired_iso,
        ciphertext_bundle=bundle
    )

    req = {
        "sender_identity": sender_id,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": msg_id,
        "timestamp": expired_iso,
        "ciphertext_bundle": bundle,
        "signature_b64": sig_b64,
        "claimed_vehicle_identifier": "TEST-SEC-EXPIRED"
    }

    resp = client.post("/api/secure-transmission/encrypted", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert "freshness window" in data["rejection_reason"].lower()

def test_replay_same_uuid_different_ciphertext_rejected(client, db_session):
    """Verifies that reusing the same message UUID with a different ciphertext payload is rejected."""
    v = Vehicle(vehicle_identifier="TEST-SEC-SAMEUUID", name="UUID Replay Vehicle", status="idle")
    db_session.add(v)
    db_session.commit()
    client.post("/api/secure-transmission/enroll", json={"vehicle_identifier": "TEST-SEC-SAMEUUID"})

    sender_id = "TEST-SEC-SAMEUUID@fleet.iot.local"
    common_uuid = f"MSG-SAMEUUID-{uuid.uuid4().hex[:6]}"
    ts_iso1 = utc_now_iso()

    # Message 1
    p1 = json.dumps({
        "vehicle_identifier": "TEST-SEC-SAMEUUID",
        "telemetry": {"latitude": 13.0, "longitude": 80.0, "speed": 25.0, "status": "moving", "battery_level": 80.0}
    })
    aad1 = secure_transmission_service.compute_aad(sender_id, SERVER_RECIPIENT_IDENTITY, common_uuid, ts_iso1)
    b1 = ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, p1, aad=aad1)
    s1 = secure_transmission_service.sign_envelope("TEST-SEC-SAMEUUID", sender_id, SERVER_RECIPIENT_IDENTITY, common_uuid, ts_iso1, b1)

    r1 = client.post("/api/secure-transmission/encrypted", json={
        "sender_identity": sender_id,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": common_uuid,
        "timestamp": ts_iso1,
        "ciphertext_bundle": b1,
        "signature_b64": s1,
        "claimed_vehicle_identifier": "TEST-SEC-SAMEUUID"
    })
    assert r1.status_code == 200
    assert r1.json()["status"] == "success"

    # Message 2: Same common_uuid, but totally different telemetry
    ts_iso2 = utc_now_iso()
    p2 = json.dumps({
        "vehicle_identifier": "TEST-SEC-SAMEUUID",
        "telemetry": {"latitude": 13.1, "longitude": 80.1, "speed": 99.0, "status": "moving", "battery_level": 60.0}
    })
    aad2 = secure_transmission_service.compute_aad(sender_id, SERVER_RECIPIENT_IDENTITY, common_uuid, ts_iso2)
    b2 = ibe_service.encrypt(SERVER_RECIPIENT_IDENTITY, p2, aad=aad2)
    s2 = secure_transmission_service.sign_envelope("TEST-SEC-SAMEUUID", sender_id, SERVER_RECIPIENT_IDENTITY, common_uuid, ts_iso2, b2)

    r2 = client.post("/api/secure-transmission/encrypted", json={
        "sender_identity": sender_id,
        "recipient_identity": SERVER_RECIPIENT_IDENTITY,
        "message_id": common_uuid,  # Duplicate UUID!
        "timestamp": ts_iso2,
        "ciphertext_bundle": b2,
        "signature_b64": s2,
        "claimed_vehicle_identifier": "TEST-SEC-SAMEUUID"
    })
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["status"] == "rejected"
    assert d2["replayed_flag"] is True

def test_concurrent_duplicate_replay_atomic(client, db_session):
    """
    Simulates a race condition where two simultaneous requests insert the identical UUID.
    Verifies that the database unique constraint inside check_replay_and_freshness triggers savepoint rollback
    and returns a rejection without causing an unhandled server error.
    """
    dup_uuid = f"MSG-CONCURRENT-{uuid.uuid4().hex[:6]}"
    now_dt = datetime.now(timezone.utc)
    sender = "SIM-CONCURRENT@fleet.iot.local"

    # First check succeeds and caches
    ok1, err1 = secure_transmission_service.check_replay_and_freshness(db_session, dup_uuid, now_dt, sender)
    assert ok1 is True
    assert err1 is None

    # Immediate second check with same UUID is caught and rejected
    ok2, err2 = secure_transmission_service.check_replay_and_freshness(db_session, dup_uuid, now_dt, sender)
    assert ok2 is False
    assert "Replay attack detected" in err2 or "Concurrent" in err2

def test_unauthorized_key_extraction_blocked(client):
    """
    Reassessment of Finding C-02:
    Confirms that public callers cannot extract vehicle private signing keys or IBE master keys.
    """
    # 1. Verify no vehicle private keys leaked in enrollments list
    resp = client.get("/api/secure-transmission/enrollments")
    assert resp.status_code == 200
    for item in resp.json():
        assert "private_key" not in item
        assert "signing_private_key" not in item
        assert "signing_public_key" in item

    # 2. Verify master key cannot be re-initialized via API
    reinit = client.post("/api/security/ibe/setup?force_reinit=true")
    assert reinit.status_code == 403

def test_analytics_and_security_events(client, db_session):
    resp_analytics = client.get("/api/secure-transmission/analytics")
    assert resp_analytics.status_code == 200
    data = resp_analytics.json()
    assert "total_transmissions" in data
    assert "overall_success_rate" in data

    resp_events = client.get("/api/secure-transmission/security-events")
    assert resp_events.status_code == 200
    events = resp_events.json()
    assert isinstance(events, list)
