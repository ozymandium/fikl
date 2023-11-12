"""
Handle generating HTML content from Jinja2 templates located in src/templates
"""
import os
import jinja2
import logging
import bs4
import re
import uuid


def generate_html(template_name, **kwargs):
    """
    Generate HTML content from a Jinja2 template.

    Parameters
    ----------
    template_name : str
        Name of the template to use. This should be the name of a file in the
        templates directory. It should not include the file extension.
    """
    logger = logging.getLogger(__name__)
    logger.debug("Generating HTML from template: %s", template_name)
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))
    logger.debug("Template directory: %s", template_dir)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    # display the list of templates that jinja sees
    logger.debug(f"Available templates: {env.list_templates()}")
    template = env.get_template(f"{template_name}.html.j2")
    return template.render(**kwargs)

def add_toc(html):
    """
    Add a table of contents to an HTML document with hyperlinks to each heading.

    Reference Code:

        import re # We are going to need to use regular expressions later on
        import requests
        from bs4 import BeautifulSoupwiki_page = requests.get("https://en.wikipedia.org/wiki/Machine_learning")soup = BeautifulSoup(wiki_page.content, 'html.parser')title_node = soup.find("title")
        tile_data = [title_node.name, title_node.get_text()]hns = soup.find_all(re.compile("h[0-9]{1}"))
        hn_structure = []
        for hn in hns:
            hn_text_content = [x for x in hn.stripped_strings if x is not None]
            if len(hn_text_content) > 0:
                hn_structure.append([hn.name, hn_text_content[0]])
        tag_template = "<{tag_name}>{content}</{tag_name}>\n"
        html_output = "<html>\n"
        html_output += tag_template.format(tag_name = tile_data[0], content = tile_data[1])
        for hn in hn_structure:
            html_output += tag_template.format(tag_name = hn[0], content = hn[1])
        html_output += "</html>"

    Parameters
    ----------
    html : str
        HTML content to add the table of contents to.

    Returns
    -------
    str
        HTML content with the table of contents added.
    """
    logger = logging.getLogger(__name__)
    logger.debug("Adding table of contents to HTML")
    soup = bs4.BeautifulSoup(html, "html.parser")
    toc = bs4.BeautifulSoup("<div id='toc'><h1>Table of Contents</h1></div>", "html.parser")
    for heading in soup.find_all(re.compile("^h[1-6]$")):
        # not all headings will have ids, so we need to check for that
        # if the heading does not have an id, we will create one
        if heading.get("id") is None:
            # make a unique id for the heading
            heading["id"] = str(uuid.uuid4())
        # add the heading to the table of contents
        toc_heading = bs4.BeautifulSoup(f"<a href='#{heading['id']}'>{heading.get_text()}</a>", "html.parser")
        toc.append(toc_heading)
        # add an anchor to the heading
        heading_anchor = bs4.BeautifulSoup(f"<a id='{heading['id']}'></a>", "html.parser")

        heading.insert(0, heading_anchor)
    soup.body.insert(0, toc)
    return str(soup)