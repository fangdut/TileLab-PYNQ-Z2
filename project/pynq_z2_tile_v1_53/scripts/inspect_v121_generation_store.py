"""Independent process reload of bounded board-test archives; no board access."""
from pathlib import Path
import sys,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'host'))
from workstation import Records
s=Records(Path(sys.argv[1]))
try:
 result=dict(records=s.all(),pending=s.confirmations.pending(),history=s.confirmations.history())
 Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(dict(records=len(result['records']),pending=result['pending']['frame'] if result['pending'] else None,history=len(result['history']))))
finally:s.db.close()
