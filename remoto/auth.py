"""Autenticação por palavra-passe/código de sessão e limite de tentativas."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import deque
from typing import Callable

# Sem caracteres ambíguos (0/O, 1/I/L) para ser fácil de ditar ao telefone.
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
COMPRIMENTO_MIN_PALAVRA_PASSE = 8


def gerar_codigo(grupos: int = 3, tamanho: int = 4) -> str:
    """Gera um código de sessão aleatório, p.ex. ``K7PQ-M3XA-9RTV`` (~59 bits)."""
    return "-".join(
        "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(tamanho)) for _ in range(grupos)
    )


def normalizar_codigo(texto: str) -> str:
    """Aceita o código com ou sem hífenes/espaços e em minúsculas."""
    return "".join(c for c in texto.upper() if c not in "- \t")


def _derivar(palavra_passe: str, sal: bytes) -> bytes:
    return hashlib.scrypt(palavra_passe.encode("utf-8"), salt=sal, n=2**14, r=8, p=1, dklen=32)


class Verificador:
    """Guarda apenas o *hash* (scrypt) da palavra-passe e compara em tempo constante."""

    def __init__(self, palavra_passe: str, normalizar: Callable[[str], str] | None = None):
        self._normalizar = normalizar or (lambda s: s)
        self._sal = secrets.token_bytes(16)
        self._hash = _derivar(self._normalizar(palavra_passe), self._sal)

    def verificar(self, tentativa: str) -> bool:
        return hmac.compare_digest(_derivar(self._normalizar(tentativa), self._sal), self._hash)


class LimitadorTentativas:
    """Bloqueia um endereço após ``max_falhas`` falhas dentro de ``janela`` segundos.

    Há também um limite global (todas as origens somadas) para travar
    ataques distribuídos por muitos IPs.
    """

    def __init__(
        self,
        max_falhas: int = 5,
        janela: float = 300.0,
        bloqueio: float = 300.0,
        max_falhas_global: int = 30,
        relogio: Callable[[], float] = time.monotonic,
    ):
        self.max_falhas = max_falhas
        self.janela = janela
        self.bloqueio = bloqueio
        self.max_falhas_global = max_falhas_global
        self._relogio = relogio
        self._falhas: dict[str, deque[float]] = {}
        self._bloqueados: dict[str, float] = {}
        self._falhas_global: deque[float] = deque()
        self._bloqueio_global_ate = 0.0

    def _limpar(self, fila: deque[float], agora: float) -> None:
        while fila and agora - fila[0] > self.janela:
            fila.popleft()

    def segundos_bloqueado(self, origem: str) -> float:
        """0 se a origem pode tentar; caso contrário, segundos até poder voltar a tentar."""
        agora = self._relogio()
        ate = max(self._bloqueados.get(origem, 0.0), self._bloqueio_global_ate)
        return max(0.0, ate - agora)

    def registar_falha(self, origem: str) -> None:
        agora = self._relogio()
        fila = self._falhas.setdefault(origem, deque())
        fila.append(agora)
        self._limpar(fila, agora)
        if len(fila) >= self.max_falhas:
            self._bloqueados[origem] = agora + self.bloqueio
            fila.clear()
        self._falhas_global.append(agora)
        self._limpar(self._falhas_global, agora)
        if len(self._falhas_global) >= self.max_falhas_global:
            self._bloqueio_global_ate = agora + self.bloqueio
            self._falhas_global.clear()

    def registar_sucesso(self, origem: str) -> None:
        self._falhas.pop(origem, None)
