// Replay a console CSV through TouchGate: t, right force, right touch raw -> sent force.
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include "touch_gate.hpp"
int main(int, char **argv) {
  std::ifstream f(argv[1]);
  TouchGate g({.sample_rate_hz = 11.0f});
  std::string line; int touches = 0; bool was = false; double hands_off_max = 0, hands_off_raw_max = 0;
  while (std::getline(f, line)) {
    std::vector<float> v; std::stringstream ss(line); std::string c;
    while (std::getline(ss, c, ',')) v.push_back(std::stof(c));
    if (v.size() != 17) continue;
    const float out = g.update(v[12], v[2]);
    if (g.touched() && !was) { touches++; std::printf("touch %2d at %.1f s  tare %.1f N  %.1f%%\n", touches, v[0], g.tare(), g.percent()); }
    if (!g.touched() && touches) { hands_off_max = std::max<double>(hands_off_max, std::fabs(out)); hands_off_raw_max = std::max<double>(hands_off_raw_max, std::fabs(v[2])); }
    was = g.touched();
  }
  std::printf("%d touches; hands-off after the first: sent max %.2f N (firmware now max %.1f N)\n", touches, hands_off_max, hands_off_raw_max);
}
