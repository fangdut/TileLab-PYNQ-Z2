# Reusable verification and deployment lessons

The milestone focuses on a measured, inspectable FPGA work product. These techniques can be adapted to other FPGA applications; they are not detection algorithms or a promise of cross-board validation.

## Verify a complete artifact bundle

Run `python skill/verify_files.py <package-root>`. The root `manifest.json` contains a `files` mapping from relative path to `bytes` and `sha256`. The script rejects missing/corrupted files and paths escaping the root. It uses only Python's standard library and contains no TileLab model, IP address or board-specific register. A team can use the same format for any BIT/XSA/ELF, simulation vectors or reports.

Validated here: full release-manifest verification; a deliberately modified fixture fails; an escaping fixture path fails. This checks file integrity against the manifest, not authorship or cryptographic trust in the manifest itself. It cannot substitute for timing, correct software/hardware pairing or numerical board tests.

## Bind an operator action to the current hardware result

Use session, revision, cycle and result identifiers. A fresh worker must return the current cycle's exact input hash, hardware boot identity and expected completion sequence. New sessions discard old good results. Confirmation rechecks the device identity and loaded model before disposition. Communication failures clear the result and hold the work item. See `host/stop_inspect_station/controller.py` and its concurrent/stale-result/disconnection tests. Adapt the wire protocol and physical interlocks to the target system; the current demo does not drive an actuator.

## Observe debug clocks on every new connection

In this project a newly spawned hw_server defaulted to15 MHz, although programming had previously selected1 MHz. A baseline run hit Invalid context while hardware completion counters continued increasing. Each video helper now explicitly selects and logs the debug clock. A subsequent complete117-photo HDMI run passed. This is evidence for controlling test conditions, not proof that every previous reset was caused by the debug clock. Device/cable frequency choices require independent validation.

## Bound the lifetime of a CAD process tree

`scripts/texture_v170/owned_process.py` terminates only the launched process tree on timeout. On Windows, killing the wrapper first can orphan a Vivado router: the HLS79 parent timed out while routing continued with severe congestion. Real process-tree tests verified that an owned child exits while an unrelated process survives. Adapt this helper to CAD automation; it does not make a congested design routable.
