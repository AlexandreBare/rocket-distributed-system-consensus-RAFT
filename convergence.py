import numpy as np
import matplotlib.pyplot as plt


correct_fractions = [0.6, 0.7, 0.8, 0.9, 1.0]#np.linspace(0.4, 1.0, 7)
convergence_times = np.empty(len(correct_fractions), dtype=object)
i = 0
for correct_fraction in correct_fractions:
    file = open(f"convergence_times/convergence_time_correct_fraction_{correct_fraction}.txt", "r")
    convergence_times[i] = [float(x) for x in file.readline()[:-1].split(",")] # read all but the last character
    i = i + 1
    file.close()

percentiles = np.stack([np.percentile(convergence_times[i], [2.5, 50, 97.5]) for i in range(len(correct_fractions))])

#plt.fill_between(correct_fractions, percentiles[:, 0], percentiles[:, 2], facecolor=None, alpha=0.25, linewidth=0.0)
plt.plot(correct_fractions, percentiles[:, 1], label = "Convergence Time (Median)")
plt.xlabel("Fraction of Correct Flight Computers")
plt.ylabel("Convergence Time in sec (95% Confidence Interval)")
plt.title("Convergence Time for 10 Flight Computers")
plt.legend()

plt.savefig("convergence_times/convergence_time2.pdf")