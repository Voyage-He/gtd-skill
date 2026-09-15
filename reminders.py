"""Daily reminders delegated to Hermes' registered cron tool; no local scheduler."""
from __future__ import annotations
import hashlib
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
