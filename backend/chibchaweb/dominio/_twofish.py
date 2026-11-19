"""Cifrado de bloque Twofish (Schneier et al., 1998) en Python puro. Privado del dominio (D-20).

Solo implementa el cifrado de un bloque de 16 bytes, que es lo que necesita el modo CTR de
``CifradoTwofish``. Se verifica con los vectores de prueba oficiales (tests/dominio/test_twofish.py).
"""

from __future__ import annotations

_MASCARA = 0xFFFFFFFF

# Tablas t de las permutaciones q0 y q1 (especificación, sección 4.3.5).
_T_Q0 = (
    (0x8, 0x1, 0x7, 0xD, 0x6, 0xF, 0x3, 0x2, 0x0, 0xB, 0x5, 0x9, 0xE, 0xC, 0xA, 0x4),
    (0xE, 0xC, 0xB, 0x8, 0x1, 0x2, 0x3, 0x5, 0xF, 0x4, 0xA, 0x6, 0x7, 0x0, 0x9, 0xD),
    (0xB, 0xA, 0x5, 0xE, 0x6, 0xD, 0x9, 0x0, 0xC, 0x8, 0xF, 0x3, 0x2, 0x4, 0x7, 0x1),
    (0xD, 0x7, 0xF, 0x4, 0x1, 0x2, 0x6, 0xE, 0x9, 0xB, 0x3, 0x0, 0x8, 0x5, 0xC, 0xA),
)
_T_Q1 = (
    (0x2, 0x8, 0xB, 0xD, 0xF, 0x7, 0x6, 0xE, 0x3, 0x1, 0x9, 0x4, 0x0, 0xA, 0xC, 0x5),
    (0x1, 0xE, 0x2, 0xB, 0x4, 0xC, 0x3, 0x7, 0x6, 0xD, 0xA, 0x5, 0xF, 0x9, 0x0, 0x8),
    (0x4, 0xC, 0x7, 0x5, 0x1, 0x6, 0x9, 0xA, 0x0, 0xE, 0xD, 0x8, 0x2, 0xB, 0x3, 0xF),
    (0xB, 0x9, 0x5, 0x1, 0xC, 0x3, 0xD, 0xE, 0x6, 0x4, 0x7, 0xF, 0x2, 0x0, 0x8, 0xA),
)

_MDS = ((0x01, 0xEF, 0x5B, 0x5B), (0x5B, 0xEF, 0xEF, 0x01), (0xEF, 0x5B, 0x01, 0xEF), (0xEF, 0x01, 0xEF, 0x5B))
_RS = (
    (0x01, 0xA4, 0x55, 0x87, 0x5A, 0x58, 0xDB, 0x9E),
    (0xA4, 0x56, 0x82, 0xF3, 0x1E, 0xC6, 0x68, 0xE5),
    (0x02, 0xA1, 0xFC, 0xC1, 0x47, 0xAE, 0x3D, 0x19),
    (0xA4, 0x55, 0x87, 0x5A, 0x58, 0xDB, 0x9E, 0x03),
)
_POLI_MDS = 0x169
_POLI_RS = 0x14D


def _ror4(x: int, n: int) -> int:
    return ((x >> n) | (x << (4 - n))) & 0xF


def _q(t: tuple[tuple[int, ...], ...], x: int) -> int:
    a0, b0 = x >> 4, x & 0xF
    a1 = a0 ^ b0
    b1 = a0 ^ _ror4(b0, 1) ^ ((8 * a0) & 0xF)
    a2, b2 = t[0][a1], t[1][b1]
    a3 = a2 ^ b2
    b3 = a2 ^ _ror4(b2, 1) ^ ((8 * a2) & 0xF)
    a4, b4 = t[2][a3], t[3][b3]
    return (b4 << 4) | a4


Q0 = tuple(_q(_T_Q0, x) for x in range(256))
Q1 = tuple(_q(_T_Q1, x) for x in range(256))


def _gf_mult(a: int, b: int, poli: int) -> int:
    resultado = 0
    while b:
        if b & 1:
            resultado ^= a
        a <<= 1
        if a & 0x100:
            a ^= poli
        b >>= 1
    return resultado


def _rol(x: int, n: int) -> int:
    return ((x << n) | (x >> (32 - n))) & _MASCARA


def _ror(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & _MASCARA


def _bytes_de(palabra: int) -> list[int]:
    return [(palabra >> (8 * i)) & 0xFF for i in range(4)]


def _palabra_de(b: list[int] | bytes) -> int:
    return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)


def _cadena_q(y: list[int], lista: list[int]) -> list[int]:
    """Aplica las q y los XOR con las palabras de la lista (función h sin el MDS)."""
    k = len(lista)
    l_ = [_bytes_de(p) for p in lista]
    y = list(y)
    if k == 4:
        y = [Q1[y[0]] ^ l_[3][0], Q0[y[1]] ^ l_[3][1], Q0[y[2]] ^ l_[3][2], Q1[y[3]] ^ l_[3][3]]
    if k >= 3:
        y = [Q1[y[0]] ^ l_[2][0], Q1[y[1]] ^ l_[2][1], Q0[y[2]] ^ l_[2][2], Q0[y[3]] ^ l_[2][3]]
    return [
        Q1[Q0[Q0[y[0]] ^ l_[1][0]] ^ l_[0][0]],
        Q0[Q0[Q1[y[1]] ^ l_[1][1]] ^ l_[0][1]],
        Q1[Q1[Q0[y[2]] ^ l_[1][2]] ^ l_[0][2]],
        Q0[Q1[Q1[y[3]] ^ l_[1][3]] ^ l_[0][3]],
    ]


def _mds(y: list[int]) -> int:
    return _palabra_de(
        [
            _gf_mult(_MDS[i][0], y[0], _POLI_MDS)
            ^ _gf_mult(_MDS[i][1], y[1], _POLI_MDS)
            ^ _gf_mult(_MDS[i][2], y[2], _POLI_MDS)
            ^ _gf_mult(_MDS[i][3], y[3], _POLI_MDS)
            for i in range(4)
        ]
    )


def _h(x: int, lista: list[int]) -> int:
    return _mds(_cadena_q(_bytes_de(x), lista))


class ClaveTwofish:
    """Clave expandida: 40 subclaves y las cajas S dependientes de la clave (con el MDS incluido)."""

    def __init__(self, clave: bytes):
        if len(clave) not in (16, 24, 32):
            raise ValueError("La clave de Twofish debe tener 16, 24 o 32 bytes")
        k = len(clave) // 8
        m = [_palabra_de(clave[4 * i : 4 * i + 4]) for i in range(2 * k)]
        me, mo = m[0::2], m[1::2]
        s = []
        for i in range(k):
            bloque = clave[8 * i : 8 * i + 8]
            fila = [0, 0, 0, 0]
            for r in range(4):
                for c in range(8):
                    fila[r] ^= _gf_mult(_RS[r][c], bloque[c], _POLI_RS)
            s.append(_palabra_de(fila))
        s.reverse()
        rho = 0x01010101
        self.subclaves: list[int] = []
        for i in range(20):
            a = _h((2 * i * rho) & _MASCARA, me)
            b = _rol(_h(((2 * i + 1) * rho) & _MASCARA, mo), 8)
            self.subclaves.append((a + b) & _MASCARA)
            self.subclaves.append(_rol((a + 2 * b) & _MASCARA, 9))
        # g(X) = s0[x0] ^ s1[x1] ^ s2[x2] ^ s3[x3]: cada caja precalcula h para un byte en su posición.
        self.cajas: list[list[int]] = [[0] * 256 for _ in range(4)]
        for x in range(256):
            for pos in range(4):
                y = [0, 0, 0, 0]
                y[pos] = _cadena_q([x] * 4, s)[pos]
                self.cajas[pos][x] = _mds(y)

    def _g(self, x: int) -> int:
        c = self.cajas
        return c[0][x & 0xFF] ^ c[1][(x >> 8) & 0xFF] ^ c[2][(x >> 16) & 0xFF] ^ c[3][x >> 24]

    def cifrar_bloque(self, bloque: bytes) -> bytes:
        if len(bloque) != 16:
            raise ValueError("El bloque de Twofish tiene 16 bytes")
        k = self.subclaves
        r = [_palabra_de(bloque[4 * i : 4 * i + 4]) ^ k[i] for i in range(4)]
        for ronda in range(16):
            t0 = self._g(r[0])
            t1 = self._g(_rol(r[1], 8))
            f0 = (t0 + t1 + k[2 * ronda + 8]) & _MASCARA
            f1 = (t0 + 2 * t1 + k[2 * ronda + 9]) & _MASCARA
            r2 = _ror(r[2] ^ f0, 1)
            r3 = _rol(r[3], 1) ^ f1
            r = [r2, r3, r[0], r[1]]
        salida = [r[(i + 2) % 4] ^ k[i + 4] for i in range(4)]
        return b"".join(p.to_bytes(4, "little") for p in salida)


def flujo_ctr(clave: ClaveTwofish, nonce: bytes, datos: bytes) -> bytes:
    """Modo CTR: el contador de 128 bits empieza en el nonce (big-endian) y se incrementa por bloque."""
    contador = int.from_bytes(nonce, "big")
    salida = bytearray()
    for inicio in range(0, len(datos), 16):
        flujo = clave.cifrar_bloque(contador.to_bytes(16, "big"))
        trozo = datos[inicio : inicio + 16]
        salida.extend(a ^ b for a, b in zip(trozo, flujo, strict=False))
        contador = (contador + 1) % (1 << 128)
    return bytes(salida)
