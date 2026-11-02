# Real-photo demonstration inputs

Twelve original, unedited MVTec AD tile photos previously used in the public development benchmark, two per category. These are not independent blind validation images. Copyright MVTec Software GmbH. Images and derived evidence retain CC BY-NC-SA 4.0: https://creativecommons.org/licenses/by-nc-sa/4.0/ . Official dataset information: https://www.mvtec.com/company/research/datasets/mvtec-ad . Each catalog entry records its exact source URL and SHA256. Do not label them as personally photographed or generated images.

The production station reads catalog.json and passes only original pixels to the FPGA. expected_offline_only.json is used by the acceptance evaluator after FPGA inference; its labels do not control the detector or release interlocks. Live runtime records are written outside this directory.
