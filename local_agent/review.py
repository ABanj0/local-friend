"""Resource versions for one-use reviews, not authority or an OS isolation boundary."""
import hashlib
import os
import stat

from .safety import Denied

CONFLICT = "Review conflict: resource changed; request a fresh review before retrying."


def signature(info):
    # Windows path/handle APIs can disagree on ctime after Git's atomic rename.
    # File identity, size, mtime and the separately checked content hash are stable.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns)


def fingerprint(path, limit=16 * 1024**2):
    """Include identity as well as bytes: delete/recreate with identical content conflicts."""
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise Denied("Review requires a regular file with one link")
    if before.st_size > limit:
        raise Denied("Resource exceeds the review size limit")
    with path.open("rb") as stream:
        if signature(before) != signature(os.fstat(stream.fileno())):
            raise Denied(CONFLICT)
        digest = hashlib.sha256()
        total = 0
        while chunk := stream.read(65536):
            total += len(chunk)
            if total > limit:
                raise Denied("Resource exceeds the review size limit")
            digest.update(chunk)
        if signature(before) != signature(os.fstat(stream.fileno())):
            raise Denied(CONFLICT)
    if signature(before) != signature(path.lstat()):
        raise Denied(CONFLICT)
    return (str(path), *signature(before), digest.hexdigest())


def require_unchanged(expected, actual):
    if expected != actual:
        raise Denied(CONFLICT)
