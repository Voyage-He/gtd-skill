## Why

当前对 Hermes Agent 适配性的审查结论只存在于对话中，后续实现时容易遗漏或丢失上下文。需要把这些问题沉淀到仓库内的可追踪文档，作为后续 OpenSpec change、实现和验证的输入。

## What Changes

- 新增一份仓库内审查记录文件，集中保存 Hermes 适配、行为 bug、文档、测试和发布清理等待改进事项。
- 记录每个问题的优先级、影响范围、证据位置和建议后续动作。
- 不修改 Hermes 插件运行逻辑，不修复已发现问题，只建立可维护的记录入口。

## Capabilities

### New Capabilities
- `review-findings-record`: 记录项目审查发现，并为后续改进提供可追踪的问题清单。

### Modified Capabilities
- 无

## Impact

- 新增文档文件，用于记录 Hermes Agent 相关审查发现。
- 影响 OpenSpec artifacts：`openspec/changes/record-hermes-review-findings/` 下新增 proposal、spec、design、tasks。
- 不影响现有 Python 工具、插件注册入口或 GTD 用户数据目录。
