import sys
import time
import subprocess
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# This defines what the incoming data should look like
class CodePayload(BaseModel):
    code: str

@app.post("/execute")
def execute_code(payload: CodePayload):
    start_time = time.perf_counter()
    try:
        # Run the code safely in a separate process
        process = subprocess.run(
            [sys.executable, "-c", payload.code],
            capture_output=True,
            text=True,
            timeout=30 # Stop if it takes longer than 10 seconds
        )
        elapsed_time = time.perf_counter() - start_time
        return {
            "stdout": process.stdout,
            "stderr": process.stderr,
            "execution_time_seconds": round(elapsed_time, 4)
        }
    except Exception as e:
        return {"stderr": str(e), "stdout": ""}

if __name__ == "__main__":
    # Start the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)