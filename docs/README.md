# Documentación de CertsPyGenerator

## Objetivo

CertsPyGenerator es una aplicación de escritorio (Python + Tkinter + OpenSSL) para crear, validar, transformar y combinar artefactos relacionados con certificados digitales.

## Funcionalidades principales

1. Generación de clave privada `.key`
   - Con contraseña o sin contraseña.
   - Generación con RSA configurable mediante tamaño de bits.

2. Eliminación de contraseña de una clave
   - Permite convertir una clave cifrada en una equivalente sin cifrado.

3. Generación de CSR
   - Se usa la clave privada seleccionada.
   - Se admite personalización del sujeto con campos como `C`, `ST`, `L`, `O`, `OU`, `CN` y `emailAddress`.

4. Repositorio de perfiles
   - Se almacenan parámetros en SQLite.
   - Se puede exportar/importar un respaldo CSV.

5. Verificación de coincidencia
   - Compara pares de llaves para verificar si pertenecen al mismo conjunto.
   - Muestra mensajes de coincidencia o error.

6. Normalización de certificados
   - Detecta archivos `.cer`, `.crt` o `.pem`.
   - Se adapta a formato Unix/DOS y PEM.

7. Concatenación de archivos
   - Permite mezclar archivos CSR, certificados y otros artefactos para obtener un resultado final visible.

8. Empaquetado ejecutable
   - Compatible con la lógica de PyInstaller para Windows, Linux y macOS.

## Requisitos del sistema

- Python 3.11+
- OpenSSL instalado y accesible en `PATH`
- Tkinter incluido en la instalación estándar de Python

## Estructura del software

- `certs_app/app.py`: interfaz gráfica.
- `certs_app/openssl_utils.py`: lógica de OpenSSL.
- `certs_app/storage.py`: base de datos y CSV.
- `scripts/build_exe.py`: empaquetado de ejecutables.
- `tests/`: pruebas de validación.

## Flujos principales

- Generación de clave -> CSR -> verificación -> concatenación.
- Perfil almacenado en repositorio -> uso para CSR -> exportación/importación.
- Certificado importado -> normalización -> uso posterior.

## Limitaciones conocidas

- La creación del ejecutable debe hacerse en la plataforma objetivo o mediante herramientas de cross-compiling.
- La validación de clave/certificado requiere que los archivos realmente correspondan al mismo par.
- OpenSSL debe estar instalado en el sistema.
