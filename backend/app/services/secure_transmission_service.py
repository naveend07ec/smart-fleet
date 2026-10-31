import os
import json
import time
import uuid
import base64
import statistics
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from app.models.vehicle import Vehicle
from app.models.telemetry import Telemetry
from app.models.secure_transmission import (
    VehicleEnrollment, SecureTransmission, ProcessedMessageCache
)
from app.schemas.secure_transmission import (
    PlaintextTransmissionRequest, EncryptedTransmissionRequest,
    TransmissionResponse, ExperimentRunResponse, TransmissionAnalyticsResponse
)
from app.schemas.telemetry import TelemetryBase
from app.services.ibe_service import ibe_service

# Configuration
SERVER_RECIPIENT_IDENTITY = "fleet-management-server-core"
MAX_TIMESTAMP_SKEW_SECONDS = 300  # 5 minutes replay window
MAX_FUTURE_SKEW_SECONDS = 30.0   # 30 seconds max clock drift allowance

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SIGNING_KEY_DIR = os.path.join(BASE_DIR, ".ibe_keys", "vehicle_signing_keys")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SecureTransmissionService:
    @staticmethod
    def compute_aad(sender_identity: str, recipient_identity: str, message_id: str, timestamp_str: str) -> bytes:
        """Constructs canonical Authenticated Associated Data (AAD) for AES-256-GCM AEAD binding."""
        return f"{sender_identity}:{recipient_identity}:{message_id}:{timestamp_str}".encode("utf-8")

    @staticmethod
    def compute_canonical_signature_message(
        sender_identity: str,
        recipient_identity: str,
        message_id: str,
        timestamp_str: str,
        ciphertext_bundle: Dict[str, Any]
    ) -> bytes:
        """
        Constructs deterministic canonical bytes covering transmission metadata and ciphertext envelope
        for Ed25519 digital signature signing and verification.
        Ensures signature covers sender identity, recipient identity, message UUID, timestamp, and ciphertext envelope.
        """
        canonical_bundle = json.dumps(ciphertext_bundle, sort_keys=True, separators=(",", ":"))
        canonical_str = (
            f"SENDER:{sender_identity}\n"
            f"RECIPIENT:{recipient_identity}\n"
            f"MSGID:{message_id}\n"
            f"TS:{timestamp_str}\n"
            f"CT:{canonical_bundle}"
        )
        return canonical_str.encode("utf-8")

    def _ensure_vehicle_keypair(self, vehicle_identifier: str) -> Tuple[ed25519.Ed25519PrivateKey, str]:
        """
        Retrieves or generates an Ed25519 keypair for an enrolled vehicle.
        Stores the private key securely in .ibe_keys/vehicle_signing_keys/{vehicle_identifier}.key.
        Returns: (private_key_obj, base64_public_key_string)
        """
        os.makedirs(SIGNING_KEY_DIR, exist_ok=True)
        key_path = os.path.join(SIGNING_KEY_DIR, f"{vehicle_identifier}.key")

        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                priv_key = serialization.load_pem_private_key(f.read(), password=None)
        else:
            priv_key = ed25519.Ed25519PrivateKey.generate()
            pem_bytes = priv_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(key_path, "wb") as f:
                f.write(pem_bytes)

        pub_raw = priv_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        pub_b64 = base64.b64encode(pub_raw).decode("ascii")
        return priv_key, pub_b64

    def get_vehicle_signing_private_key(self, vehicle_identifier: str) -> Optional[ed25519.Ed25519PrivateKey]:
        """
        Loads vehicle private signing key from secure local storage for client simulation.
        CRITICAL: Never exposed through public APIs.
        """
        key_path = os.path.join(SIGNING_KEY_DIR, f"{vehicle_identifier}.key")
        if not os.path.exists(key_path):
            return None
        with open(key_path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    def sign_envelope(
        self,
        vehicle_identifier: str,
        sender_identity: str,
        recipient_identity: str,
        message_id: str,
        timestamp_str: str,
        ciphertext_bundle: Dict[str, Any]
    ) -> str:
        """Simulates vehicular client signing outgoing transmission metadata and encrypted envelope with vehicle private key."""
        priv_key = self.get_vehicle_signing_private_key(vehicle_identifier)
        if not priv_key:
            priv_key, _ = self._ensure_vehicle_keypair(vehicle_identifier)
        msg_bytes = self.compute_canonical_signature_message(
            sender_identity=sender_identity,
            recipient_identity=recipient_identity,
            message_id=message_id,
            timestamp_str=timestamp_str,
            ciphertext_bundle=ciphertext_bundle
        )
        sig = priv_key.sign(msg_bytes)
        return base64.b64encode(sig).decode("ascii")

    def verify_envelope_signature(
        self,
        signing_public_key_b64: str,
        signature_b64: str,
        sender_identity: str,
        recipient_identity: str,
        message_id: str,
        timestamp_str: str,
        ciphertext_bundle: Dict[str, Any]
    ) -> bool:
        """Verifies Ed25519 digital signature against registered vehicle public verification key."""
        try:
            pub_raw = base64.b64decode(signing_public_key_b64)
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_raw)
            sig_raw = base64.b64decode(signature_b64)
            msg_bytes = self.compute_canonical_signature_message(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=message_id,
                timestamp_str=timestamp_str,
                ciphertext_bundle=ciphertext_bundle
            )
            pub_key.verify(sig_raw, msg_bytes)
            return True
        except Exception:
            return False

    def ensure_default_enrollments(self, db: Session) -> List[VehicleEnrollment]:
        """Automatically enrolls registered fleet vehicles for secure transmission trials with Ed25519 signing keys."""
        vehicles = db.query(Vehicle).all()
        enrollments = []
        for v in vehicles:
            existing = db.query(VehicleEnrollment).filter(
                VehicleEnrollment.vehicle_identifier == v.vehicle_identifier
            ).first()
            _, pub_b64 = self._ensure_vehicle_keypair(v.vehicle_identifier)
            if not existing:
                assigned_id = f"{v.vehicle_identifier}@fleet.iot.local"
                enr = VehicleEnrollment(
                    vehicle_identifier=v.vehicle_identifier,
                    assigned_identity=assigned_id,
                    is_enrolled=True,
                    signing_public_key=pub_b64,
                    enrolled_at=utc_now(),
                    notes="Auto-enrolled research fleet vehicle with Ed25519 key"
                )
                db.add(enr)
                enrollments.append(enr)
            else:
                if not existing.signing_public_key:
                    existing.signing_public_key = pub_b64
                enrollments.append(existing)
        if enrollments:
            db.commit()
        return enrollments

    def enroll_vehicle(
        self,
        db: Session,
        vehicle_identifier: str,
        assigned_identity: Optional[str] = None,
        notes: Optional[str] = None
    ) -> VehicleEnrollment:
        """Enrolls or re-authorizes a vehicle in the PKG access control registry with an Ed25519 signing key."""
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_identifier == vehicle_identifier).first()
        if not vehicle:
            raise ValueError(f"Vehicle '{vehicle_identifier}' does not exist in fleet registry.")

        _, pub_b64 = self._ensure_vehicle_keypair(vehicle_identifier)
        assigned_id = assigned_identity or f"{vehicle_identifier}@fleet.iot.local"
        existing = db.query(VehicleEnrollment).filter(
            VehicleEnrollment.vehicle_identifier == vehicle_identifier
        ).first()

        if existing:
            existing.assigned_identity = assigned_id
            existing.is_enrolled = True
            existing.revoked_at = None
            if not existing.signing_public_key:
                existing.signing_public_key = pub_b64
            if notes:
                existing.notes = notes
            db.commit()
            db.refresh(existing)
            return existing

        enrollment = VehicleEnrollment(
            vehicle_identifier=vehicle_identifier,
            assigned_identity=assigned_id,
            is_enrolled=True,
            signing_public_key=pub_b64,
            enrolled_at=utc_now(),
            notes=notes or "Enrolled for secure IBE transmission with Ed25519 sender auth"
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    def get_enrolled_vehicle(self, db: Session, sender_identity: str) -> Optional[VehicleEnrollment]:
        """Looks up an active vehicle enrollment by assigned identity or vehicle identifier."""
        return db.query(VehicleEnrollment).filter(
            (VehicleEnrollment.assigned_identity == sender_identity) |
            (VehicleEnrollment.vehicle_identifier == sender_identity),
            VehicleEnrollment.is_enrolled == True
        ).first()

    def check_replay_and_freshness(
        self,
        db: Session,
        message_id: str,
        message_timestamp: datetime,
        sender_identity: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates message freshness against sliding window and checks for duplicate replay.
        Enforces atomic uniqueness constraints to prevent concurrent duplicate replay attacks.
        Returns: (is_valid, error_reason)
        """
        now = utc_now()
        # Ensure timestamp has timezone
        if message_timestamp.tzinfo is None:
            message_timestamp = message_timestamp.replace(tzinfo=timezone.utc)

        # 1. Anti-future timestamp check (max 30s clock skew tolerance)
        future_skew = (message_timestamp - now).total_seconds()
        if future_skew > MAX_FUTURE_SKEW_SECONDS:
            return False, f"Message timestamp is in the future ({round(future_skew, 1)}s ahead > {MAX_FUTURE_SKEW_SECONDS}s max skew tolerance)."

        # 2. Expiration check (past replay window)
        age_seconds = (now - message_timestamp).total_seconds()
        if age_seconds > MAX_TIMESTAMP_SKEW_SECONDS:
            return False, f"Message timestamp outside permitted freshness window ({round(age_seconds, 1)}s skew > {MAX_TIMESTAMP_SKEW_SECONDS}s)."

        # 3. Check replay cache
        cached = db.query(ProcessedMessageCache).filter(
            ProcessedMessageCache.message_id == message_id
        ).first()
        if cached:
            return False, f"Duplicate message identifier '{message_id}' (Replay attack detected)."

        # 4. Atomic insert with savepoint to guard against concurrent duplicate requests
        try:
            with db.begin_nested():
                cache_entry = ProcessedMessageCache(
                    message_id=message_id,
                    sender_identity=sender_identity,
                    received_at=now
                )
                db.add(cache_entry)
                db.flush()
        except Exception:
            return False, f"Duplicate message identifier '{message_id}' (Concurrent duplicate replay detected)."

        return True, None

    # =========================================================================
    # Mode A: Conventional Plaintext Transmission
    # =========================================================================
    def process_plaintext_transmission(
        self,
        db: Session,
        request: PlaintextTransmissionRequest
    ) -> TransmissionResponse:
        """
        Mode A: Ingests raw JSON telemetry baseline over HTTP.
        Measures server duration, validates vehicle enrollment, records transmission, and persists telemetry.
        """
        t0 = time.perf_counter()
        now = utc_now()
        tx_id = f"TX-RAW-{uuid.uuid4().hex[:8].upper()}"

        raw_json_bytes = json.dumps(request.model_dump(mode="json"), separators=(",", ":")).encode("utf-8")
        raw_size = len(raw_json_bytes)

        # 1. Access Control: Verify enrollment
        enrollment = self.get_enrolled_vehicle(db, request.sender_identity)
        if not enrollment or enrollment.vehicle_identifier != request.vehicle_identifier:
            server_duration_ms = (time.perf_counter() - t0) * 1000.0
            tx_record = SecureTransmission(
                transmission_id=tx_id,
                batch_id=request.batch_id,
                vehicle_identifier=request.vehicle_identifier,
                sender_identity=request.sender_identity,
                recipient_identity=request.recipient_identity,
                transmission_mode="plaintext",
                payload_category=request.payload_category,
                original_payload_size_bytes=raw_size,
                encrypted_envelope_size_bytes=raw_size,
                payload_expansion_bytes=0,
                payload_expansion_percent=0.0,
                encryption_duration_ms=0.0,
                decryption_duration_ms=0.0,
                server_processing_duration_ms=round(server_duration_ms, 2),
                total_duration_ms=round(server_duration_ms, 2),
                status="rejected",
                rejection_reason="Unauthorized vehicle identity (vehicle not enrolled in access control registry).",
                unauthorized_identity_flag=True,
                message_id=request.message_id,
                message_timestamp=request.timestamp,
                created_at=now
            )
            db.add(tx_record)
            db.commit()
            db.refresh(tx_record)
            return self._record_to_response(tx_record, persisted=False)

        # 2. Replay & Freshness Check
        is_fresh, replay_error = self.check_replay_and_freshness(
            db=db,
            message_id=request.message_id,
            message_timestamp=request.timestamp,
            sender_identity=request.sender_identity
        )
        if not is_fresh:
            server_duration_ms = (time.perf_counter() - t0) * 1000.0
            tx_record = SecureTransmission(
                transmission_id=tx_id,
                batch_id=request.batch_id,
                vehicle_identifier=request.vehicle_identifier,
                sender_identity=request.sender_identity,
                recipient_identity=request.recipient_identity,
                transmission_mode="plaintext",
                payload_category=request.payload_category,
                original_payload_size_bytes=raw_size,
                encrypted_envelope_size_bytes=raw_size,
                payload_expansion_bytes=0,
                payload_expansion_percent=0.0,
                encryption_duration_ms=0.0,
                decryption_duration_ms=0.0,
                server_processing_duration_ms=round(server_duration_ms, 2),
                total_duration_ms=round(server_duration_ms, 2),
                status="rejected",
                rejection_reason=replay_error,
                replayed_flag=True,
                message_id=request.message_id,
                message_timestamp=request.timestamp,
                created_at=now
            )
            db.add(tx_record)
            db.commit()
            db.refresh(tx_record)
            return self._record_to_response(tx_record, persisted=False)

        # 3. Persist Telemetry in Database
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_identifier == request.vehicle_identifier).first()
        if vehicle:
            vehicle.status = request.telemetry.status
            db_telemetry = Telemetry(
                vehicle_id=vehicle.id,
                timestamp=request.timestamp if request.timestamp.tzinfo else request.timestamp.replace(tzinfo=timezone.utc),
                latitude=request.telemetry.latitude,
                longitude=request.telemetry.longitude,
                speed=request.telemetry.speed,
                status=request.telemetry.status,
                battery_level=request.telemetry.battery_level
            )
            db.add(db_telemetry)

        server_duration_ms = (time.perf_counter() - t0) * 1000.0

        tx_record = SecureTransmission(
            transmission_id=tx_id,
            batch_id=request.batch_id,
            vehicle_identifier=request.vehicle_identifier,
            sender_identity=request.sender_identity,
            recipient_identity=request.recipient_identity,
            transmission_mode="plaintext",
            payload_category=request.payload_category,
            original_payload_size_bytes=raw_size,
            encrypted_envelope_size_bytes=raw_size,
            payload_expansion_bytes=0,
            payload_expansion_percent=0.0,
            encryption_duration_ms=0.0,
            decryption_duration_ms=0.0,
            server_processing_duration_ms=round(server_duration_ms, 2),
            total_duration_ms=round(server_duration_ms, 2),
            status="success",
            message_id=request.message_id,
            message_timestamp=request.timestamp,
            created_at=now
        )
        db.add(tx_record)
        db.commit()
        db.refresh(tx_record)
        return self._record_to_response(tx_record, persisted=True)

    # =========================================================================
    # Mode B: IBE-Protected Secure Transmission with Ed25519 Sender Authentication
    # =========================================================================
    def process_encrypted_transmission(
        self,
        db: Session,
        request: EncryptedTransmissionRequest
    ) -> TransmissionResponse:
        """
        Mode B: Ingests IBE-protected envelope, validates envelope structure,
        verifies identity authorization, verifies Ed25519 digital signature,
        verifies AAD and decrypts via recipient private key, validates telemetry schema,
        persists to PostgreSQL, and logs metrics.
        """
        t0 = time.perf_counter()
        now = utc_now()
        tx_id = f"TX-IBE-{uuid.uuid4().hex[:8].upper()}"

        envelope_json_bytes = json.dumps(request.model_dump(mode="json"), separators=(",", ":")).encode("utf-8")
        envelope_size = len(envelope_json_bytes)

        try:
            msg_dt = datetime.fromisoformat(request.timestamp.replace("Z", "+00:00"))
        except Exception:
            msg_dt = now

        client_enc_duration = float(request.ciphertext_bundle.get("encryption_duration_ms", 0.0))
        original_payload_size = int(request.ciphertext_bundle.get("payload_size_bytes", 0))
        if original_payload_size <= 0:
            ct_bytes = len(base64.b64decode(request.ciphertext_bundle.get("ciphertext_b64", "")))
            original_payload_size = max(1, ct_bytes - 16)

        expansion_bytes = max(0, envelope_size - original_payload_size)
        expansion_pct = (expansion_bytes / original_payload_size) * 100.0 if original_payload_size > 0 else 0.0

        # 1. Access Control: Verify enrolled sender identity
        enrollment = self.get_enrolled_vehicle(db, request.sender_identity)
        if not enrollment:
            server_duration_ms = (time.perf_counter() - t0) * 1000.0
            tx_record = SecureTransmission(
                transmission_id=tx_id,
                batch_id=request.batch_id,
                vehicle_identifier=request.claimed_vehicle_identifier or "UNKNOWN",
                sender_identity=request.sender_identity,
                recipient_identity=request.recipient_identity,
                transmission_mode="ibe_protected",
                payload_category=request.payload_category,
                original_payload_size_bytes=original_payload_size,
                encrypted_envelope_size_bytes=envelope_size,
                payload_expansion_bytes=expansion_bytes,
                payload_expansion_percent=round(expansion_pct, 2),
                encryption_duration_ms=client_enc_duration,
                decryption_duration_ms=0.0,
                server_processing_duration_ms=round(server_duration_ms, 2),
                total_duration_ms=round(client_enc_duration + server_duration_ms, 2),
                status="rejected",
                rejection_reason="Unauthorized sender identity (identity not registered in vehicle enrollments).",
                unauthorized_identity_flag=True,
                signature_b64=request.signature_b64,
                signature_verified=False,
                message_id=request.message_id,
                message_timestamp=msg_dt,
                created_at=now
            )
            db.add(tx_record)
            db.commit()
            db.refresh(tx_record)
            return self._record_to_response(tx_record, persisted=False)

        bound_vehicle_id = enrollment.vehicle_identifier

        # Cross-vehicle identity claim check:
        if request.claimed_vehicle_identifier and request.claimed_vehicle_identifier != bound_vehicle_id:
            server_duration_ms = (time.perf_counter() - t0) * 1000.0
            tx_record = SecureTransmission(
                transmission_id=tx_id,
                batch_id=request.batch_id,
                vehicle_identifier=request.claimed_vehicle_identifier,
                sender_identity=request.sender_identity,
                recipient_identity=request.recipient_identity,
                transmission_mode="ibe_protected",
                payload_category=request.payload_category,
                original_payload_size_bytes=original_payload_size,
                encrypted_envelope_size_bytes=envelope_size,
                payload_expansion_bytes=expansion_bytes,
                payload_expansion_percent=round(expansion_pct, 2),
                encryption_duration_ms=client_enc_duration,
                decryption_duration_ms=0.0,
                server_processing_duration_ms=round(server_duration_ms, 2),
                total_duration_ms=round(client_enc_duration + server_duration_ms, 2),
                status="rejected",
                rejection_reason=f"Cross-vehicle identity substitution detected: claimed '{request.claimed_vehicle_identifier}' does not match authenticated identity '{bound_vehicle_id}'.",
                unauthorized_identity_flag=True,
                signature_b64=request.signature_b64,
                signature_verified=False,
                message_id=request.message_id,
                message_timestamp=msg_dt,
                created_at=now
            )
            db.add(tx_record)
            db.commit()
            db.refresh(tx_record)
            return self._record_to_response(tx_record, persisted=False)

        # 2. Cryptographic Sender Authentication: Verify Ed25519 Vehicle Signature
        # Ensure enrollment has public key registered
        if not enrollment.signing_public_key:
            # Auto-provision if missing (migration safety)
            _, pub_b64 = self._ensure_vehicle_keypair(bound_vehicle_id)
            enrollment.signing_public_key = pub_b64
            db.commit()

        if not request.signature_b64:
            server_duration_ms = (time.perf_counter() - t0) * 1000.0
            tx_record = SecureTransmission(
                transmission_id=tx_id,
                batch_id=request.batch_id,
                vehicle_identifier=bound_vehicle_id,
                sender_identity=request.sender_identity,
                recipient_identity=request.recipient_identity,
                transmission_mode="ibe_protected",
                payload_category=request.payload_category,
                original_payload_size_bytes=original_payload_size,
                encrypted_envelope_size_bytes=envelope_size,
                payload_expansion_bytes=expansion_bytes,
                payload_expansion_percent=round(expansion_pct, 2),
                encryption_duration_ms=client_enc_duration,
                decryption_duration_ms=0.0,
                server_processing_duration_ms=round(server_duration_ms, 2),
                total_duration_ms=round(client_enc_duration + server_duration_ms, 2),
                status="rejected",
                rejection_reason="Cryptographic sender authentication failed: Missing Ed25519 vehicle signature.",
                unauthorized_identity_flag=True,
                signature_b64=None,
                signature_verified=False,
                message_id=request.message_id,
                message_timestamp=msg_dt,
                created_at=now
            )
            db.add(tx_record)
            db.commit()
            db.refresh(tx_record)
            return self._record_to_response(tx_record, persisted=False)

        sig_valid = self.verify_envelope_signature(
            signing_public_key_b64=enrollment.signing_public_key,
            signature_b64=request.signature_b64,
            sender_identity=request.sender_identity,
            recipient_identity=request.recipient_identity,
            message_id=request.message_id,
            timestamp_str=request.timestamp,
            ciphertext_bundle=request.ciphertext_bundle
        )

        if not sig_valid:
            server_duration_ms = (time.perf_counter() - t0) * 1000.0
            tx_record = SecureTransmission(
                transmission_id=tx_id,
                batch_id=request.batch_id,
                vehicle_identifier=bound_vehicle_id,
                sender_identity=request.sender_identity,
                recipient_identity=request.recipient_identity,
                transmission_mode="ibe_protected",
                payload_category=request.payload_category,
                original_payload_size_bytes=original_payload_size,
                encrypted_envelope_size_bytes=envelope_size,
                payload_expansion_bytes=expansion_bytes,
                payload_expansion_percent=round(expansion_pct, 2),
                encryption_duration_ms=client_enc_duration,
                decryption_duration_ms=0.0,
                server_processing_duration_ms=round(server_duration_ms, 2),
                total_duration_ms=round(client_enc_duration + server_duration_ms, 2),
                status="rejected",
                rejection_reason="Cryptographic integrity verification failed: Invalid, forged, or tampered Ed25519 signature / envelope.",
                unauthorized_identity_flag=True,
                tampered_flag=True,
                signature_b64=request.signature_b64,
                signature_verified=False,
                message_id=request.message_id,
                message_timestamp=msg_dt,
                created_at=now
            )
            db.add(tx_record)
            db.commit()
            db.refresh(tx_record)
            return self._record_to_response(tx_record, persisted=False)

        # 3. Replay & Freshness Check (with atomic uniqueness protection)
        is_fresh, replay_error = self.check_replay_and_freshness(
            db=db,
            message_id=request.message_id,
            message_timestamp=msg_dt,
            sender_identity=request.sender_identity
        )
        if not is_fresh:
            server_duration_ms = (time.perf_counter() - t0) * 1000.0
            tx_record = SecureTransmission(
                transmission_id=tx_id,
                batch_id=request.batch_id,
                vehicle_identifier=bound_vehicle_id,
                sender_identity=request.sender_identity,
                recipient_identity=request.recipient_identity,
                transmission_mode="ibe_protected",
                payload_category=request.payload_category,
                original_payload_size_bytes=original_payload_size,
                encrypted_envelope_size_bytes=envelope_size,
                payload_expansion_bytes=expansion_bytes,
                payload_expansion_percent=round(expansion_pct, 2),
                encryption_duration_ms=client_enc_duration,
                decryption_duration_ms=0.0,
                server_processing_duration_ms=round(server_duration_ms, 2),
                total_duration_ms=round(client_enc_duration + server_duration_ms, 2),
                status="rejected",
                rejection_reason=replay_error,
                replayed_flag=True,
                signature_b64=request.signature_b64,
                signature_verified=True,
                message_id=request.message_id,
                message_timestamp=msg_dt,
                created_at=now
            )
            db.add(tx_record)
            db.commit()
            db.refresh(tx_record)
            return self._record_to_response(tx_record, persisted=False)

        # 4. Decrypt IBE-KEM + AES-256-GCM Envelope with AAD Binding
        aad = self.compute_aad(
            sender_identity=request.sender_identity,
            recipient_identity=request.recipient_identity,
            message_id=request.message_id,
            timestamp_str=request.timestamp
        )

        dec_result = ibe_service.decrypt(
            ciphertext_bundle=request.ciphertext_bundle,
            recipient_identity=request.recipient_identity,
            aad=aad
        )

        dec_duration_ms = float(dec_result.get("decryption_duration_ms", 0.0))

        if not dec_result["success"]:
            server_duration_ms = (time.perf_counter() - t0) * 1000.0
            tx_record = SecureTransmission(
                transmission_id=tx_id,
                batch_id=request.batch_id,
                vehicle_identifier=bound_vehicle_id,
                sender_identity=request.sender_identity,
                recipient_identity=request.recipient_identity,
                transmission_mode="ibe_protected",
                payload_category=request.payload_category,
                original_payload_size_bytes=original_payload_size,
                encrypted_envelope_size_bytes=envelope_size,
                payload_expansion_bytes=expansion_bytes,
                payload_expansion_percent=round(expansion_pct, 2),
                encryption_duration_ms=client_enc_duration,
                decryption_duration_ms=dec_duration_ms,
                server_processing_duration_ms=round(server_duration_ms, 2),
                total_duration_ms=round(client_enc_duration + server_duration_ms, 2),
                status="rejected",
                rejection_reason=f"Cryptographic integrity verification failed: {dec_result.get('error')}",
                tampered_flag=True,
                signature_b64=request.signature_b64,
                signature_verified=True,
                message_id=request.message_id,
                message_timestamp=msg_dt,
                created_at=now
            )
            db.add(tx_record)
            db.commit()
            db.refresh(tx_record)
            return self._record_to_response(tx_record, persisted=False)

        # 5. Parse & Validate Decrypted Telemetry JSON
        try:
            payload_data = json.loads(dec_result["decrypted_payload"])
            telemetry_data = payload_data.get("telemetry", payload_data)
            telemetry_model = TelemetryBase(**telemetry_data)
        except Exception as e:
            server_duration_ms = (time.perf_counter() - t0) * 1000.0
            tx_record = SecureTransmission(
                transmission_id=tx_id,
                batch_id=request.batch_id,
                vehicle_identifier=bound_vehicle_id,
                sender_identity=request.sender_identity,
                recipient_identity=request.recipient_identity,
                transmission_mode="ibe_protected",
                payload_category=request.payload_category,
                original_payload_size_bytes=original_payload_size,
                encrypted_envelope_size_bytes=envelope_size,
                payload_expansion_bytes=expansion_bytes,
                payload_expansion_percent=round(expansion_pct, 2),
                encryption_duration_ms=client_enc_duration,
                decryption_duration_ms=dec_duration_ms,
                server_processing_duration_ms=round(server_duration_ms, 2),
                total_duration_ms=round(client_enc_duration + server_duration_ms, 2),
                status="rejected",
                rejection_reason=f"Malformed decrypted telemetry payload schema: {str(e)}",
                signature_b64=request.signature_b64,
                signature_verified=True,
                message_id=request.message_id,
                message_timestamp=msg_dt,
                created_at=now
            )
            db.add(tx_record)
            db.commit()
            db.refresh(tx_record)
            return self._record_to_response(tx_record, persisted=False)

        # 6. Persist Verified Telemetry in Database
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_identifier == bound_vehicle_id).first()
        if vehicle:
            vehicle.status = telemetry_model.status
            db_telemetry = Telemetry(
                vehicle_id=vehicle.id,
                timestamp=msg_dt,
                latitude=telemetry_model.latitude,
                longitude=telemetry_model.longitude,
                speed=telemetry_model.speed,
                status=telemetry_model.status,
                battery_level=telemetry_model.battery_level
            )
            db.add(db_telemetry)

        server_duration_ms = (time.perf_counter() - t0) * 1000.0

        tx_record = SecureTransmission(
            transmission_id=tx_id,
            batch_id=request.batch_id,
            vehicle_identifier=bound_vehicle_id,
            sender_identity=request.sender_identity,
            recipient_identity=request.recipient_identity,
            transmission_mode="ibe_protected",
            payload_category=request.payload_category,
            original_payload_size_bytes=original_payload_size,
            encrypted_envelope_size_bytes=envelope_size,
            payload_expansion_bytes=expansion_bytes,
            payload_expansion_percent=round(expansion_pct, 2),
            encryption_duration_ms=client_enc_duration,
            decryption_duration_ms=dec_duration_ms,
            server_processing_duration_ms=round(server_duration_ms, 2),
            total_duration_ms=round(client_enc_duration + server_duration_ms, 2),
            status="success",
            signature_b64=request.signature_b64,
            signature_verified=True,
            message_id=request.message_id,
            message_timestamp=msg_dt,
            created_at=now
        )
        db.add(tx_record)
        db.commit()
        db.refresh(tx_record)
        return self._record_to_response(tx_record, persisted=True)

    # =========================================================================
    # Controlled Security Demonstration Execution
    # =========================================================================
    def execute_security_demonstration(
        self,
        db: Session,
        scenario: str,
        vehicle_identifier: str = "SIM-VEH-001"
    ) -> TransmissionResponse:
        """
        Executes a controlled security scenario demonstrating attack prevention:
        - valid_authorized: Legitimate encrypted telemetry with valid Ed25519 signature
        - attacker_impersonation: Attacker creates fresh envelope for server claiming enrolled vehicle ID (lacking Ed25519 private key)
        - tampered_signature: 1-byte alteration in Ed25519 signature string
        - substituted_signature: Vehicle A signature attached to Vehicle B transmission
        - unauthorized_identity: Unenrolled identity submission
        - tampered_ciphertext: 1-byte flip in ciphertext
        - tampered_tag: 1-byte flip in AEAD authentication tag
        - replay_attack: Transmission replayed twice
        - cross_vehicle_substitution: Vehicle A transmits telemetry claiming Vehicle B in header
        - future_timestamp: Timestamp 120s into the future (anti-clock skew)
        - expired_timestamp: Timestamp 600s in the past (> 300s freshness window)
        """
        self.ensure_default_enrollments(db)
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_identifier == vehicle_identifier).first()
        if not vehicle:
            vehicle = db.query(Vehicle).first()
            if not vehicle:
                raise ValueError("No vehicles available in database.")
            vehicle_identifier = vehicle.vehicle_identifier

        sender_identity = f"{vehicle_identifier}@fleet.iot.local"
        recipient_identity = SERVER_RECIPIENT_IDENTITY
        msg_id = f"MSG-DEMO-{uuid.uuid4().hex[:8].upper()}"
        ts_iso = utc_now().isoformat()

        sample_telemetry = {
            "latitude": 13.0827,
            "longitude": 80.2707,
            "speed": 45.2,
            "status": "moving",
            "battery_level": 88.5
        }
        raw_payload = json.dumps({
            "vehicle_identifier": vehicle_identifier,
            "timestamp": ts_iso,
            "telemetry": sample_telemetry
        }, separators=(",", ":"))

        if scenario == "valid_authorized":
            aad = self.compute_aad(sender_identity, recipient_identity, msg_id, ts_iso)
            enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload, aad=aad)
            sig_b64 = self.sign_envelope(
                vehicle_identifier=vehicle_identifier,
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=ts_iso,
                ciphertext_bundle=enc_bundle
            )
            req = EncryptedTransmissionRequest(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=ts_iso,
                ciphertext_bundle=enc_bundle,
                signature_b64=sig_b64,
                claimed_vehicle_identifier=vehicle_identifier,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        elif scenario == "attacker_impersonation":
            # Genuine impersonation attack:
            # Attacker encrypts new ciphertext for server using server's public parameters.
            # Attacker claims Vehicle A identity, binds AAD to Vehicle A.
            # But attacker does NOT hold Vehicle A's Ed25519 private signing key!
            # Attacker signs with a rogue ephemeral keypair.
            aad = self.compute_aad(sender_identity, recipient_identity, msg_id, ts_iso)
            enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload, aad=aad)
            rogue_key = ed25519.Ed25519PrivateKey.generate()
            msg_bytes = self.compute_canonical_signature_message(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=ts_iso,
                ciphertext_bundle=enc_bundle
            )
            forged_sig = base64.b64encode(rogue_key.sign(msg_bytes)).decode("ascii")

            req = EncryptedTransmissionRequest(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=ts_iso,
                ciphertext_bundle=enc_bundle,
                signature_b64=forged_sig,
                claimed_vehicle_identifier=vehicle_identifier,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        elif scenario == "tampered_signature":
            aad = self.compute_aad(sender_identity, recipient_identity, msg_id, ts_iso)
            enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload, aad=aad)
            sig_b64 = self.sign_envelope(
                vehicle_identifier=vehicle_identifier,
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=ts_iso,
                ciphertext_bundle=enc_bundle
            )
            # Tamper the signature by flipping characters
            sig_raw = bytearray(base64.b64decode(sig_b64))
            sig_raw[0] ^= 0x55
            corrupted_sig = base64.b64encode(bytes(sig_raw)).decode("ascii")

            req = EncryptedTransmissionRequest(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=ts_iso,
                ciphertext_bundle=enc_bundle,
                signature_b64=corrupted_sig,
                claimed_vehicle_identifier=vehicle_identifier,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        elif scenario == "substituted_signature":
            # Vehicle A signs with its own key, but claims to be Vehicle B
            target_vehicle = "SIM-VEH-002" if vehicle_identifier != "SIM-VEH-002" else "SIM-VEH-001"
            target_identity = f"{target_vehicle}@fleet.iot.local"

            aad = self.compute_aad(target_identity, recipient_identity, msg_id, ts_iso)
            enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload, aad=aad)
            # Sign with vehicle_identifier (Vehicle A) instead of target_vehicle (Vehicle B)
            sub_sig = self.sign_envelope(
                vehicle_identifier=vehicle_identifier,
                sender_identity=target_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=ts_iso,
                ciphertext_bundle=enc_bundle
            )
            req = EncryptedTransmissionRequest(
                sender_identity=target_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=ts_iso,
                ciphertext_bundle=enc_bundle,
                signature_b64=sub_sig,
                claimed_vehicle_identifier=target_vehicle,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        elif scenario == "unauthorized_identity":
            unauth_sender = "MALICIOUS-ROGUE-999@external.attacker.net"
            aad = self.compute_aad(unauth_sender, recipient_identity, msg_id, ts_iso)
            enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload, aad=aad)
            req = EncryptedTransmissionRequest(
                sender_identity=unauth_sender,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=ts_iso,
                ciphertext_bundle=enc_bundle,
                signature_b64=None,
                claimed_vehicle_identifier=vehicle_identifier,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        elif scenario == "tampered_ciphertext":
            aad = self.compute_aad(sender_identity, recipient_identity, msg_id, ts_iso)
            enc_bundle = dict(ibe_service.encrypt(recipient_identity, raw_payload, aad=aad))
            sig_b64 = self.sign_envelope(
                vehicle_identifier=vehicle_identifier,
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=ts_iso,
                ciphertext_bundle=enc_bundle
            )
            raw_ct = bytearray(base64.b64decode(enc_bundle["ciphertext_b64"]))
            raw_ct[0] ^= 0xFF
            enc_bundle["ciphertext_b64"] = base64.b64encode(bytes(raw_ct)).decode("ascii")

            req = EncryptedTransmissionRequest(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=ts_iso,
                ciphertext_bundle=enc_bundle,
                signature_b64=sig_b64,
                claimed_vehicle_identifier=vehicle_identifier,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        elif scenario == "tampered_tag":
            aad = self.compute_aad(sender_identity, recipient_identity, msg_id, ts_iso)
            enc_bundle = dict(ibe_service.encrypt(recipient_identity, raw_payload, aad=aad))
            sig_b64 = self.sign_envelope(
                vehicle_identifier=vehicle_identifier,
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=ts_iso,
                ciphertext_bundle=enc_bundle
            )
            raw_ct = bytearray(base64.b64decode(enc_bundle["ciphertext_b64"]))
            if len(raw_ct) >= 16:
                raw_ct[-1] ^= 0x01
            enc_bundle["ciphertext_b64"] = base64.b64encode(bytes(raw_ct)).decode("ascii")

            req = EncryptedTransmissionRequest(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=ts_iso,
                ciphertext_bundle=enc_bundle,
                signature_b64=sig_b64,
                claimed_vehicle_identifier=vehicle_identifier,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        elif scenario == "replay_attack":
            aad = self.compute_aad(sender_identity, recipient_identity, msg_id, ts_iso)
            enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload, aad=aad)
            sig_b64 = self.sign_envelope(
                vehicle_identifier=vehicle_identifier,
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=ts_iso,
                ciphertext_bundle=enc_bundle
            )
            req = EncryptedTransmissionRequest(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=ts_iso,
                ciphertext_bundle=enc_bundle,
                signature_b64=sig_b64,
                claimed_vehicle_identifier=vehicle_identifier,
                payload_category="medium"
            )
            # Send initial message (succeeds)
            self.process_encrypted_transmission(db, req)
            # Replay the identical message (must be rejected)
            return self.process_encrypted_transmission(db, req)

        elif scenario == "cross_vehicle_substitution":
            target_vehicle = "SIM-VEH-002" if vehicle_identifier != "SIM-VEH-002" else "SIM-VEH-001"
            aad = self.compute_aad(sender_identity, recipient_identity, msg_id, ts_iso)
            enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload, aad=aad)
            sig_b64 = self.sign_envelope(
                vehicle_identifier=vehicle_identifier,
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=ts_iso,
                ciphertext_bundle=enc_bundle
            )
            req = EncryptedTransmissionRequest(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=ts_iso,
                ciphertext_bundle=enc_bundle,
                signature_b64=sig_b64,
                claimed_vehicle_identifier=target_vehicle,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        elif scenario == "future_timestamp":
            future_ts = (utc_now() + timedelta(seconds=120)).isoformat()
            aad = self.compute_aad(sender_identity, recipient_identity, msg_id, future_ts)
            enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload, aad=aad)
            sig_b64 = self.sign_envelope(
                vehicle_identifier=vehicle_identifier,
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=future_ts,
                ciphertext_bundle=enc_bundle
            )
            req = EncryptedTransmissionRequest(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=future_ts,
                ciphertext_bundle=enc_bundle,
                signature_b64=sig_b64,
                claimed_vehicle_identifier=vehicle_identifier,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        elif scenario == "expired_timestamp":
            expired_ts = (utc_now() - timedelta(seconds=600)).isoformat()
            aad = self.compute_aad(sender_identity, recipient_identity, msg_id, expired_ts)
            enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload, aad=aad)
            sig_b64 = self.sign_envelope(
                vehicle_identifier=vehicle_identifier,
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp_str=expired_ts,
                ciphertext_bundle=enc_bundle
            )
            req = EncryptedTransmissionRequest(
                sender_identity=sender_identity,
                recipient_identity=recipient_identity,
                message_id=msg_id,
                timestamp=expired_ts,
                ciphertext_bundle=enc_bundle,
                signature_b64=sig_b64,
                claimed_vehicle_identifier=vehicle_identifier,
                payload_category="medium"
            )
            return self.process_encrypted_transmission(db, req)

        else:
            raise ValueError(f"Unknown demonstration scenario '{scenario}'.")

    # =========================================================================
    # Automated Repeatable Batch Experiment Runner
    # =========================================================================
    def run_batch_experiment(
        self,
        db: Session,
        vehicle_count: int = 5,
        messages_per_vehicle: int = 3,
        mode: str = "both",
        payload_category: str = "medium",
        notes: Optional[str] = None
    ) -> ExperimentRunResponse:
        """
        Executes a rigorous, reproducible scientific benchmark:
        - Selects vehicle_count vehicles.
        - Generates identical telemetry payloads for both modes.
        - Evaluates Mode A (baseline) and/or Mode B (IBE-protected with Ed25519 signing).
        - Computes real statistics (no fabricated data).
        """
        self.ensure_default_enrollments(db)
        vehicles = db.query(Vehicle).order_by(Vehicle.id.asc()).limit(vehicle_count).all()
        if not vehicles:
            raise ValueError("No vehicles found in database for experiment.")

        batch_id = f"BATCH-P3-{uuid.uuid4().hex[:8].upper()}"
        responses: List[TransmissionResponse] = []

        def make_telemetry(v_idx: int, m_idx: int) -> Tuple[TelemetryBase, Dict[str, Any]]:
            lat = 12.9500 + (v_idx * 0.005) + (m_idx * 0.001)
            lng = 80.1500 + (v_idx * 0.004) + (m_idx * 0.001)
            speed = 25.0 + ((v_idx * 7 + m_idx * 3) % 55)
            bat = max(10.0, 95.0 - (v_idx * 2 + m_idx * 1.5))
            status = "moving" if speed > 0 else "idle"

            t_base = TelemetryBase(
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                speed=round(speed, 2),
                status=status,
                battery_level=round(bat, 1)
            )

            diag = {}
            if payload_category == "medium":
                diag = {
                    "engine_rpm": 2400 + (v_idx * 50),
                    "coolant_temp_c": 88.0,
                    "tire_pressure_psi": [32.1, 32.0, 31.9, 32.2]
                }
            elif payload_category == "large":
                diag = {
                    "engine_rpm": 2400 + (v_idx * 50),
                    "coolant_temp_c": 88.0,
                    "oil_life_percent": 74.0,
                    "tire_pressure_psi": [32.1, 32.0, 31.9, 32.2],
                    "sensor_readings": [
                        {"sensor": "lidar_front", "dist_m": 14.2, "status": "ok"},
                        {"sensor": "radar_rear", "dist_m": 35.8, "status": "ok"},
                        {"sensor": "imu_accel", "ax": 0.12, "ay": -0.05, "az": 9.81}
                    ],
                    "waypoints_history": [
                        {"lat": 12.940, "lng": 80.140, "t_offset": -120},
                        {"lat": 12.945, "lng": 80.145, "t_offset": -60}
                    ]
                }
            return t_base, diag

        for m_idx in range(messages_per_vehicle):
            for v_idx, v in enumerate(vehicles):
                t_base, diag = make_telemetry(v_idx, m_idx)
                sender_identity = f"{v.vehicle_identifier}@fleet.iot.local"
                recipient_identity = SERVER_RECIPIENT_IDENTITY
                ts_dt = utc_now()
                ts_iso = ts_dt.isoformat()

                raw_payload_dict = {
                    "vehicle_identifier": v.vehicle_identifier,
                    "timestamp": ts_iso,
                    "telemetry": t_base.model_dump(),
                    "diagnostics": diag
                }
                raw_payload_str = json.dumps(raw_payload_dict, separators=(",", ":"))

                # 1. Evaluate Mode A (Baseline)
                if mode in ("plaintext", "both"):
                    msg_id_a = f"MSG-RAW-{uuid.uuid4().hex[:8].upper()}"
                    pt_req = PlaintextTransmissionRequest(
                        vehicle_identifier=v.vehicle_identifier,
                        sender_identity=sender_identity,
                        recipient_identity=recipient_identity,
                        message_id=msg_id_a,
                        timestamp=ts_dt,
                        telemetry=t_base,
                        batch_id=batch_id,
                        payload_category=payload_category,
                        extra_diagnostics=diag
                    )
                    resp_a = self.process_plaintext_transmission(db, pt_req)
                    responses.append(resp_a)

                # 2. Evaluate Mode B (IBE Protected + Ed25519 Signed)
                if mode in ("ibe_protected", "both"):
                    msg_id_b = f"MSG-IBE-{uuid.uuid4().hex[:8].upper()}"
                    aad = self.compute_aad(sender_identity, recipient_identity, msg_id_b, ts_iso)
                    enc_bundle = ibe_service.encrypt(recipient_identity, raw_payload_str, aad=aad)
                    sig_b64 = self.sign_envelope(
                        vehicle_identifier=v.vehicle_identifier,
                        sender_identity=sender_identity,
                        recipient_identity=recipient_identity,
                        message_id=msg_id_b,
                        timestamp_str=ts_iso,
                        ciphertext_bundle=enc_bundle
                    )
                    enc_req = EncryptedTransmissionRequest(
                        sender_identity=sender_identity,
                        recipient_identity=recipient_identity,
                        message_id=msg_id_b,
                        timestamp=ts_iso,
                        ciphertext_bundle=enc_bundle,
                        signature_b64=sig_b64,
                        claimed_vehicle_identifier=v.vehicle_identifier,
                        batch_id=batch_id,
                        payload_category=payload_category
                    )
                    resp_b = self.process_encrypted_transmission(db, enc_req)
                    responses.append(resp_b)

        total_attempted = len(responses)
        successful = [r for r in responses if r.status == "success"]
        rejected = [r for r in responses if r.status != "success"]
        success_rate = (len(successful) / total_attempted * 100.0) if total_attempted > 0 else 0.0

        pt_times = [r.total_duration_ms for r in successful if r.transmission_mode == "plaintext"]
        ibe_times = [r.total_duration_ms for r in successful if r.transmission_mode == "ibe_protected"]
        enc_times = [r.encryption_duration_ms for r in successful if r.transmission_mode == "ibe_protected"]
        dec_times = [r.decryption_duration_ms for r in successful if r.transmission_mode == "ibe_protected"]

        exp_bytes = [r.payload_expansion_bytes for r in successful if r.transmission_mode == "ibe_protected"]
        exp_pcts = [r.payload_expansion_percent for r in successful if r.transmission_mode == "ibe_protected"]

        metrics = {
            "plaintext": {
                "count": len(pt_times),
                "mean_latency_ms": round(statistics.mean(pt_times), 2) if pt_times else 0.0,
                "median_latency_ms": round(statistics.median(pt_times), 2) if pt_times else 0.0,
                "stdev_latency_ms": round(statistics.stdev(pt_times), 2) if len(pt_times) > 1 else 0.0,
                "min_latency_ms": round(min(pt_times), 2) if pt_times else 0.0,
                "max_latency_ms": round(max(pt_times), 2) if pt_times else 0.0,
            },
            "ibe_protected": {
                "count": len(ibe_times),
                "mean_total_latency_ms": round(statistics.mean(ibe_times), 2) if ibe_times else 0.0,
                "median_total_latency_ms": round(statistics.median(ibe_times), 2) if ibe_times else 0.0,
                "stdev_total_latency_ms": round(statistics.stdev(ibe_times), 2) if len(ibe_times) > 1 else 0.0,
                "mean_encryption_latency_ms": round(statistics.mean(enc_times), 2) if enc_times else 0.0,
                "median_encryption_latency_ms": round(statistics.median(enc_times), 2) if enc_times else 0.0,
                "mean_decryption_latency_ms": round(statistics.mean(dec_times), 2) if dec_times else 0.0,
                "median_decryption_latency_ms": round(statistics.median(dec_times), 2) if dec_times else 0.0,
                "mean_expansion_bytes": round(statistics.mean(exp_bytes), 1) if exp_bytes else 0.0,
                "mean_expansion_percent": round(statistics.mean(exp_pcts), 2) if exp_pcts else 0.0,
            }
        }

        return ExperimentRunResponse(
            batch_id=batch_id,
            total_attempted=total_attempted,
            total_successful=len(successful),
            total_rejected=len(rejected),
            success_rate_percent=round(success_rate, 2),
            plaintext_count=len([r for r in responses if r.transmission_mode == "plaintext"]),
            protected_count=len([r for r in responses if r.transmission_mode == "ibe_protected"]),
            metrics=metrics,
            records=responses
        )

    # =========================================================================
    # Analytics & Queries
    # =========================================================================
    def get_analytics(self, db: Session) -> TransmissionAnalyticsResponse:
        records = db.query(SecureTransmission).all()
        total = len(records)
        if total == 0:
            return TransmissionAnalyticsResponse(
                total_transmissions=0,
                plaintext_transmissions=0,
                protected_transmissions=0,
                successful_transmissions=0,
                rejected_transmissions=0,
                overall_success_rate=0.0,
                tampering_detected_count=0,
                replay_detected_count=0,
                unauthorized_identity_count=0,
                median_plaintext_latency_ms=0.0,
                median_protected_latency_ms=0.0,
                median_encryption_latency_ms=0.0,
                median_decryption_latency_ms=0.0,
                mean_payload_expansion_bytes=0.0,
                mean_payload_expansion_percent=0.0,
                by_payload_category={}
            )

        pt_list = [r for r in records if r.transmission_mode == "plaintext"]
        ibe_list = [r for r in records if r.transmission_mode == "ibe_protected"]
        succ_list = [r for r in records if r.status == "success"]
        rej_list = [r for r in records if r.status != "success"]

        pt_succ_durs = [r.total_duration_ms for r in pt_list if r.status == "success"] or [0.0]
        ibe_succ_durs = [r.total_duration_ms for r in ibe_list if r.status == "success"] or [0.0]
        enc_times = [r.encryption_duration_ms for r in ibe_list if r.encryption_duration_ms > 0] or [0.0]
        dec_times = [r.decryption_duration_ms for r in ibe_list if r.decryption_duration_ms > 0] or [0.0]
        exp_bytes = [r.payload_expansion_bytes for r in ibe_list if r.payload_expansion_bytes > 0] or [0.0]
        exp_pcts = [r.payload_expansion_percent for r in ibe_list if r.payload_expansion_percent > 0] or [0.0]

        by_cat = {}
        for cat in ("small", "medium", "large"):
            cat_recs = [r for r in ibe_list if r.payload_category == cat]
            if cat_recs:
                by_cat[cat] = {
                    "count": len(cat_recs),
                    "mean_original_bytes": round(statistics.mean([r.original_payload_size_bytes for r in cat_recs]), 1),
                    "mean_envelope_bytes": round(statistics.mean([r.encrypted_envelope_size_bytes for r in cat_recs]), 1),
                    "mean_expansion_pct": round(statistics.mean([r.payload_expansion_percent for r in cat_recs]), 2)
                }

        return TransmissionAnalyticsResponse(
            total_transmissions=total,
            plaintext_transmissions=len(pt_list),
            protected_transmissions=len(ibe_list),
            successful_transmissions=len(succ_list),
            rejected_transmissions=len(rej_list),
            overall_success_rate=round((len(succ_list) / total) * 100.0, 2),
            tampering_detected_count=len([r for r in records if r.tampered_flag]),
            replay_detected_count=len([r for r in records if r.replayed_flag]),
            unauthorized_identity_count=len([r for r in records if r.unauthorized_identity_flag]),
            median_plaintext_latency_ms=round(statistics.median(pt_succ_durs), 2),
            median_protected_latency_ms=round(statistics.median(ibe_succ_durs), 2),
            median_encryption_latency_ms=round(statistics.median(enc_times), 2),
            median_decryption_latency_ms=round(statistics.median(dec_times), 2),
            mean_payload_expansion_bytes=round(statistics.mean(exp_bytes), 1),
            mean_payload_expansion_percent=round(statistics.mean(exp_pcts), 2),
            by_payload_category=by_cat
        )

    @staticmethod
    def _record_to_response(rec: SecureTransmission, persisted: bool = False) -> TransmissionResponse:
        return TransmissionResponse(
            transmission_id=rec.transmission_id,
            batch_id=rec.batch_id,
            vehicle_identifier=rec.vehicle_identifier,
            sender_identity=rec.sender_identity,
            recipient_identity=rec.recipient_identity,
            transmission_mode=rec.transmission_mode,
            payload_category=rec.payload_category,
            original_payload_size_bytes=rec.original_payload_size_bytes,
            encrypted_envelope_size_bytes=rec.encrypted_envelope_size_bytes,
            payload_expansion_bytes=rec.payload_expansion_bytes,
            payload_expansion_percent=rec.payload_expansion_percent,
            encryption_duration_ms=rec.encryption_duration_ms,
            decryption_duration_ms=rec.decryption_duration_ms,
            server_processing_duration_ms=rec.server_processing_duration_ms,
            total_duration_ms=rec.total_duration_ms,
            status=rec.status,
            rejection_reason=rec.rejection_reason,
            tampered_flag=rec.tampered_flag,
            replayed_flag=rec.replayed_flag,
            unauthorized_identity_flag=rec.unauthorized_identity_flag,
            signature_b64=rec.signature_b64,
            signature_verified=rec.signature_verified,
            message_id=rec.message_id,
            created_at=rec.created_at,
            telemetry_persisted=persisted
        )


secure_transmission_service = SecureTransmissionService()
