from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build(target: str = "linux") -> None:
    app_path = ROOT / "certs_app" / "app.py"
    output_dir = ROOT / "dist"
    output_dir.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "CertsPyGenerator",
        str(app_path),
    ]

    if target == "windows":
        cmd.extend(["--icon", str(ROOT / "assets" / "icon.ico")]) if (ROOT / "assets" / "icon.ico").exists() else None
    elif target == "darwin":
        cmd.extend(["--icon", str(ROOT / "assets" / "icon.icns")]) if (ROOT / "assets" / "icon.icns").exists() else None

    subprocess.run(cmd, cwd=str(ROOT), check=True)
    print(f"Ejecutable generado en: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera un ejecutable para la aplicación.")
    parser.add_argument("--target", choices=["linux", "windows", "darwin"], default="linux", help="Plataforma objetivo del empaquetado.")
    args = parser.parse_args()
    build(args.target)
