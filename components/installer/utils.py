import datetime
import requests
from bs4 import BeautifulSoup
import os
import json
from helpers.utils import get_app_support_directory
import logging

logger = logging.getLogger(__name__)


def format_pypi_tooltip_html(pypi_data, font_family_name):
    """
    Takes a dictionary with PyPI info and formats it into a styled HTML string.
    """
    info = pypi_data.get("info", {})
    if not info:
        return ""

    table_rows = []

    # Core Info
    if info.get("name"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Name</td><td class="tooltip-value">{info["name"]}</td></tr>'
        )
    if info.get("version"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Version</td><td class="tooltip-value">{info["version"]}</td></tr>'
        )
    if info.get("summary"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Summary</td><td class="tooltip-value">{info["summary"].strip()}</td></tr>'
        )

    # People (Author & Maintainer)
    author = info.get("author")
    author_email = info.get("author_email")
    author_str = ""
    if author:
        author_str = author
        if author_email:
            author_str += f" &lt;{author_email}&gt;"  # Use HTML entities for < >
        table_rows.append(
            f'<tr><td class="tooltip-label">Author</td><td class="tooltip-value">{author_str}</td></tr>'
        )

    maintainer = info.get("maintainer")
    maintainer_email = info.get("maintainer_email")
    maintainer_str = ""
    if maintainer:
        maintainer_str = maintainer
        if maintainer_email:
            maintainer_str += f" &lt;{maintainer_email}&gt;"
        # Only show maintainer if they are different from the author
        if maintainer_str and maintainer_str != author_str:
            table_rows.append(
                f'<tr><td class="tooltip-label">Maintainer</td><td class="tooltip-value">{maintainer_str}</td></tr>'
            )

    # Requirements
    if info.get("requires_python"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Requires Python</td><td class="tooltip-value">{info["requires_python"]}</td></tr>'
        )
    if info.get("requires_dist"):
        deps_html = "<br>".join(info["requires_dist"])
        table_rows.append(
            f'<tr><td class="tooltip-label">Dependencies</td><td class="tooltip-value">{deps_html}</td></tr>'
        )

    # License Info (Always shows License field)
    license_val = (
        info.get("license")
        if info.get("license")
        else "<span class='tooltip-placeholder'>Not Provided</span>"
    )
    table_rows.append(
        f'<tr><td class="tooltip-label">License</td><td class="tooltip-value">{license_val}</td></tr>'
    )
    if info.get("license_file"):
        table_rows.append(
            f'<tr><td class="tooltip-label">License File</td><td class="tooltip-value">{info["license_file"]}</td></tr>'
        )

    # Links, Keywords, and Details
    if info.get("project_url"):
        url = info["project_url"]
        link_html = f'<a href="{url}" style="color: #8ab4f8;">{url}</a>'
        table_rows.append(
            f'<tr><td class="tooltip-label">Project URL</td><td class="tooltip-value">{link_html}</td></tr>'
        )
    if info.get("keywords"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Keywords</td><td class="tooltip-value">{info["keywords"]}</td></tr>'
        )
    if info.get("provides_extra"):
        provides_html = "<br>".join(info["provides_extra"])
        table_rows.append(
            f'<tr><td class="tooltip-label">Provides</td><td class="tooltip-value">{provides_html}</td></tr>'
        )
    if info.get("classifiers"):
        classifiers_html = "<br>".join(info["classifiers"])
        table_rows.append(
            f'<tr><td class="tooltip-label">Classifiers</td><td class="tooltip-value">{classifiers_html}</td></tr>'
        )

    all_rows_html = "\n".join(table_rows)

    # --- Handle special top/bottom sections ---

    # Create a prominent warning if the package is yanked
    yanked_html = ""
    if info.get("yanked"):
        reason = info.get("yanked_reason") or "No reason provided."
        yanked_html = f"""
        <div class="yanked-warning">
            <strong>Warning: This version has been yanked.</strong>
            <br><span class="yanked-reason">Reason: {reason}</span>
        </div>
        """

    # Create a footer for the fetch timestamp
    footer_html = ""
    if pypi_data.get("fetched_at"):
        try:
            # Parse ISO 8601 timestamp and format it nicely
            dt_obj = datetime.datetime.fromisoformat(
                pypi_data["fetched_at"].replace("Z", "+00:00")
            )
            # Format to something like "16 Sep 2025, 03:07 PM IST"
            dt_obj = dt_obj.astimezone(
                datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            )  # Convert to IST
            fetched_at_str = dt_obj.strftime("%d %b %Y, %I:%M %p %Z")
            footer_html = f'<div class="tooltip-footer">Cached: {fetched_at_str}</div>'
        except (ValueError, TypeError):
            pass  # Ignore if timestamp is invalid

    # --- Assemble final HTML ---
    return f"""
    <style>
        .tooltip-container {{ font-family: '{font_family_name}', sans-serif; font-size: 14px; max-width: 550px; line-height: 1.5; }}
        .tooltip-table {{ border-spacing: 0; width: 100%; }}
        .tooltip-table td {{ padding: 2px 8px; vertical-align: top; }}
        .tooltip-label {{ font-weight: 600; white-space: nowrap; text-align: left; padding-right: 12px; color: #999999; }}
        .tooltip-value {{ color: #FFFFFF; word-break: break-word; }}
        .tooltip-placeholder {{ color: #777777; font-style: italic; }}
        a {{ text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .yanked-warning {{ background-color: #5c1b16; color: #f8d7da; padding: 8px; border-radius: 4px; margin-bottom: 10px; border: 1px solid #c93a3a; }}
        .yanked-reason {{ color: #f5c6cb; }}
        .tooltip-footer {{ font-size: 11px; color: #777777; text-align: right; padding-top: 8px; border-top: 1px solid #333333; margin-top: 8px; }}
    </style>
    <div class="tooltip-container">
        {yanked_html}
        <table class="tooltip-table">
            {all_rows_html}
        </table>
        {footer_html}
    </div>
    """


def save_file(
    data: list, app_name: str = "P4cMan", file_name: str = "library_list.txt"
):
    """Saves data to a file in the application's support directory."""
    # Saves Data in a pre-defined directory
    app_support_dir = get_app_support_directory(app_name)
    file_path = os.path.join(app_support_dir, file_name)
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


def download_data_from_pypi(
    app_name: str = "P4cMan", file_name: str = "library_list.txt"
) -> list:
    """Downloads the list of all PyPI packages and saves them to a file."""
    # Downloads Data from PyPi.org
    url = "https://pypi.org/simple/"
    headers = {"User-Agent": "insomnia/11.4.0"}
    response = requests.request("GET", url, data="", headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    library_list = [tag.get_text() for tag in soup.find_all("a")]
    save_file(library_list, app_name, file_name)
    return library_list


def load_data(app_name="P4cMan", file_name="library_list.txt") -> list:
    """Loads data from a file in the application's support directory, downloading it if not present."""
    # Loads Data from a pre-defined directory
    try:
        app_support_dir = get_app_support_directory(app_name)
        file_path = os.path.join(app_support_dir, file_name)

        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                data = json.load(file)
        else:
            data = download_data_from_pypi(app_name, file_name)
    except Exception as e:
        data = []
        logging.error(f"Error loading data: {e}")
    return data
