"""独立机械检查；语义和真实检索永不因元数据齐全而冒充通过。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from artifact_helpers import load_index
from source_index import INDEX_PATH, ROOT, clean_mdx

REVISED = {"dev021", "dev024", "dev029", "dev030", "dev031", "dev033", "dev034", "dev035", "dev036", "dev037", "dev041", "dev043"}
VITAL_REVISED = {"dev021", "dev024", "dev033", "dev034", "dev036", "dev037"}
SUBTYPE_ALIASES = {
    "numeric": "numeric_table", "numeric_config_table": "numeric_table",
    "short_query": "short", "version": "edition_single", "version_single": "edition_single",
    "single_version": "edition_single", "edition": "edition_single",
    "compare": "parallel_compare", "comparison": "parallel_compare", "scattered": "scattered_ordered",
    "missing_evidence": "no_answer_in_corpus", "no_evidence": "no_answer_in_corpus", "no_answer": "no_answer_in_corpus",
    "wrong_premise": "false_premise", "irrelevant": "out_of_domain", "unrelated": "out_of_domain",
    "version_unknown": "edition_ambiguous", "edition_unknown": "edition_ambiguous", "version_ambiguous": "edition_ambiguous",
    "missing_slot": "missing_context", "missing_information": "missing_context",
    "out_of_database": "no_answer_in_corpus", "version_unspecified": "edition_ambiguous",
}
GROUP_ALIASES = {"single_hop": "single", "multi_hop": "multi", "refuse": "refusal", "refusal_correction": "refusal", "refuse_correct": "refusal", "ambiguous": "ambiguity", "clarify": "ambiguity"}
TARGETS = [
    {"single": {"synonym": 3, "numeric_table": 2, "neighbor": 2, "short": 2, "edition_single": 1},
     "multi": {"chain": 4, "parallel_compare": 2, "scattered_ordered": 2},
     "refusal": {"no_answer_in_corpus": 2, "false_premise": 1},
     "ambiguity": {"edition_ambiguous": 1, "missing_context": 1}},
    {"single": {"synonym": 2, "numeric_table": 2, "neighbor": 2, "short": 1, "edition_single": 2},
     "multi": {"chain": 3, "parallel_compare": 4, "scattered_ordered": 2},
     "refusal": {"no_answer_in_corpus": 1, "false_premise": 1, "out_of_domain": 1},
     "ambiguity": {"edition_ambiguous": 1, "missing_context": 1}},
]
VERSION_WORDS = re.compile(r"自建|自部署|云版|云端|部署|社区版|企业版|cloud|self[ -]?host|sandbox|professional|premium|\bteam\b", re.I)
NUMBER = re.compile(r"(?<![A-Za-z_])\d[\d,]*(?:\.\d+)?")


def read_questions(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    for field in ("questions", "entries", "items", "blueprint"):
        if isinstance(data.get(field), list):
            return data[field]
    if isinstance(data.get("batches"), list):
        return [q for batch in data["batches"] for q in batch.get("questions", batch.get("entries", []))]
    raise ValueError(f"无法识别题目/蓝图列表：{path}")


def qid(q: dict) -> str:
    return q.get("id", q.get("question_id", ""))


def group(q: dict) -> str:
    value = q.get("behavior_group", q.get("group", ""))
    return GROUP_ALIASES.get(value, value)


def subtype(q: dict) -> str:
    value = q.get("behavior_subtype", q.get("subtype", ""))
    return SUBTYPE_ALIASES.get(value, value)


def number(q: dict) -> int:
    match = re.fullmatch(r"dev(\d+)", qid(q))
    return int(match[1]) if match else -1


def docs_of(q: dict) -> set[str]:
    result = set(q.get("gold_docs", [])) | set(q.get("all_equivalent_gold_docs", []))
    for values in q.get("gold_doc_groups", []):
        result.update(values)
    return result


def sources(value):
    if isinstance(value, dict):
        if "document_id" in value and "original_excerpt" in value:
            yield value
        else:
            for child in value.values():
                yield from sources(child)
    elif isinstance(value, list):
        for child in value:
            yield from sources(child)


def normalized(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", value).casefold()


def report_json(result: dict, *, expanded: bool = False) -> str:
    """默认每项检查一行，保留完整actual/target，不把原始证据全文重复展开。"""
    if expanded:
        return json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    entries = []
    for name, value in result.items():
        if name in {"checks", "semantic_review"} and isinstance(value, list):
            body = ",\n".join("    " + json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in value)
            encoded = "[\n" + body + "\n  ]" if value else "[]"
        else:
            encoded = json.dumps(value, ensure_ascii=False, indent=2).replace("\n", "\n  ")
        entries.append("  " + json.dumps(name, ensure_ascii=False) + ": " + encoded)
    return "{\n" + ",\n".join(entries) + "\n}\n"


def external_review_references(paths: list[Path]) -> list[dict]:
    """只接入外部审查证据的路径/hash，不把文件自报pass当成已完成语义验收。"""
    result = []
    for path in paths:
        content = path.read_bytes()
        result.append({"path": str(path.resolve()), "sha256": hashlib.sha256(content).hexdigest(),
                       "bytes": len(content), "status": "external_evidence_attached_not_auto_accepted"})
    return result


class Validator:
    def __init__(self, questions: list[dict], evidence: dict, index: dict, *, mode: str,
                 old_questions: list[dict] | None = None, baseline: list[dict] | None = None,
                 twin_comparisons: dict | None = None):
        self.questions = questions
        self.evidence = {qid(q): q for q in evidence.get("questions", [])}
        self.index = index
        self.docs = index["documents"]
        self.mode = mode
        self.old_questions = old_questions or []
        self.baseline = baseline or []
        self.twins = (twin_comparisons or {}).get("comparisons", {})
        self.checks = []
        self.review = []

    def add(self, key, okay, actual, target, *, scope="new46", details=None, legacy=False, pending=False):
        status = "pass" if okay else "fail"
        if legacy:
            status = "legacy_observation_pass" if okay else "legacy_observation"
        if pending:
            status = "pending_scope"
        check = {"check": key, "scope": scope, "status": status, "actual": actual, "target": target}
        if details is not None:
            check["details"] = details
        self.checks.append(check)

    def semantic(self, key, question_id=None, details=None):
        self.review.append({"check": key, "question_id": question_id, "status": "requires_independent_semantic_review", "details": details})

    def source_errors(self, source):
        errors = []
        doc_id = source.get("document_id")
        if doc_id not in self.docs:
            return [f"未知文档 {doc_id}"]
        doc = self.docs[doc_id]
        path = ROOT / doc["frozen_path"]
        current_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if current_hash != doc["source_file_sha256"]:
            errors.append("索引已过期：原文hash变化")
        if source.get("source_file_sha256") != current_hash:
            errors.append("source_file_sha256不匹配")
        start, end = source.get("raw_line_start"), source.get("raw_line_end")
        lines = doc["raw_text"].splitlines()
        original = source.get("original_excerpt", "")
        if not isinstance(start, int) or not isinstance(end, int) or not 1 <= start <= end <= len(lines):
            errors.append("原文行号无效")
        elif not original or original not in "\n".join(lines[start - 1:end]):
            errors.append("原文片段未逐字出现在声明行号")
        else:
            segment = "\n".join(lines[start - 1:end])
            first_offset = segment.find(original)
            precise_start = start + segment.count("\n", 0, first_offset)
            precise_end = start + segment.count("\n", 0, first_offset + len(original) - 1)
            if (start, end) != (precise_start, precise_end):
                errors.append("原文行号不精确（含多余行）")
        if source.get("frozen_path") != doc["frozen_path"]:
            errors.append("frozen_path不匹配")
        url = f"https://github.com/langgenius/dify-docs/blob/{self.index['corpus_commit']}/zh/{doc_id}.mdx#L{start}-L{end}"
        if source.get("source_url") != url:
            errors.append("source_url commit/path/行号不匹配")
        direct = source.get("direct_evidence", {})
        parent_ref = source.get("supporting_parent", {})
        child = next((c for c in doc["children"] if c["chunk_id"] == direct.get("chunk_id")), None)
        parent = next((p for p in doc["parents"] if p["parent_id"] == parent_ref.get("parent_id")), None)
        excerpt = direct.get("excerpt", "")
        if original and excerpt:
            raw_cleaned = clean_mdx("---\ntitle: 证据校验\n---\n" + original).markdown
            if normalized(excerpt) not in normalized(raw_cleaned):
                errors.append("direct_evidence片段与original_excerpt的生产清洗结果不对应")
        if not child or not excerpt or excerpt not in child["text"]:
            errors.append("子块不存在或未完整包含清洗片段")
        if not parent or not excerpt or excerpt not in parent["text"]:
            errors.append("父块不存在或未完整包含清洗片段")
        if child and parent and child["parent_id"] != parent["parent_id"]:
            errors.append("子块不属于声明父块")
        if child and source.get("heading_path") != child["heading_path"]:
            errors.append("heading_path不匹配")
        if parent and parent_ref.get("heading_path") != parent["heading_path"]:
            errors.append("父块heading_path不匹配")
        offset = source.get("cleaned_character_offset")
        markdown = doc["cleaned_markdown"]
        if not isinstance(offset, int) or offset < 0 or markdown[offset:offset + len(excerpt)] != excerpt:
            errors.append("清洗字符偏移不匹配")
        if isinstance(offset, int) and source.get("within_current_judge_first_12000_chars") != (offset >= 0 and offset + len(excerpt) <= 12000):
            errors.append("first_12000_chars声明不准确")
        return errors

    def twin_errors(self, record, left, right):
        errors = []
        a, b = self.docs[left], self.docs[right]
        raw_a, raw_b = a["raw_text"], b["raw_text"]
        expected = {"documents": [left, right], "raw_text_identical": raw_a == raw_b,
                    "raw_bytes_identical": a["source_file_sha256"] == b["source_file_sha256"],
                    "cleaned_text_identical": a["cleaned_markdown"] == b["cleaned_markdown"],
                    "raw_sha256": {left: a["source_file_sha256"], right: b["source_file_sha256"]}}
        for name, value in expected.items():
            if record.get(name) != value:
                errors.append(f"{name}与原文不符")
        # 校验所有非equal opcode及中间未修改区间，保证逐字比较确实覆盖全部差异。
        previous_a = previous_b = 0
        for item in record.get("character_diff", []):
            a0, a1, b0, b1 = (item.get(k) for k in ("a_start", "a_end", "b_start", "b_end"))
            if not all(isinstance(v, int) for v in (a0, a1, b0, b1)) or not (previous_a <= a0 <= a1 <= len(raw_a) and previous_b <= b0 <= b1 <= len(raw_b)):
                errors.append("character_diff偏移无效")
                break
            if raw_a[previous_a:a0] != raw_b[previous_b:b0] or item.get("a_text") != raw_a[a0:a1] or item.get("b_text") != raw_b[b0:b1]:
                errors.append("character_diff未覆盖真实逐字差异")
                break
            previous_a, previous_b = a1, b1
        if raw_a[previous_a:] != raw_b[previous_b:]:
            errors.append("character_diff缺少尾部差异")
        return errors

    def run(self):
        new = [q for q in self.questions if 45 <= number(q) <= 90]
        seventy = [q for q in self.questions if 21 <= number(q) <= 90]
        existing = [q for q in self.questions if 21 <= number(q) <= 44]
        is_snapshot = self.mode == "snapshot"
        blueprint = self.mode == "blueprint"
        ids = [qid(q) for q in self.questions]
        self.add("unique_ids", len(ids) == len(set(ids)), ids, "id唯一", scope="input")
        self.add("corpus_count", len(self.docs) == 182, len(self.docs), 182, scope="source")
        self.add("new46_count", len(new) == 46, len(new), 46, pending=is_snapshot)
        if not blueprint:
            self.add("new70_count", len(seventy) == 70, len(seventy), 70, scope="new70", pending=is_snapshot)
        self.add("old20_for_90_question_dedup", len(self.old_questions) == 20 and {number(q) for q in self.old_questions} == set(range(1, 21)),
                 len(self.old_questions), "明确提供dev001–020（不自行搜索受保护路径）", scope="input+old20", pending=is_snapshot)
        for batch_number, (lo, hi) in enumerate(((45, 67), (68, 90)), 1):
            batch = [q for q in new if lo <= number(q) <= hi]
            counts = Counter(group(q) for q in batch)
            targets = TARGETS[batch_number - 1]
            goal = {k: sum(v.values()) for k, v in targets.items()}
            self.add(f"batch{batch_number}_groups", counts == goal, dict(counts), goal, pending=is_snapshot)
            actual_subtypes = {g: dict(Counter(subtype(q) for q in batch if group(q) == g)) for g in targets}
            self.add(f"batch{batch_number}_subtypes", actual_subtypes == targets, actual_subtypes, targets, pending=is_snapshot)
            triple = [qid(q) for q in batch if len(self.evidence.get(qid(q), {}).get("subasks", q.get("subasks", []))) >= 3 and "、" in q.get("question", "")]
            bad_triple = [qid(q) for q in batch if qid(q) in triple and subtype(q) != "scattered_ordered"]
            self.add(f"batch{batch_number}_three_asks", len(triple) <= 2 and not bad_triple,
                     {"detected_ids": triple, "non_scattered": bad_triple}, "最多2且仅scattered；问数须另审", pending=is_snapshot)
        use = defaultdict(list)
        for q in new:
            for doc in docs_of(q):
                use[doc].append(qid(q))
        repeated = {k: v for k, v in use.items() if len(v) > 1}
        self.add("new46_document_reuse_including_or", not repeated, repeated, "每篇<=1", pending=is_snapshot)
        all_use = defaultdict(list)
        for q in seventy:
            for doc in docs_of(q):
                all_use[doc].append(qid(q))
        excess = {d: ids for d, ids in all_use.items() if len(ids) > 2}
        self.add("new70_document_reuse_including_or", not excess, excess, "每篇<=2", scope="new70", pending=blueprint)
        self.add("new70_document_coverage", len(all_use) >= 50, len(all_use), ">=50不同原文（含等价来源）", scope="new70", pending=is_snapshot or blueprint)
        node_docs = sorted(d for d in use if "/nodes/" in d)
        self.add("new46_nodes_documents", len(node_docs) <= 8, len(node_docs), "<=8", details=node_docs, pending=is_snapshot)
        low = {d: self.docs[d]["low_coverage_group"] for d in use if d in self.docs and self.docs[d]["low_coverage_group"]}
        self.add("new46_low_coverage_documents", len(low) >= 12, len(low), ">=12（每篇去重，含等价）", details=low, pending=is_snapshot)
        for tag, target in (("scenario_or_symptom", 14), ("condition_or_exception", 7)):
            tagged = [qid(q) for q in new if tag in q.get("form_tags", self.evidence.get(qid(q), {}).get("form_tags", []))]
            self.add("new46_form_tag_" + tag, len(tagged) >= target, len(tagged), target,
                     details={"ids": tagged, "limitation": "仅计声明；题干是否真实体现该形式需独立审查"}, pending=is_snapshot)
            self.semantic("form_classification_" + tag, details=tagged)
        chains = [q for q in new if subtype(q) == "chain"]
        chain_meta = [self.evidence.get(qid(q), {}).get("chain", q.get("chain", {})) for q in chains]
        bridge_types = sorted({c.get("bridge_type") for c in chain_meta if c.get("bridge_type")})
        course_node = sum(c.get("first_document", "").startswith("learn/") and "/nodes/" in c.get("second_document", "") for c in chain_meta)
        self.add("new46_bridge_types", len(bridge_types) >= 4, bridge_types, ">=4种声明；语义分类另审", pending=is_snapshot)
        self.add("new46_course_to_node", course_node <= 1, course_node, "<=1", pending=is_snapshot)
        if not blueprint:
            single_vital = [qid(q) for q in new if sum(n.get("importance") == "vital" for n in q.get("nuggets", [])) == 1]
            all_single_vital = [qid(q) for q in seventy if sum(n.get("importance") == "vital" for n in q.get("nuggets", [])) == 1]
            self.add("new46_one_vital_questions", len(single_vital) <= 2, single_vital, "<=2", pending=is_snapshot)
            self.add("new70_one_vital_questions", len(all_single_vital) <= 14, all_single_vital, "<=14", scope="new70")
        # 90题的机械重复仅捕获逐字归一化事实；语义重复仍须审。
        facts = defaultdict(list)
        for q in self.old_questions + self.questions:
            for n in q.get("nuggets", []):
                for d in docs_of(q):
                    facts[(d, normalized(n.get("text", "")))].append(qid(q))
        duplicates = [{"document_id": k[0], "normalized_fact": k[1], "ids": sorted(set(v))}
                      for k, v in facts.items() if k[1] and len(set(v)) > 1]
        self.add("document_fact_exact_duplicates", not duplicates, duplicates, "0（仅逐字归一化）", scope="input+old20")
        self.semantic("semantic_fact_duplicate_review", details="机械同文同事实查重不覆盖同义表述、蕴含或同一句拆分；需对全部90题逐项审")
        if self.baseline:
            current = {qid(q): q for q in existing}
            changed = [qid(q) for q in self.baseline if qid(q) not in REVISED and qid(q) in current and current[qid(q)] != q]
            self.add("unmentioned_old_questions_preserved", not changed, changed, "未点名旧题逐字段保持", scope="old24")
        for q in self.questions:
            self.question_checks(q, blueprint)
        if not blueprint:
            self.semantic("false_premise_operation_style", details="至少1道新增错误前提题为操作句式；正则不能证明其产品前提确为错误")
            self.semantic("retrieval_single_original_query", details="需独立执行每题原题一次检索，不传edition、不分解，保存前5与金标OR命中；本工具不运行或猜测召回")
        return {"mode": self.mode, "method": "独立静态机械检查，未运行RAG、未读取受保护题集",
                "input_count": len(self.questions), "new46_present": len(new),
                "checks": self.checks, "semantic_review": self.review,
                "summary": dict(Counter(c["status"] for c in self.checks)),
                "semantic_review_complete": False,
                "mechanical_checks_complete": not any(c["status"] in {"fail", "pending_scope"} for c in self.checks),
                "limitations": ["不证明独立事实、题干要求、同义官方名、bridge必要性、近邻合理性、领域相邻性、答案正确性或语义去重",
                                "form_tags、bridge_type只是可审查声明，未因字段存在宣称语义通过",
                                "未运行真实单次检索、未验证数据库、未计算正式评测分数；读取原文只限冻结182篇",
                                "静态文件不能证明蓝图实际先于新题生成；该顺序需Git提交/执行日志证据"]}

    def question_checks(self, q, blueprint):
        ident = qid(q)
        old = number(q) < 45
        ev = self.evidence.get(ident, {})
        text = q.get("question", "")
        sub = subtype(q)
        current_group = group(q)
        def check(name, okay, actual, target, **kwargs):
            self.add(name, okay, actual, target, scope=ident, legacy=old and name not in {"source_integrity", "evidence_nugget_alignment", "source_document_exists", "required_revision_vital", "dev031_route_null"}, **kwargs)
        unknown = sorted(d for d in docs_of(q) if d not in self.docs)
        check("source_document_exists", not unknown, unknown, "全部在冻结182篇")
        twin_failures = []
        checked_twins = set()
        for document in docs_of(q):
            other = document.replace("cloud/", "self-host/", 1) if document.startswith("cloud/") else document.replace("self-host/", "cloud/", 1) if document.startswith("self-host/") else ""
            if other not in self.docs:
                continue
            left, right = sorted((document, other))
            pair = f"{left} <=> {right}"
            if pair in checked_twins:
                continue
            checked_twins.add(pair)
            record = self.twins.get(pair)
            if record is None:
                twin_failures.append({"pair": pair, "errors": ["缺少逐字符比较记录"]})
            else:
                errors = self.twin_errors(record, left, right)
                if errors:
                    twin_failures.append({"pair": pair, "errors": errors})
                if record.get("cleaned_text_identical"):
                    groups = q.get("gold_doc_groups", [])
                    if not any(left in values and right in values for values in groups) or q.get("edition") is not None:
                        twin_failures.append({"pair": pair, "errors": ["清洗全文相同却未同组OR或edition非null"]})
        check("twin_character_comparison_and_or", not twin_failures, {"pairs": sorted(checked_twins), "errors": twin_failures}, "存在孪生先逐字比较；相同来源同组OR")
        if checked_twins:
            self.semantic("twin_fact_equivalence_or_edition_difference", ident, "全文不同也可能题点等价；须比较本题事实，不能据文件差异判版本题")
        if blueprint:
            if sub == "chain":
                chain = ev.get("chain", q.get("chain", {}))
                check("chain_bridge_metadata", bool(chain.get("first_document")) and bool(chain.get("second_document")) and bool(chain.get("bridge_type")), chain, "列明起点、终点和桥接类型；语义另审")
            return
        check("question_evidence_present", bool(ev), bool(ev), "evidence中有对应项")
        check("reference_answer_and_risk", bool(q.get("reference_answer")) and bool(q.get("most_likely_failure")),
              {"answer": bool(q.get("reference_answer")), "risk": bool(q.get("most_likely_failure"))}, "两项非空")
        check("guessability_null", q.get("guessable_without_docs") is None, q.get("guessable_without_docs"), None)
        vital = [n for n in q.get("nuggets", []) if n.get("importance") == "vital"]
        if not old and current_group == "single" and sub == "short":
            check("short_has_vital", len(vital) >= 1, len(vital), ">=1")
        if not old and (current_group == "multi" or current_group == "single" and sub != "short"):
            target = 3 if current_group == "multi" else 2
            check("vital_count", len(vital) >= target, len(vital), f">={target}（独立性另审）")
        if ident in VITAL_REVISED:
            check("required_revision_vital", len(vital) >= 2, len(vital), ">=2（作者点名旧题）")
        self.semantic("nugget_atomicity_independence_and_question_alignment", ident)
        conjunctions = [n.get("text") for n in vital if any(word in n.get("text", "") for word in ("并且", "以及", "同时"))]
        check("vital_conjunction_screen", not conjunctions, conjunctions, "禁用连接多个事实词；无词也不证明原子性")
        alignment = []
        nuggets = q.get("nuggets", [])
        ne = ev.get("nugget_evidence", [])
        if len(ne) != len(nuggets):
            alignment.append(f"nugget_evidence数量{len(ne)} != nuggets数量{len(nuggets)}")
        for i, n in enumerate(nuggets):
            entry = next((x for x in ne if x.get("nugget_index") == i), None)
            if not entry or entry.get("text") != n.get("text") or entry.get("importance") != n.get("importance"):
                alignment.append(f"nugget {i} index/text/importance不匹配")
            elif (not entry.get("all_of") or any(not g.get("any_of") for g in entry["all_of"])) and not (sub == "injection" and not docs_of(q) and (ev.get("acceptance") or ev.get("behavioral_acceptance"))):
                alignment.append(f"nugget {i} all_of/any_of为空")
        check("evidence_nugget_alignment", not alignment, alignment, "nugget逐项一致，all_of/any_of非空")
        source_failures = []
        leaves = list(sources(ev))
        for source in leaves:
            errors = self.source_errors(source)
            if errors:
                source_failures.append({"document_id": source.get("document_id"), "chunk": source.get("direct_evidence", {}).get("chunk_id"), "errors": errors})
        check("source_integrity", not source_failures, {"source_leaves_checked": len(leaves), "failures": source_failures}, "raw行/hash/chunk/parent/heading/offset/url逐项匹配")
        if sub == "synonym":
            whitelist = ev.get("synonym_title_overlap_whitelist", q.get("synonym_title_overlap_whitelist", []))
            allowed = {item.get("trigram") for item in whitelist if isinstance(item, dict) and len(item.get("trigram", "")) == 3 and item.get("reason")}
            overlaps = defaultdict(set)
            for d in self.docs.values():
                titles = [d["title"]] + [h["text"] for h in d["headings"]]
                for title in titles:
                    # 连续三字以原字面计；不跨标点/空格拼接，白名单逐项明示。
                    for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]+", title):
                        for i in range(len(token) - 2):
                            tri = token[i:i + 3]
                            if tri.casefold() in text.casefold() and tri not in allowed:
                                overlaps[tri].add(d["document_id"])
            check("synonym_no_title_trigram", not overlaps, {k: sorted(v) for k, v in sorted(overlaps.items())}, "与182篇title+全部小标题无连续3字重合；显式白名单除外")
            self.semantic("synonym_official_function_name_absence", ident, "标题外的官方功能名也不得泄漏")
        if sub == "numeric_table":
            literals = ev.get("answer_literals", q.get("answer_literals", []))
            answer_numbers = set(NUMBER.findall(q.get("reference_answer", "") + " " + " ".join(n.get("text", "") for n in vital)))
            candidates = set(literals) | answer_numbers
            leaks = sorted(lit for lit in candidates if lit and normalized(lit) in normalized(text))
            check("numeric_answer_literal_leak", bool(candidates) and not leaks, {"literals": sorted(candidates), "leaks": leaks}, "答案数值/字段/枚举均不出现在题干")
            conf = ev.get("numeric_confusables", q.get("numeric_confusables", []))
            conf_errors = []
            conf_keys = set()
            for i, item in enumerate(conf):
                if not isinstance(item, dict):
                    conf_errors.append(f"{i}:需literal+source")
                    continue
                literal = str(item.get("literal", item.get("value", "")))
                refs = list(sources(item))
                if not literal or not refs or not any(literal in s.get("original_excerpt", "") for s in refs):
                    conf_errors.append(f"{i}:literal未在可定位原文出现")
                conf_keys.add((literal, tuple((s.get("document_id"), s.get("raw_line_start"), s.get("raw_line_end")) for s in refs)))
            check("numeric_three_confusables", len(conf_keys) >= 3 and not conf_errors, {"count": len(conf_keys), "errors": conf_errors}, ">=3不同数字/字段/相似行，均有source")
            self.semantic("numeric_confusable_similarity", ident)
        if sub == "chain":
            chain = ev.get("chain", q.get("chain", {}))
            keywords = chain.get("second_document_answer_keywords", [])
            second = self.docs.get(chain.get("second_document"), {})
            title = second.get("title", "")
            leaks = [term for term in keywords if term and term.casefold() in text.casefold()]
            invalid = [term for term in keywords if term and term.casefold() not in (second.get("cleaned_markdown", "") + " " + title).casefold()]
            check("chain_second_keywords", len(set(keywords)) >= 5 and not leaks and not invalid and not (title and title.casefold() in text.casefold()),
                  {"keywords": keywords, "leaks": leaks, "absent_from_second": invalid, "title_leak": bool(title and title.casefold() in text.casefold())}, ">=5、在第二篇、题干不含关键词/第二篇标题")
            distractors = chain.get("generic_distractor_documents", chain.get("generic_distractor_docs", []))
            docids = [d if isinstance(d, str) else d.get("document_id") for d in distractors]
            check("chain_generic_distractors", len(set(docids)) >= 2 and all(d in self.docs for d in docids), docids, ">=2篇真实泛词干扰来源")
            self.semantic("chain_bridge_necessary_and_generic_distractors_relevant", ident, chain.get("dependency"))
        if sub == "scattered_ordered":
            parents = {s.get("supporting_parent", {}).get("parent_id") for n in ne if n.get("importance") == "vital" for s in sources(n)} - {None}
            required_parent_options = [{s.get("supporting_parent", {}).get("parent_id") for s in sources(g)} - {None}
                                       for n in ne if n.get("importance") == "vital" for g in n.get("all_of", [])]
            # any_of是OR：取所有有效来源组合中所需父块数的最小值，不能用孪生替代项膨胀计数。
            def minimum_parents(remaining):
                if not remaining:
                    return 0
                first = min(remaining, key=len)
                if not first:
                    return 0
                return 1 + min(minimum_parents([g for g in remaining if p not in g]) for p in first)
            minimum = minimum_parents(required_parent_options)
            long_docs = {d: self.docs[d]["cleaned_characters"] for d in docs_of(q) if d in self.docs}
            check("scattered_three_parents", minimum >= 3, {"all_parents": sorted(parents), "minimum_required_across_or_choices": minimum}, ">=3不同必需父块，any_of不能膨胀计数（独立事实另审）")
            check("scattered_long_cleaned_document", bool(long_docs) and max(long_docs.values()) >= 6000, long_docs, "来源清洗文>=6000字符")
        if sub == "neighbor":
            contrast = ev.get("neighbor_contrast", {})
            refs = list(sources(contrast))
            distractors = ev.get("distractor_docs", [])
            check("neighbor_contrast_sources", bool(contrast.get("difference")) and len(refs) >= 2 and bool(distractors), {"source_count": len(refs), "distractor_docs": distractors}, "差异+金标与干扰原句")
            titles = [self.docs[d]["title"] for d in docs_of(q) | set(distractors) if d in self.docs]
            named = [name for name in titles if name and name in text]
            check("neighbor_no_two_candidates", len(named) < 2, named, "题干不同时列两个候选官方名称")
            self.semantic("neighbor_difference_is_distinguishing_fact", ident)
        if sub == "no_answer_in_corpus":
            audit = ev.get("no_answer_audit", {})
            terms = audit.get("terms", audit.get("keywords", audit.get("searched_terms", audit.get("lexical_checks", []))))
            if isinstance(terms, dict):
                terms = list(terms)
            if terms and isinstance(terms[0], dict):
                terms = [t.get("term", t.get("keyword", "")) for t in terms]
            terms = list(dict.fromkeys(terms))
            hits = {term: [doc_id for doc_id, d in self.docs.items() if term.casefold() in d["raw_text"].casefold()] for term in terms if term}
            near = audit.get("nearest_documents", audit.get("nearest_docs", audit.get("nearby_docs", audit.get("closest_docs", []))))
            check("no_answer_ten_zero_terms", len(terms) >= 10 and not any(hits.values()), hits, ">=10不同近似词原文全文0命中")
            check("no_answer_three_neighbours", len(near) >= 3, near, ">=3近邻及缺依据说明；语义另审")
            self.semantic("no_answer_search_terms_meaningful_and_neighbour_explanations", ident)
        if sub == "false_premise":
            contradiction_sources = list(sources(ev.get("contradiction_evidence", ev.get("boundary_evidence", []))))
            check("false_premise_contradiction_quote", bool(contradiction_sources), len(contradiction_sources), ">=1直接矛盾原句（是否矛盾另审）")
            self.semantic("product_specific_false_premise_is_directly_contradicted", ident)
        if sub == "out_of_domain":
            self.semantic("out_of_domain_is_adjacent_domain", ident)
        if sub == "edition_ambiguous":
            check("ambiguous_edition_null_no_version_words", q.get("edition") is None and not VERSION_WORDS.search(text), {"edition": q.get("edition"), "version_words": VERSION_WORDS.findall(text)}, "edition=null，题干无版本词")
            counterpart = list(sources(ev.get("counterpart_evidence", [])))
            check("ambiguous_edition_two_sources", len({s["document_id"] for s in counterpart}) >= 2, [s["document_id"] for s in counterpart], "两版本原句+不同答案；语义另审")
            self.semantic("edition_answers_truly_differ", ident)
        if sub == "missing_context":
            interpretations = ev.get("interpretations", ev.get("ambiguity", {}).get("interpretations", []))
            check("missing_slot_two_interpretations", len(interpretations) >= 2 and all(isinstance(i, dict) and i.get("answer") for i in interpretations), interpretations, ">=2种理解与各自答案；语义另审")
            self.semantic("missing_slot_ambiguity_is_real", ident)
        if ident == "dev031":
            check("dev031_route_null", q.get("expected_route") is None, q.get("expected_route"), None)
        if ident in {"dev030", "dev029", "dev041", "dev043"}:
            self.semantic("requested_old_revision_substance", ident, "dev030版本差异未考过；dev029补文档细节；dev041第二问非重复元数据行为；dev043纯注入")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=ROOT / "docs/eval/dev70/questions.jsonl")
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--index", type=Path, default=INDEX_PATH)
    parser.add_argument("--old20", type=Path, help="仅允许明确指定的旧20开发题材料；工具绝不自行搜索 backend/eval/data")
    parser.add_argument("--baseline", type=Path, default=ROOT / ".cache/dev70-completion/original24/questions.jsonl")
    parser.add_argument("--twin-comparisons", type=Path, default=ROOT / "docs/eval/dev70/twin-comparisons.json")
    parser.add_argument("--semantic-review", type=Path, action="append", default=[], help="附加独立语义审查文件路径/hash；可重复，不自动采纳其pass字段")
    parser.add_argument("--expanded", action="store_true", help="将每项检查也展开多行；默认一项一行，保留相同JSON内容")
    parser.add_argument("--mode", choices=("snapshot", "blueprint", "completion"), default="completion")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/dev70-completion/independent-validation.json")
    args = parser.parse_args()
    for path in (args.questions, args.evidence, args.old20, args.baseline, *args.semantic_review):
        if path and ("backend/eval/data" in str(path) or re.search(r"sealed|封存", str(path), re.I)):
            parser.error("拒绝读取受保护题集或封存路径")
    ev_path = args.evidence or args.questions.parent / "evidence.json"
    evidence = json.loads(ev_path.read_text()) if ev_path.exists() else {}
    validator = Validator(read_questions(args.questions), evidence, load_index(args.index), mode=args.mode,
                          old_questions=read_questions(args.old20) if args.old20 else None,
                          baseline=read_questions(args.baseline) if args.baseline.exists() else None,
                          twin_comparisons=json.loads(args.twin_comparisons.read_text()) if args.twin_comparisons.exists() else {})
    result = validator.run()
    result["external_semantic_review_evidence"] = external_review_references(args.semantic_review)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report_json(result, expanded=args.expanded))
    print(json.dumps({"output": str(args.output), "mode": args.mode, "input_count": result["input_count"],
                      "new46_present": result["new46_present"], "summary": result["summary"],
                      "semantic_reviews_required": len(result["semantic_review"])}, ensure_ascii=False))
    raise SystemExit(1 if result["summary"].get("fail") else 0)


if __name__ == "__main__":
    main()
