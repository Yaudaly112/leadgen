"""LLM-powered content generation for business descriptions, emails, and demo sites."""

from openai import AsyncOpenAI

from app.config import settings

# Lazy client — doesn't crash at import time if OPENAI_API_KEY is not yet set
client = None


def get_client() -> AsyncOpenAI:
    global client
    if client is None:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
    return client


# ── Business Description Generator ──────────────────────────────────────────────

BUSINESS_DESCRIPTION_PROMPT = """You are a professional copywriter for a web design agency. 
Write a compelling 2-3 sentence description for this local business to use on their website.

Business name: {business_name}
Business type: {business_type}
Location: {city}, {state}
Rating: {rating}/5 ({review_count} reviews)
Services: {services}

Guidelines:
- Be professional but warm
- Highlight what makes them valuable to customers
- Mention their location naturally
- Keep it under 60 words
- Do NOT mention that they don't have a website
- Write as if this is their existing business description"""


async def generate_business_description(business: dict) -> str:
    """Generate a professional business description using LLM."""
    prompt = BUSINESS_DESCRIPTION_PROMPT.format(
        business_name=business.get("business_name", ""),
        business_type=business.get("business_type", "local business"),
        city=business.get("city", ""),
        state=business.get("state", ""),
        rating=business.get("rating", "N/A"),
        review_count=business.get("review_count", "unknown"),
        services=", ".join(business.get("services", [])[:5]),
    )

    response = await get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Cold Email Generator ────────────────────────────────────────────────────────

COLD_EMAIL_PROMPT = """You are a friendly web designer reaching out to a local business owner.

Write a short, personalized cold email (under 120 words) to the owner of {business_name}, 
a {business_type} in {city}, {state}.

Context:
- They have {review_count} reviews and a {rating}/5 rating
- I built a free demo website for them: {demo_url}
- I want to offer to set it up on their own domain

Tone: Helpful, not pushy. Like a neighbor offering a favor.
Structure:
1. Personal greeting using their business name
2. Mention I noticed they're great (reference reviews/rating briefly)
3. Mention the demo site I built (include the URL naturally)
4. Clear CTA: suggest a 10-15 min call
5. Professional sign-off

Include {{unsubscribe_link}} and your physical address at the bottom for CAN-SPAM compliance.
Use --- to separate the email body from the unsubscribe footer."""


async def generate_cold_email(business: dict, demo_url: str) -> dict:
    """Generate a personalized cold email for a lead."""
    prompt = COLD_EMAIL_PROMPT.format(
        business_name=business.get("business_name", ""),
        business_type=business.get("business_type", "business"),
        city=business.get("city", ""),
        state=business.get("state", ""),
        rating=business.get("rating", "N/A"),
        review_count=business.get("review_count", "unknown"),
        demo_url=demo_url,
    )

    response = await get_client().chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.8,
    )

    content = response.choices[0].message.content.strip()

    # Split into subject and body (first line is subject, rest is body)
    lines = content.split("\n")
    subject = lines[0].strip().strip('"').strip("'")
    body = "\n".join(lines[1:]).strip()

    return {"subject": subject, "body": body}


# ── Follow-up Email Generator ───────────────────────────────────────────────────

FOLLOWUP_EMAIL_PROMPT = """You are a friendly web designer following up with a local business owner.

Write a short follow-up email (under 80 words) for {business_name}, a {business_type} in {city}, {state}.

This is follow-up #{followup_number}. They haven't responded to my previous email where I 
offered a free demo website: {demo_url}

Tone: Brief, helpful, not pushy. Add new value (e.g., mention a specific benefit of having a website 
for their type of business).

Include {{unsubscribe_link}} for CAN-SPAM compliance."""


async def generate_followup_email(
    business: dict, demo_url: str, followup_number: int
) -> dict:
    """Generate a follow-up email."""
    prompt = FOLLOWUP_EMAIL_PROMPT.format(
        business_name=business.get("business_name", ""),
        business_type=business.get("business_type", "business"),
        city=business.get("city", ""),
        state=business.get("state", ""),
        demo_url=demo_url,
        followup_number=followup_number,
    )

    response = await get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250,
        temperature=0.8,
    )

    content = response.choices[0].message.content.strip()
    lines = content.split("\n")
    subject = lines[0].strip().strip('"').strip("'")
    body = "\n".join(lines[1:]).strip()

    return {"subject": subject, "body": body}


# ── Call Script Generator ───────────────────────────────────────────────────────

CALL_SCRIPT_PROMPT = """Generate a brief phone call script for {business_name}, 
a {business_type} in {city}, {state}.

The caller is from a web design company and built a demo website: {demo_url}

Script structure (under 100 words total):
1. Brief greeting and who you are
2. One sentence about why you're calling (built them a demo site)
3. Ask if they have 2 minutes to hear about it
4. If yes: describe the demo briefly and offer to set it up
5. If no: offer to send the link via email and schedule a better time

Keep it conversational and natural. Include both a positive response path 
and a polite exit if they're not interested."""


async def generate_call_script(business: dict, demo_url: str) -> str:
    """Generate a phone call script."""
    prompt = CALL_SCRIPT_PROMPT.format(
        business_name=business.get("business_name", ""),
        business_type=business.get("business_type", "business"),
        city=business.get("city", ""),
        state=business.get("state", ""),
        demo_url=demo_url,
    )

    response = await get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Demo Site Content Generator ─────────────────────────────────────────────────

DEMO_CONTENT_PROMPT = """You are generating content for a one-page demo website for a local business.

Business: {business_name}
Type: {business_type}
Location: {city}, {state}
Rating: {rating}/5 ({review_count} reviews)
Services: {services}

Generate a JSON object with these fields (no markdown, just raw JSON):
{{
  "hero_headline": "short catchy headline (under 8 words)",
  "hero_subheadline": "supporting line (under 15 words)",
  "about_title": "About [Business Name]",
  "about_text": "2-3 sentence about section (under 60 words)",
  "services_title": "Our Services",
  "services_list": ["service 1", "service 2", "service 3", "service 4"],
  "cta_text": "Get a Free Quote",
  "cta_subtext": "Serving [city] and surrounding areas",
  "footer_text": "© 2024 [Business Name]. All rights reserved."
}}

Make it professional and conversion-focused. The business owner should be impressed 
when they see this."""


async def generate_demo_content(business: dict) -> dict:
    """Generate all text content for the demo website."""
    import json

    prompt = DEMO_CONTENT_PROMPT.format(
        business_name=business.get("business_name", ""),
        business_type=business.get("business_type", "local business"),
        city=business.get("city", ""),
        state=business.get("state", ""),
        rating=business.get("rating", "N/A"),
        review_count=business.get("review_count", "unknown"),
        services=", ".join(business.get("services", [])[:6]),
    )

    response = await get_client().chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)
