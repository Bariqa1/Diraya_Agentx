"""Environment and Heat Stress Assessment Agent for DIRAYA.

Implements standard occupational safety formulas:
  - Stull's Equation for Wet-Bulb Temperature (Twb) estimation
  - Wet-Bulb Globe Temperature (WBGT) calculation per OSHA & ISO 7243
  - Workload & Acclimatization Thresholds
  - Saudi Arabia Ministry of Human Resources Midday Outdoor Sun Ban Verification
    (قرار وزارة الموارد البشرية بحظر العمل تحت أشعة الشمس من 15 يونيو إلى 15 سبتمبر بين 12:00 و 15:00)
"""
import math
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from tools.weather_service import WeatherService


class EnvironmentAgent:
    """Evaluates environmental heat hazards and regulatory weather compliance."""

    def __init__(self, weather_service: Optional[WeatherService] = None):
        self.name = "Environment Agent"
        self.weather_service = weather_service or WeatherService()

    # =========================================================
    # 1. WET BULB & GLOBE TEMPERATURE (Stull's Equation & ISO 7243)
    # =========================================================

    @staticmethod
    def estimate_wet_bulb(temperature_c: float, humidity: float) -> float:
        """
        Calculates wet-bulb temperature using Stull (2011) equation.
        Accurate to within ~0.3°C for standard surface conditions.
        """
        rh = max(1.0, min(float(humidity), 100.0))
        t = float(temperature_c)

        wet_bulb = (
            t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
            + math.atan(t + rh)
            - math.atan(rh - 1.676331)
            + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
            - 4.686035
        )
        return wet_bulb

    @staticmethod
    def estimate_globe_temperature(
        temperature_c: float,
        outdoor: bool = True,
        direct_sun: bool = False,
    ) -> float:
        """Estimates globe temperature (Tg) accounting for radiant solar heat load."""
        if not outdoor:
            return float(temperature_c)
        if direct_sun:
            return float(temperature_c) + 10.0
        return float(temperature_c) + 3.0

    def calculate_estimated_wbgt(
        self,
        temperature_c: float,
        humidity: float,
        wind_speed: float = 0.0,
        outdoor: bool = True,
        direct_sun: bool = False,
    ) -> Dict[str, float]:
        """
        Calculates estimated Wet Bulb Globe Temperature (WBGT) in °C.
        Formula (OSHA / ISO 7243):
          - Outdoor with solar load: WBGT = 0.7*Tw + 0.2*Tg + 0.1*Td
          - Indoor / shaded:        WBGT = 0.7*Tw + 0.3*Tg
        """
        wet_bulb = self.estimate_wet_bulb(temperature_c, humidity)
        globe_temp = self.estimate_globe_temperature(temperature_c, outdoor, direct_sun)

        if outdoor and direct_sun:
            wbgt = (0.7 * wet_bulb) + (0.2 * globe_temp) + (0.1 * temperature_c)
        else:
            wbgt = (0.7 * wet_bulb) + (0.3 * globe_temp)

        return {
            "wet_bulb_c": round(wet_bulb, 1),
            "globe_temperature_c": round(globe_temp, 1),
            "estimated_wbgt_c": round(wbgt, 1),
        }

    # =========================================================
    # 2. WORKLOAD THRESHOLDS & ACCLIMATIZATION
    # =========================================================

    @staticmethod
    def get_workload_threshold(workload: str, acclimatized: bool = True) -> float:
        """Thresholds in °C WBGT based on metabolic work rate (ISO 7243 / ACGIH)."""
        thresholds_unacclimatized = {
            "light": 28.0,
            "moderate": 25.0,
            "heavy": 23.0,
            "very_heavy": 21.0,
        }
        thresholds_acclimatized = {
            "light": 30.0,
            "moderate": 28.0,
            "heavy": 26.0,
            "very_heavy": 25.0,
        }

        wl = workload.lower().strip()
        if wl not in thresholds_acclimatized:
            wl = "moderate"

        return thresholds_acclimatized[wl] if acclimatized else thresholds_unacclimatized[wl]

    def assess_heat_exposure(
        self,
        wbgt: float,
        workload: str = "moderate",
        acclimatized: bool = True,
    ) -> Dict:
        """Classifies risk into LOW, MODERATE, HIGH, VERY_HIGH based on WBGT delta."""
        threshold = self.get_workload_threshold(workload, acclimatized)
        delta = wbgt - threshold

        if delta <= -3.0:
            risk = "LOW"
        elif delta <= 0.0:
            risk = "MODERATE"
        elif delta <= 3.0:
            risk = "HIGH"
        else:
            risk = "VERY_HIGH"

        return {
            "workload": workload,
            "acclimatized": acclimatized,
            "wbgt_threshold_c": threshold,
            "wbgt_difference_c": round(delta, 1),
            "heat_exposure": risk,
        }

    # =========================================================
    # 3. SAUDI MIDDAY WORK BAN REGULATORY CHECK
    # =========================================================

    @staticmethod
    def check_saudi_midday_ban(
        current_dt: Optional[datetime] = None,
        outdoor: bool = True,
        direct_sun: bool = True,
    ) -> Dict:
        """
        Checks compliance with Saudi Ministry of Human Resources and Social Development (MHRSD)
        Decision No. 3337:
          - Period: June 15 to September 15 annually.
          - Hours: 12:00 PM to 3:00 PM (KSA Local Time, UTC+3).
          - Scope: Prohibits working under direct sun in open outdoor spaces.
        """
        if current_dt is None:
            try:
                current_dt = datetime.now(ZoneInfo("Asia/Riyadh"))
            except Exception:
                current_dt = datetime.now()

        month = current_dt.month
        day = current_dt.day
        hour = current_dt.hour
        minute = current_dt.minute

        # Check date window: June 15 (6/15) to Sept 15 (9/15)
        in_season = False
        if month in (7, 8):
            in_season = True
        elif month == 6 and day >= 15:
            in_season = True
        elif month == 9 and day <= 15:
            in_season = True

        # Check daily time window: 12:00 <= time < 15:00
        in_hours = 12 <= hour < 15

        ban_active = in_season and in_hours
        is_violation = ban_active and outdoor and direct_sun

        return {
            "saudi_midday_ban_active": ban_active,
            "is_statutory_violation": is_violation,
            "season_window": "June 15 - September 15",
            "prohibited_hours": "12:00 - 15:00 AST (Riyadh Time)",
            "current_eval_time": current_dt.strftime("%Y-%m-%d %H:%M:%S AST"),
            "legal_basis": "Saudi MHRSD Ministerial Decision No. 3337 (حظر العمل تحت أشعة الشمس)",
            "mandatory_action": (
                "إيقاف العمل الميداني تحت أشعة الشمس فوراً ونقل العمال لأماكن مظللة ومبردة"
                if is_violation else "Normal Regulatory Status"
            ),
        }

    # =========================================================
    # 4. COMPREHENSIVE ENVIRONMENT ASSESSMENT
    # =========================================================

    def assess_environment(
        self,
        temperature_c: float,
        humidity: float,
        wind_speed: float = 0.0,
        outdoor: bool = True,
        direct_sun: bool = False,
        workload: str = "moderate",
        acclimatized: bool = True,
        current_dt: Optional[datetime] = None,
    ) -> Dict:
        """Synthesizes physical, physiological, and statutory safety evaluations."""
        wbgt_data = self.calculate_estimated_wbgt(
            temperature_c=temperature_c,
            humidity=humidity,
            wind_speed=wind_speed,
            outdoor=outdoor,
            direct_sun=direct_sun,
        )

        wbgt = wbgt_data["estimated_wbgt_c"]

        exposure_data = self.assess_heat_exposure(
            wbgt=wbgt,
            workload=workload,
            acclimatized=acclimatized,
        )

        midday_ban = self.check_saudi_midday_ban(
            current_dt=current_dt,
            outdoor=outdoor,
            direct_sun=direct_sun,
        )

        warnings: List[str] = []
        if temperature_c >= 38.0:
            warnings.append("Extreme air temperature (>= 38°C)")
        elif temperature_c >= 35.0:
            warnings.append("High air temperature (>= 35°C)")

        if humidity >= 70.0:
            warnings.append("High relative humidity (>= 70%): Impairs evaporative sweat cooling")

        if wind_speed < 1.0:
            warnings.append("Stagnant air movement (< 1 m/s): Increased thermal retention")

        if direct_sun:
            warnings.append("Direct solar radiant exposure")

        if midday_ban["is_statutory_violation"]:
            warnings.append("STATUTORY VIOLATION: Working outdoors in direct sunlight during Saudi Midday Ban hours!")

        heat_exposure = exposure_data["heat_exposure"]

        # Work/Rest Cycle Recommendation (ACGIH / OSHA Standard)
        if midday_ban["is_statutory_violation"]:
            work_rest_cycle = {
                "ar": "عمل محظور نظاماً تحت أشعة الشمس المباشرة (إيقاف العمل فوراً)",
                "en": "0% Work / 100% Rest (MANDATORY WORK STOPPAGE)",
            }
            recommendation = {
                "ar": (
                    "⚠️ حظر نظامي ملزم: إيقاف الأعمال الميدانية تحت أشعة الشمس فوراً "
                    "وفقاً لقرار وزارة الموارد البشرية والتنمية الاجتماعية رقم 3337، وتوفير سوائل تبريد وأماكن راحة مكيفة."
                ),
                "en": (
                    "⚠️ Mandatory Statutory Ban: Immediate cessation of outdoor work under direct sun per Saudi MHRSD Decision 3337, "
                    "with cold hydration and cooled rest areas provided."
                ),
            }
        elif heat_exposure == "VERY_HIGH":
            work_rest_cycle = {
                "ar": "25% عمل / 75% راحة (15 دقيقة عمل، 45 دقيقة راحة في مكان بارد لكل ساعة)",
                "en": "25% Work / 75% Rest (15 min work, 45 min cool rest per hour)",
            }
            recommendation = {
                "ar": (
                    "خطر إجهاد حراري حرج: إيقاف الأعمال الشاقة غير الضرورية فوراً، وإلزام توفير لتر ماء بارد لكل عامل في الساعة، "
                    "مع فترات راحة مظللة إلزامية وتطبيق نظام مراقبة الزميل."
                ),
                "en": (
                    "Critical Heat Stress Hazard: Suspend non-essential heavy tasks. "
                    "Require 1 liter cold water per worker per hour, mandatory shaded rest, and buddy monitoring."
                ),
            }
        elif heat_exposure == "HIGH":
            work_rest_cycle = {
                "ar": "50% عمل / 50% راحة (30 دقيقة عمل، 30 دقيقة راحة في مكان بارد لكل ساعة)",
                "en": "50% Work / 50% Rest (30 min work, 30 min cool rest per hour)",
            }
            recommendation = {
                "ar": (
                    "تعرض حراري مرتفع: زيادة فترات شرب المياه (كل 20 دقيقة)، وتدوير المهام الشاقة "
                    "وتوفير محطات استراحة مظللة أو مكيفة."
                ),
                "en": (
                    "High Heat Exposure: Increase hydration breaks (every 20 minutes). "
                    "Rotate strenuous work and provide air-conditioned or shaded recovery stations."
                ),
            }
        elif heat_exposure == "MODERATE":
            work_rest_cycle = {
                "ar": "75% عمل / 25% راحة (45 دقيقة عمل، 15 دقيقة راحة لكل ساعة)",
                "en": "75% Work / 25% Rest (45 min work, 15 min rest per hour)",
            }
            recommendation = {
                "ar": (
                    "حمل حراري متوسط: الحث المستمر على شرب المياه وتكثيف مراقبة المشرفين لحالة العمال."
                ),
                "en": (
                    "Moderate Thermal Load: Regular hydration encouragement and active supervisor monitoring."
                ),
            }
        else:
            work_rest_cycle = {
                "ar": "عمل مستمر مع فترات شرب مياه منتظمة",
                "en": "Continuous work with standard hydration pauses",
            }
            recommendation = {
                "ar": "ظروف عمل تشغيلية ملائمة واعتيادية مع توفير مياه الشرب الباردة باستمرار.",
                "en": "Normal operating conditions. Ensure continuous access to cool potable drinking water.",
            }

        return {
            "temperature_c": float(temperature_c),
            "humidity_percent": float(humidity),
            "wind_speed_mps": float(wind_speed),
            "outdoor": outdoor,
            "direct_sun": direct_sun,
            "wet_bulb_c": wbgt_data["wet_bulb_c"],
            "globe_temperature_c": wbgt_data["globe_temperature_c"],
            "estimated_wbgt_c": wbgt_data["estimated_wbgt_c"],
            "workload": exposure_data["workload"],
            "acclimatized": exposure_data["acclimatized"],
            "wbgt_threshold_c": exposure_data["wbgt_threshold_c"],
            "wbgt_difference_c": exposure_data["wbgt_difference_c"],
            "heat_exposure": heat_exposure,
            "work_rest_cycle": work_rest_cycle,
            "environmental_warnings": warnings,
            "recommendation": recommendation,
            "saudi_midday_ban": midday_ban,
            "assessment_standard": "OSHA / ISO 7243 Heat Stress & Saudi MHRSD Ministerial Decision No. 3337",
        }

    def assess_current_facility(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        workload: str = "moderate",
        outdoor: bool = True,
        acclimatized: bool = True,
    ) -> Dict:
        """Live one-shot pipeline combining Geocoding, Live Open-Meteo Weather, and WBGT."""
        location = self.weather_service.get_location(latitude=latitude, longitude=longitude)
        weather = self.weather_service.get_current_weather(
            latitude=location["latitude"],
            longitude=location["longitude"],
        )

        assessment = self.assess_environment(
            temperature_c=weather["temperature_c"],
            humidity=weather["humidity_percent"],
            wind_speed=weather["wind_speed_mps"],
            outdoor=outdoor,
            direct_sun=bool(weather.get("is_day", True)) if outdoor else False,
            workload=workload,
            acclimatized=acclimatized,
        )

        return {
            "location": location,
            "weather": weather,
            "assessment": assessment,
        }
