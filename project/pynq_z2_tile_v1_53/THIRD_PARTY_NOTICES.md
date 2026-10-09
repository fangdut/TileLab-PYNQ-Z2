# 第三方来源与许可边界

本工程公开源码供比赛审查；没有以一个新许可证覆盖全部内容。原创项目代码的版权由项目贡献者保留，尚未另外选择通用开源授权；GitHub 可见不等于授予任意商业再许可。第三方代码和素材保留自己的授权条款。

1. Digilent `dvi2rgb_v1_7`、`rgb2dvi_v1_2`：官方来源 https://github.com/Digilent/vivado-library ，源文件头内的 Copyright / BSD 3-clause 完整声明保留。许可副本见 `licenses/Digilent_BSD_3_clause.txt`。使用方应保留版权、条件和免责条款；不能用作者名称背书。
2. MVTec AD tile 图片、标签及衍生回放、实际采集图：CC BY-NC-SA 4.0。作者、来源、变化和完整许可见 `data/DATA_SOURCES.md` 与 `data/real_tiles/license.txt`。不得把比赛测试素材直接带入商业产品。
3. MCS2 RGB 图片、标签及衍生图：CC BY 4.0。作者、来源和变化见 `data/DATA_SOURCES.md` 与 `data/independent_mcs2/LICENSE.txt`。
4. AMD/Xilinx Vitis BSP、FSBL、驱动、lwIP 和生成平台代码：保留随代码提供的版权/许可头；来源为本机 Vivado/Vitis 2025.2 与其官方库。`ethernet_sources/` 是本项目应用的权威源码。公开包不包含 Vivado/Vitis 安装软件；接收方自行安装相应工具。
5. Python、NumPy、Pillow、ReportLab、pypdf 与 Node：作为工具依赖安装，不将其运行环境/账号配置复制到发布包。生成手册使用本机系统字体，PDF 中嵌入必要字形，字体原始文件不随包提供。

若后续需要商业部署，应重新准备有适当授权的产品照片、明确原创代码的授权方式，并逐项核对第三方条款。
