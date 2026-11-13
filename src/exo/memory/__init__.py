"""Memoria persistente por usuario (F3, ADR-0009).

SQLite es la fuente de verdad (`store.py`); los índices de búsqueda son
derivados y se pueden reconstruir. Solo `backends/` y `embeddings/` importan
dependencias opcionales, siempre de forma diferida.
"""
