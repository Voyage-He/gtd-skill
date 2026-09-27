"""Daily reminders delegated to Hermes' registered cron tool; no local scheduler."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
try:
    from . import gtd_core as core
    from .gtd_response import response_prompt, scheduler_call, list_jobs, scheduled_skills, belongs
except ImportError:
    import gtd_core as core
    from gtd_response import response_prompt, scheduler_call, list_jobs, scheduled_skills, belongs


def runtime_timezone() -> str:
    from hermes_time import now
    return str(now().tzinfo)


def initialize(args: dict, dispatch, **kwargs) -> dict:
    """Fill missing routine jobs without changing existing cadence or pause state."""
    if not args.get('setup_schedules', True):
        return {'status': 'skipped', 'jobs': [], 'delivery_verified': False}
    return core._serialized(_initialize_selection)(args, dispatch, **kwargs)


def _initialize_selection(args, dispatch, **kwargs):
    path = core.gtd_path('schedule-setup.json')
    saved = None
    try:
        if path.exists():
            saved = json.loads(core.read_text(path))
            if (not isinstance(saved, dict) or saved.get('version') != 1
                    or not isinstance(saved.get('names'), list)
                    or any(not isinstance(name, str) or not name for name in saved['names'])
                    or len(saved['names']) != len(set(saved['names']))):
                raise core.GTDValidationError('不支持或损坏的 schedule-setup.json；请检查原文件，未覆盖')
    except Exception as exc:
        return {'status': 'incomplete', 'jobs': [], 'error': str(exc), 'delivery_verified': False}
    if 'routines' not in args:
        # Older installations have no inventory. Inspect Hermes before asking
        # the user to configure schedules again; never recreate from disk alone.
        if saved is None and dispatch is not None:
            try:
                jobs, notes = list_jobs(dispatch, **kwargs)
                existing = [job for job in jobs if belongs(job)]
                if existing:
                    names = [job.get('name') for job in existing]
                    if len(names) != len(set(names)):
                        raise core.GTDValidationError('当前目录存在同名调度，请先核对重复任务；未自动修改')
                    return {'status': 'ready', 'jobs': existing, 'notes': notes,
                            'discovered': True, 'delivery_verified': False,
                            'next_step': '已发现当前目录的既有调度，沿用原安排；仅在用户要求时增改。'}
            except Exception as exc:
                return {'status': 'incomplete', 'jobs': [], 'error': str(exc), 'delivery_verified': False}
        if saved is not None:
            if not saved['names']:
                return {'status': 'skipped', 'jobs': [], 'remembered': True, 'delivery_verified': False}
            try:
                jobs, notes = list_jobs(dispatch, **kwargs)
                results = []
                for name in saved['names']:
                    matches = [job for job in jobs if job.get('name') == name]
                    results.append({'name': name, 'status': 'existing' if len(matches) == 1 else 'needs_attention',
                                    'jobs': matches})
                return {'status': 'ready' if all(r['status'] == 'existing' for r in results) else 'incomplete',
                        'jobs': results, 'notes': notes, 'remembered': True, 'delivery_verified': False,
                        'next_step': '沿用真实调度状态；缺失或重复任务需说明并与用户确定，不自动重建或恢复。'}
            except Exception as exc:
                return {'status': 'incomplete', 'jobs': [], 'error': str(exc), 'delivery_verified': False}
        return {'status': 'needs_preferences', 'jobs': [], 'delivery_verified': False,
                'next_step': '在对话中询问用户想要哪些提醒、总结或回顾，以及每天或每周、具体星期和时间；不要代选。'}
    if args['routines'] == []:
        core.write_text(path, json.dumps({'version': 1, 'names': []}) + '\n')
        return {'status': 'skipped', 'jobs': [], 'delivery_verified': False}
    result = _initialize(args, dispatch, **kwargs)
    # Save the complete selection even after partial external success. This is
    # an inventory, never an instruction to replay stale cadence or recipients.
    if result.get('selected_names'):
        names = list(dict.fromkeys((saved or {}).get('names', []) + result['selected_names']))
        core.write_text(path, json.dumps({'version': 1, 'names': names}, ensure_ascii=False) + '\n')
    return result


def routine_name(key):
    suffix = hashlib.sha256(str(core.get_gtd_dir()).encode()).hexdigest()[:12]
    return {'daily_reminder': 'gtd-daily-' + suffix,
            'daily_summary': 'gtd-summary-' + suffix}.get(key, 'gtd-' + suffix + '-' + key)


def _initialize(args, dispatch, **kwargs):
    routines = args['routines']
    results = []
    try:
        # Validate all options before the first external mutation.
        if not isinstance(routines, list):
            raise core.GTDValidationError('routines 必须为列表')
        keys = set()
        for routine in routines:
            key = routine.get('key', '')
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', key) or key in keys:
                raise core.GTDValidationError('每项安排需要唯一且稳定的 key')
            keys.add(key)
            clock = routine.get('time')
            if not isinstance(clock, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', clock):
                raise core.GTDValidationError('每项安排必须明确指定 HH:MM 时间')
            if routine.get('frequency') not in {'daily', 'weekly'}:
                raise core.GTDValidationError('每项安排必须明确选择 daily 或 weekly')
            if routine['frequency'] == 'weekly':
                day = routine.get('weekday')
                if type(day) is not int or not 0 <= day <= 6:
                    raise core.GTDValidationError('每周安排必须明确 weekday：0 为周日，1 为周一，至 6 为周六')
            elif 'weekday' in routine:
                raise core.GTDValidationError('每天安排不应提供 weekday')
            if not isinstance(routine.get('prompt'), str) or not routine['prompt'].strip():
                raise core.GTDValidationError('每项安排需要用户选择的提醒、总结或回顾内容 prompt')
        deliver = args.get('deliver', 'origin')
        if not isinstance(deliver, str) or deliver in {'local', 'all', ''} or ',' in deliver:
            raise core.GTDValidationError('请选择 origin 或一个明确的 platform:chat_id 目标')
        jobs, _ = list_jobs(dispatch, **kwargs)
        actual_timezone = runtime_timezone()
        timezone = args.get('timezone', actual_timezone)
        ZoneInfo(timezone)
        if timezone != actual_timezone:
            raise core.GTDValidationError(f'Hermes 当前时区为 {actual_timezone}，请先调整 Hermes 时区后重试')
    except Exception as exc:
        return {'status': 'incomplete', 'jobs': [], 'error': str(exc), 'delivery_verified': False}

    for routine in routines:
        key, clock, instruction = routine['key'], routine['time'], routine['prompt']
        # Preserve names used by the earlier daily shortcuts.
        name = routine_name(key)
        entry = {'routine': key, 'name': name}
        try:
            existing = [job for job in jobs if job.get('name') == name]
            if len(existing) > 1:
                raise core.GTDValidationError('存在多个同名常规任务，请先检查 Hermes cron 列表')
            if existing:
                entry.update(status='existing', job=existing[0])
            else:
                hour, minute = map(int, clock.split(':'))
                payload = {'action': 'create', 'name': name,
                           'schedule': f"{minute} {hour} * * {routine['weekday'] if routine['frequency'] == 'weekly' else '*'}",
                           'prompt': response_prompt(instruction), 'deliver': deliver,
                           'skills': scheduled_skills(), 'attach_to_session': True}
                scheduler_call(dispatch, payload, **kwargs)
                # A submitted job may persist even when readback fails. Retry
                # always lists by stable name before attempting another create.
                entry['status'] = 'unverified'
                jobs, _ = list_jobs(dispatch, **kwargs)
                matches = [job for job in jobs if job.get('name') == name]
                if len(matches) != 1 or any(matches[0].get(field) != payload[field]
                                          for field in ('prompt', 'skills', 'attach_to_session')):
                    raise core.GTDError('调度已提交，但无法核实任务，请检查 Hermes cron 列表')
                if deliver != 'origin' and matches[0].get('deliver') != deliver:
                    raise core.GTDError('调度已提交，但无法核实接收目标，请检查 Hermes cron 列表')
                entry.update(status='created', job=matches[0])
        except Exception as exc:
            entry.setdefault('status', 'failed')
            entry['error'] = str(exc)
        results.append(entry)
        if entry['status'] == 'unverified':
            # Stop after uncertain readback rather than creating more work.
            break
    complete = len(results) == len(routines) and all(r['status'] in {'created', 'existing'} for r in results)
    return {'status': 'ready' if complete else 'incomplete', 'timezone': actual_timezone,
            'selected_names': [routine_name(r['key']) for r in routines],
            'jobs': results, 'delivery_verified': False}


def _manage(args: dict, dispatch, **kwargs) -> dict:
    action = args['action']
    if dispatch is None:
        raise core.GTDValidationError('Hermes 调度接口不可用；需要支持 ctx.dispatch_tool 的 Hermes 版本')
    name = 'gtd-daily-' + hashlib.sha256(str(core.get_gtd_dir()).encode()).hexdigest()[:12]

    def call(payload):
        return scheduler_call(dispatch, payload, **kwargs)

    listed, notes = list_jobs(dispatch, **kwargs)
    jobs = [job for job in listed if job.get('name') == name]
    if len(jobs) > 1:
        raise core.GTDValidationError('存在多个同名每日提醒，请先在 Hermes cron 中清理重复任务')
    job = jobs[0] if jobs else None
    if action == 'status':
        return {'message': '已读取 Hermes 每日提醒状态', 'configured': bool(job), 'job': job,
                'delivery_verified': False, 'notes': notes}
    if action == 'enable':
        clock = args.get('time', '09:00')
        try:
            parsed = datetime.strptime(clock, '%H:%M')
            timezone = args.get('timezone', 'Asia/Shanghai')
            ZoneInfo(timezone)
        except (ValueError, KeyError) as exc:
            raise core.GTDValidationError('time 必须为 HH:MM，timezone 必须为有效 IANA 时区') from exc
        actual_timezone = runtime_timezone()
        if actual_timezone != timezone:
            raise core.GTDValidationError(f'Hermes 当前时区为 {actual_timezone}，请先将 Hermes 时区设置为 {timezone} 后重试')
        deliver = args.get('deliver', 'origin')
        if deliver in {'local', 'all', ''} or ',' in deliver:
            raise core.GTDValidationError('每日提醒请选择 origin 或一个明确的 platform:chat_id 目标')
        prompt = response_prompt(
            '每日审视 GTD。调用 gtd_daily_check 确认逾期、今天和明天截止任务、'
            '等待跟进、通知日期及未整理数量，并结合相关内容与定时任务执行必要调整。'
            '有实际变化、新问题或需要用户处理的事项时简洁反馈；常规无变化时可静默。'
        )
        payload = {'action': 'update' if job else 'create', 'name': name,
                   'schedule': f'{parsed.minute} {parsed.hour} * * *', 'prompt': prompt,
                   'attach_to_session': True, 'skills': scheduled_skills(job)}
        # Updating cadence must preserve the original recipient unless explicitly changed.
        if not job or 'deliver' in args:
            payload['deliver'] = deliver
        if job:
            payload['job_id'] = job['id']
        result = call(payload)
        if job:
            call({'action': 'resume', 'job_id': job['id']})
        verified, notes = list_jobs(dispatch, **kwargs)
        matches = [item for item in verified if item.get('name') == name]
        if len(matches) != 1:
            raise core.GTDError('调度已提交，但无法唯一核实任务；请检查 Hermes cron 列表后重试')
        return {'message': '每日提醒任务已配置；实际发送需要 Gateway 在线及渠道可用',
                'configured': True, 'timezone': actual_timezone, 'job': matches[0],
                'scheduler_result': result, 'delivery_verified': False, 'notes': notes}
    if not job:
        raise core.GTDValidationError('尚未创建每日提醒')
    result = call({'action': {'disable': 'pause', 'run': 'run'}[action], 'job_id': job['id']})
    return {'message': '每日提醒已暂停' if action == 'disable' else '已请求试运行，请检查 Hermes 后续执行和投递结果',
            'scheduler_result': result, 'delivery_verified': False}


def manage(args: dict, dispatch, **kwargs) -> dict:
    if args['action'] == 'run':
        return _manage(args, dispatch, **kwargs)
    return core._serialized(_manage)(args, dispatch, **kwargs)
