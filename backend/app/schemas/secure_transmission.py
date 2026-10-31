from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.telemetry import TelemetryBase

class VehicleEnrollmentCreate(BaseModel):
    vehicle_identifier: str = Field(..., min_length=3, max_length=64, description="Vehicle ID e.g. SIM-VEH-001")
    assigned_identity: Optional[str] = Field(None, min_length=3, max_length=120, description="Cryptographic recipient/sender identity")
    notes: Optional[str] = Field(None, max_length=255)

class VehicleEnrollmentResponse(BaseModel):
    id: int
    vehicle_identifier: str
    assigned_identity: str
    is_enrolled: bool
    enrolled_at: datetime
    revoked_at: Optional[datetime] = None
    signing_public_key: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PlaintextTransmissionRequest(BaseModel):
    vehicle_identifier: str = Field(..., description="Sender vehicle identifier e.g. SIM-VEH-001")
    sender_identity: str = Field(..., description="Identity of the transmitting vehicle")
    recipient_identity: str = Field(default="fleet-management-server-core", description="Recipient server identity")
    message_id: str = Field(..., description="Unique UUID message identifier")
    timestamp: datetime = Field(..., description="Transmission timestamp (UTC)")
    telemetry: TelemetryBase = Field(..., description="Unencrypted telemetry payload")
    batch_id: Optional[str] = Field(None, description="Experiment batch ID")
    payload_category: str = Field(default="medium", description="Payload size class: small, medium, large")
    extra_diagnostics: Optional[Dict[str, Any]] = Field(None, description="Simulated diagnostic payload fields")


class EncryptedTransmissionRequest(BaseModel):
    sender_identity: str = Field(..., description="Identity of sending vehicle")
    recipient_identity: str = Field(..., description="Target server identity used for IBE encryption")
    message_id: str = Field(..., description="Unique UUID message identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp string")
    ciphertext_bundle: Dict[str, Any] = Field(..., description="IBE-KEM + AES-256-GCM ciphertext envelope")
    signature_b64: Optional[str] = Field(None, description="Ed25519 digital signature of sender vehicle")
    claimed_vehicle_identifier: Optional[str] = Field(None, description="Header claim for vehicle ID (validated against sender_identity)")
    batch_id: Optional[str] = Field(None, description="Experiment batch ID")
    payload_category: str = Field(default="medium", description="Payload category: small, medium, large")


class TransmissionResponse(BaseModel):
    transmission_id: str
    batch_id: Optional[str] = None
    vehicle_identifier: str
    sender_identity: str
    recipient_identity: str
    transmission_mode: str
    payload_category: str
    original_payload_size_bytes: int
    encrypted_envelope_size_bytes: int
    payload_expansion_bytes: int
    payload_expansion_percent: float
    encryption_duration_ms: float
    decryption_duration_ms: float
    server_processing_duration_ms: float
    total_duration_ms: float
    status: str
    rejection_reason: Optional[str] = None
    tampered_flag: bool = False
    replayed_flag: bool = False
    unauthorized_identity_flag: bool = False
    signature_b64: Optional[str] = None
    signature_verified: bool = False
    message_id: Optional[str] = None
    created_at: datetime
    telemetry_persisted: bool = False

    model_config = ConfigDict(from_attributes=True)


class TransmissionListResponse(BaseModel):
    items: List[TransmissionResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class ExperimentRunRequest(BaseModel):
    vehicle_count: int = Field(default=5, ge=1, le=25, description="Number of vehicles in experiment")
    messages_per_vehicle: int = Field(default=3, ge=1, le=10, description="Messages transmitted per vehicle")
    mode: str = Field(default="both", description="Transmission mode: plaintext, ibe_protected, or both")
    payload_category: str = Field(default="medium", description="Payload scale: small, medium, or large")
    notes: Optional[str] = Field(None, description="Experiment metadata or trial notes")


class ExperimentRunResponse(BaseModel):
    batch_id: str
    total_attempted: int
    total_successful: int
    total_rejected: int
    success_rate_percent: float
    plaintext_count: int
    protected_count: int
    metrics: Dict[str, Any]
    records: List[TransmissionResponse]


class TransmissionAnalyticsResponse(BaseModel):
    total_transmissions: int
    plaintext_transmissions: int
    protected_transmissions: int
    successful_transmissions: int
    rejected_transmissions: int
    overall_success_rate: float
    tampering_detected_count: int
    replay_detected_count: int
    unauthorized_identity_count: int
    median_plaintext_latency_ms: float
    median_protected_latency_ms: float
    median_encryption_latency_ms: float
    median_decryption_latency_ms: float
    mean_payload_expansion_bytes: float
    mean_payload_expansion_percent: float
    by_payload_category: Dict[str, Any]


class SecurityDemonstrationRequest(BaseModel):
    scenario: str = Field(
        ...,
        description="Scenario type: valid_authorized, attacker_impersonation, tampered_signature, substituted_signature, unauthorized_identity, tampered_ciphertext, tampered_tag, replay_attack, cross_vehicle_substitution, future_timestamp, expired_timestamp"
    )
    vehicle_identifier: Optional[str] = Field("SIM-VEH-001", description="Target vehicle identifier")
