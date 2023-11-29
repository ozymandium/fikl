"""
Classes which fetch data for columns in the decision matrix, instead of reading from a CSV file.

All fetchers must implement:
- `fetch(List[str]) -> pd.Series`
    - Takes a list of choice names
    - Returns a pandas Series with the same index as the list of choice names. The values of the Series are the
      values for the column.
- `CODE` : str
    - The identifier of the fetcher. This is used in the config yaml to specify which fetcher to use
    for a column.
"""
from typing import List
import os

import pandas as pd


class ObesityFetcher:
    """
    Fetcher for obesity data.

    Sourced from CDC 500 Cities project, 2017 data.
    https://data.cdc.gov/500-Cities-Places/500-Cities-Obesity-among-adults-aged-18-years/bjvu-3y7d/data
    """

    CODE = "Obesity"
    SOURCE_FILE = os.path.join(
        os.path.dirname(__file__), "data", "500_Cities__Obesity_among_adults_aged___18_years.csv"
    )

    def fetch(self, choices: List[str]) -> pd.Series:
        """
        Fetches obesity data for the given choices.

        Parameters
        ----------
        choices : list[str]
            List of "City, State" strings to fetch data for, e.g. "New York, NY"

        Returns
        -------
        pd.Series
            Series with the same index as the list of choices. Values are the obesity rate for the
            choice.
        """
        # ensure choices are unique
        if len(set(choices)) != len(choices):
            raise ValueError("choices must be unique")
        # read the data
        df = pd.read_csv(self.SOURCE_FILE)
        # choices is a list of strings with the format "city, state". the data has a column
        # "CityName" with the format "city", and a column "StateAbbr" with the format "state".
        # create a new column with the format "city, state"
        df["choice"] = df["CityName"] + ", " + df["StateAbbr"]
        # set the index to the new column
        df.set_index("choice", inplace=True)
        # check that all choices are in the data
        if not set(choices).issubset(set(df.index)):
            raise ValueError(f"choices not in data: {set(choices) - set(df.index)}")
        # narrow the data to only the choices we want
        df = df.loc[choices]
        # return the obesity rate for each choice
        return df["Data_Value"].astype(float)


class CountyElectionMargin:
    """
    Fetches the margin of victory for the 2020 presidential election for a county.

    Sourced from:
    MIT Election Data and Science Lab, 2018, "County Presidential Election Returns 2000-2020", 
    https://doi.org/10.7910/DVN/VOQCHQ, Harvard Dataverse, V11, UNF:6:HaZ8GWG8D2abLleXN3uEig== [fileUNF] 
    """
    CODE = "County Politics"
    SOURCE_FILE = os.path.join(
        os.path.dirname(__file__), "data", "countypres_2000-2020.csv"
    )

    def fetch(self, choices: List[str]) -> pd.Series:
        """
        Fetches the margin of victory for the 2020 presidential election for a county. Looks up the
        county in the choices list, and returns the margin of victory for the winning candidate as
        a percentage of the total votes cast.

        Parameters
        ----------
        choices : list[str]
            List of "City, State" strings to fetch data for, e.g. "New York, NY"

        Returns
        -------
        pd.Series
            Series with the same index as the list of choices. Values are the victory margin for the
            winning candidate for the choice, as a percentage of the total votes cast.
        """


LOOKUP = {
    fetcher.CODE: fetcher
    for fetcher in [
        ObesityFetcher,
    ]
}
