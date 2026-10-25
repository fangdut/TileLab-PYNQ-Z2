"""Reproduce the frozen external roof-tile stress corpus. No model computation."""
from pathlib import Path
import argparse,hashlib,json,urllib.request
from concurrent.futures import ThreadPoolExecutor


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--plan',type=Path,default=Path(__file__).resolve().parents[1]/'reports/v194/source/plan.json')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    plan=json.loads(a.plan.read_text(encoding='utf8'))
    def fetch(row):
        name=row['filename']
        if Path(name).name!=name:raise ValueError('Unsafe source filename')
        with urllib.request.urlopen(urllib.request.Request(row['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=60) as response:
            raw=response.read()
        if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('Downloaded source hash differs: '+name)
        file=a.out/name;file.write_bytes(raw)
        return dict(id=row['id'],file=str(file.resolve()),sha256=row['sha256'],label=row['label'],
                    source_url=row['url'],original_unedited=True,benchmark_is_blind=False,
                    validation_scope='unvalidated')
    rows=list(ThreadPoolExecutor(max_workers=4).map(fetch,plan['selected_before_outputs']))
    (a.out/'catalog.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(dict(downloaded=len(rows),model_computation=False,qualification='UNVALIDATED_CROSS_MATERIAL_STRESS')))


if __name__=='__main__':main()
