import requests
from tracim_backend.fixtures.users_and_groups import Base as BaseFixture
from tracim_backend.fixtures.content import Content as ContentFixture
from tracim_backend.lib.mail_notifier.daemon import MailSenderDaemon

from tracim_backend.models.contents import CONTENT_TYPES

from tracim_backend.lib.core.content import ContentApi
from tracim_backend.lib.core.user import UserApi
from tracim_backend.lib.core.workspace import WorkspaceApi
from tracim_backend.tests import MailHogTest


class TestMailNotifyDaemon(MailHogTest):
    fixtures = [BaseFixture, ContentFixture]
    config_section = 'mail_test_async'

    def test_func__create_user_with_mail_notification__ok__nominal_case(self):
        api = UserApi(
            current_user=None,
            session=self.session,
            config=self.app_config,
        )
        u = api.create_user(
            email='bob@bob',
            password='pass',
            name='bob',
            timezone='+2',
            do_save=True,
            do_notify=True,
        )
        assert u is not None
        assert u.email == "bob@bob"
        assert u.validate_password('pass')
        assert u.display_name == 'bob'
        assert u.timezone == '+2'

        # Send mail async from redis queue with daemon
        daemon = MailSenderDaemon(self.app_config, burst=True)
        daemon.run()
        # check mail received
        response = requests.get('http://127.0.0.1:8025/api/v1/messages')
        response = response.json()
        headers = response[0]['Content']['Headers']
        assert headers['From'][0] == 'Tracim Notifications <test_user_from+0@localhost>'  # nopep8
        assert headers['To'][0] == 'bob <bob@bob>'
        assert headers['Subject'][0] == '[TRACIM] Created account'

    def test_func__create_new_content_with_notification__ok__nominal_case(self):
        uapi = UserApi(
            current_user=None,
            session=self.session,
            config=self.app_config,
        )
        current_user = uapi.get_one_by_email('admin@admin.admin')
        # Create new user with notification enabled on w1 workspace
        wapi = WorkspaceApi(
            current_user=current_user,
            session=self.session,
            config=self.app_config,
        )
        workspace = wapi.get_one_by_label('Recipes')
        user = uapi.get_one_by_email('bob@fsf.local')
        wapi.enable_notifications(user, workspace)

        api = ContentApi(
            current_user=user,
            session=self.session,
            config=self.app_config,
        )
        item = api.create(
            CONTENT_TYPES.Folder.slug,
            workspace,
            None,
            'parent',
            do_save=True,
            do_notify=False,
        )
        item2 = api.create(
            CONTENT_TYPES.File.slug,
            workspace,
            item,
            'file1',
            do_save=True,
            do_notify=True,
        )
        # Send mail async from redis queue with daemon
        daemon = MailSenderDaemon(self.app_config, burst=True)
        daemon.run()
        # check mail received
        response = requests.get('http://127.0.0.1:8025/api/v1/messages')
        response = response.json()
        headers = response[0]['Content']['Headers']
        assert headers['From'][0] == '"Bob i. via Tracim" <test_user_from+3@localhost>'  # nopep8
        assert headers['To'][0] == 'Global manager <admin@admin.admin>'
        assert headers['Subject'][0] == '[TRACIM] [Recipes] file1 (Open)'
        assert headers['References'][0] == 'test_user_refs+22@localhost'
        assert headers['Reply-to'][0] == '"Bob i. & all members of Recipes" <test_user_reply+22@localhost>'  # nopep8
