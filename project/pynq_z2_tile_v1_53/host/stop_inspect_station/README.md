# Stop, inspect, confirm station

This is the operator workstation for the accepted 100 MHz V179 full-PL detector. The first milestone is a usable stop/inspect/disposition cycle; sustained 10 FPS is deferred. Detection remains entirely on the PYNQ-Z2 PL. The PC decodes original image files, sends bytes, manages the operator workflow, displays the returned mask and records evidence. The ARM firmware transports data and starts the detector for each requested inspection. This workstation mode does not halt the ARM; the separately preserved continuous HDMI test does.

## Current demonstration

Start the local service, open http://127.0.0.1:8793/ and:

1. Select a real photograph or import an original PNG/JPEG with both dimensions <=1024. The station does not resize or edit the inspection input.
2. Load and freeze the current input. Confirm that the input is held fixed.
3. Start FPGA inspection. A model-bound, previously verified development example enters `GOOD_HOLD` or `DEFECT_HOLD`. A local import or missing/mismatched qualification enters `REVIEW_HOLD`, retaining the raw FPGA output as a reference result. Neither releases automatically.
4. Check the operator confirmation box. Only a qualified good result can be confirmed for release. A qualified defect can be confirmed as segregated. An unvalidated input can only be confirmed as removed (`REMOVED`); it cannot become a good-release command even when the raw FPGA alarm is0.
5. On communication, identity, sequence or source-integrity failure, the state becomes `FAULT`, the prior result is cleared and release is blocked. Fault reset discards the old cycle; the operator must remove the item and start a new cycle.

The current system has no physical conveyor, stop sensor, brake, motor or reject actuator. Load/stop/release/segregate are a truthful photo-input workflow and logical command record, not a verified physical handling cycle. A real installation must add position/standstill feedback and actuator acknowledgment before claiming physical stop or release. It must keep fault handling independent of this demonstration UI.

The12 bundled real photos are MVTec AD tile samples already used during development. Their qualification metadata binds this development evidence to the exact model SHA256; it is not a claim that a material family is factory-qualified. Their labels exist only in `data/stop_inspect_demo/expected_offline_only.json` for the separate acceptance evaluator. The live detector never reads that file. Local imports do not inherit qualification by looking similar or matching an example's bytes. Browser requests cannot upgrade validation scope. Do not claim arbitrary painted/mixed-material accuracy or precise crack outlines: the current mask is coarse.

V194 froze a new external40-photo original-image test from a separately authored ceramic dataset. Review showed roof tiles, so it is recorded as cross-material stress, not floor-tile acceptance. The unchanged FPGA model alarmed on all20 source-labeled good and all20 defective inputs. This failure remains visible; the workflow guard does not change its predictions, threshold or reported false-positive rate. Per-pattern reference calibration and independent target-domain validation remain outstanding. See `reports/v194/` for the full protocol and results.

## Start on this computer

The running configuration is saved outside the source tree at `D:/Vivado/TileLab_RealPhotos_20261020/v193_station02_config.json`. Run:

```powershell
& 'D:/Vivado/TileLab_Runtime_V168/Scripts/python.exe' -X utf8 server.py --config 'D:/Vivado/TileLab_RealPhotos_20261020/v193_station02_config.json'
```

Only one station should control a board. The fixed port refuses a duplicate service. Result sequence checks catch another client running inference between inspections. The service binds localhost and rejects cross-origin actions. The current program identity must match the live boot; a power cycle requires redeployment and a fresh identity file. A saved good result is never restored after a server restart.

## Portable development package

The package contains matching BIT/XSA/ELF/model, original detector source and build scripts, the preserved HDMI pipeline and evidence, this workstation, 12 unedited photographs and the interlock tests. `deploy_workstation.py` performs the existing guarded volatile download, uploads the sealed model and writes a new runtime config. No Flash is written. Prerequisites: Windows, Python3.12 with NumPy/Pillow, Vivado/Vitis2025.2 and installed board USB drivers, reachable board Ethernet192.168.33.10. The existing programmer defaults to `D:/2025.2/Vitis/bin/xsdb.bat` (set `TILELAB_XSDB` for another install location).

```powershell
python project/host/stop_inspect_station/deploy_workstation.py --bundle . --out runtime/run01
python project/host/stop_inspect_station/server.py --config runtime/run01/station_config.json
```

Use a fresh output directory. Close old station/source processes before deployment. Do not run HDMI capture and TCP file inspection simultaneously. The accepted hardware retains both paths; the new workstation currently uses the original-photo TCP path. Historical 8.17 HDMI FPS is not the throughput of operator-confirmed cycles.

## Verification

```powershell
python test_controller.py
python accept_station.py --expected ../../data/stop_inspect_demo/expected_offline_only.json --store <runtime-store> --out <fresh-output>
```

`test_controller.py` uses a clearly labeled fake backend for13 interlocks/fault tests; it is not board evidence. `accept_station.py` exercises the physical board through the service, checks each real-photo result and tests prohibited actions. The acceptance requires a fresh `READY` session. Operator confirmation is supplied by this test harness for workflow verification only, not as a human physical handling claim. Edge UI checks separately exercise actual raw-good output from an unvalidated local import, refusal of release and browser scope upgrade, removal without counting it as a confirmed defect, and continued operation of the qualified demonstration examples.

## Preserved hardware pipeline

HDMI input -> PL color correction/ROI -> CDC -> DDR frame slots -> autonomous PL scheduler -> full integer detector -> validated result latch/display. V179 implements capture/inference overlap. Its source, timing, resources, 117-photo output comparisons and ARM-halted continuous-HDMI evidence remain in the verified baseline. This iteration adds the operator workflow without rebuilding that hardware.

## Remaining release work

1. Independent real-photo validation and per-pattern scope documentation; do not tune on the final blind evaluation images.
2. Longer workflow endurance and fault recovery evaluation under the final cabling/power configuration.
3. Update the technical report and demonstration video around this stopped-input workflow; include model licensing, algorithm prior art, hardware resource/timing evidence, failure records and reusable skills.
4. Obtain real whole-system/board photographs and the participant-signed official authorization. The development package is not proof of website submission.

Original station code: MIT. MVTec photos/derived models/evidence: CC BY-NC-SA4.0. Vendor and upstream code retains its original terms.

## Rebuild a runtime bundle from GitHub source

From repository root run python project/pynq_z2_tile_v1_53/tools/package_stop_station.py --out runtime/stop_inspect_bundle --zip runtime/stop_inspect_bundle.zip. This uses the already verified V179 archive committed in deliverables and the current station sources; it requires no new EDA implementation. Generated ZIP timestamps may differ from the locally handed-over archive; manifest file hashes establish contents.
