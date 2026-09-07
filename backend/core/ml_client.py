"""
Thin async HTTP client for calling the ml-service (FastAPI, port 8001).
Every call degrades gracefully: if the ML service is unreachable, callers get
a clear `MLServiceError` instead of a raw connection exception, so routers can
decide whether to fail the request or fall back to manual review.
"""
import httpx

from core.config import settings


class MLServiceError(Exception):
    def __init__(self, message: str, status_code: int = 503):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class MLClient:
    def __init__(self, base_url: str | None = None, timeout: float = 15.0):
        self.base_url = (base_url or settings.ML_SERVICE_URL).rstrip("/")
        self.timeout = timeout

    async def _post(self, path: str, json: dict | None = None, files: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=json, files=files)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise MLServiceError(f"ML service returned {exc.response.status_code} for {path}", exc.response.status_code)
        except httpx.RequestError as exc:
            raise MLServiceError(f"ML service unreachable at {path}: {exc}", 503)

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except httpx.RequestError:
            return False

    async def fuzzy_match(self, name1: str, address1: str, name2: str, address2: str) -> dict:
        return await self._post(
            "/ml/fuzzy-match",
            json={"name1": name1, "address1": address1, "name2": name2, "address2": address2},
        )

    async def ocr_extract(self, file_bytes: bytes, filename: str, content_type: str) -> dict:
        return await self._post(
            "/ml/ocr-extract",
            files={"file": (filename, file_bytes, content_type)},
        )

    async def face_match(
        self,
        selfie_bytes: bytes,
        selfie_name: str,
        id_photo_bytes: bytes,
        id_photo_name: str,
    ) -> dict:
        return await self._post(
            "/ml/face-match",
            files={
                "selfie": (selfie_name, selfie_bytes, "image/jpeg"),
                "id_photo": (id_photo_name, id_photo_bytes, "image/jpeg"),
            },
        )

    async def risk_score(
        self,
        age: int,
        income: float,
        existing_loans: int,
        avg_monthly_txn: float,
        txn_stability_score: float,
        business_type: str,
    ) -> dict:
        return await self._post(
            "/ml/risk-score",
            json={
                "age": age,
                "income": income,
                "existing_loans": existing_loans,
                "avg_monthly_txn": avg_monthly_txn,
                "txn_stability_score": txn_stability_score,
                "business_type": business_type,
            },
        )

    async def fraud_check(self, citizen_id: str, application_metadata: dict) -> dict:
        return await self._post(
            "/ml/fraud-check",
            json={"citizen_id": citizen_id, "application_metadata": application_metadata},
        )

    async def scheme_recommend(self, age: int, income_band: str, category: str, business_type: str) -> dict:
        return await self._post(
            "/ml/scheme-recommend",
            json={"age": age, "income_band": income_band, "category": category, "business_type": business_type},
        )


ml_client = MLClient()