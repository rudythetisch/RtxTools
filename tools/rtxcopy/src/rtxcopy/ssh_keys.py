from __future__ import annotations
import shutil
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from rtxcopy.config import get_config_dir


def key_path_for_dest(dest_name: str) -> Path:
    return get_config_dir() / "keys" / dest_name / "id_ed25519"


def generate_keypair(dest_name: str) -> tuple[Path, Path]:
    key_dir = get_config_dir() / "keys" / dest_name
    key_dir.mkdir(parents=True, exist_ok=True)
    key_dir.chmod(0o700)

    private_key = Ed25519PrivateKey.generate()
    priv_path = key_dir / "id_ed25519"
    pub_path = key_dir / "id_ed25519.pub"

    priv_bytes = private_key.private_bytes(Encoding.PEM, PrivateFormat.OpenSSH, NoEncryption())
    priv_path.write_bytes(priv_bytes)
    priv_path.chmod(0o600)

    pub_bytes = private_key.public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH)
    pub_path.write_bytes(pub_bytes + b"\n")
    pub_path.chmod(0o644)

    return priv_path, pub_path


def import_keypair(dest_name: str, private_key_path: Path) -> tuple[Path, Path]:
    key_dir = get_config_dir() / "keys" / dest_name
    key_dir.mkdir(parents=True, exist_ok=True)
    key_dir.chmod(0o700)

    priv_path = key_dir / "id_ed25519"
    pub_path = key_dir / "id_ed25519.pub"

    shutil.copy2(private_key_path, priv_path)
    priv_path.chmod(0o600)

    src_pub = private_key_path.with_suffix(".pub")
    if not src_pub.exists():
        src_pub = Path(str(private_key_path) + ".pub")
    if src_pub.exists():
        shutil.copy2(src_pub, pub_path)
        pub_path.chmod(0o644)
    else:
        _derive_public_key(priv_path, pub_path)

    return priv_path, pub_path


def deploy_public_key(host: str, port: int, username: str, password: str, dest_name: str) -> None:
    import paramiko

    pub_path = key_path_for_dest(dest_name).with_suffix(".pub")
    if not pub_path.exists():
        raise FileNotFoundError(f"Public key not found: {pub_path}")

    pubkey_line = pub_path.read_text().strip()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            host, port=port, username=username, password=password,
            timeout=10, allow_agent=False, look_for_keys=False,
        )
        # Single command to avoid MaxSessions=1 issues on Synology/restricted SSH daemons.
        # Key is passed via stdin to avoid shell quoting issues with the long key string.
        cmd = "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
        stdin, stdout, stderr = client.exec_command(cmd)
        stdin.write(pubkey_line + "\n")
        stdin.channel.shutdown_write()
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            raise RuntimeError(f"Remote command failed (exit {exit_code}): {stderr.read().decode()}")
    finally:
        client.close()


def _derive_public_key(priv_path: Path, pub_path: Path) -> None:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    priv_bytes = priv_path.read_bytes()
    private_key = load_pem_private_key(priv_bytes, password=None)
    pub_bytes = private_key.public_key().public_bytes(Encoding.OpenSSH, PublicFormat.OpenSSH)
    pub_path.write_bytes(pub_bytes + b"\n")
    pub_path.chmod(0o644)
