from fastapi import APIRouter, UploadFile, File
import numpy as np
import io
from PIL import Image

router = APIRouter(prefix="/ml", tags=["Face Match"])

def get_image_grayscale(image_bytes: bytes):
    """Loads image bytes into a normalized grayscale numpy array using PIL."""
    image = Image.open(io.BytesIO(image_bytes)).convert("L")
    # Standardize image size for structural comparison
    image = image.resize((150, 150))
    arr = np.asarray(image, dtype=np.float32)
    # Normalize pixel values
    arr = (arr - np.mean(arr)) / (np.std(arr) + 1e-5)
    return arr

def compute_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """Computes Normalized Cross-Correlation between the two images."""
    correlation = np.mean(img1 * img2)
    # Scale and clip score between 0.0 and 1.0
    score = (correlation + 1.0) / 2.0
    return round(float(np.clip(score, 0.0, 1.0)), 2)

@router.post("/face-match")
async def face_match(
    selfie: UploadFile = File(...),
    id_photo: UploadFile = File(...)
):
    try:
        selfie_bytes = await selfie.read()
        id_bytes = await id_photo.read()

        if not selfie_bytes or not id_bytes:
            return {
                "is_matched": False,
                "similarity_score": 0.0,
                "confidence": "none",
                "message": "Both live camera capture and ID document photo are required."
            }

        arr_selfie = get_image_grayscale(selfie_bytes)
        arr_id = get_image_grayscale(id_bytes)

        score = compute_similarity(arr_selfie, arr_id)

        # Baseline threshold for identity match
        is_matched = score >= 0.50
        confidence = "high" if score >= 0.70 else ("medium" if score >= 0.50 else "low")

        return {
            "is_matched": is_matched,
            "similarity_score": score,
            "confidence": confidence,
            "message": "Identity verification successful." if is_matched else "Face does not match the identity record."
        }

    except Exception as e:
        return {
            "is_matched": False,
            "similarity_score": 0.0,
            "confidence": "none",
            "message": f"Verification error: {str(e)}"
        }