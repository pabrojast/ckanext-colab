from ckanext.colab.lib.org_search import (
    filter_organizations,
    find_similar_organizations,
    is_exact_organization_match,
    normalize_text,
    organization_search_score,
    slim_organization,
)


ORGS = [
    {'name': 'unesco-ihp', 'title': 'UNESCO IHP Secretariat', 'display_name': 'UNESCO IHP Secretariat'},
    {'name': 'ihp-france', 'title': 'IHP National Committee of France', 'display_name': 'IHP National Committee of France'},
    {'name': 'universite-lille', 'title': 'Université de Lille', 'display_name': 'Université de Lille'},
    {'name': 'ihe-delft', 'title': 'IHE Delft', 'display_name': 'IHE Delft'},
    {'name': 'unesco-nairobi', 'title': 'UNESCO Field Office Nairobi', 'display_name': 'UNESCO Field Office Nairobi'},
]


def test_normalize_folds_accents_and_case():
    assert normalize_text('Université de Lille') == 'universite de lille'
    assert normalize_text('  IHE   Delft ') == 'ihe delft'


def test_filter_matches_title_and_slug():
    results = filter_organizations(ORGS, 'lille')
    assert [org['name'] for org in results] == ['universite-lille']

    by_slug = filter_organizations(ORGS, 'unesco-nairobi')
    assert [org['name'] for org in by_slug] == ['unesco-nairobi']


def test_filter_is_accent_insensitive():
    results = filter_organizations(ORGS, 'universite')
    assert [org['name'] for org in results] == ['universite-lille']


def test_filter_requires_all_tokens():
    results = filter_organizations(ORGS, 'ihp france')
    assert [org['name'] for org in results] == ['ihp-france']
    assert filter_organizations(ORGS, 'ihp nairobi') == []


def test_ranking_prefers_title_prefix_over_substring():
    results = filter_organizations(ORGS, 'unesco')
    names = [org['name'] for org in results]
    assert names[0] == 'unesco-ihp'
    assert 'unesco-nairobi' in names
    assert organization_search_score('unesco', ORGS[0]) > organization_search_score(
        'unesco', ORGS[4]
    )


def test_exact_match_and_similar():
    assert is_exact_organization_match(ORGS, 'Université de Lille')
    assert is_exact_organization_match(ORGS, 'universite-lille')
    assert not is_exact_organization_match(ORGS, 'Lille University')

    similar = find_similar_organizations(ORGS, 'unesco field')
    assert similar[0]['name'] == 'unesco-nairobi'
    assert find_similar_organizations(ORGS, 'x') == []


def test_slim_organization_keeps_public_fields_only():
    slim = slim_organization({
        'name': 'ihe-delft',
        'title': 'IHE Delft',
        'display_name': 'IHE Delft',
        'users': ['secret'],
        'package_count': 3,
    })
    assert slim == {
        'name': 'ihe-delft',
        'title': 'IHE Delft',
        'display_name': 'IHE Delft',
    }


def test_empty_query_does_not_match():
    assert filter_organizations(ORGS, '') == []
    assert filter_organizations(ORGS, '   ') == []
    assert organization_search_score('', ORGS[0]) is None


def test_filter_keeps_non_latin_letters():
    arabic = [
        {'name': 'ihp-egypt', 'title': 'اللجنة الوطنية المصرية', 'display_name': 'اللجنة الوطنية المصرية'},
        {'name': 'other', 'title': 'Other Org', 'display_name': 'Other Org'},
    ]
    results = filter_organizations(arabic, 'الوطنية')
    assert [org['name'] for org in results] == ['ihp-egypt']
