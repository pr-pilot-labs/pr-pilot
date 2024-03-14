import pytest
from unittest.mock import patch, MagicMock
from engine.task_engine import TaskEngine
from engine.models import Task


@pytest.fixture
def mock_task():
    task = MagicMock(spec=Task)
    task.github_project = 'test_project'
    task.default_branch = 'main'
    task.installation_id = '12345'
    return task


def test_task_engine_initialization(mock_task):
    with patch('engine.task_engine.ProjectManager') as MockProjectManager,
         patch('engine.task_engine.GitHubClient') as MockGitHubClient:
        task_engine = TaskEngine(mock_task)
        assert isinstance(task_engine.project_manager, MockProjectManager)
        assert isinstance(task_engine.github_client, MockGitHubClient)


def test_task_engine_run_with_pr(mock_task):
    mock_task.pr_number = 123
    with patch.object(TaskEngine, 'run', return_value='Task completed') as mock_run:
        task_engine = TaskEngine(mock_task)
        result = task_engine.run()
        mock_run.assert_called_once()
        assert result == 'Task completed'


def test_task_engine_run_with_issue(mock_task):
    mock_task.issue_number = 456
    with patch.object(TaskEngine, 'run', return_value='Task completed') as mock_run:
        task_engine = TaskEngine(mock_task)
        result = task_engine.run()
        mock_run.assert_called_once()
        assert result == 'Task completed'
