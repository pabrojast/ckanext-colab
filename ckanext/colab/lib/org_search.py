# encoding: utf-8
"""Organization name matching used by the registration picker and its API.

The JavaScript combobox mirrors this ranking so server-side ``?q=`` and
client-side filtering stay consistent: case-insensitive, accent-folding,
AND-tokens, title preferred over slug.
"""
from __future__ import unicode_literals

import re
import unicodedata


# Keep in sync with MAX_VISIBLE in the registration form combobox.
MAX_VISIBLE = 10


def normalize_text(value):
    """Fold case and accents so 'Université' matches 'universite'."""
    if not value:
        return ''
    decomposed = unicodedata.normalize('NFKD', str(value))
    stripped = ''.join(
        ch for ch in decomposed if unicodedata.category(ch) != 'Mn'
    )
    stripped = stripped.lower()
    stripped = re.sub(r'[^\w]+', ' ', stripped, flags=re.UNICODE)
    stripped = stripped.replace('_', ' ')
    return re.sub(r'\s+', ' ', stripped).strip()


def slim_organization(org):
    """Public payload: name (slug) + display title only."""
    name = (org.get('name') or '').strip()
    title = (org.get('title') or org.get('display_name') or name or '').strip()
    display_name = (org.get('display_name') or title or name).strip()
    return {
        'name': name,
        'title': title,
        'display_name': display_name,
    }


def organization_search_score(query, org):
    """Return a ranking score, or None if the org does not match.

    Higher is better. Exact title wins, then prefix, word-start, substring,
    then slug matches. All query tokens must appear in title or slug.
    """
    q = normalize_text(query)
    if not q:
        return None

    title = normalize_text(org.get('title') or org.get('display_name') or '')
    name = normalize_text(org.get('name') or '')
    haystack = (title + ' ' + name).strip()
    if not haystack:
        return None

    tokens = q.split()
    if not all(token in haystack for token in tokens):
        return None

    title_words = title.split()
    name_words = name.split()

    if title == q:
        score = 1000
    elif title.startswith(q):
        score = 900
    elif any(word.startswith(q) for word in title_words):
        score = 800
    elif q in title:
        score = 700
    elif name == q or name.startswith(q):
        score = 600
    elif any(word.startswith(q) for word in name_words):
        score = 550
    elif q in name:
        score = 500
    else:
        word_starts = sum(
            1 for token in tokens
            if any(word.startswith(token) for word in title_words)
        )
        score = 200 + (word_starts * 50)

    # Prefer the shorter official name when scores tie on quality.
    score -= min(len(title), 80)
    return score


def filter_organizations(orgs, query, limit=None):
    """Return matching orgs sorted by score (desc), then title."""
    scored = []
    for org in orgs or []:
        score = organization_search_score(query, org)
        if score is None:
            continue
        scored.append((score, org))

    scored.sort(key=lambda item: (
        -item[0],
        (item[1].get('title') or item[1].get('name') or '').lower(),
    ))
    results = [org for _, org in scored]
    if limit is not None:
        return results[:limit]
    return results


def find_similar_organizations(orgs, query, limit=5):
    """Matches for the 'did you mean' panel when creating a new org."""
    q = normalize_text(query)
    if len(q) < 2:
        return []
    return filter_organizations(orgs, query, limit=limit)


def is_exact_organization_match(orgs, query):
    """True when the typed name is already an existing title or slug."""
    q = normalize_text(query)
    if not q:
        return False
    for org in orgs or []:
        title = normalize_text(org.get('title') or org.get('display_name') or '')
        name = normalize_text(org.get('name') or '')
        if q == title or q == name:
            return True
    return False
