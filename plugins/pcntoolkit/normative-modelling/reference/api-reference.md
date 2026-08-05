# API Reference

Exact signatures, defaults, and valid value sets. Consult this before
writing PCNtoolkit code — several keyword names are easy to guess wrong.

Each section names its source file so you can re-check against a newer
checkout if the API has moved on.

---

## Public API surface

`pcntoolkit/__init__.py` exports exactly these 22 names:

```python
NormData
BsplineBasisFunction, FractionalPolynomialBasisFunction, LinearBasisFunction,
PolynomialBasisFunction, CompositeBasisFunction
NormativeModel
BLR, HBR
BetaLikelihood, NormalLikelihood, SHASHbLikelihood
make_prior
plot_centiles, plot_qq, plot_ridge, plot_centiles_advanced
load_fcon1000
Runner
LongitudinalScore, ZDiffScore, ZGainScore
```

`SHASHoLikelihood` and `SHASHo2Likelihood` exist in
`pcntoolkit/math_functions/likelihood.py` but are **not** exported. Import
them from their module if needed.

---

## NormData

Source: `pcntoolkit/dataio/norm_data.py`

```python
NormData.from_dataframe(
    name: str,
    dataframe: pd.DataFrame,
    covariates: List[str] | None = None,
    batch_effects: List[str] | None = None,
    response_vars: List[str] | None = None,
    subject_ids: str | None = None,
    visits: str | None = None,
    remove_Nan: bool = False,
    remove_outliers: bool = False,
    z_threshold: float = 3.0,
    attrs: Mapping[str, Any] | None = None,
) -> NormData
```

Traps: the frame keyword is `dataframe=`; the batch keyword is
`batch_effects=` (plural) while the xarray *dimension* is
`batch_effect_dims`; `remove_Nan` has a capital N.

Other constructors: `from_ndarrays`, `from_paths`, `from_fsl`, `from_bids`,
`from_xarray`, `from_netcdf`.

**Dimensions:** `observations`, `covariates`, `response_vars`,
`batch_effect_dims`.

**Data variables:** `X`, `Y`, `batch_effects`, `subject_ids`, optionally
`visits`. After predicting: `Z`, `centiles` (extra dim `centile`), `logp`,
`baseline_logp`, `Yhat`, `Y_harmonized`, `statistics` (dim `statistic`).

If no batch effects are supplied, a dummy is created with the single level
`"dummy_batch_effect"`.

```python
data.to_dataframe(dim_order: Sequence[Hashable] | None = None) -> pd.DataFrame
data.get_statistics_df() -> pd.DataFrame
```

`to_dataframe()` returns **MultiIndex columns** — tuples such as
`("X", "age")`, `("Y", "thickness")`, `("batch_effects", "site")`,
`("centiles", (response_var, centile))`. Not a flat frame.

---

## NormativeModel

Source: `pcntoolkit/normative_model.py`

```python
NormativeModel(
    template_regression_model: RegressionModel,
    savemodel: bool = True,
    evaluate_model: bool = True,
    saveresults: bool = True,
    saveplots: bool = True,
    save_dir: str | None = None,
    inscaler: str = "standardize",
    outscaler: str = "standardize",
    y_transform: str | None = None,
    name: str | None = None,
)
```

`save_dir`, not `savedir`. The first argument is normally passed
positionally. `y_transform` accepts `"log"`, `"log1p"`, or `None`; `"log"`
raises `ValueError` on non-positive Y, `"log1p"` on values below −1. The
forward transform touches `Y` only; the inverse is applied to `Y`,
`centiles`, `Yhat`, and `Y_harmonized`.

Scaler values are defined in `pcntoolkit/math_functions/scaler.py`.

### Methods

```python
fit(data: NormData) -> None
predict(data: NormData) -> NormData
fit_predict(fit_data: NormData, predict_data: NormData) -> NormData

harmonize(data: NormData, reference_batch_effect: dict | None = None) -> NormData
synthesize(...) -> NormData
save(path: str | None = None) -> None
NormativeModel.load(path: str, into=None) -> NormativeModel
```

`fit` returns `None` — it predicts, evaluates, and saves internally. Use
`predict` or `fit_predict` when you need a `NormData` back.

---

## BLR

Source: `pcntoolkit/regression_model/blr.py`

```python
BLR(
    name: str = "template",
    fixed_effect: bool = False,
    fixed_effect_slope: bool = False,
    fixed_effect_slope_indices: list[int] | Literal["all"] = None,
    heteroskedastic: bool = False,
    fixed_effect_var: bool = False,
    fixed_effect_var_slope: bool = False,
    fixed_effect_var_slope_indices: list[int] | Literal["all"] = None,
    warp_name: str | None = None,
    warp_reparam: bool = False,
    basis_function_mean: BasisFunction = None,
    basis_function_var: BasisFunction = None,
    n_iter: int = 100,
    tol: float = 1e-3,
    ard: bool = False,
    optimizer: str = "l-bfgs-b",
    l_bfgs_b_l: float = 0.1,
    l_bfgs_b_epsilon: float = 0.1,
    l_bfgs_b_norm: str = "l2",
    hyp0: np.ndarray | None = None,
    is_fitted: bool = False,
    is_from_dict: bool = False,
)
```

Two basis function arguments, `basis_function_mean` and
`basis_function_var`. There is no plain `basis_function` on BLR. Both take
BasisFunction *instances*.

`warp_name` is a string, one of: `"WarpSinhArcsinh"`, `"WarpLog"`,
`"WarpBoxCox"`, `"WarpAffine"`, `"WarpCompose"`
(`pcntoolkit/math_functions/warp.py`).

The `n_iter` and `tol` docstrings claim 300 and 1e-5; the signature is
authoritative at 100 and 1e-3.

---

## HBR

Source: `pcntoolkit/regression_model/hbr.py`

```python
HBR(
    name: str = "template",
    likelihood: Likelihood = get_default_normal_likelihood(),
    draws: int = 1500,
    tune: int = 500,
    cores: int = 4,
    chains: int = 4,
    nuts_sampler: str = "nutpie",
    init: str = "jitter+adapt_diag",
    progressbar: bool = True,
    is_fitted: bool = False,
    is_from_dict: bool = False,
)
```

`likelihood` takes an **object**, not a string. Plain strings such as
`"Normal"` work only through the `HBR.from_args` path.

### Likelihoods

Source: `pcntoolkit/math_functions/likelihood.py`

```python
NormalLikelihood(mu: BasePrior, sigma: BasePrior)
SHASHbLikelihood(mu: BasePrior, sigma: BasePrior,
                 epsilon: BasePrior, delta: BasePrior)
BetaLikelihood(alpha: BasePrior, beta: BasePrior)
```

Helper factories in the same module build a sensible default with random
intercepts and B-spline bases, e.g. `get_default_normal_likelihood()`.

---

## Priors

Source: `pcntoolkit/math_functions/prior.py`

```python
make_prior(name: str = "theta", **kwargs) -> BasePrior
```

Dispatch: `linear=True` → `LinearPrior`; `random=True` → `RandomPrior`;
otherwise → `Prior`.

```python
Prior(
    name: str = "theta",
    dims: tuple[str, ...] | str | None = None,
    mapping: str = "identity",
    mapping_params: tuple[float, ...] = None,
    dist_name: str = "Normal",
    dist_params: tuple[float | int | list, ...] = None,
)

LinearPrior(
    slope: BasePrior | None = None,
    intercept: BasePrior | None = None,
    name: str = "theta",
    dims=None,
    mapping: str = "identity",
    mapping_params: tuple[float, ...] = None,
    basis_function: BasisFunction = LinearBasisFunction(),
)

RandomPrior(
    mu: BasePrior | None = None,
    sigma: BasePrior | None = None,
    name: str = "theta",
    dims=None,
    mapping: str = "identity",
    mapping_params: tuple[float, ...] = None,
)
```

`LinearPrior` is the only one taking the singular `basis_function=`.

**`dist_name` — the complete valid set** (`PM_DISTMAP`):
`"Normal"`, `"HalfNormal"`, `"Uniform"`, `"Gamma"`, `"LogNormal"`.
Anything else raises `KeyError`. `Cauchy`, `HalfCauchy`, and `InvGamma`
appear commented out in the source and are not available.

`dist_params` is positional and family-dependent — `Gamma` is
`(alpha, beta)`, shape-rate, not shape-scale.

**`mapping` — the complete valid set:** `"identity"`, `"exp"`,
`"softplus"`. Anything else raises `ValueError`.

`mapping_params` is `(a, b)` or `(a, b, c)`, applying
`f_abc(x) = f((x - a) / b) * b + c`, with `c` defaulting to 0 when a
2-tuple is passed.

---

## Basis functions

Source: `pcntoolkit/math_functions/basis_function.py`

```python
BsplineBasisFunction(
    basis_column: int = 0,
    degree: int = 3,
    nknots: int = 5,
    left_expand: float = 0.05,
    right_expand: float = 0.05,
    knot_method: str = "uniform",   # "uniform" or "quantile"
    knots: np.ndarray | list = None,
)

PolynomialBasisFunction(basis_column: int = 0, degree: int = 3)
LinearBasisFunction(basis_column: int = 0)
CompositeBasisFunction(parts)
FractionalPolynomialBasisFunction(basis_column: int = 0, ...)
```

`nknots` has no underscore and defaults to 5. Number of B-spline columns
is `degree + nknots`.

---

## Evaluation metrics

Source: `pcntoolkit/util/evaluator.py`

```python
Evaluator.evaluate(data: NormData, statistics: List[str] = [])
```

The complete requestable set (`all_statistics`):

```python
"Rho", "Rho_p", "R2", "RMSE", "SMSE", "MSLL", "MLL",
"ShapiroW", "MACE", "MAPE", "EXPV", "Skewness", "Kurtosis"
```

Notes:

- `Rho_p` (Spearman p-value) is appended automatically whenever `Rho` is
  selected.
- `MSLL` returns `None` when `baseline_logp` is absent.
- `MLL` was formerly `NLL` and emits a `DeprecationWarning` on every call,
  including the default path.
- `BIC` has an `evaluate_bic` method but is **not** in `all_statistics`,
  so it is never computed by default and cannot be requested via
  `statistics=`.
- `ShapiroW`, `Skewness`, and `Kurtosis` are computed on `Z`.
  `Skewness`/`Kurtosis` use `bias=False` and return NaN below 3 and 4
  valid observations respectively.
- `MACE` uses `Y`, `centiles`, and `batch_effects`, averaged per
  batch-effect combination.

Results land in `data["statistics"]` with dims
`("response_vars", "statistic")`, statistic coordinates sorted
alphabetically. Retrieve with `data.get_statistics_df()`.
