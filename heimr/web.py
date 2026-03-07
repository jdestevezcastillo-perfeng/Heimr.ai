import os
import shutil
import uuid
import asyncio
import logging
from typing import Optional, Dict
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from heimr.analyzer import Analyzer

# Configuration
UPLOAD_DIR = "data/uploads"
REPORT_DIR = "demos/output"
MAX_CONCURRENT_JOBS = 1
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
MODEL_NAME = os.getenv("LLM_MODEL", "qwen3.5:27b")

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HeimrWeb")

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

app = FastAPI(title="Heimr Cloud API")

# CORS (Allow all for demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job Queue Control
semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
job_store: Dict[str, dict] = {}

class JobStatus(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None
    report_url: Optional[str] = None
    partial_report: Optional[str] = None

from typing import List

async def run_analysis(job_id: str, file_map: Dict[str, str]):
    """
    Background task to run Heimr analysis.
    """
    async with semaphore:
        try:
            job_store[job_id]["status"] = "PROCESSING"
            logger.info(f"Starting analysis for job {job_id}")

            output_path = os.path.join(REPORT_DIR, f"{job_id}.md")
            
            # Configure Analyzer
            config = {
                "llm_url": OLLAMA_URL,
                "llm_model": MODEL_NAME,
            }
            
            # Add observability sources if present
            if 'prometheus' in file_map:
                config['prometheus'] = file_map['prometheus']
            if 'loki' in file_map:
                config['loki'] = file_map['loki']
            if 'tempo' in file_map:
                config['tempo'] = file_map['tempo']

            # Upload to GCS for Fine-Tuning (if configured)
            dataset_bucket = os.getenv("DATASET_BUCKET")
            if dataset_bucket:
                try:
                    from google.cloud import storage
                    storage_client = storage.Client()
                    bucket = storage_client.bucket(dataset_bucket)
                    
                    for key, path in file_map.items():
                        blob_name = f"raw_data/{job_id}/{os.path.basename(path)}"
                        blob = bucket.blob(blob_name)
                        blob.upload_from_filename(path)
                        logger.info(f"Uploaded {path} to gs://{dataset_bucket}/{blob_name}")
                except Exception as e:
                    logger.error(f"Failed to upload to GCS: {e}")

            # Run Analyzer (Synchronously for now, but wrapped in async)
            def _analyze():
                # Determine main file (JTL/LOG)
                main_file = file_map.get('main')
                if not main_file:
                    raise ValueError("No main load test file (jtl/log/csv) found.")
                
                # Setup streaming callback
                def update_progress(chunk):
                    if "partial_report" not in job_store[job_id]:
                        job_store[job_id]["partial_report"] = ""
                    job_store[job_id]["partial_report"] += chunk

                def stream_callback(chunk):
                    loop.call_soon_threadsafe(update_progress, chunk)

                analyzer = Analyzer(
                    file_path=main_file,
                    config=config,
                    llm_url=OLLAMA_URL,
                    llm_model=MODEL_NAME
                )
                
                # Run with streaming
                result = analyzer.analyze(stream_callback=stream_callback)
                
                from heimr.cli import generate_markdown_report_content
                
                # Mock args object for the report generator
                class MockArgs:
                    tag = None
                    prometheus = 'prometheus' in file_map
                    loki = 'loki' in file_map
                    tempo = 'tempo' in file_map
                
                report_content = generate_markdown_report_content(result, MockArgs())
                with open(output_path, "w") as f:
                    f.write(report_content)
                
                # Generate PDF (Server-side)
                try:
                    from heimr.pdf_generator import PDFGenerator
                    pdf_gen = PDFGenerator()
                    pdf_path = output_path.replace('.md', '.pdf')
                    # We render from the Markdown content directly
                    pdf_gen.generate_pdf(report_content, pdf_path)
                    logger.info(f"Generated PDF report: {pdf_path}")
                except Exception as e:
                    logger.error(f"Failed to generate PDF: {e}")

                return result.status

            loop = asyncio.get_event_loop()
            final_status = await loop.run_in_executor(None, _analyze)

            job_store[job_id]["status"] = "COMPLETED"
            job_store[job_id]["message"] = f"Analysis finished with status: {final_status}"
            logger.info(f"Job {job_id} completed.")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job_store[job_id]["status"] = "FAILED"
            job_store[job_id]["message"] = str(e)
        finally:
            # Cleanup Input Files
            for path in file_map.values():
                if os.path.exists(path):
                    os.remove(path)

@app.post("/api/upload", response_model=JobStatus)
async def upload_file(files: List[UploadFile] = File(...), background_tasks: BackgroundTasks = None):
    """
    Upload JTL/LOG file + optional JSONs for analysis.
    """
    job_id = str(uuid.uuid4())
    file_map = {}

    try:
        for file in files:
            filename = file.filename.lower()
            safe_name = f"{job_id}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, safe_name)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Identify file type
            if filename.endswith(('.jtl', '.log', '.csv')):
                file_map['main'] = file_path
            elif 'prometheus' in filename and filename.endswith('.json'):
                file_map['prometheus'] = file_path
            elif 'loki' in filename and filename.endswith('.json'):
                file_map['loki'] = file_path
            elif 'tempo' in filename and filename.endswith('.json'):
                file_map['tempo'] = file_path
            elif filename.endswith('.json'):
                # Fallback: if single unknown json, assume prometheus or ignore? 
                # For safety, let's treat generic jsons as prometheus if not already set, otherwise ignore
                if 'prometheus' not in file_map:
                    file_map['prometheus'] = file_path 
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    if 'main' not in file_map:
        # Cleanup
        for path in file_map.values():
            if os.path.exists(path):
                os.remove(path)
        raise HTTPException(status_code=400, detail="No valid load test file (.jtl, .log, .csv) found in upload.")

    job_store[job_id] = {
        "job_id": job_id,
        "status": "QUEUED",
        "message": "Waiting for worker..."
    }

    background_tasks.add_task(run_analysis, job_id, file_map)

    return JobStatus(job_id=job_id, status="QUEUED")

@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = job_store[job_id]
    response = JobStatus(**job_info)
    
    if job_info["status"] == "COMPLETED":
        response.report_url = f"/api/report/{job_id}"
        
    return response

@app.get("/api/report/{job_id}")
async def get_report(job_id: str):
    report_path = os.path.join(REPORT_DIR, f"{job_id}.md")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_path)

@app.get("/api/report/{job_id}/pdf")
async def get_pdf_report(job_id: str):
    pdf_path = os.path.join(REPORT_DIR, f"{job_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF Report not found")
    return FileResponse(pdf_path, media_type='application/pdf', filename=f"heimr-report-{job_id}.pdf")

@app.get("/health")
async def health():
    return {"status": "ok"}

# Mount Static Files (Must be last to not override API routes)
from fastapi.staticfiles import StaticFiles
# In Docker, WORKDIR is /app, so website is at /app/website
# We check if local or docker path exists
if os.path.exists("website"):
    app.mount("/", StaticFiles(directory="website", html=True), name="static")
elif os.path.exists("/app/website"):
    app.mount("/", StaticFiles(directory="/app/website", html=True), name="static")
else:
    logger.warning("Website directory not found. Static site will not be served.")
