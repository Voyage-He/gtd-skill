"""Daily reminders delegated to Hermes' registered cron tool; no local scheduler."""
from __future__ import annotations
import hashlib
import re
from datetime import datetime
from zoneinfo import ZoneInfo
try:
    from . import gtd_core as core
    from .gtd_response import response_prompt, scheduler_call, list_jobs, scheduled_skills
except ImportError:
    import gtd_core as core
    from gtd_response import response_prompt, scheduler_call, list_jobs, scheduled_skills


def runtime_timezone() -> str:
    from hermes_time import now
    return str(now().tzinfo)


def initialize(args: dict, dispatch, **kwargs) -> dict:
    """Fill missing routine jobs without changing existing cadence or pause state."""
    if not args.get('setup_schedules', True):
        return {'status': 'skipped', 'jobs': [], 'delivery_verified': False}
    return core._serialized(_initialize)(args, dispatch, **kwargs)


def _initialize(args, dispatch, **kwargs):
    routines = (
        ('daily_reminder', 'gtd-daily-', args.get('reminder_time', '09:00'),
         '每日提醒：调用 gtd_daily_check，结合下一步行动，简洁列出今天的重点、'
         '逾期与即将截止事项、等待跟进和待整理数量。每天发送；没有待办时简短说明。'
         '不能因为提醒触发就把现实事项标记完成。'),
        ('daily_summary', 'gtd-summary-', args.get('summary_time', '21:00'),
         '每日总结：调用 gtd_daily_check、gtd_list_actions(show_all=true)，按今天的'
         ' completed 日期核实已完成事项，必要时读取当前目录的归档，结合收集箱和相关资料，'
         '总结今日已记录的进展、未完成事项及明日重点。每天发送；无记录时如实简短说明。'
         '不能把所有历史完成项算作今天完成，也不能推断未记录的现实进展或自动完成任务。'),
    )
    results = []
    try:
        # Validate all options before the first external mutation.
        for _, _, clock, _ in routines:
            if not isinstance(clock, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', clock):
                raise core.GTDValidationError('提醒和总结时间必须为 HH:MM')
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

    suffix = hashlib.sha256(str(core.get_gtd_dir()).encode()).hexdigest()[:12]
    for key, prefix, clock, instruction in routines:
        name = prefix + suffix
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
                           'schedule': f'{minute} {hour} * * *',
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
