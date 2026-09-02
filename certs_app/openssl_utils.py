from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Sequence


def build_key_filename(name: str, password: bool) -> str:
    clean_name = Path(name).stem.strip()
    clean_name = clean_name.replace("_pass", "").replace("_nopass", "").replace("_no_pass", "")
    clean_name = clean_name.strip("_") or "certificate"
    suffix = "_pass.key" if password else "_nopass.key"
    return f"{clean_name}{suffix}"


def build_csr_filename(name: str) -> str:
    clean_name = Path(name).stem.strip()
    clean_name = clean_name.replace("_req", "").replace("_pass", "").replace("_nopass", "").replace("_no_pass", "")
    clean_name = clean_name.strip("_") or "certificate"
    return f"{clean_name}_req.csr"


def build_cert_filename(name: str, year: int | None = None) -> str:
    clean_name = Path(name).stem.strip()
    clean_name = clean_name.replace("_cert", "").replace("_req", "").replace("_pass", "").replace("_nopass", "").replace("_no_pass", "")
    clean_name = clean_name.strip("_") or "certificate"
    actual_year = year or datetime.now().year
    return f"{clean_name}_cert_{actual_year}.pem"


def build_bundle_filename(name: str, year: int | None = None, extension: str = ".pem") -> str:
    clean_name = Path(name).stem.strip()
    clean_name = clean_name.replace("_cert", "").replace("_bundle", "").replace("_combined", "")
    actual_year = year or datetime.now().year
    ext = extension if extension.startswith(".") else f".{extension}"
    return f"{clean_name}_cert_{actual_year}{ext}"


def _openssl(*args: str) -> str:
    openssl_bin = shutil.which("openssl")
    if not openssl_bin:
        raise FileNotFoundError("OpenSSL no está instalado o no está disponible en PATH.")

    result = subprocess.run(
        [openssl_bin, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Error al ejecutar OpenSSL."
        raise RuntimeError(message)
    return result.stdout.strip()


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def generate_private_key(key_path: str, password: str | None = None, rsa_bits: int = 2048) -> str:
    key_path = str(Path(key_path))
    _ensure_parent(key_path)

    cmd = ["genpkey", "-algorithm", "RSA", "-pkeyopt", f"rsa_keygen_bits:{rsa_bits}", "-out", key_path]
    if password:
        cmd.extend(["-aes-256-cbc", "-pass", f"pass:{password}"])
    _openssl(*cmd)
    return key_path


def generate_csr(key_path: str, csr_path: str, subject: Dict[str, str], password: str | None = None) -> str:
    csr_path = str(Path(csr_path))
    _ensure_parent(csr_path)
    _require_private_key_password(key_path, password, "generar el CSR")

    sanitized = {k: str(v).strip() for k, v in subject.items() if v not in (None, "")}
    subject_parts = []
    for key in ["C", "ST", "L", "O", "OU", "CN", "emailAddress"]:
        if key in sanitized:
            subject_parts.append(f"/{key}={sanitized[key]}")
    subject_string = "".join(subject_parts)
    cmd = ["req", "-new", "-sha256", "-key", key_path, "-out", csr_path, "-subj", subject_string]
    if password:
        cmd.extend(["-passin", f"pass:{password}"])
    _openssl(*cmd)
    return csr_path


def remove_key_password(encrypted_key_path: str, output_path: str, password: str | None = None) -> str:
    output_path = str(Path(output_path))
    _ensure_parent(output_path)
    _require_private_key_password(encrypted_key_path, password, "quitar la contraseña de la clave")

    cmd = ["pkey", "-in", encrypted_key_path, "-out", output_path]
    if password:
        cmd.extend(["-passin", f"pass:{password}"])
    _openssl(*cmd)
    return output_path


def _public_key_from_private_key(private_key_path: str, password: str | None = None) -> str:
    cmd = ["pkey", "-in", private_key_path, "-pubout"]
    if password:
        cmd.extend(["-passin", f"pass:{password}"])
    return _openssl(*cmd)


def _public_key_from_certificate(cert_path: str) -> str:
    return _openssl("x509", "-in", cert_path, "-pubkey", "-noout")


def _public_key_from_csr(csr_path: str) -> str:
    return _openssl("req", "-in", csr_path, "-pubkey", "-noout")


def _detect_certificate_text(path: str) -> bool:
    try:
        data = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    upper = data.upper()
    return (
        ("BEGIN CERTIFICATE" in upper or "BEGIN X509 CERTIFICATE" in upper)
        and "CERTIFICATE REQUEST" not in upper
        and "NEW CERTIFICATE REQUEST" not in upper
    )


def _detect_csr_text(path: str) -> bool:
    try:
        data = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    upper = data.upper()
    return "CERTIFICATE REQUEST" in upper or "NEW CERTIFICATE REQUEST" in upper


def _is_encrypted_private_key(path: str) -> bool:
    try:
        data = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return "BEGIN ENCRYPTED PRIVATE KEY" in data.upper()


def _require_private_key_password(path: str, password: str | None, action: str) -> None:
    if password is None and _is_encrypted_private_key(path):
        raise ValueError(f"La clave privada está cifrada; se requiere la contraseña para {action}.")


def verify_key_pair_match(file_a: str, file_b: str, password_a: str | None = None, password_b: str | None = None) -> bool:
    if not os.path.exists(file_a) or not os.path.exists(file_b):
        raise FileNotFoundError("Ambos archivos deben existir para comparar la clave.")

    if _detect_certificate_text(file_a):
        a_public = _public_key_from_certificate(file_a)
    elif _detect_csr_text(file_a):
        a_public = _public_key_from_csr(file_a)
    else:
        _require_private_key_password(file_a, password_a, "comparar la clave")
        a_public = _public_key_from_private_key(file_a, password_a)

    if _detect_certificate_text(file_b):
        b_public = _public_key_from_certificate(file_b)
    elif _detect_csr_text(file_b):
        b_public = _public_key_from_csr(file_b)
    else:
        _require_private_key_password(file_b, password_b, "comparar la clave")
        b_public = _public_key_from_private_key(file_b, password_b)

    return a_public.strip() == b_public.strip()


def normalize_certificate_file(cert_path: str, output_path: str | None = None) -> str:
    source = Path(cert_path)
    if not source.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {cert_path}")

    if output_path is None:
        target = source.with_suffix(".pem")
    else:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

    raw = source.read_bytes()
    text = raw.decode("utf-8", errors="ignore")

    if "BEGIN CERTIFICATE" in text.upper() or "BEGIN X509 CERTIFICATE" in text.upper():
        target.write_text(text.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8")
        return str(target)

    if raw.startswith(b"0\x82") or b"-----BEGIN" not in raw:
        _openssl("x509", "-inform", "DER", "-in", str(source), "-out", str(target))
        return str(target)

    target.write_text(text.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8")
    return str(target)


def concatenate_files(paths: Sequence[str], output_path: str) -> str:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8", newline="") as out_file:
        for idx, item in enumerate(paths):
            path = Path(item)
            if not path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {item}")
            with path.open("r", encoding="utf-8", errors="surrogateescape") as in_file:
                content = in_file.read()
            out_file.write(content)
    return str(destination)
