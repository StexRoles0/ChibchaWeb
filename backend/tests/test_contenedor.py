"""Composition root: arma mapeadores, adaptadores y gestor según la configuración."""

import pytest

from chibchaweb.adaptadores import simulados
from chibchaweb.dominio.migracion import CreadorClienteLegado, CreadorHostingLegado, CreadorPagoLegado
from chibchaweb.persistencia import mapeadores
from config.contenedor import contenedor


@pytest.fixture(autouse=True)
def limpiar_cache():
    contenedor.cache_clear()
    yield
    contenedor.cache_clear()


def test_armar_el_contenedor_no_necesita_la_bd():
    """Sin la marca django_db, cualquier consulta fallaría: el contenedor debe poder armarse con la BD caída."""
    c = contenedor()
    assert c is contenedor()  # uno por proceso
    assert isinstance(c.usuarios, mapeadores.MapeadorUsuario)
    assert isinstance(c.suscripciones, mapeadores.MapeadorSuscripcion)
    assert isinstance(c.comisiones, mapeadores.MapeadorComision)
    assert isinstance(c.solicitudes, mapeadores.MapeadorSolicitudDominio)
    assert isinstance(c.tickets, mapeadores.MapeadorTicket)
    assert isinstance(c.migraciones, mapeadores.MapeadorMigracion)
    assert isinstance(c.catalogo, mapeadores.MapeadorCatalogo)


def test_un_solo_gestor_compartido_por_los_mapeadores_que_respaldan():
    c = contenedor()
    for mapeador in (c.usuarios, c.suscripciones, c.comisiones, c.solicitudes):
        assert mapeador._gestor is c.gestor
    assert [a.nombre() for a in c.gestor.algoritmos] == ["AES", "ChaCha20", "Camellia", "Twofish"]


def test_el_algoritmo_y_la_ruta_salen_de_la_configuracion(settings, tmp_path):
    settings.ALGORITMO_CIFRADO = "Twofish"
    settings.RUTA_RESPALDO = str(tmp_path / "r.log")
    gestor = contenedor().gestor
    assert gestor.algoritmo_activo == "Twofish" and gestor.medio.ruta == str(tmp_path / "r.log")


def test_con_simular_externos_usa_los_adaptadores_simulados(settings):
    settings.SIMULAR_EXTERNOS = True
    c = contenedor()
    assert isinstance(c.proveedor_autenticacion, simulados.ProveedorAutenticacionSimulado)
    assert isinstance(c.validador_medio_pago, simulados.ValidadorMedioPagoSimulado)
    assert isinstance(c.pasarela_pago, simulados.PasarelaPagoSimulada)
    assert isinstance(c.registrador_dominio, simulados.RegistradorDominioSimulado)
    assert isinstance(c.fuente_legada, simulados.FuenteLegadaSimulada)


@pytest.mark.django_db
def test_los_creadores_de_migracion_se_crean_al_usarse_con_el_catalogo_de_la_bd():
    c = contenedor()
    assert [type(x) for x in c.creadores_migracion] == [CreadorClienteLegado, CreadorHostingLegado, CreadorPagoLegado]
    assert [x.tipo() for x in c.creadores_migracion] == ["CLIENTE", "HOSTING", "PAGO"]
    assert c.migraciones._creadores is c.creadores_migracion


@pytest.mark.django_db
def test_la_migracion_simulada_con_la_fuente_y_los_creadores_del_contenedor():
    from chibchaweb.dominio.migracion import ProcesoMigracion

    c = contenedor()
    admin = c.usuarios.buscar_empleados("admin@")[0]
    proceso = ProcesoMigracion(admin, list(c.creadores_migracion))
    proceso.simular(c.fuente_legada)
    c.migraciones.insertar(proceso)
    leido = c.migraciones.buscar_por_id(proceso.id)
    assert leido.estado.value == "SIMULADA" and len(leido.log) == len(proceso.log) > 20
    assert proceso.cantidad_validos() == 15 and proceso.cantidad_invalidos() == 17


def test_propiedades_gestor_y_creadores_del_modelo():
    c = contenedor()
    assert c.usuarios.gestor is c.gestor and c.tickets.gestor is c.gestor
    assert c.migraciones.creadores is c.creadores_migracion
    assert c.usuarios.nombre_tabla == "usuario"


def test_el_contenedor_arma_los_11_servicios_con_repositorios_nunca_mapeadores():
    from chibchaweb.servicio import servicios

    c = contenedor()
    nombres = [n for n in dir(c) if n.startswith("servicio_")]
    assert len(nombres) == 11
    for nombre in nombres:
        assert isinstance(getattr(c, nombre), getattr(servicios, "".join(p.title() for p in nombre.split("_"))))
    assert c.servicio_soporte._consultas is c.servicio_consultas
