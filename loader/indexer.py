"""Батчевая индексация метаданных 1С в Qdrant."""

import uuid
from dataclasses import dataclass

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    NamedSparseVector,
    NamedVector,
    PointStruct,
    SparseVector,
    VectorParams,
    SparseVectorParams,
)

from config import (
    QDRANT_HOST,
    QDRANT_PORT,
    EMBEDDING_SERVICE_URL,
    EMBEDDING_BATCH_SIZE,
    VECTOR_DIMENSIONS,
)


@dataclass
class IndexStats:
    total_objects: int = 0
    indexed: int = 0
    errors: int = 0


class QdrantIndexer:
    def __init__(self, qdrant_host: str = QDRANT_HOST, qdrant_port: int = QDRANT_PORT):
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.http = httpx.Client(base_url=EMBEDDING_SERVICE_URL, timeout=60.0)

    def create_collection(self, collection_name: str) -> None:
        """Создаёт коллекцию с named vectors + sparse."""
        collections = [c.name for c in self.client.get_collections().collections]
        if collection_name in collections:
            self.client.delete_collection(collection_name)

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "object_name": VectorParams(
                    size=VECTOR_DIMENSIONS, distance=Distance.COSINE, on_disk=True,
                    hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
                ),
                "friendly_name": VectorParams(
                    size=VECTOR_DIMENSIONS, distance=Distance.COSINE, on_disk=True,
                    hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
                ),
            },
            sparse_vectors_config={
                "bm25": SparseVectorParams(),
            },
        )

    def _embed_dense(self, texts: list[str], prefix: str = "search_document") -> list[list[float]]:
        """Получает dense embeddings от embedding service."""
        resp = self.http.post("/embed", json={"texts": texts, "prefix": prefix})
        resp.raise_for_status()
        return resp.json()["embeddings"]

    def _embed_sparse(self, texts: list[str]) -> list[dict]:
        """Получает sparse BM25 embeddings."""
        resp = self.http.post("/embed-sparse", json={"texts": texts})
        resp.raise_for_status()
        return resp.json()["embeddings"]

    def _build_description(self, obj: dict) -> str:
        """Формирует текстовое описание объекта для payload."""
        parts = [
            f"{obj.get('object_type_ru', '')} {obj['name']} ({obj.get('synonym', '')})"
        ]

        attrs = obj.get("attributes", [])
        if attrs:
            attr_lines = []
            for a in attrs:
                if isinstance(a, dict):
                    types = ", ".join(a.get("type_info", []))
                    attr_lines.append(f"- {a['name']} ({types})" if types else f"- {a['name']}")
                else:
                    attr_lines.append(f"- {a}")
            parts.append("\nРеквизиты:\n" + "\n".join(attr_lines))

        dims = obj.get("dimensions", [])
        if dims:
            dim_lines = []
            for d in dims:
                if isinstance(d, dict):
                    types = ", ".join(d.get("type_info", []))
                    dim_lines.append(f"- {d['name']} ({types})" if types else f"- {d['name']}")
                else:
                    dim_lines.append(f"- {d}")
            parts.append("\nИзмерения:\n" + "\n".join(dim_lines))

        resources = obj.get("resources", [])
        if resources:
            res_lines = []
            for r in resources:
                if isinstance(r, dict):
                    types = ", ".join(r.get("type_info", []))
                    res_lines.append(f"- {r['name']} ({types})" if types else f"- {r['name']}")
                else:
                    res_lines.append(f"- {r}")
            parts.append("\nРесурсы:\n" + "\n".join(res_lines))

        ts = obj.get("tabular_sections", [])
        if ts:
            ts_lines = []
            for t in ts:
                if isinstance(t, dict):
                    t_attrs = [a["name"] if isinstance(a, dict) else a for a in t.get("attributes", [])]
                    ts_lines.append(f"- {t['name']} ({', '.join(t_attrs)})" if t_attrs else f"- {t['name']}")
                else:
                    ts_lines.append(f"- {t}")
            parts.append("\nТабличные части:\n" + "\n".join(ts_lines))

        regs = obj.get("register_records", [])
        if regs:
            parts.append("\nДвижения регистров:\n" + "\n".join(f"- {r}" for r in regs))

        enums = obj.get("enum_values", [])
        if enums:
            ev_names = [e["name"] if isinstance(e, dict) else e for e in enums[:20]]
            parts.append("\nЗначения перечисления:\n" + "\n".join(f"- {n}" for n in ev_names))
            if len(enums) > 20:
                parts.append(f"  ... и ещё {len(enums) - 20}")

        return "\n".join(parts)

    def _build_friendly_name(self, obj: dict) -> str:
        """Формирует friendly_name: 'ТипРу: Синоним'."""
        type_ru = obj.get("object_type_ru", "")
        synonym = obj.get("synonym", obj["name"])
        return f"{type_ru}: {synonym}" if type_ru else synonym

    def _build_payload(self, obj: dict) -> dict:
        """Формирует payload для Qdrant point."""
        # Для attributes/tabular_sections в payload храним только имена (строки)
        attrs = obj.get("attributes", [])
        attr_names = [a["name"] if isinstance(a, dict) else a for a in attrs]

        ts = obj.get("tabular_sections", [])
        ts_names = [t["name"] if isinstance(t, dict) else t for t in ts]

        return {
            "object_name": obj["name"],
            "object_type": obj.get("object_type", ""),
            "object_type_ru": obj.get("object_type_ru", ""),
            "synonym": obj.get("synonym", ""),
            "friendly_name": self._build_friendly_name(obj),
            "description": self._build_description(obj),
            "attributes": attr_names,
            "tabular_sections": ts_names,
            "register_records": obj.get("register_records", []),
            "hierarchical": obj.get("hierarchical", False),
            "config_name": "",  # будет заполнено при индексации
        }

    def index_objects(
        self,
        objects: list[dict],
        collection_name: str,
        config_name: str = "MY_CONFIG",
        progress_callback=None,
    ) -> IndexStats:
        """Индексирует список объектов метаданных в Qdrant.

        Args:
            objects: список объектов от parser API (dict из JSON).
            collection_name: имя коллекции Qdrant.
            config_name: имя конфигурации для payload.
            progress_callback: callable(indexed, total) для обновления прогресса.
        """
        stats = IndexStats(total_objects=len(objects))

        for batch_start in range(0, len(objects), EMBEDDING_BATCH_SIZE):
            batch = objects[batch_start : batch_start + EMBEDDING_BATCH_SIZE]

            # Тексты для эмбеддингов
            object_names = [obj["name"] for obj in batch]
            friendly_names = [self._build_friendly_name(obj) for obj in batch]
            # Для BM25 — конкатенация имени, синонима и описания
            bm25_texts = [
                f"{obj['name']} {obj.get('synonym', '')} {self._build_description(obj)}"
                for obj in batch
            ]

            try:
                # Получаем эмбеддинги
                name_vectors = self._embed_dense(object_names)
                friendly_vectors = self._embed_dense(friendly_names)
                sparse_vectors = self._embed_sparse(bm25_texts)

                # Формируем points
                points = []
                for i, obj in enumerate(batch):
                    payload = self._build_payload(obj)
                    payload["config_name"] = config_name

                    point = PointStruct(
                        id=str(uuid.uuid4()),
                        vector={
                            "object_name": name_vectors[i],
                            "friendly_name": friendly_vectors[i],
                        },
                        payload=payload,
                    )
                    # Добавляем sparse vector
                    point.vector["bm25"] = SparseVector(
                        indices=sparse_vectors[i]["indices"],
                        values=sparse_vectors[i]["values"],
                    )
                    points.append(point)

                self.client.upsert(collection_name=collection_name, points=points)
                stats.indexed += len(batch)

            except Exception as e:
                print(f"Error indexing batch at {batch_start}: {e}")
                stats.errors += len(batch)

            if progress_callback:
                progress_callback(stats.indexed, stats.total_objects)

        return stats

    def close(self):
        self.http.close()
        self.client.close()
