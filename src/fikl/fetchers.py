from typing import List, Callable
import importlib

import pandas as pd


class ExampleFetcher:
    """
    This is an example fetch class.
    """

    def __init__(self):
        """
        The fetcher is initialized without any arguments, as fikl does not make any assumptions
        about the input data or output data beyond their data types.
        """
        pass

    def __call__(self, choices: List[str]) -> List[float]:
        """
        The fetcher is called with a list of choices, and returns a list of floats. In this example,
        the fetcher simply returns the length of each choice string.

        Parameters
        ----------
        choices : List[str]
            A list of choices which fikl is evaluating.

        Returns
        -------
        List[float]
            A list of floats, one for each choice. Each float must be non NaN and non infinite.
        """
        return [float(len(choice)) for choice in choices]


def _get_fetcher(path: str) -> Callable:
    """
    Get an instance of the specific the fetcher class from the import path.

    Parameters
    ----------
    path : str
        import path to the fetcher class, of the form "package.module.Class" or at least
        "module.Class"

    Returns
    -------
    Callable
        an instantiated fetcher class
    """
    # split the path into the module and class name
    module, cls = path.rsplit(".", 1)
    # import the module
    mod = __import__(module, fromlist=[cls])
    # get the class from the module
    fetcher = getattr(mod, cls)
    # ensure that the fetcher has a __call__ method
    if not hasattr(fetcher, "__call__"):
        raise ValueError(f"Fetcher {path} does not have a __call__ method")
    return fetcher()


def fetch(sources: list[str], choices: list[str]) -> pd.DataFrame:
    """
    Fetch data from the sources for the choices.

    Parameters
    ----------
    sources : list[str]
        list of import paths to the fetcher classes
    choices : list[str]
        list of choices to evaluate

    Returns
    -------
    pd.DataFrame
        a dataframe with the fetched data. The index is the choices, and the columns are the sources.
    """
    # get the fetchers
    fetchers = [_get_fetcher(source) for source in sources]
    dtypes = [fetcher.DTYPE for fetcher in fetchers]
    # fetch the data
    data = [fetcher(choices) for fetcher in fetchers]
    # ensure the data types are all the advertised types
    for i, d in enumerate(data):
        if not isinstance(d, list):
            raise TypeError(f"Fetcher {sources[i]} returned a {type(d)}, not a list")
        for j, v in enumerate(d):
            if not isinstance(v, dtypes[i]):
                raise TypeError(
                    f"Fetcher {sources[i]} returned a {type(v)} at index {j}, not a {dtypes[i]}"
                )
    # create a dataframe
    df = pd.DataFrame(data).T
    # set the column names
    df.columns = sources
    # set the index
    df.index = choices
    # convert the dtypes
    df = df.astype(dict(zip(sources, dtypes)))
    return df
