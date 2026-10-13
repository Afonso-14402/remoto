"""Protocolo de mensagens entre cliente e agente.

Tudo passa por um único WebSocket (wss://<agente>/ws):

* mensagens **binárias** (agente → cliente) são frames do ecrã em JPEG;
* mensagens de **texto** são JSON, nos dois sentidos (canal de controlo).

As coordenadas do rato são sempre relativas (0 a 1) ao monitor partilhado;
o agente converte-as para píxeis reais. Ver ``docs/PROTOCOLO.md``.
"""

from __future__ import annotations

import json
import math
from typing import Any

# Tamanho máximo de uma mensagem de texto vinda do cliente (bytes).
TAMANHO_MAX_MENSAGEM = 4096
TEXTO_MAX = 256

BOTOES = frozenset({"esquerdo", "direito", "meio"})
ACOES = frozenset({"baixo", "cima"})
QUALIDADE_MIN, QUALIDADE_MAX = 10, 95
SCROLL_MAX = 20


class ErroProtocolo(ValueError):
    """Mensagem mal formada ou com valores inválidos."""


def _relativo(msg: dict, campo: str) -> float:
    v = msg.get(campo)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ErroProtocolo(f"'{campo}' tem de ser um número")
    return min(1.0, max(0.0, float(v)))


def _inteiro(msg: dict, campo: str, minimo: int, maximo: int) -> int:
    v = msg.get(campo)
    if isinstance(v, bool) or not isinstance(v, int):
        raise ErroProtocolo(f"'{campo}' tem de ser um inteiro")
    return min(maximo, max(minimo, v))


def _escolha(msg: dict, campo: str, opcoes: frozenset, omissao: str | None = None) -> str:
    v = msg.get(campo, omissao)
    if not isinstance(v, str) or v not in opcoes:
        raise ErroProtocolo(f"'{campo}' inválido")
    return v


def _texto(msg: dict, campo: str, maximo: int) -> str:
    v = msg.get(campo)
    if not isinstance(v, str) or not v or len(v) > maximo:
        raise ErroProtocolo(f"'{campo}' tem de ser texto com 1 a {maximo} caracteres")
    return v


def descodificar(dados: str) -> dict[str, Any]:
    """Converte texto JSON vindo do cliente numa mensagem validada e normalizada."""
    if len(dados) > TAMANHO_MAX_MENSAGEM:
        raise ErroProtocolo("mensagem demasiado grande")
    try:
        msg = json.loads(dados)
    except (json.JSONDecodeError, RecursionError) as e:
        raise ErroProtocolo("JSON inválido") from e
    if not isinstance(msg, dict):
        raise ErroProtocolo("a mensagem tem de ser um objeto JSON")
    return validar(msg)


def validar(msg: dict[str, Any]) -> dict[str, Any]:
    tipo = msg.get("tipo")
    if tipo == "autenticar":
        pw = msg.get("palavra_passe")
        if not isinstance(pw, str) or len(pw) > 256:
            raise ErroProtocolo("'palavra_passe' inválida")
        return {"tipo": tipo, "palavra_passe": pw}
    if tipo == "rato_mover":
        return {"tipo": tipo, "x": _relativo(msg, "x"), "y": _relativo(msg, "y")}
    if tipo == "rato_clique":
        out = {"tipo": tipo, "botao": _escolha(msg, "botao", BOTOES, "esquerdo"), "acao": None}
        if "acao" in msg:
            out["acao"] = _escolha(msg, "acao", ACOES)
        if "x" in msg or "y" in msg:
            out["x"], out["y"] = _relativo(msg, "x"), _relativo(msg, "y")
        return out
    if tipo == "rato_scroll":
        dx = _inteiro(msg, "dx", -SCROLL_MAX, SCROLL_MAX) if "dx" in msg else 0
        dy = _inteiro(msg, "dy", -SCROLL_MAX, SCROLL_MAX) if "dy" in msg else 0
        return {"tipo": tipo, "dx": dx, "dy": dy}
    if tipo == "tecla":
        return {"tipo": tipo, "valor": _texto(msg, "valor", 32), "acao": _escolha(msg, "acao", ACOES)}
    if tipo == "texto":
        return {"tipo": tipo, "valor": _texto(msg, "valor", TEXTO_MAX)}
    if tipo == "libertar_tudo":
        return {"tipo": tipo}
    if tipo == "qualidade":
        return {"tipo": tipo, "valor": _inteiro(msg, "valor", QUALIDADE_MIN, QUALIDADE_MAX)}
    if tipo == "monitor":
        return {"tipo": tipo, "indice": _inteiro(msg, "indice", 1, 64)}
    if tipo == "frame_ok":
        return {"tipo": tipo}
    if tipo == "ping":
        t = msg.get("t", 0)
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t):
            raise ErroProtocolo("'t' inválido")
        return {"tipo": tipo, "t": t}
    raise ErroProtocolo(f"tipo de mensagem desconhecido: {tipo!r}")


def para_pixeis(x: float, y: float, monitor: dict[str, int]) -> tuple[int, int]:
    """Converte coordenadas relativas (0–1) em píxeis absolutos do monitor."""
    px = monitor["left"] + round(x * (monitor["width"] - 1))
    py = monitor["top"] + round(y * (monitor["height"] - 1))
    return px, py


def codificar(tipo: str, **campos: Any) -> str:
    return json.dumps({"tipo": tipo, **campos}, ensure_ascii=False)
