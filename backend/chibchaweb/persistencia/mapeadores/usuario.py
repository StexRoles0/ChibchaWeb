"""MapeadorUsuario: agregado Usuario (cliente, empleado, distribuidor) con direcciones, tarjeta y cuenta."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db import transaction
from django.db.models import Q

from chibchaweb.dominio.cuentas import Cliente, Distribuidor, Empleado, TarjetaCredito, Usuario
from chibchaweb.dominio.errores import NoEncontradoError, ValidacionError
from chibchaweb.dominio.repositorios import RepositorioUsuario
from chibchaweb.dominio.respaldo import GestorContingencia
from chibchaweb.persistencia.mapeadores._cargador import (
    RELACIONES_CLIENTE,
    Cargador,
    cifrar_numero,
)
from chibchaweb.persistencia.mapeadores.base import (
    Mapeador,
    a_fecha,
    a_fecha_hora,
    a_json,
    actualizado,
    con_contingencia,
    de_json,
    iso,
    traducir_fallas_de_lectura,
    traducir_restauracion,
    traducir_unico,
)
from chibchaweb.persistencia.modelos_orm import (
    ZONA,
    ClienteOrm,
    CuentaAccesoOrm,
    DireccionOrm,
    DistribuidorOrm,
    EmpleadoOrm,
    MedioPagoOrm,
    SitioWebOrm,
    SuscripcionOrm,
    TarjetaCreditoOrm,
    UsuarioOrm,
)

_TIPOS = ((Cliente, "CLIENTE"), (Empleado, "EMPLEADO"), (Distribuidor, "DISTRIBUIDOR"))


@traducir_fallas_de_lectura
class MapeadorUsuario(Mapeador[Usuario], RepositorioUsuario):
    """Respalda los datos sensibles del cliente ante una caída de la BD (RT04)."""

    def __init__(self, gestor: GestorContingencia):
        super().__init__("usuario")
        self._gestor = gestor

    @property
    def gestor(self) -> GestorContingencia:
        return self._gestor

    # --- Mapeador<Usuario> ----------------------------------------------------------------------
    def insertar(self, objeto: Usuario) -> int:
        datos = self._a_datos(objeto, "insertar", con_ids=False)
        respaldo = a_json(datos)  # antes de escribir: los ids que asigne la BD no forman parte del respaldo
        datos.pop(
            "suscripciones", None
        )  # solo viajan en el respaldo: en el flujo normal las guarda MapeadorSuscripcion

        def accion() -> int:
            traducir_unico(lambda: self._escribir_insertar(datos))
            return datos["id"]

        id = con_contingencia(self._gestor, "Usuario.insertar", lambda: respaldo, accion)
        self._asignar_ids(objeto, datos)
        return id

    def actualizar(self, objeto: Usuario) -> None:
        datos = self._a_datos(objeto, "actualizar", con_ids=True)
        respaldo = a_json(datos)
        con_contingencia(
            self._gestor,
            "Usuario.actualizar",
            lambda: respaldo,
            lambda: traducir_unico(lambda: self._escribir_actualizar(datos)),
        )
        self._asignar_ids(objeto, datos)

    def buscar_por_id(self, id: int) -> Usuario:
        usuarios = self._cargador().usuarios([id])
        if not usuarios:
            raise NoEncontradoError(f"No existe el usuario {id}")
        return usuarios[0]

    def buscar_por_filtro(self, filtro: str) -> list[Usuario]:
        return self._cargar(self._filtrar(UsuarioOrm.objects.all(), filtro))

    # --- RepositorioUsuario ---------------------------------------------------------------------
    def buscar_por_identificador_externo(self, identificador: str) -> Usuario | None:
        cuenta = CuentaAccesoOrm.objects.filter(identificador_externo=(identificador or "").strip()).first()
        return self._uno(cuenta.titular_id) if cuenta else None

    def buscar_distribuidor_por_codigo(self, codigo: str) -> Distribuidor | None:
        fila = (
            DistribuidorOrm.objects.filter(codigo=(codigo or "").strip(), usuario__activo=True)
            .select_related("usuario")
            .first()
        )
        if fila is None:
            return None
        return self._cargador().distribuidores([fila])[0]

    def inactivar(self, id: int) -> None:
        filas = UsuarioOrm.objects.filter(id=id).update(activo=False, fecha_modificacion=datetime.now(ZONA))
        actualizado(filas, "el usuario", id)

    def buscar_por_correo(self, correo: str) -> Usuario | None:
        fila = UsuarioOrm.objects.filter(correo=(correo or "").strip().lower()).first()
        return self._uno(fila.id) if fila else None

    def buscar_clientes(self, filtro: str) -> list[Cliente]:
        return self._cargar(self._filtrar(UsuarioOrm.objects.filter(tipo="CLIENTE"), filtro))  # type: ignore[return-value]

    def buscar_empleados(self, filtro: str) -> list[Empleado]:
        return self._cargar(self._filtrar(UsuarioOrm.objects.filter(tipo="EMPLEADO"), filtro))  # type: ignore[return-value]

    def buscar_distribuidores(self, filtro: str) -> list[Distribuidor]:
        return self._cargar(self._filtrar(UsuarioOrm.objects.filter(tipo="DISTRIBUIDOR"), filtro))  # type: ignore[return-value]

    @traducir_restauracion
    def restaurar(self, contenido: str) -> None:
        """Reinserta o actualiza el agregado respaldado; no vuelve a respaldar."""
        datos = de_json(contenido)
        escribir = self._escribir_insertar if datos["_operacion"] == "insertar" else self._escribir_actualizar
        with transaction.atomic():
            traducir_unico(lambda: escribir(datos))

    # --- consultas ------------------------------------------------------------------------------
    def _cargador(self) -> Cargador:
        return Cargador(self._gestor)

    def _uno(self, id: int) -> Usuario:
        return self._cargador().usuarios([id])[0]

    def _cargar(self, consulta) -> list[Usuario]:
        return self._cargador().usuarios(list(consulta.order_by("id").values_list("id", flat=True)))

    @staticmethod
    def _filtrar(consulta, filtro: str):
        texto = (filtro or "").strip()
        if not texto:
            return consulta
        return consulta.filter(
            Q(nombre__icontains=texto)
            | Q(correo__icontains=texto)
            | Q(empleado__documento__icontains=texto)
            | Q(distribuidor__documento__icontains=texto)
            | Q(distribuidor__codigo__icontains=texto)
        )

    # --- dominio -> datos (JSON-seguros) --------------------------------------------------------
    def _a_datos(self, u: Usuario, operacion: str, con_ids: bool) -> dict[str, Any]:
        def i(objeto) -> int | None:
            return objeto.id if con_ids and objeto is not None else None

        datos: dict[str, Any] = {
            "_operacion": operacion,
            "tipo": next(nombre for clase, nombre in _TIPOS if isinstance(u, clase)),
            "id": i(u),
            "nombre": u.nombre,
            "correo": u.correo,
            "telefono": u.telefono,
            "activo": u.activo,
            "fecha_registro": iso(u.fecha_registro),
            "fecha_modificacion": iso(u.fecha_modificacion),
            "cuenta": None,
        }
        if u.cuenta is not None:
            c = u.cuenta
            datos["cuenta"] = {
                "id": i(c),
                "identificador_externo": c.identificador_externo,
                "proveedor": c.proveedor,
                "fecha_vinculacion": iso(c.fecha_vinculacion),
                "ultimo_acceso": iso(c.ultimo_acceso),
            }
        if isinstance(u, Cliente):
            tarjeta = u.medio_pago
            if not isinstance(tarjeta, TarjetaCredito):
                raise ValidacionError("medioPago", "Solo se admiten tarjetas de crédito")
            if tarjeta.franquicia.id is None:
                raise ValidacionError("franquicia", "La franquicia debe venir del catálogo")
            datos["residencia"] = self._direccion_a_datos(u.residencia, i(u.residencia))
            datos["facturacion"] = self._direccion_a_datos(u.facturacion, i(u.facturacion))
            # El código de seguridad nunca se guarda ni se respalda (RN-12); el número viaja cifrado por el gestor.
            datos["medio_pago"] = {
                "id": i(tarjeta),
                "numero": tarjeta.numero,
                "vencimiento": iso(tarjeta.vencimiento),
                "id_franquicia": tarjeta.franquicia.id,
            }
            datos["id_distribuidor"] = u.distribuidor.id if u.distribuidor is not None else None
            if operacion == "insertar":
                # RT04: si la BD cae al registrar, el respaldo del cliente nuevo lleva su suscripción para que
                # ``restaurar`` recree ambos (en el flujo normal las suscripciones las inserta MapeadorSuscripcion).
                datos["suscripciones"] = [
                    self._suscripcion_a_datos(s)
                    for s in u.suscripciones
                    if s.paquete.id is not None and s.plan.id is not None
                ]
        elif isinstance(u, Empleado):
            datos.update(documento=u.documento, id_rol=u.rol.id)
        elif isinstance(u, Distribuidor):
            datos.update(documento=u.documento, codigo=u.codigo)
        return datos

    @staticmethod
    def _suscripcion_a_datos(s) -> dict[str, Any]:
        return {
            "sitio": {
                "subdominio": s.sitio.subdominio,
                "dominio_propio": s.sitio.dominio_propio,
                "plataforma": s.sitio.plataforma.value,
            },
            "id_paquete": s.paquete.id,
            "id_plan": s.plan.id,
            "fecha_inicio": iso(s.fecha_inicio),
            "fecha_corte": iso(s.fecha_corte),
            "activa": s.activa,
        }

    @staticmethod
    def _direccion_a_datos(d, id: int | None) -> dict[str, Any]:
        return {"id": id, "linea": d.linea, "ciudad": d.ciudad, "codigo_postal": d.codigo_postal, "pais": d.pais}

    @staticmethod
    def _asignar_ids(objeto: Usuario, datos: dict[str, Any]) -> None:
        """Copia al dominio los ids que asignó la BD (solo a los objetos que aún no tenían)."""
        pares = [(objeto, datos)]
        if objeto.cuenta is not None:
            pares.append((objeto.cuenta, datos["cuenta"]))
        if isinstance(objeto, Cliente):
            pares += [
                (objeto.residencia, datos["residencia"]),
                (objeto.facturacion, datos["facturacion"]),
                (objeto.medio_pago, datos["medio_pago"]),
            ]
        for destino, origen in pares:
            if destino.id is None and origen["id"] is not None:
                destino.id = origen["id"]

    # --- datos -> filas -------------------------------------------------------------------------
    def _escribir_insertar(self, d: dict[str, Any]) -> None:
        fila = UsuarioOrm(
            tipo=d["tipo"],
            nombre=d["nombre"],
            correo=d["correo"],
            telefono=d["telefono"],
            activo=d["activo"],
            fecha_registro=a_fecha_hora(d["fecha_registro"]),
            fecha_modificacion=a_fecha_hora(d["fecha_modificacion"]),
        )
        fila.save(force_insert=True)
        d["id"] = fila.id
        if d["tipo"] == "CLIENTE":
            for clave in ("residencia", "facturacion"):
                self._insertar_direccion(d[clave])
            self._insertar_tarjeta(d["medio_pago"])
            ClienteOrm(
                usuario_id=fila.id,
                residencia_id=d["residencia"]["id"],
                facturacion_id=d["facturacion"]["id"],
                medio_pago_id=d["medio_pago"]["id"],
                distribuidor_id=d["id_distribuidor"],
            ).save(force_insert=True)
        elif d["tipo"] == "EMPLEADO":
            EmpleadoOrm(usuario_id=fila.id, documento=d["documento"], rol_id=d["id_rol"]).save(force_insert=True)
        else:
            DistribuidorOrm(usuario_id=fila.id, documento=d["documento"], codigo=d["codigo"]).save(force_insert=True)
        if d["cuenta"] is not None:
            self._insertar_cuenta(fila.id, d["cuenta"])
        for suscripcion in d.get("suscripciones", []):  # solo al restaurar un respaldo
            self._insertar_suscripcion(fila.id, suscripcion)

    @staticmethod
    def _insertar_suscripcion(id_titular: int, d: dict[str, Any]) -> None:
        sitio = d["sitio"]
        fila_sitio = SitioWebOrm(
            subdominio=sitio["subdominio"], dominio_propio=sitio["dominio_propio"], plataforma=sitio["plataforma"]
        )
        fila_sitio.save(force_insert=True)
        SuscripcionOrm(
            titular_id=id_titular,
            sitio_id=fila_sitio.id,
            paquete_id=d["id_paquete"],
            plan_id=d["id_plan"],
            fecha_inicio=a_fecha(d["fecha_inicio"]),
            fecha_corte=a_fecha(d["fecha_corte"]),
            activa=d["activa"],
        ).save(force_insert=True)

    def _escribir_actualizar(self, d: dict[str, Any]) -> None:
        id = d["id"]
        actualizado(
            UsuarioOrm.objects.filter(id=id).update(
                nombre=d["nombre"],
                correo=d["correo"],
                telefono=d["telefono"],
                activo=d["activo"],
                fecha_modificacion=a_fecha_hora(d["fecha_modificacion"]),
            ),
            "el usuario",
            id,
        )
        if d["tipo"] == "EMPLEADO":
            EmpleadoOrm.objects.filter(usuario_id=id).update(documento=d["documento"], rol_id=d["id_rol"])
        elif d["tipo"] == "DISTRIBUIDOR":
            DistribuidorOrm.objects.filter(usuario_id=id).update(documento=d["documento"], codigo=d["codigo"])
        else:
            self._actualizar_cliente(id, d)
        cuenta = d["cuenta"]
        if cuenta is not None:
            if cuenta["id"] is None:
                self._insertar_cuenta(id, cuenta)
            else:
                CuentaAccesoOrm.objects.filter(id=cuenta["id"]).update(
                    ultimo_acceso=a_fecha_hora(cuenta["ultimo_acceso"])
                )

    def _actualizar_cliente(self, id: int, d: dict[str, Any]) -> None:
        actual = ClienteOrm.objects.filter(usuario_id=id).first()
        if actual is None:
            raise NoEncontradoError(f"No existe el cliente {id}")
        obsoletos_direcciones: list[int] = []
        for clave, campo in (("residencia", "residencia_id"), ("facturacion", "facturacion_id")):
            direccion = d[clave]
            if direccion["id"] is None:
                obsoletos_direcciones.append(getattr(actual, campo))
                self._insertar_direccion(direccion)
            else:
                DireccionOrm.objects.filter(id=direccion["id"]).update(
                    linea=direccion["linea"],
                    ciudad=direccion["ciudad"],
                    codigo_postal=direccion["codigo_postal"],
                    pais=direccion["pais"],
                )
        medio = d["medio_pago"]
        medio_obsoleto = None
        if medio["id"] is None:
            medio_obsoleto = actual.medio_pago_id
            self._insertar_tarjeta(medio)
        else:
            algoritmo, cifrado = cifrar_numero(self._gestor, medio["numero"])
            TarjetaCreditoOrm.objects.filter(medio_id=medio["id"]).update(
                numero_cifrado=cifrado,
                algoritmo_cifrado=algoritmo,
                ultimos_digitos=medio["numero"][-4:],
                vencimiento=a_fecha(medio["vencimiento"]),
                franquicia_id=medio["id_franquicia"],
            )
        ClienteOrm.objects.filter(usuario_id=id).update(
            residencia_id=d["residencia"]["id"],
            facturacion_id=d["facturacion"]["id"],
            medio_pago_id=medio["id"],
            distribuidor_id=d["id_distribuidor"],
        )
        # Lo reemplazado ya no lo referencia nadie: no se conservan datos de tarjeta ni direcciones huérfanas.
        if medio_obsoleto is not None:
            TarjetaCreditoOrm.objects.filter(medio_id=medio_obsoleto).delete()
            MedioPagoOrm.objects.filter(id=medio_obsoleto).delete()
        if obsoletos_direcciones:
            DireccionOrm.objects.filter(id__in=obsoletos_direcciones).delete()

    @staticmethod
    def _insertar_direccion(d: dict[str, Any]) -> None:
        fila = DireccionOrm(linea=d["linea"], ciudad=d["ciudad"], codigo_postal=d["codigo_postal"], pais=d["pais"])
        fila.save(force_insert=True)
        d["id"] = fila.id

    def _insertar_tarjeta(self, m: dict[str, Any]) -> None:
        medio = MedioPagoOrm(tipo="TARJETA")
        medio.save(force_insert=True)
        algoritmo, cifrado = cifrar_numero(self._gestor, m["numero"])
        TarjetaCreditoOrm(
            medio_id=medio.id,
            numero_cifrado=cifrado,
            algoritmo_cifrado=algoritmo,
            ultimos_digitos=m["numero"][-4:],
            vencimiento=a_fecha(m["vencimiento"]),
            franquicia_id=m["id_franquicia"],
        ).save(force_insert=True)
        m["id"] = medio.id

    @staticmethod
    def _insertar_cuenta(id_titular: int, c: dict[str, Any]) -> None:
        fila = CuentaAccesoOrm(
            titular_id=id_titular,
            identificador_externo=c["identificador_externo"],
            proveedor=c["proveedor"],
            fecha_vinculacion=a_fecha_hora(c["fecha_vinculacion"]),
            ultimo_acceso=a_fecha_hora(c["ultimo_acceso"]),
        )
        fila.save(force_insert=True)
        c["id"] = fila.id


__all__ = ["RELACIONES_CLIENTE", "MapeadorUsuario"]
