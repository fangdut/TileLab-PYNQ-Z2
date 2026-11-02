"""Use packaged render_docx.py with the already documented Windows Word fallback.

Only DOCX-to-PDF conversion is replaced because this Windows runtime has no
bundled LibreOffice. The DOCX is opened read-only with macros disabled. Native
Word does not save the document. Packaged rasterize/main remain in use.
"""
from pathlib import Path
import importlib.util,subprocess,sys
skill=Path('C:/Users/Fang/.codex/plugins/cache/openai-primary-runtime/documents/26.1025.11240/skills/documents');work=Path('D:/Vivado/TileLab_RealPhotos_20261020/v202_report01')
spec=importlib.util.spec_from_file_location('packaged_render_docx',skill/'render_docx.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
def native(doc_path,user_profile,convert_tmp_dir,stem,verbose):
    pdf=Path(convert_tmp_dir)/(stem+'.pdf');command=['C:/Users/Fang/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(work/'render_word_readonly.ps1'),'-InputDocx',doc_path,'-OutputPdf',str(pdf)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=100);log=result.stdout+result.stderr;(work/'native_word_render.log').write_text(log,encoding='utf8')
    if result.returncode or not pdf.is_file():return '',log
    return str(pdf),log
renderer.convert_to_pdf=native
sys.argv=['render_docx.py',str(work/'TileLab_比赛技术报告_V202.docx'),'--output_dir',str(work/'render'),'--dpi','130','--emit_pdf']
renderer.main()
