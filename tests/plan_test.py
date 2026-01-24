from backupctl.models.plan_config import load_from_target
from backupctl.models.user_config import (
    NamedTarget,
    Target,
    Remote,
    RemoteDest,
    RsyncCfg,
    Schedule,
    NotificationCfg,
)

def test_plan_generation(tmp_path):
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    password_file = tmp_path / ".rsync_pass"
    password_file.write_text("testpass\n", encoding="utf-8")

    target = Target(
        remote=Remote(
            host="127.0.0.1",
            port=873,
            user="testuser",
            password_file=str(password_file),
            dest=RemoteDest(module="backup", folder="."),
        ),
        rsync=RsyncCfg(
            sources=[str(source_dir)],
        ),
        schedule=Schedule(),
        notification=NotificationCfg(),
    )

    named = NamedTarget.from_target("sample", target)
    plan = load_from_target(named)

    assert plan.name == "sample"
    assert plan.log.endswith("/sample")
    assert isinstance(plan.command, list)
    assert plan.command[0] == "rsync"
