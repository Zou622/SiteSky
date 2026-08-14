import hashlib
import os

from django.core.files.storage import FileSystemStorage


class DedupFileSystemStorage(FileSystemStorage):
    """
    FileSystemStorage that deduplicates files by content hash.

    Saved filenames use the SHA1 of the file content (keeping original extension).
    If a file with the same hash already exists, the existing path is returned
    and the uploaded content is discarded.
    """

    def _save(self, name, content):
        # Compute SHA1 hash of the uploaded content
        content.seek(0)
        h = hashlib.sha1()
        for chunk in content.chunks():
            h.update(chunk)
        digest = h.hexdigest()

        # preserve extension and directory
        base_dir = os.path.dirname(name)
        ext = os.path.splitext(name)[1]
        new_name = os.path.join(base_dir, f"{digest}{ext}") if base_dir else f"{digest}{ext}"

        # If file already exists, reuse it
        if self.exists(new_name):
            try:
                content.close()
            except Exception:
                pass
            return new_name

        # Ensure directory exists on the filesystem
        full_path = self.path(new_name)
        folder = os.path.dirname(full_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        # Reset pointer and save under the hashed name
        content.seek(0)
        return super()._save(new_name, content)
