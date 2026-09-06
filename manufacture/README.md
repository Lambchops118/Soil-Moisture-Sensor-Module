# Soil moisture sensor — JLCPCB manufacturing package

Generated from KiCad 10.0.4, 2026-09-05. DRC, ERC, connectivity and schematic
parity checks pass. The package contains **45 SMT placements / 23 BOM lines**.

## Upload these files

1. `gerbers_jlcpcb.zip` — two copper layers, both masks and silkscreens, outline,
   and separate plated/non-plated Excellon drills.
2. `bom_jlcpcb.csv` — JLCPCB assembly BOM with verified LCSC identifiers.
3. `cpl_jlcpcb.csv` — matching placement list, millimetres, all placements top side.

Select **2 layers, FR4, 1.6 mm, 1 oz copper, soldermask on both sides**, nominal
bounding dimensions **55 × 198.5 mm**. The main body is 43 mm wide. All 45 SMT
placements are on the **top side**, so order single-side assembly. Extended parts
are still required; this is not a Basic-only assembly. Let JLCPCB provide the assembly
fixture/rails required for the narrow, pointed outline; these are single-board files.

No via drill breaks into an SMD pad's soldermask aperture; the six vias inside U4's
exposed thermal pad are deliberate. Verify with `../scripts/check_via_in_pad.py`
after any re-route.

Keep mask over the entire capacitive comb and keep the tip free of copper.
Do not let an automated "exposed test pad" change remove the probe mask.
The 1.6 mm specification matches the saved PCB and JST's 0.8–1.6 mm board range.
Use mechanical support when inserting the long board. A thicker revision needs
the connector lead fit checked; do not silently order this package as 2.0 mm.

## Assembly and sourcing limits

`bom_all_parts.csv` is the full electronic procurement list, including the solar
panel. `manual_parts.csv` lists **J1, J2, J3, RV1, SC1 and the external panel**.
These are not in the SMT BOM/CPL. J2 and J3 are optional; J1, RV1 and SC1 are needed
for the intended build. The original manual-assembly policy for through-hole parts
is retained. DNP flags in the CAD indicate exclusion from automated assembly here,
not permission to omit required hand-fitted components from the finished node.

Every purchased electronic part has an LCSC identifier except **SC1**, the
user-approved Eaton PHV-5R4V305-R external-purchase exception. Source SC1 separately
(for example Mouser 504-PHV-5R4V305-R) and hand solder it. J4 is etched PCB copper,
and H1–H4 are drilled holes: they are not purchased electronic parts and have no
LCSC numbers. Screws, spacers, carrier plate and cable are mechanical assembly supplies.

### Library tiers and the Extended-part fee

Rechecked against the JLCPCB parts catalog on 2026-09-05
(`../review/jlc-tier-audit.json`, regenerate with `../scripts/audit_jlc_tiers.py`).
Of 23 assembly BOM lines: **13 Basic, 2 Preferred extended, 8 Extended**. Basic and
Preferred-extended lines carry no per-part loading fee, so only the 8 below attract it:

| Ref | LCSC | Why it cannot be Basic or Preferred |
| --- | --- | --- |
| U1 | C506250 | No Basic/Preferred energy-harvesting charger exists. |
| U2 | C2934560 | JLCPCB lists no Basic or Preferred ESP32 module or chip. |
| U3 | C6986 | The only Preferred 555 is the bipolar NE555DR: 4.5 V minimum, mA-class supply. |
| U4 | C2873354 | No Basic/Preferred nanoamp-quiescent buck. |
| L1, L2 | C167883, C167804 | JLCPCB's Basic/Preferred inductors are multilayer signal parts rated in single-digit mA; it carries no Basic or Preferred power inductor. |
| R16 | C17740 | TPS62842 decodes 3.3 V only from R\_SET 50.21–54.39 kΩ. No Basic or Preferred 52.3 k exists; the nearest Basic value, 51 k (C17737), leaves under 0.6% margin at the window edge before tempco. |
| C4 | C97905 | No Basic or Preferred 10 nF C0G/NP0 exists in any package. |

C4 was **changed from C1845387 to Murata C97905** because the previous choice had
zero stock. It must remain 10 nF C0G/NP0, 5% or better: this is the MPPT
sample-and-hold node and an X7R substitution is not equivalent.

L1 and L2 were **changed from the Coilcraft LPS4018 pair to Changjiang FNR40xx**
(`C167883` 22 uH / 292 mOhm, `C167804` 2.2 uH / 59 mOhm). Both are lower-DCR than the
parts they replace and together drop from $12.77 to $0.24 across a five-board order.
The whole FNR40xx series shares one land pattern regardless of height (datasheet
`datasheets/FNR_series.pdf`: a=1.9, b=1.1, C=3.7 mm), so both sit on
`Inductor_SMD:L_Changjiang_FNR4018S`. L1 is the 3.0 mm-tall FNR4030 body; nothing on
this board is height-constrained below SC1 and RV1.

Part-number verification is not a reservation of JLCPCB stock. Every line had stock
at the 2026-09-05 recheck; U1 (856) is the thin one — confirm it in the quotation. Check the other matches and quantities too. Exact
catalog links and manufacturer numbers are in the full BOM and in the schematic/PCB fields.

The CPL uses KiCad's exported rotations and a shared bottom-left origin
(KiCad X=89, Y=245.5 mm). Every placement is `top`. Inspect JLCPCB's placement
preview for U1–U4, Q1 and switches before approval, since its library's zero-angle
convention can differ. `assembly/kicad_positions.csv` retains the raw export;
`assembly/front.svg` and `back.svg` are assembly references. No order was submitted.

## Solar panel compatibility — verified

The **SM141K04L** fits the carrier: nominal 29 × 23 × 1.8 mm, ±0.3 mm dimensions;
the plate is 55 × 34 mm. It has two **3 mm rear solder contacts**, at 3 mm from
the left/right edges and halfway along the 23 mm dimension (23 mm contact spacing).
It has **no screw holes**. The manufacturer's term "surface mountable" does not
mean this laminated module should go through the PCB reflow process. The datasheet
specifies manual soldering for 5 seconds below 400°C and warns against high-temperature
reflow. The existing remote carrier and wire connection to J1 are therefore suitable.

`panel-carrier.svg` is a 1:1 mechanical cutting template, **not a PCB Gerber**:
black paths cut the outside and holes; the blue rectangle is a placement guide only.
Four 3.2 mm mounting holes have **49 × 26 mm spacing**, matching H1–H4 exactly.
Two 6 mm terminal-access holes align with the panel contacts and accommodate their
position tolerance. Use insulating plate material, at least 5 mm insulating PCB
standoffs, and small adhesive pads away from the contacts/windows. Support the
laminate without bending or clamping it. Solder and strain-relieve the wires before
attaching the carrier. Solar **+ goes to J1 pin 1 (VIN_DC)**; **− to pin 2 (GND)**.
Check the printed polarity on the actual module; back-view drawings are mirrored
relative to viewing the illuminated face. The panel is fitted with its active face
outward on the back of the node, below the antenna area.

The manufacturer datasheet is included in `datasheets/SM141K04L.pdf`, page 3 for
mechanical/soldering details. The manufacturer's current file is marked preliminary;
confirm the delivered module revision before cutting a large batch of carriers.

## Other files and reproduction

- `stencil/`: front/back paste Gerbers, kept out of the bare-board ZIP.
- `source/`: exact KiCad sources, local libraries and sourcing manifest used.
- `reports/`: DRC/ERC JSON, drill summary and validation counts.
- `sha256.json`: hashes of the release files.

Regenerate from the current board with KiCad's bundled Python:

```powershell
& 'C:/Program Files/KiCad/10.0/bin/python.exe' scripts/manufacture.py
```

The script fills zones, checks DRC/ERC, exports and checks matching BOM/CPL
designators, placement bounds, probe mask coverage and required output files.
Firmware, voltage calibration, assembly testing and weather sealing remain necessary.

Sources: [ANYSOLAR datasheet](https://anysolar.biz/wp-content/uploads/2026/06/SM141K04L-R3.5-DATASHEET.pdf),
[panel catalog entry C22012449](https://item.szlcsc.com/23442921.html),
[JLCPCB KiCad BOM/CPL guidance](https://jlcpcb.com/help/article/how-to-generate-bom-and-centroid-files-from-kicad-8),
[JST PH datasheet](https://datasheet.lcsc.com/szlcsc/1811151524_JST-Sales-America-B2B-PH-K-S-LF-SN_C131337.pdf).
