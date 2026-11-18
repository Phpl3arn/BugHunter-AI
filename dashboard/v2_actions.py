"""Strictly local synthetic research creation and human review actions."""
from integration import research_suite as rs


def exactly(params, key):
    values = params.get(key, [])
    if len(values) != 1 or not isinstance(values[0], str):
        raise ValueError('Invalid form field: ' + key)
    return values[0]


def apply(path, params):
    if path == '/research/start':
        scenario = exactly(params, 'scenario')
        if scenario not in rs.SCENARIOS:
            raise ValueError('Unsupported scenario')
        task_id = rs.create(scenario, use_ollama=False)
        return '/research/' + task_id
    if path == '/research/review':
        task_id = exactly(params, 'task_id')
        action = exactly(params, 'action')
        reviewer = exactly(params, 'reviewer')
        note = exactly(params, 'note')
        if not rs.TASK_ID.fullmatch(task_id):
            raise ValueError('Invalid research ID')
        # The review module validates legal state transitions and integrity.
        rs.transition(task_id, action, reviewer, note)
        return '/research/' + task_id
    raise ValueError('Unsupported route')
