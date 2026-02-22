"""Email sequence templates for the drip campaign.

All templates use {{variable}} placeholders that are replaced during
personalization. Every template includes a CAN-SPAM compliant footer.
"""

CAN_SPAM_FOOTER = """
<hr style="margin-top: 40px; border: none; border-top: 1px solid #ccc;">
<p style="font-size: 11px; color: #999; line-height: 1.5;">
  You are receiving this email because your commercial property may qualify for
  significant solar energy savings. If you no longer wish to receive these emails,
  you can <a href="{{unsubscribe_link}}" style="color: #999;">unsubscribe here</a>.
  <br><br>
  {{physical_address}}
</p>
""".strip()

EMAIL_SEQUENCES: list[dict] = [
    {
        "step_number": 1,
        "delay_days": 0,
        "subject_template": "Solar Savings for {{company_name}}",
        "body_template": """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Hi {{contact_name}},</p>

  <p>I came across {{company_name}} and noticed your {{building_type}} property in
  {{county}} County could be an excellent candidate for commercial solar.</p>

  <p>Based on our preliminary analysis, your roof has the potential to support a
  <strong>{{system_size}} kW solar system</strong>, which could save you approximately
  <strong>{{annual_savings}} per year</strong> on electricity costs.</p>

  <p>With current federal tax incentives covering 30% of system costs, many
  businesses like yours are seeing a full return on investment in just
  {{payback_years}} years.</p>

  <p>Would you be open to a quick 15-minute call to explore whether solar makes
  sense for {{company_name}}?</p>

  <p>Best regards,<br>
  The SolarPros Team</p>

  COMPLIANCE_FOOTER
</div>
""".strip().replace("COMPLIANCE_FOOTER", CAN_SPAM_FOOTER),
    },
    {
        "step_number": 2,
        "delay_days": 3,
        "subject_template": "{{company_name}}: Your Roof Could Save You {{annual_savings}}/Year",
        "body_template": """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Hi {{contact_name}},</p>

  <p>I wanted to follow up on my previous email about solar potential for
  {{company_name}}.</p>

  <p>Here is a deeper look at the numbers for your {{building_type}} in {{county}} County:</p>

  <ul style="line-height: 1.8;">
    <li><strong>Recommended System Size:</strong> {{system_size}} kW</li>
    <li><strong>Estimated Annual Savings:</strong> {{annual_savings}}</li>
    <li><strong>Payback Period:</strong> {{payback_years}} years</li>
    <li><strong>25-Year Net Savings:</strong> Significant long-term value</li>
  </ul>

  <p>These estimates are based on your roof area, local sunshine data, and current
  utility rates in your area. The 30% federal Investment Tax Credit (ITC) plus
  any state and local incentives can reduce your upfront costs considerably.</p>

  <p>Many commercial property owners are also using solar to meet ESG goals and
  demonstrate environmental leadership to their customers.</p>

  <p>I would love to prepare a detailed, no-obligation proposal for
  {{company_name}}. Can we set up a brief call this week?</p>

  <p>Best regards,<br>
  The SolarPros Team</p>

  COMPLIANCE_FOOTER
</div>
""".strip().replace("COMPLIANCE_FOOTER", CAN_SPAM_FOOTER),
    },
    {
        "step_number": 3,
        "delay_days": 7,
        "subject_template": "How Businesses Like {{company_name}} Are Cutting Energy Costs",
        "body_template": """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Hi {{contact_name}},</p>

  <p>Did you know that commercial solar adoption has grown over 25% year-over-year?
  Businesses across {{county}} County are making the switch, and the results speak
  for themselves.</p>

  <h3 style="color: #2c5f2d;">Case Study Highlights:</h3>

  <p><strong>A retail center in Southern California</strong> installed a 150 kW
  system and cut electricity costs by 60%, saving over $45,000 annually.</p>

  <p><strong>A warehouse and distribution facility</strong> used its expansive
  flat roof for a 300 kW installation, achieving payback in under 5 years.</p>

  <p><strong>A professional office building</strong> went solar and now markets
  itself as a green building, attracting environmentally conscious tenants willing
  to pay premium rents.</p>

  <p>Your {{building_type}} property is well-positioned to achieve similar results.
  With a {{system_size}} kW system, {{company_name}} could join the growing list
  of businesses benefiting from clean, affordable solar energy.</p>

  <p>Can I send you a free solar assessment for your property? It takes just a few
  minutes to review, and there is absolutely no obligation.</p>

  <p>Best regards,<br>
  The SolarPros Team</p>

  COMPLIANCE_FOOTER
</div>
""".strip().replace("COMPLIANCE_FOOTER", CAN_SPAM_FOOTER),
    },
    {
        "step_number": 4,
        "delay_days": 14,
        "subject_template": "Last Chance: {{company_name}} Solar Assessment Offer",
        "body_template": """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Hi {{contact_name}},</p>

  <p>This is my final follow-up regarding the solar opportunity for
  {{company_name}}.</p>

  <p>I understand you are busy, so I will keep this brief: we are offering a
  <strong>complimentary solar assessment</strong> for qualifying commercial
  properties in {{county}} County, and your {{building_type}} qualifies.</p>

  <p>Here is what the free assessment includes:</p>

  <ul style="line-height: 1.8;">
    <li>Detailed roof analysis using satellite imagery and solar irradiance data</li>
    <li>Custom system design (estimated at {{system_size}} kW for your property)</li>
    <li>Full financial projections including {{annual_savings}}/year in savings</li>
    <li>Available incentives and financing options breakdown</li>
    <li>{{payback_years}}-year payback timeline and ROI analysis</li>
  </ul>

  <p>This offer is available for a limited time as we finalize our assessments for
  this quarter. If you are even slightly curious, I would encourage you to take
  advantage of this no-cost, no-obligation analysis.</p>

  <p>Simply reply to this email or click below to schedule a call, and we will take
  care of the rest.</p>

  <p>Wishing you and {{company_name}} continued success,<br>
  The SolarPros Team</p>

  COMPLIANCE_FOOTER
</div>
""".strip().replace("COMPLIANCE_FOOTER", CAN_SPAM_FOOTER),
    },
]
