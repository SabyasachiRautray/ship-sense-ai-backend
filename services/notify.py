import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

SMTP_EMAIL    = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))


def notify_partner(
    partner_name: str,
    partner_email: str,
    partner_phone: str,
    route: str,
    affected_shipments: list,
    risk_score: int,
    recommendation: str,
    recommended_route: dict,
):
    try:
        subject = f" HIGH RISK ALERT — Route {route}"

        shipment_list = "\n".join([f"  • {s}" for s in affected_shipments])
        route_info = ""
        if recommended_route:
            route_info = f"""
Recommended Route:
  Mode     : {recommended_route.get('mode', 'N/A').upper()}
  Via      : {recommended_route.get('via', 'N/A')}
  Duration : {recommended_route.get('estimated_hours', 'N/A')} hours
  Time Saved: {recommended_route.get('time_saved_hours', 0)} hours
  Reason   : {recommended_route.get('reason', 'N/A')}
"""

        body = f"""
Dear {partner_name},

ShipSense AI has detected a HIGH RISK situation on your assigned route.

Route          : {route}
Risk Score     : {risk_score}/100
Recommendation : {recommendation.upper()}

Affected Shipments:
{shipment_list}
{route_info}
Please take immediate action to prevent SLA breaches.

— ShipSense AI Early Warning System
"""

        msg = MIMEMultipart()
        msg["From"]    = SMTP_EMAIL
        msg["To"]      = partner_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        print(f" Notified partner {partner_name} at {partner_email}")

    except Exception as e:
        # Don't crash the analysis if email fails
        print(f" Email notification failed: {e}")