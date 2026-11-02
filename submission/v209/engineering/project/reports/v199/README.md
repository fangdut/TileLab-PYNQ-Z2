# V199 验证说明

本轮是既有稳定核心上的参照适用范围与传输优化。查看status.html和summary.json。默认检测模型及BIT不变。原比赛模板DOCX是上一版基线测量快照，本轮最新数字以此补充记录为准。

重建传输：先运行experimental/transport_v199/prepare_transport.py，再使用scripts/texture_v170/rebuild_transport.py，显式设置TILE_TEXTURE_TRANSPORT_SOURCE及已有匹配BSP、硬件、模型路径。所有下载只写易失配置，保留旧稳定包。
