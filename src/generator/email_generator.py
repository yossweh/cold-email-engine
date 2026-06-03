"""
Cold Email Engine — Email Generator
Generate personalized cold emails using Claude API
"""
import anthropic
import json
from typing import Dict, Optional
from pathlib import Path


class EmailGenerator:
    """Generate personalized cold emails using Claude."""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate_email(
        self,
        lead_data: Dict,
        product_description: str,
        sender_name: str,
        sender_company: str,
        tone: str = "professional",
        template_type: str = "cold_outreach"
    ) -> Dict:
        """Generate a personalized cold email for a lead."""

        prompt = self._build_prompt(
            lead_data, product_description, sender_name,
            sender_company, tone, template_type
        )

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            return self._parse_response(response_text)

        except Exception as e:
            return {'error': str(e)}

    def _build_prompt(
        self, lead_data: Dict, product: str,
        sender_name: str, sender_company: str,
        tone: str, template_type: str
    ) -> str:
        return f"""Generate a personalized cold email.

## Lead Info:
- Company: {lead_data.get('title', 'Unknown')}
- Website: {lead_data.get('url', '')}
- Description: {lead_data.get('description', 'N/A')}
- About: {lead_data.get('about', 'N/A')[:300]}
- Tech Stack: {', '.join(lead_data.get('tech_stack', []))}
- Headlines: {', '.join(lead_data.get('headlines', [])[:3])}

## Your Product/Service:
{product}

## Sender Info:
- Name: {sender_name}
- Company: {sender_company}

## Requirements:
- Tone: {tone}
- Type: {template_type}
- Must reference something specific about their company
- Keep under 150 words
- Strong but not pushy CTA
- No generic "I hope this email finds you well"

## Output Format (JSON):
{{
  "subject": "email subject line",
  "body": "email body (plain text, with line breaks)",
  "personalization_note": "what specific detail was used",
  "confidence": 0.0-1.0
}}

Return ONLY valid JSON."""

    def _parse_response(self, text: str) -> Dict:
        """Parse Claude's response into structured data."""
        try:
            # Try to extract JSON from response
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            return {'error': 'Could not parse response', 'raw': text}
        except json.JSONDecodeError:
            return {'error': 'Invalid JSON', 'raw': text}

    def generate_batch(
        self, leads: list, product: str,
        sender_name: str, sender_company: str,
        **kwargs
    ) -> list:
        """Generate emails for multiple leads."""
        results = []
        for lead in leads:
            result = self.generate_email(
                lead, product, sender_name, sender_company, **kwargs
            )
            result['lead'] = lead
            results.append(result)
        return results


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Set ANTHROPIC_API_KEY in .env")
        exit(1)

    gen = EmailGenerator(api_key)

    sample_lead = {
        'title': 'Acme Corp',
        'url': 'https://acme.com',
        'description': 'AI-powered analytics platform',
        'about': 'We help businesses make data-driven decisions',
        'tech_stack': ['React', 'Python', 'AWS'],
        'headlines': ['Analytics Made Simple', 'Data-Driven Decisions']
    }

    result = gen.generate_email(
        lead_data=sample_lead,
        product_description="We build custom AI chatbots that increase conversion by 40%",
        sender_name="John",
        sender_company="BotBuilder",
        tone="casual"
    )

    print(json.dumps(result, indent=2))
