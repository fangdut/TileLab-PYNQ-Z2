from pathlib import Path
R=Path(__file__).resolve().parents[1]
(R/'host/benchmark.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>TileLab V1.11 验收进行中</title><style>body{font:18px/1.8 system-ui,"Microsoft YaHei";max-width:850px;margin:70px auto;color:#173e47;background:#edf4f4}a{color:#087d80}</style><a href="/">返回工作台</a><h1>V1.11 正在验收</h1><p>92 项软件测试、CRC 仿真和实际固件槽所有权测试已通过。</p><p>硬件构建和实板测试尚未全部完成。最终报告只会在各项验收通过后发布，当前不把旧版测试数字作为本版结论。</p><p>已验证的 V1.10 工程及备份完整保留。</p></html>''',encoding='utf-8')
