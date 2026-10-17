
import psycopg

from google import genai
from google.genai import types
from pinecone import Pinecone

from src.config import Settings


def main():
    settings = Settings()

    question = (
        "Kalau sisa cuti tahunan saya tidak habis, "
        "apakah bisa digunakan tahun depan?"
    )

    gemini = genai.Client(api_key=settings.gemini_api_key)
    pinecone = Pinecone(api_key=settings.pinecone_api_key)

    # 1. Ubah pertanyaan menjadi embedding
    response = gemini.models.embed_content(
        model="gemini-embedding-001",
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=1536,
        ),
    )

    embedding = response.embeddings[0].values

    # 2. Cari 3 chunk paling relevan di Pinecone
    index = pinecone.Index(settings.pinecone_index_name)

    results = index.query(
        vector=embedding,
        top_k=3,
        namespace=settings.pinecone_namespace,
        include_metadata=True,
    )

    matches = results.matches or []

    print("PERTANYAAN:", question)
    print("JUMLAH HASIL:", len(matches))

    if not matches:
        print("Tidak ada hasil dari Pinecone.")
        return

    # 3. Ambil konten resmi berdasarkan chunk_id dari Neon
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            for rank, match in enumerate(matches, start=1):
                cur.execute(
                    """
                    SELECT document_id, title, section, content
                    FROM policy_chunks
                    WHERE chunk_id = %s
                    """,
                    (match.id,),
                )

                row = cur.fetchone()

                print(f"\nHASIL {rank}")
                print("Chunk ID:", match.id)
                print("Similarity score:", round(match.score, 4))

                if row:
                    document_id, title, section, content = row

                    print("Dokumen:", document_id)
                    print("Judul:", title)
                    print("Bagian:", section)
                    print("Isi:", content)
                else:
                    print("PERINGATAN: Chunk tidak ditemukan di Neon.")


if __name__ == "__main__":
    main()
