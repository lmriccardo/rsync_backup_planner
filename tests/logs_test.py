from backupctl.inspect._core import _parse_log_meta

def test_parse_log_meta_with_stderr(tmp_path):
    log_path = tmp_path / "sample.log"
    log_path.write_text(
        "\n".join(
            [
                "Started : 2025-01-01T00:00:00",
                "Command : rsync ...",
                "----- STDOUT -----",
                "ok",
                "----- STDERR -----",
                "something went wrong",
                "----- END STDERR -----",
                "Finished : 2025-01-01T00:01:00",
                "Exit code: 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    last_run, exit_code, last_error = _parse_log_meta(log_path)

    assert last_run == "2025-01-01T00:00:00"
    assert exit_code == "1"
    assert last_error == "something went wrong"


def test_parse_log_meta_without_stderr(tmp_path):
    log_path = tmp_path / "sample.log"
    log_path.write_text(
        "\n".join(
            [
                "Started : 2025-01-01T00:00:00",
                "Command : rsync ...",
                "----- STDOUT -----",
                "ok",
                "----- STDERR -----",
                "",
                "----- END STDERR -----",
                "Finished : 2025-01-01T00:01:00",
                "Exit code: 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _, exit_code, last_error = _parse_log_meta(log_path)

    assert exit_code == "0"
    assert last_error == "none"
