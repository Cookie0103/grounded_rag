"""独立工具的失败关闭及证据完整性回归，不修改业务测试。"""

import copy
import json
import unittest

from artifact_helpers import EvidenceError, compare_twins, load_index, locate_evidence
from source_index import ROOT
from validate_completion import (
    REFERENCE_PAGE,
    VITAL_REVISED,
    Validator,
    read_questions,
    report_json,
    reuse_docs_of,
)


class EvidenceToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = load_index()
        cls.doc = "self-host/use-dify/nodes/variable-assigner"
        cls.raw = cls.index["documents"][cls.doc]["raw_text"].splitlines()[7]
        cls.validator = Validator([], {}, cls.index, mode="snapshot")

    def test_original_production_index_counts(self):
        docs = self.index["documents"]
        self.assertEqual(len(docs), 182)
        self.assertEqual(sum(len(d["parents"]) for d in docs.values()), 1252)
        self.assertEqual(sum(len(d["children"]) for d in docs.values()), 2090)

    def test_h4_exempts_only_approved_reference_or_not_primary_or_other_pages(self):
        topic = "self-host/use-dify/nodes/code"
        question = {
            "id": "dev034",
            "gold_docs": [topic],
            "gold_doc_groups": [[topic, REFERENCE_PAGE]],
        }
        self.assertEqual(reuse_docs_of(question), {topic})
        question["gold_docs"] = [REFERENCE_PAGE]
        self.assertIn(REFERENCE_PAGE, reuse_docs_of(question))
        question["id"] = "dev062"
        self.assertIn(REFERENCE_PAGE, reuse_docs_of(question))
        question["id"] = "dev059"
        question["gold_docs"] = [topic]
        question["reference_page_or_exception"] = {"document_id": REFERENCE_PAGE}
        self.assertIn(REFERENCE_PAGE, reuse_docs_of(question))
        question["id"] = "dev034"
        question["gold_doc_groups"][0].append("self-host/use-dify/build/agent")
        self.assertIn("self-host/use-dify/build/agent", reuse_docs_of(question))

    def test_link_transformation_matches_raw_and_cleaned_chunk(self):
        source = locate_evidence(self.doc, self.raw, index=self.index)
        self.assertEqual(source["raw_line_start"], 8)
        self.assertNotIn("/zh/learn/key-concepts", source["direct_evidence"]["excerpt"])
        self.assertFalse(source["database_verified"])
        self.assertEqual(self.validator.source_errors(source), [])

    def test_missing_source_fails_closed(self):
        with self.assertRaises(EvidenceError):
            locate_evidence(self.doc, "这段内容不在冻结原文中。", index=self.index)
        with self.assertRaises(EvidenceError):
            locate_evidence("not/a/frozen/document", "测试", index=self.index)

    def test_ambiguous_source_requires_line_disambiguation(self):
        with self.assertRaises(EvidenceError):
            locate_evidence(self.doc, "变量", index=self.index)

    def test_invented_cleaned_excerpt_fails_closed(self):
        with self.assertRaises(EvidenceError):
            locate_evidence(
                self.doc, self.raw, cleaned_excerpt="伪造答案。", index=self.index
            )

    def test_validator_detects_independent_source_tampering(self):
        source = locate_evidence(self.doc, self.raw, index=self.index)
        altered = copy.deepcopy(source)
        altered["source_file_sha256"] = "0" * 64
        self.assertIn("source_file_sha256不匹配", self.validator.source_errors(altered))
        altered = copy.deepcopy(source)
        altered["raw_line_start"] = altered["raw_line_end"] = 1
        self.assertIn(
            "原文片段未逐字出现在声明行号", self.validator.source_errors(altered)
        )
        altered = copy.deepcopy(source)
        altered["supporting_parent"]["parent_id"] = self.doc + "#p999"
        self.assertIn(
            "父块不存在或未完整包含清洗片段", self.validator.source_errors(altered)
        )

    def test_twin_character_diff_covers_all_changes(self):
        _pair, record = compare_twins(
            "cloud/use-dify/workspace/plugins", index=self.index
        )
        left, right = record["documents"]
        self.assertEqual(self.validator.twin_errors(record, left, right), [])
        record["character_diff"] = []
        self.assertIn(
            "character_diff缺少尾部差异",
            self.validator.twin_errors(record, left, right),
        )

    def test_known_revision_failures_are_reported(self):
        # 用可提交的审阅材料构造已知7项失败，不依赖本机未提交的original24缓存。
        base = ROOT / "docs/eval/dev70"
        questions = [
            q
            for q in read_questions(base / "questions.jsonl")
            if 21 <= int(q["id"][3:]) <= 44
        ]
        evidence = json.loads((base / "evidence.json").read_text())
        evidence["questions"] = [
            q for q in evidence["questions"] if 21 <= int(q["question_id"][3:]) <= 44
        ]
        evidence_by_id = {q["question_id"]: q for q in evidence["questions"]}
        for q in questions:
            if q["id"] in VITAL_REVISED:
                first_vital = next(
                    i for i, n in enumerate(q["nuggets"]) if n["importance"] == "vital"
                )
                for i, n in enumerate(q["nuggets"]):
                    n["importance"] = "vital" if i == first_vital else "okay"
                for entry in evidence_by_id[q["id"]]["nugget_evidence"]:
                    entry["importance"] = q["nuggets"][entry["nugget_index"]][
                        "importance"
                    ]
            if q["id"] == "dev031":
                q["expected_route"] = "REFUSE"
        twins = json.loads((ROOT / "docs/eval/dev70/twin-comparisons.json").read_text())
        report = Validator(
            questions,
            evidence,
            self.index,
            mode="snapshot",
            baseline=questions,
            twin_comparisons=twins,
        ).run()
        failures = {
            (c["scope"], c["check"]) for c in report["checks"] if c["status"] == "fail"
        }
        self.assertEqual(
            failures,
            {
                (q, "required_revision_vital")
                for q in ("dev021", "dev024", "dev033", "dev034", "dev036", "dev037")
            }
            | {("dev031", "dev031_route_null")},
        )
        self.assertFalse(report["semantic_review_complete"])
        self.assertFalse(report["mechanical_checks_complete"])
        self.assertEqual(json.loads(report_json(report)), report)
        self.assertLess(
            len(report_json(report)), len(report_json(report, expanded=True))
        )


if __name__ == "__main__":
    unittest.main()
