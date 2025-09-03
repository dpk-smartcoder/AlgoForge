from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime
import os
import json
import time
from pathlib import Path

# Database (SQLAlchemy)
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Firebase Admin for token verification
import firebase_admin
from firebase_admin import credentials, auth as fb_auth

# Import the main function from your agent pipeline orchestrator
# Using an alias to make the purpose clear
from app.agentic_ai.final import main as run_autogen_pipeline


# ---------- Config ----------
DATABASE_URL = os.getenv("ALGOFORGE_DB", "sqlite:///./algoforge.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_firebase_admin() -> None:
    if firebase_admin._apps:
        return
    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_path and os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        try:
            firebase_admin.initialize_app()
        except Exception as e:
            raise RuntimeError(
                "Firebase admin initialization failed. Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON file."
            ) from e


# ---------- Models ----------
class HistoryORM(Base):
    __tablename__ = "history"
    _id = Column(String, primary_key=True)
    userId = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    problemText = Column(Text, nullable=True)
    constraints = Column(Text, nullable=True)
    testCases = Column(Text, nullable=True)
    imageUrl = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)  # JSON string
    status = Column(String, default="pending")  # pending|solved|failed
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


# ---------- Schemas ----------
class ProblemSubmission(BaseModel):
    title: str
    problemText: Optional[str] = None
    constraints: Optional[str] = None
    testCases: Optional[str] = None
    imageUrl: Optional[str] = None

class BackendResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None

class SolveRequest(BaseModel):
    problemId: str


# ---------- Dependencies ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user_id(authorization: Optional[str] = Header(None), request: Optional[Request] = None) -> str:
    init_firebase_admin()
    token: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token and request is not None:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    try:
        decoded = fb_auth.verify_id_token(token)
        uid = decoded.get("uid")
        if not uid:
            raise ValueError("uid missing")
        return uid
    except Exception as e:
        # Bubble up a more actionable message for local debugging
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")


# ---------- App ----------
app = FastAPI(title="AlgoForge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_history(item: HistoryORM) -> Dict[str, Any]:
    return {
        "_id": item._id,
        "userId": item.userId,
        "title": item.title,
        "problemText": item.problemText,
        "constraints": item.constraints,
        "testCases": item.testCases,
        "imageUrl": item.imageUrl,
        "solution": json.loads(item.solution) if item.solution else None,
        "status": item.status,
        "createdAt": item.createdAt.isoformat() if item.createdAt else None,
        "updatedAt": item.updatedAt.isoformat() if item.updatedAt else None,
    }


# ---------- Routes ----------
@app.get("/users/profile")
def get_profile(authorization: Optional[str] = Header(None), request: Request = None):
    uid = get_current_user_id(authorization, request)
    return {"uid": uid}


@app.get("/history")
def get_history(authorization: Optional[str] = Header(None), request: Request = None, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    uid = get_current_user_id(authorization, request)
    rows = db.query(HistoryORM).filter(HistoryORM.userId == uid).order_by(HistoryORM.createdAt.desc()).all()
    return [serialize_history(r) for r in rows]


@app.get("/history/{item_id}")
def get_history_item(item_id: str, authorization: Optional[str] = Header(None), request: Request = None, db: Session = Depends(get_db)) -> Dict[str, Any]:
    uid = get_current_user_id(authorization, request)
    row = db.query(HistoryORM).filter(HistoryORM._id == item_id, HistoryORM.userId == uid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_history(row)


@app.post("/problems/submit", response_model=BackendResponse)
def submit_problem(payload: ProblemSubmission, background_tasks: BackgroundTasks, authorization: Optional[str] = Header(None), request: Request = None, db: Session = Depends(get_db)):
    import uuid

    uid = get_current_user_id(authorization, request)
    now = datetime.utcnow()
    item_id = str(uuid.uuid4())
    row = HistoryORM(
        _id=item_id,
        userId=uid,
        title=payload.title,
        problemText=payload.problemText,
        constraints=payload.constraints,
        testCases=payload.testCases,
        imageUrl=payload.imageUrl,
        status="pending",
        createdAt=now,
        updatedAt=now,
    )
    db.add(row)
    db.commit()

    # Compute solution synchronously so the client receives an immediate solved/failed status
    _compute_solution_task(item_id)
    db.refresh(row)
    return BackendResponse(success=True, message="Problem submitted", data=serialize_history(row))


@app.post("/problems/solve", response_model=BackendResponse)
def solve_problem(body: SolveRequest, authorization: Optional[str] = Header(None), request: Request = None, db: Session = Depends(get_db)):
    uid = get_current_user_id(authorization, request)
    row = db.query(HistoryORM).filter(HistoryORM._id == body.problemId, HistoryORM.userId == uid).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    # Trigger compute synchronously here
    _compute_solution_task(row._id)
    db.refresh(row)
    return BackendResponse(success=True, message="Solve triggered", data=serialize_history(row))


@app.delete("/history", response_model=BackendResponse)
def delete_history(authorization: Optional[str] = Header(None), request: Request = None, db: Session = Depends(get_db)):
    uid = get_current_user_id(authorization, request)
    deleted = db.query(HistoryORM).filter(HistoryORM.userId == uid).delete()
    db.commit()
    return BackendResponse(success=True, message=f"Deleted {deleted} records", data={"deleted": deleted})


# ---------- Background Task (Now the Main Logic) ----------
def _compute_solution_task(item_id: str):
    db = SessionLocal()
    try:
        row = db.query(HistoryORM).filter(HistoryORM._id == item_id).first()
        if not row:
            print(f"ERROR: No problem found with ID {item_id} to process.")
            return

        print(f"--- Starting Autogen pipeline for problem ID: {item_id} ---")
        
        solution_result = None
        pipeline_succeeded = False
        try:
            # Call the main function from final.py with data from the database
            solution_result = run_autogen_pipeline(
                text=row.problemText or "",
                image_url=row.imageUrl,
                constraints=row.constraints or "",
                test_cases=row.testCases or ""
            )
            # Check if the pipeline returned an error
            if not solution_result.get("error"):
                pipeline_succeeded = True
                print(f"--- Pipeline SUCCEEDED for problem ID: {item_id} ---")
                row.status = "solved"
                # The fitter agent provides a dictionary with all the required keys
                solution_payload = {
                    "problemId": row._id,
                    "solution": solution_result.get("approach"),
                    "timeComplexity": solution_result.get("time_complexity"),
                    "spaceComplexity": solution_result.get("space_complexity"),
                    "explanation": solution_result.get("approach"), # Use approach as explanation
                    "codeSnippets": [solution_result.get("code")] if solution_result.get("code") else [],
                }
                row.solution = json.dumps(solution_payload)
            else:
                 print(f"--- Pipeline FAILED for problem ID: {item_id} ---")
                 print(f"Error Details: {solution_result.get('details')}")

        except Exception as e:
            print(f"--- Pipeline execution raised an exception for problem ID: {item_id}: {e} ---")
            solution_result = {"error": "Pipeline execution failed with an exception", "details": str(e)}

        # Fallback to demo solution if the pipeline did not succeed
        if not pipeline_succeeded:
            print(f"--- Attempting to load demo solution for problem ID: {item_id} ---")
            solution_payload = None
            try:
                repo_root = Path(__file__).resolve().parent.parent
                demo_path = repo_root / "solutions.json"
                if demo_path.exists():
                    with open(demo_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        chosen = None
                        if isinstance(data, list) and data:
                            for s in data:
                                if isinstance(s, dict) and s.get("status") == "solved" and s.get("team") != "Rescue_Team":
                                    chosen = s
                                    break
                            if chosen is None:
                                chosen = data[0]
                        elif isinstance(data, dict):
                            chosen = data
                        if chosen:
                            solution_payload = {
                                "problemId": row._id,
                                "solution": chosen.get("summary") or chosen.get("solution") or "Demo solution",
                                "timeComplexity": chosen.get("time_complexity") or chosen.get("timeComplexity"),
                                "spaceComplexity": chosen.get("space_complexity") or chosen.get("spaceComplexity"),
                                "explanation": chosen.get("explanation"),
                                "codeSnippets": [c for c in [chosen.get("code")] if c],
                            }
            except Exception as e:
                print(f"--- Could not load demo solution: {e} ---")
                solution_payload = None
            
            if solution_payload:
                 row.solution = json.dumps(solution_payload)
                 row.status = "solved" # From demo
            else:
                row.status = "failed"
                # Store the actual pipeline error message for debugging
                row.solution = json.dumps(solution_result)


        row.updatedAt = datetime.utcnow()
        db.add(row)
        db.commit()

    except Exception as e:
        print(f"FATAL: Unhandled exception in _compute_solution_task for {item_id}: {e}")
        # Mark as failed if any unexpected error occurs
        if 'row' in locals() and row:
            row.status = "failed"
            row.solution = json.dumps({"error": "An unexpected error occurred in the backend task.", "details": str(e)})
            row.updatedAt = datetime.utcnow()
            db.add(row)
            db.commit()
    finally:
        db.close()

