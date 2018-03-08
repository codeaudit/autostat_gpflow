#!/usr/bin/env python3
import numpy as np
import os
from kernels import kernels_abstract, kernel_defs, mutate
import gpflow as gpf
import joblib

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


def test_kernel(kernel_wrapper, x_vals, y_vals):
    model = gpf.models.GPR(x_vals, y_vals, kern=kernel_wrapper.gpf_kernel)
    model.likelihood.variance = 0.001
    gpf.train.ScipyOptimizer().minimize(model)
    ll = model.likelihood_tensor.eval(session=model.enquire_session())
    return ll


def center(arr):
    arr -= np.mean(arr)
    arr /= np.std(arr)
    return arr


n_steps = 3

results = []
seen = set()

data = np.load("data/co2.npz")
n_data = 25
x, y = center(data['x'][:n_data]).reshape(-1, 1), center(
    data['y'][:n_data]).reshape(-1, 1)

top_kernel = None
base_kernels = [kernels_abstract.KernelWrapper(kernel_defs.SEKernel()),
                kernels_abstract.KernelWrapper(kernel_defs.LinKernel()),
                kernels_abstract.KernelWrapper(kernel_defs.PerKernel())]

prospective_kernels = base_kernels

with joblib.Parallel(n_jobs=2) as para:
    for step in range(n_steps):
        print("step {}".format(step))
        to_try = []
        for m in prospective_kernels:
            m.simplify()
            if str(m) not in seen:
                to_try.append(m)

        print("Seen {}".format(seen))
        print("-" * 20)
        print("Kernels to try {}".format(to_try))
        print("-" * 20)
        seen.update((str(m) for m in to_try))

        r = para(joblib.delayed(test_kernel)(m, x, y) for m in to_try)

        results += zip(to_try, r)
        results = sorted(results, key=lambda x2: x2[-1], reverse=True)
        top_kernel, top_ll = results[0]

        print("Top kernel is: %s (%f)" % (str(top_kernel), top_ll))
        print("=" * 20)

        prospective_kernels = mutate.mutation_generator(top_kernel)

print("Search finished")
