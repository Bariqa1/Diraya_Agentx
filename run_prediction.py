"""Run the separate Derayah predictive-safety workflow."""
import json

from agents.prediction_agent import PredictionAgent


def main():
    result = PredictionAgent().run()
    if result["status"] != "ok":
        print("DERAYAH PREDICTIVE SAFETY\n\nStatus: insufficient_data")
        return 1
    prediction, evidence = result["prediction"], result["evidence"]
    print("DERAYAH PREDICTIVE SAFETY")
    print(f"\nHistorical Pattern:\n{result['explanation']}")
    print(f"\nExpected High-Risk Zone:\n{prediction['expected_risk_zone']} - {prediction['predicted_risk_level']}")
    print(f"\nCritical Time Window:\n{prediction['critical_time_window']}")
    print(f"\nLikely Recurring Risk:\n{prediction['likely_risk']}")
    print(f"\nHistorical Evidence:\n{evidence['historical_incidents_in_zone']} historical incidents\n"
          f"{evidence['critical_incidents_in_zone']} critical incidents")
    if result.get("training_mode") == "short_history_demo":
        print("\nPrototype note: trained on a short Derayah alert log; demo-only and not real-world validation.")
    else:
        print("\nPrototype note: validate prospectively on reviewed facility incidents before deployment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
