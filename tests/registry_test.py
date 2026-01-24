from pathlib import Path
from backupctl.models.registry import Job, JobStatusType, load_registry, write_registry

def test_registry_roundtrip(tmp_path: Path) -> None:
    """Writes and reloads the registry to confirm persistence."""
    registry_path = tmp_path / "REGISTRY"
    job = Job(name="sample", cmd="0 3 * * * backupctl run sample", status=JobStatusType.enabled)
    write_registry(registry_path, {"sample": job})

    loaded = load_registry(registry_path)

    assert loaded is not None
    assert "sample" in loaded
    assert loaded["sample"].cmd == job.cmd
