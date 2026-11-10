// Final-test log: replay each pad's raw reading with its own thresholds.
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include "touch_gate.hpp"
int main(int, char **argv) {
  std::ifstream f(argv[1]); std::string line;
  TouchGate l({.on_pct = 8, .off_pct = 4, .sample_rate_hz = 11}), r({.on_pct = 3, .off_pct = 1.5, .sample_rate_hz = 11});
  int nl = 0, nr = 0; bool wl = false, wr = false; float minr = 0;
  while (std::getline(f, line)) {
    std::vector<float> v; std::stringstream ss(line); std::string c;
    while (std::getline(ss, c, ',')) { try { v.push_back(std::stof(c)); } catch (...) { v.clear(); break; } }
    if (v.size() != 22) continue;
    l.update(v[20], v[12]); r.update(v[21], v[13]);
    if (l.touched() && !wl) nl++; if (r.touched() && !wr) nr++;
    wl = l.touched(); wr = r.touched(); if (!r.touched()) minr = std::min(minr, r.percent());
  }
  std::printf("left %d touches, right %d touches; right idle reading min %.2f%%\n", nl, nr, minr);
}
