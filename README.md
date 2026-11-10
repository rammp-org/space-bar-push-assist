Bench evidence for the touch switch and tare (2026-11-10).

- run1_right_handle.csv: right pad only, 12 touch/push/pull cycles (firmware with one pad).
- run2_shared_threshold.csv: both pads, one 8 %% threshold: the right pad never crossed it.
- run3_per_handle.csv: both pads, per-handle thresholds (8/4 %%, 3/1.5 %%).
- replay*.cpp, stuck.cpp: host replays through firmware/main/touch_gate.hpp (clang++ -std=c++20 -I firmware/main).
- analyse_run1.py: the first analysis and figure.
