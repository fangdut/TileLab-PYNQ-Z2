# License scope

The MIT license in LICENSE applies to original TileLab code and documentation
whose copyright is held by the TileLab contributors. The project owner
authorized this license on 2026-10-20.

Third-party material retains its own copyright notices and license terms.
Existing file-level license notices take precedence for those files. This
project does not grant or relicense rights held by third parties.

In particular:

- Digilent HDMI IP under ip_repo retains its BSD 3-Clause notices.
- AMD/Xilinx BSP, lwIP dependencies, exported drivers, PS initialization code,
  generated hardware and vendor IP retain their applicable original terms.
  An original TileLab wrapper or modification does not replace those terms.
- Third-party datasets, images, templates and external documentation retain
  their original rights and are not relicensed under MIT by this project.
- Python, NumPy, Pillow, ReportLab and FFmpeg retain their respective licenses.

See THIRD_PARTY_NOTICES.md and the notices preserved in the distributed files.

V168 exception: data/texture_v168_examples photographs/masks and the normal
feature memory under models/texture_v168_r3 retain MVTec AD's CC BY-NC-SA 4.0
attribution, non-commercial and share-alike terms. They are not MIT material.
Pretrained PyTorch weights retain upstream terms and are downloaded separately.

V169 exception: models/texture_v169_r1 contains an MVTec AD-derived normal
profile and historical evaluation metadata. Its PCA/normal-center data retain
CC BY-NC-SA 4.0 attribution, non-commercial and share-alike terms. They are not
MIT material. The exact large FPGA model is reconstructed offline from this
profile and a SHA-verified upstream pretrained checkpoint.

## V194 external ceramic stress evaluation

Source photographs from `ceramics-defects-detection`, DOI10.17632/47x6jdbr5j.1,
retain CC BY4.0 attribution to Lucileide Aquino do Nascimento, Otilio Paulo,
Gilvan Moreira da Paz and Micherlane Rodrigues Machado da Silva. Display
thumbnails/contact sheets and recorded HDMI captures under reports/v194 retain
that source attribution; thumbnails are for report display only. Original
111MB source files are fetched separately with their exact published SHA256.
The evaluated MVTec-derived model retains its existing CC BY-NC-SA4.0 terms.
No rights to unrelated Kaggle or Ceramic Cracks Database images are asserted;
those candidate sources were not incorporated in the distributed test corpus.

## V170 integer candidate

`project/pynq_z2_tile_v1_53/models/texture_v170_r1/` contains MVTec-derived artifacts under CC BY-NC-SA 4.0 and pretrained-weight derivatives subject to original terms. The same restrictions apply to original photos, masks and derived benchmark evidence in `reports/v169/board_cases/`. Original V169/V170 source code is MIT; AMD/Xilinx sources retain their original notices.
