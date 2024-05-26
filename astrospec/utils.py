import inspect

_print = print

def print(*args, **kwargs):
    _print(f'[{inspect.stack()[1][3]}]', *args, **kwargs)
