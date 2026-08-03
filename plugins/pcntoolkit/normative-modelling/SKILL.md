---
name: normative-modelling
description: >
  Fit, configure, and interpret normative models with PCNtoolkit.
  Use when: choosing between BLR and HBR; deciding how to handle
  site or scanner effects (harmonization, batch effects);
  preparing a dataframe as NormData; configuring likelihoods,
  priors, basis functions, or warps; setting up NormativeModel
  scalers and transforms; interpreting evaluation metrics
  (Rho, SMSE, MSLL, MACE, ShapiroW).
---

# Normative Modelling

Explains how to represent data, choose a regression model, configure it,
and report results with PCNtoolkit. This is the decision guide: it covers
*which* choices are right for a given dataset, not just what the API accepts.

---

## How to use this skill

1. Read the sections below in order. They are the conceptual core and
   answer most modelling questions on their own.
2. Before writing any code, open
   [reference/api-reference.md](reference/api-reference.md) for exact
   signatures, defaults, and the closed sets of valid string values.
3. For a runnable end-to-end script, see
   [reference/worked-example.md](reference/worked-example.md).

Never guess a keyword argument name. Several are easy to get wrong
(`save_dir` not `savedir`, `nknots` not `n_knots`). Check the API
reference, and see `## Common mistakes` at the end of this file.

---

## Data

Data goes in as a dataframe, agnostic of the modality (it can be fMRI, EEG, MEG, cognitive scores, genetics, questionnaire data).

In PCNtoolkit data become an xarray dataset, so the data carries named dimensions (observations, covariates, response_vars, batch_effect_dims) rather than being a flat matrix.

In PCNtoolkit, data becomes a NormData object (built on xarray), so it carries named dimensions (observations, covariates, response_vars, batch_effect_dims) rather than being a flat matrix.

To view the data as a table, NormData.to_dataframe() flattens it into a pandas DataFrame with one row per observation and a two-level column index. The first level is the data type (X, Y, batch_effects, subject_ids) and the second is the name within it — e.g. ("X", "age") for the age covariate, ("Y", "thickness") for a response variable, ("batch_effects", "site") for a batch effect. After fitting, columns such as Z, Yhat, and centiles appear as well.

A new normative model to estimate needs roughly 3000 subjects for non-Gaussian data, but only a couple of hundred for Gaussian data.

---

## Data handling: harmonization

How PCNtoolkit handles harmonization, compared to ComBat:

ComBat's batch effect: a nuisance you want to REMOVE, not interpret.

PCNtoolkit's batch effect: we MODEL it. It must be categorical.

Modelling it instead of removing it:

- allows federated learning - you can adjust to new batch effect groups, e.g. new sites;
- does not remove information from the data.

Harmonization in PCNtoolkit is an invertible transform. It lets you model all the data as if it came from the same reference group, without removing any information from the data.

---

## Select the right model

**BLR**

Empirical Bayes → fast.

Allows fixed effects.

**HBR**

- Very simply, but not 100% correct: HBR = BLR + random effects.
- HBR does sampling, hence slower than BLR.
- The advantage of random effects: a batch effect level with little data borrows strength from the batch effect levels with more data (in neuroimaging, some sites happen to have a low number of subjects).

**Choosing by the model based on the data**

- Gaussian data: BLR, or HBR with Normal likelihood.
- Non-Gaussian data: warped BLR (warp_name="WarpSinhArcsinh"), or HBR with SHASH likelihood.

---

## Configuring BLR

The BLR config has some settings for the batch effects and some for the covariates.

**Batch effects**

- Per-group mean and variance: fixed_effect=True and fixed_effect_var=True.
- Interaction effect of covariate × batch effect: fixed_effect_slope=True and fixed_effect_var_slope=True.

**Covariates**

- The mean is modelled as a function of the covariates. Set heteroskedastic=True to let the variance vary with the covariates too.

---

## Configuring HBR

What you can configure:

**The parameters** — how each one reshapes the distribution.

- Normal likelihood has two: mu and sigma.
- SHASH likelihood has four:
  - mu = location: Slides the distribution left and right.
  - sigma = scale: Stretches it wider or narrower.
  - epsilon =skew: 0 is symmetric, positive leans right.
  - delta = tail weight: 1 is normal-like, < 1 heavier, > 1 lighter.

**Basis function** — how flexible the curve over age is.

- Expands age into smooth columns in a design matrix. For a B-spline, number of columns = degree + nknots.
- nknots: more knots, more wiggle.
- degree: higher degree, smoother each bend.

**Prior distribution** — the plausible range of each parameter.

- dist_name: the family. Normal, HalfNormal, LogNormal, Gamma and Uniform exist.
- dist_params: a positional tuple; the meaning depends on the family. E.g. Gamma is (alpha, beta), shape-rate, not shape-scale.
- If you want a parameter to be positive, either select the right dist_name (e.g. LogNormal) or apply a mapping (see next section). Sigma must be positive because it is a width for both Normal and SHASHb HBR, and delta must be positive for SHASHb HBR because the SHASHb density takes log(delta).

**Softplus mapping** — keeps parameters positive.

- a: horizontal shift.
- b: scale; larger is gentler, closer to a straight line.
- c: vertical shift, a floor on the output. It only applies if you pass a 3-tuple: mapping_params=(0.0, 3.0) leaves the floor at 0.

**linear vs random** — whether to have random effects or not

- linear=True: the parameter is a linear function of the basis-expanded covariates. This is not a fixed effect.
- random=True: the parameter gets a per-batch-effect-level offset around a shared mean. These are the random effects.

---

## Configuring NormativeModel

For positive phenotypes, one way to avoid centiles going to negative values is to set y_transform="log" inside NormativeModel.

If your data include zeros, log will fail on them. Use y_transform="log1p" instead, which computes log(1 + y) and so handles zeros safely.

---

## Selecting the right metrics to report

There are two families of metrics: point metrics and probabilistic (shape/distribution) metrics. For normative models the probabilistic ones matter more, because the model estimates a whole distribution rather than a single predicted value.

| Metric | Family | Input | Better when | Range |
|---|---|---|---|---|
| R2 | Point | Y, Yhat | Higher | ≤ 1 |
| EXPV | Point | Y, Yhat | Higher | ≤ 1 |
| Rho | Point | Y, Yhat | Higher | −1 to 1 |
| RMSE | Point | Y, Yhat | Lower | ≥ 0 |
| SMSE | Point | Y, Yhat | Lower | ≥ 0 |
| MAPE | Point | Y, Yhat | Lower | ≥ 0 |
| MLL | Probabilistic | logp | Lower | Unbounded |
| MSLL | Probabilistic | logp, baseline_logp | Lower (negative) | Unbounded |
| MACE | Probabilistic | centiles, Y | Lower | 0–1 |
| ShapiroW | Probabilistic | Z-scores | Higher | 0–1 |
| Skewness | Probabilistic | Z-scores | Closer to 0 | Unbounded |
| Kurtosis | Probabilistic | Z-scores | Closer to 0 | −2 to ∞ |

---

## Reference files

- [reference/api-reference.md](reference/api-reference.md) — exact
  signatures, defaults, and valid value sets for every class named above.
  This is the primary source; consult it before writing code.
- [reference/worked-example.md](reference/worked-example.md) — an
  end-to-end runnable script, plus short variations (HBR, warp,
  B-spline basis).

Example notebooks in the repository, by topic:

| Topic | Notebook |
|---|---|
| Loading data into NormData | [01_loading_data.ipynb](../../../examples/01_loading_data.ipynb) |
| BLR | [02_BLR.ipynb](../../../examples/02_BLR.ipynb) |
| HBR with Normal likelihood | [03_HBR_Normal.ipynb](../../../examples/03_HBR_Normal.ipynb) |
| HBR with SHASH likelihood | [04_HBR_SHASH.ipynb](../../../examples/04_HBR_SHASH.ipynb) |
| HBR with Beta likelihood | [05_HBR_Beta.ipynb](../../../examples/05_HBR_Beta.ipynb) |
| Comparing models | [07_model_comparison.ipynb](../../../examples/07_model_comparison.ipynb) |
| Basis functions | [11_composite_basis_function.ipynb](../../../examples/11_composite_basis_function.ipynb) |
| Evaluation metrics | [13_evaluation_metrics.ipynb](../../../examples/13_evaluation_metrics.ipynb) |

Rendered tutorials and auto-generated API docs:

- https://pcntoolkit.readthedocs.io/en/stable/
- https://pcntoolkit.readthedocs.io/en/stable/autoapi/index.html

---

## Common mistakes

API shapes that are easy to get wrong. These are about spelling and call
signatures only — for the modelling decisions, use the sections above.

- `NormativeModel` takes `save_dir`, not `savedir`.
- `NormData.from_dataframe` takes `dataframe=`, not `df=` or `data=`. The
  keyword is `batch_effects=` (plural), even though the resulting xarray
  dimension is `batch_effect_dims`. `remove_Nan` has a capital N.
- BLR has two basis function arguments, `basis_function_mean` and
  `basis_function_var`. There is no plain `basis_function` on BLR —
  that singular name belongs to `LinearPrior`.
- `BsplineBasisFunction` uses `nknots` (no underscore), default 5.
- `HBR(likelihood=...)` takes a likelihood object such as
  `NormalLikelihood(...)`, not a string.
- `dist_name` outside {Normal, HalfNormal, Uniform, Gamma, LogNormal}
  raises `KeyError`. `mapping` is limited to identity, exp, softplus.
- `fit(data)` returns `None`. It predicts, evaluates, and saves
  internally. Use `predict` or `fit_predict` to get a `NormData` back.
- `MSLL` returns `None` when `baseline_logp` is absent. `MLL` emits a
  `DeprecationWarning` (it was formerly `NLL`).
- Retrieve computed metrics with `data.get_statistics_df()`.
