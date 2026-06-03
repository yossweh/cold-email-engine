"""
Cold Email Engine — Lead Scraper
Scrape company info from website for personalization
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse


class LeadScraper:
    """Scrape company website for lead enrichment data."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def scrape_company(self, url: str) -> Dict:
        """Scrape company info from website."""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            data = {
                'url': url,
                'domain': urlparse(url).netloc,
                'title': self._get_title(soup),
                'description': self._get_description(soup),
                'keywords': self._get_keywords(soup),
                'about': self._get_about(soup),
                'contact_email': self._get_email(soup),
                'social_links': self._get_social(soup),
                'tech_stack': self._detect_tech(resp.text),
                'headings': self._get_headings(soup),
            }
            return data

        except Exception as e:
            return {'url': url, 'error': str(e)}

    def _get_title(self, soup: BeautifulSoup) -> str:
        title = soup.find('title')
        return title.text.strip() if title else ''

    def _get_description(self, soup: BeautifulSoup) -> str:
        meta = soup.find('meta', attrs={'name': 'description'})
        return meta.get('content', '') if meta else ''

    def _get_keywords(self, soup: BeautifulSoup) -> list:
        meta = soup.find('meta', attrs={'name': 'keywords'})
        if meta:
            return [k.strip() for k in meta.get('content', '').split(',')]
        return []

    def _get_about(self, soup: BeautifulSoup) -> str:
        # Look for about section
        for tag in soup.find_all(['section', 'div', 'p']):
            text = tag.get_text(strip=True).lower()
            if any(kw in text for kw in ['about us', 'about', 'who we are', 'our mission']):
                return tag.get_text(strip=True)[:500]
        return ''

    def _get_email(self, soup: BeautifulSoup) -> str:
        emails = set()
        for mailto in soup.select('a[href^="mailto:"]'):
            email = mailto['href'].replace('mailto:', '').split('?')[0]
            emails.add(email)
        # Also regex scan
        text = soup.get_text()
        found = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
        emails.update(found)
        return list(emails)[0] if emails else ''

    def _get_social(self, soup: BeautifulSoup) -> Dict:
        socials = {}
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'twitter.com' in href or 'x.com' in href:
                socials['twitter'] = href
            elif 'linkedin.com' in href:
                socials['linkedin'] = href
            elif 'github.com' in href:
                socials['github'] = href
        return socials

    def _detect_tech(self, html: str) -> list:
        techs = []
        indicators = {
            'React': ['react', '__NEXT_DATA__'],
            'Next.js': ['__next', '_next/static'],
            'WordPress': ['wp-content', 'wp-includes'],
            'Shopify': ['cdn.shopify.com'],
            'Stripe': ['js.stripe.com'],
            'Google Analytics': ['google-analytics', 'gtag'],
            'HubSpot': ['hubspot', 'hs-scripts'],
            'Intercom': ['intercom'],
        }
        for tech, markers in indicators.items():
            if any(m.lower() in html.lower() for m in markers):
                techs.append(tech)
        return techs

    def _get_headings(self, soup: BeautifulSoup) -> list:
        headings = []
        for h in soup.find_all(['h1', 'h2', 'h3'])[:5]:
            headings.append(h.get_text(strip=True))
        return headings


def enrich_lead(url: str) -> Dict:
    """Quick function to enrich a single lead."""
    scraper = LeadScraper()
    return scraper.scrape_company(url)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        result = enrich_lead(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python scraper.py <website_url>")
