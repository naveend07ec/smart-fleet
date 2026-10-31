from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.ibe_experiment import IBEExperiment
from app.services.ibe_service import ibe_service
from app.schemas.ibe import (
    IBEStatusResponse,
    IBESetupResponse,
    IBEEncryptRequest,
    IBEEncryptResponse,
    IBEDecryptRequest,
    IBEDecryptResponse,
    IBEExperimentCreateRequest,
    IBEExperimentResponse,
    IBEExperimentListResponse
)

router = APIRouter(prefix="/api/security/ibe", tags=["Identity-Based Encryption (IBE) Lab"])

@router.get("/status", response_model=IBEStatusResponse, summary="Get IBE scheme status and trust model parameters")
def get_ibe_status():
    """
    Returns the current cryptographic configuration, active curve, pairing type,
    and documents the PKG key escrow trust assumptions.
    """
    return ibe_service.get_status()

@router.post("/setup", response_model=IBESetupResponse, summary="Initialize or reload IBE master parameters")
def setup_ibe(force_reinit: bool = Query(False, description="Force regeneration of master secrets")):
    """
    Initializes master public parameters and master secret.
    Notice: Master secret is strictly kept local in secure key storage and is never returned in API responses.
    """
    if force_reinit and ibe_service._master_secret is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unrestricted master key reinitialization is disabled via the public API to prevent catastrophic key loss and historical ciphertext corruption. Administrative reinitialization must be performed directly on local key storage."
        )
    try:
        return ibe_service.setup(force_reinit=force_reinit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup failed: {str(e)}"
        )

@router.post("/encrypt", response_model=IBEEncryptResponse, summary="Encrypt telemetry payload for recipient identity")
def encrypt_payload(payload: IBEEncryptRequest):
    """
    Encrypts a synthetic vehicle telemetry payload using Boneh-Franklin IBE KEM
    paired with authenticated AES-256-GCM.
    """
    try:
        return ibe_service.encrypt(
            identity=payload.recipient_identity,
            payload=payload.payload
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Encryption error: {str(e)}"
        )

@router.post("/decrypt", response_model=IBEDecryptResponse, summary="Attempt decryption using recipient identity")
def decrypt_payload(payload: IBEDecryptRequest):
    """
    Attempts to decrypt the supplied ciphertext bundle using the private key derived
    for the provided recipient identity.
    If the recipient identity does not match the encrypted identity, or if the ciphertext
    is tampered, the operation is cleanly rejected without revealing private keys.
    """
    try:
        result = ibe_service.decrypt(
            ciphertext_bundle=payload.ciphertext_bundle,
            recipient_identity=payload.recipient_identity
        )
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Decryption processing error: {str(e)}"
        )

@router.post("/experiments", response_model=IBEExperimentResponse, status_code=status.HTTP_201_CREATED, summary="Run and persist a scientific IBE evaluation trial")
def create_experiment(payload: IBEExperimentCreateRequest, db: Session = Depends(get_db)):
    """
    Executes a multi-phase verification experiment:
    1. Encrypts payload for recipient_identity.
    2. Verifies authorized decryption with recipient_identity.
    3. Verifies unauthorized decryption rejection with unauthorized_identity.
    4. Verifies tamper resistance (bit-flipped ciphertext tag check).
    5. Measures high-resolution timing and persists the record in the database.
    """
    try:
        experiment = ibe_service.run_experiment(
            db=db,
            recipient_identity=payload.recipient_identity,
            unauthorized_identity=payload.unauthorized_identity,
            payload=payload.payload,
            notes=payload.notes
        )
        return experiment
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Experiment execution error: {str(e)}"
        )

@router.get("/experiments", response_model=IBEExperimentListResponse, summary="List persisted IBE scientific evaluation records")
def list_experiments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(IBEExperiment)
    total = query.count()
    items = (
        query.order_by(desc(IBEExperiment.timestamp))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return IBEExperimentListResponse(items=items, total=total)

@router.get("/experiments/{experiment_id}", response_model=IBEExperimentResponse, summary="Retrieve a specific IBE experiment trial")
def get_experiment_detail(experiment_id: str, db: Session = Depends(get_db)):
    exp = db.query(IBEExperiment).filter(IBEExperiment.experiment_id == experiment_id).first()
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found."
        )
    return exp
