import pandas as pd
import matplotlib.pyplot as plt

# Charger le fichier en ignorant les métadonnées
df = pd.read_csv("popopow.csv", comment=';')

# Décaler l'axe du temps de 3.194 secondes


# Vérifier les premiè

# Calculer la puissance pour chaque point en mW : P = (V / 47) * 3.3 * 1000
df["Power(mW)"] = (df["CH1(V)"] / 47) * 3.3 * 1000 
t1 = 0.0
t2 = 0.985
t3 = 3.135

plt.figure(figsize=(10, 5))
# Ajouter des couleurs de fond pour chaque section AVANT de tracer la courbe
plt.axvspan(df["Time(S)"].min(), t1, color='lightblue', alpha=0.3, label='Wait for interrupt')
plt.axvspan(t1, t2, color='lightgreen', alpha=0.3, label='Acquisition Phase')
plt.axvspan(t2, t3, color='lightcoral', alpha=0.3, label='Transmission Phase')
plt.axvspan(t3, df["Time(S)"].max(), color='lightblue', alpha=0.3)

# Tracer la courbe de puissance en mW
plt.plot(df["Time(S)"], df["Power(mW)"], label="Power (mW)", color='orange', linewidth=1)
plt.xlabel("Time (s)", fontsize=14)
plt.ylabel("Power (mW)", fontsize=14)

# Pour éviter les doublons dans la légende
handles, labels = plt.gca().get_legend_handles_labels()
by_label = dict(zip(labels, handles))
plt.legend(by_label.values(), by_label.keys(), fontsize=12)

plt.grid(True)
plt.savefig("power_consumption_plot.pdf")
plt.show()

# énergie totale consommée en mJ
# Calculer la puissance moyenne pendant la phase d'acquisition avec la même formule
power_2 = (0.143229 / 47) * 3.3 * 1000  # mW
energy_2 = power_2 * (t2 - t1)  # mJ
power_3 = (0.29277 / 47) * 3.3 * 1000  # mW
energy_3 = power_3 * (t3 - t2)  # mJ
energy_total = energy_2 + energy_3
print(f"Énergie totale consommée : {energy_total:.2f} mJ")
print(f"Énergie consommée pendant la phase d'acquisition : {energy_2:.2f} mJ")
print(f"Énergie consommée pendant la phase de transmission : {energy_3:.2f} mJ")
print("Power during acquisition phase (mW):", power_2)
print("Power during transmission phase (mW):", power_3)

#led 
power_led = 2 * (t3 - t2)  # mJ
print(f"Énergie consommée par les LEDs pendant la phase de transmission : {power_led:.2f} mJ")
