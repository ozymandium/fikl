"""
Tests code in src/fikl/html.py
"""
from fikl.html import (
    html_from_doc,
    prettify,
)

import unittest
from collections import OrderedDict


class TestHtmlFromDoc(unittest.TestCase):
    """
    Tests html_from_doc().
    """

    def test_simple(self) -> None:
        """
        Tests a simple case.
        """
        doc = """
        # Heading 1
        ## Heading 2
        ### Heading 3
        #### Heading 4
        ##### Heading 5
        ###### Heading 6
        """
        html = """
        <h1>Heading 1</h1>
        <h2>Heading 2</h2>
        <h3>Heading 3</h3>
        <h4>Heading 4</h4>
        <h5>Heading 5</h5>
        <h6>Heading 6</h6>
        """
        self.assertEqual(prettify(html_from_doc(doc)), prettify(html))

    def test_list(self) -> None:
        """
        Tests a simple case.
        """
        doc = """
        # Heading 1
        ## Heading 2
        ### Heading 3
        #### Heading 4
        ##### Heading 5
        ###### Heading 6

        * item 1
        * item 2
        * item 3
        """
        html = """
        <h1>Heading 1</h1>
        <h2>Heading 2</h2>
        <h3>Heading 3</h3>
        <h4>Heading 4</h4>
        <h5>Heading 5</h5>
        <h6>Heading 6</h6>
        <ul>
        <li>item 1</li>
        <li>item 2</li>
        <li>item 3</li>
        </ul>
        """
        self.assertEqual(prettify(html_from_doc(doc)), prettify(html))

    def test_table(self) -> None:
        """
        Tests a simple case.
        """
        doc = """
        # Heading 1
        ## Heading 2
        ### Heading 3
        #### Heading 4
        ##### Heading 5
        ###### Heading 6

        | A | B | C |
        |---|---|---|
        | 1 | 2 | 3 |
        | 4 | 5 | 6 |
        """
        html = """
        <h1>Heading 1</h1>
        <h2>Heading 2</h2>
        <h3>Heading 3</h3>
        <h4>Heading 4</h4>
        <h5>Heading 5</h5>
        <h6>Heading 6</h6>
        <table>
        <thead>
        <tr>
        <th>A</th>
        <th>B</th>
        <th>C</th>
        </tr>
        </thead>
        <tbody>
        <tr>
        <td>1</td>
        <td>2</td>
        <td>3</td>
        </tr>
        <tr>
        <td>4</td>
        <td>5</td>
        <td>6</td>
        </tr>
        </tbody>
        </table>
        """
        self.assertEqual(prettify(html_from_doc(doc)), prettify(html))
