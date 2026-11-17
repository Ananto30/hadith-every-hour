import os
import unittest
from unittest.mock import Mock, patch

import requests

from src.facebook_page import get_page_token, post_on_facebook_page
from src.fb_token import TokenState


class FacebookPageTokenTests(unittest.TestCase):
    def test_post_strips_surrounding_whitespace_from_both_token_sources(self):
        def prepare_post(url, **kwargs):
            request = requests.Request(
                "POST", url, headers=kwargs["headers"], data=kwargs["data"]
            ).prepare()
            self.assertEqual(
                request.headers["Authorization"], "Bearer fake-token"
            )
            return Mock(content=b"{}")

        for stored in (False, True):
            for token in ("fake-token", " \tfake-token\r\n"):
                with self.subTest(stored=stored, token=repr(token)):
                    state = TokenState(page_token=token) if stored else None
                    with (
                        patch.dict(
                            os.environ,
                            {
                                "FB_PAGE_TOKEN": token,
                                "FB_PAGE_ID": "123",
                            },
                        ),
                        patch(
                            "src.facebook_page.load_state", return_value=state
                        ),
                        patch(
                            "src.facebook_page.format_post",
                            return_value="message",
                        ),
                        patch(
                            "src.facebook_page.requests.post",
                            side_effect=prepare_post,
                        ) as post,
                    ):
                        post_on_facebook_page(Mock())
                        post.assert_called_once()

    def test_rejects_embedded_whitespace_without_exposing_token(self):
        for stored in (False, True):
            for token in ("fake\nsecret", "fake\rsecret", "fake secret"):
                with self.subTest(stored=stored, token=repr(token)):
                    state = TokenState(page_token=token) if stored else None
                    with (
                        patch.dict(
                            os.environ,
                            {
                                "FB_PAGE_TOKEN": token,
                                "FB_PAGE_ID": "123",
                            },
                        ),
                        patch(
                            "src.facebook_page.load_state", return_value=state
                        ),
                        patch(
                            "src.facebook_page.format_post",
                            return_value="message",
                        ),
                        patch("src.facebook_page.requests.post") as post,
                    ):
                        with self.assertRaisesRegex(
                            ValueError, "Facebook Page token.*whitespace"
                        ) as caught:
                            post_on_facebook_page(Mock())
                        self.assertNotIn(token, str(caught.exception))
                        post.assert_not_called()

    def test_blank_token_reports_missing_token(self):
        with (
            patch.dict(os.environ, {"FB_PAGE_TOKEN": " \r\n\t"}),
            patch("src.facebook_page.load_state", return_value=None),
        ):
            with self.assertRaisesRegex(ValueError, "No Facebook Page token"):
                get_page_token()

    def test_stored_token_takes_precedence_over_secret(self):
        with (
            patch.dict(os.environ, {"FB_PAGE_TOKEN": "fallback-token"}),
            patch(
                "src.facebook_page.load_state",
                return_value=TokenState(page_token="stored-token"),
            ),
        ):
            self.assertEqual(get_page_token(), "stored-token")
