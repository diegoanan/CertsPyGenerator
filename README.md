# CertsPyGenerator

Aplicación de escritorio en Python para gestionar claves, solicitudes CSR, certificados y validación con OpenSSL.

## Características

- Generación de claves privadas `.key` con o sin contraseña.
- Eliminación de contraseña de un `.key` cifrado para obtener una clave sin protección.
- Generación de archivos `.csr` enlazados a la clave privada seleccionada.
- Repositorio de perfiles de sujeto para reutilizar parámetros de solicitud.
- Almacenamiento en SQLite con respaldo/exportación a CSV.
- Verificación de coincidencia entre pares de llaves o entre clave y certificado.
- Normalización de archivos `.cer` o `.pem` reconociendo formato DOS/Unix y PEM.
- Concatenación de archivos `.req`, `.pem`, `.cer`, `.crt` para formar un paquete final.
- Empaquetado con PyInstaller para Windows, Linux y macOS.

## Requisitos

- Python 3.11+
- OpenSSL instalado y disponible en `PATH`
- `pip install -r requirements.txt`

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar la aplicación

```bash
python -m certs_app.app
```

## Construir ejecutable

```bash
python scripts/build_exe.py --target linux
python scripts/build_exe.py --target windows
python scripts/build_exe.py --target darwin
```

> Nota: PyInstaller compila para el sistema operativo actual. Para generar binarios para Windows o macOS desde otra plataforma, se requiere una herramienta específica de cross-compiling o ejecutar PyInstaller en la plataforma objetivo.

## Estructura principal

- `certs_app/app.py`: interfaz gráfica.
- `certs_app/openssl_utils.py`: wrappers de OpenSSL.
- `certs_app/storage.py`: repositorio SQLite/CSV.
- `scripts/build_exe.py`: empaquetado con PyInstaller.
- `docs/`: documentación y diagramas.

## Licencia

Proyecto de ejemplo para generación y manejo de certificados con OpenSSL.
