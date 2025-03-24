from fastapi import FastAPI
from pydantic import BaseModel
import openai
import os

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

class DeviceInput(BaseModel):
    deviceName: str

# Home route (optional)
@app.get("/")
def read_root():
    return {"message": "MedTech API is running. Use POST /generate or /biological."}

# Functional and Performance Requirements
@app.post("/generate")
async def generate(input: DeviceInput):
    prompt = f"""
You are a regulatory affairs assistant generating structured design input documentation for medical devices.

For the generic device: "{input.deviceName}"

Provide only the "Functional and Performance Requirements" section of the design input using the following format:

1. Material of Construction:
- [Material types, applicable standards like ASTM F75-07, F648-07, etc.]

2. Component Design and Dimension:
- [Dimensional specs, tolerances, and associated standards like ASTM F2083, ISO]

3. Wear Characteristics:
- [Expected wear behavior, wear test requirement (e.g. ISO 14243)]

4. Fatigue Properties:
- [Expected loading and fatigue cycles, methods of evaluation, applicable testing standards]

Do not generate any other content.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"result": response["choices"][0]["message"]["content"]}

# Biological and Safety Requirements
@app.post("/biological")
async def biological(input: DeviceInput):
    prompt = f"""
You are a regulatory affairs assistant generating structured design input documentation for medical devices in accordance with ISO 13485, ISO 10993, EU MDR, and US FDA guidelines.

For the generic device: "{input.deviceName}"

Provide only the "Biological and Safety Requirements" section using this format:

1. Raw Material Compatibility:
- [Describe if raw materials are biologically acceptable, inert, and safe]
- [Mention container interaction, if relevant]

2. Biological Safety:
- No tissue toxicity
- No skin irritation or microbial response
- No intracutaneous reactivity
- Resistance to infection

3. Biocompatibility Tests Required:
- Cytotoxicity
- Sensitization
- Intracutaneous Reactivity
- Systemic Toxicity
- [Add based on device nature, e.g., implantation, degradation]

4. Applicable Standards:
- ISO 10993-1, -5, -10, etc.
- USP <88>, EP (if applicable)

Do not generate unrelated text. Keep structure exact.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"result": response["choices"][0]["message"]["content"]}
