import pytest
import tempfile
from pathlib import Path

from pforge.storage import cas

# We need to patch the _CAS_ROOT variable in the cas module for testing
@pytest.fixture(autouse=True)
def patch_cas_root(monkeypatch):
    """
    This fixture automatically patches the CAS root for every test in this file
    to use a temporary directory, ensuring tests are isolated and don't leave
    artifacts behind.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        monkeypatch.setattr(cas, "_CAS_ROOT", temp_path)
        yield temp_path

def test_write_and_read_blob():
    """
    Tests that data can be written to the CAS and then read back correctly.
    """
    test_data = b"Hello, pForge!"

    # Write the data and get its hash
    sha256_hash = cas.write_blob(test_data)

    assert isinstance(sha256_hash, str)
    assert len(sha256_hash) == 64

    # Read the data back using the hash
    read_data = cas.read_blob(sha256_hash)

    assert read_data == test_data

def test_write_is_idempotent():
    """
    Tests that writing the same data multiple times does not change the
    stored file or raise an error.
    """
    test_data = "Idempotent write test"

    hash1 = cas.write_blob(test_data)
    # Get the modification time of the stored file
    storage_path = cas._get_storage_path(hash1)
    mtime1 = storage_path.stat().st_mtime

    # Write the same data again
    hash2 = cas.write_blob(test_data)
    mtime2 = storage_path.stat().st_mtime

    assert hash1 == hash2
    # The file should not have been modified
    assert mtime1 == mtime2

def test_read_nonexistent_blob_raises_error():
    """
    Tests that trying to read a blob that doesn't exist raises FileNotFoundError.
    """
    non_existent_hash = "f" * 64
    with pytest.raises(FileNotFoundError):
        cas.read_blob(non_existent_hash)

def test_data_corruption_detection(patch_cas_root):
    """
    Tests that the CAS detects if a blob file has been corrupted on disk.
    """
    test_data = b"This data will be corrupted."
    sha256_hash = cas.write_blob(test_data)

    # Manually corrupt the file on disk
    storage_path = cas._get_storage_path(sha256_hash)
    storage_path.write_bytes(b"This is now corrupted data.")

    # Trying to read the blob should now raise a DataCorruptionError
    with pytest.raises(cas.DataCorruptionError):
        cas.read_blob(sha256_hash)
