"""Read and verify the exact immutable bytes sent to a review client."""
import hashlib,re

MAX_PNG_BYTES=16*1024*1024

class EvidenceReadError(ValueError):
    def __init__(self,message,code='ARCHIVE_INTEGRITY_FAILED',http_status=409):
        super().__init__(message);self.code=code;self.http_status=http_status

def read_verified_image(path,expected):
    if not isinstance(expected,str) or re.fullmatch('[0-9a-f]{64}',expected) is None:
        raise EvidenceReadError('存档缺少有效文件校验值；文件已保留，不能确认本次读取',code='ARCHIVE_HASH_INVALID')
    try:
        with path.open('rb') as stream:data=stream.read(MAX_PNG_BYTES+1)
    except OSError as error:
        raise EvidenceReadError('存档图像暂不可读或已缺失；请检查文件或使用备份，已有记录保持不变',code='ARCHIVE_IMAGE_UNAVAILABLE',http_status=503) from error
    if len(data)>MAX_PNG_BYTES:
        raise EvidenceReadError('存档图像超过读取上限；文件已保留，不能确认完整性',code='ARCHIVE_IMAGE_TOO_LARGE')
    digest=hashlib.sha256(data).hexdigest()
    if digest!=expected:
        raise EvidenceReadError('存档图像 SHA256 与保存时不一致；文件已保留，请使用备份核查')
    # Do not reopen the pathname after verifying: it may now name another file.
    return data,digest
