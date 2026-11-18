import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("SARVAM_API_KEY=\nSARVAM_MODEL=sarvam-105b-conversations\n")
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "ENV_FILE", env_file)
    monkeypatch.setattr(main, "DATABASE_PATH", tmp_path / "test.db")
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    main.initialize_database()
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("language", "message", "intent"),
    [
        ("en-IN", "Why did my payment fail?", "payment_failed"),
        ("en-IN", "My money was debited but the merchant did not receive it.", "debited_not_received"),
        ("en-IN", "Where is my refund?", "refund_status"),
        ("en-IN", "How long will my refund take?", "refund_timeline"),
        ("en-IN", "I paid twice. What should I do?", "double_payment"),
        ("en-IN", "What does pending mean?", "pending_status"),
        ("en-IN", "Can you help me raise a complaint?", "complaint"),
        ("en-IN", "What should I do next?", "next_steps"),
        ("en-IN", "The payment failed and I was charged.", "payment_failed"),
        ("en-IN", "REFUND", "refund_status"),
        ("hi-IN", "मेरा रिफंड कहाँ है?", "refund_status"),
        ("ta-IN", "பணம் திரும்ப எப்போது வரும்?", "refund_timeline"),
        ("te-IN", "పేమెంట్ పెండింగ్ ఎందుకు?", "pending_status"),
    ],
)
def test_financial_intent_and_explicit_fallback(client, language, message, intent):
    response = client.post(
        "/api/assistant/chat",
        json={"message": message, "language": language},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["intent"] == intent
    assert result["language"] == language
    assert result["fallback"] is True
    assert "not an AI-generated answer or translation" in result["fallback_message"]


def test_short_ambiguous_message_asks_for_clarification(client):
    response = client.post(
        "/api/assistant/chat",
        json={"message": "?", "language": "en-IN"},
    )
    assert response.status_code == 200
    assert response.json()["needs_clarification"] is True
    assert "transaction reference" in response.json()["answer"]


def test_follow_up_keeps_intent_and_transaction_context(client):
    first = client.post(
        "/api/assistant/chat",
        json={
            "message": "Why did this payment fail? TXN-482801",
            "language": "en-IN",
        },
    ).json()
    second = client.post(
        "/api/assistant/chat",
        json={
            "message": "And then?",
            "language": "en-IN",
            "history": [
                {"role": "user", "content": "Why did this payment fail? TXN-482801"},
                {"role": "assistant", "content": first["answer"]},
            ],
        },
    )
    assert second.status_code == 200
    assert second.json()["intent"] == "payment_failed"
    assert second.json()["transaction"]["id"] == "TXN-482801"
    assert "refund" in second.json()["answer"].lower()


def test_refund_answer_only_uses_linked_refund_record(client):
    response = client.post(
        "/api/assistant/chat",
        json={
            "message": "Where is my refund for TXN-482801?",
            "language": "en-IN",
        },
    )
    answer = response.json()["answer"]
    assert response.json()["transaction"]["refund"]["status"] == "processing"
    assert "processing" in answer
    assert "not a bank-confirmed date or guarantee" in answer


def test_refund_reference_resolves_its_linked_transaction(client):
    response = client.post(
        "/api/assistant/chat",
        json={"message": "Where is refund RFD-482801?", "language": "en-IN"},
    )
    assert response.status_code == 200
    assert response.json()["transaction"]["id"] == "TXN-482801"
    assert "processing" in response.json()["answer"]


def test_sarvam_uses_selected_language_and_previous_messages(client, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    provider_answer = json.dumps({
        "intent": "refund_status",
        "answer": "यह डेमो रिफंड अभी प्रक्रिया में है।",
        "needs_clarification": False,
    })

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": provider_answer}}],
            }).encode()

    with patch.object(main.urllib.request, "urlopen", return_value=FakeResponse()) as urlopen:
        response = client.post(
            "/api/assistant/chat",
            json={
                "message": "और रिफंड कहाँ है?",
                "language": "hi-IN",
                "history": [{"role": "user", "content": "पैसा कट गया", "language": "hi-IN"}],
            },
        )
    assert response.status_code == 200
    assert response.json()["answer"] == "यह डेमो रिफंड अभी प्रक्रिया में है।"
    assert response.json()["fallback"] is False
    sent_body = json.loads(urlopen.call_args.args[0].data.decode())
    assert "Hindi" in sent_body["messages"][0]["content"]
    assert "[Original language: Hindi] पैसा कट गया" == sent_body["messages"][1]["content"]
    assert sent_body["model"] == "sarvam-105b-conversations"
    assert sent_body["response_format"] == {"type": "json_object"}
    assert urlopen.call_args.args[0].full_url == "https://api.sarvam.ai/v1/chat/completions"
    headers = {key.lower(): value for key, value in urlopen.call_args.args[0].header_items()}
    assert headers["api-subscription-key"] == "test-key"


def test_env_file_key_is_used_if_process_variable_is_empty(client, monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "")
    main.ENV_FILE.write_text(
        "SARVAM_API_KEY=test-key-from-env-file\nSARVAM_MODEL=sarvam-105b-conversations\n"
    )
    assert main.get_sarvam_api_key() == "test-key-from-env-file"


def test_sarvam_http_error_is_logged_without_key_and_explained(client, monkeypatch, caplog):
    import urllib.error

    monkeypatch.setenv("SARVAM_API_KEY", "do-not-log-this-key")
    error = urllib.error.HTTPError(
        "https://api.sarvam.ai/v1/chat/completions",
        400,
        "Bad Request",
        {},
        None,
    )
    with patch.object(main.urllib.request, "urlopen", side_effect=error):
        response = client.post(
            "/api/assistant/chat",
            json={"message": "Why did my payment fail?", "language": "en-IN"},
        )
    assert response.status_code == 200
    result = response.json()
    assert result["fallback"] is True
    assert "HTTP 400" in result["fallback_message"]
    assert "api_key_present=True" in caplog.text
    assert "do-not-log-this-key" not in caplog.text
    assert "SARVAM_API_KEY" not in caplog.text


def test_sarvam_failure_uses_explicit_demo_fallback(client, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    with patch.object(main.urllib.request, "urlopen", side_effect=OSError("offline")):
        response = client.post(
            "/api/assistant/chat",
            json={"message": "Where is my refund?", "language": "ta-IN"},
        )
    assert response.status_code == 200
    assert response.json()["fallback"] is True
    assert "not an AI-generated answer or translation" in response.json()["fallback_message"]


def test_demo_customer_profile_is_rukhiya(client):
    with main.database() as db:
        customer = db.execute(
            "SELECT display_name FROM customers WHERE id = 'demo-customer'"
        ).fetchone()
    assert customer["display_name"] == "Rukhiya"


def test_legacy_under_review_complaint_migrates_without_claiming_review(client):
    with main.database() as db:
        db.execute(
            """INSERT INTO complaints (id, transaction_id, category, description, status, created_at)
            VALUES ('CMP-LEGACY01', NULL, 'Payment issue', 'Legacy demo complaint record.', 'under_review', '2026-01-01T10:00:00+00:00')"""
        )
        db.execute(
            """INSERT INTO complaints (id, transaction_id, category, description, status, created_at)
            VALUES ('CMP-LEGACY02', NULL, 'Payment issue', 'Legacy migrated complaint record.', 'details_being_checked', '2026-01-02T10:00:00+00:00')"""
        )
        db.execute(
            """INSERT INTO complaint_status_history (complaint_id, status, explanation, created_at)
            VALUES ('CMP-LEGACY02', 'details_being_checked', 'Legacy demo status; no real support review is implied.', '2026-01-02T10:00:00+00:00')"""
        )
    main.initialize_database()
    for reference in ("CMP-LEGACY01", "CMP-LEGACY02"):
        migrated = client.get(f"/api/complaints/{reference}").json()
        assert migrated["status"] == "received"
        assert "no real support review is implied" in migrated["status_explanation"]
        assert migrated["timeline"][0]["status"] == "received"


def test_complaint_registration_and_each_lifecycle_status(client):
    created = client.post(
        "/api/complaints",
        json={
            "category": "Refund delayed",
            "transaction_id": "TXN-482801",
            "description": "Please help me understand the linked refund progress.",
        },
    )
    assert created.status_code == 201
    complaint = created.json()
    assert complaint["status"] == "received"
    assert complaint["status_label"] == "Complaint Received"
    assert complaint["is_demo"] is True
    assert len(complaint["timeline"]) == 5
    assert complaint["timeline"][0]["at"] is not None
    assert not complaint["timeline"][1]["complete"]

    transitions = [
        ("details_being_checked", "Details Being Checked"),
        ("action_required", "Action Required"),
        ("resolution_update", "Resolution Update"),
        ("resolved", "Resolved"),
    ]
    for next_status, label in transitions:
        response = client.patch(
            f"/api/complaints/{complaint['id']}/status",
            json={"status": next_status},
        )
        assert response.status_code == 200
        complaint = response.json()
        assert complaint["status"] == next_status
        assert complaint["status_label"] == label
        assert complaint["timeline"][[item["status"] for item in complaint["timeline"]].index(next_status)]["at"]

    assert [entry["status"] for entry in complaint["timeline"] if entry["at"]] == [
        "received",
        "details_being_checked",
        "action_required",
        "resolution_update",
        "resolved",
    ]
    assert all(entry["complete"] for entry in complaint["timeline"])
    tracked = client.get(f"/api/complaints/{complaint['id']}").json()
    assert tracked["status_explanation"].startswith("This demo complaint")


def test_complaint_transition_validation_and_saved_history(client):
    complaint = client.post(
        "/api/complaints",
        json={
            "category": "Other payment issue",
            "description": "I need an update about this payment issue.",
        },
    ).json()
    skipped = client.patch(
        f"/api/complaints/{complaint['id']}/status",
        json={"status": "resolved"},
    )
    assert skipped.status_code == 409
    assert client.get(f"/api/complaints/{complaint['id']}").json()["status"] == "received"

    update = client.patch(
        f"/api/complaints/{complaint['id']}/status",
        json={
            "status": "details_being_checked",
            "explanation": "The submitted payment reference was checked in demo records.",
        },
    ).json()
    event = next(item for item in update["timeline"] if item["status"] == "details_being_checked")
    assert event["explanation"] == "The submitted payment reference was checked in demo records."
    assert event["at"] is not None


def test_complaint_timeline_shows_optional_action_stage_as_unrecorded(client):
    complaint = client.post(
        "/api/complaints",
        json={
            "category": "Refund delayed",
            "description": "Please check whether a refund record is available.",
        },
    ).json()
    client.patch(
        f"/api/complaints/{complaint['id']}/status",
        json={"status": "details_being_checked"},
    )
    updated = client.patch(
        f"/api/complaints/{complaint['id']}/status",
        json={"status": "resolution_update"},
    ).json()
    action_stage = next(item for item in updated["timeline"] if item["status"] == "action_required")
    assert action_stage["at"] is None
    assert action_stage["skipped"] is True
    assert action_stage["status"] in {item["status"] for item in updated["timeline"]}


def test_complaint_history_preserves_repeated_status_updates(client):
    complaint = client.post(
        "/api/complaints",
        json={
            "category": "Payment not received",
            "description": "The payment needs another review after I add details.",
        },
    ).json()
    reference = complaint["id"]
    for status in ("details_being_checked", "action_required", "details_being_checked"):
        response = client.patch(
            f"/api/complaints/{reference}/status",
            json={"status": status},
        )
        assert response.status_code == 200
    result = client.get(f"/api/complaints/{reference}").json()
    checking_events = [
        item for item in result["timeline"] if item["status"] == "details_being_checked" and item["at"]
    ]
    assert len(checking_events) == 2
    assert checking_events[0]["at"] != checking_events[1]["at"]
    assert result["timeline"][3]["current"] is True
