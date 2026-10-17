
from google import genai
from google.genai import types

from src.config import Settings
from src.repository import PostgresRepository
from src.retrieval import RetrievalService
from src.tools import ToolExecutor

class GeminiEmbeddingProvider:
    def __init__(self, api_key: str, dimensions: int):
        self.client = genai.Client(api_key=api_key)
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []

        for text in texts:
            response = self.client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",
                    output_dimensionality=self.dimensions,
                ),
            )

            vectors.append(response.embeddings[0].values)

        return vectors


class MemoryCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


def main():
    settings = Settings()

    repository = PostgresRepository(
        database_url=settings.database_url,
        embedding_dimensions=settings.embedding_dimensions,
    )

    provider = GeminiEmbeddingProvider(
        api_key=settings.gemini_api_key,
        dimensions=settings.embedding_dimensions,
    )

    cache = MemoryCache()

    retrieval = RetrievalService(
        repository=repository,
        provider=provider,
        cache=cache,
        index_version=settings.policy_index_version,
    )

    question = (
        "Apakah sisa cuti tahunan saya "
        "bisa digunakan tahun depan?"
    )

    try:
        results = retrieval.search(
            query=question,
            top_k=3,
        )

        print("PERTANYAAN:", question)
        print("JUMLAH HASIL:", len(results))

        for rank, chunk in enumerate(results, start=1):
            print(f"\nHASIL {rank}")
            print("Dokumen:", chunk.document_id)
            print("Bagian:", chunk.section)
            print("Fusion score:", round(chunk.score, 4))
            print("Isi:", chunk.content)

        print("\n=== UJI CACHE ===")

        cached_results = retrieval.search(
            query=question,
            top_k=3,
        )

        print("Jumlah hasil cache:", len(cached_results))

        
        print("\n=== TOOL SEARCH HR POLICY ===")

        auth = repository.authenticate("token-alya")
        assert auth is not None, "Autentikasi gagal"

        executor = ToolExecutor(repository=repository,retrieval=retrieval,settings=settings)       
        result = executor.execute(
            tool_name="search_hr_policy",
            arguments={
                "query": (
                    "Apakah sisa cuti tahunan bisa "
                    "digunakan tahun depan?"
                ),
                "top_k": 3,
            },
            auth=auth,
        )

        documents = result["documents"]

        print("Jumlah dokumen:", len(documents))

        for i, document in enumerate(documents, 1):
            print(f"\nDOKUMEN {i}")
            print("ID:", document["document_id"])
            print("Judul:", document["title"])
            print("Bagian:", document["section"])
            print("Versi:", document["version"])
            print("Isi:", document["content"])


    finally:
        repository.close()


if __name__ == "__main__":
    main()
