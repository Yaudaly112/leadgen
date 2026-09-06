"""Demo site generator - creates one-page websites for leads."""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.services.llm import generate_business_description, generate_demo_content

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent / "generated_sites"


class DemoSiteGenerator:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        self.template = self.env.get_template("demo_page.html")

    async def generate_site(self, business: dict) -> dict:
        """Generate a complete demo website for a business."""
        # Generate content using LLM
        description = await generate_business_description(business)
        demo_content = await generate_demo_content(business)

        # Generate a unique slug for the demo URL
        slug = self._make_slug(business.get("business_name", ""))

        # Render HTML
        html_content = self.template.render(
            business_name=business.get("business_name", ""),
            business_type=business.get("business_type", ""),
            city=business.get("city", ""),
            state=business.get("state", ""),
            phone=business.get("phone", ""),
            rating=business.get("rating"),
            review_count=business.get("review_count", 0),
            hero_headline=demo_content.get("hero_headline", ""),
            hero_subheadline=demo_content.get("hero_subheadline", ""),
            about_title=demo_content.get("about_title", ""),
            about_text=demo_content.get("about_text", ""),
            services_title=demo_content.get("services_title", ""),
            services_list=demo_content.get("services_list", []),
            cta_text=demo_content.get("cta_text", "Get a Free Quote"),
            cta_subtext=demo_content.get("cta_subtext", ""),
            footer_text=demo_content.get("footer_text", ""),
            demo_url=f"{settings.demo_base_url}/{slug}",
            generated_at=datetime.utcnow().isoformat(),
        )

        # Save to disk
        output_path = OUTPUT_DIR / slug
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "index.html").write_text(html_content)

        # Build full demo URL
        demo_url = f"{settings.demo_base_url}/{slug}"

        return {
            "demo_url": demo_url,
            "slug": slug,
            "html_content": html_content,
            "output_path": str(output_path),
            "content": demo_content,
        }

    def _make_slug(self, name: str) -> str:
        """Create a URL-friendly slug from business name."""
        # Clean name
        slug = name.lower().strip()
        slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
        slug = "-".join(filter(None, slug.split("-")))[:40]

        # Add hash suffix for uniqueness
        hash_suffix = hashlib.md5(
            f"{name}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:6]

        return f"{slug}-{hash_suffix}"


demo_generator = DemoSiteGenerator()
