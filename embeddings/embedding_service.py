from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from config import MODEL_NAME, MODEL_DIMENSIONS, MAX_BATCH_SIZE, SPARSE_MODEL_NAME


# --- Models ---

class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE)
    prefix: str = Field(..., pattern=r"^(search_document|search_query)$")


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dimensions: int
    model: str
    count: int


class SparseVector(BaseModel):
    indices: list[int]
    values: list[float]


class SparseEmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE)


class SparseEmbedResponse(BaseModel):
    embeddings: list[SparseVector]
    model: str
    count: int


# --- App state ---

dense_model: Optional[SentenceTransformer] = None
sparse_model = None
sparse_model_name: str = SPARSE_MODEL_NAME


@asynccontextmanager
async def lifespan(app: FastAPI):
    global dense_model, sparse_model, sparse_model_name

    # Load dense model
    print(f"Loading dense model: {MODEL_NAME}")
    dense_model = SentenceTransformer(MODEL_NAME)
    print(f"Dense model loaded. Dimensions: {dense_model.get_sentence_embedding_dimension()}")

    # Load sparse model
    try:
        from fastembed import SparseTextEmbedding
        sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
        sparse_model_name = SPARSE_MODEL_NAME
        print(f"Sparse model loaded: {SPARSE_MODEL_NAME}")
    except Exception as e:
        print(f"FATAL: Failed to load fastembed BM25: {e}")
        print("Sparse embeddings will be unavailable.")
        sparse_model = None
        sparse_model_name = ""

    yield

    dense_model = None
    sparse_model = None


app = FastAPI(title="Embedding Service", lifespan=lifespan)


# --- Endpoints ---

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": dense_model is not None,
        "sparse_model_loaded": sparse_model is not None,
    }


@app.get("/model-info")
def model_info():
    if dense_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {
        "model": MODEL_NAME,
        "dimensions": dense_model.get_sentence_embedding_dimension(),
        "max_seq_length": dense_model.max_seq_length,
    }


@app.post("/embed", response_model=EmbedResponse)
def embed(request: EmbedRequest):
    if dense_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    prefixed = [f"{request.prefix}: {t}" for t in request.texts]
    vectors = dense_model.encode(prefixed, normalize_embeddings=True)

    return EmbedResponse(
        embeddings=[v.tolist() for v in vectors],
        dimensions=vectors.shape[1],
        model=MODEL_NAME,
        count=len(vectors),
    )


@app.post("/embed-sparse", response_model=SparseEmbedResponse)
def embed_sparse(request: SparseEmbedRequest):
    if sparse_model is None:
        raise HTTPException(status_code=503, detail="Sparse model not loaded")

    results = _compute_sparse(request.texts)

    return SparseEmbedResponse(
        embeddings=results,
        model=sparse_model_name,
        count=len(results),
    )


def _compute_sparse(texts: list[str]) -> list[SparseVector]:
    results = []
    for embedding in sparse_model.embed(texts):
        results.append(SparseVector(
            indices=embedding.indices.tolist(),
            values=embedding.values.tolist(),
        ))
    return results


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT
    uvicorn.run("embedding_service:app", host=HOST, port=PORT)
