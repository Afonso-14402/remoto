"""Tradução dos nomes de tecla do browser (``KeyboardEvent.key``) para o pynput.

Fica separado de ``input_control`` para poder ser testado sem ecrã:
devolve só o *nome* do atributo de ``pynput.keyboard.Key``.
"""

from __future__ import annotations

TECLAS_ESPECIAIS: dict[str, str] = {
    "Enter": "enter",
    "Backspace": "backspace",
    "Tab": "tab",
    "Escape": "esc",
    "Esc": "esc",
    " ": "space",
    "Shift": "shift",
    "Control": "ctrl",
    "Alt": "alt",
    "AltGraph": "alt_gr",
    "Meta": "cmd",
    "OS": "cmd",
    "CapsLock": "caps_lock",
    "ArrowUp": "up",
    "ArrowDown": "down",
    "ArrowLeft": "left",
    "ArrowRight": "right",
    "Delete": "delete",
    "Insert": "insert",
    "Home": "home",
    "End": "end",
    "PageUp": "page_up",
    "PageDown": "page_down",
    "ContextMenu": "menu",
    "PrintScreen": "print_screen",
    "ScrollLock": "scroll_lock",
    "Pause": "pause",
    "NumLock": "num_lock",
    "AudioVolumeMute": "media_volume_mute",
    "AudioVolumeDown": "media_volume_down",
    "AudioVolumeUp": "media_volume_up",
    "MediaPlayPause": "media_play_pause",
    "MediaTrackNext": "media_next",
    "MediaTrackPrevious": "media_previous",
}
TECLAS_ESPECIAIS.update({f"F{i}": f"f{i}" for i in range(1, 21)})

# Teclas que o browser envia mas que não correspondem a nada injetável.
IGNORADAS = frozenset({"Unidentified", "Dead", "Process", "Compose", "Fn", "FnLock"})


def traduzir(valor: str) -> tuple[str, str] | None:
    """Devolve ``("especial", nome_pynput)``, ``("caracter", c)`` ou ``None`` se for para ignorar."""
    if valor in IGNORADAS:
        return None
    if valor in TECLAS_ESPECIAIS:
        return ("especial", TECLAS_ESPECIAIS[valor])
    if len(valor) == 1:
        return ("caracter", valor)
    return None
