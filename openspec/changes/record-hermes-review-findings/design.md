## Context

当前项目正在从 Claude Code skill 形态扩展到 Hermes Agent 插件形态。前一次只读审查已经识别出 Hermes 注册兼容性、handler 形态、Claude 专用 prompt 复用、GTD 脚本行为 bug、日期统计偏差、仓库发布清理和 README 偏 Claude Code 等问题。

这些发现目前只存在于对话上下文中，不适合作为后续实现计划的长期依据。需要新增一份仓库文档，作为后续拆分 OpenSpec changes 和实现任务的来源。

## Goals / Non-Goals

**Goals:**
- 新增一份 Markdown 审查记录文件，集中保存 Hermes Agent 相关问题清单。
- 使用中文描述问题，保留文件路径、API 名称、命令和配置键原文。
- 每个条目提供优先级、影响、证据和后续动作，方便后续逐项转为 OpenSpec change。

**Non-Goals:**
- 不修复 Hermes 注册方式、handler 参数或工具异常处理。
- 不重构 `.claude/skills/gtd/SKILL.md` 或新增 Hermes 专用 skill。
- 不清理 `.DS_Store`、`__pycache__`、`*.pyc` 等仓库内容。
- 不新增自动化测试。

## Decisions

- 记录文件放在 `docs/hermes-review-findings.md`。`docs/` 是通用项目文档位置，避免把长期记录混在 OpenSpec change 临时目录里。
- 问题按优先级分组，优先级使用 `P0/P1/P2`，其中 `P0` 表示 Hermes 使用前应优先处理，`P1` 表示会影响可靠性或维护性，`P2` 表示发布和文档完善事项。
- 每个条目包含“问题”“影响”“证据”“建议后续动作”。这样能从记录直接派生 proposal、spec 或 tasks。
- 本次只新增记录文件，不修改运行代码。这样可以满足“避免忘记”的目的，同时把实际修复留给后续经过确认的 changes。

## Risks / Trade-offs

- [Risk] 文档可能随着代码变化过期 -> Mitigation: 每个条目写明证据路径，后续修复时同步更新或删除对应条目。
- [Risk] 问题清单过大导致后续难以执行 -> Mitigation: 按优先级拆分，后续每个高优先级问题单独创建 OpenSpec change。
- [Risk] 记录文件和 OpenSpec artifacts 内容重复 -> Mitigation: artifacts 只定义本次新增记录文件的要求，长期问题详情放在 `docs/hermes-review-findings.md`。

## Migration Plan

1. 新增 `docs/hermes-review-findings.md`。
2. 写入前次审查结论，覆盖 Hermes 兼容性、行为 bug、日期统计、文档、测试和发布清理。
3. 验证文件存在且内容包含所有高优先级问题。

## Open Questions

- 后续是否要把每个 `P0` 问题拆成独立 OpenSpec change。
- Hermes 专用 skill 的目标目录和命名是否沿用 `skills/gtd/SKILL.md`。
