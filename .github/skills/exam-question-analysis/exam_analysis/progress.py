def clamp_progress(value):
    return max(0, min(100, int(round(value))))


class ProgressTracker:
    def __init__(self, callback=None):
        self.callback = callback

    def emit(self, progress, stage, detail=''):
        if self.callback:
            self.callback(
                {
                    'progress': clamp_progress(progress),
                    'stage': stage,
                    'detail': detail,
                }
            )

    def child(self, start, end):
        span = end - start

        def child_callback(event):
            progress = start + (span * event['progress'] / 100.0)
            self.emit(progress, event['stage'], event.get('detail', ''))

        return ProgressTracker(child_callback)
