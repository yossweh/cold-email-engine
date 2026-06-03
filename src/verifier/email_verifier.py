"""
Cold Email Engine — Email Verification
Check email validity before sending to reduce bounce rate
"""
import re
import socket
import smtplib
import dns.resolver
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor


class EmailVerifier:
    """Verify email addresses to reduce bounce rate."""

    # Common disposable email domains
    DISPOSABLE_DOMAINS = {
        'tempmail.com', 'throwaway.email', 'guerrillamail.com',
        'mailinator.com', 'yopmail.com', 'temp-mail.org',
        'fakeinbox.com', 'sharklasers.com', 'guerrillamailblock.com',
        'grr.la', 'dispostable.com', '10minutemail.com',
    }

    # Role-based emails (not decision makers)
    ROLE_PREFIXES = {
        'info', 'support', 'help', 'admin', 'contact',
        'sales', 'marketing', 'team', 'office', 'hr',
        'noreply', 'no-reply', 'mail', 'postmaster',
        'webmaster', 'abuse', 'billing', 'legal',
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def verify(self, email: str) -> Dict:
        """Full email verification pipeline."""
        result = {
            'email': email,
            'valid': False,
            'score': 0,  # 0-100 confidence
            'checks': {},
            'reason': '',
        }

        # Step 1: Syntax check
        syntax = self._check_syntax(email)
        result['checks']['syntax'] = syntax
        if not syntax['valid']:
            result['reason'] = 'Invalid syntax'
            return result

        # Step 2: Domain check
        domain = email.split('@')[1]
        domain_check = self._check_domain(domain)
        result['checks']['domain'] = domain_check
        if not domain_check['valid']:
            result['reason'] = domain_check.get('reason', 'Invalid domain')
            return result

        # Step 3: MX record check
        mx_check = self._check_mx(domain)
        result['checks']['mx'] = mx_check
        if not mx_check['valid']:
            result['reason'] = 'No MX records'
            return result

        # Step 4: Disposable check
        disposable = self._check_disposable(domain)
        result['checks']['disposable'] = disposable
        if disposable['is_disposable']:
            result['score'] -= 30

        # Step 5: Role-based check
        local = email.split('@')[0]
        role = self._check_role_based(local)
        result['checks']['role'] = role
        if role['is_role']:
            result['score'] -= 20

        # Step 6: SMTP check (optional, can be slow)
        # smtp = self._check_smtp(email, domain, mx_check.get('mx_records', []))
        # result['checks']['smtp'] = smtp

        # Calculate final score
        base_score = 70
        if domain_check.get('has_website'):
            base_score += 10
        if mx_check.get('mx_count', 0) > 0:
            base_score += 15
        if not disposable['is_disposable']:
            base_score += 5
        if not role['is_role']:
            base_score += 10

        result['score'] = min(100, max(0, base_score + result['score']))
        result['valid'] = result['score'] >= 50

        if result['valid']:
            result['reason'] = 'Valid'
        else:
            result['reason'] = f'Low confidence score: {result["score"]}'

        return result

    def verify_batch(self, emails: List[str], max_workers: int = 5) -> List[Dict]:
        """Verify multiple emails in parallel."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(self.verify, emails))
        return results

    def _check_syntax(self, email: str) -> Dict:
        """Check email syntax."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        valid = bool(re.match(pattern, email))
        return {'valid': valid, 'email': email}

    def _check_domain(self, domain: str) -> Dict:
        """Check if domain exists and has website."""
        result = {'domain': domain, 'valid': False, 'has_website': False}

        try:
            socket.getaddrinfo(domain, None)
            result['valid'] = True
        except socket.gaierror:
            result['reason'] = 'Domain does not resolve'
            return result

        # Check if website exists
        import requests
        try:
            resp = requests.head(f'https://{domain}', timeout=self.timeout, allow_redirects=True)
            result['has_website'] = resp.status_code < 400
        except:
            try:
                resp = requests.head(f'http://{domain}', timeout=self.timeout, allow_redirects=True)
                result['has_website'] = resp.status_code < 400
            except:
                pass

        return result

    def _check_mx(self, domain: str) -> Dict:
        """Check MX records."""
        result = {'domain': domain, 'valid': False, 'mx_records': [], 'mx_count': 0}

        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            for mx in mx_records:
                result['mx_records'].append(str(mx.exchange))
            result['mx_count'] = len(result['mx_records'])
            result['valid'] = result['mx_count'] > 0
        except:
            pass

        return result

    def _check_disposable(self, domain: str) -> Dict:
        """Check if domain is disposable email."""
        return {
            'domain': domain,
            'is_disposable': domain.lower() in self.DISPOSABLE_DOMAINS
        }

    def _check_role_based(self, local_part: str) -> Dict:
        """Check if email is role-based (not a person)."""
        prefix = local_part.lower().split('.')[0].split('+')[0]
        return {
            'local': local_part,
            'is_role': prefix in self.ROLE_PREFIXES
        }

    def _check_smtp(self, email: str, domain: str, mx_records: list) -> Dict:
        """SMTP verification (risky — some servers block)."""
        result = {'valid': False, 'method': 'smtp'}

        for mx in mx_records[:2]:
            try:
                server = smtplib.SMTP(mx.rstrip('.'), 25, timeout=self.timeout)
                server.helo('verify.email')
                server.mail('test@verify.email')
                code, _ = server.rcpt(email)
                server.quit()

                result['code'] = code
                result['valid'] = code == 250
                return result
            except:
                continue

        return result


def filter_valid_emails(emails: List[str], min_score: int = 50) -> Tuple[List[str], List[Dict]]:
    """Filter list to only valid emails, return (valid, rejected)."""
    verifier = EmailVerifier()
    valid = []
    rejected = []

    for result in verifier.verify_batch(emails):
        if result['valid'] and result['score'] >= min_score:
            valid.append(result['email'])
        else:
            rejected.append(result)

    return valid, rejected


if __name__ == '__main__':
    import sys
    emails = sys.argv[1:] if len(sys.argv) > 1 else ['test@gmail.com', 'fake@nonexistent12345.com']

    verifier = EmailVerifier()
    for email in emails:
        result = verifier.verify(email)
        print(f"{'✅' if result['valid'] else '❌'} {email} — Score: {result['score']} — {result['reason']}")
