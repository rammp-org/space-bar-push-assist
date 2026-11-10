#include <cstdio>
#include "touch_gate.hpp"
int main() {
  TouchGate g({.sample_rate_hz = 10.0f});
  for (int i = 0; i < 50; i++) g.update(6700, 7.0f);              // idle, a 7 N offset
  float out = g.update(7500, 7.0f);                                // probe plugged in: +12 %, no force
  std::printf("jump: touched %d sent %.1f N\n", g.touched(), out);
  int k = 0; while (g.touched() && k < 1000) { out = g.update(7500, 7.0f); k++; }
  std::printf("released after %.1f s, sent %.1f N, baseline %.0f\n", k / 10.0, out, g.baseline());
  out = g.update(8300, 7.0f); std::printf("hand on the new baseline: touched %d, tare %.1f\n", g.touched(), g.tare());
  out = g.update(8300, 37.0f); std::printf("push 30 N: sent %.1f N\n", out);
}
