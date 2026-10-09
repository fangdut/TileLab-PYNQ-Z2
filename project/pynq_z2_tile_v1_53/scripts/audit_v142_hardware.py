"""Post-implementation audit; run after the V1.42 build and both Tcl audits.

Reads produced reports/BIT/XSA/DCP, then writes reports/v142/hardware_audit.json.
No Vivado, programming, transport, or physical-board operation is launched here.
"""
from pathlib import Path
import hashlib
import json
import re
import zipfile

R = Path(__file__).resolve().parents[1]
W = R / (R.name + '.sdk')
O = R / 'reports/v142'
BASELINE_RESOURCES = {'Slice LUTs': 17221.0, 'Slice Registers': 28931.0,
                      'Block RAM Tile': 67.0, 'DSPs': 2.0}
BASELINE_UTIL_SHA = '7e0e5a9a265ed30f07ff880b5113c1deee7e3d5f870c70ac2ac91810aa6d4eee'
BASELINE_BIT_SHA = '0f9d52581593ee3c18149810237b09760cfc6a77dfd3241dd33b0465c4fd567e'
MAX_DELAY_REQUIREMENTS = {'fifo_read': 10.000, 'fifo_write': 13.468,
                          'config': 53.872, 'brightness': 10.000,
                          'candidates': 10.000, 'regions': 10.000,
                          'descriptor': 10.000, 'frame_count': 40.000}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_current_report(name):
    content = (R / 'reports' / name).read_text(encoding='utf-8')
    normalized = content.replace('\\', '/')
    require(f'{R.name}/reports/{name}' in normalized,
            f'{name} was not generated for the current project path')
    require(re.search(r'\|\s*Design State\s*:\s*(?:Fully )?Routed\b', content),
            f'{name} is not a routed-design report')
    return content


def resource_values(content):
    values = {}
    for name in BASELINE_RESOURCES:
        match = re.search(r'\|\s*' + re.escape(name) + r'\s*\|\s*([\d,.]+)\s*\|', content)
        require(match is not None, 'Missing resource row: ' + name)
        values[name] = float(match[1].replace(',', ''))
    return values


def slack_values(content):
    return [float(value) for value in re.findall(r'Slack \(MET\)\s*:\s*([\d.]+)ns', content)]


def main():
    require(R.name == 'pynq_z2_tile_v1_53', 'This audit is bound to the V1.42 project')
    O.mkdir(parents=True, exist_ok=True)
    (O / 'hardware_audit.json').write_text(
        json.dumps(dict(passed=False, revision='V1.42', status='audit_in_progress')),
        encoding='utf-8')
    timing = read_current_report('timing_summary.rpt')
    require('All user specified timing constraints are met' in timing, 'Timing failed')
    table = timing[timing.index('| Design Timing Summary'):].splitlines()
    header = next(index for index, line in enumerate(table) if 'WNS(ns)' in line)
    row = table[header + 2].split()
    require(len(row) >= 12, 'Timing summary table is incomplete')
    wns, whs, wpws = map(float, (row[0], row[4], row[8]))
    require(min(wns, whs, wpws) >= 0, 'Negative setup/hold/pulse-width slack')
    require(all(float(row[index]) == 0 for index in (1, 2, 5, 6, 9, 10)),
            'Nonzero setup/hold/pulse-width violation totals')
    for category in ('no_clock', 'unconstrained_internal_endpoints', 'multiple_clock',
                     'generated_clocks', 'loops', 'latch_loops'):
        match = re.search(r'checking ' + category + r' \((\d+)\)', timing)
        require(match is not None and int(match[1]) == 0,
                'Missing/nonzero timing check: ' + category)

    used = resource_values(read_current_report('utilization.rpt'))
    drc = read_current_report('drc.rpt')
    require(not re.search(r'\|\s*(?:Error|Critical Warning)\s*\|', drc),
            'DRC error or critical warning')
    skew = read_current_report('bus_skew.rpt')
    skew_slacks = slack_values(skew)
    require(len(skew_slacks) == 8 and 'VIOLATED' not in skew,
            'Expected eight passing bus-skew constraints')

    cdc = read_current_report('cdc.rpt')
    cdc_rows = [line.split() for line in cdc.splitlines()
                if line.startswith(('Critical ', 'Info ', 'Warning '))]
    require(cdc_rows, 'No CDC result rows found')
    counts = [list(map(int, row[-5:])) for row in cdc_rows]
    require(all(endpoints == safe + unsafe + unknown
                for endpoints, safe, unsafe, unknown, _ in counts), 'Malformed CDC totals')
    unsafe = sum(row[2] for row in counts)
    unknown = sum(row[3] for row in counts)
    missing_async = sum(row[4] for row in counts)
    require(unsafe == unknown == missing_async == 0,
            'Unsafe/unknown CDC endpoints or missing ASYNC_REG remain')
    details = read_current_report('cdc_details.rpt')
    require('CDC-11' not in details and 'Critical' not in details and 'Unknown' not in details,
            'CDC details contain a critical/unknown topology')
    methodology = read_current_report('methodology.rpt')
    require('TIMING-24' not in methodology, 'Overridden timing exception warning returned')

    netlist = (O / 'reset_netlist.txt').read_text()
    for marker in ('PIXEL_REGISTERS 2', 'REFERENCE_REGISTERS 2', 'OLD_DUPLICATE_BRIDGES 0'):
        require(marker in netlist, 'Shared reset topology mismatch: ' + marker)
    reset_timing = {}
    for domain in ('reference', 'pixel'):
        for check in ('recovery', 'removal'):
            name = f'{domain}_reset_{check}.rpt'
            content = (O / name).read_text()
            values = slack_values(content)
            types = re.findall(r'Path Type:\s+(\w+)', content)
            require('VIOLATED' not in content and len(values) == 3
                    and types == [check.title()] * 3, 'Reset timing mismatch: ' + name)
            reset_timing[name] = dict(sha256=sha(O / name), paths=len(values),
                                     minimum_slack_ns=min(values), path_types=types)

    interaction = (O / 'implemented_clock_interaction.rpt').read_text()
    for a, b, kind in (('PixelClk_int', 'clk_fpga_0', 'Max Delay Datapath Only'),
                       ('clk_fpga_0', 'PixelClk_int', 'Max Delay Datapath Only'),
                       ('PixelClk_int', 'clk_fpga_1', 'False Path'),
                       ('clk_fpga_1', 'PixelClk_int', 'False Path')):
        require(any(line.split()[:2] == [a, b] and kind in line
                    for line in interaction.splitlines()), 'Clock interaction mismatch: ' + a + ' -> ' + b)
    clocks = (O / 'implemented_clocks.rpt').read_text()
    for name, period in {'clk_fpga_0': 10.0, 'clk_fpga_1': 5.0,
                         'hdmi_rx_clk': 13.468, 'PixelClk_int': 13.468}.items():
        match = re.search(r'^' + re.escape(name) + r'\s+([\d.]+)\s+', clocks, re.M)
        require(match is not None and abs(float(match[1]) - period) <= .001,
                'Implemented clock missing/wrong: ' + name)
    ignored = (O / 'implemented_ignored_exceptions.rpt').read_text()
    require('Max Delay' not in ignored, 'A max-delay constraint was ignored')
    constraints = json.loads((O / 'max_delay_audit.json').read_text())
    groups = constraints.get('groups', [])
    require(constraints.get('passed') is True and len(groups) == len(MAX_DELAY_REQUIREMENTS)
            and {group['name'] for group in groups} == set(MAX_DELAY_REQUIREMENTS),
            'Incomplete max-delay audit groups')
    for group in groups:
        require(group['timed_endpoints'] > 0
                and group['timed_endpoints'] + group['constant_endpoints'] == group['destination_cells']
                and group['minimum_slack_ns'] >= 0
                and abs(group['requirement_ns'] - MAX_DELAY_REQUIREMENTS[group['name']]) <= .001,
                'Max-delay endpoint/slack/requirement mismatch: ' + group['name'])

    bit_hash = sha(W / 'system.bit')
    require(bit_hash == sha(R / (R.name + '.runs') / 'impl_1/system_wrapper.bit'),
            'Workspace BIT differs from implemented BIT')
    require(bit_hash != BASELINE_BIT_SHA, 'V1.42 still contains the inherited V1.41 BIT')
    with zipfile.ZipFile(W / 'system.xsa') as archive:
        bits = [name for name in archive.namelist() if name.endswith('.bit')]
        require(len(bits) == 1 and hashlib.sha256(archive.read(bits[0])).hexdigest() == bit_hash,
                'XSA embedded BIT differs from current BIT')
    gate_validation = json.loads((O / 'product_gate_validation/summary.json').read_text(encoding='utf-8-sig'))
    require(gate_validation.get('passed') is True, 'Product gate module validation did not pass')
    source_hashes = {name: sha(R / name) for name in ('rtl/frame_capture_sg.v', 'rtl/product_tracker.v')}
    require(all(gate_validation['source_sha256'].get(name) == value
                for name, value in source_hashes.items()), 'Module validation does not match current RTL')

    names = ('timing_summary.rpt', 'utilization.rpt', 'drc.rpt', 'cdc.rpt',
             'cdc_details.rpt', 'methodology.rpt', 'bus_skew.rpt')
    clock_names = ('implemented_clocks.rpt', 'implemented_clock_interaction.rpt',
                   'implemented_applied.xdc', 'implemented_ignored_exceptions.rpt')
    result = dict(
        passed=True, revision='V1.42', new_hardware=True,
        scope=('Fresh routed V1.42 invalid-observation product tracker; unchanged descriptor ABI 0x54465337; '
               'timing, shared-reset topology, recovery/removal, CDC constraints and BIT/XSA equality. '
               'This audit does not validate defect accuracy, physical HDMI behavior, firmware execution, '
               'hotplug, or absence of analog metastability.'),
        wns_ns=wns, whs_ns=whs, wpws_ns=wpws, resources=used,
        baseline_revision='V1.41', baseline_resources=BASELINE_RESOURCES,
        baseline_resource_evidence=dict(report='pynq_z2_tile_v1_41/reports/utilization.rpt',
                                        sha256=BASELINE_UTIL_SHA,
                                        note='Historical routed V1.41 baseline, not a V1.42 measurement'),
        resource_delta_vs_v141={name: used[name] - value for name, value in BASELINE_RESOURCES.items()},
        bus_skew_constraints_met=len(skew_slacks), minimum_bus_skew_slack_ns=min(skew_slacks),
        cdc_rows=len(cdc_rows), cdc_unsafe_endpoints=unsafe, cdc_unknown_endpoints=unknown,
        cdc_missing_async_reg_endpoints=missing_async,
        reports_sha256={name: sha(R / 'reports' / name) for name in names},
        artifacts_sha256={name: sha(W / name) for name in ('system.bit', 'system.xsa', 'system.ltx')},
        routed_checkpoint_sha256=sha(R / (R.name + '.runs') / 'impl_1/system_wrapper_routed.dcp'),
        source_sha256=source_hashes, product_gate_validation_sha256=sha(O / 'product_gate_validation/summary.json'),
        pixel_mhz=74.25, axi_mhz=100, reference_mhz=200,
        reset_recovery_removal_reports=reset_timing, reset_netlist_sha256=sha(O / 'reset_netlist.txt'),
        max_delay_audit=constraints, implemented_clock_evidence_sha256={name: sha(O / name) for name in clock_names})
    O.mkdir(parents=True, exist_ok=True)
    (O / 'hardware_audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
