# main.py (Fully Updated)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os

from fastapi.responses import StreamingResponse
from docx import Document as WordDoc
from docx.shared import Inches
from io import BytesIO
import datetime

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")

class DeviceRequest(BaseModel):
    deviceName: str
    sections: list[str]

def generate_prompt(device_name: str, section: str) -> str:
    intro = f"Generate design input content for the medical device '{device_name}', under the section: '{section}'. Please follow the specified format and adjust details as per the device type.\n\n"

    instructions = {
        "Functional and Performance Requirements": f"""
Include the following:
1. Material of Construction – List main materials and cite relevant ASTM/ISO standards based on the device type.
2. Component Design and Dimension – Define critical design features and tolerances.
3. Wear Characteristics – Specify wear resistance needs and applicable tests.
4. Fatigue Properties – Detail expected cyclic loads and fatigue test protocols.
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

@app.post("/generate-docx")
async def generate_word(data: DeviceRequest):
    doc = WordDoc()

    # Title and metadata
    doc.add_heading(f"Design Input – {data.deviceName}", level=1)
    doc.add_paragraph(f"Document Number: DI/{data.deviceName[:3].upper()}/001 Rev. 00")
    doc.add_paragraph(f"Date: {str(datetime.date.today())}")

    # Prepare prompts for all sections
    prompts = [
        (section, generate_prompt(data.deviceName, section))
        for section in data.sections
    ]

    # Define async function to call OpenAI
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
            return section, response.choices[0].message.content.strip()
        except Exception as e:
            return section, f"⚠️ Error generating section: {str(e)}"

    # Run all requests in parallel
    results = await asyncio.gather(*[fetch(s, p) for s, p in prompts])

    # Add each section to Word doc
    for section, content in results:
        doc.add_page_break()
        doc.add_heading(section, level=2)
        doc.add_paragraph(content)

    # Final footer
    doc.add_page_break()
    doc.add_paragraph("Confidential Document – Meril Healthcare Pvt. Ltd.")

    # Prepare .docx file for download
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
