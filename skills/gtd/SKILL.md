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
- Add reference material, a work memo, a link, or a file attachment: call `gtd_reference_add`.
- Search reference material: call `gtd_reference_search`.
- View a reference card: call `gtd_reference_get`.
- Link a reference to a GTD item: call `gtd_reference_link`.
- Read reference content: call `gtd_reference_read` only when the user explicitly asks to open, read, preview, summarize, or extract content.

## Natural Language Examples

- "记录买牛奶": call `gtd_capture` with `{"content": "买牛奶"}`.
- "初始化 GTD": call `gtd_init`.
- "看看收集箱": call `gtd_inbox`.
- "今天做什么": call `gtd_daily_check`; call `gtd_list_actions` if the user needs a broader action list.
- "完成 N001": call `gtd_complete` with `{"number": "N001"}`.
- "查看统计": call `gtd_stats`.
- "把回顾时间改成周五晚上八点": call `gtd_config_set` for `review.day` and `review.time`, then verify with `gtd_config_get`.
- "把客户A合同表登记成参考资料": call `gtd_reference_add` with `title`, `file_path`, `source`, optional `purpose`, and optional `tags`.
- "找一下客户A二期资料": call `gtd_reference_search`; summarize metadata matches and do not read attachments.
- "把 R20260507-001 关联到 P003": call `gtd_reference_link`.
- "打开 R20260507-001 并总结": call `gtd_reference_read`, then answer from the returned content.

## Reference Material

Use Reference Registry for work facts, project context, group-chat notes, links, and file attachments that may need later recall. Prefer `gtd_reference_add` when the user says "记一条资料", "登记这个文件", "这个以后要用", or records a project-specific memo.

Reference tools are metadata-first:

- `gtd_reference_search`, `gtd_reference_get`, and `gtd_reference_link` must not be treated as permission to read attachment contents.
- When search returns a file attachment, show the reference ID, title, source, date, filename/path, tags, and match fields.
- Call `gtd_reference_read` only after the user explicitly asks to read, open, preview, summarize, compare, or extract content from a reference.

For file attachments:

- Use `managed: "link"` by default to keep the original file in place.
- Use `managed: "copy"` only when the user wants the file copied into the GTD reference library.
- Return or mention the suggested filename when useful; it follows the reference ID, subject, purpose, source or owner, and version.

Reference memo vs Hermes memory:

- GTD reference is for work material: project facts, customer notes, group-chat decisions, file indexes, and temporary context.
- Hermes memory is for stable cross-project preferences, identity, and long-term habits.
- If the user asks to remember a work fact such as "客户A周五前确认付款条款", use `gtd_reference_add` with `kind: "memo"`.
- If the user asks to remember a durable preference such as "以后周报默认中文简洁格式", that may belong in Hermes memory instead of GTD reference.

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
