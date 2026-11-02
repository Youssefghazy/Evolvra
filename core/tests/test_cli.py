import os

from evolvra import cli


def test_load_dotenv_reads_file_without_overriding(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        '# comment\nGROQ_API_KEY="from-file"\nEXISTING=file\n\nBROKEN LINE\n', encoding="utf-8"
    )
    sub = tmp_path / "core"
    sub.mkdir()
    monkeypatch.chdir(sub)  # found in a parent directory
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("EXISTING", "env")
    found = cli.load_dotenv()
    assert found == tmp_path / ".env"
    assert os.environ["GROQ_API_KEY"] == "from-file"
    assert os.environ["EXISTING"] == "env"


def test_cli_agents_on_empty_db(tmp_path, capsys):
    assert cli.main(["--db", str(tmp_path / "t.db"), "agents"]) == 0
    assert "no agents yet" in capsys.readouterr().out
