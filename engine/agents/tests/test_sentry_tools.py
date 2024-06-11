import pytest
from unittest.mock import patch, MagicMock
from engine.agents.integration_tools.sentry_tools import fetch_sentry_issues, create_sentry_issue, list_sentry_tools


@pytest.fixture
@patch('engine.agents.integration_tools.sentry_tools.requests.get')
def mock_fetch_sentry_issues(mock_get):
    def _mock_fetch_sentry_issues(api_key, project_slug):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'title': 'Issue 1', 'permalink': 'http://example.com/issue1', 'status': 'unresolved'},
            {'title': 'Issue 2', 'permalink': 'http://example.com/issue2', 'status': 'resolved'}
        ]
        mock_get.return_value = mock_response
        return fetch_sentry_issues(api_key, project_slug)
    return _mock_fetch_sentry_issues


@pytest.fixture
@patch('engine.agents.integration_tools.sentry_tools.requests.post')
def mock_create_sentry_issue(mock_post):
    def _mock_create_sentry_issue(api_key, project_slug, title, description):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'permalink': 'http://example.com/issue1'}
        mock_post.return_value = mock_response
        return create_sentry_issue(api_key, project_slug, title, description)
    return _mock_create_sentry_issue


def test_fetch_sentry_issues(mock_fetch_sentry_issues):
    result = mock_fetch_sentry_issues('fake_api_key', 'fake_project_slug')
    assert 'Found 2 issues for project' in result
    assert 'Title: Issue 1' in result
    assert 'Title: Issue 2' in result


def test_create_sentry_issue(mock_create_sentry_issue):
    result = mock_create_sentry_issue('fake_api_key', 'fake_project_slug', 'Issue Title', 'Issue Description')
    assert "Issue 'Issue Title' created successfully" in result


def test_list_sentry_tools():
    tools = list_sentry_tools('fake_api_key')
    assert len(tools) == 2
    assert tools[0].name == 'fetch_sentry_issues'
    assert tools[1].name == 'create_sentry_issue'
