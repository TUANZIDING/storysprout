#!/usr/bin/env python3
"""Local checks for the StorySprout documentation candidate. No network calls."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from jsonschema import Draft7Validator, FormatChecker
except ImportError:
    sys.exit("缺少jsonschema；请先在独立环境安装 检查依赖v1.0.txt。")

ROOT = Path(__file__).resolve().parents[1]


class CheckError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CheckError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"JSON重复键：{key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href", "src") and value:
                self.links.append(value)
            if key == "id" and value:
                self.ids.add(value)


def without_fences(text):
    return re.sub(r"(?ms)^```[^\n]*\n.*?^```\s*$", "", text)


def anchors(text):
    clean = without_fences(text)
    parser = References()
    parser.feed(clean)
    values = set(parser.ids)
    counts = {}
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", clean):
        slug = re.sub(r"[^\w\-\s]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        values.add(slug if not count else f"{slug}-{count}")
        counts[slug] = count + 1
    return values


def check_links(root, included):
    checked = 0
    for name in sorted(included):
        if not name.endswith(".md"):
            continue
        path = root / name
        clean = without_fences(path.read_text(encoding="utf-8"))
        parser = References()
        parser.feed(clean)
        markdown = re.findall(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", clean)
        for link in markdown + parser.links:
            link = link.strip().strip("<>")
            parts = urlsplit(link)
            if parts.scheme or parts.netloc:
                require(parts.scheme in ("https", "http", "mailto"), f"{name}: 非可移植引用")
                continue  # External links are not remotely verified by this checker.
            require(not parts.path.startswith("/"), f"{name}: 绝对文件引用")
            target = (path.parent / unquote(parts.path)).resolve() if parts.path else path.resolve()
            require(target.is_relative_to(root.resolve()), f"{name}: 引用越出仓库")
            target_name = target.relative_to(root.resolve()).as_posix()
            require(target_name in included, f"{name}: 引用未列入候选：{target_name}")
            require(target.is_file(), f"{name}: 文件不存在：{target_name}")
            if parts.fragment:
                require(target.suffix == ".md", f"{name}: 不支持的文件锚点")
                require(unquote(parts.fragment) in anchors(target.read_text(encoding="utf-8")),
                        f"{name}: 锚点不存在：{parts.fragment}")
            checked += 1
    return checked


def check_svg(path):
    svg = ET.parse(path).getroot()
    require(svg.tag.endswith("}svg"), "封面不是SVG")
    require(svg.get("viewBox") == "0 0 1600 650", "封面比例发生变化，需重做视觉核对")
    for item in svg.iter():
        require(item.tag.split("}")[-1] not in ("script", "foreignObject"), "SVG含可执行内容")
        for key, value in item.attrib.items():
            require(not key.lower().startswith("on"), "SVG含事件处理器")
            if key.split("}")[-1] == "href":
                require(value.startswith("#"), "SVG含外部资源")


def index_by_id(items, label):
    result = {}
    for item in items:
        require(item["id"] not in result, f"{label}: 重复ID {item['id']}")
        result[item["id"]] = item
    return result


def check_example(data, schema):
    Draft7Validator.check_schema(schema)
    errors = list(Draft7Validator(schema, format_checker=FormatChecker()).iter_errors(data))
    require(not errors, "契约不通过：" + "; ".join(error.message for error in errors[:3]))
    sources = index_by_id(data["sources"], "来源")
    characters = index_by_id(data["characters"], "角色")
    assets = index_by_id(data["assets"], "素材")
    chapters = index_by_id(data["chapters"], "章节")
    seen = set()

    def register(items, label):
        mapping = index_by_id(items, label)
        for entity_id in mapping:
            require(entity_id not in seen, f"全局重复ID：{entity_id}")
            seen.add(entity_id)
        return mapping

    def refs(values, mapping, label):
        for value in values:
            require(value in mapping, f"{label}: 无效引用 {value}")

    def bounds(box, label):
        require(box["x"] + box["w"] <= 1 + 1e-9 and box["y"] + box["h"] <= 1 + 1e-9,
                f"{label}: 边界越出画面")

    for entities in (sources, characters, assets, chapters):
        register(list(entities.values()), "顶层实体")
    count = 0
    for chapter in data["chapters"]:
        refs(chapter["sourceRefs"], sources, "章节来源")
        utterances = register(chapter["utterances"], "正文")
        pages = register(chapter["pages"], "页面")
        panels = register([p for page in pages.values() for p in page["panels"]], "分格")
        objects = register([o for page in pages.values() for o in page["targetObjects"]], "找物")
        vocabulary = register(chapter["vocabulary"], "词卡")
        activities = register(chapter["activities"], "活动")
        require([p["role"] for p in pages.values()] ==
                ["comic", "panorama", "words", "readAlong", "activity"], "样例不是约定的五页顺序")
        refs(chapter["audioOrder"], utterances, "播放顺序")
        for unit in utterances.values():
            refs(unit["sourceRefs"], sources, "正文来源")
            require(unit["speakerId"] in characters or unit["speakerId"] == "narrator", "正文说话者无效")
            require(unit["wordCount"] == len(unit["text"].split()), f"{unit['id']}: 词数不符")
            require(unit["textHash"] == hashlib.sha256(unit["text"].encode()).hexdigest(),
                    f"{unit['id']}: 正文哈希过期")
            audio = unit["audio"]
            if audio["assetId"] is not None:
                refs([audio["assetId"]], assets, "正文音频")
                require(assets[audio["assetId"]]["kind"] == "audio", "正文指向非音频素材")
            if audio["status"] == "ready":
                require(audio["assetId"] in assets, "ready音频没有素材")
                asset = assets[audio["assetId"]]
                require(asset["status"] == "ready" and asset["durationMs"] is not None and
                        asset["sha256"] is not None and asset["storageRef"] is not None and
                        unit["textHash"] in asset["dependencyHashes"], "ready音频未验证或正文依赖已过期")
            if audio["status"] in ("notGenerated", "previewOnly"):
                require(audio["assetId"] is None, "无成品音频状态却引用素材")
            count += 1
        for page in pages.values():
            refs(page["utteranceIds"], utterances, "页面正文")
            refs(page["vocabularyIds"], vocabulary, "页面词卡")
            refs(page["activityIds"], activities, "页面活动")
            refs(page["sourcePanelIds"], panels, "页面缩图")
            if page["role"] == "readAlong":
                require(page["utteranceIds"] == chapter["audioOrder"], "听读页与播放顺序不同")
            require([p["readingOrder"] for p in page["panels"]] ==
                    list(range(1, len(page["panels"]) + 1)), "漫画阅读顺序不连续")
            for panel in page["panels"]:
                bounds(panel["bounds"], panel["id"])
                refs(panel["characterIds"], characters, "分格角色")
                refs(panel["sourceRefs"], sources, "分格来源")
                register(panel["bubbles"], "气泡")
                for bubble in panel["bubbles"]:
                    bounds(bubble["bounds"], bubble["id"])
                    refs([bubble["utteranceId"]], utterances, "气泡正文")
                    require(utterances[bubble["utteranceId"]]["wordCount"] <=
                            data["readerProfile"]["maxWordsPerBubble"], "气泡超词数")
            if page["imageAssetId"] is not None:
                refs([page["imageAssetId"]], assets, "页面图像")
            for panel in page["panels"]:
                if panel["imageAssetId"] is not None:
                    refs([panel["imageAssetId"]], assets, "分格图像")
            for obj in page["targetObjects"]:
                bounds(obj["bounds"], obj["id"])
                if obj["vocabularyId"] is not None:
                    refs([obj["vocabularyId"]], vocabulary, "找物词卡")
        for word in vocabulary.values():
            refs([word["pronunciationUtteranceId"], word["exampleUtteranceId"]], utterances, "词卡正文")
            require(utterances[word["pronunciationUtteranceId"]]["text"] == word["displayText"],
                    "词卡与读词单元不符")
            image = word["imageSource"]
            mapping = {"panel": panels, "object": objects, "asset": assets, "none": {}}[image["kind"]]
            if image["kind"] == "none":
                require(image["id"] is None, "无图词卡仍有图像ID")
            else:
                refs([image["id"]], mapping, "词卡图像")
        evidence_maps = {"source": sources, "utterance": utterances, "object": objects, "vocabulary": vocabulary}
        for activity in activities.values():
            refs(activity["utteranceIds"], utterances, "活动正文")
            refs(activity["targetObjectIds"], objects, "活动物件")
            refs(activity["roleIds"], characters, "表演角色")
            for evidence in activity["evidenceRefs"]:
                refs([evidence["id"]], evidence_maps[evidence["kind"]], "活动证据")
            if activity["kind"] == "fillBubble":
                require(len(activity["utteranceIds"]) == 1, "填空应有唯一原句")
                tokens = utterances[activity["utteranceIds"][0]]["text"].split()
                positions = activity["blankTokenIndices"]
                require(positions and all(i < len(tokens) for i in positions), "填空位置越界")
                answer = " ".join(tokens[i].strip(".,!?:;") for i in positions)
                require(answer == activity["answer"], "填空答案与正文不同")
            if activity["answer"] is not None:
                require(activity["answerVisibility"] == "parentOnly", "答案没有隔离到家长部分")
            if activity["kind"] == "findObject":
                require(activity["answer"] in activity["targetObjectIds"], "找物答案未对应目标")
    for character in characters.values():
        refs(character["referenceAssetIds"], assets, "角色参考图")
    if data["contentStatus"] == "storyboardOnly":
        require(not any(a["status"] == "ready" for a in assets.values()), "分镜状态却声称有成品素材")
        require(not any(u["audio"]["status"] == "ready" for c in data["chapters"] for u in c["utterances"]),
                "分镜状态却声称音频已完成")
    return count


def section(text, start, end):
    require(start in text and end in text, f"正文缺少章节：{start}")
    return text.split(start, 1)[1].split(end, 1)[0]


def table_rows(text):
    return [list(map(str.strip, line.strip().strip("|").split("|")))
            for line in text.splitlines() if line.startswith("| ") and not line.startswith("| ---")]


def check_chapter(text):
    canonical = {}
    block = section(text, "## 4. 唯一正文", "## 5. 词汇")
    for row in table_rows(block):
        if not re.fullmatch(r"ch01-[sw]\d{2}", row[0]):
            continue
        require(len(row) == 7, "正文表列数错误")
        uid, speaker, english, chinese, count, pause, _ = row
        require(uid not in canonical, f"重复正文ID：{uid}")
        require(count.isdigit() and int(count) == len(english.split()), f"{uid}: 词数错误")
        require(int(count) <= 8 and pause == "3秒", f"{uid}: 词数或停顿不符")
        canonical[uid] = (speaker, english, chinese, int(count))
    expected = {f"ch01-s{i:02}" for i in range(1, 16)} | {f"ch01-w{i:02}" for i in range(1, 4)}
    require(set(canonical) == expected, "第一章应登记15句与3词，共18个单元")
    refs = set(re.findall(r"\bch01-[sw]\d{2}\b", text))
    require(refs <= set(canonical), "第一章有未登记的正文引用")
    previews = re.findall(r"〔(ch01-[sw]\d{2})〕\s*([^〔\n|→；]+?)（([^）]*)）", text)
    require(len(previews) == 16, "第一章应有16处完整审阅预览")
    for uid, english, chinese in previews:
        require((english.strip(), chinese) == canonical[uid][1:3], f"{uid}: 审阅预览与唯一正文不同")
    order_rows = table_rows(section(text, "### 第4页：", "### 第5页："))[1:]
    require([row[0] for row in order_rows] == list(map(str, range(1, 15))), "听读顺序不连续")
    order = [row[1] for row in order_rows]
    require(order == [f"ch01-s{i:02}" for i in range(1, 12)] + ["ch01-s03", "ch01-s12", "ch01-s13"],
            "故事听读顺序与漫画不同")
    require(sum(canonical[uid][3] for uid in order) == 37, "听读词次记录需更新")
    for row in order_rows:
        require(row[2] == canonical[row[1]][0], "听读说话者不同")
    comic_rows = table_rows(section(text, "### 第1页：", "### 第2页："))[1:]
    require([row[0] for row in comic_rows] == [f"ch01-p1-g{i}" for i in range(1, 7)], "漫画不是六格顺序")
    bubble_max = 0
    for row in comic_rows:
        for bubble in re.split(r"气泡\d：", row[3])[1:]:
            ids = re.findall(r"〔(ch01-s\d{2})〕", bubble)
            words = sum(canonical[uid][3] for uid in ids)
            require(words <= 8, "组合气泡超过8词")
            stated = re.search(r"(?:合计)?(\d+)词", bubble)
            require(stated and int(stated[1]) == words, "气泡词数标记错误")
            speaker = bubble.split("；", 1)[0]
            require(all(canonical[uid][0].split("（")[0] in speaker for uid in ids), "气泡说话者错误")
            bubble_max = max(bubble_max, words)
    answers = table_rows(section(text, "### 填气泡答案", "角色扮演没有"))[1:]
    activity_rows = table_rows(section(text, "### 第5页：", "**活动二："))[1:]
    require(len(answers) == len(activity_rows) == 3, "需要三个填空及独立家长答案")
    for activity, answer in zip(activity_rows, answers):
        require(activity[0] == answer[0] and activity[3] == answer[2], "活动答案引用不符")
        original = canonical[activity[3]][1]
        require(original.count(answer[1]) == 1, "答案不能唯一对应原句")
        masked = original.replace(answer[1], "________")
        require(activity[2].endswith(masked), "儿童填空与原句不同")
    targets = [row[0] for row in table_rows(section(text, "### 找物答案", "### 填气泡答案"))[1:]]
    require(targets == ["ch01-rock", "ch01-door", "ch01-suitcase"], "找物答案目标不符")
    for value in ("原书待核验", "实际新词数量待确认", "现有PDF未被修改", "尚未录音"):
        require(value in text, f"缺少边界说明：{value}")
    return len(canonical), len(order), bubble_max


def check_repository(root, check_index=False):
    manifest = read_json(root / "提交范围v1.1.json")
    names = manifest["include"]
    require(len(set(names)) == len(names), "提交范围含重复文件")
    included = set(names)
    require(not included.intersection(manifest["localOnly"]), "私人文件进入候选")
    for name in names:
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts, "提交范围路径无效")
        require(relative.name in ("README.md", ".gitignore") or
                ("_" not in relative.name and re.fullmatch(r".+v\d+\.\d+(?:\.\d+)?\.[A-Za-z0-9]+", relative.name)),
                f"文件命名不符：{name}")
        path = root / name
        require(path.is_file() and not path.is_symlink(), f"缺少候选文件或出现符号链接：{name}")
        text = path.read_text(encoding="utf-8")
        require(not re.search(r"/(?:Users|Volumes)/", text), f"{name}: 本机绝对路径")
        require(not re.search(r"\bgh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{32,}", text),
                f"{name}: 可能含凭据")
        require(not re.search(r"\{\{[^}\n]+\}\}", text), f"{name}: 未替换模板字段")
    require((root / manifest["entryPoint"]).read_bytes() ==
            (root / manifest["homepageSnapshot"]).read_bytes(), "首页与版本快照不一致")
    for entry in (manifest["entryPoint"], manifest["englishEntry"]):
        require({"use-cases", "showcase", "quick-start", "workflow", "capabilities", "contribute"} <=
                anchors((root / entry).read_text(encoding="utf-8")), "首页导航不完整")
    links = check_links(root, included)
    check_svg(root / "assets/故事芽封面v1.0.svg")
    units = check_example(read_json(root / "examples/原创故事样例v1.0.json"),
                          read_json(root / "contracts/项目数据契约v1.0.json"))
    chapter = check_chapter((root / "docs/第一章内容设计v1.1.md").read_text(encoding="utf-8"))
    ignore_rules = set((root / ".gitignore").read_text(encoding="utf-8").splitlines())
    require(all("/" + name in ignore_rules for name in manifest["localOnly"]), "本地方案缺少忽略规则")
    if (root / ".git").exists():
        ignored = subprocess.run(["git", "check-ignore", "--no-index", "-z", "--stdin"],
                                 input="\0".join(manifest["localOnly"]).encode() + b"\0",
                                 cwd=root, capture_output=True, check=False)
        require(ignored.returncode == 0 and
                {n for n in ignored.stdout.decode().split("\0") if n} == set(manifest["localOnly"]),
                "原始本地方案未被忽略")
    if check_index:
        require((root / ".git").exists(), "Git索引检查需要本项目的Git仓库")
        files = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
        tracked = {n for n in files.stdout.decode().split("\0") if n}
        require(tracked == included, f"Git索引范围不同；缺少={sorted(included-tracked)}，额外={sorted(tracked-included)}")
        unstaged = subprocess.run(["git", "diff", "--exit-code", "--name-only", "--", *names],
                                  cwd=root, capture_output=True, check=False)
        require(unstaged.returncode == 0, "暂存内容与已检查工作文件不同，请重新暂存后检查")
        subprocess.run(["git", "diff", "--cached", "--check"], cwd=root, check=True)
    return {"candidateFiles": len(names), "localReferences": links, "exampleTextUnits": units,
            "chapterTextUnits": chapter[0], "storyReadOccurrences": chapter[1],
            "maxCombinedBubbleWords": chapter[2], "gitIndexChecked": check_index}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-index", action="store_true", help="also match the Git index against the manifest")
    args = parser.parse_args()
    try:
        result = check_repository(ROOT, args.check_index)
    except (CheckError, OSError, ValueError, subprocess.CalledProcessError, ET.ParseError) as error:
        print(f"检查未通过：{error}", file=sys.stderr)
        return 1
    print("检查通过：" + json.dumps(result, ensure_ascii=False))
    print("边界：仅本地文件、引用和设计检查；不证明实图、音频、原书、课程或远端显示已验证。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
