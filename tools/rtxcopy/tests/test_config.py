import pytest
from pathlib import Path
from unittest.mock import patch

from rtxcopy.config import Config, load_config, save_config
from rtxcopy.destinations import NASDestination, ProxmoxLXCDestination


@pytest.fixture
def tmp_config_dir(tmp_path):
    with patch("rtxcopy.config.get_config_dir", return_value=tmp_path):
        (tmp_path / "keys").mkdir()
        yield tmp_path


def test_round_trip_nas(tmp_config_dir):
    dest = NASDestination(
        type="nas", name="TestNAS", host="192.168.10.5", port=22,
        username="admin", ssh_key_path="/tmp/key", default_remote_path="/backups",
    )
    config = Config(destinations=[dest], default_local_start_path="~/Downloads")
    save_config(config)
    loaded = load_config()
    assert len(loaded.destinations) == 1
    d = loaded.destinations[0]
    assert d.name == "TestNAS"
    assert d.host == "192.168.10.5"


def test_round_trip_proxmox(tmp_config_dir):
    dest = ProxmoxLXCDestination(
        type="proxmox_lxc", name="MediaLXC", node_host="192.168.10.2",
        node_port=22, node_username="root", ssh_key_path="/tmp/key", vmid=101,
    )
    config = Config(destinations=[dest])
    save_config(config)
    loaded = load_config()
    d = loaded.destinations[0]
    assert d.vmid == 101
    assert d.node_host == "192.168.10.2"


def test_empty_config(tmp_config_dir):
    config = load_config()
    assert config.destinations == []


def test_favorites_round_trip(tmp_config_dir):
    config = Config()
    config.add_favorite("TischNAS2", "/volume1/backups")
    config.add_favorite("TischNAS2", "/volume1/photos")
    config.add_favorite("MediaLXC", "/root/data")
    save_config(config)
    loaded = load_config()
    assert loaded.get_favorites("TischNAS2") == ["/volume1/backups", "/volume1/photos"]
    assert loaded.get_favorites("MediaLXC") == ["/root/data"]
    assert loaded.get_favorites("unknown") == []


def test_favorites_toggle(tmp_config_dir):
    config = Config()
    config.add_favorite("NAS", "/data")
    assert config.is_favorite("NAS", "/data")
    config.add_favorite("NAS", "/data")  # duplicate — should not add twice
    assert config.get_favorites("NAS") == ["/data"]
    config.remove_favorite("NAS", "/data")
    assert not config.is_favorite("NAS", "/data")
