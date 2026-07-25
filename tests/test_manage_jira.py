import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kirpr", "scripts"))
import manage_jira as mj  # noqa: E402


class FakeTransport:
    """Records calls and replays canned (status, payload) responses in order."""

    def __init__(self, responses=None):
        self.calls = []
        self._responses = list(responses or [])

    def __call__(self, method, url, headers, data):
        body = json.loads(data.decode("utf-8")) if data else None
        self.calls.append((method, url, body, headers.get("Authorization")))
        if not self._responses:
            raise AssertionError(f"unexpected call: {method} {url}")
        status, payload = self._responses.pop(0)
        raw = b"" if payload is None else json.dumps(payload).encode("utf-8")
        return status, raw

    def methods(self):
        return [c[0] for c in self.calls]


def parse(argv):
    return mj.build_parser().parse_args(argv)


class TestAuth(unittest.TestCase):
    def test_server_uses_bearer(self):
        transport = FakeTransport([(200, {})])
        client = mj.JiraClient("https://jira", "tok", transport=transport)
        self.assertFalse(client.is_cloud)
        client._request("GET", "/rest/api/2/issue/P-1")
        self.assertTrue(transport.calls[0][3].startswith("Bearer "))

    def test_cloud_uses_basic(self):
        transport = FakeTransport([(200, {})])
        client = mj.JiraClient("https://jira", "tok", email="me@example.com",
                               transport=transport)
        self.assertTrue(client.is_cloud)
        client._request("GET", "/rest/api/2/issue/P-1")
        self.assertTrue(transport.calls[0][3].startswith("Basic "))


class TestResolveDescription(unittest.TestCase):
    def test_inline_description_returned(self):
        args = parse(["update", "P-1", "--description", "текст"])
        self.assertEqual(mj.resolve_description(args), "текст")

    def test_file_description_is_read(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as f:
            f.write("из файла")
            path = f.name
        try:
            args = parse(["update", "P-1", "--description-file", path])
            self.assertEqual(mj.resolve_description(args), "из файла")
        finally:
            os.unlink(path)

    def test_both_description_flags_raise(self):
        args = parse(["update", "P-1", "--description", "a",
                      "--description-file", "/nope"])
        with self.assertRaises(mj.ArgError):
            mj.resolve_description(args)


class TestValidation(unittest.TestCase):
    def test_update_without_any_change_flag_raises(self):
        with self.assertRaises(mj.ArgError):
            mj.validate_update(parse(["update", "P-1"]))

    def test_update_with_status_only_passes(self):
        mj.validate_update(parse(["update", "P-1", "--status", "Done"]))

    def test_delete_without_confirm_raises(self):
        with self.assertRaises(mj.ArgError):
            mj.validate_delete(parse(["delete", "P-1"]))

    def test_delete_with_mismatched_confirm_raises(self):
        with self.assertRaises(mj.ArgError):
            mj.validate_delete(parse(["delete", "P-1", "--confirm", "P-2"]))

    def test_delete_with_matching_confirm_passes(self):
        mj.validate_delete(parse(["delete", "P-1", "--confirm", "P-1"]))


class TestParseLabels(unittest.TestCase):
    def test_splits_and_trims(self):
        self.assertEqual(mj.parse_labels(" a , b "), ["a", "b"])

    def test_empty_string_clears_labels(self):
        self.assertEqual(mj.parse_labels(""), [])

    def test_drops_empty_items(self):
        self.assertEqual(mj.parse_labels("a,,b,"), ["a", "b"])


class TestDescriptionDiff(unittest.TestCase):
    def test_added_line_is_marked(self):
        self.assertIn("+ b", mj.render_description_diff("a", "a\nb"))

    def test_hint_lines_are_dropped(self):
        out = mj.render_description_diff("abc", "abd")
        self.assertFalse([line for line in out if line.startswith("? ")])


class TestRenderDryRun(unittest.TestCase):
    def test_create_shows_project_type_and_summary(self):
        args = parse(["create", "--project", "PROJ", "--summary", "Заголовок",
                      "--type", "Task", "--priority", "Major"])
        out = mj.render_dry_run_create(args, "тело")
        self.assertIn("PROJ", out)
        self.assertIn("Task", out)
        self.assertIn("Заголовок", out)
        self.assertIn("Major", out)
        self.assertIn("сетевых записей не выполнено", out)

    def test_update_table_shows_before_and_after(self):
        current = {"key": "P-1", "fields": {"summary": "Старое"}}
        changes = [("status", "Open", "In Progress"),
                   ("assignee", "—", "ivanov")]
        out = mj.render_dry_run_update(current, changes, None, None)
        self.assertIn("| status | Open | In Progress |", out)
        self.assertIn("| assignee | — | ivanov |", out)

    def test_delete_preview_lists_subtasks(self):
        preview = {
            "key": "P-1",
            "fields": {
                "summary": "Заголовок",
                "reporter": {"displayName": "Иванов"},
                "comment": {"comments": [{"id": "1"}]},
                "subtasks": [{"key": "P-2"}],
                "issuelinks": [],
            },
        }
        out = mj.render_delete_preview(preview)
        self.assertIn("Заголовок", out)
        self.assertIn("Иванов", out)
        self.assertIn("P-2", out)
        self.assertIn("необратимо", out.lower())


class TestApplySteps(unittest.TestCase):
    def test_stops_at_first_failure(self):
        def boom():
            raise mj.ApiError("HTTP 400")

        applied, failed = mj.apply_steps([("шаг 1", lambda: None),
                                          ("шаг 2", boom)])
        self.assertEqual(applied, ["шаг 1"])
        self.assertIn("HTTP 400", failed)


class TestExplainHttp(unittest.TestCase):
    def test_401_mentions_token(self):
        self.assertIn("JIRA_TOKEN",
                      mj.explain_http(401, "GET", "/rest/api/2/issue/P-1", b""))

    def test_404_mentions_not_found(self):
        self.assertIn("не найден",
                      mj.explain_http(404, "GET", "/rest/api/2/issue/P-1", b""))

    def test_400_delete_mentions_delete_subtasks_flag(self):
        msg = mj.explain_http(400, "DELETE", "/rest/api/2/issue/P-1",
                              b'{"errorMessages":["The issue has subtasks"]}')
        self.assertIn("--delete-subtasks", msg)

    def test_400_post_does_not_mention_delete_subtasks_flag(self):
        msg = mj.explain_http(400, "POST", "/rest/api/2/issue", b"bad request")
        self.assertNotIn("--delete-subtasks", msg)


TRANSITIONS = {
    "transitions": [
        {"id": "11", "name": "Start", "to": {"name": "In Progress"}},
        {"id": "21", "name": "Finish", "to": {"name": "Done"}},
    ]
}


class TestFindTransition(unittest.TestCase):
    def test_matches_target_status(self):
        found = mj.find_transition(TRANSITIONS["transitions"], "In Progress")
        self.assertEqual(found["id"], "11")

    def test_match_is_case_insensitive(self):
        found = mj.find_transition(TRANSITIONS["transitions"], "in progress")
        self.assertEqual(found["id"], "11")

    def test_missing_transition_lists_available(self):
        with self.assertRaises(mj.ArgError) as ctx:
            mj.find_transition(TRANSITIONS["transitions"], "Blocked")
        message = str(ctx.exception)
        self.assertIn("In Progress", message)
        self.assertIn("Done", message)


class TestResolveAssignee(unittest.TestCase):
    def test_server_sends_name(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        self.assertEqual(mj.resolve_assignee(client, "ivanov"),
                         {"name": "ivanov"})
        self.assertEqual(transport.calls, [])

    def test_cloud_resolves_account_id(self):
        transport = FakeTransport([(200, [{"accountId": "abc",
                                           "displayName": "Иван"}])])
        client = mj.JiraClient("https://jira", "t", email="me@example.com",
                               transport=transport)
        self.assertEqual(mj.resolve_assignee(client, "ivanov"),
                         {"accountId": "abc"})

    def test_cloud_no_match_raises(self):
        transport = FakeTransport([(200, [])])
        client = mj.JiraClient("https://jira", "t", email="me@example.com",
                               transport=transport)
        with self.assertRaises(mj.ArgError):
            mj.resolve_assignee(client, "ghost")

    def test_cloud_ambiguous_match_raises_with_names(self):
        transport = FakeTransport([(200, [
            {"accountId": "a", "displayName": "Иван Иванов"},
            {"accountId": "b", "displayName": "Иван Петров"},
        ])])
        client = mj.JiraClient("https://jira", "t", email="me@example.com",
                               transport=transport)
        with self.assertRaises(mj.ArgError) as ctx:
            mj.resolve_assignee(client, "Иван")
        self.assertIn("Иван Петров", str(ctx.exception))

    def test_minus_one_unassigns(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", email="me@example.com",
                               transport=transport)
        self.assertIsNone(mj.resolve_assignee(client, "-1"))


class TestBuildFields(unittest.TestCase):
    def test_create_includes_project_type_and_parent(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["create", "--project", "PROJ", "--summary", "S",
                      "--type", "Task", "--parent", "PROJ-1"])
        fields = mj.build_fields(args, client, None, for_create=True)
        self.assertEqual(fields["project"], {"key": "PROJ"})
        self.assertEqual(fields["issuetype"], {"name": "Task"})
        self.assertEqual(fields["parent"], {"key": "PROJ-1"})
        self.assertEqual(fields["summary"], "S")

    def test_status_never_lands_in_fields(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--status", "Done"])
        self.assertEqual(mj.build_fields(args, client, None, for_create=False),
                         {})

    def test_labels_replace_whole_set(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--labels", "a, b"])
        fields = mj.build_fields(args, client, None, for_create=False)
        self.assertEqual(fields["labels"], ["a", "b"])

    def test_priority_and_duedate_are_mapped(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--priority", "Critical",
                      "--duedate", "2026-08-01"])
        fields = mj.build_fields(args, client, None, for_create=False)
        self.assertEqual(fields["priority"], {"name": "Critical"})
        self.assertEqual(fields["duedate"], "2026-08-01")

    def test_unassign_sets_none(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--assignee", "-1"])
        fields = mj.build_fields(args, client, None, for_create=False)
        self.assertIn("assignee", fields)
        self.assertIsNone(fields["assignee"])

    def test_empty_description_is_included(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--description", ""])
        fields = mj.build_fields(args, client, "", for_create=False)
        self.assertEqual(fields["description"], "")

    def test_empty_summary_is_included_not_dropped(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--summary", ""])
        fields = mj.build_fields(args, client, None, for_create=False)
        self.assertEqual(fields["summary"], "")


CURRENT_ISSUE = {
    "key": "P-1",
    "fields": {
        "summary": "Старое",
        "description": "строка",
        "status": {"name": "Open"},
        "assignee": None,
        "priority": {"name": "Major"},
        "labels": ["old"],
        "duedate": None,
    },
}


class TestCollectChanges(unittest.TestCase):
    def test_empty_summary_shows_up_as_a_change(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--summary", ""])
        changes = mj.collect_changes(CURRENT_ISSUE, args, client)
        self.assertIn(("summary", "Старое", ""), changes)


class TestRunCreate(unittest.TestCase):
    def test_dry_run_validates_project_with_a_get_only(self):
        transport = FakeTransport([(200, {"key": "PROJ", "name": "Проект"})])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["--dry-run", "create", "--project", "PROJ",
                      "--summary", "Заголовок", "--type", "Task"])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["GET"])
        self.assertTrue(transport.calls[0][1].endswith("/rest/api/2/project/PROJ"))
        self.assertIn("Заголовок", out)

    def test_dry_run_reports_unknown_project(self):
        transport = FakeTransport([(404, {"errorMessages": ["No project"]})])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["--dry-run", "create", "--project", "GHOST",
                      "--summary", "S", "--type", "Task"])
        with self.assertRaises(mj.ApiError):
            mj.run(args, client=client)

    def test_create_posts_fields_then_transition_then_comment(self):
        transport = FakeTransport([
            (201, {"key": "PROJ-42"}),
            (200, TRANSITIONS),
            (204, None),
            (201, {"id": "1"}),
        ])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["create", "--project", "PROJ", "--summary", "S",
                      "--type", "Task", "--status", "In Progress",
                      "--comment", "готово"])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertIn("PROJ-42", out)
        self.assertEqual(transport.methods(), ["POST", "GET", "POST", "POST"])
        self.assertEqual(transport.calls[0][2]["fields"]["issuetype"],
                         {"name": "Task"})
        self.assertEqual(transport.calls[2][2], {"transition": {"id": "11"}})
        self.assertEqual(transport.calls[3][2], {"body": "готово"})

    def test_create_reports_partial_failure(self):
        transport = FakeTransport([
            (201, {"key": "PROJ-43"}),
            (200, TRANSITIONS),
            (400, {"errorMessages": ["nope"]}),
        ])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["create", "--project", "PROJ", "--summary", "S",
                      "--type", "Task", "--status", "Done",
                      "--comment", "не дойдёт"])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 1)
        self.assertIn("PROJ-43", out)
        self.assertIn("Прервано", out)

    def test_empty_comment_reaches_network_on_create(self):
        transport = FakeTransport([
            (201, {"key": "PROJ-60"}),
            (201, {"id": "1"}),
        ])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["create", "--project", "PROJ", "--summary", "S",
                      "--type", "Task", "--comment", ""])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["POST", "POST"])
        self.assertEqual(transport.calls[1][2], {"body": ""})

    def test_create_with_bad_status_still_reports_created_key(self):
        transport = FakeTransport([
            (201, {"key": "PROJ-50"}),
            (200, TRANSITIONS),
        ])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["create", "--project", "PROJ", "--summary", "S",
                      "--type", "Task", "--status", "Bogus"])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 1)
        self.assertIn("PROJ-50", out)
        self.assertIn("Прервано", out)
        self.assertIn("Done", out)


class TestRunUpdate(unittest.TestCase):
    def test_dry_run_only_gets_and_shows_table(self):
        transport = FakeTransport([(200, CURRENT_ISSUE), (200, TRANSITIONS)])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["--dry-run", "update", "P-1", "--status", "In Progress",
                      "--priority", "Critical"])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(set(transport.methods()), {"GET"})
        self.assertIn("| status | Open | In Progress |", out)
        self.assertIn("| priority | Major | Critical |", out)

    def test_update_without_flags_raises_before_any_request(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        with self.assertRaises(mj.ArgError):
            mj.run(parse(["update", "P-1"]), client=client)
        self.assertEqual(transport.calls, [])

    def test_fields_go_in_one_put(self):
        transport = FakeTransport([(200, CURRENT_ISSUE), (204, None)])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--summary", "Новое",
                      "--priority", "Critical"])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["GET", "PUT"])
        self.assertEqual(transport.calls[1][2]["fields"]["summary"], "Новое")
        self.assertEqual(transport.calls[1][2]["fields"]["priority"],
                         {"name": "Critical"})

    def test_status_uses_transition_not_field_write(self):
        transport = FakeTransport([
            (200, CURRENT_ISSUE),
            (200, TRANSITIONS),
            (204, None),
        ])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--status", "Done"])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["GET", "GET", "POST"])
        self.assertEqual(transport.calls[2][2], {"transition": {"id": "21"}})

    def test_unknown_status_raises_with_available_list(self):
        transport = FakeTransport([(200, CURRENT_ISSUE), (200, TRANSITIONS)])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["--dry-run", "update", "P-1", "--status", "Blocked"])
        with self.assertRaises(mj.ArgError) as ctx:
            mj.run(args, client=client)
        self.assertIn("Done", str(ctx.exception))

    def test_bad_status_after_field_write_is_reported_not_raised(self):
        transport = FakeTransport([
            (200, CURRENT_ISSUE),
            (204, None),
            (200, TRANSITIONS),
        ])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--priority", "Critical",
                      "--status", "Bogus"])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 1)
        self.assertIn("Выполнено", out)
        self.assertIn("обновлены поля: priority", out)
        self.assertIn("Прервано", out)

    def test_description_diff_is_rendered_in_dry_run(self):
        transport = FakeTransport([(200, CURRENT_ISSUE)])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["--dry-run", "update", "P-1",
                      "--description", "строка\nещё"])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertIn("+ ещё", out)

    def test_empty_summary_reaches_network_not_dropped(self):
        transport = FakeTransport([(200, CURRENT_ISSUE), (204, None)])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--summary", ""])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["GET", "PUT"])
        self.assertEqual(transport.calls[1][2]["fields"]["summary"], "")

    def test_empty_comment_reaches_network_not_dropped(self):
        transport = FakeTransport([(200, CURRENT_ISSUE), (201, {"id": "1"})])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        args = parse(["update", "P-1", "--comment", ""])
        out, code = mj.run(args, client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["GET", "POST"])
        self.assertEqual(transport.calls[1][2], {"body": ""})


DELETE_PREVIEW = {
    "key": "P-1",
    "fields": {
        "summary": "Заголовок",
        "reporter": {"displayName": "Иванов"},
        "comment": {"comments": [{"id": "1"}, {"id": "2"}]},
        "subtasks": [{"key": "P-2"}],
        "issuelinks": [{"type": {"name": "Blocks"},
                        "outwardIssue": {"key": "P-3"}}],
    },
}


class TestRunDelete(unittest.TestCase):
    def test_dry_run_needs_no_confirm_and_only_gets(self):
        transport = FakeTransport([(200, DELETE_PREVIEW)])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        out, code = mj.run(parse(["--dry-run", "delete", "P-1"]), client=client)
        self.assertEqual(code, 0)
        self.assertEqual(set(transport.methods()), {"GET"})
        self.assertIn("P-2", out)
        self.assertIn("P-3", out)
        self.assertIn("--delete-subtasks", out)

    def test_delete_without_confirm_makes_no_request(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        with self.assertRaises(mj.ArgError):
            mj.run(parse(["delete", "P-1"]), client=client)
        self.assertEqual(transport.calls, [])

    def test_delete_with_wrong_confirm_makes_no_request(self):
        transport = FakeTransport([])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        with self.assertRaises(mj.ArgError):
            mj.run(parse(["delete", "P-1", "--confirm", "P-9"]), client=client)
        self.assertEqual(transport.calls, [])

    def test_delete_defaults_to_no_cascade(self):
        transport = FakeTransport([(204, None)])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        out, code = mj.run(parse(["delete", "P-1", "--confirm", "P-1"]),
                           client=client)
        self.assertEqual(code, 0)
        self.assertEqual(transport.methods(), ["DELETE"])
        self.assertIn("deleteSubtasks=false", transport.calls[0][1])

    def test_delete_subtasks_flag_switches_cascade_on(self):
        transport = FakeTransport([(204, None)])
        client = mj.JiraClient("https://jira", "t", transport=transport)
        out, code = mj.run(
            parse(["delete", "P-1", "--confirm", "P-1", "--delete-subtasks"]),
            client=client)
        self.assertEqual(code, 0)
        self.assertIn("deleteSubtasks=true", transport.calls[0][1])


class TestMainExitCodes(unittest.TestCase):
    def test_missing_env_returns_one(self):
        for name in ("JIRA_URL", "JIRA_TOKEN"):
            os.environ.pop(name, None)
        self.assertEqual(mj.main(["update", "P-1", "--summary", "s"]), 1)


if __name__ == "__main__":
    unittest.main()
