# SPDX-License-Identifier: MIT
"""PC station upgrade; uses original frozen backend and the same board owner."""
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import argparse,importlib.util,json,sys

class LocalHTTPServer(ThreadingHTTPServer):
    request_queue_size=128
    daemon_threads=True


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--station-source',type=Path,required=True)
    p.add_argument('--resume',type=Path)
    a=p.parse_args();sys.path.insert(0,str(a.station_source.resolve()))
    spec=importlib.util.spec_from_file_location('v202_server',a.station_source/'server.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    from profiles_backend import ProfilesBackend
    # Explicit local module path, independent of the legacy import directory.
    policy_spec=importlib.util.spec_from_file_location('policy_extension',Path(__file__).with_name('policy_station.py'))
    policy=importlib.util.module_from_spec(policy_spec);policy_spec.loader.exec_module(policy)
    cfg=json.loads(a.config.read_text(encoding='utf8'))
    resolve=lambda key:(a.config.parent/cfg[key]).resolve()
    server=LocalHTTPServer(('127.0.0.1',cfg.get('port',8793)),BaseHTTPRequestHandler)
    rows=json.loads(resolve('catalog').read_text(encoding='utf8'))
    for row in rows:row['file']=str((resolve('catalog').parent/row['file']).resolve())
    backend=ProfilesBackend(cfg.get('board','192.168.33.10'),resolve('profiles_registry'),resolve('program'),resolve('hardware'))
    checkpoint=json.loads(a.resume.read_text(encoding='utf-8-sig')) if a.resume else None
    station=policy.PolicyStation(backend,rows,resolve('store'),checkpoint)
    station.connection=backend.check()
    server.RequestHandlerClass=legacy.handler(station)
    print(json.dumps(dict(policy=station.state()['automatic_pass_policy'],session=station.session)),flush=True)
    server.serve_forever(poll_interval=.2)


if __name__=='__main__':main()
