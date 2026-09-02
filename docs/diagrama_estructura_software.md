# Diagrama de estructura del software

```mermaid
flowchart TD
    A[Usuario] --> B[Interfaz Tkinter]
    B --> C[certs_app/app.py]
    C --> D[certs_app/openssl_utils.py]
    C --> E[certs_app/storage.py]
    D --> F[OpenSSL]
    E --> G[(SQLite: certs_subjects.db)]
    E --> H[CSV de respaldo]
    C --> I[tests/]
    C --> J[scripts/build_exe.py]
    J --> K[PyInstaller]
    K --> L[Exe Windows/Linux/macOS]
```

## Descripción

- La capa de interfaz de usuario recoge los datos del usuario y los distribuye a las funciones de negocio.
- `openssl_utils.py` es la capa de integración con OpenSSL.
- `storage.py` centraliza la persistencia del repositorio de perfiles.
- `build_exe.py` prepara el empaquetado para producir un ejecutable portable.
