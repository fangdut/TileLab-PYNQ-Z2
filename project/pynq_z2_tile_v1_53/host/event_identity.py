"""Decode a frame-bound recovery generation, never infer it from live stats."""
def decode_event_identity(word,version):
    if type(word) is not int or not 0<=word<=0xffffffff:
        raise ValueError('Invalid event identity word')
    if version<0x11500:
        return dict(event_reason=word,recovery_generation=None)
    reason=word&255;generation=word>>8
    # V1.32 allows three successful recoveries per boot. Future protocols must
    # explicitly extend this rule instead of silently accepting reserved bits.
    if reason not in (1,2,3) or generation>3:
        raise ValueError('Invalid event reason or recovery generation')
    return dict(event_reason=reason,recovery_generation=generation)
