"""Multi-channel outreach sequence definitions by tier.

A-Tier (score >= 75): Full multi-channel (email + LinkedIn + phone + direct mail)
B-Tier (50-74): Email + LinkedIn + phone
C-Tier (< 50): Email only
"""

from __future__ import annotations


# Template variables available:
# {{company_name}}, {{contact_name}}, {{annual_savings}}, {{system_size}},
# {{payback_years}}, {{county}}, {{building_type}}, {{roof_sqft}},
# {{trigger_event}}, {{buying_role}}

A_TIER_SEQUENCE = [
    {
        "step_number": 1,
        "channel": "email",
        "delay_days": 0,
        "target_roles": ["champion", "technical_evaluator"],
        "subject_template": "{{company_name}}: ${{annual_savings}}/yr solar savings on your {{building_type}} property",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>I noticed your {{roof_sqft}} sq ft commercial property in {{county}} County "
            "is well-positioned for solar. Our analysis shows a {{system_size}} kW system could "
            "save your company <strong>${{annual_savings}} per year</strong> with a {{payback_years}}-year payback.</p>"
            "{{trigger_event}}"
            "<p>Would you have 15 minutes this week to see the full analysis?</p>"
            "<p>Best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
    {
        "step_number": 2,
        "channel": "linkedin",
        "delay_days": 0,
        "target_roles": ["economic_buyer"],
        "subject_template": None,
        "body_template": None,
        "instructions": (
            "Hi {{contact_name}}, I'm reaching out because {{company_name}}'s "
            "{{building_type}} property in {{county}} has excellent solar potential — "
            "our analysis shows ${{annual_savings}}/yr in savings. Would love to share "
            "the full report. Happy to connect!"
        ),
    },
    {
        "step_number": 3,
        "channel": "phone",
        "delay_days": 2,
        "target_roles": ["champion"],
        "subject_template": None,
        "body_template": None,
        "instructions": (
            "CALL SCRIPT for {{contact_name}} ({{buying_role}}) at {{company_name}}:\n\n"
            "Opening: 'Hi {{contact_name}}, this is [Name] from SolarPros. I'm calling because "
            "we recently completed a solar analysis of your property in {{county}} County and "
            "found some impressive savings potential.'\n\n"
            "Key points:\n"
            "- {{system_size}} kW system on your {{roof_sqft}} sq ft roof\n"
            "- ${{annual_savings}} annual savings\n"
            "- {{payback_years}}-year payback with 30% federal tax credit\n"
            "{{trigger_event}}\n\n"
            "Ask: 'Would you have 20 minutes this week to review the full analysis?'\n\n"
            "If objection: 'I completely understand. Would it be helpful if I sent over "
            "the report by email so you can review it at your convenience?'"
        ),
    },
    {
        "step_number": 4,
        "channel": "email",
        "delay_days": 3,
        "target_roles": ["economic_buyer"],
        "subject_template": "Re: {{company_name}} solar analysis — ROI breakdown",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>I wanted to follow up with a quick financial summary for {{company_name}}:</p>"
            "<ul>"
            "<li><strong>System size:</strong> {{system_size}} kW</li>"
            "<li><strong>Annual savings:</strong> ${{annual_savings}}</li>"
            "<li><strong>Payback period:</strong> {{payback_years}} years</li>"
            "<li><strong>30% Federal ITC:</strong> Significantly reduces upfront cost</li>"
            "</ul>"
            "<p>Companies like yours in {{county}} County are seeing strong ROI on commercial solar. "
            "Happy to walk through the numbers whenever convenient.</p>"
            "<p>Best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
    {
        "step_number": 5,
        "channel": "linkedin",
        "delay_days": 5,
        "target_roles": ["technical_evaluator"],
        "subject_template": None,
        "body_template": None,
        "instructions": (
            "Hi {{contact_name}}, I sent over a solar analysis for {{company_name}}'s "
            "property showing a {{system_size}} kW system. Would love to discuss the "
            "technical details with you. Open to a quick call?"
        ),
    },
    {
        "step_number": 6,
        "channel": "phone",
        "delay_days": 7,
        "target_roles": ["economic_buyer"],
        "subject_template": None,
        "body_template": None,
        "instructions": (
            "CALL SCRIPT for {{contact_name}} (Decision Maker) at {{company_name}}:\n\n"
            "Opening: 'Hi {{contact_name}}, this is [Name] from SolarPros. I've been in touch "
            "with your team about the solar analysis we completed for your property.'\n\n"
            "Key value prop: 'What really stands out is the ${{annual_savings}} in annual savings "
            "with a {{payback_years}}-year payback. After the federal tax credit, the ROI is compelling.'\n\n"
            "Close: 'I'd love to schedule a 30-minute meeting to present the full proposal. "
            "How does your calendar look next week?'"
        ),
    },
    {
        "step_number": 7,
        "channel": "email",
        "delay_days": 10,
        "target_roles": ["champion", "technical_evaluator", "economic_buyer"],
        "subject_template": "{{county}} County commercial solar case study",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>I wanted to share a quick case study of a similar {{building_type}} property "
            "in {{county}} County that went solar last year:</p>"
            "<ul>"
            "<li>Property size: ~{{roof_sqft}} sq ft</li>"
            "<li>Annual savings: Over ${{annual_savings}}</li>"
            "<li>Installation completed in under 90 days</li>"
            "</ul>"
            "<p>Your property has very similar characteristics. Would you like to see "
            "how the numbers compare?</p>"
            "<p>Best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
    {
        "step_number": 8,
        "channel": "direct_mail",
        "delay_days": 14,
        "target_roles": ["economic_buyer"],
        "subject_template": None,
        "body_template": (
            "Dear {{contact_name}},\n\n"
            "I'm writing regarding your commercial property in {{county}} County. "
            "Our solar analysis indicates a {{system_size}} kW system could save "
            "{{company_name}} approximately ${{annual_savings}} per year.\n\n"
            "Key highlights:\n"
            "- {{payback_years}}-year payback period\n"
            "- 30% Federal Investment Tax Credit\n"
            "- Locked-in energy rates for 25+ years\n\n"
            "I'd welcome the opportunity to present the full analysis. "
            "Please feel free to reach out at your convenience.\n\n"
            "Sincerely,\n"
            "The SolarPros Team\n"
            "{{physical_address}}"
        ),
        "instructions": None,
    },
    {
        "step_number": 9,
        "channel": "email",
        "delay_days": 21,
        "target_roles": ["champion", "economic_buyer"],
        "subject_template": "Final follow-up: {{company_name}} solar analysis",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>I've reached out a few times about the solar analysis for your "
            "{{building_type}} property. I understand timing may not be right.</p>"
            "<p>If commercial solar is something {{company_name}} might explore "
            "in the future, I'm happy to keep the analysis on file. Just reply "
            "to this email whenever you'd like to revisit.</p>"
            "<p>All the best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
]

B_TIER_SEQUENCE = [
    {
        "step_number": 1,
        "channel": "email",
        "delay_days": 0,
        "target_roles": ["champion", "economic_buyer"],
        "subject_template": "{{company_name}}: Commercial solar savings analysis",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>Our analysis of your {{building_type}} property in {{county}} County shows "
            "a {{system_size}} kW solar system could save {{company_name}} "
            "<strong>${{annual_savings}} per year</strong>.</p>"
            "<p>Would you have a few minutes to review the full report?</p>"
            "<p>Best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
    {
        "step_number": 2,
        "channel": "linkedin",
        "delay_days": 3,
        "target_roles": ["economic_buyer"],
        "subject_template": None,
        "body_template": None,
        "instructions": (
            "Hi {{contact_name}}, I recently analyzed {{company_name}}'s property "
            "for solar potential and found some great savings. Would love to connect "
            "and share the report!"
        ),
    },
    {
        "step_number": 3,
        "channel": "phone",
        "delay_days": 5,
        "target_roles": ["champion", "economic_buyer"],
        "subject_template": None,
        "body_template": None,
        "instructions": (
            "CALL SCRIPT: 'Hi {{contact_name}}, this is [Name] from SolarPros. "
            "I sent over a solar analysis showing ${{annual_savings}}/yr in savings "
            "for your property. Did you have a chance to take a look? I'd love to "
            "walk you through the numbers.'"
        ),
    },
    {
        "step_number": 4,
        "channel": "email",
        "delay_days": 7,
        "target_roles": ["champion", "economic_buyer"],
        "subject_template": "Re: {{company_name}} solar savings — quick follow-up",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>Just following up on the solar analysis for your property. "
            "The {{payback_years}}-year payback makes this a strong investment, "
            "especially with the 30% federal tax credit.</p>"
            "<p>Happy to answer any questions.</p>"
            "<p>Best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
    {
        "step_number": 5,
        "channel": "email",
        "delay_days": 14,
        "target_roles": ["champion", "economic_buyer"],
        "subject_template": "Final note: {{company_name}} solar potential",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>I wanted to send one final note about the solar opportunity for your property. "
            "If the timing isn't right now, I'm happy to keep the analysis on file.</p>"
            "<p>All the best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
]

C_TIER_SEQUENCE = [
    {
        "step_number": 1,
        "channel": "email",
        "delay_days": 0,
        "target_roles": ["champion", "economic_buyer"],
        "subject_template": "Solar savings opportunity for {{company_name}}",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>We've identified your commercial property in {{county}} County as a "
            "good candidate for solar energy. A {{system_size}} kW system could "
            "save approximately ${{annual_savings}} per year.</p>"
            "<p>Interested in learning more?</p>"
            "<p>Best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
    {
        "step_number": 2,
        "channel": "email",
        "delay_days": 3,
        "target_roles": ["champion", "economic_buyer"],
        "subject_template": "Re: Solar for {{company_name}}",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>Quick follow-up on the solar analysis for your property. "
            "With a {{payback_years}}-year payback, the numbers are compelling.</p>"
            "<p>Happy to share the full report.</p>"
            "<p>Best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
    {
        "step_number": 3,
        "channel": "email",
        "delay_days": 7,
        "target_roles": ["champion", "economic_buyer"],
        "subject_template": "Last note: {{company_name}} solar opportunity",
        "body_template": (
            "<p>Hi {{contact_name}},</p>"
            "<p>Just a final note about the solar opportunity for your property. "
            "If you'd like to revisit this in the future, don't hesitate to reach out.</p>"
            "<p>All the best,<br>The SolarPros Team</p>"
            '<p style="font-size:11px;color:#888">{{physical_address}}<br>'
            '<a href="{{unsubscribe_link}}">Unsubscribe</a></p>'
        ),
        "instructions": None,
    },
]


def get_sequence_for_tier(tier: str) -> list[dict]:
    """Return the outreach sequence for a given prospect tier."""
    if tier == "A":
        return A_TIER_SEQUENCE
    if tier == "B":
        return B_TIER_SEQUENCE
    return C_TIER_SEQUENCE
