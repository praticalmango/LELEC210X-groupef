import pandas as pd
import matplotlib.pyplot as plt

# Charger le fichier en ignorant les métadonnées
df = pd.read_csv("power_consump.csv", comment=';')

# Décaler l'axe du temps de 3.194 secondes
df["Time(S)"] = df["Time(S)"] + 3.194

# Vérifier les premières lignes
print(df.head())

# Tracer la courbe
plt.figure(figsize=(10, 5))
plt.plot(df["Time(S)"], df["CH2(V)"], label="CH2(V)", linewidth=1)
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.title("Power Consumption (CH2 vs Time)")
plt.legend()
plt.grid(True)

# Limiter l'axe Y entre 0 et 0.5 volts
plt.ylim(0.2, 0.4)

plt.show()

# Calculer la puissance pour chaque point en mW : P = (V^2 / 47) * 3.3 * 1000
df["Power(mW)"] = (df["CH2(V)"] ** 2 / 47) * 3.3 * 1000

# Tracer la courbe de puissance en mW
plt.figure(figsize=(10, 5))
plt.plot(df["Time(S)"], df["Power(mW)"], label="Power (mW)", color='orange', linewidth=1)
plt.xlabel("Time (s)")
plt.ylabel("Power (mW)")
plt.title("Power Consumption (Power vs Time)")
plt.legend()
plt.grid(True)

plt.show()
