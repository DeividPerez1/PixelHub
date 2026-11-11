"""Script to generate Certification Authority (CA), server, and client certificates."""

from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crypto_utils import CERTS_DIR, ensure_certificates_exist, load_certificate_from_pem


def main() -> None:
    print(f"Generating certificates in: {CERTS_DIR}")
    ensure_certificates_exist(CERTS_DIR)

    print("\nCertificates successfully generated:")
    for pem_file in sorted(CERTS_DIR.glob("*.pem")):
        if "cert" in pem_file.name:
            cert = load_certificate_from_pem(pem_file.read_bytes())
            common_name = cert.subject.rfc4514_string()
            print(f" - {pem_file.name}: Subject: {common_name}")
        else:
            print(f" - {pem_file.name}: (Private Key)")


if __name__ == "__main__":
    main()
