import imas
from matplotlib import pyplot as plt


device = 'aug'
pulse = 36440
run = 1
# user = 'g2ncummi'
user = 'penkod'
ts = 2.0

p = imas.ids(pulse,run)
p.open_env(user, device, '3')

# p.core_profiles.getSlice(ts, imas.imasdef.CLOSEST_SAMPLE)
p.core_profiles.get()
cp = p.core_profiles.profiles_1d[0]

plt.figure()
plt.subplot(2,2,1)
plt.plot(cp.grid.rho_tor_norm, 1.0e-3*cp.electrons.temperature, label='el')
for i in range(len(cp.ion)):
    if cp.ion[i].multiple_states_flag == 0 :
        plt.plot(cp.grid.rho_tor_norm, 1.0e-3*cp.ion[i].temperature, label='ion %d'%(i+1))
plt.title('temperature')
plt.ylabel('[keV]')
plt.legend()

plt.subplot(2,2,2)
plt.plot(cp.grid.rho_tor_norm, 1.0e-19*cp.electrons.density_thermal, label='el')
for i in range(len(cp.ion)):
    if cp.ion[i].multiple_states_flag == 0 :
        plt.plot(cp.grid.rho_tor_norm, 1.0e-19*cp.ion[i].density_thermal, label='ion %d'%(i+1))
plt.title('density')
plt.ylabel('[10^19 m-3]')
plt.legend()

plt.subplot(2,2,3)
plt.plot(cp.grid.rho_tor_norm, 1.0e-6*cp.j_total, label='j_tor')
plt.title('current')
plt.ylabel('[MA m-2]')
plt.xlabel('rhon')
plt.legend()

plt.subplot(2,2,4)
plt.plot(cp.grid.rho_tor_norm, cp.q, label='q')
plt.xlabel('rhon')
plt.twinx()
plt.plot(cp.grid.rho_tor_norm, cp.magnetic_shear, color='C1', label='shear')
plt.title('safety factor / shear')
plt.ylabel('[-]')
plt.legend()

plt.show()


p.close()


