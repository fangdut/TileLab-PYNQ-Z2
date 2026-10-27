# V199 transport CRC candidate accepted in the V199 package

The PL bitstream and detector model remain unchanged. The ARM change replaces
byte-at-a-time IEEE CRC32 with slicing-by-four CRC32. It adds no resize,
convolution, feature, score, threshold or mask computation to the ARM.

Generate the source from the hash-verified baseline:

```text
python prepare_transport.py --bundle ACCEPTED_BUNDLE --out NEW_SOURCE
```

Set `TILE_TEXTURE_TRANSPORT_SOURCE` to `NEW_SOURCE/main.c` when running
`scripts/texture_v170/rebuild_transport.py`, together with the matching BSP,
hardware, model and a new software output directory. Rebuild regenerates the
model identity header and records the CRC helper hash. Never copy a firmware
header from a different profile.

Native correctness test:

```text
gcc -O2 -Wall -Wextra test_crc32.c -o test_crc32.exe
test_crc32.exe
```

The test checks17416 cases including unaligned buffers and incremental updates
against an independent bitwise reference. Native correctness is separate from
board acceptance. See `../../reports/v199/transport_acceptance.json` for the
32-call matched comparison, failed first trial, all117 exact board payloads,
and packaged workflow. Sequence numbers are the only raw-output comparison
exception.

The PC connection establishment default is0.5s on the directly connected LAN.
The complete inference receive timeout is unchanged. Only establishment may
retry, before any request bytes are sent; sent requests and corrupt replies
are never replayed. Set `Board(connect_timeout=3)` for a link needing a longer
connection deadline.

This is a transport improvement, not a new FPGA architecture or accuracy
claim. The original stable archive remains the recovery baseline.
