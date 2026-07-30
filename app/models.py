"""
models.py — the SHAPES of data going in and out of our API (Pydantic schemas).

WHY THIS FILE EXISTS:
    FastAPI uses these classes to:
      1. VALIDATE incoming JSON automatically (bad input -> a clean 422 error,
         never a crash deep inside our agent),
      2. DOCUMENT the API (they become the interactive Swagger docs at /docs),
      3. SERIALIZE our responses consistently.

    Free validation + free docs from one class definition. That's why FastAPI is
    the standard choice for Python AI backends.
"""

from pydantic import BaseModel, Field


class SolveRequest(BaseModel):
    """What the client sends to solve an issue."""
    issue_number: int = Field(
        description="The GitHub issue number to solve",
        examples=[42],
    )


class SolveResponse(BaseModel):
    """The finished result of a solve."""
    issue_number: int
    summary: str
    is_bug: bool
    target_file: str
    explanation: str
    fixed_code: str
    approved: bool
    attempts: int
    pr_result: str


class JobCreated(BaseModel):
    """Returned immediately when a background solve is queued."""
    job_id: str
    status: str = "queued"
    message: str = "Poll GET /jobs/{job_id} for the result."


class JobStatus(BaseModel):
    """The state of a background job."""
    job_id: str
    status: str                      # queued | running | done | error
    result: SolveResponse | None = None
    error: str | None = None
