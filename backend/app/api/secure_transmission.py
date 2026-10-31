from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.secure_transmission import SecureTransmission, VehicleEnrollment
from app.services.secure_transmission_service import secure_transmission_service
from app.schemas.secure_transmission import (
    VehicleEnrollmentCreate, VehicleEnrollmentResponse,
    PlaintextTransmissionRequest, EncryptedTransmissionRequest,
    TransmissionResponse, TransmissionListResponse,
    ExperimentRunRequest, ExperimentRunResponse,
    TransmissionAnalyticsResponse, SecurityDemonstrationRequest
)

router = APIRouter(prefix="/api/secure-transmission", tags=["Secure Vehicle-to-Server Transmission"])

@router.post(
    "/enroll",
    response_model=VehicleEnrollmentResponse,
    summary="Enroll or re-authorize a vehicle for secure transmission"
)
def enroll_vehicle(payload: VehicleEnrollmentCreate, db: Session = Depends(get_db)):
    """
    Registers a vehicle's cryptographic identity in the PKG access control registry.
    Enforces that only authorized, enrolled vehicles can transmit telemetry.
    """
    try:
        enrollment = secure_transmission_service.enroll_vehicle(
            db=db,
            vehicle_identifier=payload.vehicle_identifier,
            assigned_identity=payload.assigned_identity,
            notes=payload.notes
        )
        return enrollment
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Enrollment failed: {str(e)}")

@router.get(
    "/enrollments",
    response_model=List[VehicleEnrollmentResponse],
    summary="List all enrolled vehicles"
)
def list_enrollments(db: Session = Depends(get_db)):
    """Retrieves all active and revoked vehicle identity enrollments."""
    secure_transmission_service.ensure_default_enrollments(db)
    return db.query(VehicleEnrollment).order_by(VehicleEnrollment.id.asc()).all()

@router.post(
    "/plaintext",
    response_model=TransmissionResponse,
    summary="Mode A: Ingest conventional unencrypted JSON telemetry baseline"
)
def receive_plaintext_telemetry(payload: PlaintextTransmissionRequest, db: Session = Depends(get_db)):
    """
    Conventional Baseline Mode:
    Ingests vehicle telemetry in readable JSON over HTTP.
    Measures transmission size, latency, verifies freshness, and persists telemetry.
    """
    try:
        return secure_transmission_service.process_plaintext_transmission(db=db, request=payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plaintext transmission ingestion error: {str(e)}"
        )

@router.post(
    "/encrypted",
    response_model=TransmissionResponse,
    summary="Mode B: Ingest IBE-protected encrypted telemetry envelope"
)
def receive_encrypted_telemetry(payload: EncryptedTransmissionRequest, db: Session = Depends(get_db)):
    """
    IBE-Protected Mode:
    Ingests vehicle telemetry encrypted with Boneh-Franklin IBE-KEM over BN128 paired with AES-256-GCM.
    Authenticates sender identity, verifies freshness against replay sliding window,
    decrypts payload using recipient private key, validates AAD binding, and persists telemetry.
    """
    try:
        return secure_transmission_service.process_encrypted_transmission(db=db, request=payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encrypted transmission processing error: {str(e)}"
        )

@router.post(
    "/demonstration",
    response_model=TransmissionResponse,
    summary="Execute a controlled security demonstration attack scenario"
)
def run_security_demonstration(payload: SecurityDemonstrationRequest, db: Session = Depends(get_db)):
    """
    Executes an interactive security test:
    - valid_authorized: Legitimate encrypted transmission with Ed25519 signature
    - attacker_impersonation: Attacker creates fresh envelope claiming enrolled vehicle ID (lacking Ed25519 private key)
    - tampered_signature: 1-byte alteration in Ed25519 signature string
    - substituted_signature: Vehicle A signature attached to Vehicle B transmission
    - unauthorized_identity: Unenrolled identity submission
    - tampered_ciphertext: Bit-flipped ciphertext body
    - tampered_tag: Bit-flipped AEAD authentication tag
    - replay_attack: Duplicate transmission resubmission
    - cross_vehicle_substitution: Vehicle A submits telemetry claiming Vehicle B
    - future_timestamp: Clock drift tampering (>30s into future)
    - expired_timestamp: Expired message outside sliding freshness window
    """
    try:
        return secure_transmission_service.execute_security_demonstration(
            db=db,
            scenario=payload.scenario,
            vehicle_identifier=payload.vehicle_identifier or "SIM-VEH-001"
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security demonstration execution error: {str(e)}"
        )

@router.post(
    "/experiments/run",
    response_model=ExperimentRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute an automated, repeatable batch experiment"
)
def run_experiment_batch(payload: ExperimentRunRequest, db: Session = Depends(get_db)):
    """
    Executes a reproducible scientific benchmark comparing Mode A (plaintext)
    and Mode B (IBE-protected) across configurable vehicle counts and payload categories.
    Computes statistical latencies, overhead, and success rates.
    """
    try:
        return secure_transmission_service.run_batch_experiment(
            db=db,
            vehicle_count=payload.vehicle_count,
            messages_per_vehicle=payload.messages_per_vehicle,
            mode=payload.mode,
            payload_category=payload.payload_category,
            notes=payload.notes
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Experiment batch execution failed: {str(e)}"
        )

@router.get(
    "/experiments",
    response_model=TransmissionListResponse,
    summary="List persisted transmission experiment records"
)
def list_transmissions(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    mode: Optional[str] = Query(None, description="Filter by mode: plaintext, ibe_protected"),
    status_filter: Optional[str] = Query(None, description="Filter by status: success, rejected"),
    batch_id: Optional[str] = Query(None, description="Filter by batch ID"),
    db: Session = Depends(get_db)
):
    query = db.query(SecureTransmission)
    if mode:
        query = query.filter(SecureTransmission.transmission_mode == mode)
    if status_filter:
        query = query.filter(SecureTransmission.status == status_filter)
    if batch_id:
        query = query.filter(SecureTransmission.batch_id == batch_id)

    total = query.count()
    items = query.order_by(desc(SecureTransmission.created_at)).offset((page - 1) * limit).limit(limit).all()
    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return TransmissionListResponse(
        items=[secure_transmission_service._record_to_response(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get(
    "/experiments/{transmission_id}",
    response_model=TransmissionResponse,
    summary="Retrieve a specific transmission experiment detail"
)
def get_transmission_detail(transmission_id: str, db: Session = Depends(get_db)):
    tx = db.query(SecureTransmission).filter(SecureTransmission.transmission_id == transmission_id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transmission record '{transmission_id}' not found."
        )
    return secure_transmission_service._record_to_response(tx)

@router.get(
    "/analytics",
    response_model=TransmissionAnalyticsResponse,
    summary="Get aggregated scientific comparative analytics"
)
def get_transmission_analytics(db: Session = Depends(get_db)):
    """Computes median latencies, expansion percentages, and security rejection totals."""
    return secure_transmission_service.get_analytics(db=db)

@router.get(
    "/security-events",
    response_model=List[TransmissionResponse],
    summary="Get audit log of rejected security events (tampering, replays, unauthorized identities)"
)
def list_security_events(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Returns transmission records that failed security checks for audit inspection."""
    events = (
        db.query(SecureTransmission)
        .filter(SecureTransmission.status != "success")
        .order_by(desc(SecureTransmission.created_at))
        .limit(limit)
        .all()
    )
    return [secure_transmission_service._record_to_response(e) for e in events]
