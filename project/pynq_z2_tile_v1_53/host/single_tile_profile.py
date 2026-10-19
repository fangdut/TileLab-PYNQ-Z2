"""Single-fixture contract and evidence checks; no image inference here."""
from pathlib import Path
import hashlib,json
def load(root):
    root=Path(root);p=json.loads((root/'config/single_tile.json').read_text(encoding='utf-8'));canonical={k:v for k,v in p.items() if k not in ('profile_id','profile_sha256')};digest=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if p.get('profile_sha256')!=digest or p.get('profile_id')!=int(digest[:8],16):raise ValueError('Single-tile profile fingerprint mismatch')
    if p['frame']!={'width':1280,'height':720,'fps':60}:raise ValueError('Single-tile input must be720p60')
    for key in ['tile_rect','inspection_roi']:
        a=p[key]
        if len(a)!=4 or any(type(x) is not int for x in a) or not(16<=a[0]<a[2]<1264 and 16<=a[1]<a[3]<704):raise ValueError('Invalid single-tile rectangle')
    if p['inspection_roi']!=p['tile_rect']:raise ValueError('This release inspects the complete declared tile rectangle; no hidden erosion')
    if p['tile_rect']!=[390,110,889,609] or any(p[k]!=v for k,v in dict(high_q16=32768,gate_q16=-393216,support=5,min_trusted=16,evidence_shift=2).items()):raise ValueError('Unsupported fixed ROI or classifier operating point')
    if p['threshold']!=90 or p['passes']!=4 or p['firmware_version']!=0x13200 or p['model_id']!=0xd06b3b9b or not all(p[k] is True for k in ['enhance','wide_weak','ridge','pixel_boost']) or p['low_gate'] is not False:raise ValueError('Unsupported fixed detector contract')
    if hashlib.sha256((root/'models/v159_integer_model.json').read_bytes()).hexdigest()!=p['model_sha256']:raise ValueError('Frozen integer model mismatch')
    return p
def roi_words(p):
    x0,y0,x1,y1=p['inspection_roi'];return x0|(y0<<16),x1|(y1<<16)
def validate_wire_contract(p,d,m):
    lo,hi=roi_words(p)
    if len(d)!=40 or len(m)!=24 or m[0]!=0x54494c33 or m[1]!=p['firmware_version'] or not m[2]:raise ValueError('Matching single-tile firmware0x13200 is required')
    if d[:7]!=[p['profile_id'],lo,hi,p['model_id'],500,p['firmware_version'],1]:raise ValueError('Board single-tile profile/ROI/model mismatch')
    return dict(profile_id=p['profile_id'],profile_sha256=p['profile_sha256'],roi=p['inspection_roi'],model_id=p['model_id'],firmware_version=m[1],boot_id=m[2],verified=True)
def validate_frame(p,frame,mask):
    cfg=frame.get('config_word');expected=0x7bf30007|(p['threshold']<<8)
    if frame.get('firmware_version')!=p['firmware_version'] or type(cfg) is not int or (cfg&0x7fffffff)!=expected:raise ValueError('Captured frame is outside the fixed single-tile detector mode')
    if mask.shape!=(720,1280):raise ValueError('Unexpected mask shape')
    x0,y0,x1,y1=p['inspection_roi']
    if mask[:y0].any() or mask[y1+1:].any() or mask[y0:y1+1,:x0].any() or mask[y0:y1+1,x1+1:].any():raise ValueError('PL mask outside declared ROI; evidence rejected, never silently cropped')
    for box in frame['boxes']:
        if not(x0<=box[0]<=box[2]<=x1 and y0<=box[1]<=box[3]<=y1):raise ValueError('PL region extends outside single-tile ROI')
    frame.update(single_tile_profile_id=p['profile_id'],single_tile_profile_sha256=p['profile_sha256'],inspection_roi=list(p['inspection_roi']),inspection_scope='SINGLE_CALIBRATED_TEXTURED_TILE',decision='crack_candidate' if frame['alarm'] else 'no_crack_candidate_in_declared_roi')
    return frame
