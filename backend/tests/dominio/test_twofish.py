"""Bloque Twofish en Python puro (D-20): vectores de prueba oficiales de la especificación."""

import pytest

from chibchaweb.dominio import _twofish

# Known-answer tests de Twofish (ecb_tbl.txt / especificación, apéndice A).
VECTORES = [
    ("00000000000000000000000000000000", "00000000000000000000000000000000", "9F589F5CF6122C32B6BFEC2F2AE8C35A"),
    ("00000000000000000000000000000000", "9F589F5CF6122C32B6BFEC2F2AE8C35A", "D491DB16E7B1C39E86CB086B789F5419"),
    (
        "0123456789ABCDEFFEDCBA98765432100011223344556677",
        "00000000000000000000000000000000",
        "CFD1D2E5A9BE9CDF501F13B892BD2248",
    ),
    (
        "0123456789ABCDEFFEDCBA987654321000112233445566778899AABBCCDDEEFF",
        "00000000000000000000000000000000",
        "37527BE0052334B89F0CFCCAE87CFA20",
    ),
    (
        "0000000000000000000000000000000000000000000000000000000000000000",
        "00000000000000000000000000000000",
        "57FF739D4DC92C1BD7FC01700CC8216F",
    ),
]


@pytest.mark.parametrize(("clave", "texto", "esperado"), VECTORES)
def test_vectores_oficiales(clave, texto, esperado):
    cifrado = _twofish.ClaveTwofish(bytes.fromhex(clave)).cifrar_bloque(bytes.fromhex(texto))
    assert cifrado.hex().upper() == esperado


def test_permutaciones_q_conocidas():
    assert _twofish.Q0[:4] == (0xA9, 0x67, 0xB3, 0xE8)
    assert _twofish.Q1[:4] == (0x75, 0xF3, 0xC6, 0xF4)
    assert sorted(_twofish.Q0) == list(range(256)) and sorted(_twofish.Q1) == list(range(256))


def test_tamanos_invalidos():
    with pytest.raises(ValueError):
        _twofish.ClaveTwofish(b"corta")
    with pytest.raises(ValueError):
        _twofish.ClaveTwofish(bytes(16)).cifrar_bloque(b"123")


def test_ctr_es_simetrico_y_soporta_bloques_parciales():
    clave = _twofish.ClaveTwofish(bytes(range(32)))
    nonce = b"\xff" * 16  # fuerza el desborde del contador
    datos = b"x" * 37
    cifrado = _twofish.flujo_ctr(clave, nonce, datos)
    assert len(cifrado) == 37 and cifrado != datos
    assert _twofish.flujo_ctr(clave, nonce, cifrado) == datos
    # el segundo bloque usa el contador 0 tras desbordar
    assert cifrado[16:32] == bytes(a ^ b for a, b in zip(datos[16:32], clave.cifrar_bloque(bytes(16)), strict=True))
