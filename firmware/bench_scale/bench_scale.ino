/*
  bench_scale - bench readout for setting the overload stops of a push-handle
  load-cell cartridge. Prints % of full scale (FS) at 115200 baud, about 10
  lines per second, with a "change since mark" column to see the stop touch.
  Runs on ESP32 (Arduino core 2.x/3.x) and Arduino Uno/Nano.
  Library: "SparkFun Qwiic Scale NAU7802" (Arduino Library Manager).
  (Attempt 7: replaces bench_hx711; the amp is now the SparkFun Qwiic Scale.)

  Wiring (no soldering, no tools: SparkFun Qwiic Scale, NAU7802, SEN-15242)
    Qwiic socket -> a Qwiic-to-female-socket cable (SparkFun PRT-14988 or
    Adafruit 4397) onto the board's header: red 3V3, black GND, blue SDA,
    yellow SCL (Uno/Nano: A4 SDA, A5 SCL; ESP32: see the defines below).
    Load cell -> the spring terminal (press each lever with a fingertip or a
    hex key, push the stripped wire in, let go): red E+ (RED), black E- (BLK),
    white A- (WHT), green A+ (GRN); check the cell's label.

  Sign convention (README "Setting the overload stops"): push reads +, pull
  reads -. The known-mass check is a pull (the mass hangs from the jack), so
  "k" sets the sign from it on the mV/V path, and "c" stores a pull
  calibration as negative.

  Scale first. The sketch refuses "m" until it has f, a scale (r or c), a
  tare, and a passed known-mass check; "m!" overrides, with a warning.
    1. "f 50" (or "f 20"): the cell's full scale, kg.
    2. "r <mV/V>": the rated output on the cell's label or calibration sheet
       (e.g. r 1.0, r 1.5, r 2.0). Or skip r and use "c <kg>" in step 4.
    3. The cradle hanging from its eye, no mass: "t" to tare.
    4. Hang the known mass from the hanger (README), then "k <kg>": the
       sketch compares its reading with the mass and prints PASS (0.88-1.03 of
       it; the flexure leaves carry 1-13 % of the load beside the cell, so a
       right scale reads a little low) or FAIL. On FAIL, or without a label
       value, "c <kg>" with the same mass on calibrates the scale (and counts
       as checked).

  Stop-setting procedure (cartridge in the cradle, base down)
    1. Jack slack: "t" to tare in this position.
    2. Jack to +120 % (line shows "<-- 120%"), then "m" to mark.
    3. Turn one push stop screw until the line shows TOUCH (about -1 %).
       Repeat for the other push screw (re-mark at +120 % first if needed).
    4. Jack to -120 %, "m", set the pull screws the same way.
    5. Release to 0 and check it reads 0 +-1 %.

  Commands (one per line, any case): t, f <kg>, r <mV/V>, c <kg>, k <kg>, m, m!, s, h
*/

#include <Arduino.h>
#include <Wire.h>
#include <stdlib.h>
#include <math.h>
#include <SparkFun_Qwiic_Scale_NAU7802_Arduino_Library.h>

// ---- Pins -----------------------------------------------------------------
#if defined(ESP32)
  #ifndef I2C_SDA
    #define I2C_SDA 7
  #endif
  #ifndef I2C_SCL
    #define I2C_SCL 8
  #endif
#endif

// ---- Tuning ---------------------------------------------------------------
#define MA_WINDOW        4      // moving-average length (samples)
#define TARE_SAMPLES     32     // readings averaged for tare / calibrate
#define PRINT_PERIOD_MS  100    // ~10 lines per second
#define READY_TIMEOUT_MS 1000   // a conversion must be ready within this time
#define BAR_WIDTH        41     // odd so 0 % has its own centre cell
#define BAR_MIN_PCT      -150.0
#define BAR_MAX_PCT      150.0

// Known-mass check window (cad/calc/head_calc.txt 10): the leaves carry 1-13 %
// of the mass beside the cell, so a right scale reads a little low.
#define PASS_LO 0.88
#define PASS_HI 1.03

/*
  Counts at full scale from the rated output (no calibration weight needed).
  NAU7802 at gain 128 with its own LDO as both the reference and the bridge
  excitation (the Qwiic Scale's E+ is AVDD): full-scale differential input is
  +-0.5 * AVDD / 128, which maps to +-2^23 counts, and the bridge gives
  rated_mV_per_V * 1e-3 * AVDD, so AVDD cancels (ratiometric):
    counts_at_FS = rated_mV_per_V * 1e-3 * 256 * 2^23
                 = rated_mV_per_V * 2147483.648   (about 2.147 M per 1 mV/V)
  Real boards differ by a few % (gain tolerance); the known-mass check "k"
  catches a wrong scale, and "c <kg>" calibrates on the mass.
*/
#define COUNTS_PER_MV_PER_V 2147483.648

NAU7802 scale;

// ---- Settings (RAM only) --------------------------------------------------
float fsKg = 50.0;          // cell full scale, kg (recommended 50 kg cell; "f" must still be given)
float ratedMvV = 1.0;       // rated output, mV/V
float countsPerKg = 0.0;    // from "c <kg>"; 0 = use mV/V. Signed: a pull calibration is stored negative
int8_t polarity = 1;        // mV/V path: set by "k" so that the known pull reads negative
long tareCounts = 0;
bool fsSet = false;         // "f" given
bool scaleSet = false;      // "r" or "c" given
bool tared = false;
int8_t massCheck = 0;       // 0 not done, 1 PASS, -1 FAIL (reset by f, r and c)
bool streaming = true;
bool markSet = false;
float markPct = 0.0;

// ---- Moving average -------------------------------------------------------
long maBuf[MA_WINDOW];
uint8_t maIdx = 0;
uint8_t maCount = 0;
long maSum = 0;

// ---- Timing / serial ------------------------------------------------------
unsigned long lastReadyMs = 0;
unsigned long lastPrintMs = 0;
unsigned long lastWarnMs = 0;
char lineBuf[32];
uint8_t lineLen = 0;

// ---- ADC ------------------------------------------------------------------
bool adcReady() { return scale.available(); }

long adcRead() { return (long)scale.getReading(); }

// Blocking read with timeout. Returns false if no conversion became ready.
bool adcReadBlocking(long &out) {
  unsigned long t0 = millis();
  while (!adcReady()) {
    if (millis() - t0 > READY_TIMEOUT_MS) return false;
    delay(1);
  }
  out = adcRead();
  return true;
}

// Average n fresh readings. Returns false on timeout.
bool adcAverage(uint8_t n, long &out) {
  long sum = 0;   // 32 * 2^23 fits in 32 bits
  for (uint8_t i = 0; i < n; i++) {
    long v;
    if (!adcReadBlocking(v)) return false;
    sum += v;
  }
  out = sum / (long)n;
  return true;
}

void maPush(long v) {
  if (maCount == MA_WINDOW) maSum -= maBuf[maIdx];
  else maCount++;
  maBuf[maIdx] = v;
  maSum += v;
  maIdx = (maIdx + 1) % MA_WINDOW;
}

long maValue() { return maCount ? maSum / (long)maCount : 0; }

void maReset() { maIdx = 0; maCount = 0; maSum = 0; }

// ---- Conversions ----------------------------------------------------------
float netToKg(long net) {
  if (countsPerKg != 0.0) return (float)net / countsPerKg;
  float countsFs = ratedMvV * COUNTS_PER_MV_PER_V;
  return polarity * (float)net / countsFs * fsKg;
}

float kgToPct(float kg) { return kg / fsKg * 100.0; }

// ---- Printing helpers -----------------------------------------------------
void printF(float v, int8_t width, uint8_t prec) {
  char buf[16];
  dtostrf(v, width, prec, buf);
  Serial.print(buf);
}

void printL(long v, uint8_t width) {
  char buf[16];
  snprintf(buf, sizeof(buf), "%*ld", (int)width, v);
  Serial.print(buf);
}

int barIndex(float pct) {
  float x = (pct - BAR_MIN_PCT) / (BAR_MAX_PCT - BAR_MIN_PCT) * (BAR_WIDTH - 1);
  int i = (int)floor(x + 0.5);
  if (i < 0) i = 0;
  if (i > BAR_WIDTH - 1) i = BAR_WIDTH - 1;
  return i;
}

// '|' = 0 %, '!' = +-120 %, '=' = fill from 0, '*' = current value.
// '<' or '>' at the end when off the scale.
void printBar(float pct) {
  char bar[BAR_WIDTH + 1];
  int c = barIndex(0.0);
  int lo = barIndex(-120.0);
  int hi = barIndex(120.0);
  int p = barIndex(pct);
  for (int i = 0; i < BAR_WIDTH; i++) bar[i] = '.';
  int a = p < c ? p : c;
  int b = p < c ? c : p;
  for (int i = a; i <= b; i++) bar[i] = '=';
  bar[c] = '|';
  bar[lo] = '!';
  bar[hi] = '!';
  if (pct < BAR_MIN_PCT) bar[0] = '<';
  else if (pct > BAR_MAX_PCT) bar[BAR_WIDTH - 1] = '>';
  else bar[p] = '*';
  bar[BAR_WIDTH] = '\0';
  Serial.print('[');
  Serial.print(bar);
  Serial.print(']');
}

void printHeader() {
  Serial.println(F("    raw-avg       kg    %FS   dMark  bar -150 .. 0 .. +150 %FS"));
}

void printSettings() {
  Serial.print(F("Settings: FS "));
  printF(fsKg, 1, 2);
  Serial.print(F(" kg, rated "));
  printF(ratedMvV, 1, 4);
  Serial.print(F(" mV/V, tare "));
  Serial.print(tareCounts);
  Serial.print(F(" counts, scale "));
  if (countsPerKg != 0.0) {
    Serial.print(F("calibrated "));
    printF(countsPerKg, 1, 1);
    Serial.println(F(" counts/kg"));
  } else {
    Serial.print(F("from mV/V, FS = "));
    printF(ratedMvV * COUNTS_PER_MV_PER_V, 1, 0);
    Serial.println(F(" counts"));
  }
  Serial.print(F("Ready to mark: "));
  if (!fsSet) Serial.print(F("no (f <kg> first) "));
  if (!scaleSet) Serial.print(F("no (r <mV/V> or c <kg> first) "));
  if (!tared) Serial.print(F("no (t first) "));
  if (massCheck <= 0) Serial.print(F("no (known-mass check k <kg> not passed; m! overrides) "));
  if (fsSet && scaleSet && tared && massCheck > 0) Serial.print(F("yes"));
  Serial.print(F(". Known-mass check: "));
  Serial.println(massCheck > 0 ? F("PASS") : (massCheck < 0 ? F("FAIL") : F("not done")));
  Serial.print(F("Sign: push +, pull -. Streaming "));
  Serial.println(streaming ? F("on") : F("off"));
}

void printHelp() {
  Serial.println(F("Commands (one per line, any case):"));
  Serial.println(F("  t          tare (average 32 readings, no load)"));
  Serial.println(F("  f <kg>     set cell full scale, e.g. f 20 or f 50"));
  Serial.println(F("  r <mV/V>   set rated output (also clears calibration)"));
  Serial.println(F("  c <kg>     calibrate with this known mass hanging (a pull) on the cell (after tare)"));
  Serial.println(F("  k <kg>     check the scale with this known mass hanging (PASS 0.88-1.03)"));
  Serial.println(F("  m          mark current reading; dMark shows change since mark"));
  Serial.println(F("  m!         mark without a passed known-mass check (not recommended)"));
  Serial.println(F("  s          toggle streaming"));
  Serial.println(F("  h          this help"));
  Serial.println(F("Flags: '<-- 120%' within 1 % of +-120 %FS; 'TOUCH' when moved"));
  Serial.println(F("       at least 1 %FS toward zero since the mark."));
}

void notReady() { Serial.println(F("Scale not ready (check the Qwiic cable)")); }

// ---- Commands -------------------------------------------------------------
void handleLine(char *s) {
  while (*s == ' ' || *s == '\t') s++;
  if (*s == '\0') return;
  char cmd = (char)tolower((unsigned char)*s);
  char *arg = s + 1;
  while (*arg == ' ' || *arg == '\t') arg++;
  bool hasArg = (*arg != '\0');
  float val = hasArg ? (float)atof(arg) : 0.0;

  switch (cmd) {
    case 't': {
      Serial.println(F("Taring, keep the cell unloaded..."));
      long avg;
      if (!adcAverage(TARE_SAMPLES, avg)) { notReady(); return; }
      tareCounts = avg;
      tared = true;
      markSet = false;
      maReset();
      Serial.print(F("Tare = "));
      Serial.println(tareCounts);
      break;
    }
    case 'f':
      if (!hasArg || val <= 0.0) { Serial.println(F("Usage: f <kg>, e.g. f 20")); return; }
      fsKg = val;
      fsSet = true;
      massCheck = 0;                    // the mV/V scale depends on fsKg: check again
      markSet = false;
      printSettings();
      break;
    case 'r':
      if (!hasArg || val <= 0.0) { Serial.println(F("Usage: r <mV/V>, e.g. r 1.0")); return; }
      ratedMvV = val;
      countsPerKg = 0.0;
      polarity = 1;
      scaleSet = true;
      massCheck = 0;
      markSet = false;
      printSettings();
      break;
    case 'c': {
      if (!hasArg || val <= 0.0) { Serial.println(F("Usage: c <kg> with that mass hanging from the hanger")); return; }
      if (!tared) { Serial.println(F("Tare (t) with the mass off first")); return; }
      Serial.println(F("Calibrating, hold the load still..."));
      long avg;
      if (!adcAverage(TARE_SAMPLES, avg)) { notReady(); return; }
      long net = avg - tareCounts;
      if (labs(net) < 100) { Serial.println(F("Reading too close to tare; not calibrated")); return; }
      countsPerKg = -(float)net / val;  // the hanging mass is a pull: it reads -val, so a push reads +
      polarity = 1;
      scaleSet = true;
      massCheck = 1;                    // calibrated on a known mass
      markSet = false;
      maReset();
      printSettings();
      break;
    }
    case 'k': {
      if (!hasArg || val <= 0.0) { Serial.println(F("Usage: k <kg> with that mass hanging from the hanger")); return; }
      if (!scaleSet || !tared) { Serial.println(F("Set the scale (r <mV/V>) and tare (t) first")); return; }
      Serial.println(F("Checking, hold the load still..."));
      long avg;
      if (!adcAverage(TARE_SAMPLES, avg)) { notReady(); return; }
      float kgS = netToKg(avg - tareCounts);
      if (countsPerKg == 0.0 && kgS > 0.0) {   // mV/V path: the known pull must read negative
        polarity = -polarity;
        kgS = -kgS;
        Serial.println(F("Sign set from the known pull: push reads +, pull reads -"));
      }
      float kg = fabs(kgS);
      float ratio = kg / val;
      Serial.print(F("Known mass "));
      printF(val, 1, 2);
      Serial.print(F(" kg reads "));
      printF(kg, 1, 3);
      Serial.print(F(" kg, ratio "));
      printF(ratio, 1, 3);
      if (ratio >= PASS_LO && ratio <= PASS_HI) {
        massCheck = 1;
        Serial.println(F(": PASS"));
      } else {
        massCheck = -1;
        Serial.println(F(": FAIL. Check f and r, or calibrate: c <kg> with this mass on"));
      }
      break;
    }
    case 'm': {
      bool force = (*arg == '!');
      if (!fsSet || !scaleSet || !tared) {
        Serial.println(F("Not marked: set f <kg>, then r <mV/V> (or c <kg> with a known mass), then t"));
        printSettings();
        return;
      }
      if (massCheck <= 0 && !force) {
        if (massCheck < 0) Serial.println(F("Not marked: the known-mass check FAILED. Calibrate (c <kg>) or check f and r; m! overrides"));
        else Serial.println(F("Not marked: no known-mass check yet (k <kg>). m! overrides"));
        return;
      }
      if (massCheck <= 0) Serial.println(F("Warning (m!): scale not confirmed with a known mass; stops set now may not be at 1.2 x FS"));
      long net = maValue() - tareCounts;
      markPct = kgToPct(netToKg(net));
      markSet = true;
      Serial.print(F("Mark at "));
      printF(markPct, 1, 1);
      Serial.println(F(" %FS"));
      break;
    }
    case 's':
      streaming = !streaming;
      Serial.println(streaming ? F("Streaming on") : F("Streaming off"));
      if (streaming) printHeader();
      break;
    case 'h':
    case '?':
      printHelp();
      printSettings();
      break;
    default:
      Serial.println(F("Unknown command, h for help"));
      return;
  }
  if (streaming && cmd != 's') printHeader();
}

void pollSerial() {
  while (Serial.available() > 0) {
    char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (lineLen > 0) {
        lineBuf[lineLen] = '\0';
        handleLine(lineBuf);
        lineLen = 0;
      }
    } else if (lineLen < sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = ch;
    }
  }
}

// ---- Output line ----------------------------------------------------------
void printLine() {
  long raw = maValue();
  long net = raw - tareCounts;
  float kg = netToKg(net);
  float pct = kgToPct(kg);

  printL(raw, 11);
  Serial.print(' ');
  printF(kg, 8, 2);
  Serial.print(' ');
  printF(pct, 6, 1);
  Serial.print(' ');
  if (markSet) printF(pct - markPct, 7, 1);
  else Serial.print(F("      -"));
  Serial.print(F("  "));
  printBar(pct);

  if (fabs(fabs(pct) - 120.0) <= 1.0) Serial.print(F("  <-- 120%"));
  if (markSet && markPct != 0.0) {
    float towardZero = (markPct > 0.0) ? (markPct - pct) : (pct - markPct);
    if (towardZero >= 1.0) Serial.print(F("  TOUCH"));
  }
  Serial.println();
}

// ---- Setup / loop ---------------------------------------------------------
void setup() {
  Serial.begin(115200);
  unsigned long t0 = millis();
  while (!Serial && millis() - t0 < 2000) { }   // native-USB boards

#if defined(ESP32)
  Wire.begin(I2C_SDA, I2C_SCL);
#else
  Wire.begin();
#endif

  Serial.println();
  Serial.println(F("bench_scale: load-cell stop-setting readout (NAU7802)"));
  printHelp();
  printSettings();

  if (scale.begin()) {
    scale.setLDO(NAU7802_LDO_3V3);      // reference and bridge excitation
    scale.setGain(NAU7802_GAIN_128);
    scale.setSampleRate(NAU7802_SPS_80);
    scale.calibrateAFE();
    tareCounts = 0;
    Serial.println(F("Scale found. Unload the cell and send t to tare."));
  } else {
    notReady();
  }
  lastReadyMs = millis();
  if (streaming) printHeader();
}

void loop() {
  pollSerial();

  if (adcReady()) {
    maPush(adcRead());
    lastReadyMs = millis();
    if (streaming && millis() - lastPrintMs >= PRINT_PERIOD_MS) {
      lastPrintMs = millis();
      printLine();
    }
  } else if (millis() - lastReadyMs > READY_TIMEOUT_MS &&
             millis() - lastWarnMs > READY_TIMEOUT_MS) {
    lastWarnMs = millis();
    notReady();
  }
}
