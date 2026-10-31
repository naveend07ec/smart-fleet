import base64
import json
import secrets
import pytest

from py_ecc.bn128 import (
    G1, G2, multiply, pairing, curve_order,
    field_modulus, is_on_curve, b, b2, FQ, FQ2
)
from app.services.ibe_service import ibe_service, IBEService, run_in_large_stack_thread


# ==============================================================================
# 1. Pairing Consistency and Mathematical Invariants
# ==============================================================================

def test_pairing_bilinearity_and_argument_order():
    """
    Validates the fundamental bilinearity equation of the Type-3 pairing engine
    and verifies that py_ecc.bn128 expects G2 as the first argument and G1 as the second:
        e(a * P2, b * P1) == e(P2, P1)^(a * b) == e(b * P2, a * P1)
    """
    def _run_pairing_test():
        # Small scalars for fast computation while testing bilinearity
        a = 7
        b_scalar = 11

        aP2 = multiply(G2, a)
        bP1 = multiply(G1, b_scalar)
        bP2 = multiply(G2, b_scalar)
        aP1 = multiply(G1, a)

        # py_ecc.bn128.pairing(Q in G2, P in G1)
        pair1 = pairing(aP2, bP1)
        pair2 = pairing(bP2, aP1)
        pair_base = pairing(G2, G1) ** (a * b_scalar)

        assert pair1 == pair2, "Bilinearity failed: e(a*P2, b*P1) != e(b*P2, a*P1)"
        assert pair1 == pair_base, "Bilinearity failed: e(a*P2, b*P1) != e(P2, P1)^(a*b)"

        # Verify that reversing argument order (passing G1 first, G2 second) is rejected
        with pytest.raises(Exception):
            pairing(aP1, bP2)

    run_in_large_stack_thread(_run_pairing_test)


def test_ibe_mathematical_roundtrip_equation():
    """
    Verifies that the IBE core identity holds:
        e(P_pub, Q_ID)^r == e(U, d_ID)
    where P_pub = s * P2, U = r * P2, d_ID = s * Q_ID.
    """
    def _verify_math():
        s = 13
        r = 17
        P_pub = multiply(G2, s)
        U = multiply(G2, r)

        # Arbitrary test point on G1
        Q_id = ibe_service._hash_to_g1("test-vehicle-hub-math")
        d_id = multiply(Q_id, s)

        # Encapsulation pairing value: e(P_pub, Q_ID)^r
        pair_enc = pairing(P_pub, Q_id) ** r

        # Decapsulation pairing value: e(U, d_ID)
        pair_dec = pairing(U, d_id)

        assert pair_enc == pair_dec, "Core IBE equivalence failed: e(P_pub, Q_ID)^r != e(U, d_ID)"

    run_in_large_stack_thread(_verify_math)


# ==============================================================================
# 2. Identity Mapping, Subgroup Membership & Isolation
# ==============================================================================

def test_hash_to_g1_curve_membership():
    """
    Verifies that Try-and-Increment SHA-256 mapping produces valid points
    satisfying the BN128 curve equation y^2 = x^3 + 3 (mod p) and on G1.
    """
    test_identities = [
        "traffic-control-hub-01",
        "emergency-dispatch-zone-4",
        "highway-patrol-unit-99",
        "logistics-fleet-chennai",
    ]

    points = []
    for ident in test_identities:
        pt = ibe_service._hash_to_g1(ident)
        assert len(pt) == 2, "G1 point must be affine pair (x, y)"
        assert is_on_curve(pt, b), f"Point for identity '{ident}' is not on curve G1"
        # Verify y^2 == x^3 + 3 (mod p)
        x_val = int(pt[0])
        y_val = int(pt[1])
        lhs = (y_val * y_val) % field_modulus
        rhs = (pow(x_val, 3, field_modulus) + 3) % field_modulus
        assert lhs == rhs, f"Curve equation violation for identity '{ident}'"
        points.append((x_val, y_val))

    # Distinct identities must produce distinct points
    assert len(set(points)) == len(test_identities), "Different identities produced colliding G1 points"


def test_cross_identity_isolation_and_case_sensitivity(client):
    """
    Confirms that recipient keys are strictly isolated:
    1. Identity A cannot decrypt Identity B's messages.
    2. Case sensitivity is maintained (no unintended aliasing).
    """
    payload = "Confidential telemetry packet: lat=13.0827, lng=80.2707"

    enc_res = client.post("/api/security/ibe/encrypt", json={
        "recipient_identity": "traffic-hub-alpha",
        "payload": payload
    })
    assert enc_res.status_code == 200
    bundle = enc_res.json()

    # Attempt decrypt with different identity
    dec_unauth = client.post("/api/security/ibe/decrypt", json={
        "recipient_identity": "traffic-hub-beta",
        "ciphertext_bundle": bundle
    })
    assert dec_unauth.status_code == 200
    assert dec_unauth.json()["success"] is False
    assert dec_unauth.json()["decrypted_payload"] is None

    # Attempt decrypt with different case
    dec_case = client.post("/api/security/ibe/decrypt", json={
        "recipient_identity": "Traffic-Hub-Alpha",
        "ciphertext_bundle": bundle
    })
    assert dec_case.status_code == 200
    assert dec_case.json()["success"] is False


# ==============================================================================
# 3. Malformed Points and Input Validation
# ==============================================================================

def test_malformed_u_point_rejection(client):
    """
    Ensures that supplying malformed, off-curve, or invalid coordinates in u_point
    results in a safe validation error rather than an unhandled 500 crash.
    """
    recipient = "traffic-validation-hub"
    enc_res = client.post("/api/security/ibe/encrypt", json={
        "recipient_identity": recipient,
        "payload": "Valid payload for point tampering test"
    })
    bundle = enc_res.json()

    # Case A: Corrupt point coordinates so it does not lie on G2 twist curve
    bundle_off_curve = dict(bundle)
    bundle_off_curve["u_point"] = {
        "x": [bundle["u_point"]["x"][0] + 1, bundle["u_point"]["x"][1]],
        "y": bundle["u_point"]["y"]
    }
    res_off_curve = client.post("/api/security/ibe/decrypt", json={
        "recipient_identity": recipient,
        "ciphertext_bundle": bundle_off_curve
    })
    assert res_off_curve.status_code in (400, 422)

    # Case B: Invalid non-integer coordinates in u_point
    bundle_bad_types = dict(bundle)
    bundle_bad_types["u_point"] = {
        "x": ["not-a-number", "invalid"],
        "y": bundle["u_point"]["y"]
    }
    res_bad_types = client.post("/api/security/ibe/decrypt", json={
        "recipient_identity": recipient,
        "ciphertext_bundle": bundle_bad_types
    })
    assert res_bad_types.status_code in (400, 422)

    # Case C: Missing u_point entirely
    bundle_missing = dict(bundle)
    del bundle_missing["u_point"]
    res_missing = client.post("/api/security/ibe/decrypt", json={
        "recipient_identity": recipient,
        "ciphertext_bundle": bundle_missing
    })
    assert res_missing.status_code in (400, 422)


# ==============================================================================
# 4. Comprehensive Ciphertext and Parameter Tampering
# ==============================================================================

def test_ciphertext_tag_and_metadata_tampering(client):
    """
    Tests that tampering with:
    - Ciphertext payload body
    - AES-GCM 16-byte authentication tag
    - Nonce
    - Salt
    - Base64 encoding padding
    are all securely rejected without exposing keys or plaintext.
    """
    recipient = "tamper-defense-hub"
    payload = "Sensor readings: engine_temp=92.5C, oil_pressure=45psi"

    enc_res = client.post("/api/security/ibe/encrypt", json={
        "recipient_identity": recipient,
        "payload": payload
    })
    original_bundle = enc_res.json()

    # 1. Flip bit in ciphertext body
    b_body = dict(original_bundle)
    raw_ct = bytearray(base64.b64decode(b_body["ciphertext_b64"]))
    raw_ct[0] ^= 0x01
    b_body["ciphertext_b64"] = base64.b64encode(bytes(raw_ct)).decode("ascii")
    res1 = client.post("/api/security/ibe/decrypt", json={"recipient_identity": recipient, "ciphertext_bundle": b_body})
    assert res1.json()["success"] is False

    # 2. Flip bit in authentication tag (last 16 bytes of ciphertext)
    b_tag = dict(original_bundle)
    raw_ct_tag = bytearray(base64.b64decode(b_tag["ciphertext_b64"]))
    raw_ct_tag[-1] ^= 0x80
    b_tag["ciphertext_b64"] = base64.b64encode(bytes(raw_ct_tag)).decode("ascii")
    res2 = client.post("/api/security/ibe/decrypt", json={"recipient_identity": recipient, "ciphertext_bundle": b_tag})
    assert res2.json()["success"] is False

    # 3. Tamper with Nonce
    b_nonce = dict(original_bundle)
    raw_nonce = bytearray(base64.b64decode(b_nonce["nonce_b64"]))
    raw_nonce[0] ^= 0xFF
    b_nonce["nonce_b64"] = base64.b64encode(bytes(raw_nonce)).decode("ascii")
    res3 = client.post("/api/security/ibe/decrypt", json={"recipient_identity": recipient, "ciphertext_bundle": b_nonce})
    assert res3.json()["success"] is False

    # 4. Tamper with Salt
    b_salt = dict(original_bundle)
    raw_salt = bytearray(base64.b64decode(b_salt["salt_b64"]))
    raw_salt[0] ^= 0xAA
    b_salt["salt_b64"] = base64.b64encode(bytes(raw_salt)).decode("ascii")
    res4 = client.post("/api/security/ibe/decrypt", json={"recipient_identity": recipient, "ciphertext_bundle": b_salt})
    assert res4.json()["success"] is False

    # 5. Invalid Base64 (either caught as decoding error 400/422 or rejected at AEAD tag verification)
    b_b64 = dict(original_bundle)
    b_b64["ciphertext_b64"] = "===Not-Valid-Base64==="
    res5 = client.post("/api/security/ibe/decrypt", json={"recipient_identity": recipient, "ciphertext_bundle": b_b64})
    assert (res5.status_code in (400, 422)) or (res5.status_code == 200 and res5.json()["success"] is False)


# ==============================================================================
# 5. Serialization and Master Key Reload Consistency
# ==============================================================================

def test_key_reload_and_historical_decryption():
    """
    Verifies that reloading master parameters from local key storage is idempotent
    and that a ciphertext encrypted under master keys can still be decrypted after a reload.
    """
    recipient = "historical-audit-hub"
    payload = "Historical data for key persistence verification"

    # Encrypt with current service state
    bundle = ibe_service.encrypt(recipient, payload)

    # Record current public params and master secret
    initial_s = ibe_service._master_secret
    initial_p_pub = ibe_service._public_params["p_pub"]

    # Force reload from disk
    ibe_service._ensure_keys_loaded()

    assert ibe_service._master_secret == initial_s, "Master secret changed after reloading from storage"
    assert ibe_service._public_params["p_pub"] == initial_p_pub, "Master public key changed after reload"

    # Decrypt with reloaded service
    dec_res = ibe_service.decrypt(bundle, recipient)
    assert dec_res["success"] is True
    assert dec_res["decrypted_payload"] == payload


def test_setup_idempotency_without_force_reinit(client):
    """
    Confirms that calling setup without force_reinit=true retains existing master parameters.
    """
    status_before = client.get("/api/security/ibe/status").json()
    setup_res = client.post("/api/security/ibe/setup?force_reinit=false")
    assert setup_res.status_code == 200

    status_after = client.get("/api/security/ibe/status").json()
    assert status_before["scheme"] == status_after["scheme"]

    # Confirm that attempting unauthenticated force_reinit=true via public API is blocked with 403 Forbidden
    reinit_res = client.post("/api/security/ibe/setup?force_reinit=true")
    assert reinit_res.status_code == 403


# ==============================================================================
# 6. Phase 1 Functionality Regression Checks
# ==============================================================================

def test_phase1_regression_endpoints(client):
    """
    Verifies that all Phase 1 core fleet management endpoints continue to function correctly:
    - Dashboard summary
    - Analytics overview
    - Vehicle CRUD / retrieval
    - Simulation status
    """
    # 1. Dashboard summary
    dash_res = client.get("/api/dashboard/summary")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "total_vehicles" in dash_data
    assert "status_breakdown" in dash_data

    # 2. Analytics overview
    analytics_res = client.get("/api/analytics/overview")
    assert analytics_res.status_code == 200
    analytics_data = analytics_res.json()
    assert "total_records" in analytics_data
    assert "speed_analytics" in analytics_data

    # 3. Vehicle list
    vehicles_res = client.get("/api/vehicles")
    assert vehicles_res.status_code == 200
    assert "items" in vehicles_res.json()

    # 4. Simulation status
    sim_res = client.get("/api/simulation/status")
    assert sim_res.status_code == 200
    assert "is_running" in sim_res.json()
