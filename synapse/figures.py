"""Validate PNG bytes and publish figures atomically, avoiding partial outputs."""

from io import BytesIO
import os
from pathlib import Path
import tempfile

from PIL import Image


def save_png(figure, path, *, dpi):
    path = Path(path)
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=dpi)
    data = buffer.getvalue()
    with Image.open(BytesIO(data)) as image:
        image.verify()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            written = stream.write(data)
            if written != len(data):
                raise OSError(f"Incomplete image write: {path.name}")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        if path.read_bytes() != data:
            raise OSError(f"Image verification failed after saving: {path.name}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
