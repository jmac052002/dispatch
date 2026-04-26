import hashlib
import hmac 
import os 
from fastapi import FastAPI, Request, HTTPException, Header
from mangum import Mangum 
from dotenv import load_dotenv 

load_dotenv()

app = FastAPI() 
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "") 

def validate_signature(payload: bytes, signature_header: str) -> bool: 
    if not signature_header: 
        return False 
    
    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    expected_header = f"sha256={expected}"

    return hmac.compare_digest(expected_header, signature_header) 

@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default=None)
):
    payload = await request.body()

    if not validate_signature(payload, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()
    workflow_run = event.get("workflow_run", {})

    if workflow_run.get("conclusion") == "failure":
        repo = event.get("repository", {}).get("full_name", "unknown")
        workflow = workflow_run.get("name", "unknown")
        print(f"Triage triggered — repo: {repo}, workflow: {workflow}")

    return {"status": "received"}

handler = Mangum(app)