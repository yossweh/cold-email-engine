"""
Cold Email Engine — Email Generator
Generate personalized cold emails using Claude API (with template fallback)
"""
import json
from typing import Dict, Optional
from pathlib import Path


class EmailGenerator:
    """Generate personalized cold emails using Claude or templates."""

    def __init__(self, api_key: str = ''):
        self.api_key = api_key
        self.client = None

        if api_key and api_key != 'sk-ant-xxx':
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key)
            except:
                pass

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

        # Try Claude API first
        if self.client:
            try:
                return self._generate_with_claude(
                    lead_data, product_description, sender_name,
                    sender_company, tone, template_type
                )
            except Exception as e:
                # Fallback to template
                return self._generate_with_template(
                    lead_data, product_description, sender_name,
                    sender_company, tone
                )
        else:
            # Use template fallback
            return self._generate_with_template(
                lead_data, product_description, sender_name,
                sender_company, tone
            )

    def _generate_with_claude(
        self, lead_data: Dict, product: str,
        sender_name: str, sender_company: str,
        tone: str, template_type: str
    ) -> Dict:
        """Generate using Claude API."""
        prompt = self._build_prompt(
            lead_data, product, sender_name,
            sender_company, tone, template_type
        )

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text
        return self._parse_response(response_text)

    def _generate_with_template(
        self, lead_data: Dict, product: str,
        sender_name: str, sender_company: str,
        tone: str
    ) -> Dict:
        """Generate using built-in templates (no API needed)."""
        company = lead_data.get('title', lead_data.get('company', 'your company'))
        description = lead_data.get('description', '')
        url = lead_data.get('url', '')

        # Personalization based on lead data
        personalization = ''
        if description:
            personalization = f"I noticed that {company} is focused on {description[:100]}."
        elif url:
            personalization = f"I came across {company} and was impressed by what you're building."
        else:
            personalization = f"I've been following {company} and think there's a great fit here."

        # Templates based on tone
        templates = {
            'professional': {
                'subject': f"Quick question about {company}'s growth",
                'body': f"""Hi there,

{personalization}

We help companies like {company} {product}.

Would you be open to a quick 15-minute call this week to discuss how we could help?

Best regards,
{sender_name}
{sender_company}"""
            },
            'casual': {
                'subject': f"Hey {company} team 👋",
                'body': f"""Hey!

{personalization}

We've been helping companies {product} — and I think {company} could really benefit.

Got 15 mins this week for a quick chat?

Cheers,
{sender_name}"""
            },
            'friendly': {
                'subject': f"Love what {company} is doing!",
                'body': f"""Hi there!

{personalization}

We specialize in helping companies like yours {product}.

I'd love to share some ideas on how we could help {company} grow. Would you be open to a quick call?

Looking forward to hearing from you!
{sender_name}
{sender_company}"""
            },
            'direct': {
                'subject': f"{product} for {company}",
                'body': f"""Hi,

{personalization}

We {product}.

15-minute call this week?

{sender_name}
{sender_company}"""
            },
        }

        template = templates.get(tone, templates['professional'])

        return {
            'subject': template['subject'],
            'body': template['body'],
            'personalization_note': f'Template-based using {company} info',
            'confidence': 0.7,
            'method': 'template'
        }

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
