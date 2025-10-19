# import anthropic
# import os
#
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# # Initialize Anthropic client
# client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
#
# def generate_ai_reply(sender_name: str, sender_email: str, subject: str, body: str) -> str:
#     """
#     Calls Anthropic API to generate a polite, helpful reply
#     based on the sender's email (name, email, subject, and body).
#     Ensures the AI addresses the sender correctly.
#     """
#     try:
#         prompt = f"""
#         You are Strathy, Strathmore University's AI Administrative Assistant.
#
#         The sender is:
#         Name: {sender_name}
#         Email: {sender_email}
#
#         They wrote the following email:
#         Subject: {subject}
#         Body: {body}
#
#         Write a professional, concise, and helpful reply.
#         Make sure to address the sender by their actual name: {sender_name}.
#         Do not invent or assume other names.
#         """
#
#         response = client.messages.create(
#             model="claude-3-7-sonnet-latest",  # or claude-3-sonnet for cheaper cost
#             max_tokens=300,
#             messages=[{"role": "user", "content": prompt}]
#         )
#
#         return response.content[0].text.strip()
#
#     except Exception as e:
#         return f"(Error generating AI reply: {e})"

# =====================
# === Gemini Client ===
# =====================
from google import genai
import os


GEMINI_API_KEY = os.getenv("GENAI_API_KEY")  # set this in your environment
client = genai.Client(api_key=GEMINI_API_KEY)

def generate_ai_reply(sender_name: str, sender_email: str, subject: str, body: str) -> str:
    """
    Calls Google's Gemini API to generate a polite, helpful reply
    based on the sender's email (name, email, subject, and body).
    """
    try:
        prompt = f"""
        You are Strathy, Strathmore University's AI Administrative Assistant.

        The sender is:
        Name: {sender_name}
        Email: {sender_email}

        They wrote the following email:
        Subject: {subject}
        Body: {body}

        Write a professional, concise, and helpful reply.
        Make sure to address the sender by their actual name: {sender_name}.
        Do not invent or assume other names.
        """

        response = client.models.generate_content(
            model="gemini-2.5-pro",  # or "gemini-1.5-flash" for faster/cheaper responses
            contents=prompt,
        )

        return response.text.strip()

    except Exception as e:
        return f"(Error generating AI reply: {e})"