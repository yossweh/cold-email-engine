"""
Cold Email Engine — CSV Import & Lead Management
Import leads from CSV, Google Sheets, or manual input
"""
import csv
import json
import re
from typing import Dict, List, Optional
from pathlib import Path


class LeadManager:
    """Manage leads from various sources."""

    # Common CSV column mappings
    COLUMN_MAP = {
        'email': ['email', 'e-mail', 'mail', 'email_address', 'emailaddress'],
        'name': ['name', 'full_name', 'fullname', 'first_name', 'contact_name'],
        'company': ['company', 'organization', 'org', 'business', 'company_name'],
        'website': ['website', 'url', 'site', 'homepage', 'domain'],
        'title': ['title', 'job_title', 'position', 'role'],
        'phone': ['phone', 'telephone', 'mobile', 'cell'],
        'linkedin': ['linkedin', 'linkedin_url', 'linkedin_profile'],
        'notes': ['notes', 'description', 'comment', 'comments'],
    }

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or Path(__file__).parent.parent.parent / 'data')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.leads_dir = self.data_dir / 'leads'
        self.leads_dir.mkdir(parents=True, exist_ok=True)

    def import_csv(self, filepath: str, list_name: str = None) -> Dict:
        """Import leads from CSV file."""
        filepath = Path(filepath)
        if not filepath.exists():
            return {'error': f'File not found: {filepath}'}

        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            raw_leads = list(reader)

        if not raw_leads:
            return {'error': 'CSV is empty'}

        # Map columns
        mapped_leads = []
        for raw in raw_leads:
            lead = self._map_columns(raw)
            if lead.get('email'):
                mapped_leads.append(lead)

        # Save to leads directory
        if not list_name:
            list_name = filepath.stem

        output_path = self.leads_dir / f'{list_name}.json'
        with open(output_path, 'w') as f:
            json.dump(mapped_leads, f, indent=2)

        return {
            'list_name': list_name,
            'total_raw': len(raw_leads),
            'total_imported': len(mapped_leads),
            'skipped': len(raw_leads) - len(mapped_leads),
            'output_path': str(output_path),
            'sample': mapped_leads[:3] if mapped_leads else [],
        }

    def _map_columns(self, raw_row: Dict) -> Dict:
        """Map CSV columns to standard format."""
        lead = {}

        # Normalize keys
        normalized = {k.lower().strip().replace(' ', '_'): v for k, v in raw_row.items() if v}

        for standard, aliases in self.COLUMN_MAP.items():
            for alias in aliases:
                if alias in normalized:
                    lead[standard] = normalized[alias]
                    break

        # Extract email from any column if not found
        if 'email' not in lead:
            for v in normalized.values():
                if '@' in str(v):
                    lead['email'] = str(v).strip()
                    break

        # Extract website from email domain if not found
        if 'website' not in lead and 'email' in lead:
            domain = lead['email'].split('@')[1]
            if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                lead['website'] = f'https://{domain}'

        return lead

    def import_manual(self, entries: List[str], list_name: str = 'manual') -> Dict:
        """Import from manual input (emails or URLs)."""
        leads = []
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            if '@' in entry:
                # It's an email
                lead = {'email': entry}
                domain = entry.split('@')[1]
                if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                    lead['website'] = f'https://{domain}'
                leads.append(lead)
            elif entry.startswith('http') or '.' in entry:
                # It's a URL
                if not entry.startswith('http'):
                    entry = f'https://{entry}'
                leads.append({'website': entry})

        # Save
        output_path = self.leads_dir / f'{list_name}.json'
        with open(output_path, 'w') as f:
            json.dump(leads, f, indent=2)

        return {
            'list_name': list_name,
            'total_imported': len(leads),
            'output_path': str(output_path),
            'leads': leads,
        }

    def get_list(self, list_name: str) -> List[Dict]:
        """Get leads from a saved list."""
        path = self.leads_dir / f'{list_name}.json'
        if not path.exists():
            return []
        with open(path) as f:
            return json.load(f)

    def list_all(self) -> List[Dict]:
        """List all saved lead lists."""
        lists = []
        for f in self.leads_dir.glob('*.json'):
            with open(f) as fh:
                leads = json.load(fh)
            lists.append({
                'name': f.stem,
                'count': len(leads),
                'path': str(f),
            })
        return lists

    def deduplicate(self, list_name: str) -> Dict:
        """Remove duplicate emails from a list."""
        leads = self.get_list(list_name)
        seen = set()
        unique = []

        for lead in leads:
            email = lead.get('email', '').lower()
            if email and email not in seen:
                seen.add(email)
                unique.append(lead)
            elif not email:
                unique.append(lead)

        # Save deduplicated
        output_path = self.leads_dir / f'{list_name}.json'
        with open(output_path, 'w') as f:
            json.dump(unique, f, indent=2)

        return {
            'list_name': list_name,
            'before': len(leads),
            'after': len(unique),
            'removed': len(leads) - len(unique),
        }

    def merge_lists(self, list_names: List[str], output_name: str) -> Dict:
        """Merge multiple lead lists into one."""
        all_leads = []
        for name in list_names:
            all_leads.extend(self.get_list(name))

        # Deduplicate
        seen = set()
        unique = []
        for lead in all_leads:
            email = lead.get('email', '').lower()
            if email and email not in seen:
                seen.add(email)
                unique.append(lead)

        output_path = self.leads_dir / f'{output_name}.json'
        with open(output_path, 'w') as f:
            json.dump(unique, f, indent=2)

        return {
            'output_name': output_name,
            'merged_from': list_names,
            'total': len(unique),
            'output_path': str(output_path),
        }

    def export_csv(self, list_name: str, output_path: str = None) -> str:
        """Export leads to CSV."""
        leads = self.get_list(list_name)
        if not leads:
            return ''

        if not output_path:
            output_path = str(self.leads_dir / f'{list_name}_export.csv')

        # Collect all keys
        all_keys = set()
        for lead in leads:
            all_keys.update(lead.keys())

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
            writer.writeheader()
            writer.writerows(leads)

        return output_path


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python lead_manager.py import <file.csv> [list_name]")
        print("  python lead_manager.py list")
        print("  python lead_manager.py show <list_name>")
        sys.exit(1)

    manager = LeadManager()

    cmd = sys.argv[1]

    if cmd == 'import':
        result = manager.import_csv(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(json.dumps(result, indent=2))

    elif cmd == 'list':
        lists = manager.list_all()
        for l in lists:
            print(f"  {l['name']}: {l['count']} leads")

    elif cmd == 'show':
        leads = manager.get_list(sys.argv[2])
        print(json.dumps(leads[:5], indent=2))
        print(f"... {len(leads)} total")
