#pragma once

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "format.hpp"

/// Self-describing, runtime-settable parameters (INTERFACE.md, "Params").
///
/// Each parameter has a key, a label, a unit, a default, a range and a group,
/// so a host (the MIB control panel) can render whatever the board lists. Values
/// live in RAM; set() takes effect at once (the owner polls version() and
/// re-applies), and the store (NVS on the board) saves and loads them.
///
/// No ESP-IDF dependency: builds and tests on a host.
class ParamTable {
public:
  enum class Type { Float, Bool };

  struct Def {
    std::string key;   ///< snake_case, at most 15 characters (the NVS key limit)
    std::string label; ///< what a person reads
    std::string unit;  ///< the unit the value is in ("" for a bool)
    std::string group; ///< panel grouping
    Type type{Type::Float};
    float def{0};
    float min{0};
    float max{0};
    float step{0};
  };

  explicit ParamTable(std::vector<Def> defs) : defs_(std::move(defs)) {
    values_.reserve(defs_.size());
    for (const auto &d : defs_)
      values_.push_back(d.def);
  }

  /// Index of a key, or nullopt.
  std::optional<size_t> find(std::string_view key) const {
    for (size_t i = 0; i < defs_.size(); i++)
      if (defs_[i].key == key)
        return i;
    return std::nullopt;
  }

  /// Set a value, clamped to its range (a bool becomes 0 or 1). Returns the
  /// index, or nullopt for an unknown key or a non-finite value.
  std::optional<size_t> set(std::string_view key, float value) {
    const auto i = find(key);
    if (!i || !std::isfinite(value))
      return std::nullopt;
    const Def &d = defs_[*i];
    const float v = d.type == Type::Bool ? (value != 0 ? 1.0f : 0.0f)
                                         : std::clamp(value, d.min, d.max);
    {
      std::lock_guard<std::mutex> lk(mutex_);
      values_[*i] = v;
    }
    version_++;
    return i;
  }

  /// Every value back to its default (RAM only).
  void reset_to_defaults() {
    {
      std::lock_guard<std::mutex> lk(mutex_);
      for (size_t i = 0; i < defs_.size(); i++)
        values_[i] = defs_[i].def;
    }
    version_++;
  }

  float get(std::string_view key) const {
    const auto i = find(key);
    std::lock_guard<std::mutex> lk(mutex_);
    return i ? values_[*i] : 0.0f;
  }
  bool get_bool(std::string_view key) const { return get(key) != 0; }

  /// Bumped by every change; a user re-applies when it moves.
  uint32_t version() const { return version_.load(); }

  const std::vector<Def> &defs() const { return defs_; }

  /// One parameter as a JSON object.
  std::string json(size_t i) const {
    const Def &d = defs_[i];
    float v;
    {
      std::lock_guard<std::mutex> lk(mutex_);
      v = values_[i];
    }
    if (d.type == Type::Bool)
      return fmt::format(R"({{"key":"{}","label":"{}","type":"bool","value":{},"default":{},)"
                         R"("group":"{}"}})",
                         d.key, d.label, v != 0 ? 1 : 0, d.def != 0 ? 1 : 0, d.group);
    return fmt::format(R"({{"key":"{}","label":"{}","unit":"{}","value":{},"default":{},)"
                       R"("min":{},"max":{},"step":{},"group":"{}"}})",
                       d.key, d.label, d.unit, num(v), num(d.def), num(d.min), num(d.max),
                       num(d.step), d.group);
  }

  /// All parameters: {"params":[...]}.
  std::string json() const {
    std::string out = R"({"params":[)";
    for (size_t i = 0; i < defs_.size(); i++) {
      if (i)
        out += ',';
      out += json(i);
    }
    return out + "]}";
  }

protected:
  // Shortest form that reads back to the same float ("2", "0.005").
  static std::string num(float v) { return fmt::format("{}", v); }

  std::vector<Def> defs_;
  std::vector<float> values_;
  mutable std::mutex mutex_;
  std::atomic<uint32_t> version_{0};
};
