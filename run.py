from prompt_toolkit import PromptSession, HTML
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.completion import Completer, Completion


def bottom_toolbar():
    return HTML('SSH Wizard - type <b><style bg="ansired">help</style></b> to list all commands')


completer = NestedCompleter.from_nested_dict({
    'connect': {
        'version': None,
        'clock': None,
        'ip': {
            'interface': {'brief'}
        }
    },
    'remove': None,
    'add': None,
    'help': None,
    'exit': None,
})

if __name__ == '__main__':

    session = PromptSession(
        message=">>> ",
        bottom_toolbar=bottom_toolbar,
        completer=completer,
        complete_while_typing=True
    )

    while True:
        text = session.prompt()
        print('You said: %s' % text)
