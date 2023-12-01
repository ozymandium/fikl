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
import pprint
import logging
import requests

import pandas as pd
import geocoder


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

    def __init__(self): 
        self.df = pd.read_csv(self.SOURCE_FILE)
        # filter out non-2020 data
        self.df = self.df[self.df["year"] == 2020]
        # filter out rows where party is not DEMOCRAT or REPUBLICAN
        self.df = self.df[self.df["party"].isin(["DEMOCRAT", "REPUBLICAN"])]

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
        logger = logging.getLogger(__name__)
        ret = []

        session = requests.Session()

        for choice in choices:
            # use geocoder to get the county name from the choice
            g = geocoder.osm(choice, session=session)
            logging.debug(f"geocoder result for {choice}:\n{pprint.pformat(g.json)}")

            # `county` will be formatted as "Suffolk County". need to convert it to "SUFFOLK"
            county = g.json["raw"]["address"]["county"]
            county = county.replace(" County", "").upper()
            # state abbreviation is in the address as "US-MA"
            # FIXME: can uppercase the state in the geocoder query and remove this filter instead of
            #        replacing "US-" with ""
            state = g.json["raw"]["address"]["ISO3166-2-lvl4"]
            state = state.replace("US-", "")
            # filter the data to only the county and state we want
            df = self.df[(self.df["county_name"] == county) & (self.df["state_po"] == state)]

            # ensure totalvotes is the same for both rows
            if df["totalvotes"].nunique() != 1:
                raise ValueError("totalvotes not the same for both parties")
            
            # the margin is the percent of votes for the winning party minus the percent of votes
            # for the losing party. don't need to determine the winner, just take the difference
            # between the two percentages and return the absolute value.
            # some states have separate results for different types of voting, e.g. mail-in vs
            # in-person. we don't care about that, so sum all the votes for each party.
            # d_votes = float(df[df["party"] == "DEMOCRAT"]["candidatevotes"].iloc[0])
            # r_votes = float(df[df["party"] == "REPUBLICAN"]["candidatevotes"].iloc[0])
            d_votes = float(df[df["party"] == "DEMOCRAT"]["candidatevotes"].sum())
            r_votes = float(df[df["party"] == "REPUBLICAN"]["candidatevotes"].sum())
            total_votes = float(df["totalvotes"].iloc[0])
            margin = abs((d_votes - r_votes) / total_votes) * 100.
            ret.append(margin)

        session.close()

        return pd.Series(ret, index=choices)



LOOKUP = {
    fetcher.CODE: fetcher
    for fetcher in [
        ObesityFetcher,
        CountyElectionMargin,
    ]
}
