"""
Utilidades mínimas para trabajar con mensajes FIX de manera opcional.

No dependemos de tipos específicos como simplefix.Message (que no existe en
algunas versiones). En su lugar, probamos importar simplefix en runtime y
proveemos helpers que funcionen aún si la librería no está disponible.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List, Tuple

try:
	import simplefix  # type: ignore
except Exception:  # librería no instalada o API distinta
	simplefix = None  # type: ignore


SOH = "\x01"


def build_fix_message(fields: List[Tuple[str, str]]) -> bytes:
	"""Construye un mensaje FIX (8=... 9=... ... 10=checksum) en bytes.

	- fields: lista de (tag, valor), e.g. [("35", "A"), ("49", "SND"), ...]
	Si está simplefix, usamos su builder; si no, lo construimos manualmente.
	"""
	if simplefix is not None:
		builder = simplefix.FixMessage()  # type: ignore[attr-defined]
		for tag, value in fields:
			builder.append_pair(int(tag), value)
		return builder.encode()

	# Construcción manual: agregamos header si no viene incluido
	tags = dict(fields)
	begin_string = tags.get("8", "FIX.4.4")

	# Ensamblar cuerpo sin BodyLength (9) ni checksum (10)
	body_pairs = [(k, v) for k, v in fields if k not in ("8", "9", "10")]
	body = SOH.join(f"{k}={v}" for k, v in body_pairs) + SOH

	# Calcular BodyLength (bytes del body + del begin string y el tag 8 y SOH?)
	# En FIX, BodyLength es la longitud desde tag 35 hasta antes de 10.
	# Para mantenerlo simple y robusto, calculamos sobre body únicamente si el tag 8 se enviará aparte.
	body_length = len(body.encode("ascii"))

	head = f"8={begin_string}{SOH}9={body_length}{SOH}"
	message_wo_checksum = (head + body).encode("ascii")

	chksum = sum(message_wo_checksum) % 256
	trailer = f"10={chksum:03d}{SOH}".encode("ascii")
	return message_wo_checksum + trailer


def parse_fix_message(raw: bytes) -> Dict[str, str]:
	"""Parsea un mensaje FIX en un dict simple tag->valor.
	Intenta usar simplefix si existe, si no, parse manual por SOH.
	"""
	if simplefix is not None and hasattr(simplefix, "SimpleFix"):
		# Algunas versiones exponen SimpleFix parser
		parser = simplefix.SimpleFix()  # type: ignore[attr-defined]
		parser.append(raw)
		msg = parser.get_message()
		result: Dict[str, str] = {}
		if msg is not None:
			for tag, val in msg.pairs():  # type: ignore[attr-defined]
				result[str(tag)] = val.decode("ascii") if isinstance(val, (bytes, bytearray)) else str(val)
		return result

	# Fallback manual
	text = raw.decode("ascii", errors="ignore")
	parts = text.split(SOH)
	out: Dict[str, str] = {}
	for p in parts:
		if not p:
			continue
		if "=" not in p:
			continue
		k, v = p.split("=", 1)
		out[k] = v
	return out


def is_simplefix_available() -> bool:
	return simplefix is not None

