import os
import re
import json
import base64
import time
import secrets
import hashlib
import threading
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone
import uuid

from py_ecc import bn128
from py_ecc.bn128 import (
    G1, G2, multiply, pairing, curve_order,
    field_modulus, is_on_curve, b, FQ, FQ2
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models.ibe_experiment import IBEExperiment

# Ensure thread stack size accommodates pure-python recursive pairing on Windows
threading.stack_size(8 * 1024 * 1024)

SCHEME_NAME = "Boneh-Franklin-BN128-AES256GCM"
KEY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".ibe_keys")

def run_in_large_stack_thread(func, *args, **kwargs):
    """Executes a function in a thread with 8MB stack to guarantee safe BN128 pairings on Windows."""
    result = []
    error = []

    def target():
        try:
            res = func(*args, **kwargs)
            result.append(res)
        except Exception as e:
            error.append(e)

    th = threading.Thread(target=target)
    th.start()
    th.join()

    if error:
        raise error[0]
    return result[0]


class IBEService:
    _instance: Optional["IBEService"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(IBEService, cls).__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self):
        self._master_secret: Optional[int] = None
        self._public_params: Optional[Dict[str, Any]] = None
        self._key_lock = threading.Lock()
        self._ensure_keys_loaded()

    def _ensure_keys_loaded(self):
        """Loads master keys from local storage, or generates new ones if not present."""
        os.makedirs(KEY_DIR, exist_ok=True)
        secret_path = os.path.join(KEY_DIR, "master_secret.key")
        public_path = os.path.join(KEY_DIR, "master_public.json")

        if os.path.exists(secret_path) and os.path.exists(public_path):
            try:
                with open(secret_path, "r", encoding="utf-8") as f:
                    self._master_secret = int(f.read().strip())
                with open(public_path, "r", encoding="utf-8") as f:
                    self._public_params = json.load(f)
                return
            except Exception:
                pass  # Regenerate if corrupted

        self._generate_master_keys(secret_path, public_path)

    def _generate_master_keys(self, secret_path: str, public_path: str):
        # 1. Master secret scalar s in [2, curve_order - 1]
        s = secrets.randbelow(curve_order - 2) + 2
        # 2. Master public parameter P_pub = s * G2 (in G2)
        P_pub = multiply(G2, s)

        # Serialize P_pub coordinates
        # G2 point format in py_ecc is ((x_real, x_imag), (y_real, y_imag))
        p_pub_serialized = {
            "x": [int(P_pub[0].coeffs[0]), int(P_pub[0].coeffs[1])],
            "y": [int(P_pub[1].coeffs[0]), int(P_pub[1].coeffs[1])],
        }

        self._master_secret = s
        self._public_params = {
            "scheme": SCHEME_NAME,
            "curve": "BN128 (alt_bn128)",
            "curve_order": str(curve_order),
            "field_modulus": str(field_modulus),
            "p_pub": p_pub_serialized,
            "initialized_at": datetime.now(timezone.utc).isoformat()
        }

        with open(secret_path, "w", encoding="utf-8") as f:
            f.write(str(s))
        with open(public_path, "w", encoding="utf-8") as f:
            json.dump(self._public_params, f, indent=2)

    def get_status(self) -> Dict[str, Any]:
        with self._key_lock:
            is_ready = self._master_secret is not None and self._public_params is not None
            return {
                "status": "ready" if is_ready else "uninitialized",
                "scheme": SCHEME_NAME,
                "curve": "BN128 (Barreto-Naehrig)",
                "pairing_type": "Asymmetric Optimal Ate (Type 3)",
                "symmetric_cipher": "AES-256-GCM",
                "key_derivation": "HKDF-SHA256",
                "public_params_available": is_ready,
                "pkg_trust_model": (
                    "Centralized PKG with key escrow limitation: The PKG holds master secret s "
                    "and can theoretically derive private keys for any recipient identity."
                ),
                "is_simulated_iot_layer": True
            }

    def setup(self, force_reinit: bool = False) -> Dict[str, Any]:
        """Setup / Re-initialization of master public parameters and master secret."""
        with self._key_lock:
            secret_path = os.path.join(KEY_DIR, "master_secret.key")
            public_path = os.path.join(KEY_DIR, "master_public.json")
            if force_reinit or not os.path.exists(secret_path):
                self._generate_master_keys(secret_path, public_path)

            return {
                "message": "IBE master parameters initialized successfully.",
                "scheme": SCHEME_NAME,
                "curve": self._public_params["curve"],
                "p_pub": self._public_params["p_pub"],
                "initialized_at": self._public_params["initialized_at"]
            }

    @staticmethod
    def validate_identity(identity: str) -> str:
        """Validates recipient identity string format."""
        if not identity or not isinstance(identity, str):
            raise ValueError("Identity must be a non-empty string.")
        norm = identity.strip()
        if len(norm) < 3 or len(norm) > 100:
            raise ValueError(f"Identity length must be between 3 and 100 characters (got {len(norm)}).")
        if not re.match(r"^[a-zA-Z0-9_\-\.@]+$", norm):
            raise ValueError("Identity contains invalid characters. Allowed: alphanumeric, hyphens, dots, underscores, @.")
        return norm

    @staticmethod
    def _hash_to_g1(identity: str) -> Tuple[FQ, FQ]:
        """
        Maps arbitrary recipient identity string to a valid point Q_ID on G1 curve (y^2 = x^3 + 3).
        Uses deterministic Try-and-Increment with SHA-256.
        """
        counter = 0
        while True:
            digest = hashlib.sha256(f"IBE-HASH-G1:{identity}:{counter}".encode("utf-8")).digest()
            x_int = int.from_bytes(digest, "big") % field_modulus
            # y^2 = x^3 + 3 (mod p)
            y2 = (pow(x_int, 3, field_modulus) + 3) % field_modulus
            # Test quadratic residue (Euler's criterion: y2^((p-1)/2) == 1)
            if pow(y2, (field_modulus - 1) // 2, field_modulus) == 1:
                # Square root mod p: since p % 4 == 3, sqrt = y2^((p+1)/4) mod p
                y_int = pow(y2, (field_modulus + 1) // 4, field_modulus)
                pt = (FQ(x_int), FQ(y_int))
                if is_on_curve(pt, b):
                    return pt
            counter += 1

    def _get_master_p_pub_point(self) -> Tuple[FQ2, FQ2]:
        """Reconstructs P_pub point on G2."""
        raw = self._public_params["p_pub"]
        x_fq2 = FQ2(raw["x"])
        y_fq2 = FQ2(raw["y"])
        return (x_fq2, y_fq2)

    def extract_private_key(self, identity: str) -> Tuple[FQ, FQ]:
        """
        PKG component: Derives recipient private key d_ID = s * Q_ID in G1.
        Protected internal method — never exposed to unauthenticated public API callers.
        """
        valid_id = self.validate_identity(identity)
        with self._key_lock:
            if self._master_secret is None:
                raise RuntimeError("IBE system is not initialized.")
            s = self._master_secret

        Q_id = self._hash_to_g1(valid_id)
        d_id = multiply(Q_id, s)
        return d_id

    def encrypt(self, identity: str, payload: bytes | str, aad: Optional[bytes] = None) -> Dict[str, Any]:
        """
        Encrypts a telemetry payload for the specified recipient identity.
        Optionally binds Authenticated Associated Data (AAD) into AES-256-GCM.
        Returns serialized ciphertext bundle.
        """
        valid_id = self.validate_identity(identity)
        if isinstance(payload, str):
            payload_bytes = payload.encode("utf-8")
        else:
            payload_bytes = payload

        if len(payload_bytes) == 0:
            raise ValueError("Payload cannot be empty.")
        if len(payload_bytes) > 200 * 1024:
            raise ValueError("Payload exceeds maximum research size limit (200 KB).")

        return run_in_large_stack_thread(self._encrypt_internal, valid_id, payload_bytes, aad)

    def _encrypt_internal(self, identity: str, payload_bytes: bytes, aad: Optional[bytes] = None) -> Dict[str, Any]:
        start_time = time.perf_counter()

        # 1. Map identity to point Q_ID in G1
        Q_id = self._hash_to_g1(identity)

        # 2. Ephemeral scalar r in [2, curve_order - 1]
        r = secrets.randbelow(curve_order - 2) + 2
        # 3. Ephemeral public point U = r * G2 in G2
        U = multiply(G2, r)

        # 4. Compute pairing e(P_pub, Q_id) and shared secret g^r = e(P_pub, Q_id)^r
        P_pub = self._get_master_p_pub_point()
        pair_val = pairing(P_pub, Q_id)
        shared_pairing_elem = pair_val ** r

        # 5. Derive 256-bit AES key via HKDF-SHA256
        salt = secrets.token_bytes(16)
        pairing_bytes = str(shared_pairing_elem).encode("utf-8")
        kdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b"IBE-TELEMETRY-AES256GCM")
        aes_key = kdf.derive(pairing_bytes)

        # 6. Symmetric authenticated encryption
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(aes_key)
        # AESGCM.encrypt appends 16-byte tag to the ciphertext
        raw_ciphertext = aesgcm.encrypt(nonce, payload_bytes, aad)

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Serialize bundle
        u_serialized = {
            "x": [int(U[0].coeffs[0]), int(U[0].coeffs[1])],
            "y": [int(U[1].coeffs[0]), int(U[1].coeffs[1])],
        }

        bundle = {
            "version": "1.0",
            "scheme": SCHEME_NAME,
            "recipient_identity": identity,
            "u_point": u_serialized,
            "salt_b64": base64.b64encode(salt).decode("ascii"),
            "nonce_b64": base64.b64encode(nonce).decode("ascii"),
            "ciphertext_b64": base64.b64encode(raw_ciphertext).decode("ascii"),
            "payload_size_bytes": len(payload_bytes),
            "ciphertext_size_bytes": len(raw_ciphertext),
            "encryption_duration_ms": round(duration_ms, 2)
        }
        return bundle

    def decrypt(
        self,
        ciphertext_bundle: Dict[str, Any],
        recipient_identity: str,
        aad: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Decrypts a ciphertext bundle for a specific recipient identity using the matching private key.
        Optionally verifies Authenticated Associated Data (AAD) in AES-256-GCM.
        Rejects tampered ciphertexts and unauthorized identity keys with safe error responses.
        """
        valid_id = self.validate_identity(recipient_identity)
        return run_in_large_stack_thread(self._decrypt_internal, ciphertext_bundle, valid_id, aad)

    def _decrypt_internal(
        self,
        bundle: Dict[str, Any],
        recipient_identity: str,
        aad: Optional[bytes] = None
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()

        # Validation of bundle fields
        required_fields = ["u_point", "salt_b64", "nonce_b64", "ciphertext_b64"]
        for f in required_fields:
            if f not in bundle:
                raise ValueError(f"Malformed ciphertext bundle: missing field '{f}'.")

        try:
            salt = base64.b64decode(bundle["salt_b64"])
            nonce = base64.b64decode(bundle["nonce_b64"])
            raw_ciphertext = base64.b64decode(bundle["ciphertext_b64"])
            u_raw = bundle["u_point"]
            U = (FQ2(u_raw["x"]), FQ2(u_raw["y"]))
        except Exception as e:
            raise ValueError(f"Invalid Base64 or corrupted point formatting: {str(e)}")

        # Extract recipient's private key d_ID in G1
        d_id = self.extract_private_key(recipient_identity)

        # Compute pairing e(U, d_id)
        try:
            pair_val = pairing(U, d_id)
        except Exception as e:
            raise ValueError(f"Cryptographic pairing computation failed: {str(e)}")

        # Derive symmetric key via HKDF
        pairing_bytes = str(pair_val).encode("utf-8")
        kdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=b"IBE-TELEMETRY-AES256GCM")
        aes_key = kdf.derive(pairing_bytes)

        # Attempt authenticated decryption
        aesgcm = AESGCM(aes_key)
        try:
            decrypted_bytes = aesgcm.decrypt(nonce, raw_ciphertext, aad)
        except InvalidTag:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "success": False,
                "error": "Authentication tag verification failed (unauthorized identity key or corrupted ciphertext).",
                "decrypted_payload": None,
                "decryption_duration_ms": round(duration_ms, 2)
            }

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        try:
            payload_str = decrypted_bytes.decode("utf-8")
        except UnicodeDecodeError:
            payload_str = base64.b64encode(decrypted_bytes).decode("ascii")

        return {
            "success": True,
            "error": None,
            "decrypted_payload": payload_str,
            "decryption_duration_ms": round(duration_ms, 2)
        }

    def run_experiment(
        self,
        db: Session,
        recipient_identity: str,
        unauthorized_identity: str,
        payload: str,
        notes: Optional[str] = None
    ) -> IBEExperiment:
        """
        Executes a complete, reproducible scientific IBE evaluation:
        1. Encrypt for recipient_identity.
        2. Authorized decrypt with recipient_identity.
        3. Unauthorized decrypt with unauthorized_identity (must fail).
        4. Tamper check: bit-flipped ciphertext (must fail).
        5. Persists metrics in database.
        """
        valid_rec = self.validate_identity(recipient_identity)
        valid_unauth = self.validate_identity(unauthorized_identity)
        if valid_rec == valid_unauth:
            raise ValueError("Authorized and unauthorized identities must be distinct.")

        # 1. Encrypt
        enc_res = self.encrypt(valid_rec, payload)

        # 2. Authorized Decryption
        auth_dec = self.decrypt(enc_res, valid_rec)
        auth_ok = auth_dec["success"] and auth_dec["decrypted_payload"] == payload

        # 3. Unauthorized Decryption
        unauth_dec = self.decrypt(enc_res, valid_unauth)
        unauth_rejected = not unauth_dec["success"]

        # 4. Tamper check: flip 1 byte in ciphertext
        tampered_bundle = dict(enc_res)
        raw_ct = bytearray(base64.b64decode(enc_res["ciphertext_b64"]))
        if len(raw_ct) > 0:
            raw_ct[0] ^= 0xFF
            tampered_bundle["ciphertext_b64"] = base64.b64encode(bytes(raw_ct)).decode("ascii")
            tamper_dec = self.decrypt(tampered_bundle, valid_rec)
            tamper_ok = not tamper_dec["success"]
        else:
            tamper_ok = True

        overall_status = "success" if (auth_ok and unauth_rejected and tamper_ok) else "failed"

        exp = IBEExperiment(
            experiment_id=f"IBE-EXP-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc),
            scheme=SCHEME_NAME,
            recipient_identity=valid_rec,
            unauthorized_identity=valid_unauth,
            payload_size_bytes=enc_res["payload_size_bytes"],
            ciphertext_size_bytes=enc_res["ciphertext_size_bytes"],
            encryption_duration_ms=enc_res["encryption_duration_ms"],
            decryption_duration_ms=auth_dec["decryption_duration_ms"],
            authorized_success=auth_ok,
            unauthorized_rejected=unauth_rejected,
            tamper_check_passed=tamper_ok,
            status=overall_status,
            notes=notes or "Synthetic IoT telemetry research trial."
        )

        db.add(exp)
        db.commit()
        db.refresh(exp)
        return exp


ibe_service = IBEService()
