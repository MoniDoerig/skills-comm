# Worked Example

An end-to-end normative model, then short variations. All snippets use
`load_fcon1000()` so they run without local data files.

For exact signatures see [api-reference.md](api-reference.md).

---

## End-to-end: BLR

```python
from pcntoolkit import (
    BLR,
    NormData,
    NormativeModel,
    load_fcon1000,
    plot_centiles,
    plot_qq,
)

# 1. Load data. load_fcon1000() returns a NormData directly.
#    From your own dataframe instead:
#        data = NormData.from_dataframe(
#            name="my_study",
#            dataframe=df,
#            covariates=["age"],
#            batch_effects=["site", "sex"],
#            response_vars=["thickness"],
#        )
norm_data: NormData = load_fcon1000()

# 2. Pick the response variables to model.
norm_data = norm_data.sel({"response_vars": ["Left-Lateral-Ventricle"]})

# 3. Split. The split is stratified over batch effects.
train, test = norm_data.train_test_split()

# 4. Wrap a regression model in the NormativeModel meta-estimator.
model = NormativeModel(
    BLR(),
    inscaler="standardize",
    outscaler="standardize",
    save_dir="resources/blr/save_dir",
)

# 5. Fit on train, predict on test. fit_predict takes BOTH datasets
#    and returns the predicted NormData.
model.fit_predict(train, test)

# 6. Metrics. Computed during fit/predict, retrieved as a dataframe.
print(train.get_statistics_df())
print(test.get_statistics_df())

# 7. Plots.
plot_centiles(model, scatter_data=train)
plot_qq(test, plot_id_line=True)
```

`fit_predict` writes results into `save_dir` and evaluates automatically.
If you only want the fitted model, `model.fit(train)` returns `None` — the
results are still written and stored on the passed data.

---

## Variation: non-Gaussian data with a warped BLR

Per the model-selection guidance, non-Gaussian response variables want a
warp rather than a plain Gaussian fit.

```python
model = NormativeModel(
    BLR(warp_name="WarpSinhArcsinh", warp_reparam=True),
    inscaler="standardize",
    outscaler="standardize",
)
```

---

## Variation: non-linear age effect and heteroskedasticity in BLR

```python
from pcntoolkit import BsplineBasisFunction

model = NormativeModel(
    BLR(
        # basis_column=0 is age when age is the first covariate
        basis_function_mean=BsplineBasisFunction(basis_column=0, nknots=5, degree=3),
        heteroskedastic=True,
        basis_function_var=BsplineBasisFunction(basis_column=0, nknots=3, degree=1),
        # per-site mean and variance
        fixed_effect=True,
        fixed_effect_var=True,
    ),
    inscaler="standardize",
    outscaler="standardize",
)
```

BLR takes `basis_function_mean` and `basis_function_var` separately —
there is no plain `basis_function` argument.

---

## Variation: HBR with a Normal likelihood

Use HBR when you want random effects, so small sites borrow strength from
large ones.

```python
from pcntoolkit import HBR, BsplineBasisFunction, NormalLikelihood, make_prior

mu = make_prior(
    linear=True,                                    # mu varies with the covariates
    slope=make_prior(dist_name="Normal", dist_params=(0.0, 10.0)),
    intercept=make_prior(
        random=True,                                # per-site/sex offsets
        mu=make_prior(dist_name="Normal", dist_params=(0.0, 1.0)),
        sigma=make_prior(
            dist_name="Normal", dist_params=(0.0, 1.0),
            mapping="softplus", mapping_params=(0.0, 3.0),   # keep positive
        ),
    ),
    basis_function=BsplineBasisFunction(basis_column=0, nknots=5, degree=3),
)

sigma = make_prior(
    linear=True,                                    # heteroskedastic
    slope=make_prior(dist_name="Normal", dist_params=(0.0, 2.0)),
    intercept=make_prior(dist_name="Normal", dist_params=(1.0, 1.0)),
    basis_function=BsplineBasisFunction(basis_column=0, nknots=5, degree=3),
    mapping="softplus",                             # sigma must be positive
    mapping_params=(0.0, 3.0),
)

model = NormativeModel(
    HBR(likelihood=NormalLikelihood(mu=mu, sigma=sigma), draws=1500, tune=500),
    inscaler="standardize",
    outscaler="standardize",
)
```

Inside a prior the argument is singular `basis_function=`. `likelihood`
takes an object, not a string.

---

## Variation: HBR with a SHASH likelihood

For skewed or heavy-tailed data. `epsilon` controls skew, `delta` tail
weight; `delta` must be positive because the density takes `log(delta)`.

```python
from pcntoolkit import SHASHbLikelihood

epsilon = make_prior(dist_name="Normal", dist_params=(0.0, 1.0))
delta = make_prior(
    dist_name="Normal", dist_params=(1.0, 1.0),
    mapping="softplus", mapping_params=(0.0, 3.0, 0.3),   # floor at 0.3
)

model = NormativeModel(
    HBR(likelihood=SHASHbLikelihood(mu=mu, sigma=sigma,
                                    epsilon=epsilon, delta=delta)),
    inscaler="standardize",
    outscaler="standardize",
)
```

The 3-tuple `mapping_params=(a, b, c)` adds the floor `c`; a 2-tuple
leaves it at 0.

---

## Variation: positive phenotypes

Stops centiles running negative. Use `log1p` when the data contain zeros.

```python
model = NormativeModel(BLR(), y_transform="log")     # strictly positive Y
model = NormativeModel(BLR(), y_transform="log1p")   # Y may contain zeros
```

---

## Variation: transfer to a new site

Adapts an existing model to batch-effect levels it was not fitted on,
without refitting from scratch.

```python
# Hold out two sites from the fit
transfer_data, fit_data = norm_data.batch_effects_split(
    {"site": ["Milwaukee_b", "Oulu"]}, names=("transfer", "fit")
)
train, test = fit_data.train_test_split()
transfer_train, transfer_test = transfer_data.train_test_split()

model.fit_predict(train, test)

# transfer_predict returns a NEW model; the original is unchanged
transferred_model = model.transfer_predict(transfer_train, transfer_test)

# extend_predict instead keeps the old sites and adds the new ones
extended_model = model.extend_predict(transfer_train, transfer_test)
```

Both default to writing into `<save_dir>_transfer` / `<save_dir>_extend`.

---

## Saving, loading, merging

```python
model.save("resources/blr/save_dir")
loaded = NormativeModel.load("resources/blr/save_dir")

# merge is a classmethod: save_dir first, then >=2 models
merged = NormativeModel.merge("resources/merged", [model_a, model_b])
```

---

## Harmonization

An invertible transform that expresses all observations as if measured in
one reference batch, without discarding information.

```python
harmonized = model.harmonize(test)
# adds Y_harmonized to the returned NormData
```
