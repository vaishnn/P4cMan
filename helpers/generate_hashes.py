import hashlib
import logging

logger = logging.getLogger(__name__)


def hash_file(file_path: str) -> str:
    """Calculates the SHA-256 hash of a file and return SHA-256 string"""
    # a hash object
    sha256_hash = hashlib.sha256()

    try:
        # Open the file in binary for efficient and less memory consumption
        with open(file_path, "rb") as f:
            # Read the file in some chunks and update the hash
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

            return sha256_hash.hexdigest()
    except FileNotFoundError:
        logging.error(f"Error: File not found at {file_path}")
        return ""
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return ""
