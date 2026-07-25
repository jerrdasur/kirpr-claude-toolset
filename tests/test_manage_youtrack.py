import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kirpr", "scripts"))
import manage_youtrack as my  # noqa: E402


class FakeTransport:
    """Records calls and replays canned (status, payload) responses in order."""

    def __init__(self, responses=None):
        self.calls = []
        self._responses = list(responses or [])

    def __call__(self, method, url, headers, data):
        body = json.loads(data.decode("utf-8")) if data else None
        self.calls.append((method, url, body))
        if not self._responses:
            raise AssertionError(f"unexpected call: {method} {url}")
        status, payload = self._responses.pop(0)
        raw = b"" if payload is None else json.dumps(payload).encode("utf-8")
        return status, raw

    def methods(self):
        return [c[0] for c in self.calls]


def parse(argv):
    return my.build_parser().parse_args(argv)


class TestResolveDescription(unittest.TestCase):
    def test_inline_description_returned(self):
        args = parse(["update", "SAS-1", "--description", "текст"])
        self.assertEqual(my.resolve_description(args), "текст")

    def test_absent_description_is_none(self):
        args = parse(["update", "SAS-1", "--summary", "s"])
        self.assertIsNone(my.resolve_description(args))

    def test_file_description_is_read(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f:
            f.write("из файла")
            path = f.name
        try:
            args = parse(["update", "SAS-1", "--description-file", path])
            self.assertEqual(my.resolve_description(args), "из файла")
        finally:
            os.unlink(path)

    def test_both_description_flags_raise(self):
        args = parse(["update", "SAS-1", "--description", "a",
                      "--description-file", "/nope"])
        with self.assertRaises(my.ArgError):
            my.resolve_description(args)

    def test_unreadable_description_file_raises(self):
        args = parse(["update", "SAS-1", "--description-file",
                      "/definitely/not/here.md"])
        with self.assertRaises(my.ArgError):
            my.resolve_description(args)


class TestValidation(unittest.TestCase):
    def test_update_without_any_change_flag_raises(self):
        with self.assertRaises(my.ArgError):
            my.validate_update(parse(["update", "SAS-1"]))

    def test_update_with_command_only_passes(self):
        my.validate_update(parse(["update", "SAS-1", "--command", "State Open"]))

    def test_update_with_empty_description_passes(self):
        my.validate_update(parse(["update", "SAS-1", "--description", ""]))

    def test_delete_without_confirm_raises(self):
        with self.assertRaises(my.ArgError):
            my.validate_delete(parse(["delete", "SAS-1"]))

    def test_delete_with_mismatched_confirm_raises(self):
        with self.assertRaises(my.ArgError):
            my.validate_delete(parse(["delete", "SAS-1", "--confirm", "SAS-2"]))

    def test_delete_with_matching_confirm_passes(self):
        my.validate_delete(parse(["delete", "SAS-1", "--confirm", "SAS-1"]))


class TestDescriptionDiff(unittest.TestCase):
    def test_added_line_is_marked(self):
        out = my.render_description_diff("a", "a\nb")
        self.assertIn("+ b", out)

    def test_removed_line_is_marked(self):
        out = my.render_description_diff("a\nb", "a")
        self.assertIn("- b", out)

    def test_unchanged_line_is_kept_with_two_spaces(self):
        out = my.render_description_diff("a", "a\nb")
        self.assertIn("  a", out)

    def test_hint_lines_are_dropped(self):
        out = my.render_description_diff("abc", "abd")
        self.assertFalse([line for line in out if line.startswith("? ")])

    def test_empty_old_description(self):
        out = my.render_description_diff(None, "новое")
        self.assertIn("+ новое", out)


class TestRenderDryRun(unittest.TestCase):
    def test_create_lists_project_and_commands(self):
        out = my.render_dry_run_create("SAS", "Заголовок", "тело", "SAS-200",
                                       ["State Open"], "коммент")
        self.assertIn("SAS", out)
        self.assertIn("Заголовок", out)
        self.assertIn("`State Open`", out)
        self.assertIn("SAS-200", out)
        self.assertIn("сетевых записей не выполнено", out)

    def test_update_shows_summary_before_and_after(self):
        current = {"idReadable": "SAS-1", "summary": "Старое", "description": "тело"}
        out = my.render_dry_run_update(current, "Новое", None, [], None)
        self.assertIn("Старое", out)
        self.assertIn("Новое", out)

    def test_update_does_not_promise_command_result(self):
        current = {"idReadable": "SAS-1", "summary": "S", "description": ""}
        out = my.render_dry_run_update(current, None, None, ["State Open"], None)
        self.assertIn("`State Open`", out)
        self.assertNotIn("| State |", out)

    def test_delete_preview_lists_what_disappears(self):
        preview = {
            "idReadable": "SAS-1",
            "summary": "Заголовок",
            "reporter": {"name": "Иванов"},
            "comments": [{"id": "1"}, {"id": "2"}],
            "links": [{"linkType": {"name": "Subtask"}, "direction": "INWARD",
                       "issues": [{"idReadable": "SAS-2"}]}],
        }
        out = my.render_delete_preview(preview)
        self.assertIn("Заголовок", out)
        self.assertIn("Иванов", out)
        self.assertIn("2", out)
        self.assertIn("SAS-2", out)
        self.assertIn("необратимо", out.lower())


class TestApplySteps(unittest.TestCase):
    def test_all_steps_applied(self):
        applied, failed = my.apply_steps([("шаг 1", lambda: None),
                                          ("шаг 2", lambda: None)])
        self.assertEqual(applied, ["шаг 1", "шаг 2"])
        self.assertIsNone(failed)

    def test_stops_at_first_failure(self):
        def boom():
            raise my.ApiError("HTTP 400")

        applied, failed = my.apply_steps([("шаг 1", lambda: None),
                                          ("шаг 2", boom),
                                          ("шаг 3", lambda: None)])
        self.assertEqual(applied, ["шаг 1"])
        self.assertIn("шаг 2", failed)
        self.assertIn("HTTP 400", failed)


class TestExplainHttp(unittest.TestCase):
    def test_401_mentions_token(self):
        msg = my.explain_http(401, "GET", "/api/issues/SAS-1", b"denied")
        self.assertIn("YOUTRACK_TOKEN", msg)

    def test_404_mentions_not_found(self):
        msg = my.explain_http(404, "GET", "/api/issues/SAS-1", b"")
        self.assertIn("не найден", msg)

    def test_body_is_included(self):
        msg = my.explain_http(400, "POST", "/api/commands", b"bad query")
        self.assertIn("bad query", msg)


class TestClientErrors(unittest.TestCase):
    def test_error_status_raises_api_error(self):
        transport = FakeTransport([(500, {"error": "boom"})])
        client = my.YouTrackClient("https://yt.example.com", "t",
                                   transport=transport)
        with self.assertRaises(my.ApiError):
            client._request("GET", "/api/issues/SAS-1")

    def test_empty_body_returns_none(self):
        transport = FakeTransport([(200, None)])
        client = my.YouTrackClient("https://yt.example.com", "t",
                                   transport=transport)
        self.assertIsNone(client._request("DELETE", "/api/issues/SAS-1"))

    def test_trailing_slash_stripped_from_base_url(self):
        transport = FakeTransport([(200, {"ok": True})])
        client = my.YouTrackClient("https://yt.example.com/", "t",
                                   transport=transport)
        client._request("GET", "/api/issues/SAS-1")
        self.assertEqual(transport.calls[0][1],
                         "https://yt.example.com/api/issues/SAS-1")


PROJECTS = [{"id": "0-1", "shortName": "SAS"}, {"id": "0-2", "shortName": "OPS"}]


class TestResolveProject(unittest.TestCase):
    def test_project_found_by_short_name(self):
        transport = FakeTransport([(200, PROJECTS)])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        self.assertEqual(client.resolve_project_id("SAS"), "0-1")

    def test_unknown_project_raises(self):
        transport = FakeTransport([(200, PROJECTS)])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        with self.assertRaises(my.ArgError):
            client.resolve_project_id("NOPE")

    def test_project_resolved_from_parent_issue(self):
        transport = FakeTransport([(200, {"project": {"id": "0-9"}})])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        self.assertEqual(client.resolve_project_id_from_issue("SAS-200"), "0-9")


class TestRunCreate(unittest.TestCase):
    def test_dry_run_makes_only_get_requests(self):
        transport = FakeTransport([(200, PROJECTS)])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["--dry-run", "create", "--project", "SAS",
                      "--summary", "Заголовок", "--command", "State Open"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(set(transport.methods()), {"GET"})
        self.assertIn("Заголовок", out)

    def test_create_posts_issue_then_command_then_comment(self):
        transport = FakeTransport([
            (200, PROJECTS),
            (200, {"idReadable": "SAS-42", "id": "2-42"}),
            (200, {}),
            (200, {"id": "c1"}),
        ])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["create", "--project", "SAS", "--summary", "Заголовок",
                      "--description", "тело", "--command", "assignee ivanov",
                      "--comment", "готово"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertIn("SAS-42", out)
        self.assertEqual(transport.methods(), ["GET", "POST", "POST", "POST"])
        self.assertEqual(transport.calls[1][2],
                         {"project": {"id": "0-1"}, "summary": "Заголовок",
                          "description": "тело"})
        self.assertEqual(transport.calls[2][2],
                         {"query": "assignee ivanov",
                          "issues": [{"idReadable": "SAS-42"}]})
        self.assertEqual(transport.calls[3][2], {"text": "готово"})

    def test_parent_becomes_subtask_command(self):
        transport = FakeTransport([
            (200, PROJECTS),
            (200, {"idReadable": "SAS-42"}),
            (200, {}),
        ])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["create", "--project", "SAS", "--summary", "S",
                      "--parent", "SAS-200"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.calls[2][2]["query"], "subtask of SAS-200")

    def test_project_falls_back_to_parent_when_list_forbidden(self):
        transport = FakeTransport([
            (403, {"error": "no admin"}),
            (200, {"project": {"id": "0-9"}}),
            (200, {"idReadable": "SAS-43"}),
            (200, {}),
        ])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["create", "--project", "SAS", "--summary", "S",
                      "--parent", "SAS-200"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.calls[2][2]["project"], {"id": "0-9"})

    def test_project_failure_without_parent_propagates(self):
        transport = FakeTransport([(403, {"error": "no admin"})])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["create", "--project", "SAS", "--summary", "S"])
        with self.assertRaises(my.ApiError):
            my.run(args, client=client)

    def test_empty_comment_reaches_network_on_create(self):
        transport = FakeTransport([
            (200, PROJECTS),
            (200, {"idReadable": "SAS-45"}),
            (200, {"id": "c1"}),
        ])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["create", "--project", "SAS", "--summary", "S",
                      "--comment", ""])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["GET", "POST", "POST"])
        self.assertEqual(transport.calls[2][2], {"text": ""})

    def test_command_failure_reports_created_issue_and_exits_nonzero(self):
        transport = FakeTransport([
            (200, PROJECTS),
            (200, {"idReadable": "SAS-44"}),
            (400, {"error": "bad command"}),
        ])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["create", "--project", "SAS", "--summary", "S",
                      "--command", "Nonsense"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 1)
        self.assertIn("SAS-44", out)
        self.assertIn("Прервано", out)


CURRENT = {"idReadable": "SAS-1", "summary": "Старое", "description": "строка"}

DELETE_PREVIEW = {
    "idReadable": "SAS-1",
    "summary": "Заголовок",
    "reporter": {"name": "Иванов"},
    "comments": [{"id": "c1"}],
    "links": [{"linkType": {"name": "Subtask"}, "direction": "OUTWARD",
               "issues": [{"idReadable": "SAS-2"}]}],
}


class TestRunUpdate(unittest.TestCase):
    def test_dry_run_makes_only_get_requests(self):
        transport = FakeTransport([(200, CURRENT)])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["--dry-run", "update", "SAS-1", "--summary", "Новое"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(set(transport.methods()), {"GET"})
        self.assertIn("Старое", out)
        self.assertIn("Новое", out)

    def test_update_without_flags_raises_before_any_request(self):
        transport = FakeTransport([])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["update", "SAS-1"])
        with self.assertRaises(my.ArgError):
            my.run(args, client=client)
        self.assertEqual(transport.calls, [])

    def test_summary_and_description_go_in_one_post(self):
        transport = FakeTransport([(200, CURRENT), (200, {"id": "2-1"})])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["update", "SAS-1", "--summary", "Новое",
                      "--description", "новое тело"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["GET", "POST"])
        self.assertEqual(transport.calls[1][2],
                         {"summary": "Новое", "description": "новое тело"})

    def test_commands_are_sent_one_by_one(self):
        transport = FakeTransport([(200, CURRENT), (200, {}), (200, {})])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["update", "SAS-1", "--command", "State In Progress",
                      "--command", "assignee ivanov"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.calls[1][2]["query"], "State In Progress")
        self.assertEqual(transport.calls[2][2]["query"], "assignee ivanov")

    def test_partial_failure_lists_applied_and_exits_nonzero(self):
        transport = FakeTransport([
            (200, CURRENT),
            (200, {"id": "2-1"}),
            (400, {"error": "bad"}),
        ])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["update", "SAS-1", "--summary", "Новое",
                      "--command", "Nonsense", "--comment", "не дойдёт"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 1)
        self.assertIn("обновлены поля", out)
        self.assertIn("Прервано", out)
        self.assertNotIn("добавлен комментарий", out)
        self.assertEqual(len(transport.calls), 3)

    def test_empty_description_clears_field(self):
        transport = FakeTransport([(200, CURRENT), (200, {"id": "2-1"})])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["update", "SAS-1", "--description", ""])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.calls[1][2], {"description": ""})

    def test_empty_summary_reaches_network_not_dropped(self):
        transport = FakeTransport([(200, CURRENT), (200, {"id": "2-1"})])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["update", "SAS-1", "--summary", ""])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["GET", "POST"])
        self.assertEqual(transport.calls[1][2], {"summary": ""})

    def test_empty_comment_reaches_network_not_dropped(self):
        transport = FakeTransport([(200, CURRENT), (200, {"id": "c1"})])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["update", "SAS-1", "--comment", ""])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["GET", "POST"])
        self.assertEqual(transport.calls[1][2], {"text": ""})


class TestRunDelete(unittest.TestCase):
    def test_dry_run_needs_no_confirm_and_only_gets(self):
        transport = FakeTransport([(200, DELETE_PREVIEW)])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["--dry-run", "delete", "SAS-1"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(set(transport.methods()), {"GET"})
        self.assertIn("Заголовок", out)
        self.assertIn("SAS-2", out)

    def test_delete_without_confirm_makes_no_request(self):
        transport = FakeTransport([])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["delete", "SAS-1"])
        with self.assertRaises(my.ArgError):
            my.run(args, client=client)
        self.assertEqual(transport.calls, [])

    def test_delete_with_wrong_confirm_makes_no_request(self):
        transport = FakeTransport([])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["delete", "SAS-1", "--confirm", "SAS-2"])
        with self.assertRaises(my.ArgError):
            my.run(args, client=client)
        self.assertEqual(transport.calls, [])

    def test_delete_with_matching_confirm_sends_delete(self):
        transport = FakeTransport([(200, None)])
        client = my.YouTrackClient("https://yt", "t", transport=transport)
        args = parse(["delete", "SAS-1", "--confirm", "SAS-1"])
        out, code = my.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["DELETE"])
        self.assertTrue(transport.calls[0][1].endswith("/api/issues/SAS-1"))
        self.assertIn("SAS-1", out)


class TestMainExitCodes(unittest.TestCase):
    def test_arg_error_returns_one(self):
        os.environ.pop("YOUTRACK_URL", None)
        os.environ.pop("YOUTRACK_TOKEN", None)
        self.assertEqual(my.main(["update", "SAS-1", "--summary", "s"]), 1)


if __name__ == "__main__":
    unittest.main()
