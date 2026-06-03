"""
Cold Email Engine — Follow-up Sequences
Auto follow-up if no reply received
"""
import json
import time
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from enum import Enum


class SequenceStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REPLIED = "replied"
    BOUNCED = "bounced"
    COMPLETED = "completed"
    PAUSED = "paused"


class FollowUpSequence:
    """Manage follow-up email sequences."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.sequences_dir = self.data_dir / 'sequences'
        self.sequences_dir.mkdir(parents=True, exist_ok=True)

    def create_sequence(
        self,
        name: str,
        emails: List[Dict],
        delay_days: Optional[List[int]] = None,
        max_followups: int = 3
    ) -> Dict:
        """
        Create a follow-up sequence.

        emails: List of email content dicts:
            [
                {"subject": "Initial", "body": "..."},
                {"subject": "Follow-up 1", "body": "..."},
                {"subject": "Follow-up 2", "body": "..."},
            ]

        delay_days: Days to wait between each follow-up
            [0, 3, 7] = send immediately, wait 3 days, wait 7 days
        """
        if delay_days is None:
            delay_days = [0, 3, 7, 14]  # Default: immediate, 3d, 7d, 14d

        sequence = {
            'name': name,
            'created': datetime.now().isoformat(),
            'status': SequenceStatus.ACTIVE.value,
            'steps': [],
            'max_followups': max_followups,
            'stats': {
                'total_leads': 0,
                'sent': 0,
                'replied': 0,
                'bounced': 0,
                'pending': 0,
            }
        }

        for i, email in enumerate(emails[:max_followups + 1]):
            step = {
                'step_number': i,
                'delay_days': delay_days[i] if i < len(delay_days) else delay_days[-1],
                'subject': email['subject'],
                'body': email['body'],
                'condition': email.get('condition', 'no_reply'),  # no_reply, opened, clicked
            }
            sequence['steps'].append(step)

        # Save sequence template
        seq_path = self.sequences_dir / f'{name}.json'
        with open(seq_path, 'w') as f:
            json.dump(sequence, f, indent=2)

        return sequence

    def start_sequence(self, sequence_name: str, leads: List[Dict]) -> Dict:
        """Start a sequence for a list of leads."""
        seq_path = self.sequences_dir / f'{sequence_name}.json'
        if not seq_path.exists():
            return {'error': f'Sequence not found: {sequence_name}'}

        with open(seq_path) as f:
            sequence = json.load(f)

        # Create tracking for each lead
        tracking = {
            'sequence': sequence_name,
            'started': datetime.now().isoformat(),
            'leads': []
        }

        for lead in leads:
            lead_tracking = {
                'email': lead.get('email', ''),
                'name': lead.get('name', ''),
                'company': lead.get('company', ''),
                'current_step': 0,
                'status': SequenceStatus.ACTIVE.value,
                'history': [],
                'next_send': datetime.now().isoformat(),
            }
            tracking['leads'].append(lead_tracking)

        # Save tracking
        tracking_path = self.sequences_dir / f'{sequence_name}_tracking.json'
        with open(tracking_path, 'w') as f:
            json.dump(tracking, f, indent=2)

        # Update stats
        sequence['stats']['total_leads'] = len(leads)
        sequence['stats']['pending'] = len(leads)
        with open(seq_path, 'w') as f:
            json.dump(sequence, f, indent=2)

        return {
            'sequence': sequence_name,
            'leads_count': len(leads),
            'steps': len(sequence['steps']),
            'tracking_path': str(tracking_path),
        }

    def get_pending_sends(self, sequence_name: str) -> List[Dict]:
        """Get leads that are ready for next email in sequence."""
        tracking_path = self.sequences_dir / f'{sequence_name}_tracking.json'
        if not tracking_path.exists():
            return []

        with open(tracking_path) as f:
            tracking = json.load(f)

        seq_path = self.sequences_dir / f'{sequence_name}.json'
        with open(seq_path) as f:
            sequence = json.load(f)

        now = datetime.now()
        pending = []

        for lead in tracking['leads']:
            if lead['status'] != SequenceStatus.ACTIVE.value:
                continue

            next_send = datetime.fromisoformat(lead['next_send'])
            if now >= next_send:
                step_num = lead['current_step']
                if step_num < len(sequence['steps']):
                    step = sequence['steps'][step_num]
                    pending.append({
                        'email': lead['email'],
                        'name': lead['name'],
                        'company': lead['company'],
                        'step': step_num,
                        'subject': step['subject'],
                        'body': self._personalize(step['body'], lead),
                        'delay_days': step['delay_days'],
                    })

        return pending

    def mark_sent(self, sequence_name: str, email: str) -> Dict:
        """Mark an email as sent in the sequence."""
        return self._update_lead(sequence_name, email, 'sent')

    def mark_replied(self, sequence_name: str, email: str) -> Dict:
        """Mark a lead as replied (stops follow-ups)."""
        return self._update_lead(sequence_name, email, 'replied')

    def mark_bounced(self, sequence_name: str, email: str) -> Dict:
        """Mark an email as bounced."""
        return self._update_lead(sequence_name, email, 'bounced')

    def _update_lead(self, sequence_name: str, email: str, action: str) -> Dict:
        """Update lead status in tracking."""
        tracking_path = self.sequences_dir / f'{sequence_name}_tracking.json'
        if not tracking_path.exists():
            return {'error': 'Tracking not found'}

        with open(tracking_path) as f:
            tracking = json.load(f)

        seq_path = self.sequences_dir / f'{sequence_name}.json'
        with open(seq_path) as f:
            sequence = json.load(f)

        for lead in tracking['leads']:
            if lead['email'].lower() == email.lower():
                if action == 'sent':
                    lead['history'].append({
                        'step': lead['current_step'],
                        'sent_at': datetime.now().isoformat(),
                        'subject': sequence['steps'][lead['current_step']]['subject'] if lead['current_step'] < len(sequence['steps']) else '',
                    })
                    lead['current_step'] += 1

                    # Schedule next follow-up
                    if lead['current_step'] < len(sequence['steps']):
                        delay = sequence['steps'][lead['current_step']]['delay_days']
                        lead['next_send'] = (datetime.now() + timedelta(days=delay)).isoformat()
                    else:
                        lead['status'] = SequenceStatus.COMPLETED.value

                elif action == 'replied':
                    lead['status'] = SequenceStatus.REPLIED.value
                    sequence['stats']['replied'] += 1

                elif action == 'bounced':
                    lead['status'] = SequenceStatus.BOUNCED.value
                    sequence['stats']['bounced'] += 1

                break

        # Save
        with open(tracking_path, 'w') as f:
            json.dump(tracking, f, indent=2)
        with open(seq_path, 'w') as f:
            json.dump(sequence, f, indent=2)

        return {'status': 'updated', 'email': email, 'action': action}

    def _personalize(self, template: str, lead: Dict) -> str:
        """Replace placeholders with lead data."""
        replacements = {
            '{{name}}': lead.get('name', 'there'),
            '{{first_name}}': lead.get('name', 'there').split()[0] if lead.get('name') else 'there',
            '{{company}}': lead.get('company', 'your company'),
            '{{email}}': lead.get('email', ''),
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result

    def get_stats(self, sequence_name: str) -> Dict:
        """Get sequence statistics."""
        tracking_path = self.sequences_dir / f'{sequence_name}_tracking.json'
        if not tracking_path.exists():
            return {'error': 'Tracking not found'}

        with open(tracking_path) as f:
            tracking = json.load(f)

        stats = {
            'total': len(tracking['leads']),
            'active': sum(1 for l in tracking['leads'] if l['status'] == SequenceStatus.ACTIVE.value),
            'replied': sum(1 for l in tracking['leads'] if l['status'] == SequenceStatus.REPLIED.value),
            'bounced': sum(1 for l in tracking['leads'] if l['status'] == SequenceStatus.BOUNCED.value),
            'completed': sum(1 for l in tracking['leads'] if l['status'] == SequenceStatus.COMPLETED.value),
            'avg_steps': sum(len(l['history']) for l in tracking['leads']) / max(1, len(tracking['leads'])),
        }

        return stats

    def list_sequences(self) -> List[Dict]:
        """List all sequences."""
        sequences = []
        for f in self.sequences_dir.glob('*.json'):
            if '_tracking' not in f.name:
                with open(f) as fh:
                    seq = json.load(fh)
                sequences.append({
                    'name': seq['name'],
                    'steps': len(seq['steps']),
                    'status': seq['status'],
                    'leads': seq['stats']['total_leads'],
                })
        return sequences


# Default follow-up templates
DEFAULT_TEMPLATES = [
    {
        "subject": "Quick question, {{first_name}}",
        "body": """Hi {{first_name}},

I noticed {{company}} and thought you might be interested in what we're building.

We help companies like yours increase conversion rates by 40% with AI-powered automation.

Would you be open to a quick 15-minute call this week?

Best,
[Your Name]""",
    },
    {
        "subject": "Re: Quick question, {{first_name}}",
        "body": """Hi {{first_name}},

Just following up on my last email. I know you're busy, so I'll keep this short.

We've helped companies like [Similar Company] achieve:
• 40% increase in conversion
• 60% reduction in manual work
• 3x faster response times

Would love to show you how this could work for {{company}}.

Best,
[Your Name]""",
    },
    {
        "subject": "Last try, {{first_name}}",
        "body": """Hi {{first_name}},

I don't want to be a pest, so this will be my last email.

If converting more leads with less effort sounds interesting, here's my calendar link: [link]

If not, no worries at all. I'll stop reaching out.

Best,
[Your Name]""",
    },
]


if __name__ == '__main__':
    # Example usage
    seq = FollowUpSequence()

    # Create sequence
    result = seq.create_sequence(
        name="demo-campaign",
        emails=DEFAULT_TEMPLATES,
        delay_days=[0, 3, 7],
    )
    print(f"Created sequence: {result['name']}")

    # Start with sample leads
    leads = [
        {"email": "john@example.com", "name": "John", "company": "Acme Corp"},
        {"email": "jane@test.com", "name": "Jane", "company": "Test Inc"},
    ]

    result = seq.start_sequence("demo-campaign", leads)
    print(f"Started for {result['leads_count']} leads")

    # Check pending
    pending = seq.get_pending_sends("demo-campaign")
    print(f"Pending sends: {len(pending)}")
