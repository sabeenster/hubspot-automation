from datetime import timedelta
from html import escape
from typing import List

from .automation import is_due_to_draft, recommended_confirmation_template_name, scheduled_from_timestamp
from .models import ApprovalRequest, Lead, Template


def render_admin_page(
    leads: List[Lead],
    templates: List[Template],
    approval_requests: List[ApprovalRequest],
    flash_message: str = "",
    admin_token: str = "",
    automatic_draft_enabled: bool = False,
) -> str:
    template_rows = "\n".join(render_template_row(template, admin_token) for template in templates)
    lead_rows = "\n".join(render_lead_row(lead, templates, admin_token) for lead in leads[:50])
    approval_rows = "\n".join(
        render_approval_row(request, leads, templates, admin_token) for request in approval_requests[:50]
    )
    flash_html = (
        f'<div class="flash">{escape(flash_message)}</div>' if flash_message else ""
    )
    auto_state = (
        "Automatic Gmail draft creation is ON."
        if automatic_draft_enabled
        else "Automatic Gmail draft creation is OFF. Manual draft creation is available."
    )
    auto_class = "auto-on" if automatic_draft_enabled else "auto-off"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Agentway Automation Admin</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --card: #fffaf4;
      --ink: #1f1a17;
      --muted: #6f655f;
      --line: #dbcfc4;
      --accent: #0f766e;
      --accent-2: #b45309;
      --danger: #9f1239;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Iowan Old Style", "Palatino Linotype", serif;
      background:
        radial-gradient(circle at top left, rgba(180,83,9,0.08), transparent 28%),
        linear-gradient(180deg, #f8f4ed 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    .wrap {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }}
    .hero {{
      display: grid;
      gap: 14px;
      margin-bottom: 24px;
    }}
    .eyebrow {{
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 12px;
      font-weight: 700;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(34px, 5vw, 58px);
      line-height: 0.95;
      font-weight: 700;
    }}
    .subtitle {{
      max-width: 760px;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.5;
      margin: 0;
    }}
    .flash {{
      margin: 18px 0 0;
      padding: 14px 16px;
      border: 1px solid rgba(15,118,110,0.22);
      background: rgba(15,118,110,0.08);
      color: var(--accent);
      border-radius: 16px;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    .auto-state {{
      padding: 14px 16px;
      border-radius: 16px;
      font-family: "Helvetica Neue", Arial, sans-serif;
      font-size: 14px;
      border: 1px solid var(--line);
    }}
    .auto-off {{
      background: rgba(159,18,57,0.08);
      color: var(--danger);
      border-color: rgba(159,18,57,0.2);
    }}
    .auto-on {{
      background: rgba(15,118,110,0.08);
      color: var(--accent);
      border-color: rgba(15,118,110,0.2);
    }}
    .grid {{
      display: grid;
      grid-template-columns: 360px minmax(0, 1fr);
      gap: 22px;
      align-items: start;
    }}
    .card {{
      background: rgba(255,250,244,0.9);
      backdrop-filter: blur(8px);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 18px 60px rgba(31,26,23,0.06);
      overflow: hidden;
    }}
    .card h2 {{
      margin: 0;
      padding: 22px 22px 8px;
      font-size: 22px;
    }}
    .card-copy {{
      margin: 0;
      padding: 0 22px 18px;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.5;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    .template-stack {{
      display: grid;
      gap: 14px;
      padding: 0 16px 18px;
    }}
    .template-row {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: #fffdf9;
      display: grid;
      gap: 12px;
    }}
    .template-row strong {{
      display: block;
      font-size: 16px;
    }}
    .meta {{
      color: var(--muted);
      font-size: 13px;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    .inputs {{
      display: grid;
      grid-template-columns: 1fr 1fr auto;
      gap: 10px;
      align-items: end;
    }}
    label {{
      display: grid;
      gap: 6px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--muted);
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    input, select, button {{
      font: inherit;
    }}
    input[type="number"], input[type="password"], select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 11px 12px;
      background: white;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    input[type="text"], textarea {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 11px 12px;
      background: white;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    textarea {{
      min-height: 156px;
      resize: vertical;
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 12px 16px;
      background: var(--ink);
      color: white;
      cursor: pointer;
      font-family: "Helvetica Neue", Arial, sans-serif;
      font-weight: 700;
    }}
    button.secondary {{
      background: white;
      color: var(--ink);
      border: 1px solid var(--line);
    }}
    .leads {{
      padding: 0 16px 18px;
      display: grid;
      gap: 14px;
    }}
    .lead-row {{
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(255,248,240,0.95));
      display: grid;
      gap: 14px;
    }}
    .lead-top {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }}
    .lead-name {{
      font-size: 24px;
      line-height: 1;
      margin-bottom: 6px;
    }}
    .lead-email {{
      color: var(--muted);
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    .badge {{
      white-space: nowrap;
      border-radius: 999px;
      padding: 8px 10px;
      background: rgba(180,83,9,0.1);
      color: var(--accent-2);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    .facts {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 18px;
      color: var(--muted);
      font-size: 13px;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    .facts span strong {{
      color: var(--ink);
      font-weight: 700;
    }}
    .actions {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: end;
    }}
    .hint {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    .empty {{
      padding: 22px;
      color: var(--muted);
      font-family: "Helvetica Neue", Arial, sans-serif;
    }}
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .inputs, .actions {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">Agentway Ops Console</div>
      <h1>Turn new leads into ready-to-review drafts.</h1>
      <p class="subtitle">Agentway watches HubSpot, prepares personalized Gmail drafts, and leaves the final review and Send click to you.</p>
      <div class="auto-state {auto_class}">{escape(auto_state)}</div>
      {flash_html}
    </section>
    <section class="grid">
      <article class="card">
        <h2>Delay Settings</h2>
        <p class="card-copy">These template delays control when Agentway creates a Gmail draft. Update them here without a code change.</p>
        <div class="template-stack">
          {template_rows or '<div class="empty">No templates available.</div>'}
        </div>
      </article>
      <article class="card">
        <h2>Pending Draft Requests</h2>
        <p class="card-copy">New email submissions and demo bookings land here until their Gmail draft has been created.</p>
        <div class="leads">
          {approval_rows or '<div class="empty">No approvals pending right now.</div>'}
        </div>
      </article>
      <article class="card">
        <h2>Create a Draft Manually</h2>
        <p class="card-copy">Choose a lead and template to create an additional Gmail draft for review.</p>
        <div class="leads">
          {lead_rows or '<div class="empty">No leads found yet.</div>'}
        </div>
      </article>
    </section>
  </div>
</body>
</html>"""


def render_template_row(template: Template, admin_token: str) -> str:
    hidden = render_hidden_token(admin_token)
    return f"""
    <form class="template-row" method="post" action="/admin/templates">
      {hidden}
      <input type="hidden" name="template_name" value="{escape(template.template_name)}" />
      <div>
        <strong>{escape(template.template_name)}</strong>
        <div class="meta">Lead type: {escape(template.lead_type)} | Current delay: {template.delay_days} days, {template.delay_minutes} minutes</div>
      </div>
      <div class="inputs">
        <label>Delay Days
          <input type="number" name="delay_days" min="0" value="{template.delay_days}" />
        </label>
        <label>Delay Minutes
          <input type="number" name="delay_minutes" min="0" value="{template.delay_minutes}" />
        </label>
        <button type="submit">Save Delay</button>
      </div>
      <label>Subject
        <input type="text" name="subject" value="{escape(template.subject)}" />
      </label>
      <label>Body
        <textarea name="body">{escape(template.body)}</textarea>
      </label>
    </form>
    """


def render_approval_row(
    approval_request: ApprovalRequest,
    leads: List[Lead],
    templates: List[Template],
    admin_token: str,
) -> str:
    lead = next((item for item in leads if item.lead_id == approval_request.lead_id), None)
    template = next((item for item in templates if item.template_name == approval_request.template_name), None)
    display_name = (
        f"{(lead.first_name if lead else '') or ''} {(lead.last_name if lead else '') or ''}".strip()
        or (lead.email if lead else approval_request.lead_id)
    )
    hidden = render_hidden_token(admin_token)
    return f"""
    <form class="lead-row" method="post" action="/admin/create-request-draft">
      {hidden}
      <input type="hidden" name="approval_request_id" value="{escape(approval_request.approval_request_id)}" />
      <input type="hidden" name="approval_token" value="{escape(approval_request.approval_token)}" />
      <div class="lead-top">
        <div>
          <div class="lead-name">{escape(display_name)}</div>
          <div class="lead-email">{escape(lead.email if lead else '')}</div>
        </div>
        <div class="badge">{escape(approval_request.status)}</div>
      </div>
      <div class="facts">
        <span><strong>Template:</strong> {escape(approval_request.template_name)}</span>
        <span><strong>Reason:</strong> {escape(approval_request.reason)}</span>
        <span><strong>Requested:</strong> {escape(approval_request.requested_at)}</span>
        <span><strong>Source:</strong> {escape((lead.source if lead else '') or 'unknown')}</span>
      </div>
      <div class="actions">
        <div class="hint">
          {escape(template.subject if template else '')}
        </div>
        <div style="display:grid;gap:10px;">
          <button type="submit">Create Gmail Draft</button>
        </div>
      </div>
    </form>
    """


def render_lead_row(lead: Lead, templates: List[Template], admin_token: str) -> str:
    first_name = lead.first_name or ""
    last_name = lead.last_name or ""
    display_name = f"{first_name} {last_name}".strip() or (lead.email or "Unknown lead")
    template_name = recommended_confirmation_template_name(lead)
    template = next((item for item in templates if item.template_name == template_name), None)
    if template:
      anchor = scheduled_from_timestamp(lead, template)
      due_at = anchor + timedelta(days=template.delay_days, minutes=template.delay_minutes)
      due_text = due_at.isoformat().replace("+00:00", "Z")
      due_now = is_due_to_draft(lead, template)
      delay_copy = f"{template.delay_days}d {template.delay_minutes}m"
    else:
      due_text = "n/a"
      due_now = False
      delay_copy = "n/a"

    hidden = render_hidden_token(admin_token)
    options = "".join(
        render_template_option(template, template_name)
        for template in templates
        if template.template_name in {
            "email_signup_confirmation",
            "demo_booking_confirmation",
            "post_demo_followup",
        }
    )
    return f"""
    <form class="lead-row" method="post" action="/admin/create-draft">
      {hidden}
      <input type="hidden" name="lead_id" value="{escape(lead.lead_id)}" />
        <div class="lead-top">
        <div>
          <div class="lead-name">{escape(display_name)}</div>
          <div class="lead-email">{escape(lead.email or "")}</div>
        </div>
        <div class="badge">{escape(lead.lead_type or 'lead')}</div>
      </div>
      <div class="facts">
        <span><strong>Status:</strong> {escape(lead.status or 'new')}</span>
        <span><strong>Source:</strong> {escape(lead.source or 'unknown')}</span>
        <span><strong>Campaign:</strong> {escape(lead.ad_campaign_name or lead.utm_campaign or 'n/a')}</span>
        <span><strong>Template:</strong> {escape(template_name or 'none')}</span>
      </div>
      <div class="actions">
        <div class="hint">
          Delay window: {escape(delay_copy)}. Due from: {escape(due_text)}. Currently {'eligible to draft' if due_now else 'waiting for delay window'}.
        </div>
        <div style="display:grid;gap:10px;">
          <label>Template
            <select name="template_name">{options}</select>
          </label>
          <button type="submit">Create Gmail Draft</button>
        </div>
      </div>
    </form>
    """


def render_hidden_token(admin_token: str) -> str:
    if not admin_token:
        return ""
    return f'<input type="hidden" name="admin_token" value="{escape(admin_token)}" />'


def render_template_option(template: Template, selected_template_name: str) -> str:
    selected = " selected" if template.template_name == selected_template_name else ""
    return f'<option value="{escape(template.template_name)}"{selected}>{escape(template.template_name)}</option>'
