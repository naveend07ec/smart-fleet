from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class IBEStatusResponse(BaseModel):
    status: str
    scheme: str
    curve: str
    pairing_type: str
    symmetric_cipher: str
    key_derivation: str
    public_params_available: bool
    pkg_trust_model: str
    is_simulated_iot_layer: bool

class IBESetupResponse(BaseModel):
    message: str
    scheme: str
    curve: str
    p_pub: Dict[str, Any]
    initialized_at: str

class IBEEncryptRequest(BaseModel):
    recipient_identity: str = Field(..., min_length=3, max_length=100, description="Authorized recipient identity tag")
    payload: str = Field(..., min_length=1, max_length=200000, description="Plaintext telemetry payload (JSON or string)")

class IBEEncryptResponse(BaseModel):
    version: str
    scheme: str
    recipient_identity: str
    u_point: Dict[str, Any]
    salt_b64: str
    nonce_b64: str
    ciphertext_b64: str
    payload_size_bytes: int
    ciphertext_size_bytes: int
    encryption_duration_ms: float

class IBEDecryptRequest(BaseModel):
    recipient_identity: str = Field(..., min_length=3, max_length=100, description="Identity claiming private key decryption")
    ciphertext_bundle: Dict[str, Any] = Field(..., description="Encrypted ciphertext bundle containing u_point, salt, nonce, ciphertext")

class IBEDecryptResponse(BaseModel):
    success: bool
    decrypted_payload: Optional[str] = None
    error: Optional[str] = None
    decryption_duration_ms: float

class IBEExperimentCreateRequest(BaseModel):
    recipient_identity: str = Field(default="traffic-control-hub-01", min_length=3, max_length=100)
    unauthorized_identity: str = Field(default="unauthorized-intruder-node", min_length=3, max_length=100)
    payload: str = Field(..., min_length=1, max_length=200000, description="Telemetry data string or JSON to encrypt")
    notes: Optional[str] = Field(default=None, max_length=255)

class IBEExperimentResponse(BaseModel):
    id: int
    experiment_id: str
    timestamp: datetime
    scheme: str
    recipient_identity: str
    unauthorized_identity: Optional[str] = None
    payload_size_bytes: int
    ciphertext_size_bytes: int
    encryption_duration_ms: float
    decryption_duration_ms: float
    authorized_success: bool
    unauthorized_rejected: bool
    tamper_check_passed: bool
    status: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class IBEExperimentListResponse(BaseModel):
    items: List[IBEExperimentResponse]
    total: int
