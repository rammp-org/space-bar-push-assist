# Input devices and the MIB

How to add MIB support for an input device that drives the base, with the push-assist
handles as the worked example. The MIB code referred to here is `rammp-org/RAMMP-mib-fw`
at `7021c38` (main, 2026-11-02); the wire types are in `rammp-org/rammp-rtps`.

Status, 2026-11-02:
- The push-assist board reads both handles and publishes them as `rammp::HandleForce`
  over RTPS (rammp-rtps [PR #23](https://github.com/rammp-org/rammp-rtps/pull/23)). The
  board also serves a dashboard, params and OTA over ethernet (`firmware/INTERFACE.md`).
- `rammp-rtps` already has the PUSH_ASSIST drive state.
- Still to do: the MIB driving from it (see [What's left](#whats-left-by-repo)).

## The rule: devices measure, the MIB decides

Every input device publishes **what it measures**, in physical or normalized units, with
its health. It never publishes motion commands. The MIB (or whatever board integrates
the robot) owns the step from measurement to motion. It turns the data into a forward
and a turn target and feeds them to the trajectory planner.

| On the device | On the MIB |
|---|---|
| Calibration, tare, zero tracking | Which input drives, given the state (`DriveCommand`, arbitration, e-stop) |
| Sensor noise filtering, deadzones that hide sensor rest noise | Mapping to forward and turn: gains, dead bands that are driving decisions, limits |
| Health: is the sensor answering, is a correction at its limit | Stopping when the data goes quiet, stale or unhealthy |
| A steady publish rate | The trajectory planner (speed, acceleration and jerk per drive profile) |

Why the line sits there:
- **Safety and ownership in one place:** the MIB already decides who drives, handles the
  e-stop and limits the chair. A device that sent motion commands would bypass that.
- **Tuning without reflashing devices:** how hard to push for how fast is a driving
  decision. It lives with the drive profiles, not in each device's firmware.
- **Data that stays useful:** forces in newtons can be logged, plotted and reused (the
  Jetson, a later admittance controller). A velocity command can't be.

The joystick already works this way. The HMI applies its own calibration and its
deadzone, then sends normalized stick deflection (`XYTwist`, −1..1 per axis). It doesn't
send raw potentiometer voltages, and it doesn't send velocities. The MIB decides what
the deflection means.

## How the MIB drives today

```
XYTwist (joystick, -1..1)  ─┐
                            ├─> MibSystem ──> DriveController::set_target(linear, angular)   [-1, 1]
TwistSetpoint (Jetson,      │                 DriveController::set_velocity(m/s, rad/s)      (normalized
  m/s and rad/s)           ─┘                    by the profile's maxima, radius kept)
                                              ──> espp::TrajectoryPlanner  (limits per drive profile)
                                              ──> DifferentialDrive        (wheel RPM)
                                              ──> MotorCommand to the PACE RACER boards
```

- **Stick:** `MibSystem::apply_stick()` calls `drive_controller_.set_target(sample.y,
  -sample.x)`, but only in DRIVE_ENABLED. `y` is forward. `x` is positive to the right,
  and the drive follows REP 103, where positive angular is counter-clockwise (a left
  turn). So x is negated, in this one place (MIB issue #59).
- **Autonomy:** `handle_autonomy_setpoint()` calls `set_velocity(linear_mps,
  angular_radps)` in AUTONOMOUS and SHARED. If no setpoint arrives for
  `twist_setpoint_timeout` (300 ms), `stop_if_twist_lapsed()` stops the drive.
- **Planner:** `set_target()` takes −1..1 per axis. The planner scales that by the active
  profile's maximum velocities and limits acceleration (and jerk, if set).

  | Profile | Max linear | Max angular | Linear accel | Angular accel |
  |---|---|---|---|---|
  | LOW | 0.35 m/s | 1.0 rad/s | 0.5 m/s² | 1.0 rad/s² |
  | NORMAL | 0.75 m/s | 2.0 rad/s | 1.0 m/s² | 2.0 rad/s² |
  | HIGH | 1.0 m/s | 3.14 rad/s | 2.0 m/s² | 4.0 rad/s² |

  These are in `MIBconfig.hpp`. `stop()` decelerates to zero through the planner; it
  doesn't cut the motors.

## Adding an input device: checklist

1. **Message:** add it to `rammp-rtps`, following its README ("Add a new RTPS topic and
   type"). Use `rammp/<publisher>/<message>`, or the ROS 2 names if the Jetson reads it.
   Carry measurements in units (N, rad, −1..1), a health field, and nothing that's a
   motion command.
2. **Device:** publish at the sensor's own rate, best-effort, latest wins. Publish NaN or
   a cleared health bit when a sensor drops out, rather than going silent or sending
   zeros. Zero is a valid "no push", not "no data".
3. **MIB state:** decide which `MibSystemState` the device drives in, and how it is
   entered and left (`DriveCommand`). Don't let two inputs drive in the same state
   unless that state says how they blend (SHARED).
4. **MIB conversion:** write one pure function, measurement in and `(linear, angular)` in
   −1..1 out, with no ESP-IDF in it, so it can be tested on a host. Call
   `drive_controller_.set_target()` with the result.
5. **MIB safety:**
   - Stop through `drive_controller_.stop()` when the data lapses. Copy
     `stop_if_twist_lapsed()`: a deadline renewed by every message, checked on the state
     task.
   - Also stop on NaN, on a cleared health bit, and when the state is left.
6. **Signs:** forward is +. On the wire, a turn follows the device's natural sense. The
   MIB converts to REP 103 (counter-clockwise +) in the conversion function, and nowhere
   else.

## Push assist

Two handles, each with one tension and compression load cell. Push reads +, pull
reads −. The two handles give two axes:
- **Forward:** left + right.
- **Turn:** left − right. Positive when the left handle pushes harder, which turns the
  chair clockwise (to the right) seen from above. That is the same sense as
  `XYTwist.twist`.

### What the board publishes

`rammp::HandleForce` on `rammp/push_assist/handle_force`, from rammp-rtps
`messages/push_assist_message.hpp` (PR #23). It is best-effort and goes out once per
load-cell conversion, at 10 or 80 Hz:

```cpp
struct HandleForce {
  float left_n;   /**< N, push +, pull -; NaN while that handle's amp is not answering */
  float right_n;  /**< N, same for the right handle */
  uint8_t flags;  /**< kHandleForceLeftOk, RightOk, LeftZeroAtLimit, RightZeroAtLimit,
                       Updating (firmware update running: do not drive) */
  uint32_t seq;   /**< +1 per sample, so the MIB can count drops */
};
```

`firmware/tools/rtps_listen.py` subscribes to it from a laptop, as the MIB will.

### Entering and leaving PUSH_ASSIST

This is already defined in `rammp-rtps` (`DriveCommand`, `MibSystemState::PUSH_ASSIST`):
- The joystick sends `DriveCommand{DISABLE, profile, push_assist = true}` to enter
  PUSH_ASSIST, and `DISABLE` with `push_assist = false` to leave it. It resends the exit
  every 500 ms while the input is held.
- In PUSH_ASSIST the stick is not read for driving.
- AUTONOMOUS and SHARED are accepted from PUSH_ASSIST. ENABLE isn't: leave first.
- Push assist ignores `DriveCommand.profile`. The MIB should use its own profile for
  push assist. LOW (0.35 m/s, 1 rad/s) is the conservative start.

### The conversion

The reference, for the MIB to port. The same function runs live on the dashboard
(`pushToTwist()` in `firmware/web/dashboard.html`), which shows the `linear` and
`angular` the MIB would command while you push the handles.

```cpp
struct PushAssistGains {
  float dead_band_n;    // per handle; below this a handle reads as 0
  float forward_full_n; // forward force past the dead bands for linear = 1
  float turn_full_n;    // left - right past the dead bands for |angular| = 1
  float reverse_max;    // cap on backing up when the handles are pulled, 0..1
};

// left_n, right_n: HandleForce fields, push +.
// Returns {linear, angular} in [-1, 1] for DriveController::set_target(),
// angular counter-clockwise + (REP 103).
std::pair<float, float> push_to_twist(float left_n, float right_n, const PushAssistGains &g) {
  auto band = [&](float f) {  // remove the dead band, keep the sign
    return std::fabs(f) <= g.dead_band_n ? 0.0f : f - std::copysign(g.dead_band_n, f);
  };
  const float l = band(left_n), r = band(right_n);
  float linear = (l + r) / g.forward_full_n;
  float angular = -(l - r) / g.turn_full_n;   // left harder = clockwise = negative in REP 103
  linear = std::max(linear, -g.reverse_max);
  // Over full scale: scale both down together, so the turn radius holds
  // (as DriveController::set_velocity does).
  const float scale = std::max({1.0f, std::fabs(linear), std::fabs(angular)});
  return {linear / scale, angular / scale};
}
```

Starting values, to tune on the chair with the dashboard:

| Gain | Start | Why |
|---|---|---|
| `dead_band_n` | 10 N, or max(10 N, 280 N × \|c\| × 1.2) | `c` is each handle's lean crosstalk, measured in the main README's assembly step 12 |
| `forward_full_n` | 60 N | A firm two-handed push reaches full LOW-profile speed (0.35 m/s) |
| `turn_full_n` | 30 N | Turning takes a smaller force difference than going forward |
| `reverse_max` | 0.3 | Pulling backs the chair up slowly |

Notes for the MIB side:
- **Smoothing:** the planner's acceleration limits do it. The firmware does no extra
  filtering, so don't add a slow low-pass on top: it adds lag between the push and the
  chair answering.
- **Rate:** at 10 S/s there is 100 ms between samples. For driving, wire the HX711s'
  RATE pin high for 80 S/s and set `PA_HX711_80SPS` (see `firmware/README.md`).
- **One hand:** one handle alone gives forward plus a turn toward the other side, which
  is how a manual chair answers one hand.
- **Stop conditions:** stop with `stop()` when any of these happens:
  - No `HandleForce` arrives for 300 ms (the same as `twist_setpoint_timeout`).
  - Either force is NaN, or either ok bit is clear.
  - Either zero-tracking cap bit is set. Ask for a tare on the joystick.
  - The `Updating` bit is set.
  - PUSH_ASSIST is left, or the e-stop latches.
- **Zero drift:** the board tracks it (`firmware/README.md`, "Zero drift and zero
  tracking"). On the bench the assembled handle drifted about 0.1 N/min and the tracker
  held it within 0.02 N. The MIB doesn't need its own zero handling, only the cap bits.

## What's left, by repo

| Repo | Work |
|---|---|
| `rammp-rtps` | Review and merge PR #23 (`HandleForce`); later decide whether it goes ROS 2 facing |
| `space-bar-push-assist` | Done: `firmware/` publishes `HandleForce`. Still to do: wire RATE high for 80 S/s |
| `RAMMP-mib-fw` | In draft PR #65 (`spacebar-support`): `push_to_twist()` with a host test, the gains and push-assist planner limits saved in NVS and tunable from the control panel (`MibSystem::push_assist_gains()`), and the panel's link to this board (data, params, OTA). Still to do: PUSH_ASSIST in `SystemState`, entered and left by `DriveCommand.push_assist`; a `HandleForce` subscriber feeding `push_to_twist()` into `set_target()`; the lapse, health and cap stops |
| HMI joystick | The push-assist enter and exit (already described in `DriveCommand`), and a tare request if the MIB asks for one |
