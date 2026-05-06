---
name: gtd
description: Use the Hermes GTD tools to capture, organize, review, and complete work in a Markdown GTD system.
---

# GTD Workflow For Hermes Agent

Use the registered `gtd_*` tools first for all GTD operations. Do not ask the user to run local scripts or shell commands for normal GTD work. Parse each tool response as JSON, check `ok`, and summarize the result in natural language. Show raw JSON only when the user asks for it.

## Tool Mapping

- Initialize GTD: call `gtd_init`.
- Capture an idea or task: call `gtd_capture` with `content`.
- View the inbox: call `gtd_inbox`.
- Process an inbox item: call `gtd_inbox_process` with `index` and one target.
- Get the next ID: call `gtd_next_number` with `prefix` as `N`, `W`, or `P`.
- List next actions: call `gtd_list_actions`, optionally with `context` or `show_all`.
- Complete an item: call `gtd_complete` with a number such as `N001`, `W001`, or `P001`.
- Archive completed work: call `gtd_archive`.
- Daily check: call `gtd_daily_check`, and optionally follow with `gtd_list_actions`.
- Weekly review: call `gtd_weekly_review`.
- Stats: call `gtd_stats`.
- Read config: call `gtd_config_get`, optionally with `key`.
- Update config: call `gtd_config_set` with `key` and `value`.

## Natural Language Examples

- "记录买牛奶": call `gtd_capture` with `{"content": "买牛奶"}`.
- "初始化 GTD": call `gtd_init`.
- "看看收集箱": call `gtd_inbox`.
- "今天做什么": call `gtd_daily_check`; call `gtd_list_actions` if the user needs a broader action list.
- "完成 N001": call `gtd_complete` with `{"number": "N001"}`.
- "查看统计": call `gtd_stats`.
- "把回顾时间改成周五晚上八点": call `gtd_config_set` for `review.day` and `review.time`, then verify with `gtd_config_get`.

## Inbox Processing

When the user asks to organize the inbox, call `gtd_inbox` first.

If the inbox returns `count: 0`, tell the user the inbox is empty and stop.

For each item, guide the GTD decision:

- Not useful: call `gtd_inbox_process` with `target: "trash"`.
- Reference material: use `target: "reference"`.
- Maybe later: use `target: "someday_maybe"`.
- Already done or less than two minutes and completed now: use `target: "done"`.
- Concrete next action: use `target: "next_actions"` and include `context` and `deadline` when available.
- Waiting for someone else: use `target: "waiting_for"` and include `delegate` and `estimated` when available.
- Multi-step outcome: use `target: "projects"` and include `project_name` and `first_action` when available.

## Error Handling

If a tool returns `ok: false`, tell the user what failed using `message`, and give a concrete correction. For example, if `gtd_complete` says the number was not found, suggest calling `gtd_list_actions` or checking whether the number is a `N`, `W`, or `P` item.

## Data Directory

The tools use `GTD_DIR` when it is set. Otherwise they default to `~/gtd`. Do not assume the directory exists; call `gtd_init` when the user is starting fresh or when file structure errors indicate the system has not been initialized.
