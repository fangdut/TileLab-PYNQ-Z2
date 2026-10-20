from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from program_single_tile import verify_programming_log,SUCCESS

class ProgrammingLogTests(unittest.TestCase):
    def test_exit_zero_transcript_cannot_hide_tcl_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'xsdb.log'
            for text in ('','PROGRAMMING_FAILED: Memory map unavailable\n',SUCCESS+'\nPROGRAMMING_FAILED: later failure\n',SUCCESS+'\n'+SUCCESS+'\n'):
                p.write_text(text)
                with self.assertRaises(RuntimeError):verify_programming_log(p)
            p.write_text('INFO: hardware initialized\n'+SUCCESS+'\n');verify_programming_log(p)

if __name__=='__main__':unittest.main()
