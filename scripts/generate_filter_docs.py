"""
Generate 100 RF Filter Design Documents as PDF files.

These documents simulate filter design test cases and specifications
for RF/microwave filter engineering (SAW, BAW, FBAR, TC-SAW).
"""

import os
import json
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

_doc_cfg = config.uc_document_config("filter_design")
DATA_DIR = config.uc_data_dir("filter_design")
DOC_PREFIX = _doc_cfg["document_prefix"]
TOTAL_DOCUMENTS = _doc_cfg["total_documents"]
CLASSIFICATION = _doc_cfg["classification"]

try:
    from fpdf import FPDF
except ImportError:
    print("fpdf2 is required. Install with: pip install fpdf2")
    sys.exit(1)

# ── RF Filter domain data ──────────────────────────────────────────

FILTER_TYPES = [
    "SAW (Surface Acoustic Wave)",
    "BAW (Bulk Acoustic Wave)",
    "FBAR (Film Bulk Acoustic Resonator)",
    "TC-SAW (Temperature Compensated SAW)",
    "Coupled Resonator Filter",
    "Ladder Filter",
    "Lattice Filter",
    "Duplexer Module",
    "Multiplexer Module",
    "Low-Pass Filter",
    "Band-Pass Filter",
    "High-Pass Filter",
    "Notch Filter",
]

FREQUENCY_BANDS = [
    "Band 1 (2100 MHz)", "Band 2 (1900 MHz)", "Band 3 (1800 MHz)",
    "Band 5 (850 MHz)", "Band 7 (2600 MHz)", "Band 8 (900 MHz)",
    "Band 12 (700 MHz)", "Band 13 (700 MHz)", "Band 20 (800 MHz)",
    "Band 25 (1900 MHz)", "Band 26 (850 MHz)", "Band 28 (700 MHz)",
    "Band 30 (2300 MHz)", "Band 38 (2600 MHz TDD)", "Band 40 (2300 MHz TDD)",
    "Band 41 (2500 MHz TDD)", "Band 66 (AWS)", "Band 71 (600 MHz)",
    "n77 (3.3-4.2 GHz 5G NR)", "n78 (3.3-3.8 GHz 5G NR)",
    "n79 (4.4-5.0 GHz 5G NR)", "WiFi 2.4 GHz", "WiFi 5 GHz",
    "WiFi 6E (6 GHz)", "GPS L1 (1575 MHz)", "GPS L5 (1176 MHz)",
]

SUBSTRATE_MATERIALS = [
    "128° YX LiNbO3", "42° YX LiTaO3", "36° YX LiTaO3",
    "AlN on Si", "AlN on SiC", "ScAlN on Si",
    "Quartz", "Langasite", "PZT on Si",
]

APPLICATIONS = [
    "5G NR Sub-6 GHz Front-End Module",
    "4G LTE Carrier Aggregation",
    "WiFi 6E Coexistence Filter",
    "GPS/GNSS Anti-Jamming Filter",
    "Automotive V2X Communication",
    "IoT Narrowband Module",
    "Millimeter-Wave Beamforming",
    "UWB (Ultra-Wideband) Filter",
    "Satellite L-Band Filter",
    "Public Safety Band Filter",
]

DESIGN_TOOLS = [
    "Sonnet EM Suite v16", "Keysight ADS 2024", "COMSOL Multiphysics 6.2",
    "Ansys HFSS 2024R1", "Cadence AWR Microwave Office", "CST Studio Suite 2024",
    "Matlab RF Toolbox R2024b", "Synopsys CustomSim", "PathWave EM Design",
]

MEASUREMENT_INSTRUMENTS = [
    "Keysight N5227B PNA", "Rohde & Schwarz ZNA67", "Keysight E5080B ENA",
    "Rohde & Schwarz ZNB40", "Anritsu MS46122B ShockLine",
    "Keysight N9041B UXA", "Rohde & Schwarz FSW Signal Analyzer",
]

TEST_STATUSES = ["PASS", "FAIL", "CONDITIONAL PASS", "NEEDS REVIEW"]
PRIORITIES = ["P1 - Critical", "P2 - High", "P3 - Medium", "P4 - Low"]

ENGINEERS = [
    "Dr. Elena Vasquez", "Dr. Hiroshi Tanaka", "Dr. Anya Krishnamurthy",
    "Mark Sullivan", "Dr. Mei-Ling Chen", "Dr. Olaf Bergstrom",
    "Dr. Raj Patel", "Sarah Okonkwo", "Dr. Pierre Dubois",
    "Jennifer Kim", "Dr. Ahmed Al-Farsi", "Dr. Lena Kowalski",
    "Dr. Takeshi Yamamoto", "Ana Reyes", "Dr. Stefan Richter",
]

DESIGN_CENTERS = [
    "Irvine Design Center", "Osaka Design Center", "Cedar Rapids Lab",
    "Singapore RF Lab", "Andover HQ Lab", "Newbury Park Design Center",
    "Helsinki 5G Lab", "San Jose Advanced Design Lab",
]

PACKAGE_TYPES = [
    "WLP (Wafer Level Package)", "CSP (Chip Scale Package)",
    "QFN (Quad Flat No-Lead)", "LGA (Land Grid Array)",
    "Flip-Chip BGA", "Fan-Out WLP", "SiP (System in Package)",
]


def _generate_s_params():
    """Generate realistic S-parameter summary."""
    il = round(random.uniform(0.8, 3.5), 2)
    rl = round(random.uniform(10, 25), 1)
    rej = round(random.uniform(25, 55), 1)
    iso = round(random.uniform(20, 50), 1)
    return il, rl, rej, iso


def _generate_filter_doc_data(doc_id):
    """Generate all raw data for a filter design document."""
    ftype = random.choice(FILTER_TYPES)
    band = random.choice(FREQUENCY_BANDS)
    substrate = random.choice(SUBSTRATE_MATERIALS)
    app = random.choice(APPLICATIONS)
    tool = random.choice(DESIGN_TOOLS)
    instrument = random.choice(MEASUREMENT_INSTRUMENTS)
    status = random.choice(TEST_STATUSES)
    priority = random.choice(PRIORITIES)
    engineer = random.choice(ENGINEERS)
    reviewer = random.choice([e for e in ENGINEERS if e != engineer])
    center = random.choice(DESIGN_CENTERS)
    pkg = random.choice(PACKAGE_TYPES)

    base_date = datetime(2024, 1, 1)
    created = base_date + timedelta(days=random.randint(0, 500))
    modified = created + timedelta(days=random.randint(1, 60))

    doc_number = f"{DOC_PREFIX}-{doc_id:04d}"
    rev = f"Rev {random.choice(['A','B','C','D'])}.{random.randint(1,9)}"

    center_freq = round(random.uniform(600, 6000), 1)
    bw = round(random.uniform(20, 400), 1)
    il, rl, rej, iso = _generate_s_params()
    q_factor = random.randint(500, 15000)
    temp_coeff = round(random.uniform(-30, -5), 1)
    die_w = round(random.uniform(0.5, 3.0), 1)
    die_h = round(random.uniform(0.5, 2.5), 1)
    die_size = f"{die_w} x {die_h} mm"
    wafer_size = random.choice(["6-inch", "8-inch"])
    n_resonators = random.randint(3, 12)
    electrode_material = random.choice(['Al', 'Mo/Al', 'Mo', 'W', 'Pt/Al'])
    passivation = random.choice(['SiO2', 'Si3N4', 'SiO2/Si3N4 stack'])
    group_delay_var = round(random.uniform(1, 8), 1)
    power_handling = random.randint(26, 36)
    die_yield = round(random.uniform(80, 99), 1)
    esd_tolerance = random.choice([500, 1000, 2000])
    min_yield = random.randint(85, 98)
    max_group_delay = random.randint(2, 10)
    temp_drift = round(abs(temp_coeff) * 125 / 1e6 * center_freq, 1)
    min_power = random.randint(25, 35)

    return {
        "doc_number": doc_number,
        "rev": rev,
        "ftype": ftype,
        "band": band,
        "substrate": substrate,
        "app": app,
        "tool": tool,
        "instrument": instrument,
        "status": status,
        "priority": priority,
        "engineer": engineer,
        "reviewer": reviewer,
        "center": center,
        "pkg": pkg,
        "created": created,
        "modified": modified,
        "center_freq": center_freq,
        "bw": bw,
        "il": il,
        "rl": rl,
        "rej": rej,
        "iso": iso,
        "q_factor": q_factor,
        "temp_coeff": temp_coeff,
        "die_size": die_size,
        "die_w": die_w,
        "die_h": die_h,
        "wafer_size": wafer_size,
        "n_resonators": n_resonators,
        "electrode_material": electrode_material,
        "passivation": passivation,
        "group_delay_var": group_delay_var,
        "power_handling": power_handling,
        "die_yield": die_yield,
        "esd_tolerance": esd_tolerance,
        "min_yield": min_yield,
        "max_group_delay": max_group_delay,
        "temp_drift": temp_drift,
        "min_power": min_power,
    }


def _generate_filter_doc_text(doc_id):
    """Generate all text content for a filter design document."""
    d = _generate_filter_doc_data(doc_id)
    ftype = d["ftype"]
    band = d["band"]
    substrate = d["substrate"]
    app = d["app"]
    tool = d["tool"]
    instrument = d["instrument"]
    status = d["status"]
    priority = d["priority"]
    engineer = d["engineer"]
    reviewer = d["reviewer"]
    center = d["center"]
    pkg = d["pkg"]
    created = d["created"]
    modified = d["modified"]
    doc_number = d["doc_number"]
    rev = d["rev"]
    center_freq = d["center_freq"]
    bw = d["bw"]
    il = d["il"]
    rl = d["rl"]
    rej = d["rej"]
    iso = d["iso"]
    q_factor = d["q_factor"]
    temp_coeff = d["temp_coeff"]
    die_size = d["die_size"]
    wafer_size = d["wafer_size"]

    sections = {}

    sections["header"] = {
        "Document Number": doc_number,
        "Revision": rev,
        "Classification": CLASSIFICATION,
        "Title": f"{ftype} - {band} for {app}",
        "Subtitle": f"Design Validation and Performance Characterization",
    }

    sections["doc_info"] = {
        "Author": engineer,
        "Reviewer": reviewer,
        "Design Center": center,
        "Created Date": created.strftime("%Y-%m-%d"),
        "Last Modified": modified.strftime("%Y-%m-%d"),
        "Status": status,
        "Priority": priority,
    }

    sections["1_objective"] = (
        f"This document describes the design, simulation, and characterization of a "
        f"{ftype} filter targeting {band} for {app}. The filter is designed on "
        f"{substrate} substrate with a target center frequency of {center_freq} MHz "
        f"and bandwidth of {bw} MHz. The objective is to validate that the filter "
        f"meets the required insertion loss, rejection, and linearity specifications "
        f"for integration into the {app} module. This design iteration addresses "
        f"feedback from the previous revision regarding out-of-band rejection "
        f"improvements and temperature stability."
    )

    sections["2_scope"] = (
        f"- Filter Type: {ftype}\n"
        f"- Frequency Band: {band}\n"
        f"- Application: {app}\n"
        f"- Substrate: {substrate}\n"
        f"- Package: {pkg}\n"
        f"- Design Tool: {tool}\n"
        f"- Design Center: {center}\n\n"
        f"This specification applies to all variants of the {ftype} design "
        f"targeting {band}. Results are used to qualify the design for "
        f"mass production release."
    )

    n_resonators = d["n_resonators"]
    electrode_material = d["electrode_material"]
    passivation = d["passivation"]
    group_delay_var = d["group_delay_var"]
    power_handling = d["power_handling"]
    die_yield = d["die_yield"]
    esd_tolerance = d["esd_tolerance"]
    min_yield = d["min_yield"]
    max_group_delay = d["max_group_delay"]
    temp_drift = d["temp_drift"]
    min_power = d["min_power"]

    sections["3_design_parameters"] = (
        f"Center Frequency:       {center_freq} MHz\n"
        f"Bandwidth (3 dB):       {bw} MHz\n"
        f"Insertion Loss Target:  <= {round(il + 0.3, 1)} dB\n"
        f"Return Loss Target:     >= {round(rl - 2, 0)} dB\n"
        f"Out-of-Band Rejection:  >= {round(rej - 3, 0)} dB\n"
        f"Isolation (Duplexer):   >= {round(iso - 5, 0)} dB\n"
        f"Q Factor:               {q_factor}\n"
        f"Temperature Coefficient:{temp_coeff} ppm/°C\n"
        f"Die Size:               {die_size}\n"
        f"Wafer Size:             {wafer_size}\n"
        f"Number of Resonators:   {n_resonators}\n"
        f"Electrode Material:     {electrode_material}\n"
        f"Passivation:            {passivation}"
    )

    procedure_steps = [
        f"1. Open {tool} and load the {ftype} template project.",
        f"2. Define the substrate stack: {substrate} with specified layer thicknesses.",
        f"3. Set design targets: center freq {center_freq} MHz, BW {bw} MHz.",
        f"4. Run initial EM simulation with 2D mesh density of 20 cells/wavelength.",
        f"5. Optimize resonator geometry using gradient descent (target IL < {round(il + 0.3, 1)} dB).",
        f"6. Verify coupling coefficients between resonator stages.",
        f"7. Run 3D FEM simulation to account for package parasitics ({pkg}).",
        f"8. Export GDS-II layout for mask fabrication.",
        f"9. Fabricate prototype wafers ({wafer_size}, {substrate}).",
        f"10. Perform on-wafer probing using {instrument}.",
        f"11. Measure S-parameters (S11, S21, S12, S22) from 100 MHz to {round(center_freq * 3)} MHz.",
        f"12. Compare measured results against simulation and specification limits.",
        f"13. Perform temperature cycling (-40°C to +85°C) and re-measure.",
        f"14. Document results and generate summary report.",
    ]
    sections["4_test_procedure"] = "\n".join(procedure_steps)

    sections["5_acceptance_criteria"] = (
        f"- Insertion loss at center frequency shall be <= {round(il + 0.3, 1)} dB\n"
        f"- Return loss in passband shall be >= {round(rl - 2, 0)} dB\n"
        f"- Out-of-band rejection at +/- {round(bw * 1.5)} MHz offset >= {round(rej - 3, 0)} dB\n"
        f"- Group delay variation across passband shall be <= {max_group_delay} ns\n"
        f"- Temperature drift over -40°C to +85°C shall be <= {temp_drift} MHz\n"
        f"- Power handling shall be >= +{min_power} dBm at 1 dB compression\n"
        f"- ESD tolerance >= {esd_tolerance} V (HBM)\n"
        f"- Die yield on qualification lot >= {min_yield}%"
    )

    sections["6_test_results"] = (
        f"Measurement Date:       {modified.strftime('%Y-%m-%d')}\n"
        f"Devices Tested:         {random.randint(10, 100)}\n"
        f"Insertion Loss (meas):  {il} dB\n"
        f"Return Loss (meas):     {rl} dB\n"
        f"Rejection (meas):       {rej} dB\n"
        f"Isolation (meas):       {iso} dB\n"
        f"Q Factor (meas):        {q_factor}\n"
        f"Group Delay Variation:  {group_delay_var} ns\n"
        f"Power Handling:         +{power_handling} dBm\n"
        f"Die Yield:              {die_yield}%\n\n"
        f"Result Classification:  {status}"
    )

    perf = "excellent" if status == "PASS" else "acceptable" if status == "CONDITIONAL PASS" else "below-target"
    obs_items = [
        f"a) The {ftype} design demonstrated {perf} performance for {band}.",
        f"b) {'Insertion loss met target specification.' if il < 2.5 else 'Insertion loss is marginally above target; electrode thickness optimization recommended.'}",
        f"c) {'Out-of-band rejection exceeded the minimum requirement.' if rej > 30 else 'Rejection at near-band offset requires additional resonator tuning.'}",
        f"d) {random.choice(['Temperature stability was within specification across full range.', 'Slight frequency drift observed at +85°C; TC layer thickness may need adjustment.', 'Group delay flatness improved compared to previous revision.', 'Simulation-to-measurement correlation was within 3% for all key parameters.', 'Package parasitic effects were consistent with 3D EM model predictions.'])}",
        f"e) {random.choice(['No delamination observed after 1000-cycle thermal shock test.', 'Wafer-level uniformity was excellent (sigma < 1.5%).', 'ESD robustness exceeded specification by 2x margin.', 'Cross-talk between adjacent filter channels was below -55 dB.', 'Batch-to-batch reproducibility confirmed over 3 wafer lots.'])}",
    ]
    sections["7_observations"] = "\n".join(obs_items)

    if status == "PASS":
        sections["8_corrective_actions"] = "No corrective actions required. Design passed all acceptance criteria."
    else:
        actions = [
            f"1. {'Optimize resonator geometry to reduce insertion loss by ~0.3 dB.' if status == 'FAIL' else 'Review near-band rejection margin for worst-case temperature.'}",
            f"2. {'Re-run EM simulation with refined mesh for better accuracy.' if status != 'PASS' else 'N/A'}",
            f"3. {'Escalate to advanced materials team for alternative piezoelectric stack.' if status == 'FAIL' else 'Schedule follow-up measurement after design tweak.'}",
        ]
        sections["8_corrective_actions"] = "\n".join(actions)

    sections["9_signoff"] = (
        f"Author:     {engineer:<30s} Date: {modified.strftime('%Y-%m-%d')}\n"
        f"Reviewer:   {reviewer:<30s} Date: {(modified + timedelta(days=random.randint(1, 7))).strftime('%Y-%m-%d')}\n"
        f"Approver:   {'Dr. ' + random.choice(['James Liu', 'Karen Mitchell', 'Hans Weber', 'Yuko Ishida']):<30s} Date: {(modified + timedelta(days=random.randint(3, 14))).strftime('%Y-%m-%d')}"
    )

    return doc_number, sections, d


def _build_json_doc(d: dict, sections: dict) -> dict:
    """Build a structured JSON document from raw data and text sections.

    The JSON representation gives the search indexer direct access to every
    structured field without relying on lossy PDF text extraction.
    """
    doc_number = d["doc_number"]
    return {
        "document_number": doc_number,
        "revision": d["rev"],
        "classification": CLASSIFICATION,
        "title": f"{d['ftype']} - {d['band']} for {d['app']}",
        "subtitle": "Design Validation and Performance Characterization",
        "author": d["engineer"],
        "reviewer": d["reviewer"],
        "design_center": d["center"],
        "created_date": d["created"].strftime("%Y-%m-%d"),
        "last_modified": d["modified"].strftime("%Y-%m-%d"),
        "status": d["status"],
        "priority": d["priority"],
        "filter_type": d["ftype"],
        "frequency_band": d["band"],
        "substrate_material": d["substrate"],
        "application": d["app"],
        "design_tool": d["tool"],
        "measurement_instrument": d["instrument"],
        "package_type": d["pkg"],
        "wafer_size": d["wafer_size"],
        "center_frequency_mhz": d["center_freq"],
        "bandwidth_3db_mhz": d["bw"],
        "insertion_loss_target_db": round(d["il"] + 0.3, 1),
        "return_loss_target_db": round(d["rl"] - 2, 0),
        "rejection_target_db": round(d["rej"] - 3, 0),
        "isolation_target_db": round(d["iso"] - 5, 0),
        "insertion_loss_measured_db": d["il"],
        "return_loss_measured_db": d["rl"],
        "rejection_measured_db": d["rej"],
        "isolation_measured_db": d["iso"],
        "q_factor": d["q_factor"],
        "temperature_coefficient_ppm_per_c": d["temp_coeff"],
        "die_size": d["die_size"],
        "n_resonators": d["n_resonators"],
        "electrode_material": d["electrode_material"],
        "passivation": d["passivation"],
        "group_delay_variation_ns": d["group_delay_var"],
        "power_handling_dbm": d["power_handling"],
        "die_yield_pct": d["die_yield"],
        "esd_tolerance_v": d["esd_tolerance"],
        "sections": {
            "1_OBJECTIVE": sections["1_objective"],
            "2_SCOPE": sections["2_scope"],
            "3_DESIGN_PARAMETERS": sections["3_design_parameters"],
            "4_TEST_PROCEDURE": sections["4_test_procedure"],
            "5_ACCEPTANCE_CRITERIA": sections["5_acceptance_criteria"],
            "6_TEST_RESULTS": sections["6_test_results"],
            "7_OBSERVATIONS": sections["7_observations"],
            "8_CORRECTIVE_ACTIONS": sections["8_corrective_actions"],
            "9_SIGN_OFF": sections["9_signoff"],
        },
    }


class FilterDesignPDF(FPDF):
    """Custom PDF class for filter design documents."""

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, CLASSIFICATION, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(0, 51, 102)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 51, 102)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def body_text(self, text):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def key_value(self, key, value):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(0, 0, 0)
        self.cell(55, 5, key + ":")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, str(value), new_x="LMARGIN", new_y="NEXT")


def generate_pdf(doc_id):
    """Generate a single filter design PDF document and structured JSON data."""
    doc_number, sections, raw_data = _generate_filter_doc_text(doc_id)
    hdr = sections["header"]

    pdf = FilterDesignPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Title block
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, "FILTER DESIGN TEST CASE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, hdr["Title"], align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, hdr["Subtitle"], align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Document info table
    info = sections["doc_info"]
    pdf.section_title("DOCUMENT INFORMATION")
    for k, v in {**{"Document Number": doc_number, "Revision": hdr["Revision"]}, **info}.items():
        pdf.key_value(k, v)
    pdf.ln(3)

    # Numbered sections
    numbered = [
        ("1. OBJECTIVE", "1_objective"),
        ("2. SCOPE", "2_scope"),
        ("3. DESIGN PARAMETERS", "3_design_parameters"),
        ("4. TEST PROCEDURE", "4_test_procedure"),
        ("5. ACCEPTANCE CRITERIA", "5_acceptance_criteria"),
        ("6. TEST RESULTS", "6_test_results"),
        ("7. OBSERVATIONS AND FINDINGS", "7_observations"),
        ("8. CORRECTIVE ACTIONS", "8_corrective_actions"),
        ("9. SIGN-OFF", "9_signoff"),
    ]

    for title, key in numbered:
        pdf.section_title(title)
        pdf.body_text(sections[key])

    # Footer
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"END OF DOCUMENT - {doc_number}", align="C")

    json_doc = _build_json_doc(raw_data, sections)
    return doc_number, pdf, json_doc


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print(f"Generating {TOTAL_DOCUMENTS} filter design PDF + JSON documents in: {DATA_DIR}")
    manifest = []

    for i in range(1, TOTAL_DOCUMENTS + 1):
        doc_number, pdf, json_doc = generate_pdf(i)
        filename = f"{doc_number}.pdf"
        filepath = os.path.join(DATA_DIR, filename)
        pdf.output(filepath)

        # Save structured JSON alongside the PDF — used by chunk_and_index.py
        # for more reliable, lossy-free section extraction
        json_filename = f"{doc_number}.json"
        json_filepath = os.path.join(DATA_DIR, json_filename)
        with open(json_filepath, "w", encoding="utf-8") as jf:
            json.dump(json_doc, jf, indent=2, default=str)

        manifest.append({"id": i, "document_number": doc_number, "filename": filename, "json_filename": json_filename})
        print(f"  Generated: {filename} + {json_filename}")

    manifest_path = os.path.join(DATA_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nSuccessfully generated {TOTAL_DOCUMENTS} PDF + JSON documents and manifest.json in {DATA_DIR}")


if __name__ == "__main__":
    main()
