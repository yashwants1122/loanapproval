import json
import math
import sys

payload = json.loads(sys.argv[1])
principal = float(payload["principal"])
annual_rate = float(payload["annual_rate"])
months = int(payload["months"])

if principal <= 0 or annual_rate < 0 or months <= 0:
    raise ValueError("Invalid calculation inputs")

monthly_rate = annual_rate / 12 / 100
if monthly_rate == 0:
    emi = principal / months
else:
    emi = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)

print(json.dumps({"emi": round(emi, 2)}))
