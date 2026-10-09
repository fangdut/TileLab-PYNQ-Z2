from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];W=R/(R.name+'.sdk');O=R/'reports/v132'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
vendor=W/'hdmi_platform/ps7_cortexa9_0/standalone_a9/bsp/libsrc/lwip220/src/lwip-2.2.0'
driver=vendor/'contrib/ports/xilinx/netif/xemacpsif_dma.c';d=driver.read_text()
assert 'XEmacPs_BdSetAddressTx(txbd, (UINTPTR)q->payload)' in d and 'pbuf_ref(q)' in d
assert 'tx_pbufs_storage[index + bdindex] = (UINTPTR)q' in d
assert 'pbuf_free(p)' in d
network=W/'ethernet_sources/network.c';assert 'flags=TCP_WRITE_FLAG_COPY;' in network.read_text()
native=json.loads((O/'native_stream/result.json').read_text())
counter=json.loads((R/'reports/v132_nocopy_trial/native_stream/dma_counterexample.json').read_text())
assert native['passed'] and native['borrowed_payload_writes']==0 and native['copied_payload_writes']>1000 and native['gem_retained_reference_checks']>1000
assert native['source_sha256']['network.c']==sha(network) and counter['counterexample_reproduced']
result=dict(passed=True,vendor_driver=str(driver),vendor_driver_sha256=sha(driver),network_sha256=sha(network),
 finding='GEM TX descriptor points to pbuf payload and holds pbuf reference until TX completion; TCP abort is not proof of hardware release.',
 correction='All header and payload tcp_write calls copy bounded data into lwIP-owned pbuf storage. GEM reference retains that copied allocation independently of application scratch/DDR slot reuse.',
 counterexample=counter,gem_retained_reference_checks=native['gem_retained_reference_checks'],scope='Installed AMD driver source audit plus actual network.c native delayed-DMA-reference model. Does not claim forcing a physical GEM stall on the board.')
(O/'gem_ownership_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
