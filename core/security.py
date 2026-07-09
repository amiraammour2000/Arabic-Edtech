# core/security.py
import hashlib
import qrcode
import io
import base64
from datetime import datetime
from loguru import logger


class SecurityService:

    @staticmethod
    def generate_hash(text: str, salt: str = "") -> str:
        raw = f"{text}-{salt}-{datetime.now().isoformat()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_qr_code(data: str) -> str:
        """Génère un QR code en base64 pour intégration PDF/HTML."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    @staticmethod
    def generate_watermark(text: str = "ARABIC EDTECH PRO") -> str:
        """Texte de filigrane pour le PDF."""
        return text