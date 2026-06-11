# %% Imports
import os
import numpy as np
import ast
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

# %% Global variables
AUTOCALIBRATION_DATA_PATH = "autocalibration_data"
AUTOCALIBRATION_RESULTS_PATH = "autocalibration_results"


# %%
def get_poke_calibration_parameters(plot=True, save_filename=None):
    autocal_df, autocal_filename = load_autocalibration_results(use_most_recent=True)
    poke2fit_lr_params = get_linear_regression_parameters(autocal_df)
    poke2fit_me_params = get_mixed_effects_regression_parameters(autocal_df)
    save_filename = save_filename if save_filename else autocal_filename[:-4] + "_results"
    save_path = os.path.join(AUTOCALIBRATION_RESULTS_PATH, save_filename)
    fig_filename = save_filename + ".pdf"
    fig_path = os.path.join(AUTOCALIBRATION_RESULTS_PATH,fig_filename)
    if plot:
        plot_poke_calibration_fits(autocal_df, poke2fit_me_params, fig_path)
    with open(save_path + "_mixed_effects.txt", "w") as f:
        f.write(repr(poke2fit_me_params.T.to_dict()))
    with open(save_path + "_ind_fits.txt", "w") as f:
        f.write(repr(poke2fit_lr_params.T.to_dict()))
    return poke2fit_lr_params, poke2fit_me_params


def load_autocalibration_results(use_most_recent=True, specified_file=None):
    """"""
    autocal_files = os.listdir(AUTOCALIBRATION_DATA_PATH)
    autocal_files = [f for f in autocal_files if f.endswith(".tsv")]
    autocal_datetimes = [pd.to_datetime(f.split("-", 1)[1].split(".")[0]) for f in autocal_files]
    if use_most_recent:
        idx = autocal_datetimes.index(max(autocal_datetimes))
        autocal_filename = autocal_files[idx]
    else:
        autocal_filename = specified_file
        assert (
            autocal_filename in autocal_files
        ), f"Specified file {autocal_filename} not found in {AUTOCALIBRATION_DATA_PATH}"
    print(f"loading_file: {autocal_filename}")
    autocal_path = os.path.join(AUTOCALIBRATION_DATA_PATH, autocal_filename)
    autocal_results = pd.read_csv(autocal_path, sep="\t")
    autocal_results = autocal_results[autocal_results.subtype == "print"].content.apply(ast.literal_eval).to_list()
    autocal_df = pd.DataFrame(autocal_results)
    # Compute release volume per release.
    autocal_df["single_release_vol"] = autocal_df.release_weight.div(autocal_df.n_release).mul(1000)  # in uL
    return autocal_df, autocal_filename


def plot_poke_calibration_fits(autocal_df, poke2fit_me_params, fig_path):
    """"""
    g = sns.FacetGrid(autocal_df, col="poke", col_wrap=7)
    g.map_dataframe(sns.regplot, x="single_release_vol", y="release_duration", ci=None)
    g.map_dataframe(plot_fe_fit, x="single_release_vol", poke2fit_me_params=poke2fit_me_params)
    g.set_titles(col_template="{col_name}")
    plt.tight_layout()
    plt.savefig(fig_path)
    plt.show()
    return


def plot_fe_fit(data, x, color, poke2fit_me_params):
    """Add mixed effects fit to plots."""
    poke = data.poke.unique()[0]
    xmin = data.single_release_vol.min()
    xmax = data.single_release_vol.max()
    intercept = poke2fit_me_params.loc[poke, "i"]
    slope = poke2fit_me_params.loc[poke, "s"]
    ymin = intercept + slope * xmin
    ymax = intercept + slope * xmax
    plt.plot([xmin, xmax], [ymin, ymax], color="r")


def get_linear_regression_parameters(autocal_df):
    """"""
    poke2fit = {}
    for poke in autocal_df.poke.unique():
        poke_df = autocal_df[autocal_df.poke == poke]
        slope, intercept = np.polyfit(x=poke_df.single_release_vol, y=poke_df.release_duration, deg=1)
        poke2fit[poke] = {"s": round(slope, 2), "i": round(intercept, 2)}  # slope [s] is in ms/uL, intercept [i] in ms.
    return pd.DataFrame(poke2fit).T


def get_mixed_effects_regression_parameters(autocal_df):
    md = smf.mixedlm(
        "release_duration ~ single_release_vol",
        autocal_df,
        groups=autocal_df["poke"],
        re_formula="~ single_release_vol",
    )
    mdf = md.fit(method=["lbfgs"])
    poke2fit = {}
    for poke in autocal_df.poke.unique():
        slope = mdf.fe_params.single_release_vol + mdf.random_effects[poke].single_release_vol
        intercept = mdf.fe_params.Intercept + mdf.random_effects[poke].Group
        poke2fit[poke] = {"s": round(slope, 2), "i": round(intercept, 2)}  # slope [s] is in ms/uL, intercept [i] in ms.
    return pd.DataFrame(poke2fit).T


if __name__ == "__main__":
    get_poke_calibration_parameters()
