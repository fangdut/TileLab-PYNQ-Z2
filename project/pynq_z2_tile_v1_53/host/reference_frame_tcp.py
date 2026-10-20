"""Bounded, CRC-checked full-frame FPGA metric protocol on private lab TCP9134."""
import hashlib,secrets,socket,struct,time,zlib
import numpy as np
MAGIC=0x52463167
def exact(sock,n,deadline=None):
    out=bytearray(n);view=memoryview(out);offset=0
    while offset<n:
        if deadline is not None:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Reference logical request deadline exceeded')
            sock.settimeout(remaining)
        got=sock.recv_into(view[offset:])
        if not got:raise OSError('Incomplete reference response')
        offset+=got
    return bytes(out)
def inspect(address,paired,fit,source_crc=0,reference_crc=0,timeout=15):
    if paired.shape!=(500,500) or paired.dtype!=np.dtype('<u8'):raise ValueError('Expected500x500 paired uint64')
    gains=fit['gain_q8'];offsets=fit['offset_integer']
    if len(gains)!=3 or len(offsets)!=3 or any(type(n) is not int or not 205<=n<=320 for n in gains) or any(type(n) is not int or not -20<=n<=20 for n in offsets):raise ValueError('Unsupported photometric coefficients')
    payload=paired.tobytes();nonce=secrets.randbelow(0xffffffff)+1
    words=[MAGIC,2,nonce,len(payload),zlib.crc32(payload),*gains,*[n&0xffffffff for n in offsets],18,9,source_crc,reference_crc]
    head=struct.pack('<15I',*words);head+=struct.pack('<I',zlib.crc32(head));started=time.perf_counter();deadline=time.monotonic()+timeout
    with socket.create_connection((address,9134),timeout=timeout) as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4*1024*1024);s.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        s.sendall(head+payload);raw=exact(s,64,deadline);r=struct.unpack('<16I',raw)
        if r[0]!=MAGIC or r[2]!=nonce or r[15]!=zlib.crc32(raw[:60]) or r[9]!=0x16700601 or r[10]!=0x16700 or r[11]!=words[4] or r[12]!=source_crc or r[13]!=reference_crc:raise ValueError('Reference result identity/CRC mismatch')
        if r[1]!=0 or r[3]!=1000000 or r[7:9]!=(500,500) or not r[14]:raise ValueError('FPGA reference engine rejected or returned incomplete output')
        body=exact(s,r[3],deadline)
        if zlib.crc32(body)!=r[4]:raise ValueError('FPGA score CRC mismatch')
    proof=dict(request_id=nonce,pl_id=r[9],firmware=r[10],input_crc32=r[11],output_crc32=r[4],output_crc_verified=True,paired_sha256=hashlib.sha256(payload).hexdigest(),score_sha256=hashlib.sha256(body).hexdigest(),engine_seconds=((r[6]<<32)|r[5])/r[14],request_seconds=time.perf_counter()-started,partition='HOST_ALIGNMENT_MATCHED_REFERENCE_EDGE_MAP;PL_Q8_NORMALIZATION_FULL_FRAME_SCORE;HOST_COMPONENTS')
    return np.frombuffer(body,dtype='<u4').reshape(500,500).copy(),proof
