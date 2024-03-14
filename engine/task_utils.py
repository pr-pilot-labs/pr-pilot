from engine.langchain.generate_task_title import generate_task_title


def generate_task_title_wrapper(task):
    if task.pr_number:
        pr = task.github_repo.get_pull(task.pr_number)
        task.title = generate_task_title(pr.body, task.user_request)
    else:
        issue = task.github_repo.get_issue(task.issue_number)
        task.title = generate_task_title(issue.body, task.user_request)
    task.save()
