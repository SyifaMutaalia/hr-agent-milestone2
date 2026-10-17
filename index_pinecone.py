import psycopg
from openai import OpenAI
from pinecone import Pinecone
from src.config import Settings


def main():
    settings = Settings()

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY belum dikonfigurasi")

    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY belum dikonfigurasi")

    if settings.embedding_model != "text-embedding-3-small":
        raise RuntimeError("Model embedding harus text-embedding-3-small")

    if settings.embedding_dimensions != 1536:
        raise RuntimeError("Dimensi embedding harus 1536")

    if settings.pinecone_namespace != "hr-policies-openai":
        raise RuntimeError("Namespace harus hr-policies-openai")

    openai_client = OpenAI(api_key=settings.openai_api_key)
    pinecone = Pinecone(api_key=settings.pinecone_api_key)
    index = pinecone.Index(settings.pinecone_index_name)

    # Ambil dokumen HR dari Neon PostgreSQL
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    chunk_id,
                    document_id,
                    title,
                    section,
                    content
                FROM policy_chunks
                ORDER BY chunk_id
            """)
            chunks = cur.fetchall()

    print(f"Jumlah chunks dari Neon: {len(chunks)}")

    if not chunks:
        raise RuntimeError("Tidak ada policy chunks di Neon")

    vectors = []

    for i, chunk in enumerate(chunks, start=1):
        chunk_id, document_id, title, section, content = chunk

        document_text = (
            f"Judul: {title}\n"
            f"Bagian: {section}\n"
            f"Isi: {content}"
        )

        response = openai_client.embeddings.create(
            model=settings.embedding_model,
            input=document_text,
            dimensions=settings.embedding_dimensions,
        )

        embedding = response.data[0].embedding

        if len(embedding) != settings.embedding_dimensions:
            raise ValueError(
                f"Dimensi embedding tidak sesuai: {chunk_id}"
            )

        vectors.append({
            "id": str(chunk_id),
            "values": embedding,
            "metadata": {
                "document_id": str(document_id),
                "title": str(title),
                "section": str(section),
            },
        })

        print(f"[{i}/{len(chunks)}] OpenAI embedding berhasil")

    # Upload ke namespace OpenAI, tanpa menghapus namespace Gemini
    index.upsert(
        vectors=vectors,
        namespace=settings.pinecone_namespace,
    )

    print("Upload OpenAI embedding ke Pinecone berhasil.")
    print(f"Total vectors dikirim: {len(vectors)}")


if __name__ == "__main__":
    main()
