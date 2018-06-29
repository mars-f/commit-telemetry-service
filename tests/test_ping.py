# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Test ping construction for sending to telemetry.mozilla.org.
"""
from unittest.mock import patch, sentinel

import pytest

pytestmark = pytest.mark.usefixtures('null_config')


@pytest.mark.parametrize(
    "changeset_landingsystem, expected",
    [
        # case: the landingsystem JSON field is present and has a value
        ({"landingsystem": "lando"}, "lando"),
        # case: the landingsystem JSON field is present and is null
        ({"landingsystem": None}, None),
        # case: the landingsystem JSON field is missing
        ({}, None),
    ],
)
def test_extract_landingsystem(changeset_landingsystem, expected):
    from committelemetry.telemetry import payload_for_changeset

    with patch('committelemetry.telemetry.determine_review_system'), patch(
        'committelemetry.telemetry.fetch_changeset'
    ) as fetch_changeset, patch('committelemetry.telemetry.diffstat_for_changeset'):
        dummy_changeset = {'pushdate': (15278721560, 0), 'parents': []}
        dummy_changeset.update(changeset_landingsystem)
        fetch_changeset.return_value = dummy_changeset

        payload = payload_for_changeset('', '')

        assert payload['landingSystem'] == expected


@pytest.mark.parametrize(
    "changeset_parents, diffstat_should_be_computed",
    [
        ({"parents": []}, True),
        ({"parents": ["123abc"]}, True),
        ({"parents": ["123abc", "456def"]}, False),
    ],
)
def test_diffstat_is_only_computed_for_non_merge_changesets(
    changeset_parents, diffstat_should_be_computed
):
    # Changesets with more than one parent are merges.  We want to skip computing
    # diffstats for them.

    from committelemetry.telemetry import payload_for_changeset

    with patch('committelemetry.telemetry.determine_review_system'), patch(
        'committelemetry.telemetry.fetch_changeset'
    ) as fetch_changeset, patch(
        'committelemetry.telemetry.diffstat_for_changeset'
    ) as diffstat_for_changeset:
        dummy_changeset = {'pushdate': (15278721560, 0)}
        dummy_changeset.update(changeset_parents)
        fetch_changeset.return_value = dummy_changeset
        diffstat_for_changeset.return_value = sentinel.diffstat

        payload = payload_for_changeset('', '')

        if diffstat_should_be_computed:
            diffstat_for_changeset.assert_called_once()
            assert payload['diffstat'] == sentinel.diffstat
        else:
            diffstat_for_changeset.assert_not_called()
            assert payload['diffstat'] is None
