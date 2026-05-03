import click


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Copy files to NAS or Proxmox LXC/VM over SSH."""
    if ctx.invoked_subcommand is None:
        from rtxcopy.app import RtxCopyApp
        RtxCopyApp().run()


@main.command()
def manage() -> None:
    """Manage destinations and SSH keys."""
    from rtxcopy.app import RtxCopyApp
    RtxCopyApp(start_screen="manage").run()


@main.command()
@click.argument("dest_name")
def keygen(dest_name: str) -> None:
    """Generate or deploy SSH key for a destination (non-interactive)."""
    from rtxcopy.ssh_keys import generate_keypair
    priv, pub = generate_keypair(dest_name)
    click.echo(f"Key pair generated:\n  Private: {priv}\n  Public:  {pub}")


if __name__ == "__main__":
    main()
