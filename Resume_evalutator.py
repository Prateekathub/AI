
#Setting up the LLM

import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from pydantic import BaseModel, Field
from pathlib import Path
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


load_dotenv()

hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    raise ValueError("HF_TOKEN was not found. Check your .env file.")

client = InferenceClient(
    model="Qwen/Qwen3-32B",
    token=hf_token,
)

# Sample job description
job_description = """
Software Engineer

Responsibilities:
- Build clean, scalable, reusable software.
- Work with developers and product owners to understand requirements.
- Contribute to design, implementation, automated testing, and delivery.
- Follow engineering practices such as code reviews and unit testing.

Qualifications:
- Proficiency in at least one programming language, such as Python, Java, or JavaScript.
- Ability to learn additional languages and tools.
- Interest in building reliable cloud software.
"""


# Define the JSON structure we want from the model
class JobDescription(BaseModel):
    job_title: str
    responsibilities: list[str]
    required_skills: list[str]
    preferred_skills: list[str] = Field(default_factory=list)
    qualifications: list[str]


system_message = """
You are an expert HR analyst.
Extract information from the job description accurately.
Use only information stated in the description; do not invent requirements.
Return the result in the requested JSON format.
"""

user_message = f"""
Convert the following job description into the required structured format.

Job description:
{job_description}
"""


response = client.chat_completion(
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "job_description",
            "schema": JobDescription.model_json_schema(),
        },
    }
)
#Resume Parse

class Experience(BaseModel):
    company: str | None = None
    role: str | None = None
    duration: str | None = None
    description: str | None = None
    skills_used: list[str] = []


class Resume(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    total_experience_years: float | None = None

    skills: list[str] = []
    experiences: list[Experience] = []
    education: list[str] = []
    projects: list[str] = []
    certifications: list[str] = []

resume_system_message = """
You are an expert HR analyst. Extract the candidate's information from the resume.
Use only information stated in the resume. Do not infer or invent details.
If a field is missing, use null for optional fields and an empty list for list fields.
Return data matching the provided JSON schema.
"""

resume_user_message = f"""
Extract structured information from this resume:

"""
resume_text = """
Jordan Lee
Software Engineer

Skills: Python, Java, SQL
Experience: Built and maintained web applications using Python.
Education: B.S. in Computer Science
"""

resume_response = client.chat_completion(
    messages=[
        {"role": "system", "content": resume_system_message},
        {"role": "user", "content": resume_user_message},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "resume",
            "schema": Resume.model_json_schema(),
        },
    }
)

parsed_resume = Resume.model_validate_json(
resume_response.choices[0].message.content
)
raw_json = resume_response.choices[0].message.content


def read_pdf(file_path: str | Path) -> str:
    """Extract text from a PDF file."""
    reader = PdfReader(str(file_path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        pages.append(f"--- Page {page_number} ---\n{page_text}")

    return "\n\n".join(pages)


def read_docx(file_path: str | Path) -> str:
    """Extract DOCX paragraphs and tables in document order."""
    document = Document(str(file_path))
    sections = []

    for item in document.element.body.iterchildren():
        if item.tag.endswith("}p"):
            paragraph = Paragraph(item, document)
            text = paragraph.text.strip()
            if text:
                sections.append(text)

        elif item.tag.endswith("}tbl"):
            table = Table(item, document)
            table_rows = []

            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                table_rows.append(" | ".join(cells))

            if table_rows:
                sections.append("[Table]\n" + "\n".join(table_rows))

    return "\n\n".join(sections)


def read_resume(file_path: str | Path) -> str:
    """Choose the reader based on the file extension."""
    file_path = Path(file_path)
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return read_pdf(file_path)
    elif extension == ".docx":
        return read_docx(file_path)
    else:
        raise ValueError(
            f"Unsupported file type: {extension}. Please provide a PDF or DOCX file."
        )


from pathlib import Path
import time


# Parse the job description into the JobDescription Pydantic model
job_response = client.chat_completion(
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "job_description",
            "schema": JobDescription.model_json_schema(),
        },
    },
    max_tokens=1000,
)

job = JobDescription.model_validate_json(
    job_response.choices[0].message.content
)


from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    score: float
    details: list[str] = Field(default_factory=list)


def parse_resume(resume_text: str) -> Resume:
    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert HR analyst. Extract only information "
                    "stated in the resume. Do not invent missing details. "
                    "Return data matching the JSON schema."
                ),
            },
            {
                "role": "user",
                "content": f"Extract structured information from this resume:\n\n{resume_text}",
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "resume",
                "schema": Resume.model_json_schema(),
            },
        },
        max_tokens=1500,
    )

    return Resume.model_validate_json(response.choices[0].message.content)


def final_score(job: JobDescription, resume: Resume) -> MatchResult:
    response = client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an evidence-based resume evaluator. Compare the "
                    "resume with the job description. Do not invent qualifications. "
                    "Return a score from 0 to 100 and explain matches and gaps "
                    "in the JSON schema format."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Job description:\n{job.model_dump_json(indent=2)}\n\n"
                    f"Resume:\n{resume.model_dump_json(indent=2)}"
                ),
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "match_result",
                "schema": MatchResult.model_json_schema(),
            },
        },
        max_tokens=800,
    )

    return MatchResult.model_validate_json(response.choices[0].message.content)
# Read, parse, and score each resume in the resumes folder
resume_folder = Path("resumes")
all_results = []

for file_path in resume_folder.iterdir():
    if not file_path.is_file():
        continue

    if file_path.suffix.lower() not in [".pdf", ".docx"]:
        continue

    print(f"\nProcessing: {file_path.name}")

    resume_text = read_resume(file_path)
    parsed_resume = parse_resume(resume_text)

    # Optional pause between model requests
    time.sleep(5)

    result = final_score(job, parsed_resume)
    print("Score:", result.score)

    all_results.append({
        "name": parsed_resume.name,
        "score": result.score,
        "details": result.details,
    })


# Sort highest scores first
all_results.sort(
    key=lambda candidate: candidate["score"],
    reverse=True,
)

for candidate in all_results:
    print(candidate)
