from __future__ import annotations
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import paramiko

from rtxcopy.destinations import Destination, NASDestination, ProxmoxLXCDestination, ProxmoxQEMUDestination


@dataclass
class TransferJob:
    sources: list[Path]
    destination: Destination
    remote_path: str
    dry_run: bool = False


ProgressCallback = Callable[[int, int], None]  # (bytes_sent, total_bytes)


def transfer(job: TransferJob, progress_callback: ProgressCallback | None = None) -> None:
    dest = job.destination
    if isinstance(dest, NASDestination):
        _transfer_nas(job, progress_callback)
    elif isinstance(dest, (ProxmoxLXCDestination, ProxmoxQEMUDestination)):
        _transfer_proxmox(job, progress_callback)


def _connect(host: str, port: int, username: str, key_path: Path) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, port=port, username=username, key_filename=str(key_path), timeout=15)
    return client


def _total_size(sources: list[Path]) -> int:
    total = 0
    for src in sources:
        if src.is_dir():
            for f in src.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        elif src.is_file():
            total += src.stat().st_size
    return total


def _transfer_nas(job: TransferJob, progress_callback: ProgressCallback | None) -> None:
    dest = job.destination
    assert isinstance(dest, NASDestination)

    if job.dry_run:
        return

    client = _connect(dest.host, dest.port, dest.username, dest.key_path)
    try:
        sftp = client.open_sftp()
        total = _total_size(job.sources)
        sent = 0

        def _cb(transferred: int, _total: int) -> None:
            nonlocal sent
            sent += transferred
            if progress_callback:
                progress_callback(sent, total)

        for src in job.sources:
            remote_dest = job.remote_path.rstrip("/") + "/" + src.name
            _sftp_upload(sftp, src, remote_dest, _cb)
        sftp.close()
    finally:
        client.close()


def _sftp_upload(sftp: paramiko.SFTPClient, local: Path, remote: str, cb: Callable) -> None:
    if local.is_file():
        sftp.put(str(local), remote, callback=cb)
    elif local.is_dir():
        try:
            sftp.mkdir(remote)
        except OSError:
            pass
        for child in local.iterdir():
            _sftp_upload(sftp, child, remote + "/" + child.name, cb)


def _transfer_proxmox(job: TransferJob, progress_callback: ProgressCallback | None) -> None:
    from rtxcopy.proxmox import push_to_lxc, push_to_qemu

    dest = job.destination
    assert isinstance(dest, (ProxmoxLXCDestination, ProxmoxQEMUDestination))

    if job.dry_run:
        return

    client = _connect(dest.node_host, dest.node_port, dest.node_username, dest.key_path)
    try:
        sftp = client.open_sftp()
        total = _total_size(job.sources)
        sent = 0

        with tempfile.TemporaryDirectory() as tmp:
            for src in job.sources:
                tmp_remote = f"/tmp/rtxcopy_{src.name}"
                remote_dest = job.remote_path.rstrip("/") + "/" + src.name

                def _cb(transferred: int, _total: int) -> None:
                    nonlocal sent
                    sent += transferred
                    if progress_callback:
                        progress_callback(sent, total)

                _sftp_upload(sftp, src, tmp_remote, _cb)

                if isinstance(dest, ProxmoxLXCDestination):
                    push_to_lxc(client, dest.vmid, tmp_remote, remote_dest)
                else:
                    push_to_qemu(client, dest.vmid, tmp_remote, remote_dest)

                client.exec_command(f"rm -rf {tmp_remote!r}")

        sftp.close()
    finally:
        client.close()
