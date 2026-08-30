"""
Tests for HealthRecordRepository - get_by_id, update, delete, and id exposure
in get_all().
"""
from datetime import datetime, timezone


def _make_patient(patient_repo, name="Test Patient"):
    return patient_repo.add(name)["id"]


def test_get_all_includes_id(patient_repo, record_repo):
    patient_id = _make_patient(patient_repo)
    record_repo.save(
        timestamp=datetime.now(timezone.utc),
        patient_id=patient_id,
        record_type="BP",
        value="120/80",
        unit="mmHg"
    )

    records = record_repo.get_all()
    assert len(records) == 1
    assert isinstance(records[0].id, int)


def test_get_by_id_found(patient_repo, record_repo):
    patient_id = _make_patient(patient_repo)
    record_id, _ = record_repo.save(
        timestamp=datetime.now(timezone.utc),
        patient_id=patient_id,
        record_type="BP",
        value="120/80",
        unit="mmHg"
    )

    record = record_repo.get_by_id(record_id)
    assert record is not None
    assert record["id"] == record_id
    assert record["value"] == "120/80"
    assert record["unit"] == "mmHg"


def test_get_by_id_not_found(record_repo):
    assert record_repo.get_by_id(999999) is None


def test_update_value_only(patient_repo, record_repo):
    patient_id = _make_patient(patient_repo)
    record_id, _ = record_repo.save(
        timestamp=datetime.now(timezone.utc),
        patient_id=patient_id,
        record_type="BP",
        value="120/80",
        unit="mmHg"
    )

    updated = record_repo.update(record_id, value="121/81")
    assert updated["value"] == "121/81"
    assert updated["unit"] == "mmHg"


def test_update_unit_only(patient_repo, record_repo):
    patient_id = _make_patient(patient_repo)
    record_id, _ = record_repo.save(
        timestamp=datetime.now(timezone.utc),
        patient_id=patient_id,
        record_type="BP",
        value="120/80",
        unit="mmHg"
    )

    updated = record_repo.update(record_id, unit="kPa", update_unit=True)
    assert updated["value"] == "120/80"
    assert updated["unit"] == "kPa"


def test_update_value_and_unit(patient_repo, record_repo):
    patient_id = _make_patient(patient_repo)
    record_id, _ = record_repo.save(
        timestamp=datetime.now(timezone.utc),
        patient_id=patient_id,
        record_type="BP",
        value="120/80",
        unit="mmHg"
    )

    updated = record_repo.update(record_id, value="130/85", unit="kPa", update_unit=True)
    assert updated["value"] == "130/85"
    assert updated["unit"] == "kPa"


def test_update_nonexistent_id_returns_none(record_repo):
    assert record_repo.update(999999, value="1") is None


def test_update_no_fields_returns_current_record(patient_repo, record_repo):
    patient_id = _make_patient(patient_repo)
    record_id, _ = record_repo.save(
        timestamp=datetime.now(timezone.utc),
        patient_id=patient_id,
        record_type="BP",
        value="120/80",
        unit="mmHg"
    )

    unchanged = record_repo.update(record_id)
    assert unchanged["value"] == "120/80"
    assert unchanged["unit"] == "mmHg"


def test_delete_existing(patient_repo, record_repo):
    patient_id = _make_patient(patient_repo)
    record_id, _ = record_repo.save(
        timestamp=datetime.now(timezone.utc),
        patient_id=patient_id,
        record_type="BP",
        value="120/80",
        unit="mmHg"
    )

    assert record_repo.delete(record_id) is True
    assert record_repo.get_by_id(record_id) is None


def test_delete_nonexistent_returns_false(record_repo):
    assert record_repo.delete(999999) is False
