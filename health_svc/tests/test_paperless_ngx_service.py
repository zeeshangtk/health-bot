"""
Unit tests for PaperlessNgxService, focused on patient-name tag resolution.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import httpx
import pytest

from services.paperless_ngx_service import PaperlessNgxService


@pytest.fixture
def temp_file():
    """Create a temporary file for upload tests."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"fake-image-bytes")
        path = tmp.name
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def service():
    return PaperlessNgxService(
        base_url="http://paperless.test",
        api_token="test-token",
        timeout=5,
        verify_ssl=False,
    )


def _mock_client(mock_client_cls, *, get_side_effect=None, post_side_effect=None):
    """Wire up httpx.Client(...) as a context manager whose get/post are mocked."""
    client_instance = MagicMock()
    if get_side_effect is not None:
        client_instance.get.side_effect = get_side_effect
    if post_side_effect is not None:
        client_instance.post.side_effect = post_side_effect
    mock_client_cls.return_value.__enter__.return_value = client_instance
    return client_instance


def _response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestGetOrCreateTagId:
    def test_reuses_existing_tag(self, service):
        with patch("services.paperless_ngx_service.httpx.Client") as mock_client_cls:
            client_instance = _mock_client(
                mock_client_cls,
                get_side_effect=[_response({"results": [{"id": 7, "name": "Asgar"}]})],
            )

            tag_id = service._get_or_create_tag_id("Asgar")

        assert tag_id == 7
        client_instance.post.assert_not_called()
        client_instance.get.assert_called_once_with(
            "http://paperless.test/api/tags/",
            headers=service.headers,
            params={"name__iexact": "Asgar"},
        )

    def test_creates_tag_when_missing(self, service):
        with patch("services.paperless_ngx_service.httpx.Client") as mock_client_cls:
            client_instance = _mock_client(
                mock_client_cls,
                get_side_effect=[_response({"results": []})],
                post_side_effect=[_response({"id": 99, "name": "New Patient"})],
            )

            tag_id = service._get_or_create_tag_id("New Patient")

        assert tag_id == 99
        client_instance.post.assert_called_once_with(
            "http://paperless.test/api/tags/",
            headers=service.headers,
            json={"name": "New Patient"},
        )

    def test_falls_back_to_lookup_on_create_conflict(self, service):
        with patch("services.paperless_ngx_service.httpx.Client") as mock_client_cls:
            client_instance = _mock_client(
                mock_client_cls,
                get_side_effect=[
                    _response({"results": []}),
                    _response({"results": [{"id": 11, "name": "Racy Patient"}]}),
                ],
                post_side_effect=[_response({}, status_code=400)],
            )

            tag_id = service._get_or_create_tag_id("Racy Patient")

        assert tag_id == 11
        assert client_instance.get.call_count == 2

    def test_raises_on_other_create_errors(self, service):
        with patch("services.paperless_ngx_service.httpx.Client") as mock_client_cls:
            _mock_client(
                mock_client_cls,
                get_side_effect=[_response({"results": []})],
                post_side_effect=[_response({}, status_code=500)],
            )

            with pytest.raises(httpx.HTTPStatusError):
                service._get_or_create_tag_id("Broken Patient")


class TestUploadMedicalDocumentTagging:
    def test_patient_tag_merged_with_provided_tag_ids(self, service, temp_file):
        with patch.object(service, "_get_or_create_tag_id", return_value=42):
            with patch("services.paperless_ngx_service.httpx.Client") as mock_client_cls:
                client_instance = MagicMock()
                client_instance.post.return_value = _response({"status": "success"})
                mock_client_cls.return_value.__enter__.return_value = client_instance

                service.upload_medical_document(
                    document_path=temp_file,
                    patient_name="Nazra",
                    date="2026-08-31",
                    hospital_name="Test Hospital",
                    json_extraction={},
                    tag_ids=[5],
                )

        _, kwargs = client_instance.post.call_args
        assert sorted(kwargs["data"]["tags"]) == ["42", "5"]

    def test_upload_fails_when_tag_resolution_fails(self, service, temp_file):
        with patch.object(
            service, "_get_or_create_tag_id", side_effect=httpx.HTTPStatusError(
                "error", request=MagicMock(), response=MagicMock()
            )
        ):
            with pytest.raises(httpx.HTTPStatusError):
                service.upload_medical_document(
                    document_path=temp_file,
                    patient_name="Nazra",
                    date="2026-08-31",
                    hospital_name="Test Hospital",
                    json_extraction={},
                )


class TestUploadMedicalDocumentCreatedDate:
    def test_created_date_set_for_parseable_date(self, service, temp_file):
        with patch.object(service, "_get_or_create_tag_id", return_value=1):
            with patch("services.paperless_ngx_service.httpx.Client") as mock_client_cls:
                client_instance = MagicMock()
                client_instance.post.return_value = _response({"status": "success"})
                mock_client_cls.return_value.__enter__.return_value = client_instance

                service.upload_medical_document(
                    document_path=temp_file,
                    patient_name="Nazra",
                    date="08-11-2025 03:17 PM",
                    hospital_name="Test Hospital",
                    json_extraction={},
                )

        _, kwargs = client_instance.post.call_args
        assert kwargs["data"]["created"] == "2025-11-08"

    def test_created_date_omitted_when_unparseable(self, service, temp_file):
        with patch.object(service, "_get_or_create_tag_id", return_value=1):
            with patch("services.paperless_ngx_service.httpx.Client") as mock_client_cls:
                client_instance = MagicMock()
                client_instance.post.return_value = _response({"status": "success"})
                mock_client_cls.return_value.__enter__.return_value = client_instance

                service.upload_medical_document(
                    document_path=temp_file,
                    patient_name="Nazra",
                    date="Unknown Date",
                    hospital_name="Test Hospital",
                    json_extraction={},
                )

        _, kwargs = client_instance.post.call_args
        assert "created" not in kwargs["data"]


class TestUploadMedicalDocumentReportTypeTag:
    def test_report_type_tag_merged_with_patient_tag(self, service, temp_file):
        def fake_get_or_create(tag_name):
            return {"Nazra": 42, "Laboratory Reports": 77}[tag_name]

        with patch.object(service, "_get_or_create_tag_id", side_effect=fake_get_or_create):
            with patch("services.paperless_ngx_service.httpx.Client") as mock_client_cls:
                client_instance = MagicMock()
                client_instance.post.return_value = _response({"status": "success"})
                mock_client_cls.return_value.__enter__.return_value = client_instance

                service.upload_medical_document(
                    document_path=temp_file,
                    patient_name="Nazra",
                    date="2026-08-31",
                    hospital_name="Test Hospital",
                    json_extraction={},
                    report_type="Laboratory Reports",
                )

        _, kwargs = client_instance.post.call_args
        assert sorted(kwargs["data"]["tags"]) == ["42", "77"]

    def test_no_report_type_tag_when_absent(self, service, temp_file):
        with patch.object(service, "_get_or_create_tag_id", return_value=42) as mock_tag:
            with patch("services.paperless_ngx_service.httpx.Client") as mock_client_cls:
                client_instance = MagicMock()
                client_instance.post.return_value = _response({"status": "success"})
                mock_client_cls.return_value.__enter__.return_value = client_instance

                service.upload_medical_document(
                    document_path=temp_file,
                    patient_name="Nazra",
                    date="2026-08-31",
                    hospital_name="Test Hospital",
                    json_extraction={},
                )

        mock_tag.assert_called_once_with("Nazra")

    def test_upload_fails_when_report_type_tag_resolution_fails(self, service, temp_file):
        def fake_get_or_create(tag_name):
            if tag_name == "Laboratory Reports":
                raise httpx.HTTPStatusError("error", request=MagicMock(), response=MagicMock())
            return 42

        with patch.object(service, "_get_or_create_tag_id", side_effect=fake_get_or_create):
            with pytest.raises(httpx.HTTPStatusError):
                service.upload_medical_document(
                    document_path=temp_file,
                    patient_name="Nazra",
                    date="2026-08-31",
                    hospital_name="Test Hospital",
                    json_extraction={},
                    report_type="Laboratory Reports",
                )


class TestUploadMedicalDocumentFromDictReportType:
    def test_report_type_and_date_extracted_and_passed_through(self, service, temp_file):
        medical_info = {
            "hospital_info": {
                "hospital_name": "Test Hospital",
                "report_type": "Laboratory Reports",
            },
            "patient_info": {
                "patient_name": "Nazra",
                "sample_date": "08-11-2025 03:17 PM",
            },
        }

        with patch.object(
            service, "upload_medical_document", return_value={"status": "success"}
        ) as mock_upload:
            service.upload_medical_document_from_dict(
                document_path=temp_file,
                medical_info=medical_info,
            )

        _, kwargs = mock_upload.call_args
        assert kwargs["report_type"] == "Laboratory Reports"
        assert kwargs["date"] == "08-11-2025 03:17 PM"

    def test_missing_report_type_passed_as_none(self, service, temp_file):
        medical_info = {
            "hospital_info": {"hospital_name": "Test Hospital"},
            "patient_info": {"patient_name": "Nazra", "sample_date": "08-11-2025 03:17 PM"},
        }

        with patch.object(
            service, "upload_medical_document", return_value={"status": "success"}
        ) as mock_upload:
            service.upload_medical_document_from_dict(
                document_path=temp_file,
                medical_info=medical_info,
            )

        _, kwargs = mock_upload.call_args
        assert kwargs["report_type"] is None


class TestUploadMedicalDocumentRealMultipartEncoding:
    """
    Regression coverage for a real bug: building `data` as a flat list of
    (key, value) tuples for repeated "tags" fields raised
    "sequence item 1: expected a bytes-like object, tuple found" once combined
    with `files=` in a real httpx multipart request - a mocked httpx.Client
    never exercises the actual encoder, so it slipped through unnoticed until
    it broke production uploads. Routing through httpx.MockTransport runs the
    real request-encoding path while still avoiding the network.
    """

    def test_multipart_request_with_multiple_tags_encodes_successfully(self, service, temp_file):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["request"] = request
            return httpx.Response(200, json={"status": "success"})

        real_client = httpx.Client(transport=httpx.MockTransport(handler))

        with patch.object(service, "_get_or_create_tag_id", side_effect=[42, 77]):
            with patch("services.paperless_ngx_service.httpx.Client", return_value=real_client):
                service.upload_medical_document(
                    document_path=temp_file,
                    patient_name="Nazra",
                    date="2026-08-31",
                    hospital_name="Test Hospital",
                    json_extraction={},
                    report_type="Laboratory Reports",
                )

        body = captured["request"].content
        assert body.count(b'name="tags"') == 2
        assert b"42" in body and b"77" in body
