from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List
from docx import Document as WordDoc
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from io import BytesIO
import openai
import os
import asyncio
import re
import json
from pathlib import Path
from fastapi import Request
from fastapi.responses import JSONResponse
import datetime

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://merilmoretolife.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Data Models ---
class DeviceRequest(BaseModel):
    deviceName: str
    intendedUse: str
    sections: list[str]

class FinalizedDevice(BaseModel):
    deviceName: str
    intendedUse: str
    designInputHtml: str
    finalizedBy: str
    diComplete: bool
    doComplete: bool
    finalizedAt: str
    sections: list[str]  # ✅ Add this line

class DesignOutputRequest(BaseModel):
    deviceName: str
    intendedUse: str
    section: str

class UpdateRequest(BaseModel):
    deviceName: str
    intendedUse: str
    section: str
    currentContent: str
    remark: str

# --- Helpers ---
def insert_page_number(paragraph):
    run = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = 'PAGE'
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'separate')
    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'end')
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)

def generate_prompt(device_name: str, intended_use: str, section: str) -> str:
    intro = f"Generate design input content for the medical device '{device_name}', intended for '{intended_use}', under the section: '{section}'. Please follow the specified format, adjust details as per the device type and Use globally accepted medtech regulatory language.\n\n"

    instructions = {
        "Functional and Performance Requirements": f"""
Include the following:
1. Material of Construction – List main materials and cite relevant ASTM/ISO standards based on the device type.
2. Component Design and Dimension – Define critical design features and tolerances.
3. Mechanical Properties and tests with relevant/applicable USP/ISO/ASTM,etc. standards.
Tailor content based on whether the device is an implant, instrument, or external device.
""",

        "Biological and Safety Requirements": f"""
Include:
1. Raw Material Compatibility – Mention inertness, sterilization tolerance, and chemical compatibility.
2. Biological Safety – Address cytotoxicity, irritation, sensitization, systemic effects.
3. Biocompatibility Tests Required – Based on ISO 10993-1 and contact duration, list applicable tests from ISO 10993 series and USP <87>/<88>.
4. Applicable Standards – List ISO 10993-1 and USP references only here.
Base all content on the nature, location, and duration of contact.
""",

        "Labeling and IFU Requirements": f"""
Include:
1. Label Information – List key product identifiers (name, code, lot, expiry, symbols).
2. Labeling Standards – Mention EN ISO 15223-1, EN ISO 20417, 21 CFR 801.109, ISO 14630.
3. IFU and e-IFU Requirements – Include indication, warnings, usage, multilingual needs, and digital/e-IFU compliance under EU Regulation 207/2012.
Tailor label/IFU fields based on region and class.
""",

        "Sterilization Requirements": f"""
Include:
1. Sterilization Method – Recommend EO, Steam, Gamma, or others based on material.
2. Applicable Standards – ISO 11135, ISO 11137, ISO 17665, ISO 10993-7, ISO 11737-1/2, USP <71>, <85>, <61>.
3. Required Tests – Bioburden, SAL 10⁻⁶, residuals, endotoxins, seal integrity.
Ensure compatibility with device sensitivity and configuration.
""",

        "Stability / Shelf Life Requirements": f"""
Include:
1. Shelf Life Objective – Specify target duration based on comparable products.
2. Factors Impacting Stability – Temperature, humidity, UV exposure, packaging.
3. Stability Study – Real-time and accelerated aging (ASTM F1980), post-aging validation.
4. Applicable Standards – ASTM F1980, ISO 11607-1, ICH Q1A(R2).
""",

        "Packaging and Shipping Requirements": f"""
Include:
1. Packaging Objectives – Protect from light, moisture, contamination, damage, maintain sterility.
2. Packaging Materials – Detail materials used (Tyvek, foil, blister), and barrier properties.
3. Packaging Configuration – Describe primary, secondary, tertiary setup and inclusion of IFU.
4. Standards – EN ISO 11607-1/2, ASTM F88.
Adjust for product fragility, sterility, and logistics.
""",

        "Manufacturing Requirements": f"""
Include:
1. Facility Infrastructure – GMP design: epoxy flooring, HEPA filters, material finishes.
2. Cleanroom Classification – ISO Class 8 or better depending on operation.
3. Equipment and Sanitation – GMP-compliant equipment, cleaning protocols.
4. QC and Storage – Environmental control, microbiology lab, USP testing capability.
Standards: ISO 13485, 21 CFR Part 820.
""",

        "Statutory and Regulatory Requirements": f"""
Include:
1. Indian Regulatory – CDSCO rules, classification (A–D), MD-13, MD-9, ISO 13485.
2. EU Regulatory – CE Marking, Detailed EU MDR classification (Class and Rule) from https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32017R0745, GSPR, Technical File, ISO 13485.
3. US FDA – Class I/II/III, 510(k)/PMA, QSR (21 CFR Part 820), Establishment Registration.
Tailor classification and pathways based on device use and risk.
"""
    }

    return intro + instructions.get(section, "Provide general content.")

def generate_do_prompt(device_name: str, intended_use: str, section: str) -> str:
    if section == "Functional and Performance Requirements":
        return f"""
Generate the Design Output for a medical device called '{device_name}', intended for '{intended_use}', under the section: 'Functional and Performance Requirements'.

Include the following clearly, using clean formatting and tables where applicable:

1. Material of Construction:
- Specify exact materials, and cite relevant ISO/ASTM standards used for material validation in reference to its design input.

2. Component Design and Dimension:
- Define dimensional requirements and allowable tolerances, preferably in table format.
- Highlight size range if applicable.

3. Mechanical Properties:
- Applicable Mechanical Properties and Tests conducted and expected limits or acceptance criteria.
- Mention applicable standards - USP/ISO/ASTM.

Consider Design Input for giving Output Results.
Base the output on relevant real standards like USP, ISO, ASTM. Include tables with actual parameter ranges (e.g., tensile strength by USP size). Avoid generalizations.
"""

    elif section == "Biological and Safety Requirements":
        return f"""
Generate the Design Output for a medical device called '{device_name}', intended for '{intended_use}', under the section: 'Biological and Safety Requirements'.

Only include one subsection:

## 1. Biocompatibility Tests Requirements

- Inject this statement every time before table: "Based on the nature and duration of body contact, following is the list of all required biocompatibility tests as per ISO 10993-1."
- Format the information as a markdown table with the following columns:

| Sr. No. | Standard Reference | Study Name | Study No. |
|---------|--------------------|------------|-----------|

- Include standard numbers (e.g., ISO 10993-5:2009, USP <87>, USP <88>, etc...).
- Leave the "Study No." column blank.
- Do not include any notes or extra text outside the table.
"""

    elif section == "Packaging and Shipping Requirements":
        return f"""
Generate the Design Output for a medical device called '{device_name}', intended for '{intended_use}', under the section: 'Packaging and Shipping Requirements'.

Include a clear, product-specific packaging configuration (e.g., for surgical sutures). Mention:

1. Primary Packaging: e.g., suture wound in 8-shape, in paper/plastic tray, etc.
2. Secondary Packaging: pouch (e.g., aluminum), and box with IFU.
3. Sterility Maintenance: mention compatibility with sterilization and shelf life.
4. Qualification Tests: include the table below based on ASTM and USP standards.
5. Transportation Tests: include all relevant ASTM and IS references.

### Packaging Qualification Tests

| Parameter        | Acceptance Criteria  |
|------------------|----------------------|
| Seal Strength    | ≥ 2N                 |
| Seal Width       | ≥ 5mm                |
| Seal Integrity   | No Leakage           |
| Sterility        | USP <71>             |

### Transportation Tests

Mention the following:
- ASTM D4169-16: Performance Testing of Shipping Containers and Systems
- ASTM D5276: Drop Test of Loaded Containers by Free Fall
- ASTM D999: Vibration Testing of Shipping Containers
- IS 7028-4: Vertical Impact Drop Test
- IS 7028-2: Vibration Test at Fixed Low Frequency

The packaging configuration must ensure maintenance of sterility, physical integrity, and resistance during transport.
"""

    elif section == "Labeling and IFU Requirements":
        return f"""
Generate the Design Output for the section 'Labeling and IFU Requirements' for the device '{device_name}', intended for '{intended_use}'.

This section must include label content, relevant labeling standards, and what will be included in the IFU or e-IFU. Format clearly.
"""

    elif section == "Sterilization Requirements":
        return f"""
Generate the Design Output for the section 'Sterilization Requirements' for the device '{device_name}', intended for '{intended_use}'.

Mention sterilization method (EO, gamma, steam, etc.), validation approach, applicable standards (ISO 11135, ISO 11137, USP <71>, <85>), and test protocols.
"""

    elif section == "Stability / Shelf Life Requirements":
        return f"""
Generate the Design Output for the section 'Stability / Shelf Life Requirements' for the device '{device_name}', intended for '{intended_use}'.

Include aging studies (real-time and accelerated), packaging integrity over time, and applicable standards like ASTM F1980.
"""

    elif section == "Manufacturing Requirements":
        return f"""
Generate the Design Output for the section 'Manufacturing Requirements' for the device '{device_name}', intended for '{intended_use}'.

List facility requirements (GMP, ISO Class 8), cleanroom specs, QC infrastructure, and validation of processes and equipment.
"""

    elif section == "Statutory and Regulatory Requirements":
        return f"""
Generate the Design Output for the section 'Statutory and Regulatory Requirements' for the device '{device_name}', intended for '{intended_use}'.

Summarize applicable regulatory pathways (CDSCO, EU MDR, US FDA), classification, and conformance to ISO 13485, 21 CFR Part 820, GSPR, etc.
"""

    else:
        return f"Generate appropriate Design Output content for section: '{section}' for a device named '{device_name}' with intended use '{intended_use}'."

# --- /generate Design Input ---
@app.post("/generate")
async def generate_response(data: DeviceRequest):
    outputs = {}
    for section in data.sections:
        prompt = generate_prompt(data.deviceName, data.intendedUse, section)
        completion = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        outputs[section] = completion.choices[0].message.content.strip()

    return {"results": outputs}

@app.post("/generate-docx")
async def generate_word(data: DeviceRequest):
    doc = WordDoc()

    # Set font globally
    style = doc.styles['Normal']
    style.font.name = 'Helvetica'
    style.font.size = Pt(12)

    section = doc.sections[0]

    # Header
    header = section.header
    header_table = header.add_table(rows=1, cols=3, width=Inches(7.5))
    header_table.autofit = False
    header_table.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    header_table.columns[0].width = Inches(2)
    header_table.columns[1].width = Inches(3.5)
    header_table.columns[2].width = Inches(2)

    # Logo
    logo_cell = header_table.cell(0, 0)
    logo_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    logo_para = logo_cell.paragraphs[0]
    logo_para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    logo_para.add_run().add_picture("meril_logo.jpg", width=Inches(1.1))

    # Title
    center_cell = header_table.cell(0, 1)
    center_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    center_para = center_cell.paragraphs[0]
    center_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = center_para.add_run("Design Input")
    run.bold = True
    run.font.size = Pt(17)
    run.font.name = 'Helvetica'

    # Doc Number
    right_cell = header_table.cell(0, 2)
    right_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    right_para = right_cell.paragraphs[0]
    right_para.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    run = right_para.add_run(f"Document Number: DI/{data.deviceName[:3].upper()}/001\nRev. 00")
    run.font.size = Pt(11)
    run.font.name = 'Helvetica'

    # Line under header
    header_line = header.add_paragraph()
    header_line_format = header_line.paragraph_format
    header_line_format.space_before = Pt(2)
    header_line_format.space_after = Pt(2)
    hr = header_line.add_run("―" * 54)
    hr.font.name = 'Helvetica'
    hr.font.size = Pt(8)

    # Footer
    footer = section.footer
    footer_line = footer.add_paragraph()
    footer_line.add_run("―" * 54).font.size = Pt(8)
    footer_line.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    footer_paragraph = footer.add_paragraph()
    footer_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = footer_paragraph.add_run("Meril Healthcare Pvt. Ltd.\nConfidential Document - Page ")
    run.font.size = Pt(10)
    run.font.name = 'Helvetica'
    insert_page_number(footer_paragraph)

    # First page: title (no excessive spacing)
    doc.add_paragraph()
    for _ in range(6): doc.add_paragraph()
    title_para = doc.add_paragraph()
    title_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = title_para.add_run(f"Design Input – {data.deviceName}")
    run.bold = True
    run.font.size = Pt(23)
    run.font.name = 'Helvetica'

    # TOC on page 2
    doc.add_page_break()
    doc.add_heading("Table of Contents", level=1)
    numbered_sections = [f"{i+1}. {title}" for i, title in enumerate(data.sections)]
    for sec in numbered_sections:
        para = doc.add_paragraph(sec)
        para.style.font.name = 'Helvetica'
        para.paragraph_format.space_after = Pt(4)

    # Prompts
    prompts = [(section, generate_prompt(data.deviceName, data.intendedUse, section)) for section in data.sections]

    async def fetch(section, prompt):
        try:
            response = await asyncio.wait_for(
                openai.ChatCompletion.acreate(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5
                ),
                timeout=30
            )
            raw = response.choices[0].message.content.strip()
            cleaned = re.sub(r"[\*\#]+", "", raw)
            cleaned = re.sub(r"\n(?=\d+\.)", "\n", cleaned)

            # Parse lines and bold subsection titles
            lines = cleaned.split("\n")
            formatted = []
            for line in lines:
                match = re.match(r"^(\d+\.\s*)([A-Z].+)", line)
                if match:
                    formatted.append(("bold", match.group(0)))
                else:
                    formatted.append(("normal", line))
            return section, formatted
        except Exception as e:
            return section, [("normal", f"⚠️ Error generating section: {str(e)}")]

    results = await asyncio.gather(*[fetch(s, p) for s, p in prompts])

    # Section content
    for i, (section, lines) in enumerate(results):
        doc.add_page_break()

        heading = doc.add_paragraph()
        heading.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        run = heading.add_run(f"{i+1}. {section}")
        run.bold = True
        run.font.size = Pt(15)
        run.font.name = 'Helvetica'

        for tag, line in lines:
            if not line.strip():
                continue
            if tag == "bold":
                # Add 1 line space before subsection title
                doc.add_paragraph()

            para = doc.add_paragraph()
            para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
            para.paragraph_format.space_after = Pt(0 if tag == "bold" else 8)
            run = para.add_run(line.strip())
            run.font.name = 'Helvetica'
            run.font.size = Pt(12)
            if tag == "bold":
                run.bold = True

    # Save file
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=Design_Input_{data.deviceName.replace(' ', '_')}.docx"
        }
    )

# --- /generate-do (Design Output) ---
@app.post("/generate-do")
async def generate_design_output(data: DesignOutputRequest):
    prompt = generate_do_prompt(data.deviceName, data.intendedUse, data.section)
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return {"result": response.choices[0].message.content.strip()}
    except Exception as e:
        return {"error": str(e)}

# In-memory storage for finalized DI entries
finalized_devices_db = []
DATA_FILE = Path("finalized_data.json")

@app.on_event("startup")
async def load_finalized_data():
    global finalized_devices_db
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            finalized_devices_db = json.load(f)

class FinalizedDevice(BaseModel):
    deviceName: str
    intendedUse: str
    designInputHtml: str
    finalizedBy: str
    diComplete: bool
    doComplete: bool
    finalizedAt: str
    sections: list[str] 


@app.post("/finalize-di")
async def save_finalized_di(data: FinalizedDevice):
    record = data.dict()
    finalized_devices_db.insert(0, record)

    # Save to file
    with open(DATA_FILE, "w") as f:
        json.dump(finalized_devices_db, f, indent=2)

    return {"message": "Saved successfully"}

@app.get("/finalized-devices")
async def get_finalized_devices() -> List[FinalizedDevice]:
    return finalized_devices_db

@app.post("/update-section")
async def update_section(data: UpdateRequest):
    prompt = f"""Revise the following Design Input content for the medical device '{data.deviceName}', intended for '{data.intendedUse}', under the section '{data.section}'.

Only make precise updates based on the user remark provided below. Do not rewrite the entire section. Only modify or remove the specific sentence or subsection as per the remark. Maintain the original structure.

User Remark:
{data.remark}

Current Section Content:
{data.currentContent}
"""
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return {"result": response.choices[0].message.content.strip()}
    except Exception as e:
        return {"error": str(e)}

@app.post("/regenerate-section")
async def regenerate_with_remark(data: DesignOutputRequest, remark: str = ""):
    base_prompt = generate_do_prompt(data.deviceName, data.intendedUse, data.section)
    if remark:
        base_prompt += f"\n\nUser Remark: {remark}\nPlease revise the content accordingly, keeping the structure intact."
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=[{"role": "user", "content": base_prompt}],
            temperature=0.4
        )
        return {"result": response.choices[0].message.content.strip()}
    except Exception as e:
        return {"error": str(e)}
