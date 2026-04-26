"""
Generate 100 Engineering Documents for KLA Manufacturing Test Cases.

These documents simulate semiconductor inspection and metrology test cases
used in KLA's manufacturing quality assurance processes.
"""

import os
import json
import random
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# KLA product lines and systems
PRODUCT_LINES = [
    "Surfscan SP7", "Surfscan SP5", "Puma 9xxx", "Puma 9900",
    "2920 Series", "eDR-7100", "Candela 8520",
    "ICOS T3/T7", "Zeta-388", "Zeta-20",
    "WaferSight PWG", "Archer 700", "Archer 750",
    "ATL/LMS IPRO8", "5D Analyzer",
    "Teron SL650", "Teron 640", "C205 Broadband Plasma",
]

INSPECTION_TYPES = [
    "Unpatterned Wafer Inspection", "Patterned Wafer Inspection",
    "Macro Defect Inspection", "E-Beam Inspection",
    "Optical Overlay Metrology", "Film Thickness Measurement",
    "CD-SEM Measurement", "Wafer Geometry Measurement",
    "Surface Roughness Analysis", "Particle Detection",
    "Bare Wafer Inspection", "Reticle Inspection",
    "IC Substrate Inspection", "LED Inspection",
    "3D NAND Inspection", "FinFET Inspection",
]

DEFECT_TYPES = [
    "Crystal Originated Particles (COP)", "Scratches", "Haze",
    "Residue", "Pits", "Mounds", "Stacking Faults",
    "Pattern Defects", "Bridge Defects", "Missing Pattern",
    "Extra Pattern", "CD Variation", "Overlay Shift",
    "Edge Placement Error", "Film Non-Uniformity",
    "Contamination", "Micro-cracks", "Voids",
    "Delamination", "Corrosion", "ESD Damage",
]

PROCESS_STEPS = [
    "Post-Lithography", "Post-Etch", "Post-CMP", "Post-Deposition",
    "Pre-Diffusion", "Post-Implant", "Post-Clean", "Pre-Bonding",
    "Post-Metallization", "Final Inspection", "Incoming Wafer QC",
    "Post-Oxidation", "Post-Anneal", "Post-Planarization",
]

WAFER_SIZES = ["200mm", "300mm", "450mm"]
TECHNOLOGY_NODES = ["3nm", "5nm", "7nm", "10nm", "14nm", "22nm", "28nm", "45nm", "65nm"]

TEST_STATUSES = ["PASS", "FAIL", "CONDITIONAL PASS", "NEEDS REVIEW"]
SEVERITY_LEVELS = ["Critical", "Major", "Minor", "Informational"]
PRIORITIES = ["P1 - Critical", "P2 - High", "P3 - Medium", "P4 - Low"]

ENGINEERS = [
    "Dr. Sarah Chen", "James Rodriguez", "Dr. Amir Patel",
    "Emily Nakamura", "Dr. Klaus Weber", "Lisa Johansson",
    "Dr. Wei Zhang", "Michael Torres", "Dr. Priya Sharma",
    "Robert Kim", "Dr. Anna Petrova", "David Okafor",
    "Dr. Yuki Tanaka", "Maria Gonzalez", "Dr. Thomas Mueller",
]

FAB_LOCATIONS = [
    "Milpitas Fab A", "Milpitas Fab B", "Hsinchu Fab 12",
    "Hsinchu Fab 15", "Dresden Fab 3", "Singapore Fab 7",
    "Pyeongtaek Fab 2", "Chandler Fab 42",
]


def generate_test_procedure(inspection_type, product_line, defect_type):
    """Generate a realistic test procedure."""
    steps = [
        f"1. Power on the {product_line} system and allow 30-minute warm-up period.",
        f"2. Load the calibration wafer and run the standard calibration routine.",
        f"3. Verify calibration results are within specification (±2% tolerance).",
        f"4. Load the test wafer onto the stage using the automated handler.",
        f"5. Select the '{inspection_type}' recipe from the recipe library.",
        f"6. Configure detection sensitivity to target {defect_type} defects.",
        f"7. Set scan parameters: full wafer scan with edge exclusion of 3mm.",
        f"8. Initiate the inspection run and monitor real-time defect map.",
        f"9. Upon completion, review the defect density map and classification results.",
        f"10. Export results to the factory automation system (SECS/GEM interface).",
        f"11. Compare results against the golden reference baseline.",
        f"12. Document any anomalies and generate the summary report.",
    ]
    return "\n".join(steps)


def generate_acceptance_criteria(inspection_type, technology_node):
    """Generate acceptance criteria for the test case."""
    criteria = [
        f"- Defect detection sensitivity must meet {technology_node} node requirements",
        f"- False positive rate shall not exceed 5% of total detected events",
        f"- Scan throughput must be ≥ {random.randint(40, 120)} wafers per hour",
        f"- Classification accuracy shall be ≥ {random.randint(90, 99)}% for known defect types",
        f"- Repeatability (3-sigma) shall be within ±{random.uniform(0.5, 3.0):.1f}% for {inspection_type}",
        f"- System uptime during test shall be ≥ 98%",
        f"- All results must be traceable through the MES integration",
        f"- Measurement correlation with reference tool shall be ≥ {random.uniform(0.92, 0.99):.2f} R²",
    ]
    return "\n".join(criteria)


def generate_document(doc_id):
    """Generate a single engineering test case document."""
    product_line = random.choice(PRODUCT_LINES)
    inspection_type = random.choice(INSPECTION_TYPES)
    defect_type = random.choice(DEFECT_TYPES)
    process_step = random.choice(PROCESS_STEPS)
    wafer_size = random.choice(WAFER_SIZES)
    tech_node = random.choice(TECHNOLOGY_NODES)
    status = random.choice(TEST_STATUSES)
    severity = random.choice(SEVERITY_LEVELS)
    priority = random.choice(PRIORITIES)
    engineer = random.choice(ENGINEERS)
    reviewer = random.choice([e for e in ENGINEERS if e != engineer])
    fab = random.choice(FAB_LOCATIONS)

    base_date = datetime(2024, 1, 1)
    created_date = base_date + timedelta(days=random.randint(0, 500))
    modified_date = created_date + timedelta(days=random.randint(1, 60))

    doc_number = f"KLA-MFG-TC-{doc_id:04d}"
    revision = f"Rev {random.choice(['A', 'B', 'C', 'D'])}.{random.randint(1, 9)}"

    defect_count = random.randint(0, 5000)
    defect_density = round(defect_count / (3.14159 * (150 if wafer_size == "300mm" else 100) ** 2) * 1e4, 2)
    nuisance_rate = round(random.uniform(0.5, 8.0), 1)
    capture_rate = round(random.uniform(85.0, 99.9), 1)

    document = f"""{'='*80}
ENGINEERING TEST CASE DOCUMENT
{'='*80}

Document Number: {doc_number}
Revision: {revision}
Classification: CONFIDENTIAL - KLA Internal Use Only

Title: {inspection_type} - {defect_type} Detection on {product_line}
Subtitle: {process_step} Quality Validation for {tech_node} Node Manufacturing

{'─'*80}
DOCUMENT INFORMATION
{'─'*80}

Author:           {engineer}
Reviewer:         {reviewer}
Fab Location:     {fab}
Created Date:     {created_date.strftime('%Y-%m-%d')}
Last Modified:    {modified_date.strftime('%Y-%m-%d')}
Status:           {status}
Priority:         {priority}
Severity Level:   {severity}

{'─'*80}
1. OBJECTIVE
{'─'*80}

This test case validates the capability of the {product_line} system to detect
and classify {defect_type} defects during {process_step.lower()} inspection
at the {tech_node} technology node. The test is conducted at {fab} to ensure
manufacturing quality standards are met for {wafer_size} wafer production.

The primary objective is to verify that the inspection system meets the required
detection sensitivity and classification accuracy for {defect_type} defects
that are critical to yield at the {tech_node} node. This test case is part of
the ongoing qualification program for the {product_line} platform.

{'─'*80}
2. SCOPE
{'─'*80}

- Product Line: {product_line}
- Inspection Type: {inspection_type}
- Target Defect: {defect_type}
- Process Step: {process_step}
- Wafer Size: {wafer_size}
- Technology Node: {tech_node}
- Fab Location: {fab}

This test case applies to all {product_line} systems deployed at {fab}
for {process_step.lower()} monitoring in the {tech_node} manufacturing line.
Results from this test are used to establish baseline performance metrics
and to qualify new recipe configurations.

{'─'*80}
3. TEST CONFIGURATION
{'─'*80}

System:                {product_line}
Software Version:      v{random.randint(8, 15)}.{random.randint(0, 9)}.{random.randint(100, 999)}
Recipe:                {inspection_type.replace(' ', '_').upper()}_{tech_node}_{process_step.replace('-', '_').upper()}
Illumination Mode:     {"Darkfield" if random.random() > 0.5 else "Brightfield"}
Scan Speed:            {random.choice(["High", "Medium", "Low"])} ({random.randint(50, 200)} mm/s)
Pixel Size:            {random.choice(["0.1μm", "0.25μm", "0.5μm", "1.0μm"])}
Edge Exclusion:        {random.randint(2, 5)}mm
Sampling Plan:         {random.choice(["Full wafer", "5-point", "9-point", "21-point"])} sampling

{'─'*80}
4. TEST PROCEDURE
{'─'*80}

{generate_test_procedure(inspection_type, product_line, defect_type)}

{'─'*80}
5. ACCEPTANCE CRITERIA
{'─'*80}

{generate_acceptance_criteria(inspection_type, tech_node)}

{'─'*80}
6. TEST RESULTS
{'─'*80}

Test Execution Date:   {modified_date.strftime('%Y-%m-%d')}
Wafers Tested:         {random.randint(5, 50)}
Total Defects Found:   {defect_count}
Defect Density:        {defect_density} defects/cm²
Nuisance Rate:         {nuisance_rate}%
Capture Rate:          {capture_rate}%
Test Duration:         {random.randint(30, 480)} minutes
System Uptime:         {round(random.uniform(96.0, 100.0), 1)}%

Result Classification: {status}

{'─'*80}
7. OBSERVATIONS AND FINDINGS
{'─'*80}

During the execution of this test case, the following observations were noted:

a) The {product_line} demonstrated {"excellent" if status == "PASS" else "acceptable" if status == "CONDITIONAL PASS" else "below-target"} performance
   in detecting {defect_type} at the {tech_node} node.

b) {"The capture rate exceeded the minimum threshold, confirming system readiness." if capture_rate > 90 else "The capture rate requires optimization of the detection algorithm."}

c) {"Nuisance rate is within acceptable limits." if nuisance_rate < 5 else "Nuisance rate exceeds the target threshold; recipe tuning is recommended."}

d) {random.choice([
    "No significant drift was observed during the test duration.",
    "Minor calibration drift was detected after extended run; re-calibration resolved the issue.",
    "Edge-zone defect detection showed improved performance compared to previous revision.",
    "Cross-correlation with the reference SEM confirmed classification accuracy.",
    "Throughput metrics met production requirements without sensitivity compromise.",
])}

e) {random.choice([
    "The system successfully integrated with the factory automation host.",
    "SECS/GEM communication was verified with zero packet loss during data transfer.",
    "Recipe portability between systems at this fab was confirmed.",
    "Statistical process control charts showed stable performance over the test period.",
    "The defect review station correlation was within specification.",
])}

{'─'*80}
8. CORRECTIVE ACTIONS (if applicable)
{'─'*80}

{f"No corrective actions required. Test passed all acceptance criteria." if status == "PASS" else f"""
The following corrective actions are recommended:

1. {"Re-tune detection algorithm thresholds for " + defect_type + " at " + tech_node + " node." if status == "FAIL" else "Review edge-zone detection parameters for optimization."}
2. {"Schedule follow-up test after recipe optimization." if status != "PASS" else "N/A"}
3. {"Escalate to R&D for algorithm enhancement if re-tuning does not resolve sensitivity gap." if status == "FAIL" else "Monitor performance over next 30 production days."}
"""}

{'─'*80}
9. SIGN-OFF
{'─'*80}

Author:     {engineer:<30s} Date: {modified_date.strftime('%Y-%m-%d')}
Reviewer:   {reviewer:<30s} Date: {(modified_date + timedelta(days=random.randint(1, 7))).strftime('%Y-%m-%d')}
Approver:   {"Dr. " + random.choice(["Richard Lee", "Susan Park", "Hans Schmidt", "Kenji Watanabe"]):<30s} Date: {(modified_date + timedelta(days=random.randint(3, 14))).strftime('%Y-%m-%d')}

{'='*80}
END OF DOCUMENT - {doc_number}
{'='*80}
"""
    return doc_number, document


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print(f"Generating 100 engineering test case documents in: {DATA_DIR}")
    manifest = []

    for i in range(1, 101):
        doc_number, content = generate_document(i)
        filename = f"{doc_number}.txt"
        filepath = os.path.join(DATA_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        manifest.append({"id": i, "document_number": doc_number, "filename": filename})
        print(f"  Generated: {filename}")

    # Write manifest
    manifest_path = os.path.join(DATA_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nSuccessfully generated 100 documents and manifest.json in {DATA_DIR}")


if __name__ == "__main__":
    main()
