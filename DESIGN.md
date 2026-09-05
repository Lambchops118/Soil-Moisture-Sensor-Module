# Solar Soil Moisture Sensor — design notes

Handoff notes for whoever (or whatever) picks this up next. Covers what the board is,
how it works, and the reasoning behind choices that aren't obvious from the files.

KiCad 10.0.x project lives in `hardware/`. Schematic and layout are both DRC/ERC clean.

---

## What it is

A solar-harvesting, battery-free soil moisture probe that reports over MQTT. One PCB,
43 mm body width × 198.5 mm long (55 mm across mounting tabs), 2 layers, 1.6 mm FR4. The top ~85 mm carries the electronics and stays
above ground; the bottom ~89 mm is an etched capacitive probe that goes in the soil.
Silkscreen marks the boundary: `MAX SOIL LINE / SEAL BELOW` at y = 132.

No battery — energy is stored in a 3 F / 5.4 V supercapacitor. The node spends almost
all its time asleep and only wakes when the cap has enough charge to complete a Wi-Fi
transmission.

## Signal chain

```
SM141K04L panel ──J1──► BQ25570 boost/MPPT ──► SC1 (3F supercap, VBAT)
                            │                        │
                            └─ BAT_OK ──────┐        └──► TPS62842 buck ──► +3V3
                                            │                                 │
                                            └──► EN                           │
                                                                              ▼
   probe (J4 comb) ──► TLC555 astable ──FREQ_IN──► ESP32-C3 IO5 ──► Wi-Fi/MQTT
              ▲                  ▲
              │                  └── VCC_SENSOR, gated by Q1 (PMOS) from IO4
              └── J3 optional external probe (same net)
```

Moisture is read as a **frequency**, not a voltage. Wet soil raises the probe's
capacitance, which slows the 555. Firmware counts edges on IO5 and converts.

## Key parts and why

| Ref | Part | Why this one |
|---|---|---|
| U1 | BQ25570 | Cold-starts from 600 mV, so it works at dawn/under cloud. Has the MPPT and the VBAT_OK comparator built in. |
| U2 | ESP32-C3-WROOM-02-N4 | Wi-Fi + MQTT in a pre-certified module; no RF layout work needed. |
| U3 | TLC555CDR | CMOS 555 — µA-class supply current, runs at 3.3 V. A bipolar NE555 would not. |
| U4 | TPS62842DGRR | 60 nA quiescent buck. Quiescent current dominates the energy budget here. |
| SC1 | Eaton PHV 3F 5.4 V | Supercap, not a Li-ion: survives freeze/thaw and has no cycle-life limit. |
| Q1 | AO3401A | High-side PMOS so the whole sensor subsystem draws literally zero when idle. |

## Design decisions worth knowing

**MPPT is set to 80% of Voc.** `VOC_SAMP` is tied to `VSTOR`, which selects the 80%
ratio → 2.21 V against the SM141K04L's 2.76 V Voc. The panel's Vmp is ~2.28 V, so this
lands close to the real maximum power point. If the panel ever changes, this is the
first thing to revisit.

**Overvoltage is set below the supercap rating.** R2+R18+R19 (7 M) over R1+R17 (4 M)
gives VBAT_OV ≈ 4.99 V, comfortably under SC1's 5.4 V.

**The ESP is hard-gated on stored energy.** `BAT_OK` drives the buck's `EN` directly,
so the ESP physically cannot power up until the cap reaches ~4.08 V, and drops out
below ~3.63 V (R3+R20 = 4 M, R4+R21+R22+R23 = 8 M, R5 = 1.5 M). This is what stops the
classic brownout-loop failure where the node keeps half-booting and never transmits.

**The BQ25570's internal buck is deliberately unused.** `VOUT_EN` and `VOUT_SET` are
grounded and `LBUCK`/`VOUT` float; the external TPS62842 runs from VBAT instead. Its
quiescent current is far lower, which matters more than the extra part.

**The sensor rail is switched, not always-on.** Q1 gates `VCC_SENSOR` from IO4
(drive low = on, R11 pulls the gate high by default). The 555 and its RC network only
draw current during a measurement window.

**The probe is soldermask-covered on purpose.** J4's pads are `F.Cu` only with no mask
opening — the mask is the dielectric and the waterproofing. Do not "fix" this by adding
mask apertures; bare copper in soil corrodes and shorts.

**No copper behind or beside the probe.** Two keepout rule areas (y 132 → 221.2) forbid
pour on F.Cu and forbid *everything* on B.Cu. A ground plane behind the comb would
shunt the fringing field and kill sensitivity. Consequence: you cannot place parts or
route on B.Cu below the soil line, and no vias at all down there.

**U3 stays above the soil line.** It was considered for burial next to the comb to
shorten the high-impedance `OSC_RC` node. Rejected: with an 85 mm comb the electrode
itself dominates the node capacitance, so the ~20 mm of feed trace is marginal, and
burying it would mean potting a SOIC-8, restructuring the pours, and giving up both
RV1 (unsealable, unreachable trimmer) and J3.

**RV1 trims the baseline.** Cable and trace capacitance shift the dry-soil frequency.
RV1 exists to null that out in hardware. If it's ever removed, replace it with a fixed
resistor and do a two-point calibration in firmware instead.

**J3 is in parallel with J4, not an alternative.** The etched comb is always present,
so anything plugged into J3 *adds* capacitance rather than replacing it.

## Probe geometry

`SoilProbe:SoilProbe_IDC_40x85mm` — 40 × 85 mm interdigitated comb, 68 fingers
(34 per net), 1.25 mm pitch, 0.75 mm finger, 0.5 mm gap. Bus bars at x = 97 (`OSC_RC`)
and x = 136 (`GND`).

Depths below the seal line at y = 132: comb top 3 mm, comb bottom 88.0 mm (3.46″),
structural triangle starts 89.5 mm (3.52″) below the seal line and extends another
24 mm to y = 245.5. Active comb depth is unchanged. Comb length must be a multiple of 2.5 mm
to keep the finger count even and the pattern symmetric, which is why it isn't exact.

Back-side silkscreen carries 1″/2″/3″/3.5″ depth graduations for installation.

Oscillator: `f = 1.44 / ((R_A + 2·R_B)·C)` with R_A = R12 = 10 k and
R_B = R13 + RV1 = 47–147 k. Expect roughly **13–190 kHz** across the trim range and
dry-to-wet. (The 55 mm comb this replaced ran ~20–300 kHz — retune firmware if it was
written against the old board.)

## Verifying changes

```bash
kicad-cli sch erc --format report --severity-all -o review/erc.txt hardware/SoilMoistureSensor.kicad_sch
```

```bash
kicad-cli pcb drc --format report --schematic-parity --all-track-errors --severity-all -o review/drc.txt hardware/SoilMoistureSensor.kicad_pcb
```

Both should report zero. Note that `kicad-cli` does **not** refill zones — after any
scripted layout edit you must refill or the DRC result is stale:

```python
import pcbnew
B = pcbnew.LoadBoard("hardware/SoilMoistureSensor.kicad_pcb")
filler = pcbnew.ZONE_FILLER(B)
filler.Fill(B.Zones())
B.Save("hardware/SoilMoistureSensor.kicad_pcb")
```

Use KiCad's bundled Python (`<KiCad>/bin/python.exe`) for `pcbnew`. The SWIG
"memory leak" messages it prints on exit are noise, not errors.

`scripts/` holds the generator scripts from the original build. They are historical —
the `.kicad_pcb` and `.kicad_sch` are the source of truth now, not the scripts.

## Gotchas

- **Ground pour islands.** This is a 2-layer board with pours on both sides, and
  stitching vias were originally placed on a coarse grid. That once left an entire
  pour region — with SW1 and SW2's ground pads in it — floating with no via. After any
  layout change, confirm DRC reports **0 unconnected items**, and check the F.Cu GND
  zone for extra `filled_polygon` blocks that no via touches.
- **The `.kicad_sch` is CRLF and the `.kicad_pcb` is CRLF.** Scripted edits in Python
  must open with `newline=''` and write back the same endings, or the diff explodes.
- 1.6 mm FR4 at 198.5 mm long is floppy. Add a spine/support; a 2.0 mm revision
  needs connector lead fit checked and updated manufacturing specifications.

## September 2026 mechanical and telemetry revision

**Routing review:** the original board passed DRC, and the revised board passes
DRC with all track errors and schematic parity enabled: zero violations, zero
unconnected items, zero parity issues. ERC also reports zero errors/warnings.
Zones were refilled before checking. Copper/outline inspection confirmed the
existing probe geometry, rear probe keepout, and antenna-area copper clearance
are retained. Reports: `review/baseline-drc.txt`, `review/updated-drc.txt`,
`review/updated-erc.txt`; inspection image: `review/board-inspection.png`.
These are CAD checks, not measured RF, power, or mechanical validation.

**Insertion point:** the full-width comb ends above the new 24 mm triangular
extension. A two-layer rule area prohibits tracks, pads, vias, footprints and
zone fills throughout this structural tip. Seal its cut edges as with the probe.

**Supercap telemetry:** R24 = 2 MΩ 1% from VBAT to VCAP_ADC; R25 = 100 kΩ 1%
and C13 = 100 nF from VCAP_ADC to GND. These three 0603 parts are on the **front**,
near U2, so that the whole board assembles single-sided; each connects down to its
existing rear routing through an adjacent tented via. R24 is 2 MΩ rather than 2.2 MΩ
because 2 MΩ shares the Basic C22976 reel already used by ten other resistors.
VCAP_ADC connects to module pad 15, GPIO3 / ADC1 channel 3.
Use 0 dB attenuation, calibrated ADC millivolts, and
`supercap_volts = adc_millivolts * 21.0 / 1000.0`.
Disable GPIO pulls, wait at least 100 ms after power-up, and average readings
before enabling Wi-Fi. The filter time constant is about 9.5 ms.

The deliberately low divider output is 238 mV at 5 V; even at 5.4 V with worst-case
1% resistor tolerances it stays below 263 mV. This avoids the usual high-voltage
divider input when the buck shuts off the ESP supply. Drain is 2.38 µA at 5 V.
The tradeoff is accuracy: the ESP's specified ±10 mV calibrated ADC error becomes
approximately ±0.21 V referred to the cap, before resistor and leakage errors.
For tighter telemetry, calibrate the assembled board against a meter at two cap
voltages. Check powered-off behavior and readings on the first assembled board.
Reference: [Espressif ESP32-C3 datasheet, DC and ADC characteristics](https://documentation.espressif.com/esp32-c3_datasheet_en.html).
Firmware/MQTT publishing still needs implementation; this repository has no firmware.

**Panel mounting:** H1–H4 are 3.2 mm non-plated M3 holes in copper-free side tabs.
Centers are (92,80), (141,80), (92,106), (141,106) mm: **49 × 26 mm spacing**.
Use a 55 × 34 mm insulating carrier plate behind the board, with matching
holes and at least 5 mm insulating standoffs (trim protruding leads as needed).
Adhere the 29 × 23 mm SM141K04L to the outward-facing carrier surface, centered
at board (116.5,93) mm; its outline is on B.Fab. The carrier keeps the panel clear
of solder joints and the antenna. Route its insulated cable around the edge to J1,
with strain relief. The panel itself is not drilled; the carrier and hardware are
separate assembly items. The manufacturer drawing confirms two 3 mm rear solder
contacts, 23 mm apart, and no screw holes. Although called surface mountable, this
laminated panel requires hand soldering (5 seconds below 400°C), not high-temperature
reflow. `manufacture/panel-carrier.svg` adds two 6 mm contact-access holes and is
a 1:1 carrier template. See `manufacture/README.md` for assembly and polarity.

## Manufacturing package

`manufacture/` contains the JLCPCB Gerber/drill ZIP, matched 45-placement SMT
BOM/CPL, full procurement and manual-fit lists, paste layers, CAD source snapshot,
and clean DRC/ERC reports. Manufacturer, MPN, LCSC and assembly fields are now in
both schematic and PCB. All purchased electronic parts have verified LCSC numbers
except the Eaton SC1, retained for separate purchase by explicit user choice.
The external SM141K04L is LCSC C22012449. Etched J4 and drilled H1–H4 are not parts.
All 45 SMT placements are on the top side, so this orders as single-side assembly.
Of 23 assembly BOM lines, 13 are JLCPCB Basic and 2 are Preferred extended, both of
which are free of the per-part loading fee; the 8 Extended lines (U1-U4, L1, L2, R16,
C4) have no Basic or Preferred equivalent, and `manufacture/README.md` records why
for each. Stock was not reserved, but every line had stock on 2026-09-05; U1, L1 and
L2 are the thin ones. Re-run `scripts/audit_jlc_tiers.py` to refresh the check.
The released board is **1.6 mm**, matching the selected JST connector specification;
use a support/spine rather than changing to 2 mm without checking connector fit.

## Open work

1. **Supplier availability:** confirm U1 in the quotation and review JLCPCB's
   placement preview. Eight Extended parts remain unavoidable.
2. **Via-in-pad:** 19 vias land inside ordinary SMD pads, three of them breaking
   the pad edge (C12.2, R15.1, U4.5). These date from the original auto-routing.
   A via inside a pad's mask aperture wicks solder off the joint during reflow, so
   they are an assembly-yield risk worth clearing before a production run. The two
   vias in U4's exposed pad are deliberate and should stay.
3. **Manual assembly:** SC1, RV1, J1 and optional J2/J3 are hand-fitted; the solar
   module is hand-wired on its carrier.
4. **Panel carrier assembly:** source an insulating plate, spacers, and fasteners
   using the mounting dimensions above.
5. **No firmware in this repo.** Implement and calibrate supercap telemetry.
