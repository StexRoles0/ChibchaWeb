# Interfaz de usuario

Los mockups (1280×800) están en `docs/ui/mockups/`. Son la referencia visual: el diseño y los textos deben parecerse a ellos, aunque no tienen que coincidir al píxel. El frontend tiene que verse bien desde 1280 px y ser usable en 768 px (el menú lateral se vuelve desplegable).

## Pantallas, rutas y guardas

| Id | Mockup | Ruta Angular | Guarda | CU |
|---|---|---|---|---|
| M-01 | `M01_acceso.png` | `/acceso` | `sinSesion` | AUTH-01/02 |
| — | — | `/auth/callback` | — | AUTH-02 (procesa `code` y `state`, y redirige) |
| M-02 | `M02_registro_datos.png` | `/registro/datos` | `identidadPendiente` | AUTH-03 |
| M-03 | `M03_registro_plan.png` | `/registro/plan` | `identidadPendiente` | AUTH-03 |
| M-04 | `M04_registro_pago.png` | `/registro/pago` | `identidadPendiente` | AUTH-03 |
| M-05 | `M05_inicio_cliente.png` | `/cliente` | `esCliente` | — |
| M-06 | `M06_perfil.png` | `/cliente/perfil` | `esCliente` | CLI-01 |
| M-07 | `M07_modificar_perfil.png` | `/cliente/perfil/editar?pestana=` | `esCliente` | CLI-03 |
| M-08 | `M08_eliminar_perfil.png` | `/cliente/perfil/eliminar` | `esCliente` | CLI-02 |
| M-09 | `M09_dominios.png` | `/cliente/dominios` | `esCliente` | DOM-01/02 |
| M-10 | `M10_soporte.png` | `/soporte/reportar` (cliente: `/cliente/soporte`) | `autenticado` | SOP-01 |
| M-11 | `M11_inicio_gestion.png` | `/gestion` | `operacion('GESTIONAR_EMPLEADOS')` | — |
| M-12 | `M12_empleados.png` | `/gestion/empleados` | ídem | EMP-01, CON-01 |
| M-13 | `M13_form_empleado.png` | `/gestion/empleados/nuevo`, `/gestion/empleados/:id/editar`, `/gestion/distribuidores/nuevo`, `/gestion/distribuidores/:id/editar` | ídem | EMP-02/03, DIS-02/03 |
| M-14 | `M14_detalle_empleado.png` | `/gestion/empleados/:id`, `/gestion/distribuidores/:id` | ídem | CON-02 |
| M-15 | `M15_distribuidores.png` | `/gestion/distribuidores` | `operacion('GESTIONAR_DISTRIBUIDORES')` | DIS-01 |
| M-16 | `M16_clientes.png` | `/gestion/clientes` (+ panel de detalle) | `operacion('CONSULTAR_REGISTROS')` | CON-01/02 |
| M-17 | `M17_bandeja.png` | `/soporte/bandeja`, `/soporte/tickets/:id` | `operacion('ATENDER_TICKETS')` | SOP-02/03 |
| M-18 | `M18_inicio_admin.png` | `/admin` | `operacion('MIGRAR_DATOS')` | — |
| M-19 | `M19_migracion.png` | `/admin/migracion` | ídem | MIG-01 |
| M-20 | `M20_contingencia.png` | `/admin/contingencia` | `operacion('GESTIONAR_CONTINGENCIA')` | RT04 |

La confirmación de baja (EMP-04, DIS-04) es un **diálogo modal**, no una ruta.

## Navegación por rol (del documento de modelado)

- **Después del login:** Cliente → `/cliente`; Gestión → `/gestion`; Soporte → `/soporte/bandeja`; Administrador → `/admin`; sin registrar → `/registro/datos`.
- **Cliente (menú lateral):** Inicio · Mi perfil · Dominios · Soporte · Cerrar sesión.
- **Gestión:** Inicio · Empleados · Distribuidores · Clientes · Reportar novedad · Cerrar sesión.
- **Soporte:** Bandeja de tickets · Reportar novedad · Cerrar sesión.
- **Administrador:** Inicio · Migración · Contingencia · Reportar novedad · Cerrar sesión.
- **Registro:** M-02 → M-03 → M-04, con *Volver* en cada paso. Los datos se guardan en un `RegistroStore` (signal) hasta *Crear cuenta*. *Cancelar registro* → `POST /auth/logout` → M-01.

## Comportamientos que hay que respetar

- **M-02:** nombre y correo llegan ya llenos desde la identidad. El correo es de solo lectura y lleva la marca "✓ Verificado".
- **M-03:** tarjetas de paquete con la tarifa. Al elegir plan se muestra el **monto del periodo** calculado en el cliente con RN-01, solo como vista previa (el backend vuelve a calcular).
- **M-04:** la franquicia se detecta mientras se escribe el número (con los mismos patrones de `seed`), el vencimiento se escribe como `MM/AA` y se envía `AAAA-MM-01`, y el CVV va como `type=password`. Los errores 422 se muestran debajo del campo que indica `campo`.
- **M-07:** tres pestañas (`PERSONAL`, `PAQUETE_PLAN`, `PAGO`). *Guardar* manda solo la pestaña activa.
- **M-09 y M-10:** formulario arriba y tabla del historial abajo. Al enviar se refresca la tabla.
- **M-17:** fecha (por defecto hoy) y lista de tickets. Al seleccionar uno se abre el detalle con los movimientos, la observación (obligatoria) y los botones *Marcar resuelto* / *Escalar de nivel*. *Escalar* se deshabilita si el nivel es el último o si el ticket ya está resuelto.
- **M-19:** el botón *Ejecutar migración real* solo se habilita cuando hay un proceso `SIMULADA`. El log se muestra en una tabla con el nivel en color (INFO verde, ADVERTENCIA oro, ERROR rojo).
- **M-20:** radio con los 4 algoritmos y *Aplicar*, más la tabla de pendientes y *Sincronizar respaldo*.
- **503 `CONTINGENCIA`:** banner global de color oro: "El sistema está en modo contingencia; tu operación quedó respaldada y se aplicará al restablecerse el servicio."
- **401:** el interceptor manda a `/acceso`. **403:** página "No tienes permiso".

## Tokens de diseño (de `mock/app.css`)

```scss
:root {
  --verde: #0E5A4B;  --verde-2: #127A64;  --verde-claro: #E3F1EC;
  --oro: #D99A1E;    --oro-claro: #FBF1DC;
  --tinta: #18231F;  --tinta-2: #4B5A55;  --tinta-3: #7B8A85;
  --linea: #DCE3E0;  --fondo: #F4F6F5;    --blanco: #FFFFFF;
  --rojo: #B42318;   --rojo-claro: #FDECEA;
  --azul: #1F5FAD;   --azul-claro: #E6EEF8;
  --radio: 10px;
}
```

- Tipografía **Inter** de 14 px, con títulos de 22–24 px y peso 700.
- Barra superior verde (`--verde`) de 60 px con la marca "Chibcha**WEB**" ("WEB" en `--oro`) y el avatar oro. Menú lateral blanco de 224 px, con el ítem activo en `--verde-claro`.
- Tarjetas blancas con borde `--linea` y radio de 10 px. Campos de 40 px de alto con foco de 2 px en `--verde-2`.
- Etiquetas de estado: ABIERTO/REGISTRADA en azul, ESCALADO/SIMULADA en oro, RESUELTO/ENVIADA/EJECUTADA/EXITOSO en verde, y FALLIDA/REVERTIDA/FALLIDO/CANCELADA en rojo.
- No uses Angular Material. Usa estilos propios con estos tokens en `src/styles/` para que se parezca a los mockups.
