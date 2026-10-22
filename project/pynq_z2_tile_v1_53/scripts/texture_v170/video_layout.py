"""Versioned physical input ownership; unknown layouts are never guessed."""
LEGACY_VERSIONS=(0x17100001,0x17200001)
OVERLAP_VERSION=0x17500001
FRAME_BASES=(0x06000000,0x06400000,0x06800000,0x06c00000)
def validate_frame_base(version,base):
    if version in LEGACY_VERSIONS:
        if base!=FRAME_BASES[0]:raise ValueError('Legacy video requires the fixed input slot')
    elif version==OVERLAP_VERSION:
        if base not in FRAME_BASES:raise ValueError('Published input base is outside the four owned slots')
    else:raise ValueError('Unknown video input ownership layout')
    return base
