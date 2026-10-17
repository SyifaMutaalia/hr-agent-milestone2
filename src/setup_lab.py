from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def chunk_policy(path: Path) -> list[dict[str, str]]:
    from pathlib import Path
import hashlib
import re


def chunk_policy(path: Path) -> list[dict]:
    path = Path(path)
    raw_text = path.read_text(encoding="utf-8")

    # Pisahkan YAML front matter dari isi dokumen
    match = re.match(
        r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z",
        raw_text,
        flags=re.DOTALL,
    )

    if not match:
        raise ValueError(
            f"Dokumen {path.name} tidak memiliki YAML front matter"
        )

    metadata_text, body = match.groups()

    metadata = {}

    for line in metadata_text.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()

    required = (
        "document_id",
        "title",
        "version",
        "effective_date",
    )

    for field in required:
        if not metadata.get(field):
            raise ValueError(
                f"Metadata {field} tidak ditemukan"
            )

    # Pisahkan isi dokumen berdasarkan heading ##
    sections = re.split(
        r"(?m)^##\s+",
        body,
    )

    chunks = []

    for section in sections:
        section = section.strip()

        if not section:
            continue

        lines = section.splitlines()
        heading = lines[0].strip()
        content = "\n".join(lines[1:]).strip()

        if not content:
            continue

        # ID deterministik berdasarkan dokumen dan heading
        identifier = (
            f"{metadata['document_id']}|"
            f"{metadata['version']}|"
            f"{heading}"
        )

        suffix = hashlib.sha256(
            identifier.encode("utf-8")
        ).hexdigest()[:12]

        chunk = {
            "chunk_id": f"{metadata['document_id']}-{suffix}",
            "document_id": metadata["document_id"],
            "title": metadata["title"],
            "version": metadata["version"],
            "effective_date": metadata["effective_date"],
            "section": heading,
            "content": content,
        }

        chunks.append(chunk)

    return chunks


def reset_and_seed() -> None:
    # TODO(M2): Create pgvector schema, seed synthetic identities/balances, batch embed, and upsert chunks.
    raise NotImplementedError


if __name__ == "__main__":
    reset_and_seed()

