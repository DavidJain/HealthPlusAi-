"""Admin document operations on a throwaway vector store."""

from __future__ import annotations

from healthplus.knowledge_base.models import Chunk
from healthplus.vector_database.vector_store import VectorStore


def _chunk(i: int, source: str, category: str) -> Chunk:
    return Chunk(
        chunk_id=f"{source}-{i}",
        doc_id=source,
        text=f"text {i}",
        source=source,
        category=category,
        page_number=1,
        chunk_index=i,
    )


def test_list_and_delete_documents(tmp_path):
    store = VectorStore(persist_dir=tmp_path, collection_name="test_docs")
    chunks = [_chunk(0, "Doctors.pdf", "doctors"), _chunk(1, "Doctors.pdf", "doctors"), _chunk(0, "Pricing.pdf", "pricing")]
    store.upsert(chunks, [[float(i), 1.0, 0.5] for i in range(3)])

    assert store.documents() == [
        {"source": "Doctors.pdf", "category": "doctors", "chunks": 2},
        {"source": "Pricing.pdf", "category": "pricing", "chunks": 1},
    ]
    assert store.delete_source("Doctors.pdf") == 2
    assert store.documents() == [{"source": "Pricing.pdf", "category": "pricing", "chunks": 1}]
    assert store.delete_source("missing.pdf") == 0
