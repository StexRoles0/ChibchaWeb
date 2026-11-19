"""RT04: ServicioContingencia con el gestor real (archivo plano en tmp_path) y repositorios en memoria."""

import pytest

from chibchaweb.dominio.errores import ContingenciaActivaError, ReglaNegocioError, ValidacionError
from chibchaweb.servicio.dto import ResumenDTO

EVENTOS = [
    ("Usuario.insertar", '{"correo":"a@b.co","numero_tarjeta":"4242424242424242"}'),
    ("Suscripcion.registrar_pago", '{"pago":1}'),
    ("Comision.registrar_cheque", '{"cheque":1}'),
    ("SolicitudDominio.insertar", '{"nombre":"x"}'),
    ("Usuario.actualizar", '{"nombre":"Z"}'),
]


@pytest.fixture
def con_pendientes(gestor):
    for tipo, contenido in EVENTOS:
        gestor.respaldar(tipo, contenido)


# --- consultar_respaldo_pendiente (P-06) -------------------------------------------------------
def test_sin_eventos_no_hay_pendientes(contingencia):
    assert contingencia.consultar_respaldo_pendiente() == []


def test_p06_lista_tipo_y_algoritmo_en_el_orden_escrito(contingencia, gestor, con_pendientes):
    gestor.cambiar_algoritmo("Twofish")
    gestor.respaldar("Usuario.actualizar", "{}")
    pendientes = contingencia.consultar_respaldo_pendiente()
    assert [(p.id, p.titulo, p.subtitulo, p.estado) for p in pendientes] == [
        *[(i, tipo, "AES", "PENDIENTE") for i, (tipo, _) in enumerate(EVENTOS, 1)],
        (6, "Usuario.actualizar", "Twofish", "PENDIENTE"),
    ]
    assert all(isinstance(p, ResumenDTO) for p in pendientes)


def test_p06_no_expone_el_contenido_ni_descifra(contingencia, gestor, con_pendientes, monkeypatch):
    def prohibido():
        raise AssertionError("consultar no debe descifrar nada")

    monkeypatch.setattr(gestor, "recuperar_pendientes", prohibido)
    texto = repr(contingencia.consultar_respaldo_pendiente())
    assert "4242" not in texto and "a@b.co" not in texto


def test_una_linea_con_formato_invalido_se_muestra_como_tal(contingencia, gestor):
    gestor.medio.escribir("basura")
    (fila,) = contingencia.consultar_respaldo_pendiente()
    assert (fila.titulo, fila.estado) == ("(formato inválido)", "INVALIDO")


# --- sincronizar_respaldo (RN-30, D-27) --------------------------------------------------------
def test_sin_eventos_sincroniza_cero_sin_abrir_transaccion(contingencia, unidad):
    assert contingencia.sincronizar_respaldo() == 0
    assert unidad.llamadas == []


def test_rn30_reinserta_en_orden_cada_evento_en_su_repositorio_y_vacia_el_medio(
    contingencia, gestor, con_pendientes, usuarios, suscripciones, comisiones, solicitudes, unidad
):
    assert contingencia.sincronizar_respaldo() == 5
    assert usuarios.restaurados == [EVENTOS[0][1], EVENTOS[4][1]]
    assert suscripciones.restaurados == [EVENTOS[1][1]]
    assert comisiones.restaurados == [EVENTOS[2][1]]
    assert solicitudes.restaurados == [EVENTOS[3][1]]
    assert unidad.llamadas == ["iniciar", "confirmar"]
    assert gestor.medio.leer_pendientes() == [] and contingencia.consultar_respaldo_pendiente() == []


def test_rn30_si_un_evento_falla_se_revierte_todo_no_se_vacia_el_medio_y_se_informa_cuantos_iban(
    contingencia, gestor, con_pendientes, usuarios, suscripciones, unidad
):
    suscripciones.fallar_restaurar_en = 0  # el segundo evento (el primero de suscripciones) falla
    with pytest.raises(ReglaNegocioError) as error:
        contingencia.sincronizar_respaldo()
    mensaje = error.value.mensaje
    assert "evento 2 de 5" in mensaje and "Se procesaron 1 de 5" in mensaje and "Suscripcion.registrar_pago" in mensaje
    assert "4242" not in mensaje
    assert unidad.llamadas == ["iniciar", "revertir"]  # nunca se confirmó
    assert len(gestor.medio.leer_pendientes()) == 5  # el medio no se vació


def test_d27_reintentar_tras_un_fallo_procesa_todo_desde_el_primer_evento(
    contingencia, gestor, con_pendientes, suscripciones
):
    suscripciones.fallar_restaurar_en = 0
    with pytest.raises(ReglaNegocioError):
        contingencia.sincronizar_respaldo()
    suscripciones.fallar_restaurar_en = None
    assert contingencia.sincronizar_respaldo() == 5
    assert gestor.medio.leer_pendientes() == []


def test_un_evento_de_un_tipo_desconocido_detiene_y_revierte(contingencia, gestor, unidad):
    gestor.respaldar("Ticket.insertar", "{}")
    with pytest.raises(ReglaNegocioError, match="Ticket.insertar"):
        contingencia.sincronizar_respaldo()
    assert unidad.llamadas == ["iniciar", "revertir"] and len(gestor.medio.leer_pendientes()) == 1


def test_un_error_de_infraestructura_revierte_y_se_propaga_sin_vaciar_el_medio(
    contingencia, gestor, con_pendientes, usuarios, unidad
):
    usuarios.fallar_con = None

    def cae(contenido):
        raise ConnectionError("la BD sigue caída")

    usuarios.restaurar = cae
    with pytest.raises(ConnectionError):
        contingencia.sincronizar_respaldo()
    assert unidad.llamadas == ["iniciar", "revertir"] and len(gestor.medio.leer_pendientes()) == 5


def test_si_revertir_tambien_falla_se_propaga_el_error_original(contingencia, gestor, con_pendientes, usuarios, unidad):
    usuarios.restaurar = lambda c: (_ for _ in ()).throw(ConnectionError("caída"))

    def rota():
        raise RuntimeError("conexión rota")

    unidad.revertir = rota
    with pytest.raises(ConnectionError):
        contingencia.sincronizar_respaldo()


def test_contingencia_activa_al_restaurar_se_propaga(contingencia, gestor, con_pendientes, usuarios):
    usuarios.restaurar = lambda c: (_ for _ in ()).throw(ContingenciaActivaError("BD caída"))
    with pytest.raises(ContingenciaActivaError):
        contingencia.sincronizar_respaldo()


def test_un_respaldo_alterado_no_se_sincroniza(contingencia, gestor, con_pendientes, unidad):
    ruta = gestor.medio.ruta
    texto = open(ruta, encoding="utf-8").read().replace("Usuario.insertar", "Usuario.actualizar", 1)
    open(ruta, "w", encoding="utf-8").write(texto)
    with pytest.raises(ReglaNegocioError):
        contingencia.sincronizar_respaldo()
    assert unidad.llamadas == []


# --- cambiar_algoritmo_cifrado (RN-29) ---------------------------------------------------------
@pytest.mark.parametrize("nombre", ["AES", "ChaCha20", "Camellia", "Twofish"])
def test_rn29_cambia_el_algoritmo_activo(contingencia, gestor, nombre):
    assert contingencia.cambiar_algoritmo_cifrado(nombre) is None
    assert gestor.algoritmo_activo == nombre


@pytest.mark.parametrize("nombre", ["DES", "", "aes", None])
def test_rn29_un_algoritmo_desconocido_es_validacion_en_el_campo_nombre(contingencia, gestor, nombre):
    with pytest.raises(ValidacionError) as error:
        contingencia.cambiar_algoritmo_cifrado(nombre)
    assert error.value.campo == "nombre" and gestor.algoritmo_activo == "AES"


def test_rn29_los_eventos_cifrados_con_un_algoritmo_anterior_se_sincronizan_tras_cambiarlo(
    contingencia, gestor, usuarios
):
    gestor.respaldar("Usuario.insertar", '{"a":1}')  # AES
    contingencia.cambiar_algoritmo_cifrado("ChaCha20")
    gestor.respaldar("Usuario.actualizar", '{"b":2}')  # ChaCha20
    assert [p.subtitulo for p in contingencia.consultar_respaldo_pendiente()] == ["AES", "ChaCha20"]
    assert contingencia.sincronizar_respaldo() == 2
    assert usuarios.restaurados == ['{"a":1}', '{"b":2}']


def test_d27_un_evento_malformado_es_un_evento_fallido_y_tras_corregirlo_se_reintenta(
    contingencia, gestor, usuarios, unidad
):
    """Los mapeadores traducen el contenido inválido a ``ReglaNegocioError``: el servicio lo trata como cualquier
    evento fallido (revierte, conserva el medio, informa K de M) y el reintento posterior procesa todo."""
    gestor.respaldar("Usuario.insertar", "{}")
    gestor.respaldar("Usuario.actualizar", '{"_operacion":"actualizar","id":9999}')
    usuarios.fallar_restaurar_en = 1
    with pytest.raises(ReglaNegocioError) as error:
        contingencia.sincronizar_respaldo()
    assert "evento 2 de 2" in error.value.mensaje and "Se procesaron 1 de 2" in error.value.mensaje
    assert unidad.llamadas == ["iniciar", "revertir"] and len(gestor.medio.leer_pendientes()) == 2
    usuarios.fallar_restaurar_en = None  # el administrador corrige el respaldo
    assert contingencia.sincronizar_respaldo() == 2
    assert gestor.medio.leer_pendientes() == []
