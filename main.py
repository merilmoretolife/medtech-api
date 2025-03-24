from fastapi import FastAPI
from pydantic import BaseModel
import openai
import os

app = FastAPI()
@app.get("/")
def read_root():
    return {"message": "MedTech API is running. Use POST /generate with a deviceName."}

openai.api_key = os.getenv("OPENAI_API_KEY")

class DeviceInput(BaseModel):
    deviceName: str

@app.post("/generate")
async def generate(input: DeviceInput):
    prompt = f"""
You are a regulatory affairs assistant generating structured design input documentation for medical devices.

For the generic device: "{input.deviceName}"

Provide only the "Functional and Performance Requirements" section of the design input using the following format:

1. Material of Construction:
- [Materials and standards]

2. Component Design and Dimension:
- [Design & ASTM/ISO standards]

3. Wear Characteristics:
- [Testing like ISO 14243]

4. Fatigue Properties:
- [Expected load, testing standards]
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return {"result": response["choices"][0]["message"]["content"]}
