# V182 registered instruction decode (unaccepted timing experiment)

The accepted board remains V179/HLS62 at8.169553FPS continuous HDMI, with
117/117 original-photo and HDMI decisions correct. V180 split-DDR125MHz
fails actual setup at-0.598ns, hold+0.037ns,DRC0, and was never programmed.
Its worst path changes from the prior SmartConnect FIFO to raw opcode bit27
(`t_1_load_reg_11896_reg[27]`) feeding BRAM write enable. The7.641ns data
path is83.14%routing. This experiment addresses that measured control path.

The47 binary task opcodes match the graph and are1,2,3. Previous generated
RTL carries a32-bit opcode through repeated long-lived comparisons. Source
`texture_control_decode.cpp` / frozen HLS64 derives the C117-exact residual
stream source63 and adds a separate, two-stage, three-bit one-hot decoder.
Standard conv/depthwise/add map to001/010/100. Raw unsupported values map to
000, retaining original error3; they must not be truncated into a valid opcode.
Depth is passed explicitly to conv, so its RAM/control logic does not reread
the raw32-bit opcode. Nearest mode retains zero instruction/depth handling.

Image resolution, frozen model, threshold and numeric operations stay the
same. The goal is control timing, not changed detection scores. Full117 C,
invalid-opcode checks, HLS resources/scheduling, full RTL and whole-video
physical timing must pass before programming and a fresh board experiment.
No achieved125MHz, new accuracy, speed or national-award readiness is claimed.
