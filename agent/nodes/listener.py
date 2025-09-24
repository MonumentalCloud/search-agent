import logging
import re

from configs.load import setup_root_logger

_logger = setup_root_logger()


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def listen(query: str) -> str:
    _logger.debug("listener_start", extra={"trace_id": getattr(_logger, 'trace_id', 'n/a')})
    normalized = _normalize_spaces(query)
    _logger.debug("listener_normalized", extra={"trace_id": getattr(_logger, 'trace_id', 'n/a'), "normalized": normalized})
    return normalized

