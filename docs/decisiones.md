# Decisiones técnicas

Cada decisión nueva se agrega al final con su número. Las que cambian el modelo de EA también van en `pendientes-modelo.md`.

| # | Decisión | Motivo |
|---|---|---|
| D-01 | **Repositorios en el dominio** (Separated Interface). Los servicios dependen de `RepositorioX`; los mapeadores los implementan. | DC-SRV-01 hacía que el servicio dependiera de los mapeadores. El flujo correcto es frontend → servicio → dominio ← persistencia. |
| D-02 | **Contenedor manual** en `config/contenedor.py` (sin biblioteca de DI). | Con 11 servicios alcanza. Es explícito y fácil de revisar. |
| D-03 | **Esquema SQL como fuente de verdad**; ORM `managed=False`, sin migraciones de Django para el negocio. | El modelo ER ya está aprobado en el documento. Las migraciones de Django solo cubren las apps internas (`sessions`, `contenttypes`). |
| D-04 | **Sesión de Django + CSRF** en lugar de JWT. | Mismo origen y cookie HttpOnly. Guardar la identidad pendiente del registro es simple. |
| D-05 | **OIDC con Google** como proveedor real (`AdaptadorOAuth` con `authlib`). En desarrollo se usa `ProveedorAutenticacionSimulado`, donde el código `dev:<correo>` devuelve una identidad verificada con `sub = "dev|<correo>"`. | Así se puede probar sin credenciales. Cambia por configuración (`SIMULAR_EXTERNOS`). |
| D-06 | **Adaptadores simulados** en `adaptadores/simulados.py`. Validador: rechaza tarjetas que terminan en `0002`. Pasarela: rechaza las que terminan en `0341` y devuelve `REF-<uuid8>` en los demás casos. Registrador: rechaza dominios que contienen `rechazo`. Fuente legada: lee `backend/datos_legados/*.csv` (clientes, hosting, pagos), donde hay filas válidas e inválidas. | Hacen posibles los flujos alternos y las pruebas e2e. Son otras implementaciones de las mismas interfaces del dominio (Adapter). |
| D-07 | **Cifrado:** `cryptography` para AES-256-GCM, ChaCha20-Poly1305 y Camellia-256-CBC (+HMAC); el paquete `twofish` para el bloque Twofish, en modo CTR implementado dentro de `CifradoTwofish` (+HMAC). Formato: `nonce‖cifrado‖tag` en base64. | `cryptography` no trae Twofish. Si `twofish` no compila en la imagen, se usa `pycryptodomex` como alternativa, pero se avisa antes. |
| D-08 | **Montos con `Decimal`**, en JSON como string. | Evita errores de redondeo en tarifas y comisiones. |
| D-09 | **Tareas programadas como management commands** (`chibchaweb/tareas/management/commands/`), programadas con `supercronic` en el contenedor `tareas`. | FAC-01 y COM-01/02 son del actor Tiempo. No tienen pantalla. |
| D-10 | **Transacción por petición** con el decorador `@transaccional` en la vista. `UnidadDeTrabajo` solo para la migración. | Así el servicio no importa `django.db`. |
| D-11 | `pais` de las direcciones = `"Colombia"` por defecto. | `DatosClienteDTO` no tiene país y la columna es `NOT NULL`. |
| D-12 | El correo del registro sale de la identidad verificada y no se puede editar. El nombre sí se puede editar en M-02. | RN-05. |
| D-13 | Angular **standalone + signals**, estilos propios con los tokens de `ui.md`, sin Angular Material. | Para parecerse a los mockups. |
| D-14 | Pruebas: `pytest` + `pytest-django`; dominio sin BD; servicios con repositorios en memoria (`tests/falsos.py`); integración contra PostgreSQL real (docker). Frontend: Jest/Karma para unidades y Playwright para e2e. | Pirámide de pruebas alineada con las capas. |
