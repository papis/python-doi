import re
import sys
import logging

from typing import Optional


__version__ = '0.2.0'
logger = logging.getLogger("doi")   # type: logging.Logger


def pdf_to_doi(filepath: str, maxlines: Optional[int] = None) -> Optional[str]:
    """Try to get DOI from a filepath. It looks for a regex in the binary
    data and returns the first DOI found, in the hopes that this DOI
    is the correct one.

    :param filepath: Path to the pdf file.
    :param maxlines: Maximum number of lines that should be checked
        For some documents, it could spend a long time trying to look for
        a DOI, and DOIs in the middle of documents don't tend to be the correct
        DOI of the document.
    :returns: DOI or ``None``.
    """
    if maxlines is None:
        maxlines = sys.maxsize

    with open(filepath, 'rb') as fd:
        for j, line in enumerate(fd):
            doi = find_doi_in_text(line.decode('ascii', errors='ignore'))
            if doi:
                return doi
            if j > maxlines:
                return None
        return None


def validate_doi(doi: str) -> Optional[str]:
    """We check that the DOI can be resolved by
    `official means <http://www.doi.org/factsheets/DOIProxy.html>`_. If so, we
    return the resolved URL, otherwise, we return ``None`` (which means the
    DOI is invalid).

    :param doi: Identifier.
    :returns: The URL assigned to the DOI or ``None``.
    """
    from urllib.error import HTTPError
    import urllib.request
    import urllib.parse
    import json
    url = "https://doi.org/api/handles/{doi}".format(doi=doi)
    logger.debug('handle url %s', url)
    request = urllib.request.Request(url)

    try:
        result = json.loads(urllib.request.urlopen(request).read().decode())
    except HTTPError:
        raise ValueError('HTTP 404: DOI not found')
    else:
        urls = [v['data']['value']
                for v in result['values'] if v.get('type') == 'URL']
        return urls[0] if urls else None


def get_clean_doi(doi: str) -> str:
    """Check if the DOI is actually a URL and in that case just get
    the exact DOI.

    :param doi: String containing a DOI.
    :returns: The extracted DOI.
    """
    doi = re.sub(r'%2F', '/', doi)
    # For pdfs
    doi = re.sub(r'\)>', ' ', doi)
    doi = re.sub(r'\)/S/URI', ' ', doi)
    doi = re.sub(r'(/abstract)', '', doi)
    doi = re.sub(r'\)$', '', doi)
    return doi


def find_doi_in_text(text: str) -> Optional[str]:
    """Try to find a DOI in a text.

    :param text: Text in which to look for DOI.
    :returns: A DOI, if found, otherwise ``None``.
    """
    text = get_clean_doi(text)
    forbidden_doi_characters = r'"\s%$^\'<>@,;:#?&'
    # Sometimes it is in the javascript defined
    var_doi = re.compile(
        r'doi(.org)?'
        r'\s*(=|:|/|\()\s*'
        r'("|\')?'
        r'(?P<doi>[^{fc}]+)'
        r'("|\'|\))?'
        .format(
            fc=forbidden_doi_characters
        ), re.I
    )

    for regex in [var_doi]:
        miter = regex.finditer(text)
        try:
            m = next(miter)
            if m:
                doi = m.group('doi')
                return get_clean_doi(doi)
        except StopIteration:
            pass
    return None


def get_real_url_from_doi(doi: str) -> Optional[str]:
    """Get a URL corresponding to a DOI.

    :param doi: Identifier.
    :returns: A URL for the DOI. If the DOI is invalid, return ``None``.
    """
    url = validate_doi(doi)
    if url is None:
        return url

    m = re.match(r'.*linkinghub\.elsevier.*/pii/([A-Z0-9]+).*', url, re.I)
    if m:
        return ('https://www.sciencedirect.com/science/article/abs/pii/{pii}'
                .format(pii=m.group(1)))
    return url
