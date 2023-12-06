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


class DepressionFetcher:
    """
    Fetcher for depression data.
    Source from CDC PLACES project, 2023 data.
    https://data.cdc.gov/500-Cities-Places/PLACES-Place-Data-GIS-Friendly-Format-2023-release/vgc8-iyc4
    """

    CODE = "Depression"
    SOURCE_FILE = os.path.join(
        os.path.dirname(__file__),
        "data",
        "PLACES__Place_Data__GIS_Friendly_Format___2023_release.csv",
    )

    def fetch(self, choices: List[str]) -> pd.Series:
        """
        Fetches depression data for the given choices.
        Parameters
        ----------
        choices : list[str]
            List of choice names to fetch data for
        Returns
        -------
        pd.Series
            Series with the same index as the list of choices. Values are the depression rate for the
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
        df["choice"] = df["PlaceName"] + ", " + df["StateAbbr"]
        # set the index to the new column
        df.set_index("choice", inplace=True)
        # check that all choices are in the data
        if not set(choices).issubset(set(df.index)):
            raise ValueError(f"choices not in data: {set(choices) - set(df.index)}")
        # narrow the data to only the choices we want
        df = df.loc[choices]
        # return the depression rate for each choice
        return df["DEPRESSION_AdjPrev"].astype(float)


class CityToCountyLookup:
    """
    Given a string with the format "city, state_abbr", returns a list of counties in which the city
    lies.

    Uses 2020 census data. See data/census/README.md for details.

    Parameters
    ----------
    city_and_state : str
        String with the format "city, state_abbr", e.g. "New York, NY"

    Returns
    -------
    list[str]
        List of counties in which the city lies, e.g. ["Guilford", "Randolph"]
    """

    PLACE_TO_COUNTY_FILE = os.path.join(
        os.path.dirname(__file__), "data/census/national_place2020.txt"
    )
    STATE_FILE = os.path.join(os.path.dirname(__file__), "data/census/national_state2020.txt")
    COUNTY_POPULATION_FILE = os.path.join(
        os.path.dirname(__file__), "data/census/co-est2022-pop.xlsx"
    )

    def __init__(self):
        # load the place to county data
        self.place_county_df = pd.read_csv(self.PLACE_TO_COUNTY_FILE, sep="|")
        # remove all columns except the ones we need
        self.place_county_df = self.place_county_df[["STATE", "PLACENAME", "COUNTIES"]]

        # load the state data
        self.state_abbr_df = pd.read_csv(self.STATE_FILE, sep="|")
        # remove all columns except the ones we need
        self.state_abbr_df = self.state_abbr_df[["STATE", "STATE_NAME"]]

        # load the county population data
        self.county_pop_df = pd.read_excel(self.COUNTY_POPULATION_FILE, skiprows=3, skipfooter=5)
        # there are a lot of merged cells, so we need to do some cleanup
        # the first column is the name of the county, but it's merged with the state name
        # it also sometimes has a leading "." character. Remove only a leading "." character
        self.county_pop_df["name"] = self.county_pop_df["Unnamed: 0"].str.replace(".", "", 1)
        # the first row is the united states total, so remove it
        self.county_pop_df = self.county_pop_df.iloc[1:]
        # rename the 2022 column to "population"
        self.county_pop_df.rename(columns={2022: "population"}, inplace=True)
        # remove all columns except the ones we need
        self.county_pop_df = self.county_pop_df[["name", "population"]]
        # name column is in the format "county, state". split it into two columns: "county" and
        # "state". "state" is the state abbreviation instead of the full name, determined using the
        # _get_state_abbr method.
        self.county_pop_df["county"] = self.county_pop_df["name"].str.split(", ").str[0]
        self.county_pop_df["state"] = self.county_pop_df["name"].str.split(", ").str[1]
        self.county_pop_df["state"] = self.county_pop_df["state"].apply(self._get_state_abbr)
        # remove the name column
        self.county_pop_df.drop(columns=["name"], inplace=True)
        # county column will have either " County" or " Parish" appended to it. remove it.
        self.county_pop_df["county"] = self.county_pop_df["county"].str.replace(" County", "")
        self.county_pop_df["county"] = self.county_pop_df["county"].str.replace(" Parish", "")
        # set the index to the state and county columns
        self.county_pop_df.set_index(["state", "county"], inplace=True)

    def _get_counties(self, state: str, city: str) -> List[str]:
        # filter rows where the state abbreviation matches and the PLACENAME column contains the
        # city name
        df = self.place_county_df[
            (self.place_county_df["STATE"] == state)
            & (self.place_county_df["PLACENAME"] == city + " city")
        ]
        # there should only be one row
        if len(df) != 1:
            raise ValueError(f"multiple rows for {state}, {city}:\n{df}")
        # get the counties column and split it on the ~ character
        counties = df["COUNTIES"].iloc[0].split("~")
        # remove trailing " County" or " Parish" from each county
        counties = [county.replace(" County", "") for county in counties]
        counties = [county.replace(" Parish", "") for county in counties]
        # remove empty strings
        counties = [county for county in counties if county != ""]
        return counties

    def _get_county_pop(self, state: str, county: str) -> int:
        """
        Returns the population of the given county. County population is stored in an XSLX file
        in the census data.

        Parameters
        ----------
        state : str
            State abbreviation, e.g. "NC"
        county : str
            County name, e.g. "Guilford"

        Returns
        -------
        int
            Population of the county
        """
        # filter rows where the state and county match
        df = self.county_pop_df[
            (self.county_pop_df.index.get_level_values(0) == state)
            & (self.county_pop_df.index.get_level_values(1) == county)
        ]
        # there should only be one row
        if len(df) != 1:
            raise ValueError(f"multiple rows for {state}, {county}")
        # get the population
        return df["population"].iloc[0]

    def _get_state_abbr(self, state: str) -> str:
        """
        Returns the state abbreviation for the given state name. State names are stored in a TXT
        file in the census data, and parsed in self.state_abbr_df.

        Parameters
        ----------
        state : str
            State name, e.g. "North Carolina"

        Returns
        -------
        str
            State abbreviation, e.g. "NC"
        """
        # filter rows where the state name matches
        df = self.state_abbr_df[self.state_abbr_df["STATE_NAME"] == state]
        # there should only be one row
        if len(df) != 1:
            raise ValueError(f"multiple rows for {state}")
        # get the state abbreviation
        return df["STATE"].iloc[0]

    def __call__(self, state: str, city: str) -> str:
        """
        Given a string with the format "city, state_abbr", returns the primary county in which the
        city lies. The primary county is the county with the largest population among all counties
        in which the city lies.

        Parameters
        ----------
        city : str
            City name, e.g. "New York"
        state : str
            State abbreviation, e.g. "NY"

        Returns
        -------
        str

        """
        counties = self._get_counties(state, city)
        # get the population of each county
        county_populations = [self._get_county_pop(state, county) for county in counties]
        # get the index of the county with the largest population
        max_county_idx = county_populations.index(max(county_populations))
        # return the county name
        return counties[max_county_idx]


class CountyElectionMargin:
    """
    Fetches the margin of victory for the 2020 presidential election for a county.

    Sourced from:
    MIT Election Data and Science Lab, 2018, "County Presidential Election Returns 2000-2020",
    https://doi.org/10.7910/DVN/VOQCHQ, Harvard Dataverse, V11, UNF:6:HaZ8GWG8D2abLleXN3uEig== [fileUNF]
    """

    CODE = "County Politics"
    SOURCE_FILE = os.path.join(os.path.dirname(__file__), "data", "countypres_2000-2020.csv")

    def __init__(self):
        self.df = pd.read_csv(self.SOURCE_FILE)
        # filter out non-2020 data
        self.df = self.df[self.df["year"] == 2020]
        # filter out rows where party is not DEMOCRAT or REPUBLICAN
        self.df = self.df[self.df["party"].isin(["DEMOCRAT", "REPUBLICAN"])]

        self.city_to_county = CityToCountyLookup()

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

        for choice in choices:
            # look up county for city
            city, state = choice.split(", ")
            # convert to upper case since that's how it's stored in the data
            county = self.city_to_county(state, city).upper()
            logger.debug(f"city: {city}, state: {state}, county: {county}")

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
            margin = abs((d_votes - r_votes) / total_votes) * 100.0
            ret.append(margin)

        return pd.Series(ret, index=choices)


class ZoriFetcher:
    """
    Zillow Observed Rent Index (ZORI) fetcher.

    https://www.zillow.com/research/data/

    Zillow Observed Rent Index (ZORI): A smoothed measure of the typical observed market rate rent
    across a given region. ZORI is a repeat-rent index that is weighted to the rental housing stock
    to ensure representativeness across the entire market, not just those homes currently listed
    for-rent. The index is dollar-denominated by computing the mean of listed rents that fall into
    the 40th to 60th percentile range for all homes and apartments in a given region, which is once
    again weighted to reflect the rental housing stock. Details available in ZORI methodology.

    Note that this is for all rentals, not just apartments, or certain sizes of apartments.
    """

    CODE = "ZORI"
    SOURCE_FILE = os.path.join(
        os.path.dirname(__file__), "data", "City_zori_uc_sfrcondomfr_sm_sa_month.csv"
    )

    def __init__(self):
        self.df = pd.read_csv(self.SOURCE_FILE)
        # create a new column with the format "city, state"
        self.df["choice"] = self.df["RegionName"] + ", " + self.df["State"]
        # rename the 2023-10-31 column to "zori"
        self.df.rename(columns={"2023-10-31": "zori"}, inplace=True)
        # filter out columns we don't need
        self.df = self.df[["choice", "zori"]]
        # set the index to the choice column
        self.df.set_index("choice", inplace=True)

    def fetch(self, choices: List[str]) -> pd.Series:
        """
        Fetches the ZORI for the given choices.

        Parameters
        ----------
        choices : list[str]
            List of "City, State" strings to fetch data for, e.g. "New York, NY"

        Returns
        -------
        pd.Series
            Series with the same index as the list of choices. Values are the ZORI for the
            choice.
        """
        # ensure choices are unique
        if len(set(choices)) != len(choices):
            raise ValueError("choices must be unique")
        # check that all choices are in the data
        if not set(choices).issubset(set(self.df.index)):
            raise ValueError(f"choices not in data: {set(choices) - set(self.df.index)}")
        # narrow the data to only the choices we want
        df = self.df.loc[choices]
        # return the ZORI for each choice
        return df["zori"].astype(float)


LOOKUP = {
    fetcher.CODE: fetcher
    for fetcher in [
        ObesityFetcher,
        CountyElectionMargin,
        DepressionFetcher,
        ZoriFetcher,
    ]
}
