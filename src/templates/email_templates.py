"""
Email Template Library — Pre-built cold email templates for 0xChapo
Categories: Cold Outreach, Follow-up, Re-engagement, Partnership, Job Inquiry
"""

TEMPLATES = [
    # ==================== COLD OUTREACH ====================
    {
        "id": "co-value-prop",
        "name": "Value Proposition Intro",
        "category": "Cold Outreach",
        "description": "Lead with a clear value proposition tailored to the prospect's company.",
        "subject": "Quick question about {{company_name}}'s growth",
        "body": """Hi {{first_name}},

I noticed {{company_name}} has been scaling fast — congrats on the recent growth.

We've been helping similar companies in {{industry}} reduce {{pain_point}} by up to 40% without adding headcount.

Would it make sense to hop on a quick 15-min call to see if we could do the same for {{company_name}}?

Best,
{{sender_name}}
{{sender_company}}""",
    },
    {
        "id": "co-problem-solver",
        "name": "Problem-Solver Cold Email",
        "category": "Cold Outreach",
        "description": "Identify a specific pain point and position your solution upfront.",
        "subject": "Struggling with {{pain_point}} at {{company_name}}?",
        "body": """Hey {{first_name}},

Most {{industry}} teams I talk to are drowning in {{pain_point}} — and the usual fixes just don't scale.

We built {{product_name}} specifically for this. Companies like {{case_study_company}} cut their {{metric}} by 35% in the first month.

I'd love to show you how it works in under 10 minutes. Open to a quick chat this week?

Cheers,
{{sender_name}}""",
    },
    {
        "id": "co-mutual-connection",
        "name": "Mutual Connection Intro",
        "category": "Cold Outreach",
        "description": "Leverage a shared connection or event to warm up the outreach.",
        "subject": "{{mutual_connection}} suggested I reach out",
        "body": """Hi {{first_name}},

{{mutual_connection}} mentioned you're working on some exciting things at {{company_name}} — especially around {{topic}}.

I've been helping teams in that space with {{brief_description}}, and thought it could be worth a conversation.

No pressure at all — would you be open to a 15-minute chat this week?

Best,
{{sender_name}}
{{sender_company}}""",
    },
    {
        "id": "co-case-study",
        "name": "Case Study Hook",
        "category": "Cold Outreach",
        "description": "Lead with a concrete result from a similar company to build credibility.",
        "subject": "How {{case_study_company}} grew revenue 3x",
        "body": """Hi {{first_name}},

I wanted to share a quick story. {{case_study_company}}, a company similar to {{company_name}}, was dealing with the same {{pain_point}} challenge.

After working with us, they saw:
• 40% reduction in {{metric}}
• 3x increase in {{key_result}}
• ROI within the first 60 days

I put together a short case study that breaks down exactly how they did it. Want me to send it over?

{{sender_name}}
{{sender_company}}""",
    },

    # ==================== FOLLOW-UP ====================
    {
        "id": "fu-gentle-nudge",
        "name": "Gentle Nudge Follow-up",
        "category": "Follow-up",
        "description": "A polite, low-pressure follow-up after no response to initial outreach.",
        "subject": "Re: Quick question about {{company_name}}'s growth",
        "body": """Hi {{first_name}},

Just floating this back to the top of your inbox — I know things get busy.

If {{pain_point}} isn't a priority right now, totally understand. But if it is, I'd love to share how we can help.

Worth 15 minutes?

{{sender_name}}""",
    },
    {
        "id": "fu-value-add",
        "name": "Value-Add Follow-up",
        "category": "Follow-up",
        "description": "Follow up with a useful resource or insight instead of just bumping the thread.",
        "subject": "Thought you'd find this useful, {{first_name}}",
        "body": """Hi {{first_name}},

I came across this article on {{industry}} trends and immediately thought of {{company_name}}: {{resource_link}}

It touches on exactly the kind of challenges we've been solving for companies like yours.

Would love to chat about how this applies to what you're building. Free this Thursday?

Best,
{{sender_name}}""",
    },
    {
        "id": "fu-breakup",
        "name": "Breakup Email",
        "category": "Follow-up",
        "description": "Final follow-up that creates urgency by implying you'll stop reaching out.",
        "subject": "Should I close your file?",
        "body": """Hi {{first_name}},

I've reached out a few times and haven't heard back — I don't want to be that person clogging your inbox.

I'll assume the timing isn't right and close out your file on my end.

If anything changes, feel free to reply to this email and we can pick up the conversation.

All the best,
{{sender_name}}
{{sender_company}}""",
    },

    # ==================== RE-ENGAGEMENT ====================
    {
        "id": "re-warm-lead",
        "name": "Warm Lead Re-engagement",
        "category": "Re-engagement",
        "description": "Re-engage a lead that went cold after showing initial interest.",
        "subject": "Still thinking about {{topic}}?",
        "body": """Hi {{first_name}},

We chatted a while back about {{topic}} and I wanted to check in.

Since then, we've shipped some major updates:
• {{feature_1}}
• {{feature_2}}
• {{feature_3}}

Thought it might be worth another look. Want me to give you a quick tour of what's new?

{{sender_name}}""",
    },
    {
        "id": "re-campaign-update",
        "name": "Industry Update Re-engagement",
        "category": "Re-engagement",
        "description": "Re-engage dormant leads with relevant industry news or company updates.",
        "subject": "{{industry}} is shifting fast — here's what's changing",
        "body": """Hi {{first_name}},

A lot has changed in {{industry}} since we last connected. Here's what we're seeing:

1. {{trend_1}}
2. {{trend_2}}
3. {{trend_3}}

Companies that adapt now are seeing 2-3x better results. We've been helping teams navigate this shift.

Would love to share what's working. Coffee chat this week?

{{sender_name}}
{{sender_company}}""",
    },

    # ==================== PARTNERSHIP ====================
    {
        "id": "pt-strategic",
        "name": "Strategic Partnership Pitch",
        "category": "Partnership",
        "description": "Propose a mutually beneficial partnership or integration opportunity.",
        "subject": "Partnership idea: {{sender_company}} x {{company_name}}",
        "body": """Hi {{first_name}},

I've been following {{company_name}}'s work in {{industry}} and I'm impressed by what you've built.

I think there's a strong overlap between our audiences. We serve {{audience_description}} and I see an opportunity for us to:

• {{benefit_1}}
• {{benefit_2}}
• {{benefit_3}}

Would you be open to exploring a partnership? I'd love to set up a call to discuss.

Best,
{{sender_name}}
{{sender_title}}, {{sender_company}}""",
    },
    {
        "id": "pt-integration",
        "name": "Integration / Co-Marketing",
        "category": "Partnership",
        "description": "Propose a product integration or joint marketing initiative.",
        "subject": "Let's build something together",
        "body": """Hey {{first_name}},

Quick intro — I'm {{sender_name}} from {{sender_company}}. We help {{audience}} with {{solution}}.

I noticed {{company_name}} serves a similar audience and I think our tools complement each other perfectly.

A few ideas:
→ Integration between our platforms
→ Co-branded webinar or content
→ Cross-referral arrangement

Our users have actually been asking for something like this. Interested in chatting?

{{sender_name}}""",
    },

    # ==================== JOB INQUIRY ====================
    {
        "id": "ji-outbound-app",
        "name": "Proactive Job Inquiry",
        "category": "Job Inquiry",
        "description": "Reach out to a company you'd love to work for, even without an open listing.",
        "subject": "Experienced {{role}} — interested in {{company_name}}",
        "body": """Hi {{first_name}},

I'm {{sender_name}}, a {{role}} with {{years_experience}} years of experience in {{industry}}.

I've been following {{company_name}} for a while and love what you're doing with {{specific_project_or_product}}. I believe my background in {{skill_1}} and {{skill_2}} could add real value to your team.

Here's a quick snapshot:
• {{achievement_1}}
• {{achievement_2}}
• {{achievement_3}}

I know you might not have an open role listed, but I'd love to explore if there's a fit. Would you be open to a conversation?

Best regards,
{{sender_name}}
{{linkedin_url}}""",
    },
    {
        "id": "ji-referral-outreach",
        "name": "Referral-Seeking Job Inquiry",
        "category": "Job Inquiry",
        "description": "Ask for a referral or introduction to the hiring manager at a target company.",
        "subject": "Seeking a referral to join {{company_name}}",
        "body": """Hi {{first_name}},

I hope this doesn't come out of nowhere — I'm reaching out because I'm very interested in the {{role}} position at {{company_name}}.

I have a strong background in {{relevant_experience}} and I've been following your team's work on {{project}}. I think I'd be a great fit.

Since you're already at {{company_name}}, would you be willing to pass along my resume to the hiring manager? I've attached it here for convenience.

Really appreciate your time — happy to return the favor anytime.

Thanks,
{{sender_name}}""",
    },
]


def get_templates_by_category():
    """Group templates by category for display."""
    categories = {}
    for t in TEMPLATES:
        cat = t["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
    return categories


def get_template_by_id(template_id):
    """Retrieve a single template by its ID."""
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    return None


def get_categories():
    """Return a list of unique category names."""
    return list(dict.fromkeys(t["category"] for t in TEMPLATES))
