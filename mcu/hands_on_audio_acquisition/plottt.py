import re
import matplotlib.pyplot as plt

# Texte du log (tu peux aussi le lire depuis un fichier)
log_data = """
[2025-10-08 17:36:10] INFO    : ADC PA0 value: 1510
[2025-10-08 17:36:10] INFO    : ADC PA0 value: 1531
[2025-10-08 17:36:10] INFO    : ADC PA0 value: 1537
[2025-10-08 17:36:10] INFO    : ADC PA0 value: 1547
[2025-10-08 17:36:10] INFO    : ADC PA0 value: 1525
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1513
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1495
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1477
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1463
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1431
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1404
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1391
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1250
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1335
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1295
[2025-10-08 17:36:11] INFO    : ADC PA0 value: 1355
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 1250
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 1227
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 1177
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 1138
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 1097
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 1122
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 1056
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 1027
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 1028
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 973
[2025-10-08 17:36:12] INFO    : ADC PA0 value: 967
[2025-10-08 17:36:13] INFO    : ADC PA0 value: 941
[2025-10-08 17:36:13] INFO    : ADC PA0 value: 930
[2025-10-08 17:36:13] INFO    : ADC PA0 value: 928
[2025-10-08 17:36:13] INFO    : ADC PA0 value: 931
[2025-10-08 17:36:13] INFO    : ADC PA0 value: 936
"""

# Extraction des valeurs ADC avec une expression régulière
values = [int(x) for x in re.findall(r"ADC PA0 value: (\d+)", log_data)]

# Vérification
print("Valeurs extraites :", values)

# Tracé
plt.figure(figsize=(10, 4))
plt.plot(values, marker='o', linestyle='-', label='ADC PA0')
plt.title("Valeurs ADC lues sur PA0")
plt.xlabel("Échantillon")
plt.ylabel("Valeur ADC (0–4095)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
