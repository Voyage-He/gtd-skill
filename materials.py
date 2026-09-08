"""Material-bundle state and evidence-linked organization; Hermes supplies understanding."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from . import gtd_core as core
except ImportError:
    import gtd_core as core


def _attachments(data: dict) -> list[dict]:
    return data.get('attachments') or ([data['attachment']] if data.get('attachment') else [])


def _sources(data: dict) -> dict[str, str]:
    messages = data.get('messages') or [{'text': data.get('message_text', data.get('note', ''))}]
    result = {f'message:{i}': item.get('text', '') for i, item in enumerate(messages, 1)}
    for index, analysis in data.get('attachment_analysis', {}).items():
        if analysis.get('status') in {'complete', 'partial'}:
            result[f'attachment:{index}'] = analysis.get('text', '')
    return result


def _save(data: dict) -> None:
    core.write_reference_card(data)
    core.upsert_reference_index(data)


def _check_revision(data: dict, expected_revision: int) -> None:
    if expected_revision != data.get('materials_revision', 0):
        raise core.GTDValidationError('材料或分析已更新，请重新读取上下文后整理')


def _evidence(data: dict, evidence: list[dict]) -> list[dict]:
    sources = _sources(data)
    if not evidence:
        raise core.GTDValidationError('待办需要至少一条原文依据')
    result = []
    for item in evidence:
        if not isinstance(item, dict):
            raise core.GTDValidationError('依据必须包含 source 和 quote')
        source, quote = item.get('source', ''), item.get('quote', '')
        if not isinstance(quote, str) or not quote.strip() or quote not in sources.get(source, ''):
            raise core.GTDValidationError(f'依据无法在保存的原文中找到: {source}')
        result.append({'source': source, 'quote': quote})
    return result


def _coverage(data: dict) -> dict:
    statuses = {str(i): data.get('attachment_analysis', {}).get(str(i), {}).get('status', 'pending')
                for i in range(1, len(_attachments(data)) + 1)}
    return {'status': 'complete' if all(s == 'complete' for s in statuses.values()) else 'partial',
            'attachments': statuses}


@core._serialized
def context(*, reference_id: str = '', channel: str = '', chat_id: str = '') -> dict:
    if not reference_id:
        if not channel or not chat_id:
            raise core.GTDValidationError('查询归组候选需要 channel 和 chat_id；读取材料需要 reference_id')
        candidates = []
        for path in core.reference_cards_dir().glob('R*.md'):
            data = core.read_reference_card(path.stem)
            origins = [data.get('origin', {})] + [m.get('origin', {}) for m in data.get('messages', [])]
            if not any(o.get('channel') == channel and o.get('chat_id') == chat_id for o in origins):
                continue
            candidates.append({'reference_id': path.stem, 'title': data.get('title', ''),
                               'summary': data.get('summary', '')[:320],
                               'updated_at': data.get('materials_updated_at', data.get('captured_at', '')),
                               'state': data.get('materials_state', 'saved'),
                               'attachment_count': len(_attachments(data))})
        candidates.sort(key=lambda item: (item['updated_at'], item['reference_id']), reverse=True)
        return {'candidates': candidates[:20], 'auto_merged': False}
    data = core.read_reference_card(reference_id)
    sources = _sources(data)
    files = []
    for i, attachment in enumerate(_attachments(data), 1):
        analysis = data.get('attachment_analysis', {}).get(str(i), {})
        files.append({'source': f'attachment:{i}', 'attachment_index': i,
                      'path': attachment['path'], 'name': attachment.get('original_name', attachment.get('name')),
                      'mime': attachment.get('mime', ''), 'exists': Path(attachment['path']).is_file(),
                      'analysis': {key: value for key, value in analysis.items() if key != 'text'} or {'status': 'pending'}})
    return {'reference_id': data['reference_id'], 'revision': data.get('materials_revision', 0),
            'title': data.get('title', ''), 'state': data.get('materials_state', 'saved'),
            'messages': data.get('messages', []), 'sources': sources, 'files': files,
            'coverage': _coverage(data), 'organization': data.get('organization'),
            'relations': core.relations(reference_id)['relations'],
            'existing_actions': data.get('material_actions', {})}


@core._serialized
def analyze_attachment(*, reference_id: str, attachment_index: int, expected_revision: int,
                       status: str, method: str, text: str = '', summary: str = '',
                       keywords: list[str] | None = None, locator: str = '', error: str = '') -> dict:
    data = core.read_reference_card(reference_id)
    _check_revision(data, expected_revision)
    if not 1 <= attachment_index <= len(_attachments(data)):
        raise core.GTDValidationError('附件序号不存在')
    if status not in {'complete', 'partial', 'failed'} or not method.strip():
        raise core.GTDValidationError('需要有效的分析状态和方法')
    if status == 'failed' and not error.strip():
        raise core.GTDValidationError('解析失败时必须说明原因')
    if status != 'failed' and not (text.strip() or summary.strip()):
        raise core.GTDValidationError('已分析的附件需要提取文字或摘要')
    if status == 'partial' and not locator.strip():
        raise core.GTDValidationError('部分解析需要说明覆盖页码或视频时段')
    entry = {'status': status, 'method': method, 'text': text if status != 'failed' else '',
             'summary': summary if status != 'failed' else '', 'keywords': keywords or [],
             'locator': locator, 'error': error, 'analyzed_at': core.now_str()}
    data.setdefault('attachment_analysis', {})[str(attachment_index)] = entry
    data['materials_revision'] = expected_revision + 1
    data['materials_state'] = 'needs_organization'
    data['materials_updated_at'] = core.now_str()
    _save(data)
    return {'reference_id': data['reference_id'], 'revision': data['materials_revision'], 'coverage': _coverage(data)}


def _line(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or '\n' in value or '\r' in value:
        raise core.GTDValidationError(f'{field} 必须是非空单行文字')
    return value.strip()


@core._serialized
def organize(*, reference_id: str, expected_revision: int, title: str, summary: str,
             classification: str, actions: list[dict] | None = None,
             keywords: list[str] | None = None, questions: list[str] | None = None) -> dict:
    data = core.read_reference_card(reference_id)
    _check_revision(data, expected_revision)
    title = _line(title, 'title')
    if not summary.strip():
        raise core.GTDValidationError('需要整件事的摘要')
    if classification not in {'reference', 'actions', 'project', 'needs_clarification'}:
        raise core.GTDValidationError('无效的整理类型')
    actions, questions, keywords = actions or [], questions or [], keywords or []
    if classification in {'reference', 'needs_clarification'} and actions:
        raise core.GTDValidationError('纯参考或待澄清资料不能同时创建待办')
    if classification in {'actions', 'project'} and not actions:
        raise core.GTDValidationError('行动或项目需要至少一个下一步行动')
    if classification == 'needs_clarification' and not questions:
        raise core.GTDValidationError('需要说明待澄清的问题')
    payload = {'revision': expected_revision, 'title': title, 'summary': summary,
               'classification': classification, 'actions': actions, 'keywords': keywords, 'questions': questions}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    previous = data.get('organization', {})
    if previous.get('fingerprint') == fingerprint:
        return {**previous, 'duplicate': True}
    normalized = []
    seen = set()
    stored = data.get('material_actions', {})
    for action in actions:
        key = action.get('key', '')
        if not isinstance(key, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', key) or key in seen:
            raise core.GTDValidationError('行动 key 必须是组内唯一的稳定英文标识')
        seen.add(key)
        content = _line(action.get('content', ''), 'content')
        deadline = action.get('deadline', '')
        core.validate_date(deadline)
        evidence = _evidence(data, action.get('evidence', []))
        if key in stored and (stored[key]['content'] != content or stored[key]['deadline'] != deadline):
            raise core.GTDValidationError('同一行动已有不同描述或日期，请核实并修改原任务，不能另建重复任务')
        normalized.append({'key': key, 'content': content, 'deadline': deadline, 'evidence': evidence})
    project_number = data.get('material_project', '')
    new_project = classification == 'project' and not project_number
    if classification == 'project' and not project_number:
        project_number = core.reserve_number('P')
    created = []
    for action in normalized:
        if action['key'] in stored:
            continue
        number = core.reserve_number('N')
        metadata = ['context: @任意']
        if action['deadline']:
            metadata.append('deadline: ' + action['deadline'])
        metadata.append('reference: ' + data['reference_id'])
        core._append_target('next_actions.md', f"- [ ] {number}: {action['content']} ({', '.join(metadata)})\n")
        stored[action['key']] = {**action, 'number': number}
        created.append(number)
    if classification == 'project' and not data.get('material_project'):
        first = stored[normalized[0]['key']]['number']
        core._append_target('projects.md', f"\n### {project_number}: {title}\n- **状态**: 活跃\n- **下一步**: [[next_actions.md#{first}|{first}]]\n- **资料**: {data['reference_id']}\n")
        data['material_project'] = project_number
    # Generation history is not ownership. Reorganizing must not recreate links
    # that the user explicitly removed from previously generated tasks.
    linked = created + ([project_number] if new_project else [])
    data['related_items'] = list(dict.fromkeys(data.get('related_items', []) + linked))
    data['material_actions'] = stored
    data['title'], data['summary'] = title, summary
    data['tags'] = list(dict.fromkeys(core._normalize_list(data.get('tags')) + keywords))
    data['materials_state'] = 'needs_clarification' if classification == 'needs_clarification' else 'organized'
    data['organization'] = {'reference_id': data['reference_id'], 'revision': expected_revision,
                            'fingerprint': fingerprint, 'classification': classification, 'summary': summary,
                            'questions': questions, 'action_numbers': [a['number'] for a in stored.values()],
                            'project_number': project_number, 'coverage': _coverage(data), 'created': created}
    _save(data)
    return {**data['organization'], 'duplicate': False}
