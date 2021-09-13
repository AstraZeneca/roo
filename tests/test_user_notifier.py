from roo.user_notifier import UserNotifier


def test_notifications_quiet(capsys):
    UserNotifier(True).message('Test notification')
    captured_quiet = capsys.readouterr()

    assert captured_quiet.out.strip() == ''


def test_notifications_verbose(capsys):
    UserNotifier(False).message('Test notification')

    captured_verbose = capsys.readouterr()
    assert captured_verbose.out.strip() == 'Test notification'


def test_indent(capsys):
    UserNotifier(False).message('Test notification', 4)

    captured_verbose = capsys.readouterr()
    assert captured_verbose.out == '    Test notification\n'
