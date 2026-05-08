from pathlib import Path


class CertificateLoader:
    def __init__(self, cert_dir: str):
        self.cert_dir = Path(cert_dir)

    def load_for_tenant(self, tenant_id: str) -> bytes:
        cert_file = self.cert_dir / f"{tenant_id}.pfx"
        if not cert_file.exists():
            raise FileNotFoundError(f"Certificado não encontrado: {cert_file}")
        return cert_file.read_bytes()
