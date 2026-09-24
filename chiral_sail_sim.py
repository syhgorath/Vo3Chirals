"""
VO-3 Chiralis: Chiral Photonic Sail Dynamics Simulator
Author: Ziya Yesilbahce (2026)
DOI: 10.5281/zenodo.22939390
License: MIT
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# --- Fiziksel ve Donanım Sabitleri ---
C = 299792458.0             # Işık hızı (m/s)
P0 = 100e6                  # Lazer Gücü: 100 MW (10^8 W)
W0 = 1.2                    # Lazer bel yarıçapı / Beam waist (m)
R_REFL = 0.9998             # Yansıtma katsayısı (Dielektrik ayna)
MASS = 0.005                # Sonda kütlesi: 5 gram (0.005 kg)
BLADE_PITCH_DEG = 20.0      # Helis hücum açısı (derece)
BLADE_PITCH = np.radians(BLADE_PITCH_DEG)
R_EFF = 0.35                # Efektif kuvvet kolu yarıçapı (m)
R_MAX = 0.50                # Kanat dış yarıçapı (m)
R_HUB = 0.05                # Gövde/hub yarıçapı (m)
I_ZZ = 0.5 * MASS * (R_MAX**2)  # Z ekseni eylemsizlik momenti (kg.m^2)
SIGMA_YIELD = 1200e6        # Malzeme akma sınırı: 1200 MPa (C/SiC)
RHO_MEMBRANE = 1800.0       # Malzeme yoğunluğu (kg/m^3)

def laser_intensity(r):
    """TEM00 Gauss lazer şiddet dağılımı (W/m^2)."""
    return (2.0 * P0 / (np.pi * W0**2)) * np.exp(-2.0 * (r**2) / (W0**2))

def optomechanical_forces(x, y, vx, vy, omega_z):
    """
    Kiral helis kanatlara etki eden foton basıncı, tork ve geri çağırıcı kuvvet.
    """
    r_offset = np.sqrt(x**2 + y**2)
    
    # Eksenel itki (Fz)
    fz = (2.0 * P0 * R_REFL / C) * (np.cos(BLADE_PITCH)**2)
    # Eksen dışına çıkıldığında Gauss profili düşüşü
    beam_coupling = np.exp(-2.0 * (r_offset**2) / (W0**2))
    fz_eff = fz * beam_coupling
    
    # Eksenel tork (tau_z)
    tau_z = (P0 * R_REFL * R_EFF / C) * np.sin(2.0 * BLADE_PITCH) * beam_coupling
    
    # Kiral gradyan geri çağırıcı yanal kuvvet (Optik cımbız / Beam-riding)
    # Lazer merkezine doğru çeken harmonik geri yükleme gradyanı
    k_trap = (4.0 * P0 * R_REFL / (C * W0**2)) * np.sin(BLADE_PITCH)
    fx = -k_trap * x
    fy = -k_trap * y
    
    return fz_eff, tau_z, fx, fy

def calculate_stress(omega_z, fz):
    """
    Kanat kökündeki von Mises eşdeğer gerilmesini hesaplar (Pa).
    """
    # 1. Santrifüj gerilmesi
    sigma_cf = 0.5 * RHO_MEMBRANE * (omega_z**2) * (R_MAX**2 - R_HUB**2)
    # 2. İtki kaynaklı eğilme gerilmesi (basitleştirilmiş kiriş modeli)
    blade_area = (np.pi * (R_MAX**2 - R_HUB**2)) / 4.0
    pressure = fz / blade_area
    sigma_bend = (pressure * (R_MAX - R_HUB)**2) / (2.0 * (0.001**2))
    
    # Toplam von Mises (çekme + eğilme)
    sigma_vm = np.sqrt((sigma_cf + sigma_bend)**2)
    return sigma_vm

def equations_of_motion(t, state):
    """
    Durum vektörü: [x, y, z, vx, vy, vz, omega_z]
    """
    x, y, z, vx, vy, vz, omega = state
    
    fz, tau_z, fx, fy = optomechanical_forces(x, y, vx, vy, omega)
    
    # İvmeler
    ax = fx / MASS
    ay = fy / MASS
    az = fz / MASS
    alpha_z = tau_z / I_ZZ
    
    return [vx, vy, vz, ax, ay, az, alpha_z]

# --- Simülasyon Çalıştırma ---
if __name__ == "__main__":
    print("VO-3 Chiralis Uçuş Dinamiği Simülasyonu Başlatılıyor...")
    
    # Başlangıç koşulları: Merkezden 15 cm sapma ile bırakılıyor (x0 = 0.15 m)
    init_state = [0.15, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    t_span = (0, 10.0)  # İlk 10 saniyelik kararlılık testi
    t_eval = np.linspace(0, 10.0, 2000)
    
    sol = solve_ivp(equations_of_motion, t_span, init_state, t_eval=t_eval, rtol=1e-7)
    
    t = sol.t
    x_pos = sol.y[0]
    y_pos = sol.y[1]
    z_pos = sol.y[2]
    vz = sol.y[5]
    omega = sol.y[6]
    
    # Gerilme dizisi
    fz_nominal = (2.0 * P0 * R_REFL / C) * (np.cos(BLADE_PITCH)**2)
    stresses_mpa = np.array([calculate_stress(w, fz_nominal) / 1e6 for w in omega])
    
    # Çökme/Kırılma Kontrolü
    max_stress = np.max(stresses_mpa)
    print(f"Maksimum Kök Gerilmesi: {max_stress:.2f} MPa (Limit: {SIGMA_YIELD/1e6:.0f} MPa)")
    if max_stress >= (SIGMA_YIELD / 1e6):
        print("UYARI: Yapısal akma sınırı aşıldı! Kanat kopması meydana geldi.")
    else:
        print("DURUM: Gerilme emniyetli bölgede. Kiral yapı kararlı.")

    # --- Görselleştirme ---
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    
    # 1. Yanal Kararlılık (Beam-Riding / X-Y Salınımı)
    axs[0, 0].plot(t, x_pos * 100, label='X Sapması (cm)', color='cyan')
    axs[0, 0].axhline(0, color='gray', linestyle='--')
    axs[0, 0].set_title("Lazer Ekseninde Tutunma (Beam-Riding Trapping)")
    axs[0, 0].set_xlabel("Zaman (s)")
    axs[0, 0].set_ylabel("Sapma (cm)")
    axs[0, 0].grid(True, alpha=0.3)
    axs[0, 0].legend()
    
    # 2. Açısal Hız (Spin-Up)
    axs[0, 1].plot(t, omega, color='gold')
    axs[0, 1].set_title("Kiral Açısal Hızlanma (Spin Dynamics)")
    axs[0, 1].set_xlabel("Zaman (s)")
    axs[0, 1].set_ylabel("Omega (rad/s)")
    axs[0, 1].grid(True, alpha=0.3)
    
    # 3. İleri Hız (Axial Velocity)
    axs[1, 0].plot(t, vz / 1000, color='lime')
    axs[1, 0].set_title("Eksenel İleri Hız (Vz)")
    axs[1, 0].set_xlabel("Zaman (s)")
    axs[1, 0].set_ylabel("Hız (km/s)")
    axs[1, 0].grid(True, alpha=0.3)
    
    # 4. Malzeme Gerilmesi (von Mises Stress)
    axs[1, 1].plot(t, stresses_mpa, color='crimson')
    axs[1, 1].axhline(SIGMA_YIELD/1e6, color='red', linestyle='--', label='Akma Limiti (1200 MPa)')
    axs[1, 1].set_title("Kanat Kökü von Mises Gerilmesi")
    axs[1, 1].set_xlabel("Zaman (s)")
    axs[1, 1].set_ylabel("Gerilme (MPa)")
    axs[1, 1].grid(True, alpha=0.3)
    axs[1, 1].legend()
    
    plt.tight_layout()
    plt.savefig("vo3_chiralis_simulation.png", dpi=300)
    print("Simülasyon tamamlandı. Grafikler 'vo3_chiralis_simulation.png' olarak kaydedildi.")