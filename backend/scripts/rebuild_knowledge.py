from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from knowledge_base.service import knowledge_base


def main() -> None:
    status = knowledge_base.sync(force=True)
    print(
        "Knowledge base rebuilt: "
        f"{status['documents']} documents, {status['chunks']} chunks, "
        f"indexed_at={status['indexed_at']}"
    )


if __name__ == "__main__":
    main()
