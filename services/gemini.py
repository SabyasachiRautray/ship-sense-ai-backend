import google.generativeai as genai
from openai import OpenAI
import json
import re
import time
import hashlib
from datetime import datetime
from config import GEMINI_API_KEY, NVIDIA_API_KEY

nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

_CACHE     = {}
CACHE_TTL  = 3600


def _cache_key(shipment, weather, traffic) -> str:
    road = traffic.get("road", {})
    raw  = f"{shipment['origin']}-{shipment['destination']}-{road.get('congestion_level')}-{weather.get('description')}"
    return hashlib.md5(raw.encode()).hexdigest()


def _compute_time_gaps(shipment: dict) -> dict:
    """Pre-compute all time deltas so the model doesn't have to."""
    now = datetime.utcnow()
    gaps = {
        "now_utc":              now.strftime("%Y-%m-%d %H:%M UTC"),
        "hours_until_eta":      None,
        "hours_until_sla":      None,
        "sla_buffer_hours":     None,   # how much slack after ETA before SLA breach
        "is_eta_after_sla":     False,  # ETA already breaches SLA
    }
    try:
        eta_str = shipment["eta"].replace("T", " ").split(".")[0]
        sla_str = shipment["sla_deadline"].replace("T", " ").split(".")[0]
        eta = datetime.fromisoformat(eta_str)
        sla = datetime.fromisoformat(sla_str)
        gaps["hours_until_eta"]  = round((eta - now).total_seconds() / 3600, 2)
        gaps["hours_until_sla"]  = round((sla - now).total_seconds() / 3600, 2)
        gaps["sla_buffer_hours"] = round((sla - eta).total_seconds() / 3600, 2)
        gaps["is_eta_after_sla"] = eta > sla
    except Exception as e:
        print(f"⚠️ Time gap computation failed: {e}")
    return gaps


def _build_prompt(shipment, weather, traffic, news) -> str:
    road  = traffic.get("road",  {})
    air   = traffic.get("air",   {})
    water = traffic.get("water", {})
    alt   = road.get("alternate_route")

    # Pre-compute time gaps — critical for accurate delay estimation
    gaps = _compute_time_gaps(shipment)

    air_line   = f"AIR via {air.get('via','?')}: {air['duration_hours']}h available"      if air.get("available")   else "AIR: Not available"
    water_line = f"WATER via {water.get('via','?')}: {water['duration_hours']}h available" if water.get("available") else "WATER: Not available"
    alt_line   = (f"ALTERNATE ROAD via {alt['via']}: {alt['duration_hours']}h "
                  f"(saves {alt['time_saved_hours']}h vs current road)")                   if alt else "ALTERNATE ROAD: None"

    news_summary = "\n".join(
        f"  - {n['title'][:100]}" for n in news[:3]
    ) if news else "  - No active disruptions reported"

    # SLA breach warning line
    if gaps["is_eta_after_sla"]:
        sla_status = f"⚠️ CRITICAL: ETA already exceeds SLA deadline by {abs(gaps['sla_buffer_hours']):.1f}h — SLA BREACH IS CERTAIN"
    elif gaps["sla_buffer_hours"] is not None and gaps["sla_buffer_hours"] < 2:
        sla_status = f"⚠️ WARNING: Only {gaps['sla_buffer_hours']:.1f}h buffer between ETA and SLA — any delay causes breach"
    elif gaps["sla_buffer_hours"] is not None:
        sla_status = f"Buffer: {gaps['sla_buffer_hours']:.1f}h between ETA and SLA deadline"
    else:
        sla_status = "SLA buffer: unknown"

    return f"""You are a senior logistics risk analyst with expertise in supply chain disruptions.
Your task is to assess shipment delay risk and estimate the precise delay in hours.
Respond ONLY with a valid JSON object. No markdown, no explanation, no text outside the JSON.

═══════════════════════════════════════════
SHIPMENT DETAILS
═══════════════════════════════════════════
Shipment ID : {shipment['shipment_id']}
Route       : {shipment['origin']} → {shipment['destination']}
Carrier     : {shipment['carrier']}

TIMELINE (all times in UTC):
  Current time       : {gaps['now_utc']}
  ETA                : {shipment['eta']}
  SLA Deadline       : {shipment['sla_deadline']}
  Hours until ETA    : {gaps['hours_until_eta']}h
  Hours until SLA    : {gaps['hours_until_sla']}h
  SLA buffer after ETA: {gaps['sla_buffer_hours']}h
  SLA STATUS         : {sla_status}

═══════════════════════════════════════════
LIVE SIGNAL DATA
═══════════════════════════════════════════
WEATHER at {shipment['origin']}:
  Condition  : {weather.get('description', 'unknown')}
  Temperature: {weather.get('temp', 'N/A')}°C
  Wind Speed : {weather.get('wind_speed', 0)} m/s
  Severity   : {weather.get('severity', 0)}/10
  (severity ≥7 = major weather delay expected; 4-6 = moderate; <4 = minor)

ROAD CONDITIONS:
  Distance   : {road.get('distance_km', 'N/A')} km
  Normal time: {road.get('duration_hours', 'N/A')}h
  Current ETA delay: {road.get('estimated_delay_hours', 0)}h due to congestion
  Congestion : {road.get('congestion_level', 'Unknown')}
  {alt_line}

ALTERNATIVE TRANSPORT:
  {air_line}
  {water_line}
  Fastest available: {traffic.get('fastest_mode', 'road')} at {traffic.get('fastest_hours', 'N/A')}h

NEWS & DISRUPTIONS:
{news_summary}

═══════════════════════════════════════════
DELAY ESTIMATION INSTRUCTIONS
═══════════════════════════════════════════
Calculate estimated_delay_hours using this logic:
1. Start with road congestion delay: {road.get('estimated_delay_hours', 0)}h
2. Add weather contribution: severity/10 × 2.0h  →  +{round(weather.get('severity', 0) / 10 * 2.0, 2)}h
3. Add news disruption penalty: +1.0h per active disruption (max +3.0h)
4. If ETA buffer < 2h, add +1.5h urgency factor
5. If ETA already exceeds SLA, delay = hours_until_eta + congestion delay
6. Round to 1 decimal place

Your estimated_delay_hours MUST be consistent with your risk_score:
  - risk_score >70  → delay typically ≥3h
  - risk_score 40-70 → delay typically 1-3h
  - risk_score <40  → delay typically <1h

═══════════════════════════════════════════
RISK SCORING RULES
═══════════════════════════════════════════
Score the risk 0-100:
  +35 if SLA breach is already certain (ETA > SLA)
  +25 if buffer < 2h
  +20 if weather severity ≥ 7
  +10 if weather severity 4-6
  +20 if road congestion = High
  +10 if road congestion = Medium
  +15 if active news disruptions exist
  +10 if road delay > 2h
  +5  if road delay 1-2h
  Cap at 98

risk_level:
  High   → score > 70
  Medium → score 40-70
  Low    → score < 40

═══════════════════════════════════════════
RECOMMENDATION RULES
═══════════════════════════════════════════
Use EXACTLY one of these strings:
  "reroute shipment"            → High risk + faster alternative exists
  "assign alternative carrier"  → High risk + current carrier unreliable
  "send pre-alert to customer"  → Medium/High risk + SLA breach likely
  "expedite dispatch"           → Medium risk + time still available
  "monitor closely"             → Low risk

═══════════════════════════════════════════
RESPONSE FORMAT — Return this exact JSON:
═══════════════════════════════════════════
{{
  "risk_score": <integer 0-100>,
  "risk_level": "<High|Medium|Low>",
  "reasons": [
    "<reason 1: cite specific numbers from the data above>",
    "<reason 2: cite specific numbers from the data above>",
    "<reason 3: cite specific numbers from the data above>"
  ],
  "recommendation": "<exact string from recommendation rules>",
  "recommended_route": {{
    "mode": "<road|air|water>",
    "via": "<specific route description>",
    "estimated_hours": <float>,
    "time_saved_hours": <float>,
    "reason": "<concrete reason citing time and cost savings>"
  }},
  "estimated_delay_hours": <float — calculated per delay estimation instructions>,
  "confidence": "<percentage e.g. 87%>"
}}"""


def analyze_with_gemini(shipment: dict, weather: dict, traffic: dict, news: list) -> dict:
    road  = traffic.get("road",  {})
    air   = traffic.get("air",   {})
    water = traffic.get("water", {})

    # Check cache
    ck = _cache_key(shipment, weather, traffic)
    if ck in _CACHE:
        cached_time, cached_result = _CACHE[ck]
        if time.time() - cached_time < CACHE_TTL:
            print(f"📦 Cache hit for {shipment['origin']}→{shipment['destination']}")
            return cached_result

    prompt = _build_prompt(shipment, weather, traffic, news)

    # ── 1. NVIDIA Llama (primary) ──────────────────────
    try:
        response = nvidia_client.chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a logistics risk analyst AI. "
                        "You ONLY output valid JSON. No markdown fences, no explanation, "
                        "no text before or after the JSON object. "
                        "Every numeric field must be a number, not a string."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.15,   # slightly higher than 0.1 for more nuanced scoring
            max_tokens=700,
        )
        raw    = response.choices[0].message.content.strip()
        raw    = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)

        # Post-process: clamp and validate estimated_delay_hours
        result = _validate_and_fix(result, traffic, weather)

        _CACHE[ck] = (time.time(), result)
        print(f"✅ NVIDIA Llama responded for {shipment['origin']}→{shipment['destination']}")
        return result

    except json.JSONDecodeError as e:
        print(f"❌ Llama returned invalid JSON: {e}")

    except Exception as e:
        print(f"❌ NVIDIA failed: {e}")

    # ── 2. Smart fallback ──────────────────────────────
    print("⚠️ All models failed — using smart fallback")
    return _smart_fallback(shipment, traffic, road, air, water, weather)


def _validate_and_fix(result: dict, traffic: dict, weather: dict) -> dict:
    """Ensure delay hours are consistent with risk score and real signal data."""
    road        = traffic.get("road", {})
    congestion  = road.get("estimated_delay_hours", 0)
    severity    = weather.get("severity", 0)
    weather_add = round(severity / 10 * 2.0, 2)
    base_delay  = round(congestion + weather_add, 2)

    score = result.get("risk_score", 0)

    # If model returned 0 or unrealistically low delay, recalculate
    model_delay = result.get("estimated_delay_hours", 0)
    if model_delay == 0 and base_delay > 0:
        result["estimated_delay_hours"] = base_delay
        print(f"🔧 Fixed delay: 0 → {base_delay}h")
    elif score > 70 and model_delay < 2.0:
        result["estimated_delay_hours"] = max(base_delay, 2.0)
        print(f"🔧 Fixed delay for High risk: {model_delay} → {result['estimated_delay_hours']}h")
    elif score > 40 and model_delay < 0.5:
        result["estimated_delay_hours"] = max(base_delay, 0.5)
        print(f"🔧 Fixed delay for Medium risk: {model_delay} → {result['estimated_delay_hours']}h")

    # Clamp risk_score
    result["risk_score"] = max(0, min(98, int(result.get("risk_score", 0))))

    return result


def _smart_fallback(shipment, traffic, road, air, water, weather={}) -> dict:
    fastest     = traffic.get("fastest_mode", "road")
    fastest_hrs = traffic.get("fastest_hours", road.get("duration_hours", 9.0))
    road_hrs    = road.get("duration_hours", 9.0)
    congestion  = road.get("congestion_level", "Medium")
    road_delay  = road.get("estimated_delay_hours", 1.5)
    severity    = weather.get("severity", 0)
    time_saved  = round(max(road_hrs - fastest_hrs, 0), 2)

    best_via = (
        air.get("via")   if fastest == "air"   else
        water.get("via") if fastest == "water" else
        f"{shipment['origin']}→{shipment['destination']}"
    )

    # Calculate delay the same way the prompt instructs
    weather_add = round(severity / 10 * 2.0, 2)
    estimated_delay = round(road_delay + weather_add, 2)

    # Score
    risk_score = 0
    if congestion == "High":   risk_score += 20
    if congestion == "Medium": risk_score += 10
    if road_delay > 2:         risk_score += 10
    elif road_delay > 1:       risk_score += 5
    if severity >= 7:          risk_score += 20
    elif severity >= 4:        risk_score += 10
    risk_score = min(risk_score, 95)
    risk_level = "High" if risk_score > 70 else "Medium" if risk_score > 40 else "Low"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reasons": [
            f"Road journey of {road_hrs}h over {road.get('distance_km', '?')}km with {congestion} congestion",
            f"Estimated road delay of {road_delay}h plus weather adds {weather_add}h",
            f"Fastest alternative is {fastest} at {fastest_hrs}h, saving {time_saved}h"
        ],
        "recommendation": "send pre-alert to customer" if risk_level == "High" else "monitor closely",
        "recommended_route": {
            "mode":             fastest,
            "via":              best_via or f"{shipment['origin']}→{shipment['destination']}",
            "estimated_hours":  fastest_hrs,
            "time_saved_hours": time_saved,
            "reason":           f"{fastest.capitalize()} route saves {time_saved}h vs road"
        },
        "estimated_delay_hours": estimated_delay,
        "confidence":            "65%"
    }