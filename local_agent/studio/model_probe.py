"""Model metadata admission through the fixed owned local-probe boundary."""
from local_agent.studio import probes


def identity(config, cancelled, *, timeout=8):
    try:
        result = probes.run('model', config, cancelled, timeout=timeout)
        if set(result) != {'digest', 'server_version'}:
            raise ValueError('Unsupported model metadata')
        return result
    except ValueError:
        raise ValueError('Scheduled model admission unavailable, cancelled or timed out; review and re-enable the schedule') from None
