"""
SSH/SFTP connector for remote farmer audio sources.

When a farmer registers an SSH data source, their connection credentials
(host, port, username, password or private_key, remote_folder) are stored
in FarmerDataSource.connection_config as JSON.

The poller calls `download_new_files()` each scan cycle. Only files that
haven't been seen yet are downloaded to a local staging folder and returned
for processing.

Paramiko is the SSH library: it handles key exchange, auth, and gives us an
SFTP channel over the same connection. We close both the SFTP channel and
the SSH transport after every scan to avoid stale connections.
"""

import io
from pathlib import Path
from typing import Optional

import paramiko

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}


def _build_client(config: dict) -> paramiko.SSHClient:
    """
    Create and return an authenticated SSH client from a connection_config dict.

    Required keys:  ssh_host, ssh_username
    Optional keys:  ssh_port (default 22), ssh_password, ssh_private_key (PEM string)

    If ssh_private_key is provided it takes priority over ssh_password.
    """
    client = paramiko.SSHClient()
    # AutoAddPolicy accepts any host key — acceptable for an internal tool.
    # In production you'd load a known_hosts file and use RejectPolicy.
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    host     = config["ssh_host"]
    port     = int(config.get("ssh_port", 22))
    username = config["ssh_username"]
    password = config.get("ssh_password")
    pem_key  = config.get("ssh_private_key")

    if pem_key:
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(pem_key))
        client.connect(host, port=port, username=username, pkey=pkey, timeout=15)
    else:
        client.connect(host, port=port, username=username, password=password, timeout=15)

    return client


def test_connection(config: dict) -> dict:
    """
    Try to open an SSH connection and list the remote folder.
    Returns {"ok": True} or {"ok": False, "error": "<message>"}.

    Called when a farmer first registers their SSH data source so we can
    give immediate feedback rather than waiting for the next poll cycle.
    """
    try:
        client = _build_client(config)
        sftp = client.open_sftp()
        remote_folder = config.get("remote_folder", "/")
        sftp.listdir(remote_folder)
        sftp.close()
        client.close()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def download_file_bytes(config: dict, remote_path: str) -> bytes:
    """
    Open a single remote file over SFTP and return its contents as bytes.

    Used by the processing job to fetch audio for a pending AudioSource
    whose source_url is a remote path (ssh source type).
    """
    client = _build_client(config)
    sftp = client.open_sftp()
    try:
        with sftp.open(remote_path, "rb") as fh:
            return fh.read()
    finally:
        sftp.close()
        client.close()


def download_new_files(
    config: dict,
    known_paths: set,
    staging_dir: Path,
) -> list[Path]:
    """
    Connect to the farmer's remote server, list audio files in remote_folder,
    download any that are not in known_paths, and return the local paths.

    Args:
        config       – connection_config dict from FarmerDataSource
        known_paths  – set of source_url strings already in audio_sources (skip these)
        staging_dir  – local folder to save downloaded files into

    Returns:
        List of Path objects for successfully downloaded files.
    """
    staging_dir.mkdir(parents=True, exist_ok=True)

    remote_folder = config.get("remote_folder", "/")
    downloaded: list[Path] = []

    client = _build_client(config)
    sftp = client.open_sftp()

    try:
        remote_files = sftp.listdir_attr(remote_folder)

        for attr in remote_files:
            filename = attr.filename
            if Path(filename).suffix.lower() not in AUDIO_EXTENSIONS:
                continue

            remote_path = f"{remote_folder.rstrip('/')}/{filename}"

            # Use remote path as the canonical identifier (matches source_url)
            if remote_path in known_paths:
                continue

            local_path = staging_dir / filename
            sftp.get(remote_path, str(local_path))
            downloaded.append(local_path)

            print(f"[SSH] downloaded {remote_path} → {local_path}")
    finally:
        sftp.close()
        client.close()

    return downloaded
