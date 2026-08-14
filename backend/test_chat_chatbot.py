import os
import json
import pytest
import tempfile
from fastapi.testclient import TestClient

from app.main import app
from app.services.extractor import extract_zip_file, get_project_directory
from app.services.chat_service import retrieve_project_context

client = TestClient(app)

@pytest.fixture
def sample_project():
    """Project with auth.py and utils.py for chat retrieval tests."""
    with tempfile.TemporaryDirectory() as td:
        src_dir = os.path.join(td, "src")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "auth.py"), "w", encoding="utf-8") as f:
            f.write(
                "import hashlib\nfrom utils import hash_token\n\n"
                "def authenticate_user(username: str, token: str) -> bool:\n"
                "    \"\"\"Validates user token credentials.\"\"\"\n"
                "    return hash_token(username) == token\n"
            )
        with open(os.path.join(src_dir, "utils.py"), "w", encoding="utf-8") as f:
            f.write(
                "import hashlib\n\n"
                "def hash_token(data: str) -> str:\n"
                "    return hashlib.sha256(data.encode()).hexdigest()\n"
            )

        import zipfile
        zip_path = os.path.join(td, "chat_sample.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for fname in os.listdir(src_dir):
                zf.write(os.path.join(src_dir, fname), fname)
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        meta = extract_zip_file(zip_bytes, "chat_sample.zip")
        pdir = get_project_directory(meta.project_id)
        yield meta.project_id, pdir


def test_chat_empty_message_error():
    """Test 1: Empty message returns 400 Bad Request."""
    res = client.post("/api/chat", json={"message": "   "})
    assert res.status_code == 400


def test_chat_context_retrieval_specific_file(sample_project):
    """Test 2: Context retrieval specifically targets mentioned file."""
    pid, _ = sample_project
    context, sources, facts = retrieve_project_context(pid, "What functions are in auth.py?")
    assert "auth.py" in context
    assert "authenticate_user" in context
    assert any("auth.py" in s.file for s in sources)
    assert len(facts) > 0


def test_chat_dependency_retrieval(sample_project):
    """Test 3: Asking about dependencies retrieves architecture context."""
    pid, _ = sample_project
    context, sources, facts = retrieve_project_context(pid, "Explain the dependency graph and imports")
    assert "DEPENDENCY" in context or "Files" in context


def test_chat_endpoint_valid_request(sample_project):
    """Test 4: POST /api/chat returns 200 with structured ChatResponse."""
    pid, _ = sample_project
    res = client.post("/api/chat", json={
        "project_id": pid,
        "message": "What does auth.py do?"
    })
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "conversation_id" in data
    assert data["conversation_id"] is not None
    assert isinstance(data["sources"], list)
    assert isinstance(data["verified_facts"], list)


def test_chat_conversation_continuation(sample_project):
    """Test 5: Providing conversation_id preserves session continuity."""
    pid, _ = sample_project
    conv_id = "test-session-1234"
    res1 = client.post("/api/chat", json={
        "project_id": pid,
        "message": "Explain auth.py",
        "conversation_id": conv_id
    })
    assert res1.status_code == 200
    assert res1.json()["conversation_id"] == conv_id

    res2 = client.post("/api/chat", json={
        "project_id": pid,
        "message": "What imports does it use?",
        "conversation_id": conv_id
    })
    assert res2.status_code == 200
    assert res2.json()["conversation_id"] == conv_id


def test_chat_no_project_graceful_handling():
    """Test 6: Request without project_id returns guidance rather than crashing."""
    res = client.post("/api/chat", json={
        "message": "Hello, how do I analyze my code?"
    })
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
