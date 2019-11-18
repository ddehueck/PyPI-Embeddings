from collections import OrderedDict
import requests


class RetrieveProjectReadmeTask:
    """
    Retrieve README file from GitHub if available.
    Modified from: https://github.com/thoth-station/selinon-worker/blob/master/thoth/worker/tasks/github.py
    """

    _GITHUB_README_PATH = (
        "https://raw.githubusercontent.com/{owner}/{repo}/master/README{extension}"
    )

    # Based on https://github.com/github/markup#markups
    # Markup type to its possible extensions mapping, we use OrderedDict as we
    # check the most used types first
    README_TYPES = OrderedDict(
        (
            ("Markdown", ("md", "markdown", "mdown", "mkdn")),
            ("reStructuredText", ("rst",)),
            ("AsciiDoc", ("asciidoc", "adoc", "asc")),
            ("Textile", ("textile",)),
            ("RDoc", ("rdoc",)),
            ("Org", ("org",)),
            ("Creole", ("creole",)),
            ("MediaWiki", ("mediawiki", "wiki")),
            ("Pod", ("pod",)),
            ("Unknown", ("",)),
        )
    )

    def run(self, owner, name) -> dict:
        """Retrieve README file from GitHub."""

        for readme_type, extensions in self.README_TYPES.items():
            for extension in extensions:
                if extension:
                    extension = "." + extension

                url = self._GITHUB_README_PATH.format(
                    owner=owner, repo=name, extension=extension
                )

                oauth = ''#'?client_id=44b21a666f2054cf9300&client_secret=2e0138cdc64cc15ff89d58a9e1f10614b365b3ff'

                response = requests.get(url + oauth)
                if response.status_code != 200:
                    continue

                return {
                    "type": readme_type,
                    "content": response.text,
                    "url": url,
                }
        # Nothing was found
        return {
            "type": None,
            "content": '',
            "url": None,
        }
