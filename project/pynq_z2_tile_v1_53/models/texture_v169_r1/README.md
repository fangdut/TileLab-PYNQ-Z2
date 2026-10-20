# V169 frozen normal profile

MVTec AD Tile-derived PCA/normal centers: CC BY-NC-SA 4.0. Original project code remains MIT; these data are not MIT.
Pretrained backbone weights retain their upstream terms. Source: https://www.mvtec.com/company/research/datasets/mvtec-ad

This folder stores the frozen normal profile, threshold and the offline historical benchmark. It does not claim board acceptance. See reports/v169/acceptance.json for actual board scope.

Use tools/fpga_texture_v169/rebuild_model.py to reconstruct the exact model.bin. It checks the upstream checkpoint SHA, profile SHA and final FPGA blob SHA. Original build: CPU Torch 2.14.1+cpu, torchvision 0.29.1+cpu, NumPy 2.5.2. The 100 MB model.bin is an offline exported DDR blob; inference is executed by PL.
