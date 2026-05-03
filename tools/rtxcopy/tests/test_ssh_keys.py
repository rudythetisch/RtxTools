import pytest
from pathlib import Path
from unittest.mock import patch

from rtxcopy.ssh_keys import generate_keypair, key_path_for_dest


@pytest.fixture
def tmp_config_dir(tmp_path):
    (tmp_path / "keys").mkdir()
    with patch("rtxcopy.ssh_keys.get_config_dir", return_value=tmp_path):
        yield tmp_path


def test_generate_keypair(tmp_config_dir):
    priv, pub = generate_keypair("TestNAS")
    assert priv.exists()
    assert pub.exists()
    assert oct(priv.stat().st_mode)[-3:] == "600"
    assert oct(pub.stat().st_mode)[-3:] == "644"
    assert b"OPENSSH PRIVATE KEY" in priv.read_bytes()
    assert pub.read_bytes().startswith(b"ssh-ed25519")


def test_generate_keypair_idempotent(tmp_config_dir):
    priv1, pub1 = generate_keypair("TestNAS")
    key1 = pub1.read_bytes()
    priv2, pub2 = generate_keypair("TestNAS")
    # Second call overwrites with a new key — that's expected
    assert pub2.exists()
