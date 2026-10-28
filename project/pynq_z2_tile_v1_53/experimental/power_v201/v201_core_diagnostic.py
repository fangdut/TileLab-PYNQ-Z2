from pathlib import Path
import sys,json,serial,threading,time,argparse
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path('D:/Vivado/TileLab_RealPhotos_20261020/v201_core200_01'));p.add_argument('--frames',type=int,default=200);p.add_argument('--clock',type=int,default=100);a=p.parse_args()
P=Path('D:/Vivado/TileLab_SingleTile_V164_20261019/project/pynq_z2_tile_v1_53');W=Path('D:/Vivado/TileLab_RealPhotos_20261020');out=a.out;out.mkdir(exist_ok=False)
sys.path.insert(0,str(P/'tools/fpga_texture_v170'));from board_client import Board
catalog=json.loads((W/'v200_catalog01/catalog.json').read_text());item=next(r for r in catalog if r['id']=='6621d769324f6e05d5838380');image=(W/'v200_catalog01'/item['file']).resolve()
stop=threading.Event();port=serial.Serial('COM20',115200,timeout=.2)
def monitor():
    with (out/'uart.bin').open('ab') as f:
        while not stop.is_set():
            b=port.read(4096)
            if b:f.write(b);f.flush()
t=threading.Thread(target=monitor,daemon=True);t.start()
try:
    board=Board(timeout=60);model=board.upload(W/'v200_profiles03/texture');r=board.infer(image,out/'seed',model)
    (out/'plan.json').write_text(json.dumps(dict(scope='CONTINUOUS_FIXED_FRAME_PL_ONLY_DIAGNOSTIC_NOT_VIDEO_FPS',frames=a.frames,runtime_divider_clock_mhz=a.clock,boot_identity=r['boot_identity'],model_sha256=model['sha256'])))
    board.auto_benchmark(a.frames,model,r,out/'summary.json')
finally:
    stop.set();t.join(2);port.close()
