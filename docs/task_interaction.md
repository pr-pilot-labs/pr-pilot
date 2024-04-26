```mermaid
classDiagram
    class TaskEngine {
        +Task task
        +int max_steps
        +create_unique_branch_name(basis: str): str
        +setup_working_branch(branch_name_basis: str): str
        +finalize_working_branch(branch_name: str): bool
        +generate_task_title(): void
        +run(): str
        +create_bill(): void
        +clone_github_repo(): void
    }
    class Task {
        -UUID id
        -String task_type
        -String title
        -String status
        -DateTime created
        -int installation_id
        -String github_project
        -String github_user
        -String branch
        -int issue_number
        -int pr_number
        -String user_request
        -String head
        -String base
        -int comment_id
        -String comment_url
        -int response_comment_id
        -String response_comment_url
        -String result
        -String pilot_command
        +schedule(): void
    }
    class TaskScheduler {
        +Task task
        +schedule(): void
    }
    TaskEngine --|> Task : executes
    TaskScheduler --|> Task : schedules
```

This diagram visualizes the relationship between `TaskEngine`, `Task`, and `TaskScheduler` within the PR Pilot project. `TaskEngine` is responsible for executing tasks, while `TaskScheduler` is responsible for scheduling them. `Task` acts as the central entity that is executed by the `TaskEngine` and scheduled by the `TaskScheduler`.