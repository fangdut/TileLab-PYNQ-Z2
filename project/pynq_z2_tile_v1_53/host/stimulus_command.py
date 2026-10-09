"""Small versioned HDMI test-source command; never a shell command."""
import secrets
MAX_COMMAND_BYTES=128
SOURCES={'video','fast','ultrafast','real_video','holdout_video','dark_video','calib_video','transport_noise','burst'}

def valid_source(value):
    if not isinstance(value,str):return False
    if value in SOURCES:return True
    for prefix,count,digits in [('station_',7,1),('real_',117,3),('calib_',230,3),('holdout_',24,3)]:
        if value.startswith(prefix):
            suffix=value[len(prefix):]
            return len(suffix)==digits and suffix.isascii() and suffix.isdigit() and int(suffix)<count
    return False

def valid_id(value):
    return isinstance(value,str) and len(value)==32 and all(c in '0123456789abcdef' for c in value)

def parse_command(text):
    if not isinstance(text,str) or len(text.encode('utf-8'))>MAX_COMMAND_BYTES:raise ValueError('输入命令过大或类型错误')
    text=text.strip()
    if valid_source(text):return dict(version=0,source=text,request_id=None)
    fields=text.split(' ')
    if len(fields)!=3 or fields[0]!='TILE_CMD_V1' or not valid_id(fields[1]) or not valid_source(fields[2]):raise ValueError('输入命令未知、不完整或身份无效')
    return dict(version=1,source=fields[2],request_id=fields[1])

def make_command(source,request_id=None):
    if not valid_source(source):raise ValueError('Unknown stimulus')
    request_id=secrets.token_hex(16) if request_id is None else request_id
    if not valid_id(request_id):raise ValueError('Invalid stimulus request identity')
    payload=f'TILE_CMD_V1 {request_id} {source}\n'.encode('ascii')
    assert len(payload)<=MAX_COMMAND_BYTES
    return payload,request_id
