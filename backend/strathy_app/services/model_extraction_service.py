import os
import json
import anthropic

# Initialize Anthropic client (make sure ANTHROPIC_API_KEY env var is set)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an intelligent extraction model for university admission data.

Your goal is to analyze a student's email or message and extract the following structured fields:

- full_name: The student's full name.
- admission_number: The student's admission number if mentioned (examples: "148705", "156443", "BBIT/00432/23"). If not present, return "".
- course: The course code or name (e.g., "BBIT" or "Bachelor of Business Information Technology"). If not present, return "".
- year: The academic year as a single digit string (e.g., "1", "2", "3", "4"). If not present, return "".
- semester: The semester number as a single digit string (e.g., "1" or "2"). If not present, return "".
- year_semester: Combined representation "year.semester" (e.g., "4.2"). If either year or semester is missing, return "".
- group: The group or section (e.g., "A", "B", "C", "D", "E"). If not present, return "".
- full_thread_summary: If this email is part of a longer thread, write a 2–4 sentence summary capturing the full context or purpose of the conversation so far.
- details_status: One of "complete", "partial", or "empty". "complete" means full_name, admission_number, course, year, semester and group are all present. "partial" if at least one field found but not all. "empty" if none of the main fields found.
- missing_fields: A JSON array listing the missing main fields from: ["full_name","admission_number","course","year","semester","group"].
- follow_up_message: If status is "partial" or "empty", produce a short polite message to request the missing fields from the student. If status is "complete", return an empty string.

Rules:
- Return ONLY a valid JSON object, and use those exact keys and types.
- Keep values as strings (use "" for missing).
- For year and semester try to normalize numeric forms. For example:
  - "year 4 semester 2" -> "year": "4", "semester": "2", "year_semester": "4.2"
  - "4.2", "4/2", "4-2" in the text should map to year "4" semester "2" and year_semester "4.2".
- Admission numbers can be numeric-only (6 digits). Return as-is.
- If the model is unsure about a value, leave it empty ("") and include it in missing_fields.
- Do not include any commentary — only the JSON.

Example output:
{
  "full_name": "John Mwangi",
  "admission_number": "148705",
  "course": "BBIT",
  "year": "4",
  "semester": "2",
  "year_semester": "4.2",
  "group": "B",
  "full_thread_summary": "Student has been discussing project submission deadlines and timetable updates over several messages.",
  "details_status": "partial",
  "missing_fields": ["admission_number"],
  "follow_up_message": "Hi John, could you please share your admission number so we can assist you better?"
}
"""

def extract_student_details(email_body: str) -> dict:
    """
    Send the email text to Anthropic and return structured JSON (with semester, message_summary, and full_thread_summary).
    """
    response = client.messages.create(
        model="claude-3-5-sonnet-latest",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": email_body}],
        max_tokens=3000,
        temperature=0
    )

    # Safely parse model response (expecting pure JSON text)
    content = response.content[0].text.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {"error": "Invalid JSON returned from model", "raw": content}

    # Fallback: If full_thread_summary is missing, reuse message_summary
    if "full_thread_summary" not in data or not data.get("full_thread_summary"):
        data["full_thread_summary"] = data.get("message_summary", "")

    return data
