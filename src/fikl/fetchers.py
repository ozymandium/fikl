from typing import List


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
        return [len(choice) for choice in choices]
