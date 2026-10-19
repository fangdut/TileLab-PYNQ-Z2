# V1.55 offline references

`support_profiles_v155.py` is the frozen canonical reference for the two optional V1.55 profiles. It is used by evaluation and RTL vector generation, and is not imported for live host inference. The live host sends parameters and decodes the PL mask.

`wide_line_reference_v155.py` and `test_wide_line_v155.py` retain a weak-only intermediate experiment and the independently checked line feature; their no-new-seed property does not describe the final conservative profile, which intentionally adds >60 seeds. `directional_link_reference.py`, `tree_features_v155.py`, and `integer_tree_v155.py` are experiment references. No learned tree/network was selected, and there is no deployed tree ROM.

Selection is fixed in `reports/v155/FINAL_PROFILE.json`. The exposed old/development experiments and failed learned-model selection are preserved under `reports/v155/experiments`. New reserved groups were evaluated once with all three profiles after selection; they are now exposed regression data for future work.
