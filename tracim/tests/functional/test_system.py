# coding=utf-8
from tracim.tests import FunctionalTest

"""
Tests for /api/v2/system subpath endpoints.
"""

class TestApplicationEndpoint(FunctionalTest):
    """
    Tests for /api/v2/system/applications
    """

    def test_api__get_applications__ok_200__nominal_case(self):
        """
        Get applications list with a registered user.
        """
        self.testapp.authorization = (
            'Basic',
            (
                'admin@admin.admin',
                'admin@admin.admin'
            )
        )
        res = self.testapp.get('/api/v2/system/applications', status=200)
        res = res.json_body
        application = res[0]
        assert application['label'] == "Text Documents"
        assert application['slug'] == 'contents/htmlpage'
        assert application['fa_icon'] == 'file-text-o'
        assert application['hexcolor'] == '#3f52e3'
        assert application['is_active'] is True
        assert 'config' in application
        application = res[1]
        assert application['label'] == "Markdown Plus Documents"
        assert application['slug'] == 'contents/markdownpluspage'
        assert application['fa_icon'] == 'file-code'
        assert application['hexcolor'] == '#f12d2d'
        assert application['is_active'] is True
        assert 'config' in application
        application = res[2]
        assert application['label'] == "Files"
        assert application['slug'] == 'contents/files'
        assert application['fa_icon'] == 'paperclip'
        assert application['hexcolor'] == '#FF9900'
        assert application['is_active'] is True
        assert 'config' in application
        application = res[3]
        assert application['label'] == "Threads"
        assert application['slug'] == 'contents/threads'
        assert application['fa_icon'] == 'comments-o'
        assert application['hexcolor'] == '#ad4cf9'
        assert application['is_active'] is True
        assert 'config' in application
        application = res[4]
        assert application['label'] == "Calendar"
        assert application['slug'] == 'calendar'
        assert application['fa_icon'] == 'calendar-alt'
        assert application['hexcolor'] == '#757575'
        assert application['is_active'] is True
        assert 'config' in application

    def test_api__get_workspace__err_401__unregistered_user(self):
        """
        Get applications list with an unregistered user (bad auth)
        """
        self.testapp.authorization = (
            'Basic',
            (
                'john@doe.doe',
                'lapin'
            )
        )
        res = self.testapp.get('/api/v2/system/applications', status=401)
        assert isinstance(res.json, dict)
        assert 'code' in res.json.keys()
        assert 'message' in res.json.keys()
        assert 'details' in res.json.keys()
