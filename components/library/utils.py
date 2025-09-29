def rank_query(dataList, query):
    """
    Ranks a list of data items based on a query string.

    The function filters `dataList` to find items whose 'name' field (case-insensitive) contains the `query` string (case-insensitive).
    The matching items are then sorted by the position of the first occurrence of the `query` within their 'name' field.
    Items where the query appears earlier in the name will be ranked higher.

    Args:
        dataList (list): A list of dictionaries, where each dictionary is expected to have a 'name' key (str).
        query (str): The search string to use for filtering and ranking.

    Returns:
        list: A new list containing the matching items from `dataList`, sorted by the relevance of the query's
              position within their 'name'. If no matches are found, an empty list is returned.
    """
    lower_query = query.lower()
    matches = [item for item in dataList if lower_query in item["name"].lower()]
    sorted_matches = sorted(
        matches, key=lambda item: item["name"].lower().find(lower_query)
    )
    return sorted_matches


def human_readable_size(size: int) -> str:
    """
    Converts a size in bytes into a human-readable string with appropriate units.

    The function formats the given size (in bytes) into a more readable format,
    using B, KB, MB, or GB units, rounded to two decimal places.
    It also wraps the unit in an HTML `<span>` tag for styling.

    Args:
        size (int): The size in bytes (e.g., file size).

    Returns:
        str: A string representing the size with its unit,
             e.g., "1.23 <span style='font-size:8pt'>KB</span>".
    """
    if size / (1024 * 1024 * 1024) < 0.1:
        if size / (1024 * 1024) < 0.1:
            if size / (1024) < 0.1:
                if size < 0.1:
                    return f"{size * 8} <span style='font-size:8pt'>b</span>"
                else:
                    return f"{size:.2f} <span style='font-size:8pt'>B</span>"
            else:
                return f"{size / 1024:.2f} <span style='font-size:8pt'>KB</span>"
        else:
            return f"{size / (1024 * 1024):.2f} <span style='font-size:8pt'>MB</span>"
    else:
        return (
            f"{size / (1024 * 1024 * 1024):.2f} <span style='font-size:8pt'>GB</span>"
        )


def format_project_urls(urls):
    """Formats a list of project URLs into clickable <a> tags."""
    if not urls:
        return ""
    links = []
    for url_str in urls:
        # Handles formats like "Homepage, https://..."
        parts = [part.strip() for part in url_str.split(",", 1)]
        if len(parts) == 2:
            name, url = parts
            links.append(f'<a href="{url}" style="color: #8ab4f8;">{name}</a>')
        else:  # Fallback for plain URLs
            links.append(f'<a href="{url_str}" style="color: #8ab4f8;">{url_str}</a>')
    return "<br>".join(links)


def format_tooltip_html(item, font_family_name):
    """
    Takes a dictionary of package metadata and formats it into a styled HTML string.
    """
    table_rows = []

    # --- Core Info ---
    if item.get("name"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Name</td><td class="tooltip-value">{item["name"]}</td></tr>'
        )
    if item.get("version"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Version</td><td class="tooltip-value">{item["version"]}</td></tr>'
        )
    if item.get("summary"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Summary</td><td class="tooltip-value">{item["summary"].strip()}</td></tr>'
        )
    if item.get("author"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Author</td><td class="tooltip-value">{item["author"]}</td></tr>'
        )

    # --- Requirements ---
    if item.get("requires_python"):
        table_rows.append(
            f'<tr><td class="tooltip-label">Requires Python</td><td class="tooltip-value">{item["requires_python"]}</td></tr>'
        )
    if item.get("requires_dist"):
        deps_html = "<br>".join(item["requires_dist"])
        table_rows.append(
            f'<tr><td class="tooltip-label">Dependencies</td><td class="tooltip-value">{deps_html}</td></tr>'
        )

    # --- License Info (Always shows License field) ---
    license_val = (
        item.get("license")
        if item.get("license")
        else "<span class='tooltip-placeholder'>Not Provided</span>"
    )
    table_rows.append(
        f'<tr><td class="tooltip-label">License</td><td class="tooltip-value">{license_val}</td></tr>'
    )
    if item.get("license_expression"):
        table_rows.append(
            f'<tr><td class="tooltip-label">License Expression</td><td class="tooltip-value">{item["license_expression"]}</td></tr>'
        )
    if item.get("license_file"):
        files_html = "<br>".join(item["license_file"])
        table_rows.append(
            f'<tr><td class="tooltip-label">License Files</td><td class="tooltip-value">{files_html}</td></tr>'
        )

    # --- Links & Details ---
    if item.get("project_url"):
        urls_html = format_project_urls(item["project_url"])
        table_rows.append(
            f'<tr><td class="tooltip-label">Project URLs</td><td class="tooltip-value">{urls_html}</td></tr>'
        )
    if item.get("provides_extra"):
        provides_html = "<br>".join(item["provides_extra"])
        table_rows.append(
            f'<tr><td class="tooltip-label">Provides</td><td class="tooltip-value">{provides_html}</td></tr>'
        )
    if item.get("classifier"):
        classifiers_html = "<br>".join(item["classifier"])
        table_rows.append(
            f'<tr><td class="tooltip-label">Classifiers</td><td class="tooltip-value">{classifiers_html}</td></tr>'
        )

    all_rows_html = "\n".join(table_rows)

    return f"""
    <style>
        .tooltip-container {{ font-family: '{font_family_name}', sans-serif; font-size: 14px; max-width: 500px; line-height: 1.5; }}
        .tooltip-table {{ border-spacing: 0; width: 100%; }}
        .tooltip-table td {{ padding: 2px 8px; vertical-align: top; }}
        .tooltip-label {{ font-weight: 600; white-space: nowrap; text-align: left; padding-right: 12px; color: #999999; }}
        .tooltip-value {{ color: #FFFFFF; }}
        .tooltip-placeholder {{ color: #777777; font-style: italic; }}
        a {{ text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
    <div class="tooltip-container">
        <table class="tooltip-table">
            {all_rows_html}
        </table>
    </div>
    """
