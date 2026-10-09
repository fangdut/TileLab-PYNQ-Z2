# 素材来源与生成记录

本文件记录早期合成素材。当前目录同时包含真实 MVTec 照片回放和 MCS2 外部照片；来源与许可见 DATA_SOURCES.md。回放运动由程序生成，不是工厂实拍流水线。

程序生成：scripts/generate_tile_data.py，随机种子 2026092200 加样本编号。96 张 1280×720 图片及其裂痕真值掩码。它们采用相同的场景生成器，不代表独立工厂分布。

图像生成：使用内置 image_gen 工具，未使用 CLI/API fallback。
文件：ai_tile_crack_SYNTHETIC.png。原始工具输出尺寸为 1672×940；视频编码时缩放为 1280×720。
该图未经像素级真值标注，不参与 reports/synthetic_metrics.json 的指标计算。

完整提示词：

Use case: scientific-educational, photorealistic material inspection test image. Produce one 1280x720 landscape image suitable for a laboratory FPGA HDMI input demonstration. Orthographic overhead view of one large light ivory matte ceramic tile filling almost all the frame with a thin dark conveyor border. Realistic very subtle fine ceramic grain, even diffuse industrial illumination, low texture. In the tile's right half a clearly visible naturally branching dark hairline surface crack, including a main diagonal winding fracture and two short branches; left half is intact normal ceramic. Crack must be dark graphite gray against light tile, physically plausible with irregular width. No red marks, no bounding boxes, no labels, no rulers, no captions, no logos, no hands, no camera UI. This is SYNTHETIC demo input and not a real inspection result.

三段视频由 FFmpeg 编码为 H.264 1280×720 60fps：静止程序样本 12 秒、AI 外观照片 8 秒、移动挑战 10 秒。编码和电脑显示可能改变像素值，因此视频用于板上流程测试；RTL 精确像素比较使用未压缩 MEM 数据。
