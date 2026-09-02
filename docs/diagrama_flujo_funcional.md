# Diagrama de flujo de funcionalidades

```mermaid
flowchart TD
    A[Iniciar app] --> B{¿Generar llave?}
    B -->|Sí| C[Ingresar nombre, bits, contraseña]
    C --> D[Generar .key]
    D --> E{¿Generar CSR?}
    E -->|Sí| F[Seleccionar .key y datos del sujeto]
    F --> G[Generar .csr]

    D --> H{¿Quitar contraseña?}
    H -->|Sí| I[Seleccionar .key cifrada]
    I --> J[Generar clave sin contraseña]

    B --> K{¿Verificar par de llaves?}
    K -->|Sí| L[Seleccionar archivos]
    L --> M{Coinciden?}
    M -->|Sí| N[Mostrar coincidencia]
    M -->|No| O[Mostrar error]

    B --> P{¿Normalizar certificado?}
    P -->|Sí| Q[Seleccionar .cer/.pem]
    Q --> R[Convertir o normalizar formato]
    R --> S[Mostrar salida]

    B --> T{¿Concatenar archivos?}
    T -->|Sí| U[Seleccionar archivos]
    U --> V[Concatenar resultados]
    V --> W[Mostrar archivo final]

    B --> X{¿Usar repositorio?}
    X -->|Sí| Y[Guardar/consultar perfiles]
    Y --> Z[Exportar/importar CSV]
    Z --> AA[SQLite]
```

## Resumen del flujo

1. El usuario crea o importa una clave privada.
2. Puede generar un CSR a partir de esa clave.
3. Puede convertir una clave protegida a una sin contraseña.
4. Puede comparar llaves para ver si son compatibles.
5. Puede normalizar certificados para trabajo con PEM o DER.
6. Puede combinar múltiples archivos en una salida final.
7. El repositorio centraliza datos reutilizables y sus respaldos.
