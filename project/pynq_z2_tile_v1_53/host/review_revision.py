"""Persistent optimistic concurrency for human review, not detector metadata."""
MAX_REVISION=9007199254740991  # Largest exactly represented JavaScript integer.

class ReviewError(ValueError):
    def __init__(self,message,code='REVIEW_CONFLICT',http_status=409,current=None):
        super().__init__(message);self.code=code;self.http_status=http_status;self.current=current

def require_revision(value):
    if type(value) is not int or not 0<=value<=MAX_REVISION:
        raise ReviewError('缺少有效复核修订号；请重新打开记录后再提交',code='REVIEW_REVISION_REQUIRED',http_status=428)
    return value
