"""
Handle generating HTML content from Jinja2 templates located in src/templates
"""
import os
import jinja2
import logging


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
