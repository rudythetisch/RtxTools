from __future__ import annotations
import paramiko


def push_to_lxc(ssh: paramiko.SSHClient, vmid: int, src_on_node: str, dest_in_container: str) -> None:
    cmd = f"pct push {vmid} {src_on_node!r} {dest_in_container!r}"
    _, stdout, stderr = ssh.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        raise RuntimeError(f"pct push failed (exit {exit_code}): {stderr.read().decode()}")


def push_to_qemu(ssh: paramiko.SSHClient, vmid: int, src_on_node: str, dest_in_vm: str) -> None:
    # Requires QEMU Guest Agent installed in the VM
    cmd = f"qm guest exec {vmid} -- bash -c 'cat > {dest_in_vm!r}' < {src_on_node!r}"
    _, stdout, stderr = ssh.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        raise RuntimeError(f"qm guest exec failed (exit {exit_code}): {stderr.read().decode()}")


def list_containers(ssh: paramiko.SSHClient) -> list[dict]:
    results = []
    for vm_type, cmd in [("lxc", "pct list"), ("qemu", "qm list")]:
        _, stdout, _ = ssh.exec_command(cmd)
        lines = stdout.read().decode().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if parts:
                results.append({"vmid": parts[0], "name": parts[1] if len(parts) > 1 else "", "type": vm_type})
    return results
