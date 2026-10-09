from pathlib import Path
R=Path(__file__).resolve().parents[1]
if (R/'scripts/board_v112_transport.py').exists():raise SystemExit('Seed already generated; edit the generated tests directly.')
s=(R/'scripts/board_v111_transport.py').read_text().replace('0x10b00','0x10c00')
s=s.replace("assert c.last_timing['pixel_crc_verified'];","assert c.last_timing['pixel_crc_verified'] and c.last_timing['header_crc_verified'];")
(R/'scripts/board_v112_transport.py').write_text(s)
s=(R/'scripts/board_v111_recovery.py').read_text().replace('0x10b00','0x10c00')
s=s.replace('corrupt_rle=False):','corrupt_rle=False,corrupt_identity=None):')
s=s.replace('self.corrupt_rle=corrupt_rle;', 'self.corrupt_identity=corrupt_identity;self.identity_proof=None;self.corrupt_rle=corrupt_rle;')
old="head=exact(board,272);h=struct.unpack('<68I',head);body=exact(board,h[2]) if h[2] else b''"
new="prefix=exact(board,272);h=struct.unpack('<68I',prefix);head=prefix+(exact(board,4) if h[3]&4 else b'');body=exact(board,h[2]) if h[2] else b''"
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace("head=struct.pack('<68I',*hh)", "head=struct.pack('<68I',*hh)+head[272:]")
s=s.replace('conn.sendall(head+body)', '''if self.corrupt_identity and q[1]==1 and not self.injected:
                        self.injected=True;index={'frame':6,'product':41}[self.corrupt_identity];hh=list(h);hh[index]^=1
                        self.identity_proof=dict(field=self.corrupt_identity,original=h[index],damaged=hh[index])
                        head=struct.pack('<68I',*hh)+head[272:]
                    conn.sendall(head+body)''')
s=s.replace("kwargs.get('corrupt_rle'))", "kwargs.get('corrupt_rle') or kwargs.get('corrupt_identity'))")
s=s.replace("assert rows[0]['pixel_crc_verified'];", "assert rows[0]['pixel_crc_verified'] and rows[0]['header_crc_verified'];")
s=s.replace('corruption_proof=proxy.corruption_proof,', 'corruption_proof=proxy.corruption_proof,identity_proof=proxy.identity_proof,')
s=s.replace("results.append(case('bounded_30s_outage',outage=60))",'''for field in ('frame','product'):
            results.append(case('corrupt_'+field,corrupt_identity=field))
            bridge=EthernetBridge('169.254.200.10');f,im,mask=bridge.capture(89)
            original=results[-1]['frames'][0]
            assert f['event_id']==original['event'] and f['frame_id']==original['frame'] and f['product_id']==original['desc'][37]
            assert f['pixel_crc_verified'] and f['header_crc_verified'];bridge.ack(f);bridge.close();time.sleep(.2)
        results.append(case('bounded_30s_outage',outage=60))''')
s=s.replace('tests=7','tests=9')
(R/'scripts/board_v112_recovery.py').write_text(s)
s=(R/'scripts/board_v111_station.py').read_text().replace("all(e['pixel_crc_verified'] for e in events)","all(e['pixel_crc_verified'] and e['header_crc_verified'] for e in events)")
(R/'scripts/board_v112_station.py').write_text(s)
(R/'scripts/audit_v112_station.py').write_text((R/'scripts/audit_v111_station.py').read_text())
s=(R/'scripts/board_v111_background.py').read_text().replace('0x10b00','0x10c00').replace("all(e['pixel_crc_verified'] for e in records)","all(e['pixel_crc_verified'] and e['header_crc_verified'] for e in records)")
(R/'scripts/board_v112_background.py').write_text(s)
s=(R/'scripts/switch_from_v110.ps1').read_text().replace('pynq_z2_tile_v1_10','pynq_z2_tile_v1_11').replace('V1.10','V1.11')
(R/'scripts/switch_from_v111.ps1').write_text(s)
print('V1.12 actual-board tests prepared: header framing, frame/product corruption and no wrong ACK')
