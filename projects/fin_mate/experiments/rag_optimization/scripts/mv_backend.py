"""D7 corpus-shaping backends.

Components:
- StEmbedding — local sentence-transformers embedding (BAAI/bge-small-en-v1.5 by
  default; pass model_name="sentence-transformers/clip-ViT-B-32" for the CLIP
  vision-capable text/image encoder). $0, no Ark embedding key needed.
- D7Backend — in-memory llama-index backend with configurable chunk_size/overlap
  and document-level retrieval. Drives the same VanillaIndex as VeADK's
  InMemoryKnowledgeBackend but returns NodeWithScore (keeps file_path for eval).

CLIP note: run_d7 uses bge-small-en for retrieval quality on text corpora. CLIP is
implemented here (image-capable) but its image channel can't feed a text-only
generation model, so it is not used in the D7 matrix.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import PrivateAttr

try:
    from llama_index.core.base.embeddings.base import BaseEmbedding as _BaseEmbedding
except ImportError:
    _BaseEmbedding = None

try:
    from veadk.knowledgebase.backends.in_memory_backend import InMemoryKnowledgeBackend
except ImportError:
    InMemoryKnowledgeBackend = None


class StEmbedding(_BaseEmbedding):
    """Local sentence-transformers embedding (text, optionally image-capable CLIP)."""

    model_name: str = "BAAI/bge-small-en-v1.5"
    _model: Any = PrivateAttr(default=None)

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)

    def _get_text_embedding(self, text: str) -> list[float]:
        self._load()
        return self._model.encode(text).tolist()

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._get_text_embedding(query)

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        self._load()
        return [v.tolist() for v in self._model.encode(texts)]

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)

    async def _aget_text_embedding(self, text: str) -> list[float]:
        return self._get_text_embedding(text)

    def class_name(self) -> str:
        return "StEmbedding"


class LocalVisionEmbedding(StEmbedding):
    """CLIP image-capable embedding (text encoder used for queries/docs)."""

    model_name: str = "sentence-transformers/clip-ViT-B-32"


def get_splitter(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50):
    """llama-index sentence splitter (mirrors veadk get_llama_index_splitter)."""
    from llama_index.core.node_parser import SentenceSplitter

    # veadk routes .py/.md/html to dedicated parsers; for the D7 corpus (txt/md/
    # csv/html/pdf) sentence splitting is the right uniform choice for comparability.
    return SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


if InMemoryKnowledgeBackend is not None:

    class D7Backend(InMemoryKnowledgeBackend):
        """Local in-memory backend: configurable chunk params + local embeddings.

        Attributes:
            chunk_size: SentenceSplitter chunk_size (default 512 = veadk default)
            chunk_overlap: SentenceSplitter chunk_overlap (default 50)
            embed_model_name: sentence-transformers model for embeddings
        """

        chunk_size: int = 512
        chunk_overlap: int = 50
        embed_model_name: str = "BAAI/bge-small-en-v1.5"
        index: str = "d7"

        def model_post_init(self, __context: Any) -> None:
            from llama_index.core import VectorStoreIndex

            self._embed_model = StEmbedding(model_name=self.embed_model_name)
            self._vector_index = VectorStoreIndex([], embed_model=self._embed_model)

        def add_from_files(self, files: list[str], file_extractor: dict | None = None) -> bool:
            from llama_index.core import SimpleDirectoryReader

            documents = SimpleDirectoryReader(
                input_files=files,
                file_extractor=file_extractor if file_extractor is not None else {},
            ).load_data()
            nodes = self._split_documents(documents)
            self._vector_index.insert_nodes(nodes)
            return True

        def _split_documents(self, documents):
            from llama_index.core.schema import BaseNode

            splitter = get_splitter("", self.chunk_size, self.chunk_overlap)
            nodes: list[BaseNode] = []
            for document in documents:
                nodes.extend(splitter.get_nodes_from_documents([document]))
            return nodes

        def retrieve(self, query: str, top_k: int = 5) -> list[Any]:
            """Return NodeWithScore list with node.metadata['file_path'] + .text."""
            _retriever = self._vector_index.as_retriever(similarity_top_k=top_k)
            return _retriever.retrieve(query)

        def corpus_ids(self) -> list[str]:
            """All document file identifiers in the index (for sparse grep channel)."""
            return sorted({node.metadata.get("file_path", "") for node in self._vector_index.docstore.docs.values()})

else:
    D7Backend = None  # type: ignore[misc]


def build_d7_kb(
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    embed_model_name: str = "BAAI/bge-small-en-v1.5",
) -> "KnowledgeBase":
    """Build a VeADK KnowledgeBase backed by D7Backend (local in-memory)."""
    from veadk.knowledgebase import KnowledgeBase

    if D7Backend is None:
        raise ImportError("veadk-python required")
    return KnowledgeBase(
        backend=D7Backend(
            index="d7", chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            embed_model_name=embed_model_name,
        )
    )