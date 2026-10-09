"""Bounded normal-link validation of default request deadlines on real hardware.

Uses only the already-running V1.40 Station, which owns the board connection.
Twelve manual archives are intentional. No fault injection or hardware changes.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import time
import traceback
from board_v140_diagnostics import (Client, ROOT, FIRMWARE, ERRORS, sha, write,
    wait_for, paused, adopted, healthy, checked_pixels, save_evidence, programmed_proof)

PROFILES = {
    'default': dict(recipe='mvtec_hdmi_weak_v124', threshold=90, passes=4, low_gate=False),
    'low_gate': dict(recipe='synthetic_dark_v137', threshold=36, passes=2, low_gate=True),
}
MODES = {'raw': {'RAW32'}, 'rle': {'WORD_RLE', 'RAW32'}, 'packed': {'WORD_RLE', 'BGR24_MASK1', 'RAW32'}}


def sources():
    names = ['scripts/board_v140_deadline.py', 'scripts/board_v140_diagnostics.py',
             'host/workstation.py', 'host/tcp_transport.py', 'host/hdmi_display.ps1',
             'host/recipes.py', 'host/recipes.json', 'host/word_rle.py', 'host/packed_pixels.py',
             'data/conveyor/station_0.png', 'data/conveyor/station_6.png', 'data/conveyor/transport_noise.png']
    return {name: sha(ROOT / name) for name in names}


def profile_matches(frame, profile):
    return (frame and frame.get('applied_threshold') == profile['threshold']
            and frame.get('weak_passes') == profile['passes']
            and frame.get('low_gate_enabled') is profile['low_gate'])


def main():
    output = ROOT / 'reports/v140/deadline_board'
    run = output / ('run_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    run.mkdir(parents=True)
    client = Client('http://127.0.0.1:8770')
    result = dict(passed=False, revision='V1.40', started_at=datetime.now(timezone.utc).isoformat(),
        run_directory=str(run), source_sha256=sources(), startup_programmed_proof=programmed_proof(),
        profiles=PROFILES, cases=[], controls=[], cleanup_errors=[],
        scope='Real board normal-link integration, default 3s control / 8s capture budgets; Station alone owns the socket',
        limitations=['Two synthetic recipes with compressible station_0 input; no independent detector accuracy measurement.',
            'PACK25 is optional. Actual codecs are reported; selecting packed capability does not prove PACK25 payload coverage.',
            'Full-range transport_noise caused board invalid frames even without host image requests. It failed separate stress validation and remains unresolved.',
            'The first image follows an explicit disconnect; health or capability status may open the connection before the image command. Retry metadata is checked.',
            'Normal-link latency margins do not prove worst-case network behavior or hard real-time scheduling.',
            'Partial-transfer failure handling is tested separately with controlled clocks/local sockets.',
            'No new external-monitor human visual confirmation or physical disconnection test.'])
    boot = result['startup_programmed_proof']['record']['boot_id']
    result.update(boot_id=boot, firmware_version=FIRMWARE)
    write(run / 'provenance.json', {k: result[k] for k in ('source_sha256', 'startup_programmed_proof')})
    touched = False
    try:
        initial = client.state()
        assert initial['board_stats']['boot_id'] == boot and initial['board_stats']['version'] == FIRMWARE
        touched = True
        paused(client)
        client.ok('storage', mode='preview', max_archive_mib=1024)
        client.ok('preview_rate', value=2)
        client.ok('freeze_preview', enabled=False)
        old_ids = {r['id'] for r in client.records()}
        for name, profile in PROFILES.items():
            paused(client)
            request = client.ok('display', value='station_6')['response']['request_id']
            client.ok('recipe', value=profile['recipe'])
            previous = client.state()['captures']
            client.ok('start')
            warm = wait_for(client, lambda s: s['captures'] > previous
                and adopted(s, 'station_6', request) and profile_matches(s.get('frame'), profile)
                and s['board_stats']['current_product_id'] == 0 and s['board_stats']['depth'] == 0
                and not s['pending_operation'], seconds=15)
            if 'before' not in result:
                result['before'] = warm['board_stats']
            previous = warm['captures']
            request = client.ok('display', value='station_0')['response']['request_id']
            wait_for(client, lambda s: s['captures'] >= previous + 2 and adopted(s, 'station_0', request)
                and profile_matches(s.get('frame'), profile), seconds=15)
            paused(client)
            for mode, codecs in MODES.items():
                client.ok('wire_mode', value=mode)
                source = 'station_0'
                count = client.state()['captures']
                request = client.ok('display', value=source)['response']['request_id']
                client.ok('start')
                wait_for(client, lambda s: s['captures'] >= count + 2 and adopted(s, source, request)
                    and profile_matches(s.get('frame'), profile) and s['board_stats']['depth'] == 0
                    and not s['pending_operation'], seconds=15)
                paused(client)
                # Close before the first manual image. Station health preflight
                # may establish this fresh connection before the image command.
                client.ok('disconnect')
                for connection in ('fresh', 'reused'):
                    prior = client.state()
                    assert not prior['busy'] and not prior['pending_operation'] and not prior['pending_confirmation']
                    count = prior['captures']
                    ids = {r['id'] for r in client.records()}
                    client.ok('capture')
                    final = wait_for(client, lambda s: s['captures'] == count + 1 and not s['busy']
                        and not s['pending_operation'] and not s['pending_confirmation'], seconds=15)
                    healthy(final, boot)
                    rows = [r for r in client.records() if r['id'] not in ids]
                    assert len(rows) == 1 and rows[0]['reason'] == 'manual'
                    frame = rows[0]
                    assert profile_matches(frame, profile) and frame['recipe_id'] == profile['recipe']
                    assert frame['wire_codec'] in codecs, (mode, frame['wire_codec'])
                    assert frame['retry_count'] == 0, 'Unexpected retry on the normal-link margin test'
                    assert 0 <= frame['total_request_ms'] < 8000
                    original, mask = client.image(frame, archived=True), client.image(frame, True, True)
                    check = checked_pixels(frame, original, mask, boot, FIRMWARE)
                    evidence = save_evidence(run, name + '_' + mode + '_' + connection, frame, original, mask, check)
                    result['cases'].append(dict(profile=name, mode=mode, source=source, connection=connection,
                        capture_budget_seconds=8, capture_elapsed_ms=frame['total_request_ms'],
                        capture_margin_ms=8000-frame['total_request_ms'], evidence=evidence,
                        manual_saved_and_confirmation_completed=True, paused_after_capture=not final['enabled']))
                status = client.ok('status')
                assert status['response']['boot_id'] == boot and status['response']['error_status'] == 0
                assert status['milliseconds'] < 3000
                result['controls'].append(dict(profile=name, mode=mode, http_elapsed_ms=status['milliseconds'],
                    control_budget_seconds=3, scope='HTTP wall observation includes API overhead'))
        request = client.ok('display', value='station_6')['response']['request_id']
        client.ok('start')
        wait_for(client, lambda s: adopted(s, 'station_6', request) and s['board_stats']['depth'] == 0
            and s['board_stats']['current_product_id'] == 0 and not s['pending_operation'], seconds=15)
        paused(client)
        final = client.state()
        result['after'] = final['board_stats']
        result['error_deltas'] = {k: (result['after'][k]-result['before'][k]) & 0xffffffff for k in ERRORS}
        assert not any(result['error_deltas'].values())
        rows = [r for r in client.records() if r['id'] not in old_ids]
        assert len(rows) == 12 and {r['id'] for r in rows} == {c['evidence']['frame']['id'] for c in result['cases']}
        result.update(actual_wire_codecs=sorted({c['evidence']['frame']['wire_codec'] for c in result['cases']}),
            packed_codec_exercised=any(c['evidence']['frame']['wire_codec']=='BGR24_MASK1' for c in result['cases']),
            high_density_stress_passed=False, new_manual_archives=len(rows), final_control={k: final[k] for k in
            ('enabled', 'busy', 'manual_waiting', 'pending_operation', 'pending_confirmation')},
            sources_unchanged=sources()==result['source_sha256'],
            programmed_artifacts_unchanged=programmed_proof()==result['startup_programmed_proof'])
        assert result['sources_unchanged'] and result['programmed_artifacts_unchanged']
        result['passed'] = True
    except Exception:
        result['error'] = traceback.format_exc()
        raise
    finally:
        if touched:
            for fn in (lambda: paused(client), lambda: client.ok('storage', mode='preview', max_archive_mib=1024),
                       lambda: client.ok('display', value='station_6')):
                try:
                    fn()
                except Exception as error:
                    result['cleanup_errors'].append(str(error))
            if result['cleanup_errors']:
                result['passed'] = False
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        write(run/'summary.json', result)
        write(output/'summary.json', result)
    print(json.dumps(dict(passed=result['passed'], cases=len(result['cases']), summary=str(output/'summary.json'))))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
